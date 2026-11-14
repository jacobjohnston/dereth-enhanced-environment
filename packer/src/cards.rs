//! Cards worked out as a pack is packed: each model with no pictures of its own is drawn from
//! round it into a level of pictures, its colour and its normal. Only the pictures are made here;
//! the client lays the card's level itself.

use std::collections::{HashMap, HashSet};
use std::f32::consts::TAU;

use crate::art_pack::{PackLod, PackModel};
use crate::gltf::VERTEX_FLOATS;
use crate::images::{self, Image};
use crate::manifest::{DataId, Views};
use crate::math;

/// The cards' make, in the key a packed pack keeps each card under: bumped whenever a card is
/// drawn differently, so a pack packed with older cards has them drawn again as it opens.
pub const MAKE: u32 = 1;

/// The views round a card's model, and the tiles to a row.
pub const VIEWS: Views = Views {
    count: 16,
    columns: 4,
};

/// A tile's texels a metre of its model's height, and the least and most of its height.
const TEXELS_A_METRE: f32 = 8.0;
const LEAST_TILE: u32 = 32;
const MOST_TILE: u32 = 128;

/// Texels drawn each way for each texel kept, before the pictures are shrunk to their size.
const SUPERSAMPLE: u32 = 2;

/// How many texels the colour round a card's edges is carried into the empty texels beyond.
const BLEED: u32 = 6;

/// The share of its colour a texel no other view sees keeps: shaded by the rest of the model.
const HIDDEN_KEPT: f32 = 0.2;

/// The share of the views a texel is seen from where it keeps all its colour, matched to the
/// models drawn whole: a leaf's, and a solid surface's, an open face of which is seen from seven
/// views of the sixteen.
const LEAF_OPEN_SHARE: f32 = 2.0 / 3.0;
const SOLID_OPEN_SHARE: f32 = 0.4;

/// A picture's largest level, four bytes a texel.
#[derive(Debug)]
pub struct Texels {
    width: u32,
    height: u32,
    rgba: Vec<u8>,
}

impl Texels {
    fn of(image: &Image) -> Option<Self> {
        let level = image.levels.first()?;
        let rgba = match image.format {
            Some(f) => crate::block_codec::decode(f, image.width, image.height, level),
            None => level.to_vec(),
        };
        (rgba.len() == (image.width * image.height * 4) as usize).then_some(Self {
            width: image.width,
            height: image.height,
            rgba,
        })
    }

    /// The texel at `uv`, the picture repeated.
    fn at(&self, uv: [f32; 2]) -> [u8; 4] {
        #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)] // wrapped into range
        let (x, y) = (
            ((uv[0].rem_euclid(1.0) * self.width as f32) as u32).min(self.width - 1),
            ((uv[1].rem_euclid(1.0) * self.height as f32) as u32).min(self.height - 1),
        );
        let i = ((y * self.width + x) * 4) as usize;
        [
            self.rgba[i],
            self.rgba[i + 1],
            self.rgba[i + 2],
            self.rgba[i + 3],
        ]
    }
}

/// A card worked out for a model: its colour and normal pictures.
#[derive(Debug)]
pub struct Card {
    pub colour: Image,
    pub normal: Image,
}

/// One part a card is drawn from: triangles of one surface, in the model's own space, height up.
#[derive(Debug)]
pub struct Part<'a> {
    /// [`VERTEX_FLOATS`] floats a vertex.
    pub vertices: &'a [f32],
    /// Three a triangle.
    pub indices: &'a [u32],
    /// Its base colour picture.
    pub picture: Option<&'a Texels>,
    /// The base colour, linear, and its alpha.
    pub base_color: [f32; 4],
    /// The alpha it is cut below.
    pub cut: Option<f32>,
    /// Whether both faces are drawn.
    pub double_sided: bool,
}

/// A card for each of `models` with no pictures of its own, but those `skip` names, drawn from
/// their pictures in `images`: each card's pictures by its model, colour first.
pub fn add_cards(
    models: &[PackModel],
    images: &[Image],
    skip: &HashSet<DataId>,
) -> Vec<(DataId, [Image; 2])> {
    let wanted: Vec<usize> = (0..models.len())
        .filter(|k| !skip.contains(&models[*k].id) && source(&models[*k]).is_some())
        .collect();
    let mut used: Vec<u32> = wanted
        .iter()
        .filter_map(|k| source(&models[*k]))
        .flat_map(|l| &l.primitives)
        .filter_map(|p| p.material.base_color_image)
        .collect();
    used.sort_unstable();
    used.dedup();
    let decoded = images::par_map(used.clone(), &|i| {
        images.get(i as usize).and_then(Texels::of)
    });
    let pictures: HashMap<u32, Texels> = used
        .into_iter()
        .zip(decoded)
        .filter_map(|(i, t)| t.map(|t| (i, t)))
        .collect();
    let cards = images::par_map(wanted.clone(), &|k| bake(&models[k], &pictures));
    wanted
        .into_iter()
        .zip(cards)
        .filter_map(|(k, card)| card.map(|c| (models[k].id, [c.colour, c.normal])))
        .collect()
}

/// The level a model's card is drawn from: its first level of shape the view draws, for a model
/// with no level of pictures.
fn source(m: &PackModel) -> Option<&PackLod> {
    if m.lods.iter().any(|l| l.views.is_some()) {
        return None;
    }
    m.lods
        .iter()
        .find(|l| !l.shadows_only && !l.primitives.is_empty())
}

/// Where a model's card stands round its upright axis: half its width, its foot and its top.
fn extent(parts: &[Part<'_>]) -> Option<(f32, f32, f32)> {
    let (mut half, mut foot, mut top) = (0.0f32, f32::MAX, f32::MIN);
    for p in parts {
        for v in p.vertices.as_chunks::<VERTEX_FLOATS>().0 {
            half = half.max(math::hypotf(v[0], v[1]));
            foot = foot.min(v[2]);
            top = top.max(v[2]);
        }
    }
    (half > 0.05 && top - foot > 0.05).then_some((half, foot, top))
}

/// `v` rounded up to a whole block of four.
fn blocks(v: f32) -> u32 {
    #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)] // a small positive size
    let n = v.ceil().max(4.0) as u32;
    n.next_multiple_of(4)
}

/// The texels of one view as drawn: the nearest surface's depth, colour, normal and coverage,
/// and whether it is a leaf (a cut-out surface, or any of a plant's).
struct Drawn {
    depth: Vec<f32>,
    colour: Vec<[f32; 3]>,
    normal: Vec<[f32; 3]>,
    leaf: Vec<bool>,
}

/// `m`'s card, drawn from `pictures` (its base colour pictures, by index); `None` for a model too
/// small or flat to draw.
fn bake(m: &PackModel, pictures: &HashMap<u32, Texels>) -> Option<Card> {
    bake_parts(&parts(m, pictures)?, m.foliage)
}

/// The parts `m`'s card is drawn from, their pictures from `pictures`.
fn parts<'a>(m: &'a PackModel, pictures: &'a HashMap<u32, Texels>) -> Option<Vec<Part<'a>>> {
    let parts = source(m)?
        .primitives
        .iter()
        .map(|p| Part {
            vertices: &p.vertices,
            indices: &p.indices,
            picture: p.material.base_color_image.and_then(|i| pictures.get(&i)),
            base_color: p.material.base_color,
            cut: p.material.alpha_cutoff,
            double_sided: p.material.double_sided,
        })
        .collect();
    Some(parts)
}

/// The card of a model drawn from `parts` (cut-out growth if `foliage`); `None` for one too small
/// or flat to draw.
#[allow(clippy::too_many_lines)] // one drawing of every view
pub fn bake_parts(parts: &[Part<'_>], foliage: bool) -> Option<Card> {
    let (half, foot, top) = extent(parts)?;
    let height = top - foot;
    #[allow(clippy::cast_precision_loss)] // tile sizes
    let tile_h = blocks(height * TEXELS_A_METRE).clamp(LEAST_TILE, MOST_TILE);
    #[allow(clippy::cast_precision_loss)]
    let tile_w = blocks(tile_h as f32 * 2.0 * half / height).clamp(16, 2 * MOST_TILE);
    let (count, columns) = (VIEWS.count, VIEWS.columns);
    let rows = count.div_ceil(columns);
    #[allow(clippy::cast_possible_truncation)] // a byte's 256 values
    let linear: [f32; 256] = std::array::from_fn(|v| linear(v as u8));
    let (sw, sh) = (tile_w * SUPERSAMPLE, tile_h * SUPERSAMPLE);
    let (width, height_px) = (sw * columns, sh * rows);
    let texels = (width * height_px) as usize;
    let mut drawn = Drawn {
        depth: vec![f32::INFINITY; texels],
        colour: vec![[0.0; 3]; texels],
        normal: vec![[0.0, 0.0, 1.0]; texels],
        leaf: vec![false; texels],
    };
    for k in 0..count {
        let (toward, across) = bearing(k);
        let (ox, oy) = ((k % columns) * sw, (k / columns) * sh);
        #[allow(clippy::cast_precision_loss)]
        let (fw, fh) = (sw as f32, sh as f32);
        for p in parts {
            let picture = p.picture;
            let cut = p.cut;
            let verts = p.vertices.as_chunks::<VERTEX_FLOATS>().0;
            // Each vertex on the view's tile: across, down from the top, and how far along the
            // view from the plane through the axis.
            let placed: Vec<[f32; 3]> = verts
                .iter()
                .map(|v| {
                    [
                        (v[0] * across[0] + v[1] * across[1]) / half * 0.5 * fw + 0.5 * fw,
                        (top - v[2]) / height * fh,
                        -(v[0] * toward[0] + v[1] * toward[1]),
                    ]
                })
                .collect();
            for tri in p.indices.as_chunks::<3>().0 {
                let [a, b, c] = tri.map(|i| i as usize);
                let (Some(pa), Some(pb), Some(pc)) = (placed.get(a), placed.get(b), placed.get(c))
                else {
                    continue;
                };
                let area = (pb[0] - pa[0]) * (pc[1] - pa[1]) - (pc[0] - pa[0]) * (pb[1] - pa[1]);
                if area.abs() < 1e-9 {
                    continue;
                }
                #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
                let span = |lo: f32, hi: f32, most: u32| {
                    (
                        lo.floor().max(0.0) as u32,
                        (hi.ceil().max(0.0) as u32).min(most),
                    )
                };
                let (x0, x1) = span(pa[0].min(pb[0]).min(pc[0]), pa[0].max(pb[0]).max(pc[0]), sw);
                let (y0, y1) = span(pa[1].min(pb[1]).min(pc[1]), pa[1].max(pb[1]).max(pc[1]), sh);
                for y in y0..y1 {
                    for x in x0..x1 {
                        #[allow(clippy::cast_precision_loss)]
                        let (px, py) = (x as f32 + 0.5, y as f32 + 0.5);
                        let w0 = ((pb[0] - px) * (pc[1] - py) - (pc[0] - px) * (pb[1] - py)) / area;
                        let w1 = ((pc[0] - px) * (pa[1] - py) - (pa[0] - px) * (pc[1] - py)) / area;
                        let w2 = 1.0 - w0 - w1;
                        if w0 < 0.0 || w1 < 0.0 || w2 < 0.0 {
                            continue;
                        }
                        let s = w0 * pa[2] + w1 * pb[2] + w2 * pc[2];
                        let i = ((oy + y) * width + ox + x) as usize;
                        if s >= drawn.depth[i] {
                            continue;
                        }
                        let mix = |o: usize, n: usize| -> [f32; 4] {
                            let mut out = [0.0; 4];
                            for (j, slot) in out.iter_mut().enumerate().take(n) {
                                *slot = w0 * verts[a][o + j]
                                    + w1 * verts[b][o + j]
                                    + w2 * verts[c][o + j];
                            }
                            out
                        };
                        let uv = mix(10, 2);
                        let tint = mix(12, 4);
                        let texel = picture.map_or([255; 4], |t| t.at([uv[0], uv[1]]));
                        let alpha = f32::from(texel[3]) / 255.0 * p.base_color[3] * tint[3];
                        if cut.is_some_and(|c| alpha < c) {
                            continue;
                        }
                        let n = mix(3, 3);
                        let mut n = normalised([n[0], n[1], n[2]]);
                        // A two-sided face seen from behind faces the eye; a leaf keeps its plant's.
                        if !foliage && p.double_sided && n[0] * toward[0] + n[1] * toward[1] < 0.0 {
                            n = n.map(|c| -c);
                        }
                        drawn.depth[i] = s;
                        drawn.colour[i] = [0, 1, 2].map(|c| {
                            linear[usize::from(texel[c])]
                                * p.base_color[c]
                                * tint[c].clamp(0.0, 1.0)
                        });
                        drawn.normal[i] = n;
                        drawn.leaf[i] = foliage || cut.is_some();
                    }
                }
            }
        }
    }
    shade_hidden(&mut drawn, (sw, sh), width, half);
    let (colour, normal) = pictures_of(&drawn, width, height_px, half);
    let shrunk = |rgba: Vec<u8>, srgb: bool| {
        let mut made = images::with_view_levels(width, height_px, rgba, srgb);
        made.levels.remove(0);
        made.width = width / SUPERSAMPLE;
        made.height = height_px / SUPERSAMPLE;
        images::compressed(made, images::BlockFormat::Bc7)
    };
    let colour = shrunk(colour, true);
    let normal = shrunk(normal, false);
    Some(Card { colour, normal })
}

/// Each view's bearing round the axis: the way it looks along, and the way across it.
fn bearing(k: u32) -> ([f32; 2], [f32; 2]) {
    #[allow(clippy::cast_precision_loss)] // a handful of views
    let theta = TAU * k as f32 / VIEWS.count as f32;
    let (sin, cos) = (math::sinf(theta), math::cosf(theta));
    ([cos, sin], [-sin, cos])
}

/// `drawn`'s colour darkened by how few of the views see each texel: a needle deep in its crown
/// is shaded by the rest of it, as the model's own shadows and occlusion shade it.
fn shade_hidden(drawn: &mut Drawn, tile: (u32, u32), width: u32, half: f32) {
    let (sw, sh) = tile;
    let (count, columns) = (VIEWS.count, VIEWS.columns);
    let ways: Vec<([f32; 2], [f32; 2])> = (0..count).map(bearing).collect();
    #[allow(clippy::cast_precision_loss)] // tile sizes
    let (fw, views) = (sw as f32, count as f32);
    // A texel nearer than another view's surface by less than this is the surface it sees.
    let slack = 3.0 * 2.0 * half / fw;
    let at = |k: u32, x: u32, y: u32| {
        (((k / columns) * sh + y) * width + (k % columns) * sw + x) as usize
    };
    let mut kept = vec![1.0f32; drawn.depth.len()];
    for (k, (toward, across)) in (0..count).zip(&ways) {
        for y in 0..sh {
            for x in 0..sw {
                let s = drawn.depth[at(k, x, y)];
                if !s.is_finite() {
                    continue;
                }
                #[allow(clippy::cast_precision_loss)]
                let a = ((x as f32 + 0.5) / fw - 0.5) * 2.0 * half;
                let p = [across[0] * a - toward[0] * s, across[1] * a - toward[1] * s];
                let i = at(k, x, y);
                let (leaf, n) = (drawn.leaf[i], drawn.normal[i]);
                // A solid surface is seen only from in front of it; a leaf from either side.
                let seen = (0..count)
                    .zip(&ways)
                    .filter(|(j, (t, c))| {
                        if !leaf && n[0] * t[0] + n[1] * t[1] < -0.05 {
                            return false;
                        }
                        let xj = (p[0] * c[0] + p[1] * c[1]) / half * 0.5 * fw + 0.5 * fw;
                        #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
                        let xj = (xj.max(0.0) as u32).min(sw - 1);
                        -(p[0] * t[0] + p[1] * t[1]) <= drawn.depth[at(*j, xj, y)] + slack
                    })
                    .count();
                let share = if leaf {
                    LEAF_OPEN_SHARE
                } else {
                    SOLID_OPEN_SHARE
                };
                #[allow(clippy::cast_precision_loss)]
                let open = (seen as f32 / views / share).min(1.0);
                kept[i] = HIDDEN_KEPT + (1.0 - HIDDEN_KEPT) * open;
            }
        }
    }
    for (c, k) in drawn.colour.iter_mut().zip(kept) {
        *c = c.map(|v| v * k);
    }
}

/// The colour picture (coverage in alpha) and normal picture (depth in alpha) of `drawn`, the
/// colour and normal carried a little way into the empty texels so their edges filter cleanly.
fn pictures_of(drawn: &Drawn, width: u32, height: u32, half: f32) -> (Vec<u8>, Vec<u8>) {
    let n = (width * height) as usize;
    let mut filled: Vec<bool> = drawn.depth.iter().map(|d| d.is_finite()).collect();
    let mut colour = drawn.colour.clone();
    let mut normal = drawn.normal.clone();
    for _ in 0..BLEED * SUPERSAMPLE {
        let was = filled.clone();
        for y in 0..height {
            for x in 0..width {
                let i = (y * width + x) as usize;
                if was[i] {
                    continue;
                }
                let (mut c, mut nn, mut k) = ([0.0f32; 3], [0.0f32; 3], 0.0f32);
                for (dx, dy) in [(-1i32, 0i32), (1, 0), (0, -1), (0, 1)] {
                    let (qx, qy) = (x.cast_signed() + dx, y.cast_signed() + dy);
                    if qx < 0 || qy < 0 || qx >= width.cast_signed() || qy >= height.cast_signed() {
                        continue;
                    }
                    let j = (qy.cast_unsigned() * width + qx.cast_unsigned()) as usize;
                    if was[j] {
                        for e in 0..3 {
                            c[e] += colour[j][e];
                            nn[e] += normal[j][e];
                        }
                        k += 1.0;
                    }
                }
                if k > 0.0 {
                    colour[i] = c.map(|v| v / k);
                    normal[i] = normalised(nn);
                    filled[i] = true;
                }
            }
        }
    }
    let mut c_out = Vec::with_capacity(n * 4);
    let mut n_out = Vec::with_capacity(n * 4);
    for i in 0..n {
        let covered = drawn.depth[i].is_finite();
        c_out.extend(colour[i].map(srgb));
        c_out.push(if covered { 255 } else { 0 });
        n_out.extend(normal[i].map(|v| unit_byte(v * 0.5 + 0.5)));
        n_out.push(if covered {
            unit_byte(0.5 + drawn.depth[i] / (2.0 * half))
        } else {
            255
        });
    }
    (c_out, n_out)
}

fn normalised(v: [f32; 3]) -> [f32; 3] {
    let l = (v[0] * v[0] + v[1] * v[1] + v[2] * v[2]).sqrt();
    if l > 1e-6 {
        v.map(|c| c / l)
    } else {
        [0.0, 0.0, 1.0]
    }
}

fn linear(v: u8) -> f32 {
    let c = f32::from(v) / 255.0;
    if c <= 0.04045 {
        c / 12.92
    } else {
        math::powf((c + 0.055) / 1.055, 2.4)
    }
}

fn srgb(linear: f32) -> u8 {
    let c = linear.clamp(0.0, 1.0);
    let s = if c <= 0.003_130_8 {
        c * 12.92
    } else {
        1.055 * math::powf(c, 1.0 / 2.4) - 0.055
    };
    unit_byte(s)
}

fn unit_byte(v: f32) -> u8 {
    #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)] // clamped to 0..255
    let b = (v.clamp(0.0, 1.0) * 255.0).round() as u8;
    b
}

