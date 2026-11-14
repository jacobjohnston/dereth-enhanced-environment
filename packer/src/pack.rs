//! Packing an art pack's folder into one file (Pyreal's `tools/art/src/pack.rs`): [`pack`] writes
//! it, and [`check`] says whether a file is what its folder packs into now.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use crate::manifest::MANIFEST_FILE;
use crate::packed::{self, Contents, Kind};

/// What [`pack`] wrote.
#[derive(Debug)]
pub struct Report {
    /// The packed file.
    pub out: PathBuf,
    /// The pack's name.
    pub name: String,
    /// Its records, the contents among them.
    pub records: usize,
    /// Its length.
    pub bytes: u64,
    /// What the pack could not read or make, left out of it, a line each.
    pub problems: Vec<String>,
}

/// The file the folder `dir` packs into unless another is named: beside it, its name and `.dat`.
#[must_use]
pub fn default_out(dir: &Path) -> PathBuf {
    let name = dir
        .file_name()
        .map_or_else(|| "pack".into(), |n| n.to_string_lossy().into_owned());
    dir.with_file_name(format!("{name}.dat"))
}

/// The folder `dir` packed, in memory.
fn build(dir: &Path, layout: u32) -> Result<packed::Packed, String> {
    let at = dir.join(MANIFEST_FILE);
    let manifest = std::fs::read_to_string(&at).map_err(|e| format!("{}: {e}", at.display()))?;
    packed::pack(
        &manifest,
        &mut |path| std::fs::read(dir.join(path)).map_err(|e| format!("{path}: {e}")),
        layout,
    )
}

/// Pack the folder `dir` into the file `out` in `layout`, in place of any there. It is written
/// beside `out` first and then moved over it, so a pack that fails leaves the file that was there.
///
/// # Errors
/// The pack will not open or is too large for one file, or the file will not write.
pub fn pack(dir: &Path, out: &Path, layout: u32) -> Result<Report, String> {
    let made = build(dir, layout)?;
    let partial = out.with_file_name(format!(
        "{}.partial",
        out.file_name()
            .map_or_else(|| "pack".into(), |n| n.to_string_lossy().into_owned())
    ));
    let written = std::fs::write(&partial, &made.bytes)
        .and_then(|()| std::fs::rename(&partial, out))
        .map_err(|e| format!("{}: {e}", out.display()));
    if written.is_err() {
        let _ = std::fs::remove_file(&partial);
    }
    written?;
    Ok(Report {
        out: out.to_path_buf(),
        name: made.name,
        records: made.records,
        bytes: made.bytes.len() as u64,
        problems: made.problems,
    })
}

/// Whether a packed file is what its folder packs into now.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Freshness {
    /// Byte for byte.
    Current,
    /// It differs: a line for each record that changed, is new or is gone, by its key (none
    /// when only the container around them differs).
    Stale(Vec<String>),
    /// There is no file.
    Missing,
}

/// Whether the file `out` is what the folder `dir` packs into now in `layout`: packed again in
/// memory and compared byte for byte.
///
/// # Errors
/// The pack will not open or is too large for one file, or the file will not read.
pub fn check(dir: &Path, out: &Path, layout: u32) -> Result<Freshness, String> {
    let made = build(dir, layout)?;
    let have = match std::fs::read(out) {
        Ok(bytes) => bytes,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(Freshness::Missing),
        Err(e) => return Err(format!("{}: {e}", out.display())),
    };
    if have == made.bytes {
        return Ok(Freshness::Current);
    }
    Ok(Freshness::Stale(differences(have, made.bytes)))
}

/// The records of the packed file `have` that are not those of `made`, a line each.
fn differences(have: Vec<u8>, made: Vec<u8>) -> Vec<String> {
    let (have, made) = match (Contents::of_file(have), Contents::of_file(made)) {
        (Ok(have), Ok(made)) => (have, made),
        (Err(e), _) | (_, Err(e)) => return vec![format!("the file: {e}")],
    };
    let by_key = |c: &Contents| -> BTreeMap<(Kind, String), [u8; 32]> {
        c.records
            .iter()
            .map(|r| ((r.kind, r.key.clone()), r.sha256))
            .collect()
    };
    let (old, new) = (by_key(&have), by_key(&made));
    let mut lines = Vec::new();
    if have.layout != made.layout {
        lines.push(format!("packed in layout {}, not {}", have.layout, made.layout));
    }
    if have.name != made.name {
        lines.push(format!("renamed: {:?} to {:?}", have.name, made.name));
    }
    for (key, sha) in &new {
        match old.get(key) {
            None => lines.push(format!("new: {}", key.1)),
            Some(was) if was != sha => lines.push(format!("changed: {}", key.1)),
            Some(_) => {}
        }
    }
    lines.extend(
        old.keys()
            .filter(|key| !new.contains_key(*key))
            .map(|key| format!("gone: {}", key.1)),
    );
    lines
}
