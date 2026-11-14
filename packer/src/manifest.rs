//! An art pack's manifest, `manifest.toml` at the top of the pack's folder: Pyreal's
//! `pyreal_assets::art_pack` (`core/assets/src/art_pack.rs`), which describes the format, read the
//! same way and refused for the same reasons, with the lookups only the client makes left out.

use std::collections::{HashMap, HashSet};

/// A retail record's id.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct DataId(pub u32);

impl DataId {
    #[must_use]
    pub const fn raw(self) -> u32 {
        self.0
    }
}

/// A record's fingerprint (Pyreal's `pyreal_assets::fingerprint`): only read and compared here.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Fingerprint {
    /// A picture's size and average hash.
    Picture { width: u32, height: u32, hash: u64 },
    /// A model's hash.
    Model(u64),
}

impl Fingerprint {
    /// The fingerprint `text` spells: `picture 64x64 0123456789abcdef` or `model 0123456789abcdef`.
    #[must_use]
    pub fn parse(text: &str) -> Option<Self> {
        let words: Vec<&str> = text.split_whitespace().collect();
        let hex = |s: &str| {
            (s.len() == 16)
                .then(|| u64::from_str_radix(s, 16).ok())
                .flatten()
        };
        match words.as_slice() {
            ["picture", size, hash] => {
                let (w, h) = size.split_once('x')?;
                Some(Self::Picture {
                    width: w.parse().ok()?,
                    height: h.parse().ok()?,
                    hash: hex(hash)?,
                })
            }
            ["model", hash] => Some(Self::Model(hex(hash)?)),
            _ => None,
        }
    }
}

/// The manifest format this module reads.
pub const FORMAT: i64 = 1;

/// The manifest's file name at the top of a pack's folder.
pub const MANIFEST_FILE: &str = "manifest.toml";

/// The number the first kind of ground cover's model is known by, the kinds after it counting up:
/// it stands for no retail object, and no retail object's id reaches it.
pub const GROUND_COVER_IDS: u32 = 0xC000_0000;

/// A pack's manifest.
#[derive(Debug, Clone, PartialEq)]
pub struct ArtPackManifest {
    /// The pack's name.
    pub name: String,
    /// Its models, in the order the manifest lists them.
    pub models: Vec<ManifestModel>,
    /// Its ground materials, in the order the manifest lists them.
    pub grounds: Vec<ManifestGround>,
    /// Its materials for retail pictures, in the order the manifest lists them.
    pub materials: Vec<ManifestMaterial>,
    /// The kinds of plant it lays over the land. Each kind's model is among [`Self::models`], after
    /// the models for retail objects, under the id the kind names.
    pub ground_cover: Vec<ManifestGroundCover>,
    /// The lights it gives retail objects, in the order the manifest lists them.
    pub lights: Vec<ManifestLight>,
    /// The moons it draws again, in the order the manifest lists them.
    pub moons: Vec<ManifestMoon>,
}

/// A retail moon a pack draws again as a ball.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ManifestMoon {
    /// The retail moon's graphics object.
    pub object: DataId,
    /// Its colour, and its height in alpha, over the whole ball longitude by latitude.
    pub surface: String,
    /// What burns on its night side, laid as the surface is.
    pub lights: Option<String>,
    /// A layer of cloud over the ground, its cover in alpha, laid as the surface is.
    pub clouds: Option<String>,
    /// Who made it, with what, under which license.
    pub credit: Credit,
}

/// Where a pack's light is given to its object.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LightPlace {
    /// Where the object stands outdoors.
    Outdoors,
    /// Where it stands in a building's or a dungeon's rooms.
    Indoors,
    /// Wherever it stands.
    Both,
}

impl LightPlace {
    /// Whether an object standing outdoors (`outdoors`) or in a room is given the light.
    #[must_use]
    pub fn takes(self, outdoors: bool) -> bool {
        match self {
            Self::Outdoors => outdoors,
            Self::Indoors => !outdoors,
            Self::Both => true,
        }
    }
}

/// How a pack's light moves.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LightFlicker {
    /// As a flame does.
    Flame,
    /// As a bed of embers breathes.
    Embers,
    /// Not at all.
    Steady,
}

/// A light a pack gives a retail object.
#[derive(Debug, Clone, PartialEq)]
pub struct ManifestLight {
    /// The retail object.
    pub object: DataId,
    /// Where it is given.
    pub place: LightPlace,
    /// Metres from where retail's light stood: east, north and up.
    pub offset: [f32; 3],
    /// Its colour temperature, kelvin.
    pub kelvin: f32,
    /// Lumens.
    pub brightness: f32,
    /// Metres across.
    pub size: f32,
    /// Metres its light reaches.
    pub reach: f32,
    /// Whether it casts shadows.
    pub shadows: bool,
    /// How it moves.
    pub flicker: LightFlicker,
    /// How brightly the air about it glows.
    pub haze: f32,
    /// How much of its glow it keeps against the daylight.
    pub presence: f32,
    /// Metres: the object's lights this near each other are one light; 0 for none.
    pub gather: f32,
    /// Who made it, with what, and under which license.
    pub credit: Credit,
}

/// One kind of plant a pack lays over the land.
#[derive(Debug, Clone, PartialEq)]
pub struct ManifestGroundCover {
    /// The number its model is known by, from [`GROUND_COVER_IDS`].
    pub id: DataId,
    /// The retail terrain types it grows on, each 0 to 31.
    pub grounds: Vec<u8>,
    /// How many plants a square metre.
    pub density: f32,
    /// The smallest and the largest it is scaled by.
    pub scale: (f32, f32),
    /// The steepest slope it grows on, degrees.
    pub steepest: f32,
}

/// One material drawn in place of retail pictures: the pictures it stands for and its own.
#[derive(Debug, Clone, PartialEq)]
pub struct ManifestMaterial {
    /// The retail pictures (texture records, `0x05...`) it is drawn in place of.
    pub textures: Vec<DataId>,
    /// The base color picture, with the retail picture's alpha.
    pub base_color: String,
    /// The tangent-space normal picture: red along the picture's width, green up it.
    pub normal: Option<String>,
    /// The roughness picture, in its red.
    pub roughness: Option<String>,
    /// The ambient occlusion picture, in its red.
    pub occlusion: Option<String>,
    /// The height picture, in its red: white is the surface, black its deepest.
    pub height: Option<String>,
    /// How strongly the normal picture bends the normal.
    pub normal_scale: f32,
    /// Whether the retail picture is drawn in place of [`Self::base_color`], which is then only
    /// a flat colour for a reader that draws no relief.
    pub keep_retail_picture: bool,
    /// How wet it looks in a room, from 0 to 1.
    pub damp: f32,
    /// A picture of where it is wet, in its red: white as wet as [`Self::damp`] says, black dry.
    pub damp_map: Option<String>,
    /// Whether it is wet on floors too, not only on walls.
    pub damp_floors: bool,
    /// Whether a film of slime lies on it where it is damp.
    pub slime: bool,
    /// Whether it is glacier ice: deep blue, opaque, with light bent through it.
    pub ice: bool,
    /// How strongly it shines as silk or satin does, from 0 to 1.
    pub sheen: f32,
    /// A small picture of fine surface many materials may share, laid over its own: its bend in
    /// red and green, its speckle in blue and its roughness in alpha, each about a half.
    pub grit: Option<String>,
    /// How many times the grit repeats across one repeat of the retail picture, along its width
    /// and up it.
    pub grit_repeat: [f32; 2],
    /// What it is made of beyond its pictures.
    pub matter: Matter,
    /// The fingerprint of the retail picture each of [`Self::textures`] was made from, where it
    /// names one.
    pub fingerprints: Vec<Option<Fingerprint>>,
    /// Which records it is drawn on.
    pub draws_on: DrawsOn,
    /// The palettes (`0x04...`) it is drawn in alone; any, where it names none.
    pub palettes: Vec<DataId>,
    /// Who made it, with what, and under which license.
    pub credit: Credit,
}

/// What a material is made of beyond its pictures: a metal, how smooth, or clear as ice or a gem.
#[derive(Debug, Clone, Copy, PartialEq, Default)]
pub struct Matter {
    /// A metal, its picture brightened this many times to its colour.
    pub metal: Option<f32>,
    /// How smooth it is where no roughness picture says, 0 to 1.
    pub gloss: Option<f32>,
    /// Clear in its picture's own colour, this share of the world behind seen through it.
    pub clear: Option<f32>,
    /// How strongly a clear material bends light: its index of refraction.
    pub refraction: f32,
    /// How much of a film of water lies on it, 0 to 1.
    pub wet: Option<f32>,
}

impl Matter {
    /// Whether it says nothing beyond its pictures.
    #[must_use]
    pub fn is_plain(&self) -> bool {
        self.metal.is_none() && self.gloss.is_none() && self.clear.is_none() && self.wet.is_none()
    }
}

/// Which retail records an entry is drawn on.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum DrawsOn {
    /// Those whose fingerprint matches its own; any, where it names none.
    #[default]
    Matching,
    /// Any record of its id.
    Any,
    /// None: the entry is not drawn.
    Nothing,
}

/// A retail ground a pack's material is drawn for.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Ground {
    /// A terrain type, 0 to 31.
    Type(u8),
    /// The road laid over the terrain.
    Road,
}

/// One ground material: the retail grounds it is drawn for, its pictures and how large a repeat
/// of them is.
#[derive(Debug, Clone, PartialEq)]
pub struct ManifestGround {
    /// The retail grounds it is drawn for.
    pub grounds: Vec<Ground>,
    /// The base colour picture.
    pub base_color: String,
    /// The tangent-space normal picture, red toward east and green toward north.
    pub normal: Option<String>,
    /// The height picture, in its red: where two grounds meet, the higher shows through.
    pub height: Option<String>,
    /// The roughness picture, in its red.
    pub roughness: Option<String>,
    /// The ambient occlusion picture, in its red.
    pub occlusion: Option<String>,
    /// How many metres one repeat of the pictures covers.
    pub size: f32,
    /// How strongly the normal picture bends the normal.
    pub normal_scale: f32,
    /// Laid on the steep slopes of its grounds rather than on their flat ground: a `[[steep]]`
    /// table's.
    pub steep: bool,
    /// The fingerprint of the retail picture its grounds are laid with in the world it was made
    /// for, where it names one: it is drawn only where the world's region matches.
    pub fingerprint: Option<Fingerprint>,
    /// Who made it, with what, and under which license.
    pub credit: Credit,
}

/// One model: the retail object it is drawn in place of, its levels of detail, how it is lit
/// and who made it.
#[derive(Debug, Clone, PartialEq)]
pub struct ManifestModel {
    /// The retail object: a setup (`0x02...`) or a graphics object (`0x01...`).
    pub id: DataId,
    /// The levels of detail, nearest first.
    pub lods: Vec<ManifestLod>,
    /// Cut-out growth: the model's cut-out materials (needles, leaves, grass) are drawn from both
    /// sides and lit through from behind as well as from the front. Its other materials (a
    /// trunk) are ordinary surfaces.
    pub foliage: bool,
    /// How much the wind moves it: 0 not at all, 1 as much as growth of its height moves.
    pub wind: f32,
    /// The fingerprint of the retail object it was made for, where it names one.
    pub fingerprint: Option<Fingerprint>,
    /// Which records it is drawn on.
    pub draws_on: DrawsOn,
    /// Who made it, with what, and under which license.
    pub credit: Credit,
}

/// One level of detail.
#[derive(Debug, Clone, PartialEq)]
pub struct ManifestLod {
    /// The glTF 2.0 file, relative to the pack's folder.
    pub file: String,
    /// How far from the eye it is drawn, metres; `None` for the last level drawn at any
    /// distance.
    pub distance: Option<f32>,
    /// For a level that is pictures of the model seen from round it, how they are laid out.
    pub views: Option<Views>,
    /// Drawn into the sun's shadows alone, never into the view.
    pub shadows_only: bool,
}

/// How a level made of pictures of its model lays them out: how many views round the model, and
/// how many tiles to a row of its pictures.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Views {
    /// The views, evenly round the model's upright axis.
    pub count: u32,
    /// The tiles to a row.
    pub columns: u32,
}

/// Who made a model, with what, and under which license.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct Credit {
    /// The author.
    pub author: String,
    /// The tool or pipeline it was made with.
    pub tool: String,
    /// The license it is shared under.
    pub license: String,
}

/// Why a manifest was refused, as a sentence.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ManifestError(pub String);

impl std::fmt::Display for ManifestError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "art pack manifest: {}", self.0)
    }
}

fn fail<T>(why: impl Into<String>) -> Result<T, ManifestError> {
    Err(ManifestError(why.into()))
}

impl ArtPackManifest {
    /// The manifest in `text`.
    ///
    /// # Errors
    /// [`ManifestError`] when the text is not TOML, its format is not [`FORMAT`], or a model is
    /// incomplete or contradicts another: an id that is not a setup or a graphics object, an id
    /// listed twice, no level of detail, a file path that is absolute or climbs out of the pack,
    /// distances that do not grow, a level before the last with no distance, or a credit left
    /// out; or a ground material is: a ground that is not a terrain type or the road, a ground
    /// two materials claim, no base color, or a size that is not a positive number; or a
    /// material for retail pictures is: a picture that is not a texture record, a picture two
    /// materials claim, no base color, a picture path outside the pack, or a damp, a grit repeat
    /// or a switch out of range; or a kind of ground cover is: a ground that is not a terrain
    /// type, a density, scale or slope out of range, or a last level with no distance or pictures
    /// for a level.
    pub fn parse(text: &str) -> Result<Self, ManifestError> {
        let table: toml::Table = match text.parse() {
            Ok(t) => t,
            Err(e) => return fail(format!("not TOML: {e}")),
        };
        let Some(pack) = table.get("pack").and_then(toml::Value::as_table) else {
            return fail("no [pack] table");
        };
        match pack.get("format").and_then(toml::Value::as_integer) {
            Some(FORMAT) => {}
            Some(f) => return fail(format!("format {f}, and this client reads format {FORMAT}")),
            None => return fail("the [pack] table names no format"),
        }
        let name = pack
            .get("name")
            .and_then(toml::Value::as_str)
            .unwrap_or_default()
            .to_owned();
        let empty = Vec::new();
        let listed = match table.get("model") {
            None => &empty,
            Some(toml::Value::Array(a)) => a,
            Some(_) => return fail("`model` is not a list of [[model]] tables"),
        };
        // Each entry is checked against the earlier entries of its own id, found through these.
        let mut model_at: HashMap<DataId, Vec<usize>> = HashMap::new();
        let mut models: Vec<ManifestModel> = Vec::with_capacity(listed.len());
        for (i, m) in listed.iter().enumerate() {
            let Some(m) = m.as_table() else {
                return fail(format!("model {} is not a table", i + 1));
            };
            let model = model(m).map_err(|e| ManifestError(format!("model {}: {}", i + 1, e.0)))?;
            let same = model_at.entry(model.id).or_default();
            if same.iter().any(|&k| {
                let o = &models[k];
                o.fingerprint.is_none() || o.fingerprint == model.fingerprint
            }) {
                return fail(format!("{:#010X} is listed twice", model.id.0));
            }
            same.push(models.len());
            models.push(model);
        }
        let mut ground_at: HashMap<(bool, Ground), Vec<usize>> = HashMap::new();
        let mut grounds: Vec<ManifestGround> = Vec::new();
        for (kind, steep) in [("terrain", false), ("steep", true)] {
            let listed = match table.get(kind) {
                None => &empty,
                Some(toml::Value::Array(a)) => a,
                Some(_) => return fail(format!("`{kind}` is not a list of [[{kind}]] tables")),
            };
            for (i, g) in listed.iter().enumerate() {
                let Some(g) = g.as_table() else {
                    return fail(format!("{kind} {} is not a table", i + 1));
                };
                let mut ground =
                    ground(g).map_err(|e| ManifestError(format!("{kind} {}: {}", i + 1, e.0)))?;
                ground.steep = steep;
                for k in &ground.grounds {
                    let same = ground_at.get(&(steep, *k)).map_or(&[][..], Vec::as_slice);
                    if same.iter().any(|&j| {
                        let o = &grounds[j];
                        o.fingerprint.is_none() || o.fingerprint == ground.fingerprint
                    }) {
                        return fail(format!("{kind} {}: {k:?} has a material already", i + 1));
                    }
                }
                for k in &ground.grounds {
                    let same = ground_at.entry((steep, *k)).or_default();
                    if same.last() != Some(&grounds.len()) {
                        same.push(grounds.len());
                    }
                }
                grounds.push(ground);
            }
        }
        let listed = match table.get("material") {
            None => &empty,
            Some(toml::Value::Array(a)) => a,
            Some(_) => return fail("`material` is not a list of [[material]] tables"),
        };
        let mut material_at: HashMap<DataId, Vec<usize>> = HashMap::new();
        let mut materials: Vec<ManifestMaterial> = Vec::with_capacity(listed.len());
        for (i, m) in listed.iter().enumerate() {
            let Some(m) = m.as_table() else {
                return fail(format!("material {} is not a table", i + 1));
            };
            let material =
                material(m).map_err(|e| ManifestError(format!("material {}: {}", i + 1, e.0)))?;
            for (t, print) in material.textures.iter().zip(&material.fingerprints) {
                let same = material_at.get(t).map_or(&[][..], Vec::as_slice);
                if same.iter().map(|&j| &materials[j]).any(|o| {
                    let apart = !o.palettes.is_empty()
                        && !material.palettes.is_empty()
                        && !o.palettes.iter().any(|p| material.palettes.contains(p));
                    !apart
                        && o.textures
                            .iter()
                            .zip(&o.fingerprints)
                            .any(|(u, p)| u == t && (p.is_none() || p == print))
                }) {
                    return fail(format!(
                        "material {}: {:#010X} has a material already",
                        i + 1,
                        t.0
                    ));
                }
            }
            for t in &material.textures {
                let same = material_at.entry(*t).or_default();
                if same.last() != Some(&materials.len()) {
                    same.push(materials.len());
                }
            }
            materials.push(material);
        }
        let listed = match table.get("ground_cover") {
            None => &empty,
            Some(toml::Value::Array(a)) => a,
            Some(_) => return fail("`ground_cover` is not a list of [[ground_cover]] tables"),
        };
        let mut ground_cover: Vec<ManifestGroundCover> = Vec::with_capacity(listed.len());
        for (i, c) in listed.iter().enumerate() {
            let Some(c) = c.as_table() else {
                return fail(format!("ground cover {} is not a table", i + 1));
            };
            let id = DataId(GROUND_COVER_IDS + u32::try_from(i).unwrap_or(u32::MAX >> 2));
            let (kind, model) = kind_of_cover(c, id)
                .map_err(|e| ManifestError(format!("ground cover {}: {}", i + 1, e.0)))?;
            ground_cover.push(kind);
            models.push(model);
        }
        let listed = match table.get("light") {
            None => &empty,
            Some(toml::Value::Array(a)) => a,
            Some(_) => return fail("`light` is not a list of [[light]] tables"),
        };
        let mut light_at: HashMap<DataId, Vec<usize>> = HashMap::new();
        let mut lights: Vec<ManifestLight> = Vec::with_capacity(listed.len());
        for (i, l) in listed.iter().enumerate() {
            let Some(l) = l.as_table() else {
                return fail(format!("light {} is not a table", i + 1));
            };
            let light = light(l).map_err(|e| ManifestError(format!("light {}: {}", i + 1, e.0)))?;
            let same = light_at.entry(light.object).or_default();
            if same.iter().map(|&j| &lights[j]).any(|o| {
                o.place.takes(true) && light.place.takes(true)
                    || o.place.takes(false) && light.place.takes(false)
            }) {
                return fail(format!(
                    "light {}: {:#010X} has a light there already",
                    i + 1,
                    light.object.0
                ));
            }
            same.push(lights.len());
            lights.push(light);
        }
        let listed = match table.get("moon") {
            None => &empty,
            Some(toml::Value::Array(a)) => a,
            Some(_) => return fail("`moon` is not a list of [[moon]] tables"),
        };
        let mut moon_ids: HashSet<DataId> = HashSet::new();
        let mut moons: Vec<ManifestMoon> = Vec::with_capacity(listed.len());
        for (i, m) in listed.iter().enumerate() {
            let Some(m) = m.as_table() else {
                return fail(format!("moon {} is not a table", i + 1));
            };
            let moon = moon(m).map_err(|e| ManifestError(format!("moon {}: {}", i + 1, e.0)))?;
            if !moon_ids.insert(moon.object) {
                return fail(format!(
                    "moon {}: {:#010X} is listed twice",
                    i + 1,
                    moon.object.0
                ));
            }
            moons.push(moon);
        }
        Ok(Self {
            name,
            models,
            grounds,
            materials,
            ground_cover,
            lights,
            moons,
        })
    }
}

/// The id in `raw`: `0x` and eight hex digits, of a setup or a graphics object.
fn object_id(raw: &str) -> Result<DataId, ManifestError> {
    let digits = raw
        .trim()
        .strip_prefix("0x")
        .or_else(|| raw.trim().strip_prefix("0X"));
    let Some(id) = digits.and_then(|d| u32::from_str_radix(d, 16).ok()) else {
        return fail(format!("id {raw:?} is not 0x and hex digits"));
    };
    match id >> 24 {
        0x01 | 0x02 => Ok(DataId(id)),
        _ => fail(format!(
            "id {id:#010X} is neither a setup (0x02...) nor a graphics object (0x01...)"
        )),
    }
}

/// Whether `path` names a file inside the pack: relative, `/` between its parts, and no part
/// empty, `.` or `..`.
fn inside_the_pack(path: &str) -> bool {
    !path.is_empty()
        && !path.starts_with('/')
        && !path.contains('\\')
        && !path.contains(':')
        && path
            .split('/')
            .all(|part| !part.is_empty() && part != "." && part != "..")
}

fn text<'t>(t: &'t toml::Table, key: &str) -> Result<&'t str, ManifestError> {
    match t.get(key).and_then(toml::Value::as_str).map(str::trim) {
        Some(v) if !v.is_empty() => Ok(v),
        _ => fail(format!("no {key}")),
    }
}

/// The grounds `v` names: a terrain type, `"road"`, or a list of them.
fn grounds_of(v: Option<&toml::Value>) -> Result<Vec<Ground>, ManifestError> {
    let one = |v: &toml::Value| -> Result<Ground, ManifestError> {
        match v {
            toml::Value::Integer(t) => match u8::try_from(*t) {
                Ok(t) if t < 32 => Ok(Ground::Type(t)),
                _ => fail(format!("ground {t} is not a terrain type from 0 to 31")),
            },
            toml::Value::String(s) if s.trim().eq_ignore_ascii_case("road") => Ok(Ground::Road),
            other => fail(format!(
                "ground {other} is neither a terrain type nor \"road\""
            )),
        }
    };
    let grounds = match v {
        None => return fail("no ground"),
        Some(toml::Value::Array(a)) => a.iter().map(one).collect::<Result<Vec<_>, _>>()?,
        Some(v) => vec![one(v)?],
    };
    if grounds.is_empty() {
        return fail("no ground");
    }
    Ok(grounds)
}

fn ground(t: &toml::Table) -> Result<ManifestGround, ManifestError> {
    let grounds = grounds_of(t.get("ground"))?;
    let picture = |key: &str| -> Result<Option<String>, ManifestError> {
        match t.get(key) {
            None => Ok(None),
            Some(v) => match v.as_str().map(str::trim) {
                Some(p) if inside_the_pack(p) => Ok(Some(p.to_owned())),
                _ => fail(format!("{key} is not a path inside the pack")),
            },
        }
    };
    let Some(base_color) = picture("base_color")? else {
        return fail("no base_color");
    };
    let number = |key: &str| -> Result<Option<f32>, ManifestError> {
        #[allow(clippy::cast_possible_truncation, clippy::cast_precision_loss)]
        // Metres and strengths, well inside both types' range.
        match t.get(key) {
            None => Ok(None),
            Some(toml::Value::Float(f)) => Ok(Some(*f as f32)),
            Some(toml::Value::Integer(i)) => Ok(Some(*i as f32)),
            Some(_) => fail(format!("{key} is not a number")),
        }
    };
    let size = match number("size")? {
        Some(s) if s.is_finite() && s > 0.0 => s,
        Some(s) => return fail(format!("size {s} is not a positive number")),
        None => return fail("no size"),
    };
    let normal_scale = match number("normal_scale")? {
        Some(s) if s.is_finite() && s >= 0.0 => s,
        Some(s) => return fail(format!("normal_scale {s} is not a number from 0")),
        None => 1.0,
    };
    Ok(ManifestGround {
        grounds,
        base_color,
        normal: picture("normal")?,
        height: picture("height")?,
        roughness: picture("roughness")?,
        occlusion: picture("occlusion")?,
        size,
        normal_scale,
        steep: false,
        fingerprint: fingerprints_of(t.get("fingerprint"), 1)?.remove(0),
        credit: Credit {
            author: text(t, "author")?.to_owned(),
            tool: text(t, "tool")?.to_owned(),
            license: text(t, "license")?.to_owned(),
        },
    })
}

/// The retail pictures `v` names: a texture record id (`0x05...`), or a list of them.
fn textures_of(v: Option<&toml::Value>) -> Result<Vec<DataId>, ManifestError> {
    let one = |v: &toml::Value| -> Result<DataId, ManifestError> {
        let Some(raw) = v.as_str() else {
            return fail(format!("texture {v} is not 0x and hex digits"));
        };
        let digits = raw
            .trim()
            .strip_prefix("0x")
            .or_else(|| raw.trim().strip_prefix("0X"));
        match digits.and_then(|d| u32::from_str_radix(d, 16).ok()) {
            Some(id) if id >> 24 == 0x05 => Ok(DataId(id)),
            Some(id) => fail(format!(
                "texture {id:#010X} is not a texture record (0x05...)"
            )),
            None => fail(format!("texture {raw:?} is not 0x and hex digits")),
        }
    };
    let textures = match v {
        None => return fail("no texture"),
        Some(toml::Value::Array(a)) => a.iter().map(one).collect::<Result<Vec<_>, _>>()?,
        Some(v) => vec![one(v)?],
    };
    if textures.is_empty() {
        return fail("no texture");
    }
    Ok(textures)
}

/// The fingerprints `v` names for `count` records: one text, or a list of one for each.
fn fingerprints_of(
    v: Option<&toml::Value>,
    count: usize,
) -> Result<Vec<Option<Fingerprint>>, ManifestError> {
    let one = |v: &toml::Value| -> Result<Fingerprint, ManifestError> {
        v.as_str()
            .and_then(Fingerprint::parse)
            .map_or_else(|| fail(format!("fingerprint {v} is not one")), Ok)
    };
    match v {
        None => Ok(vec![None; count]),
        Some(toml::Value::Array(a)) if a.len() == count => {
            a.iter().map(|v| one(v).map(Some)).collect()
        }
        Some(toml::Value::Array(_)) => fail(format!("fingerprint does not name {count}")),
        Some(v) if count == 1 => Ok(vec![Some(one(v)?)]),
        Some(_) => fail(format!("fingerprint does not name {count}")),
    }
}

/// The palettes `v` names: palette records (`0x04...`), one or a list.
fn palettes_of(v: Option<&toml::Value>) -> Result<Vec<DataId>, ManifestError> {
    let one = |v: &toml::Value| -> Result<DataId, ManifestError> {
        let id = v
            .as_str()
            .and_then(|s| s.trim().strip_prefix("0x"))
            .and_then(|d| u32::from_str_radix(d, 16).ok());
        match id {
            Some(id) if id >> 24 == 0x04 => Ok(DataId(id)),
            _ => fail(format!("palette {v} is not a palette record (0x04...)")),
        }
    };
    match v {
        None => Ok(Vec::new()),
        Some(toml::Value::Array(a)) => a.iter().map(one).collect(),
        Some(v) => Ok(vec![one(v)?]),
    }
}

/// The records an entry is drawn on, as its `draws_on` says.
fn draws_on(t: &toml::Table) -> Result<DrawsOn, ManifestError> {
    match t.get("draws_on").map(|v| v.as_str()) {
        None | Some(Some("matching")) => Ok(DrawsOn::Matching),
        Some(Some("any")) => Ok(DrawsOn::Any),
        Some(Some("none")) => Ok(DrawsOn::Nothing),
        Some(_) => fail("draws_on is not matching, any or none"),
    }
}

fn material(t: &toml::Table) -> Result<ManifestMaterial, ManifestError> {
    let textures = textures_of(t.get("texture"))?;
    let picture = |key: &str| -> Result<Option<String>, ManifestError> {
        match t.get(key) {
            None => Ok(None),
            Some(v) => match v.as_str().map(str::trim) {
                Some(p) if inside_the_pack(p) => Ok(Some(p.to_owned())),
                _ => fail(format!("{key} is not a path inside the pack")),
            },
        }
    };
    let Some(base_color) = picture("base_color")? else {
        return fail("no base_color");
    };
    #[allow(clippy::cast_possible_truncation, clippy::cast_precision_loss)]
    // A strength, well inside both types' range.
    let normal_scale = match t.get("normal_scale") {
        None => 1.0,
        Some(toml::Value::Float(f)) if f.is_finite() && *f >= 0.0 => *f as f32,
        Some(toml::Value::Integer(i)) if *i >= 0 => *i as f32,
        Some(v) => return fail(format!("normal_scale {v} is not a number from 0")),
    };
    let flag = |key: &str| match t.get(key) {
        None => Ok(false),
        Some(toml::Value::Boolean(b)) => Ok(*b),
        Some(v) => fail(format!("{key} {v} is not true or false")),
    };
    #[allow(clippy::cast_possible_truncation, clippy::cast_precision_loss)]
    // A share, well inside both types' range.
    let damp = match t.get("damp") {
        None => 0.0,
        Some(toml::Value::Float(f)) if (0.0..=1.0).contains(f) => *f as f32,
        Some(toml::Value::Integer(i)) if (0..=1).contains(i) => *i as f32,
        Some(v) => return fail(format!("damp {v} is not a number from 0 to 1")),
    };
    #[allow(clippy::cast_possible_truncation, clippy::cast_precision_loss)]
    // A share, well inside both types' range.
    let sheen = match t.get("sheen") {
        None => 0.0,
        Some(toml::Value::Float(f)) if (0.0..=1.0).contains(f) => *f as f32,
        Some(toml::Value::Integer(i)) if (0..=1).contains(i) => *i as f32,
        Some(v) => return fail(format!("sheen {v} is not a number from 0 to 1")),
    };
    #[allow(clippy::cast_possible_truncation, clippy::cast_precision_loss)]
    // A count of repeats, well inside both types' range.
    let part = |v: &toml::Value| {
        match v {
            toml::Value::Float(f) if *f > 0.0 => Some(*f as f32),
            toml::Value::Integer(i) if *i > 0 => Some(*i as f32),
            _ => None,
        }
        // Finite once narrowed: a manifest's 1e300 is an `f32` infinity.
        .filter(|f| f.is_finite())
    };
    let grit_repeat = match t.get("grit_repeat") {
        None => [1.0, 1.0],
        Some(toml::Value::Array(a)) if a.len() == 2 => match (part(&a[0]), part(&a[1])) {
            (Some(u), Some(v)) => [u, v],
            _ => return fail("grit_repeat is not two numbers above 0"),
        },
        Some(_) => return fail("grit_repeat is not two numbers above 0"),
    };
    #[allow(clippy::cast_possible_truncation, clippy::cast_precision_loss)]
    // A share or an index, well inside both types' range.
    let number = |key: &str, lo: f64, hi: f64| match t.get(key) {
        None => Ok(None),
        Some(toml::Value::Float(f)) if (lo..=hi).contains(f) => Ok(Some(*f as f32)),
        Some(toml::Value::Integer(i)) if (lo..=hi).contains(&(*i as f64)) => Ok(Some(*i as f32)),
        Some(v) => fail(format!("{key} {v} is not a number from {lo} to {hi}")),
    };
    let fingerprints = fingerprints_of(t.get("fingerprint"), textures.len())?;
    let draws_on = draws_on(t)?;
    let palettes = palettes_of(t.get("palettes"))?;
    let matter = Matter {
        metal: flag("metal")?.then_some(number("brighten", 0.1, 20.0)?.unwrap_or(1.0)),
        gloss: number("gloss", 0.0, 1.0)?,
        clear: number("clear", 0.0, 1.0)?,
        refraction: number("refraction", 1.0, 3.0)?.unwrap_or(1.31),
        wet: number("wet", 0.0, 1.0)?,
    };
    Ok(ManifestMaterial {
        textures,
        base_color,
        normal: picture("normal")?,
        roughness: picture("roughness")?,
        occlusion: picture("occlusion")?,
        height: picture("height")?,
        normal_scale,
        keep_retail_picture: flag("keep_retail_picture")?,
        damp,
        damp_map: picture("damp_map")?,
        damp_floors: flag("damp_floors")?,
        slime: flag("slime")?,
        ice: flag("ice")?,
        sheen,
        grit: picture("grit")?,
        grit_repeat,
        matter,
        fingerprints,
        draws_on,
        palettes,
        credit: Credit {
            author: text(t, "author")?.to_owned(),
            tool: text(t, "tool")?.to_owned(),
            license: text(t, "license")?.to_owned(),
        },
    })
}

/// A light a pack gives a retail object.
fn light(t: &toml::Table) -> Result<ManifestLight, ManifestError> {
    let object = object_id(t.get("object").and_then(toml::Value::as_str).unwrap_or(""))?;
    let place = match t.get("where").map(|v| v.as_str()) {
        None => LightPlace::Both,
        Some(Some("outdoors")) => LightPlace::Outdoors,
        Some(Some("indoors")) => LightPlace::Indoors,
        Some(Some("both")) => LightPlace::Both,
        Some(_) => return fail("where is not outdoors, indoors or both"),
    };
    #[allow(clippy::cast_possible_truncation, clippy::cast_precision_loss)]
    // Metres, lumens and kelvin from a manifest, well inside both types' range.
    let part = |v: &toml::Value| {
        match v {
            toml::Value::Float(f) => Some(*f as f32),
            toml::Value::Integer(i) => Some(*i as f32),
            _ => None,
        }
        // Finite once narrowed: a manifest's 1e300 is an `f32` infinity.
        .filter(|f| f.is_finite())
    };
    let offset = match t.get("offset") {
        None => [0.0; 3],
        Some(toml::Value::Array(a)) if a.len() == 3 => {
            match (part(&a[0]), part(&a[1]), part(&a[2])) {
                (Some(x), Some(y), Some(z)) => [x, y, z],
                _ => return fail("offset is not three numbers"),
            }
        }
        Some(_) => return fail("offset is not three numbers"),
    };
    let within = |key: &str, lo: f32, hi: f32, otherwise: Option<f32>| match t.get(key) {
        None => otherwise.map_or_else(|| fail(format!("no {key}")), Ok),
        Some(v) => match part(v) {
            Some(v) if (lo..=hi).contains(&v) => Ok(v),
            Some(v) => fail(format!("{key} {v} is not from {lo} to {hi}")),
            None => fail(format!("{key} is not a number")),
        },
    };
    let shadows = match t.get("shadows") {
        None => true,
        Some(v) => match v.as_bool() {
            Some(b) => b,
            None => return fail("shadows is not true or false"),
        },
    };
    let flicker = match t.get("flicker").map(|v| v.as_str()) {
        None | Some(Some("steady")) => LightFlicker::Steady,
        Some(Some("flame")) => LightFlicker::Flame,
        Some(Some("embers")) => LightFlicker::Embers,
        Some(_) => return fail("flicker is not flame, embers or steady"),
    };
    Ok(ManifestLight {
        object,
        place,
        offset,
        kelvin: within("kelvin", 1000.0, 12000.0, None)?,
        brightness: within("brightness", 0.1, 100_000.0, None)?,
        size: within("size", 0.0, 2.0, Some(0.1))?,
        reach: within("reach", 0.5, 60.0, None)?,
        shadows,
        flicker,
        haze: within("haze", 0.0, 4.0, Some(0.0))?,
        presence: within("presence", 0.0, 1.0, Some(0.0))?,
        gather: within("gather", 0.0, 30.0, Some(0.0))?,
        credit: Credit {
            author: text(t, "author")?.to_owned(),
            tool: text(t, "tool")?.to_owned(),
            license: text(t, "license")?.to_owned(),
        },
    })
}

/// A retail moon a pack draws again.
fn moon(t: &toml::Table) -> Result<ManifestMoon, ManifestError> {
    let object = object_id(t.get("object").and_then(toml::Value::as_str).unwrap_or(""))?;
    if object.0 >> 24 != 0x01 {
        return fail(format!("{:#010X} is not a graphics object", object.0));
    }
    let picture = |key: &str| -> Result<Option<String>, ManifestError> {
        match t.get(key) {
            None => Ok(None),
            Some(v) => match v.as_str().map(str::trim) {
                Some(p) if inside_the_pack(p) => Ok(Some(p.to_owned())),
                _ => fail(format!("{key} is not a path inside the pack")),
            },
        }
    };
    let Some(surface) = picture("surface")? else {
        return fail("no surface");
    };
    Ok(ManifestMoon {
        object,
        surface,
        lights: picture("lights")?,
        clouds: picture("clouds")?,
        credit: Credit {
            author: text(t, "author")?.to_owned(),
            tool: text(t, "tool")?.to_owned(),
            license: text(t, "license")?.to_owned(),
        },
    })
}

/// The number at `key`, whole or not.
fn number(t: &toml::Table, key: &str) -> Result<Option<f32>, ManifestError> {
    #[allow(clippy::cast_possible_truncation, clippy::cast_precision_loss)]
    // A small number from a manifest, well inside both types' range.
    match t.get(key) {
        None => Ok(None),
        Some(toml::Value::Float(f)) => Ok(Some(*f as f32)),
        Some(toml::Value::Integer(i)) => Ok(Some(*i as f32)),
        Some(_) => fail(format!("{key} is not a number")),
    }
}

/// One kind of ground cover and its model, known by `id`.
fn kind_of_cover(
    t: &toml::Table,
    id: DataId,
) -> Result<(ManifestGroundCover, ManifestModel), ManifestError> {
    let grounds = grounds_of(t.get("ground"))?
        .into_iter()
        .map(|g| match g {
            Ground::Type(t) => Ok(t),
            Ground::Road => fail("nothing grows on the road"),
        })
        .collect::<Result<Vec<u8>, ManifestError>>()?;
    let Some(density) = number(t, "density")? else {
        return fail("no density");
    };
    if !(density > 0.0 && density <= 16.0) {
        return fail(format!("density {density} is not above 0 and at most 16"));
    }
    let scale = match t.get("scale") {
        None => (1.0, 1.0),
        Some(toml::Value::Array(a)) => {
            let at = |k: usize| {
                #[allow(clippy::cast_possible_truncation, clippy::cast_precision_loss)]
                // A small number from a manifest, well inside both types' range.
                a.get(k).and_then(|v| {
                    v.as_float()
                        .map(|f| f as f32)
                        .or_else(|| v.as_integer().map(|i| i as f32))
                })
            };
            match (a.len(), at(0), at(1)) {
                (2, Some(lo), Some(hi)) => (lo, hi),
                _ => return fail("scale is not two numbers"),
            }
        }
        Some(_) => match number(t, "scale")? {
            Some(s) => (s, s),
            None => return fail("scale is not a number"),
        },
    };
    if !(scale.0 > 0.0 && scale.0 <= scale.1 && scale.1.is_finite()) {
        return fail(format!("scale {scale:?} does not grow from above 0"));
    }
    let steepest = number(t, "steepest")?.unwrap_or(40.0);
    if !(steepest > 0.0 && steepest <= 90.0) {
        return fail(format!("steepest {steepest} is not above 0 and at most 90"));
    }
    let foliage = flag(t, "foliage", true)?;
    let model = model_known_as(t, id, foliage)?;
    if model.lods.iter().any(|l| l.views.is_some()) {
        return fail("a level is pictures of the model, which ground cover does not draw");
    }
    if model
        .lods
        .iter()
        .rfind(|l| !l.shadows_only)
        .is_none_or(|l| l.distance.is_none())
    {
        return fail("its last level names no distance, and it is drawn near the eye alone");
    }
    Ok((
        ManifestGroundCover {
            id,
            grounds,
            density,
            scale,
            steepest,
        },
        model,
    ))
}

/// The true or false at `key`, `otherwise` where there is none.
fn flag(t: &toml::Table, key: &str, otherwise: bool) -> Result<bool, ManifestError> {
    match t.get(key) {
        None => Ok(otherwise),
        Some(v) => match v.as_bool() {
            Some(b) => Ok(b),
            None => fail(format!("{key} is not true or false")),
        },
    }
}

fn model(t: &toml::Table) -> Result<ManifestModel, ManifestError> {
    let id = object_id(t.get("id").and_then(toml::Value::as_str).unwrap_or(""))?;
    let foliage = flag(t, "foliage", false)?;
    model_known_as(t, id, foliage)
}

/// The model a table describes, its levels and its credit, known by `id`.
fn model_known_as(
    t: &toml::Table,
    id: DataId,
    foliage: bool,
) -> Result<ManifestModel, ManifestError> {
    let credit = Credit {
        author: text(t, "author")?.to_owned(),
        tool: text(t, "tool")?.to_owned(),
        license: text(t, "license")?.to_owned(),
    };
    let Some(levels) = t.get("lod").and_then(toml::Value::as_array) else {
        return fail("no [[model.lod]] level of detail");
    };
    if levels.is_empty() {
        return fail("no [[model.lod]] level of detail");
    }
    let mut lods: Vec<ManifestLod> = Vec::with_capacity(levels.len());
    for (k, l) in levels.iter().enumerate() {
        let Some(l) = l.as_table() else {
            return fail(format!("level {k} is not a table"));
        };
        let file = text(l, "file")?;
        if !inside_the_pack(file) {
            return fail(format!(
                "level {k}'s file {file:?} is not a path inside the pack"
            ));
        }
        #[allow(clippy::cast_possible_truncation, clippy::cast_precision_loss)]
        // A distance in metres, well inside both types' range.
        let distance = match l.get("distance") {
            None => None,
            Some(toml::Value::Float(f)) => Some(*f as f32),
            Some(toml::Value::Integer(i)) => Some(*i as f32),
            Some(_) => return fail(format!("level {k}'s distance is not a number")),
        };
        let shadows_only = match l.get("shadows_only") {
            None => false,
            Some(v) => match v.as_bool() {
                Some(b) => b,
                None => return fail(format!("level {k}'s shadows_only is not true or false")),
            },
        };
        if shadows_only && (k == 0 || k + 1 == levels.len()) {
            return fail(format!(
                "level {k} is for the shadows only, and the first and the last level are drawn"
            ));
        }
        // A level for the shadows alone has no distance of its own in the view.
        let distance = distance.filter(|_| !shadows_only);
        if let Some(d) = distance {
            if !(d.is_finite() && d > 0.0) {
                return fail(format!("level {k}'s distance {d} is not a positive number"));
            }
            if let Some(before) = lods
                .iter()
                .rev()
                .find(|p| !p.shadows_only)
                .and_then(|p| p.distance)
            {
                if d <= before {
                    return fail(format!(
                        "level {k}'s distance {d} does not reach past the level before it"
                    ));
                }
            }
        }
        if !shadows_only
            && lods
                .iter()
                .rev()
                .find(|p| !p.shadows_only)
                .is_some_and(|p| p.distance.is_none())
        {
            return fail(format!(
                "a level before level {k} names no distance, and only the last level may leave \
                 it out"
            ));
        }
        let count = |key: &str| -> Result<Option<u32>, ManifestError> {
            match l.get(key) {
                None => Ok(None),
                Some(v) => match v.as_integer().and_then(|n| u32::try_from(n).ok()) {
                    Some(n) if n >= 1 => Ok(Some(n)),
                    _ => fail(format!("level {k}'s {key} is not a whole number from 1")),
                },
            }
        };
        let views = match (count("views")?, count("columns")?) {
            (None, None) => None,
            (None, Some(_)) => return fail(format!("level {k} names columns and no views")),
            (Some(count), columns) => {
                if count < 2 {
                    return fail(format!("level {k} names fewer than two views"));
                }
                Some(Views {
                    count,
                    columns: columns.unwrap_or(count).min(count),
                })
            }
        };
        lods.push(ManifestLod {
            file: file.to_owned(),
            distance,
            views,
            shadows_only,
        });
    }
    let wind = number(t, "wind")?.unwrap_or(if foliage { 1.0 } else { 0.0 });
    if !(0.0..=2.0).contains(&wind) {
        return fail(format!("wind {wind} is not from 0 to 2"));
    }
    Ok(ManifestModel {
        id,
        lods,
        foliage,
        wind,
        fingerprint: fingerprints_of(t.get("fingerprint"), 1)?.remove(0),
        draws_on: draws_on(t)?,
        credit,
    })
}

