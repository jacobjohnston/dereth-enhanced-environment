//! The transcendental functions the packing uses, the same bits on every host: `pxfm`'s, correctly
//! rounded, as Pyreal's `pyreal_primitives::num::math` calls them (its default, portable build).
//!
//! A correctly rounded result does not depend on how it is computed, so it is the same whether
//! `pxfm` takes its FMA path or not. A negative base's power is computed from its magnitude, its
//! sign set here, and every NaN result is the one quiet NaN.

/// From here up every `f32` is an even integer.
const EVEN_F32: f32 = 16_777_216.0;

fn n32(r: f32) -> f32 {
    if r.is_nan() {
        f32::from_bits(0x7FC0_0000)
    } else {
        r
    }
}

pub fn sinf(x: f32) -> f32 {
    n32(pxfm::f_sinf(x))
}

pub fn cosf(x: f32) -> f32 {
    n32(pxfm::f_cosf(x))
}

pub fn powf(x: f32, y: f32) -> f32 {
    n32(if x.is_sign_negative() {
        let r = pxfm::f_powf(x.abs(), y);
        if y.trunc() == y {
            // An integer, or infinite (even).
            #[allow(clippy::cast_possible_truncation)]
            let odd = y.abs() < EVEN_F32 && (y as i32) & 1 != 0;
            if odd {
                -r
            } else {
                r
            }
        } else if x == 0.0 || x.is_infinite() {
            r
        } else {
            f32::NAN
        }
    } else {
        pxfm::f_powf(x, y)
    })
}

pub fn hypotf(x: f32, y: f32) -> f32 {
    n32(pxfm::f_hypotf(x, y))
}
