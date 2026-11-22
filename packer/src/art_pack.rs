//! An art pack's folder opened as the client opens it (Pyreal's `pyreal-art-pack`, `lib.rs`), with
//! every file it read for itself and every picture it made kept for packing ([`open`]).
//!
//! The models are read from their glTF files, their pictures decoded, given their levels and
//! compressed in BC7; each ground's three pictures are brought to the first ground's size; each
//! material's pictures are made as [`materials::material`] says; grit and moon pictures are made
//! once each; and a model with no pictures of its own gets a card ([`cards`]). What will not read
//! is left out with a line saying why, as the client leaves it out.

use std::collections::{BTreeMap, HashMap, HashSet};

use crate::manifest::{ArtPackManifest, DataId, ManifestGround, Views, MANIFEST_FILE};
use crate::{cards, gltf, images, materials, packed, Image};

/// A metallic-roughness material, its pictures by index into the pack's pictures: what a card is
/// drawn with.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct PackMaterial {
    /// The base colour factor, linear, with alpha.
    pub base_color: [f32; 4],
    pub base_color_image: Option<u32>,
    pub normal_image: Option<u32>,
    pub metal_rough_image: Option<u32>,
    pub occlusion_image: Option<u32>,
    /// The alpha a pixel is cut below, for a cut-out material.
    pub alpha_cutoff: Option<f32>,
    /// Whether both faces are drawn.
    pub double_sided: bool,
}

/// One part of a level of detail: triangles of one material.
#[derive(Debug, Clone, PartialEq)]
pub struct PackPrimitive {
    /// [`gltf::VERTEX_FLOATS`] floats a vertex, model space, height up.
    pub vertices: Vec<f32>,
    /// Three a triangle.
    pub indices: Vec<u32>,
    pub material: PackMaterial,
}

/// One level of detail.
#[derive(Debug, Clone, PartialEq)]
pub struct PackLod {
    /// How far from the eye it is drawn, metres; infinite for a last level with no limit.
    pub distance: f32,
    pub primitives: Vec<PackPrimitive>,
    /// For a level that is pictures of the model seen from round it, how they are laid out.
    pub views: Option<Views>,
    /// Drawn into the sun's shadows alone, never into the view.
    pub shadows_only: bool,
}

/// One model of a pack.
#[derive(Debug, Clone, PartialEq)]
pub struct PackModel {
    /// The retail object it is drawn in place of.
    pub id: DataId,
    /// Cut-out growth.
    pub foliage: bool,
    /// Its levels of detail, nearest first.
    pub lods: Vec<PackLod>,
}

/// What opening a pack read and made, and what it could not.
#[derive(Debug, Default)]
pub struct Opened {
    /// The pack's name.
    pub name: String,
    /// The hash of its manifest and every file it read.
    pub hash: String,
    /// Every file read for itself (the manifest, the models and their buffers), by path.
    pub files: BTreeMap<String, Vec<u8>>,
    /// Every picture made, by what a packed pack keeps it under.
    pub pictures: BTreeMap<String, Vec<Image>>,
    /// What would not read, a line each.
    pub problems: Vec<String>,
}

/// What a ground material takes where it names no picture: a level height, a flat normal, a
/// rough surface and no occlusion.
const GROUND_DEFAULTS: [u8; 4] = [128, 128, 230, 255];

/// A ground's three pictures from its base colour with the height in alpha (`albedo`), its
/// normal in red and green (`normal`), both `side` texels a side, and its roughness and
/// occlusion in red and green (`surface`), at half that, with their levels and compressed. A
/// larger normal or surface that is the same at every texel (`constant`) is one block of it.
fn ground_pictures(
    side: u32,
    albedo: Vec<u8>,
    normal: Vec<u8>,
    surface: &[u8],
    constant: [bool; 2],
) -> [Image; 3] {
    let half = (side / 2).max(1);
    let block = |rgba: &[u8]| rgba[..4].repeat(16);
    let (nside, normal) = if constant[0] && side > 4 {
        (4, block(&normal))
    } else {
        (side, normal)
    };
    let (half, surface) = if constant[1] && half > 4 {
        (4, block(surface))
    } else {
        (half, resampled(side, side, surface, half))
    };
    let albedo = Image {
        srgb: true,
        ..images::with_levels(side, side, albedo, false, None)
    };
    [
        images::compressed(albedo, images::BlockFormat::Bc7),
        images::compressed(
            images::with_levels(nside, nside, normal, false, None),
            images::BlockFormat::Bc5,
        ),
        images::compressed(
            images::with_levels(half, half, surface, false, None),
            images::BlockFormat::Bc5,
        ),
    ]
}

/// `rgba` (`w` by `h`) resampled to `size` by `size`, wrapping at its edges (a ground picture
/// repeats), each texel the bilinear mix of the four nearest.
fn resampled(w: u32, h: u32, rgba: &[u8], size: u32) -> Vec<u8> {
    if (w, h) == (size, size) {
        return rgba.to_vec();
    }
    let (w, h) = (w.max(1) as usize, h.max(1) as usize);
    let n = size.max(1) as usize;
    let mut out = Vec::with_capacity(n * n * 4);
    #[allow(
        clippy::cast_precision_loss,
        clippy::cast_possible_truncation,
        clippy::cast_sign_loss
    )]
    // Texel coordinates of pictures far smaller than a float's exact range.
    for y in 0..n {
        let fy = ((y as f32 + 0.5) * h as f32 / n as f32 - 0.5).rem_euclid(h as f32);
        let (y0, ty) = (fy.floor() as usize % h, fy.fract());
        let y1 = (y0 + 1) % h;
        for x in 0..n {
            let fx = ((x as f32 + 0.5) * w as f32 / n as f32 - 0.5).rem_euclid(w as f32);
            let (x0, tx) = (fx.floor() as usize % w, fx.fract());
            let x1 = (x0 + 1) % w;
            for c in 0..4 {
                let at = |xx: usize, yy: usize| f32::from(rgba[(yy * w + xx) * 4 + c]);
                let top = at(x0, y0) + (at(x1, y0) - at(x0, y0)) * tx;
                let bottom = at(x0, y1) + (at(x1, y1) - at(x0, y1)) * tx;
                out.push((top + (bottom - top) * ty + 0.5).clamp(0.0, 255.0) as u8);
            }
        }
    }
    out
}

/// The files of one ground material, as read.
struct GroundFiles {
    base: Vec<u8>,
    normal: Option<Vec<u8>>,
    height: Option<Vec<u8>>,
    roughness: Option<Vec<u8>>,
    occlusion: Option<Vec<u8>>,
}

impl GroundFiles {
    /// The files `entry` names, read through `read`.
    fn read(
        entry: &ManifestGround,
        read: &mut dyn FnMut(&str) -> Result<Vec<u8>, String>,
    ) -> Result<Self, String> {
        let base = read(&entry.base_color)?;
        let mut channel = |path: &Option<String>| path.as_deref().map(&mut *read).transpose();
        Ok(Self {
            base,
            normal: channel(&entry.normal)?,
            height: channel(&entry.height)?,
            roughness: channel(&entry.roughness)?,
            occlusion: channel(&entry.occlusion)?,
        })
    }
}

/// The ground material `entry`'s three pictures from its `files`, brought to `size` by `size`
/// texels (its base colour's own size when `size` is `None`).
fn ground(
    entry: &ManifestGround,
    files: &GroundFiles,
    size: Option<u32>,
) -> Result<[Image; 3], String> {
    let picture = |bytes: &[u8], path: &str| -> Result<(u32, u32, Vec<u8>), String> {
        images::decode_png(bytes).map_err(|e| format!("{path}: {e}"))
    };
    let (w, h, base) = picture(&files.base, &entry.base_color)?;
    if w == 0 || h == 0 {
        return Err(format!("{}: an empty picture", entry.base_color));
    }
    let side = size.unwrap_or(w.max(h));
    let base = resampled(w, h, &base, side);
    let channel =
        |bytes: &Option<Vec<u8>>, path: &Option<String>| -> Result<Option<Vec<u8>>, String> {
            let (Some(bytes), Some(path)) = (bytes, path) else {
                return Ok(None);
            };
            let (w, h, rgba) = picture(bytes, path)?;
            Ok(Some(resampled(w, h, &rgba, side)))
        };
    let normal = channel(&files.normal, &entry.normal)?;
    let height = channel(&files.height, &entry.height)?;
    let roughness = channel(&files.roughness, &entry.roughness)?;
    let occlusion = channel(&files.occlusion, &entry.occlusion)?;
    let texels = (side as usize) * (side as usize);
    let mut albedo = Vec::with_capacity(texels * 4);
    let mut bent = Vec::with_capacity(texels * 4);
    let mut surface = Vec::with_capacity(texels * 4);
    let red = |p: &Option<Vec<u8>>, i: usize, c: usize, default: u8| {
        p.as_ref().map_or(default, |p| p[i * 4 + c])
    };
    for i in 0..texels {
        albedo.extend([
            base[i * 4],
            base[i * 4 + 1],
            base[i * 4 + 2],
            red(&height, i, 0, GROUND_DEFAULTS[0]),
        ]);
        bent.extend([
            red(&normal, i, 0, GROUND_DEFAULTS[0]),
            red(&normal, i, 1, GROUND_DEFAULTS[1]),
            0,
            255,
        ]);
        surface.extend([
            red(&roughness, i, 0, GROUND_DEFAULTS[2]),
            red(&occlusion, i, 0, GROUND_DEFAULTS[3]),
            0,
            255,
        ]);
    }
    Ok(ground_pictures(
        side,
        albedo,
        bent,
        &surface,
        [normal.is_none(), roughness.is_none() && occlusion.is_none()],
    ))
}

/// A picture of a pack's models, to be made from its file.
struct PendingPicture {
    path: String,
    /// The file's bytes, read to make the picture from.
    bytes: Vec<u8>,
    srgb: bool,
    cutoff: Option<f32>,
    /// A picture of a level of pictures of its model seen from round it.
    views: bool,
}

impl PendingPicture {
    /// What a packed pack keeps the picture under.
    fn key(&self) -> String {
        packed::model_key(&self.path, self.srgb, self.cutoff, self.views)
    }
}

/// The picture made from a model's picture file's `bytes`: decoded, stretched to whole blocks,
/// given its levels and compressed.
fn make(path: &str, bytes: &[u8], srgb: bool, cutoff: Option<f32>, views: bool) -> Result<Image, String> {
    let (w, h, rgba) = images::decode_png(bytes).map_err(|e| format!("{path}: {e}"))?;
    let (w, h, rgba) = images::to_whole_blocks(w, h, rgba);
    let levels = if views {
        images::with_view_levels(w, h, rgba, srgb)
    } else {
        images::with_levels(w, h, rgba, srgb, cutoff)
    };
    Ok(images::compressed(levels, images::BlockFormat::Bc7))
}

/// What an opening pack reads its files through: each hashed as it is read, and the files read
/// for themselves kept.
struct Reader<'r> {
    read: &'r mut dyn FnMut(&str) -> Result<Vec<u8>, String>,
    hash: ContentHash,
    kept: BTreeMap<String, Vec<u8>>,
}

impl Reader<'_> {
    /// The file at `path`, read for itself: a model or one of its buffers.
    fn file(&mut self, path: &str) -> Result<Vec<u8>, String> {
        let bytes = self.for_picture(path)?;
        self.kept.insert(path.to_owned(), bytes.clone());
        Ok(bytes)
    }

    /// The file at `path`, read to make a picture from.
    fn for_picture(&mut self, path: &str) -> Result<Vec<u8>, String> {
        let bytes = (self.read)(path)?;
        self.hash.part(path, &bytes);
        Ok(bytes)
    }
}

/// A short hash of what a pack read: the first eight bytes of its BLAKE3 hash in hex, each file
/// framed by the lengths of its path and its bytes (the client's report hash).
#[derive(Debug, Clone, Default)]
struct ContentHash(blake3::Hasher);

impl ContentHash {
    fn part(&mut self, name: &str, bytes: &[u8]) {
        let len = |n: usize| u64::try_from(n).unwrap_or(u64::MAX).to_le_bytes();
        self.0.update(&len(name.len()));
        self.0.update(name.as_bytes());
        self.0.update(&len(bytes.len()));
        self.0.update(bytes);
    }

    fn finish(&self) -> String {
        self.0.finalize().as_bytes()[..8]
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect()
    }
}

/// The pack whose manifest is `manifest_text`, its files read through `read_file` by path
/// relative to the pack, opened as the client opens a folder: what it read and made.
///
/// # Errors
/// The manifest will not read, or names models none of which reads.
#[allow(clippy::too_many_lines)] // the client's one pass over the manifest
pub fn open(
    manifest_text: &str,
    read_file: &mut dyn FnMut(&str) -> Result<Vec<u8>, String>,
) -> Result<Opened, String> {
    // Every file read is hashed as it is read, after the manifest.
    let mut reader = Reader {
        read: read_file,
        hash: ContentHash::default(),
        kept: BTreeMap::new(),
    };
    reader.hash.part(MANIFEST_FILE, manifest_text.as_bytes());
    reader
        .kept
        .insert(MANIFEST_FILE.to_owned(), manifest_text.as_bytes().to_vec());
    let manifest = ArtPackManifest::parse(manifest_text).map_err(|e| e.to_string())?;
    let mut recorded: BTreeMap<String, Vec<Image>> = BTreeMap::new();
    let mut problems = Vec::new();
    let mut models = Vec::new();
    // Each picture once, by path and whether it holds colour, read here and made below.
    let mut pending: Vec<PendingPicture> = Vec::new();
    let mut by_path: HashMap<(String, bool, bool), u32> = HashMap::new();
    for entry in &manifest.models {
        let label = gltf::label(entry.id);
        let mut lods = Vec::with_capacity(entry.lods.len());
        let mut failed = None;
        for lod in &entry.lods {
            let read_model = reader
                .file(&lod.file)
                .and_then(|json| gltf::decode(&json, &lod.file, &mut |p| reader.file(p)));
            match read_model {
                Ok(primitives) => lods.push((lod, primitives)),
                Err(e) => {
                    failed = Some(e);
                    break;
                }
            }
        }
        if let Some(e) = failed {
            problems.push(format!("{label}: {e}"));
            continue;
        }
        let mut picture = |path: &Option<String>,
                           srgb: bool,
                           cutoff: Option<f32>,
                           views: bool|
         -> Result<Option<u32>, String> {
            let Some(path) = path else {
                return Ok(None);
            };
            if let Some(i) = by_path.get(&(path.clone(), srgb, views)) {
                return Ok(Some(*i));
            }
            let bytes = reader.for_picture(path)?;
            let i = u32::try_from(pending.len()).map_err(|_| "too many pictures".to_owned())?;
            pending.push(PendingPicture {
                path: path.clone(),
                bytes,
                srgb,
                cutoff,
                views,
            });
            by_path.insert((path.clone(), srgb, views), i);
            Ok(Some(i))
        };
        let mut built = Vec::with_capacity(lods.len());
        let mut broken = None;
        for (lod, primitives) in lods {
            let mut parts = Vec::with_capacity(primitives.len());
            let views = lod.views.is_some();
            for p in primitives {
                let m = &p.material;
                let material = (|| -> Result<PackMaterial, String> {
                    Ok(PackMaterial {
                        base_color: m.base_color,
                        base_color_image: picture(&m.base_color_image, true, m.alpha_cutoff, views)?,
                        normal_image: picture(&m.normal_image, false, None, views)?,
                        metal_rough_image: picture(&m.metal_rough_image, false, None, views)?,
                        occlusion_image: picture(&m.occlusion_image, false, None, views)?,
                        alpha_cutoff: m.alpha_cutoff,
                        double_sided: m.double_sided,
                    })
                })();
                match material {
                    Ok(material) => parts.push(PackPrimitive {
                        vertices: p.vertices,
                        indices: p.indices,
                        material,
                    }),
                    Err(e) => {
                        broken = Some(e);
                        break;
                    }
                }
            }
            if broken.is_some() {
                break;
            }
            built.push(PackLod {
                distance: lod.distance.unwrap_or(f32::INFINITY),
                primitives: parts,
                views: lod.views,
                shadows_only: lod.shadows_only,
            });
        }
        if let Some(e) = broken {
            problems.push(format!("{label}: {e}"));
            continue;
        }
        models.push(PackModel {
            id: entry.id,
            foliage: entry.foliage,
            lods: built,
        });
    }
    // The pictures made (decoded, given their levels and compressed) on every thread at once; a
    // model whose picture will not make is left out.
    let keys: Vec<String> = pending.iter().map(PendingPicture::key).collect();
    let decoded = images::par_map(pending, &|p| make(&p.path, &p.bytes, p.srgb, p.cutoff, p.views));
    for (key, made) in keys.into_iter().zip(&decoded) {
        if let Ok(image) = made {
            recorded.insert(key, vec![image.clone()]);
        }
    }
    let failed: HashMap<u32, String> = (0u32..)
        .zip(&decoded)
        .filter_map(|(i, d)| d.as_ref().err().map(|e| (i, e.clone())))
        .collect();
    models.retain(|m: &PackModel| {
        let Some(e) = m
            .lods
            .iter()
            .flat_map(|l| &l.primitives)
            .flat_map(|p| {
                let m = &p.material;
                [
                    m.base_color_image,
                    m.normal_image,
                    m.metal_rough_image,
                    m.occlusion_image,
                ]
            })
            .flatten()
            .find_map(|i| failed.get(&i))
        else {
            return true;
        };
        problems.push(format!("{}: {e}", gltf::label(m.id)));
        false
    });
    let images: Vec<Image> = decoded
        .into_iter()
        .map(|d| d.unwrap_or_else(|_| images::with_levels(1, 1, vec![0; 4], false, None)))
        .collect();
    // Cards for the models with none of their own.
    let skip: HashSet<DataId> = manifest.ground_cover.iter().map(|c| c.id).collect();
    for (id, made) in cards::add_cards(&models, &images, &skip) {
        recorded.insert(packed::card_key(id), made.to_vec());
    }
    if models.is_empty() && !manifest.models.is_empty() {
        return Err(format!(
            "no model of the pack would read: {}",
            problems.join("; ")
        ));
    }
    // Every ground at the first one's size, so they are drawn from one array: the files read
    // here, the pictures made on every thread at once.
    let files: Vec<(&ManifestGround, Result<GroundFiles, String>)> = manifest
        .grounds
        .iter()
        .map(|entry| {
            let files = GroundFiles::read(entry, &mut |p| reader.for_picture(p));
            (entry, files)
        })
        .collect();
    let side = files.iter().find_map(|(_, f)| {
        let (w, h) = images::png_size(&f.as_ref().ok()?.base).ok()?;
        Some(w.max(h))
    });
    let made = images::par_map(files, &|(entry, f)| {
        (entry, f.and_then(|f| ground(entry, &f, side)))
    });
    for (entry, g) in made {
        match g {
            Ok(g) => {
                recorded.insert(packed::ground_key(entry), g.to_vec());
            }
            Err(e) => problems.push(format!("ground {:?}: {e}", entry.grounds)),
        }
    }
    // The materials for retail pictures: the files read here, the pictures made on every thread
    // at once.
    let files: Vec<_> = manifest
        .materials
        .iter()
        .map(|entry| {
            let files = materials::MaterialFiles::read(entry, &mut |p| reader.for_picture(p));
            (entry, files)
        })
        .collect();
    let made = images::par_map(files, &|(entry, f)| {
        (entry, f.and_then(|f| materials::material(entry, &f)))
    });
    let mut named = Vec::with_capacity(made.len());
    for (entry, m) in made {
        match m {
            Ok(m) => {
                let mut made: Vec<Image> = m.albedo.into_iter().collect();
                made.extend([m.normal, m.surface]);
                recorded.insert(packed::material_key(entry), made);
                named.push(entry);
            }
            Err(e) => problems.push(format!(
                "material {}: {e}",
                entry
                    .textures
                    .iter()
                    .chain(entry.solid.iter().flat_map(|sd| sd.surfaces.iter()))
                    .map(|t| format!("{:#010X}", t.0))
                    .collect::<Vec<_>>()
                    .join(", ")
            )),
        }
    }
    // The metal maps, one each however many materials share it.
    let mut metal_seen: HashSet<&str> = HashSet::new();
    for entry in &named {
        let Some(path) = entry.metal_map.as_deref() else {
            continue;
        };
        if !metal_seen.insert(path) {
            continue;
        }
        let made = reader
            .for_picture(path)
            .and_then(|bytes| materials::metal(&bytes, path));
        match made {
            Ok(image) => {
                recorded.insert(packed::metal_key(path), vec![image]);
            }
            Err(e) => problems.push(format!("metal map {path}: {e}")),
        }
    }
    // The grit pictures, one each however many materials share it.
    let mut grit_seen: HashSet<&str> = HashSet::new();
    for entry in named {
        let Some(path) = entry.grit.as_deref() else {
            continue;
        };
        if !grit_seen.insert(path) {
            continue;
        }
        let made = reader
            .for_picture(path)
            .and_then(|bytes| materials::grit(&bytes, path));
        match made {
            Ok(image) => {
                recorded.insert(packed::grit_key(path), vec![image]);
            }
            Err(e) => problems.push(format!("grit {path}: {e}")),
        }
    }
    // The moons' pictures, made as a model's colour is.
    for entry in &manifest.moons {
        let mut made = |path: &str| -> Result<(), String> {
            let image = reader
                .for_picture(path)
                .and_then(|bytes| make(path, &bytes, true, None, false))?;
            recorded.insert(packed::moon_key(path), vec![image]);
            Ok(())
        };
        let moon = made(&entry.surface).and_then(|()| {
            entry.lights.as_deref().map(&mut made).transpose()?;
            entry.clouds.as_deref().map(&mut made).transpose()?;
            Ok(())
        });
        if let Err(e) = moon {
            problems.push(format!("moon {:#010X}: {e}", entry.object.0));
        }
    }
    Ok(Opened {
        name: manifest.name,
        hash: reader.hash.finish(),
        files: reader.kept,
        pictures: recorded,
        problems,
    })
}
