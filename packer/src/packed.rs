//! An art pack packed into one file (Pyreal's `pyreal-art-pack`, `packed.rs`): its manifest, every
//! file its models are read from, and every picture made as the pack opens, ready for drawing, so
//! a packed pack opens without decoding or compressing a picture. [`pack`] packs one.
//!
//! **The file** is a dat container in the later layout, its blocks [`BLOCK`] bytes and its data
//! subset [`SUBSET`]. Record 1 is its contents; every other record, numbered from 2 in the
//! contents' order, is one of the pack's files, byte for byte, or the pictures made from them, and
//! one identical to an earlier record is not written again but takes its id. Numbers are
//! little-endian, and a string is a 32-bit length and its UTF-8.
//!
//! **Layouts.** In layout 1 ([`PLAIN`]) a record is stored as it is. In layout 2 ([`COMPRESSED`])
//! a record is stored as a zstd frame, or as it is where the frame would be no shorter; the
//! contents are never compressed.
//!
//! **The contents**: `DAPK`, the layout, the manifest format, the pack's name, and the hash of the
//! folder it was packed from. Then a count and, for each record, its kind (0 a file, 1 pictures),
//! its key, its id (0 for an empty file, which has no record), its length, in layout 2 its length
//! as stored, and the SHA-256 of its bytes; then the SHA-256 of all that.
//!
//! **A file** is keyed by its path in the pack. **Pictures** are keyed by how they are made, a
//! `:` between the parts ([`model_key`], [`ground_key`], [`material_key`], [`metal_key`],
//! [`grit_key`], [`moon_key`], [`card_key`]). A pictures record holds a count, then each picture: its width and
//! height, whether it holds color (1) or data (0), its blocks (0 for four bytes a texel, 4 for
//! BC4, 5 for BC5, 7 for BC7) and its level count, then each level, largest first, as its length
//! and its bytes.

use std::borrow::Cow;
use std::collections::HashMap;

use crate::dat::{self, Container};
use crate::images::{BlockFormat, Image};
use crate::manifest::{DataId, ManifestGround, ManifestMaterial, FORMAT};
use crate::{art_pack, cards};

/// The layout whose records are stored as they are.
pub const PLAIN: u32 = 1;

/// The layout whose records are stored as zstd frames where that is shorter.
pub const COMPRESSED: u32 = 2;

/// The zstd level a compressed pack is written at: the slowest to write, the same to read.
const ZSTD_LEVEL: i32 = 19;

/// The container's block size as written, which its header records.
pub const BLOCK: u32 = 0x400;

/// The data subset a packed pack's header carries: `Pack`.
pub const SUBSET: u32 = u32::from_le_bytes(*b"Pack");

/// The contents' magic: `DAPK`.
const MAGIC: u32 = u32::from_le_bytes(*b"DAPK");

/// The contents' record.
pub const CONTENTS: DataId = DataId(1);

/// The first record after the contents.
const FIRST: u32 = 2;

/// The largest packed pack: a container's blocks lie below 2 GiB, where the high bit of a link
/// marks a free block.
const LARGEST: u64 = 0x8000_0000;

/// The blocks the writer keeps free beyond what the record it writes needs.
const RESERVE: u64 = 0x34;

/// What a record of a packed pack holds.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Kind {
    /// One of the pack's files, byte for byte.
    File,
    /// Pictures made from the pack's files.
    Pictures,
}

/// One record a packed pack's contents name.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Record {
    pub kind: Kind,
    /// A file's path, or how its pictures are made.
    pub key: String,
    /// Its id in the container, shared with an identical record; 0 for an empty file.
    pub id: DataId,
    /// Its length.
    pub size: u32,
    /// Its length as stored: `size` where it is stored as it is, shorter for a zstd frame.
    pub stored: u32,
    /// The SHA-256 of its bytes.
    pub sha256: [u8; 32],
}

/// A packed pack's contents: what the pack is and every record it holds.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Contents {
    pub layout: u32,
    /// The manifest format the pack was packed for.
    pub format: u32,
    pub name: String,
    /// The hash of the folder it was packed from.
    pub hash: String,
    /// Its records, in the order their ids were given.
    pub records: Vec<Record>,
}

fn put(out: &mut Vec<u8>, v: u32) {
    out.extend_from_slice(&v.to_le_bytes());
}

fn put_text(out: &mut Vec<u8>, s: &str) {
    put(out, u32::try_from(s.len()).unwrap_or(u32::MAX));
    out.extend_from_slice(s.as_bytes());
}

/// Bytes read from the front.
struct Bytes<'a>(&'a [u8]);

impl<'a> Bytes<'a> {
    fn take(&mut self, n: usize) -> Option<&'a [u8]> {
        if self.0.len() < n {
            return None;
        }
        let (front, rest) = self.0.split_at(n);
        self.0 = rest;
        Some(front)
    }

    fn u32(&mut self) -> Option<u32> {
        Some(u32::from_le_bytes(self.take(4)?.try_into().ok()?))
    }

    fn text(&mut self) -> Option<String> {
        let n = usize::try_from(self.u32()?).ok()?;
        String::from_utf8(self.take(n)?.to_vec()).ok()
    }
}

impl Contents {
    /// The contents' record.
    #[must_use]
    pub fn encode(&self) -> Vec<u8> {
        let mut out = Vec::new();
        put(&mut out, MAGIC);
        put(&mut out, self.layout);
        put(&mut out, self.format);
        put_text(&mut out, &self.name);
        put_text(&mut out, &self.hash);
        put(
            &mut out,
            u32::try_from(self.records.len()).unwrap_or(u32::MAX),
        );
        for r in &self.records {
            out.push(match r.kind {
                Kind::File => 0,
                Kind::Pictures => 1,
            });
            put_text(&mut out, &r.key);
            put(&mut out, r.id.raw());
            put(&mut out, r.size);
            if self.layout == COMPRESSED {
                put(&mut out, r.stored);
            }
            out.extend_from_slice(&r.sha256);
        }
        let sum = dat::record_hash(&out);
        out.extend_from_slice(&sum);
        out
    }

    /// The contents' record, read: the reason, as a sentence, when it is not a packed pack's, or
    /// one of another layout or manifest format, or damaged.
    ///
    /// # Errors
    /// As above.
    pub fn decode(bytes: &[u8]) -> Result<Self, String> {
        let mut b = Bytes(bytes);
        if b.u32() != Some(MAGIC) {
            return Err("not a packed art pack".into());
        }
        let layout = match b.u32() {
            Some(n @ (PLAIN | COMPRESSED)) => n,
            Some(n) => return Err(format!("packed in layout {n}")),
            None => return Err("its contents are damaged".into()),
        };
        let damaged = || "its contents are damaged".to_owned();
        let (body, sum) = bytes.split_at(bytes.len().checked_sub(32).ok_or_else(damaged)?);
        if dat::record_hash(body)[..] != sum[..] {
            return Err(damaged());
        }
        let mut b = Bytes(body.get(8..).ok_or_else(damaged)?);
        let format = b.u32().ok_or_else(damaged)?;
        if i64::from(format) != FORMAT {
            return Err(format!("packed from manifest format {format}"));
        }
        let read = |b: &mut Bytes<'_>| -> Option<Self> {
            let name = b.text()?;
            let hash = b.text()?;
            let count = b.u32()?;
            let mut records = Vec::new();
            for _ in 0..count {
                let kind = match b.take(1)?[0] {
                    0 => Kind::File,
                    1 => Kind::Pictures,
                    _ => return None,
                };
                let key = b.text()?;
                let id = DataId(b.u32()?);
                let size = b.u32()?;
                let stored = if layout == COMPRESSED { b.u32()? } else { size };
                let sha256 = b.take(32)?.try_into().ok()?;
                records.push(Record {
                    kind,
                    key,
                    id,
                    size,
                    stored,
                    sha256,
                });
            }
            b.0.is_empty().then_some(Self {
                layout,
                format,
                name,
                hash,
                records,
            })
        };
        read(&mut b).ok_or_else(damaged)
    }

    /// The contents of the packed file `bytes`.
    ///
    /// # Errors
    /// It is not a packed pack, or its contents will not read.
    pub fn of_file(mut bytes: Vec<u8>) -> Result<Self, String> {
        let file = Container::open(&mut bytes)?;
        if file.data_subset() != SUBSET {
            return Err("not a packed art pack".into());
        }
        Self::decode(&file.read(CONTENTS)?)
    }
}

/// What a packed pack keeps a model's picture under: how it is made, its path last.
#[must_use]
pub fn model_key(path: &str, srgb: bool, cutoff: Option<f32>, views: bool) -> String {
    format!(
        "model:{}:{}:{}:{path}",
        if srgb { "color" } else { "data" },
        cutoff.map_or_else(|| "-".to_owned(), |c| c.to_string()),
        if views { "views" } else { "-" },
    )
}

/// What a packed pack keeps a ground material's three pictures under: the paths of the pictures
/// they are made from.
#[must_use]
pub fn ground_key(entry: &ManifestGround) -> String {
    let path = |p: &Option<String>| p.clone().unwrap_or_default();
    format!(
        "ground:{}:{}:{}:{}:{}",
        entry.base_color,
        path(&entry.normal),
        path(&entry.height),
        path(&entry.roughness),
        path(&entry.occlusion),
    )
}

/// What a packed pack keeps a material's three pictures under, or two where it keeps the retail
/// picture: the paths of the pictures they are made from (no base color for the two), the normal
/// scale its normal picture is bent by and how damp it is.
#[must_use]
pub fn material_key(entry: &ManifestMaterial) -> String {
    let path = |p: &Option<String>| p.clone().unwrap_or_default();
    let base = if entry.keep_retail_picture {
        ""
    } else {
        entry.base_color.as_str()
    };
    let key = format!(
        "material:{base}:{}:{}:{}:{}:{}:{}",
        path(&entry.normal),
        path(&entry.roughness),
        path(&entry.occlusion),
        path(&entry.height),
        entry.normal_scale,
        entry.damp,
    );
    match &entry.damp_map {
        Some(map) => format!("{key}:{map}"),
        None => key,
    }
}

/// What a packed pack keeps a material's metal map under, whichever materials share it.
#[must_use]
pub fn metal_key(path: &str) -> String {
    format!("metal:{path}")
}

/// What a packed pack keeps a material's clear map under, whichever materials share it.
#[must_use]
pub fn clear_key(path: &str) -> String {
    format!("clear:{path}")
}

/// What a packed pack keeps a grit picture under, whichever materials share it.
#[must_use]
pub fn grit_key(path: &str) -> String {
    format!("grit:{path}")
}

/// What a packed pack keeps a moon's picture under.
#[must_use]
pub fn moon_key(path: &str) -> String {
    format!("moon:{path}")
}

/// What a packed pack keeps a model's card under: the cards' make and the model's id.
#[must_use]
pub fn card_key(id: DataId) -> String {
    format!("card:{}:{:#010X}", cards::MAKE, id.raw())
}

/// The number a pictures record gives a picture's blocks.
fn blocks_code(format: Option<BlockFormat>) -> u32 {
    match format {
        None => 0,
        Some(BlockFormat::Bc4) => 4,
        Some(BlockFormat::Bc5) => 5,
        Some(BlockFormat::Bc7) => 7,
    }
}

/// The length of the pictures record holding `pictures`.
fn pictures_len(pictures: &[Image]) -> usize {
    4 + pictures
        .iter()
        .map(|p| 20 + p.levels.iter().map(|l| 4 + l.len()).sum::<usize>())
        .sum::<usize>()
}

/// The pictures record holding `pictures`.
fn encode_pictures(pictures: &[Image]) -> Vec<u8> {
    let count = |n: usize| u32::try_from(n).unwrap_or(u32::MAX);
    let mut out = Vec::with_capacity(pictures_len(pictures));
    put(&mut out, count(pictures.len()));
    for p in pictures {
        put(&mut out, p.width);
        put(&mut out, p.height);
        put(&mut out, u32::from(p.srgb));
        put(&mut out, blocks_code(p.format));
        put(&mut out, count(p.levels.len()));
        for level in &p.levels {
            put(&mut out, count(level.len()));
            out.extend_from_slice(level);
        }
    }
    out
}

/// What [`pack`] made.
#[derive(Debug)]
pub struct Packed {
    /// The pack's name.
    pub name: String,
    /// What it could not read or make, left out of the file, a line each.
    pub problems: Vec<String>,
    /// The packed file.
    pub bytes: Vec<u8>,
    /// Its records, the contents among them.
    pub records: usize,
}

/// The pack whose manifest is `manifest`, every file it names read through `read` by its path
/// relative to the pack, packed into one file in `layout`: opened as the client opens it, with
/// every file it read for itself and every picture it made. The same files always give the same
/// bytes: the records are written in their keys' order, with no date, into a container exactly as
/// large as they need, each identical record written once.
///
/// # Errors
/// The pack will not open, or is too large for one file.
#[allow(clippy::too_many_lines)] // one pass from the folder to the file
pub fn pack(
    manifest: &str,
    read: &mut dyn FnMut(&str) -> Result<Vec<u8>, String>,
    layout: u32,
) -> Result<Packed, String> {
    let block = BLOCK;
    if ![PLAIN, COMPRESSED].contains(&layout) {
        return Err(format!("no layout {layout}: {PLAIN} or {COMPRESSED}"));
    }
    let opened = art_pack::open(manifest, read)?;
    let (files, pictures) = (&opened.files, &opened.pictures);
    let too_large = |what: &str| format!("{what} is larger than one record holds");
    let mut contents = Contents {
        layout,
        format: u32::try_from(FORMAT).unwrap_or(u32::MAX),
        name: opened.name.clone(),
        hash: opened.hash.clone(),
        records: Vec::with_capacity(files.len() + pictures.len()),
    };
    let listed = files
        .iter()
        .map(|(key, bytes)| (Kind::File, key, Cow::Borrowed(&bytes[..])))
        .chain(
            pictures
                .iter()
                .map(|(key, made)| (Kind::Pictures, key, Cow::Owned(encode_pictures(made)))),
        );
    // Hashed as listed, so a record identical to an earlier one takes its id.
    let mut next = FIRST;
    let mut ids: HashMap<(u32, [u8; 32]), DataId> = HashMap::new();
    let mut first = Vec::with_capacity(contents.records.capacity());
    for (kind, key, bytes) in listed {
        let size = u32::try_from(bytes.len()).map_err(|_| too_large(key))?;
        let sha256 = dat::record_hash(&bytes);
        let mut fresh = false;
        let id = if size == 0 {
            DataId(0)
        } else {
            *ids.entry((size, sha256)).or_insert_with(|| {
                fresh = true;
                next += 1;
                DataId(next - 1)
            })
        };
        first.push(fresh);
        contents.records.push(Record {
            kind,
            key: key.clone(),
            id,
            size,
            stored: size,
            sha256,
        });
    }
    let bytes_of = |r: &Record| -> Cow<'_, [u8]> {
        match r.kind {
            Kind::File => Cow::Borrowed(&files[&r.key]),
            Kind::Pictures => Cow::Owned(encode_pictures(&pictures[&r.key])),
        }
    };
    // Each record written once as it is stored, compressed side by side in layout 2.
    let fresh: Vec<&Record> = contents
        .records
        .iter()
        .zip(&first)
        .filter(|(_, first)| **first)
        .map(|(r, _)| r)
        .collect();
    let stored: Vec<(DataId, Vec<u8>)> = crate::images::par_map(fresh, &|r: &Record| {
        let bytes = bytes_of(r);
        let frame = (layout == COMPRESSED)
            .then(|| zstd::bulk::compress(&bytes, ZSTD_LEVEL).ok())
            .flatten()
            .filter(|f| f.len() < bytes.len());
        (r.id, frame.unwrap_or_else(|| bytes.into_owned()))
    });
    let lengths: HashMap<DataId, u32> = stored
        .iter()
        .map(|(id, b)| (*id, u32::try_from(b.len()).unwrap_or(u32::MAX)))
        .collect();
    for r in &mut contents.records {
        if let Some(&n) = lengths.get(&r.id) {
            r.stored = n;
        }
    }
    // The container exactly as large as the records need: a chain each, the contents', the
    // directory's nodes as it grows, and the room the writer keeps in hand.
    let per = u64::from(block - 4);
    let blocks = |len: usize| (len as u64).div_ceil(per);
    let records = (next - FIRST) as usize + 1;
    let nodes = blocks(dat::NODE_SIZE) * (1 + 2 * (records as u64).div_ceil(30));
    let total = contents
        .records
        .iter()
        .zip(&first)
        .filter(|(_, first)| **first)
        .map(|(r, _)| blocks(r.stored as usize))
        .sum::<u64>()
        + blocks(contents.encode().len())
        + nodes
        + RESERVE
        + 2;
    let size = 0x400 + u64::from(block) * total;
    if size > LARGEST {
        return Err(format!(
            "the pack takes {} MB packed, and one file holds {} MB",
            size >> 20,
            LARGEST >> 20
        ));
    }
    let size = u32::try_from(size).map_err(|_| too_large("the pack"))?;
    // Its length set once, before the writer fills it.
    let mut storage = vec![0u8; size as usize];
    let mut w = Container::create(&mut storage, block, dat::PORTAL_DATFILE, SUBSET, size)?;
    for (id, bytes) in &stored {
        w.save(*id, bytes).map_err(|e| format!("{id:?}: {e}"))?;
    }
    w.save(CONTENTS, &contents.encode())?;
    // Grown past what was reckoned, it may not reach past what one file holds either.
    let file_size = w.file_size();
    drop(w);
    if u64::from(file_size) > LARGEST {
        return Err(format!(
            "the pack takes {} MB packed, and one file holds {} MB",
            file_size >> 20,
            LARGEST >> 20
        ));
    }
    Ok(Packed {
        name: opened.name,
        problems: opened.problems,
        bytes: storage,
        records,
    })
}
