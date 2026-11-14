//! A pack's materials for retail pictures, their pictures packed for drawing: the base color in
//! BC7, unless the material keeps the retail picture, its normal in BC5 at its own size, and its
//! roughness, occlusion, height and dampness in BC7 at about half theirs ([`material`]).
//!
//! The base color is held as the retail picture is held: in the display's encoding and read as
//! stored, so the stages a retail surface is drawn with compute with it exactly as they compute
//! with the retail picture. Its smaller levels are still averaged in linear light, so it does not
//! darken with distance.

use crate::manifest::ManifestMaterial;

use super::images::{self, BlockFormat, Image};

/// A material's pictures, packed for drawing: its base color (none where it keeps the retail
/// picture), its normal and its surface.
#[derive(Debug, Clone, PartialEq)]
pub struct MaterialPictures {
    pub albedo: Option<Image>,
    pub normal: Image,
    pub surface: Image,
}

/// What a material takes where it names no picture: a flat normal, a rough surface and no
/// occlusion.
const DEFAULTS: [u8; 4] = [128, 128, 230, 255];

/// The side of a bend picture with no picture of its own, and of the surface of a material that
/// has only a base colour: one block, which the engine draws as no map.
const FLAT: u32 = 4;

/// The files of one material, as read.
pub(super) struct MaterialFiles {
    base: Option<Vec<u8>>,
    normal: Option<Vec<u8>>,
    roughness: Option<Vec<u8>>,
    occlusion: Option<Vec<u8>>,
    height: Option<Vec<u8>>,
    damp_map: Option<Vec<u8>>,
}

impl MaterialFiles {
    /// The files `entry` names, read through `read`: its base color only where it does not keep
    /// the retail picture.
    pub(super) fn read(
        entry: &ManifestMaterial,
        read: &mut dyn FnMut(&str) -> Result<Vec<u8>, String>,
    ) -> Result<Self, String> {
        let base = if entry.keep_retail_picture {
            None
        } else {
            Some(read(&entry.base_color)?)
        };
        let mut channel = |path: &Option<String>| path.as_deref().map(&mut *read).transpose();
        Ok(Self {
            base,
            normal: channel(&entry.normal)?,
            roughness: channel(&entry.roughness)?,
            occlusion: channel(&entry.occlusion)?,
            height: channel(&entry.height)?,
            damp_map: channel(&entry.damp_map)?,
        })
    }
}

/// The part a normal picture's byte `v` holds (0..255 for -1..1), times `scale`.
fn bent(v: u8, scale: f32) -> f32 {
    (f32::from(v) / 255.0 * 2.0 - 1.0) * scale
}

/// A grit picture from its file, with its levels, in BC7: its smaller levels average to no bend and
/// no speckle, so it fades with distance rather than shimmers.
pub(super) fn grit(bytes: &[u8], path: &str) -> Result<Image, String> {
    let (w, h, rgba) = images::decode_png(bytes).map_err(|e| format!("{path}: {e}"))?;
    if w == 0 || h == 0 {
        return Err(format!("{path}: an empty picture"));
    }
    let (w, h, rgba) = images::to_whole_blocks(w, h, rgba);
    Ok(images::compressed(
        images::with_levels(w, h, rgba, false, None),
        BlockFormat::Bc7,
    ))
}

/// The material `entry` from its `files`, each picture made whole blocks of four, with its levels,
/// and compressed: the base color at its own size; the normal at its own, and the surface at half
/// its pictures' (or the normal's), each no larger than the base color's (the first of the other
/// pictures' where it keeps the retail picture) and never stretched up to it. A normal with no
/// picture of its own, or a material with only a base colour, is one block.
pub(super) fn material(
    entry: &ManifestMaterial,
    files: &MaterialFiles,
) -> Result<MaterialPictures, String> {
    let picture = |bytes: &[u8], path: &str| -> Result<(u32, u32, Vec<u8>), String> {
        let (w, h, rgba) = images::decode_png(bytes).map_err(|e| format!("{path}: {e}"))?;
        if w == 0 || h == 0 {
            return Err(format!("{path}: an empty picture"));
        }
        Ok((w, h, rgba))
    };
    let sized = [
        (&files.base, Some(entry.base_color.as_str())),
        (&files.normal, entry.normal.as_deref()),
        (&files.roughness, entry.roughness.as_deref()),
        (&files.occlusion, entry.occlusion.as_deref()),
        (&files.height, entry.height.as_deref()),
    ]
    .into_iter()
    .find_map(|(bytes, path)| Some((bytes.as_ref()?, path?)));
    let (w, h, first) = match sized {
        Some((bytes, path)) => {
            let (w, h, first) = picture(bytes, path)?;
            images::to_whole_blocks(w, h, first)
        }
        // One that only says what it is made of: one block of each map.
        None if !entry.matter.is_plain() => (FLAT, FLAT, Vec::new()),
        None => return Err("keeps the retail picture and names no picture of its own".to_owned()),
    };
    let base = files.base.is_some().then_some(first);
    let channel = |bytes: &Option<Vec<u8>>,
                   path: &Option<String>|
     -> Result<Option<(u32, u32, Vec<u8>)>, String> {
        match (bytes, path) {
            (Some(bytes), Some(path)) => picture(bytes, path).map(Some),
            _ => Ok(None),
        }
    };
    // A picture's own size in whole blocks, no larger than the base color's.
    let fit = |pw: u32, ph: u32| (pw.next_multiple_of(4).min(w), ph.next_multiple_of(4).min(h));
    let normal = channel(&files.normal, &entry.normal)?.map(|(pw, ph, rgba)| {
        let (nw, nh) = fit(pw, ph);
        (nw, nh, images::stretched(pw, ph, &rgba, nw, nh))
    });
    let maps = [
        channel(&files.roughness, &entry.roughness)?,
        channel(&files.occlusion, &entry.occlusion)?,
        channel(&files.height, &entry.height)?,
        channel(&files.damp_map, &entry.damp_map)?,
    ];
    let (nw, nh) = normal.as_ref().map_or((FLAT, FLAT), |n| (n.0, n.1));
    let scale = entry.normal_scale;
    let bends: Vec<u8> = (0..(nw as usize) * (nh as usize))
        .flat_map(|i| {
            let at = |c: usize| normal.as_ref().map_or(DEFAULTS[c], |n| n.2[i * 4 + c]);
            let (x, y) = (bent(at(0), scale), bent(at(1), scale));
            // A bend past the picture's plane is held just short of it.
            let k = 0.98 / crate::math::hypotf(x, y).max(0.98);
            #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
            // LINT-OK: -1..1 brought to 0..255 and rounded.
            let byte = |v: f32| ((v * k * 0.5 + 0.5) * 255.0 + 0.5).clamp(0.0, 255.0) as u8;
            [byte(x), byte(y), 0, 255]
        })
        .collect();
    // The surface along one side, made at `full` and halved, or at its pictures' `own` size where
    // that is smaller than the half.
    let side = |full: u32, own: u32| {
        let half = (full / 2).max(1);
        if own < half {
            (own, own)
        } else {
            (full, half)
        }
    };
    let largest = maps
        .iter()
        .flatten()
        .map(|m| (m.0, m.1))
        .reduce(|a, b| (a.0.max(b.0), a.1.max(b.1)));
    let ((mw, hw), (mh, hh)) = match largest {
        Some((pw, ph)) => {
            let (ow, oh) = fit(pw, ph);
            (side(w, ow), side(h, oh))
        }
        None if normal.is_some() => (side(nw, nw), side(nh, nh)),
        None => ((FLAT, FLAT), (FLAT, FLAT)),
    };
    let [roughness, occlusion, height, damp_map] =
        maps.map(|m| m.map(|(pw, ph, rgba)| images::stretched(pw, ph, &rgba, mw, mh)));
    let at = |p: &Option<Vec<u8>>, i: usize, default: u8| p.as_ref().map_or(default, |p| p[i * 4]);
    #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
    // LINT-OK: 0..1 brought to 0..255 and rounded.
    let damp = (entry.damp * 255.0 + 0.5) as u8;
    let surface: Vec<u8> = (0..(mw as usize) * (mh as usize))
        .flat_map(|i| {
            [
                at(&roughness, i, DEFAULTS[2]),
                at(&occlusion, i, DEFAULTS[3]),
                at(&height, i, 255),
                // LINT-OK: two bytes multiplied, brought back to a byte.
                u8::try_from(u32::from(damp) * u32::from(at(&damp_map, i, 255)) / 255)
                    .unwrap_or(255),
            ]
        })
        .collect();
    let surface = images::stretched(mw, mh, &surface, hw, hh);
    let albedo = base.map(|base| Image {
        srgb: false,
        ..images::compressed(
            images::with_levels(w, h, base, true, None),
            BlockFormat::Bc7,
        )
    });
    Ok(MaterialPictures {
        albedo,
        normal: images::compressed(
            images::with_levels(nw, nh, bends, false, None),
            BlockFormat::Bc5,
        ),
        surface: images::compressed(
            images::with_levels(hw, hh, surface, false, None),
            BlockFormat::Bc7,
        ),
    })
}
