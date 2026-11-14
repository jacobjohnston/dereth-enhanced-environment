//! Block compression for pictures made at run time: BC4 (one channel), BC5 (two) and BC7 (four),
//! each block four by four texels, and the decoding of what it writes.
//!
//! A picture compressed so takes a quarter of the memory of eight bits a channel (BC7, BC5) or an
//! eighth (BC4), and the device samples it as it samples the uncompressed picture. The encoders
//! work on the bytes as they are stored, so a colour picture is compressed in the display's
//! encoding and decodes back to it.
//!
//! - **BC4** keeps red: two end values and an index of three bits a texel into the eight values
//!   between them.
//! - **BC5** keeps red and green, a BC4 block each.
//! - **BC7** keeps all four channels in one of two of its modes, a block at a time: mode 5 where it
//!   comes nearer with no texel further off, else mode 6. Mode 6 puts them on one line: two end
//!   colours of seven bits a channel and one shared low bit each, and an index of four bits a texel
//!   into the sixteen colours between them. Mode 5 puts colour on one line with seven-bit ends and
//!   alpha on its own with whole-byte ends, two bits a texel each, so a flat colour and opaque
//!   alpha come back exactly. The decoder reads those two modes.
//!
//! A picture whose sides are not whole blocks is compressed as if its last row and column were
//! repeated out to the block's edge; the decoder returns the picture's own texels only.

/// One of the block formats.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum BlockFormat {
    /// Red alone, eight bytes a block. A pack makes none, but its records name the format.
    #[allow(dead_code)]
    Bc4,
    /// Red and green, sixteen bytes a block.
    Bc5,
    /// All four channels, sixteen bytes a block.
    Bc7,
}

impl BlockFormat {
    /// The bytes of one block.
    #[must_use]
    pub const fn block_bytes(self) -> usize {
        match self {
            Self::Bc4 => 8,
            Self::Bc5 | Self::Bc7 => 16,
        }
    }

    /// The bytes of a `width` by `height` picture in this format.
    #[must_use]
    pub fn len(self, width: u32, height: u32) -> usize {
        blocks(width) * blocks(height) * self.block_bytes()
    }
}

/// The blocks across `texels`.
fn blocks(texels: u32) -> usize {
    (texels.max(1) as usize).div_ceil(4)
}

/// The sixteen texels of the block at `(bx, by)`, four bytes each, rows top first, clamped to
/// the picture's edge.
fn gather(rgba: &[u8], width: usize, height: usize, bx: usize, by: usize) -> [[u8; 4]; 16] {
    let mut out = [[0u8; 4]; 16];
    for (k, t) in out.iter_mut().enumerate() {
        let x = (bx * 4 + k % 4).min(width - 1);
        let y = (by * 4 + k / 4).min(height - 1);
        let i = (y * width + x) * 4;
        t.copy_from_slice(&rgba[i..i + 4]);
    }
    out
}

/// The most threads one picture's encode is spread across, the calling thread included.
const MAX_THREADS: usize = 16;
/// The fewest block rows a thread is given.
const MIN_ROWS: usize = 16;

fn threads() -> usize {
    std::thread::available_parallelism()
        .map_or(1, std::num::NonZeroUsize::get)
        .min(MAX_THREADS)
}

/// Run `f(first_row, band)` over the block rows of `out` (`row_bytes` a row), in bands on
/// several threads when there are rows enough. Each band is its own slice, so the bytes are
/// those one thread writes.
fn par_rows(out: &mut [u8], row_bytes: usize, f: &(dyn Fn(usize, &mut [u8]) + Sync)) {
    let rows = out.len() / row_bytes.max(1);
    let bands = threads().min(rows / MIN_ROWS).max(1);
    if bands == 1 {
        f(0, out);
        return;
    }
    let per = rows.div_ceil(bands);
    std::thread::scope(|scope| {
        let mut chunks = out.chunks_mut(per * row_bytes).enumerate();
        let first = chunks.next();
        for (t, band) in chunks {
            scope.spawn(move || f(t * per, band));
        }
        if let Some((_, band)) = first {
            f(0, band);
        }
    });
}

/// `rgba` (`width` by `height`, four bytes a texel) compressed to `format`: BC4 from red, BC5
/// from red and green, BC7 from all four. Blocks run row by row from the top.
///
/// # Panics
/// `rgba` is shorter than `width * height * 4`.
#[must_use]
pub fn encode(format: BlockFormat, width: u32, height: u32, rgba: &[u8]) -> Vec<u8> {
    let (w, h) = (width.max(1) as usize, height.max(1) as usize);
    assert!(
        rgba.len() >= w * h * 4,
        "a picture of {w}x{h} needs {} bytes",
        w * h * 4
    );
    let bw = blocks(width);
    let size = format.block_bytes();
    let mut out = vec![0u8; format.len(width, height)];
    par_rows(&mut out, bw * size, &|first, band| {
        for (r, row) in band.chunks_mut(bw * size).enumerate() {
            let by = first + r;
            for (bx, block) in row.chunks_mut(size).enumerate() {
                let texels = gather(rgba, w, h, bx, by);
                match format {
                    BlockFormat::Bc4 => block.copy_from_slice(&bc4_block(&texels.map(|t| t[0]))),
                    BlockFormat::Bc5 => {
                        block[..8].copy_from_slice(&bc4_block(&texels.map(|t| t[0])));
                        block[8..].copy_from_slice(&bc4_block(&texels.map(|t| t[1])));
                    }
                    BlockFormat::Bc7 => block.copy_from_slice(&bc7_block(&texels)),
                }
            }
        }
    });
    out
}

/// `blocks` (as [`encode`] wrote them) back to four bytes a texel, `width` by `height`: BC4 as
/// red with green and blue nought and alpha whole, BC5 as red and green with blue nought and
/// alpha whole, BC7 as written.
///
/// # Panics
/// `blocks` is shorter than [`BlockFormat::len`].
#[must_use]
pub fn decode(format: BlockFormat, width: u32, height: u32, blocks_in: &[u8]) -> Vec<u8> {
    let (w, h) = (width.max(1) as usize, height.max(1) as usize);
    let bw = blocks(width);
    let size = format.block_bytes();
    assert!(
        blocks_in.len() >= format.len(width, height),
        "{format:?} {w}x{h} needs {} bytes",
        format.len(width, height)
    );
    let mut out = vec![0u8; w * h * 4];
    for y in 0..h {
        for x in 0..w {
            let at = ((y / 4) * bw + x / 4) * size;
            let block = &blocks_in[at..at + size];
            let k = (y % 4) * 4 + x % 4;
            let t = match format {
                BlockFormat::Bc4 => [bc4_texel(block, k), 0, 0, 255],
                BlockFormat::Bc5 => [bc4_texel(&block[..8], k), bc4_texel(&block[8..], k), 0, 255],
                BlockFormat::Bc7 => bc7_texel(block, k),
            };
            out[(y * w + x) * 4..(y * w + x) * 4 + 4].copy_from_slice(&t);
        }
    }
    out
}

// --- BC4 ------------------------------------------------------------------------------------

/// The eight values of a BC4 block with end values `a` > `b`, as the device reads them, in
/// eighths of a level: `a`, `b`, then six steps from `a` toward `b`.
fn bc4_palette(a: u8, b: u8) -> [f32; 8] {
    let (a, b) = (f32::from(a), f32::from(b));
    let mut p = [a, b, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0];
    for (k, v) in p.iter_mut().enumerate().skip(2) {
        // LINT-OK: k is 2..8.
        #[allow(clippy::cast_precision_loss)]
        let j = (k - 1) as f32;
        *v = (a * (7.0 - j) + b * j) / 7.0;
    }
    p
}

/// The value texel `k` of a BC4 block reads as, rounded to a byte.
fn bc4_texel(block: &[u8], k: usize) -> u8 {
    let (a, b) = (block[0], block[1]);
    let bits = u64::from_le_bytes([
        block[2], block[3], block[4], block[5], block[6], block[7], 0, 0,
    ]);
    // LINT-OK: three bits.
    #[allow(clippy::cast_possible_truncation)]
    let i = ((bits >> (3 * k)) & 7) as usize;
    let v = if a > b {
        bc4_palette(a, b)[i]
    } else {
        // The six-value form: six steps between, then nought and whole.
        let (fa, fb) = (f32::from(a), f32::from(b));
        // LINT-OK: i is 0..8.
        #[allow(clippy::cast_precision_loss)]
        let j = i as f32;
        match i {
            0 => fa,
            1 => fb,
            6 => 0.0,
            7 => 255.0,
            _ => (fa * (6.0 - j) + fb * (j - 1.0)) / 5.0,
        }
    };
    to_byte(v)
}

fn to_byte(v: f32) -> u8 {
    // LINT-OK: a value clamped to 0..255 and rounded.
    #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
    let b = (v.clamp(0.0, 255.0) + 0.5) as u8;
    b
}

/// The nearest of `palette` to each of `values`, and the squared error.
fn bc4_fit(values: &[u8; 16], palette: &[f32; 8]) -> ([u8; 16], f32) {
    let mut idx = [0u8; 16];
    let mut err = 0.0;
    for (i, v) in values.iter().enumerate() {
        let v = f32::from(*v);
        let (mut best, mut best_d) = (0u8, f32::INFINITY);
        for (k, p) in (0u8..).zip(palette) {
            let d = (p - v) * (p - v);
            if d < best_d {
                (best, best_d) = (k, d);
            }
        }
        idx[i] = best;
        err += best_d;
    }
    (idx, err)
}

/// The share of the second end value in each of a BC4 block's eight values.
const BC4_SHARE: [f32; 8] = [
    0.0,
    1.0,
    1.0 / 7.0,
    2.0 / 7.0,
    3.0 / 7.0,
    4.0 / 7.0,
    5.0 / 7.0,
    6.0 / 7.0,
];

/// One BC4 block of `values`: end values the extremes, then fitted to the indices they give by
/// least squares, the best kept.
fn bc4_block(values: &[u8; 16]) -> [u8; 8] {
    let hi = *values.iter().max().unwrap_or(&0);
    let lo = *values.iter().min().unwrap_or(&0);
    if hi == lo {
        // One value: both ends it, every index the first.
        return [hi, lo, 0, 0, 0, 0, 0, 0];
    }
    let (mut a, mut b) = (hi, lo);
    let (mut idx, mut err) = bc4_fit(values, &bc4_palette(a, b));
    for _ in 0..2 {
        // The end values that best fit these indices.
        let (mut s00, mut s01, mut s11, mut r0, mut r1) = (0.0f32, 0.0, 0.0, 0.0, 0.0);
        for (v, i) in values.iter().zip(idx) {
            let t = BC4_SHARE[usize::from(i)];
            let v = f32::from(*v);
            s00 += (1.0 - t) * (1.0 - t);
            s01 += t * (1.0 - t);
            s11 += t * t;
            r0 += (1.0 - t) * v;
            r1 += t * v;
        }
        let det = s00 * s11 - s01 * s01;
        if det.abs() < 1e-6 {
            break;
        }
        let na = to_byte((s11 * r0 - s01 * r1) / det);
        let nb = to_byte((s00 * r1 - s01 * r0) / det);
        let (na, nb) = match na.cmp(&nb) {
            std::cmp::Ordering::Greater => (na, nb),
            std::cmp::Ordering::Less => (nb, na),
            std::cmp::Ordering::Equal => break,
        };
        let (ni, ne) = bc4_fit(values, &bc4_palette(na, nb));
        if ne >= err {
            break;
        }
        (a, b, idx, err) = (na, nb, ni, ne);
    }
    let mut bits = 0u64;
    for (k, i) in idx.iter().enumerate() {
        bits |= u64::from(*i) << (3 * k);
    }
    let i = bits.to_le_bytes();
    [a, b, i[0], i[1], i[2], i[3], i[4], i[5]]
}

// --- BC7 mode 6 ---------------------------------------------------------------------------------

/// The sixteen weights of a four-bit index, in sixty-fourths of the second end colour.
const BC7_WEIGHTS: [u32; 16] = [0, 4, 9, 13, 17, 21, 26, 30, 34, 38, 43, 47, 51, 55, 60, 64];

/// Channel `c` of the colour between `a` and `b` at weight `w` sixty-fourths, as the device
/// reads it.
fn bc7_mix(a: u8, b: u8, w: u32) -> u8 {
    let v = ((64 - w) * u32::from(a) + w * u32::from(b) + 32) >> 6;
    // LINT-OK: a weighted mean of two bytes.
    #[allow(clippy::cast_possible_truncation)]
    let v = v as u8;
    v
}

/// The sixteen colours between `a` and `b`.
fn bc7_palette(a: [u8; 4], b: [u8; 4]) -> [[u8; 4]; 16] {
    BC7_WEIGHTS.map(|w| [0, 1, 2, 3].map(|c| bc7_mix(a[c], b[c], w)))
}

/// Each texel's index into the colours between `a` and `b`, by where it falls along the line
/// between them (the colours all lie on it), and the squared error.
fn bc7_fit(texels: &[[u8; 4]; 16], a: [u8; 4], b: [u8; 4]) -> ([u8; 16], u32) {
    let palette = bc7_palette(a, b);
    let d: [f32; 4] = [0, 1, 2, 3].map(|c| f32::from(b[c]) - f32::from(a[c]));
    let dd: f32 = d.iter().map(|v| v * v).sum();
    let mut idx = [0u8; 16];
    let mut err = 0u32;
    for (k, t) in texels.iter().enumerate() {
        let i = if dd < 1e-6 {
            0
        } else {
            let along: f32 = (0..4)
                .map(|c| (f32::from(t[c]) - f32::from(a[c])) * d[c])
                .sum::<f32>()
                / dd;
            // LINT-OK: a share clamped to 0..1, scaled to sixty-fourths.
            #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
            let w = (along.clamp(0.0, 1.0) * 64.0) as u32;
            // The nearest weight, and its neighbour above when that is nearer in colour.
            let near = BC7_WEIGHTS.partition_point(|x| *x < w).min(15);
            let below = near.saturating_sub(1);
            let sq = |p: &[u8; 4]| -> u32 {
                (0..4)
                    .map(|c| {
                        let e = i32::from(p[c]) - i32::from(t[c]);
                        e.unsigned_abs() * e.unsigned_abs()
                    })
                    .sum()
            };
            if sq(&palette[below]) <= sq(&palette[near]) {
                below
            } else {
                near
            }
        };
        let e: u32 = (0..4)
            .map(|c| {
                let e = i32::from(palette[i][c]) - i32::from(t[c]);
                e.unsigned_abs() * e.unsigned_abs()
            })
            .sum();
        err += e;
        // LINT-OK: an index of sixteen.
        #[allow(clippy::cast_possible_truncation)]
        {
            idx[k] = i as u8;
        }
    }
    (idx, err)
}

/// `v` as seven bits and the low bit `p`: the nearest byte whose low bit is `p`.
fn with_low_bit(v: f32, p: u8) -> u8 {
    let q = ((v - f32::from(p)) / 2.0).round().clamp(0.0, 127.0);
    // LINT-OK: seven bits.
    #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
    let q = q as u8;
    q * 2 + p
}

/// `v` as a byte of each channel sharing one low bit: whichever low bit lands nearer.
fn shared_low_bit(v: [f32; 4]) -> [u8; 4] {
    let take = |p: u8| v.map(|c| with_low_bit(c, p));
    let off = |q: [u8; 4]| -> f32 { (0..4).map(|c| (f32::from(q[c]) - v[c]).powi(2)).sum() };
    let (even, odd) = (take(0), take(1));
    if off(even) <= off(odd) {
        even
    } else {
        odd
    }
}

/// The end colours `a` and `b` taken to bytes with a shared low bit each, and fitted: the end
/// colours, the indices and the squared error.
fn bc7_quantised(
    texels: &[[u8; 4]; 16],
    a: [f32; 4],
    b: [f32; 4],
) -> ([u8; 4], [u8; 4], [u8; 16], u32) {
    let (qa, qb) = (shared_low_bit(a), shared_low_bit(b));
    let (idx, err) = bc7_fit(texels, qa, qb);
    (qa, qb, idx, err)
}

/// The end values of `N` channels along the line the texels spread along most, from the
/// furthest texel each way.
fn principal_ends<const N: usize>(px: &[[f32; N]; 16]) -> ([f32; N], [f32; N]) {
    let mut mean = [0.0f32; N];
    for p in px {
        for c in 0..N {
            mean[c] += p[c] / 16.0;
        }
    }
    // The texels' spread, and the direction of most of it (by repeated multiplication).
    let mut cov = [[0.0f32; N]; N];
    for p in px {
        for i in 0..N {
            for j in 0..N {
                cov[i][j] += (p[i] - mean[i]) * (p[j] - mean[j]);
            }
        }
    }
    let mut axis = [0.0f32; N];
    // Start from the channel that varies most.
    let widest = (0..N)
        .max_by(|x, y| cov[*x][*x].total_cmp(&cov[*y][*y]))
        .unwrap_or(0);
    axis[widest] = 1.0;
    for _ in 0..8 {
        let mut next = [0.0f32; N];
        for i in 0..N {
            next[i] = (0..N).map(|j| cov[i][j] * axis[j]).sum();
        }
        let len = next.iter().map(|v| v * v).sum::<f32>().sqrt();
        if len < 1e-6 {
            break;
        }
        axis = next.map(|v| v / len);
    }
    let along = |p: &[f32; N]| -> f32 { (0..N).map(|c| (p[c] - mean[c]) * axis[c]).sum() };
    let lo = px.iter().map(along).fold(f32::INFINITY, f32::min);
    let hi = px.iter().map(along).fold(f32::NEG_INFINITY, f32::max);
    let end =
        |t: f32| -> [f32; N] { std::array::from_fn(|c| (mean[c] + axis[c] * t).clamp(0.0, 255.0)) };
    (end(lo), end(hi))
}

/// The end values that best fit these indices into `weights` (sixty-fourths) by least squares;
/// none where every texel has the same weight.
fn fitted_ends<const N: usize>(
    px: &[[f32; N]; 16],
    idx: &[u8; 16],
    weights: &[u32],
) -> Option<([f32; N], [f32; N])> {
    let (mut s00, mut s01, mut s11) = (0.0f32, 0.0, 0.0);
    let (mut r0, mut r1) = ([0.0f32; N], [0.0f32; N]);
    for (p, i) in px.iter().zip(idx) {
        // LINT-OK: sixty-fourths.
        #[allow(clippy::cast_precision_loss)]
        let t = weights[usize::from(*i)] as f32 / 64.0;
        s00 += (1.0 - t) * (1.0 - t);
        s01 += t * (1.0 - t);
        s11 += t * t;
        for c in 0..N {
            r0[c] += (1.0 - t) * p[c];
            r1[c] += t * p[c];
        }
    }
    let det = s00 * s11 - s01 * s01;
    if det.abs() < 1e-6 {
        return None;
    }
    let na = std::array::from_fn(|c| ((s11 * r0[c] - s01 * r1[c]) / det).clamp(0.0, 255.0));
    let nb = std::array::from_fn(|c| ((s00 * r1[c] - s01 * r0[c]) / det).clamp(0.0, 255.0));
    Some((na, nb))
}

/// One BC7 block of `texels` in mode 6: the end colours from the line the texels spread along
/// most, then fitted to the indices they give by least squares, the best kept; and its squared
/// error.
fn bc7_mode6(texels: &[[u8; 4]; 16]) -> ([u8; 16], u32) {
    let px: [[f32; 4]; 16] = texels.map(|t| t.map(f32::from));
    let (lo, hi) = principal_ends(&px);
    let (mut a, mut b, mut idx, mut err) = bc7_quantised(texels, lo, hi);
    for _ in 0..2 {
        if err == 0 {
            break;
        }
        let Some((na, nb)) = fitted_ends(&px, &idx, &BC7_WEIGHTS) else {
            break;
        };
        let (qa, qb, qi, qe) = bc7_quantised(texels, na, nb);
        if qe >= err {
            break;
        }
        (a, b, idx, err) = (qa, qb, qi, qe);
    }
    // The first texel's index is written with three bits: its top bit must be clear, so the end
    // colours swap round where it is not.
    if idx[0] >= 8 {
        std::mem::swap(&mut a, &mut b);
        idx = idx.map(|i| 15 - i);
    }
    let mut bits: u128 = 1 << 6;
    let mut at = 7;
    let mut put = |v: u128, n: u32| {
        bits |= v << at;
        at += n;
    };
    for c in 0..4 {
        put(u128::from(a[c] >> 1), 7);
        put(u128::from(b[c] >> 1), 7);
    }
    put(u128::from(a[0] & 1), 1);
    put(u128::from(b[0] & 1), 1);
    for (k, i) in idx.iter().enumerate() {
        put(u128::from(*i), if k == 0 { 3 } else { 4 });
    }
    (bits.to_le_bytes(), err)
}

// --- BC7 mode 5 ---------------------------------------------------------------------------------

/// The four weights of a two-bit index, in sixty-fourths of the second end value.
const BC7_WEIGHTS2: [u32; 4] = [0, 21, 43, 64];

/// A seven-bit colour end value as the device widens it to a byte.
fn widen7(v: u8) -> u8 {
    v << 1 | v >> 6
}

/// The seven-bit value whose widened byte lands nearest `v`.
fn nearest7(v: f32) -> u8 {
    // LINT-OK: a value clamped to seven bits.
    #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
    let q = (v * 127.0 / 255.0).round().clamp(0.0, 127.0) as u8;
    let off = |x: u8| (f32::from(widen7(x)) - v).abs();
    [q.saturating_sub(1), q, (q + 1).min(127)]
        .into_iter()
        .min_by(|x, y| off(*x).total_cmp(&off(*y)))
        .unwrap_or(q)
}

/// Seven-bit end values whose colour a third of the way along is `c`: every byte has a pair
/// within two steps of half of it.
fn single7(c: u8) -> (u8, u8) {
    let h = c >> 1;
    let near = h.saturating_sub(2)..=(h + 2).min(127);
    let mut best = (h, h, u8::MAX);
    for a in near.clone() {
        for b in near.clone() {
            let e = bc7_mix(widen7(a), widen7(b), BC7_WEIGHTS2[1]).abs_diff(c);
            if e < best.2 {
                best = (a, b, e);
            }
        }
    }
    (best.0, best.1)
}

/// Each texel's nearest of the four values between `a` and `b`, and the squared error.
fn fit2<const N: usize>(texels: &[[u8; N]; 16], a: [u8; N], b: [u8; N]) -> ([u8; 16], u32) {
    let palette: [[u8; N]; 4] =
        BC7_WEIGHTS2.map(|w| std::array::from_fn(|c| bc7_mix(a[c], b[c], w)));
    let mut idx = [0u8; 16];
    let mut err = 0u32;
    for (k, t) in texels.iter().enumerate() {
        let sq =
            |p: &[u8; N]| -> u32 { (0..N).map(|c| u32::from(p[c].abs_diff(t[c])).pow(2)).sum() };
        let (i, e) = (0u8..4)
            .zip(&palette)
            .map(|(i, p)| (i, sq(p)))
            .min_by_key(|x| x.1)
            .unwrap_or((0, 0));
        idx[k] = i;
        err += e;
    }
    (idx, err)
}

/// End values `a` and `b` stored as `store` gives and read back as `read` gives, fitted, then
/// refitted by least squares while that helps: the stored ends, the indices and the squared error.
fn mode5_part<const N: usize>(
    texels: &[[u8; N]; 16],
    a: [f32; N],
    b: [f32; N],
    store: fn(f32) -> u8,
    read: fn(u8) -> u8,
) -> ([u8; N], [u8; N], [u8; 16], u32) {
    let px = texels.map(|t| t.map(f32::from));
    let take = |a: [f32; N], b: [f32; N]| {
        let (qa, qb) = (a.map(store), b.map(store));
        let (idx, err) = fit2(texels, qa.map(read), qb.map(read));
        (qa, qb, idx, err)
    };
    let mut best = take(a, b);
    for _ in 0..2 {
        if best.3 == 0 {
            break;
        }
        let Some((na, nb)) = fitted_ends(&px, &best.2, &BC7_WEIGHTS2) else {
            break;
        };
        let next = take(na, nb);
        if next.3 >= best.3 {
            break;
        }
        best = next;
    }
    best
}

/// One BC7 block of `texels` in mode 5: colour along one line with seven-bit ends, alpha apart
/// with whole-byte ends, two-bit indices each; and its squared error. A flat colour is exact.
fn bc7_mode5(texels: &[[u8; 4]; 16]) -> ([u8; 16], u32) {
    let rgb = texels.map(|t| [t[0], t[1], t[2]]);
    let alpha = texels.map(|t| [t[3]]);
    let (mut ca, mut cb, mut ci, ce) = if rgb.iter().all(|t| *t == rgb[0]) {
        let ends = rgb[0].map(single7);
        let (a, b) = (ends.map(|e| e.0), ends.map(|e| e.1));
        let (idx, err) = fit2(&rgb, a.map(widen7), b.map(widen7));
        (a, b, idx, err)
    } else {
        let (lo, hi) = principal_ends(&rgb.map(|t| t.map(f32::from)));
        mode5_part(&rgb, lo, hi, nearest7, widen7)
    };
    let lo = alpha.iter().map(|t| t[0]).min().unwrap_or(0);
    let hi = alpha.iter().map(|t| t[0]).max().unwrap_or(0);
    let (mut aa, mut ab, mut ai, ae) = mode5_part(
        &alpha,
        [f32::from(lo)],
        [f32::from(hi)],
        to_byte,
        std::convert::identity,
    );
    // Each set's first index is written with one bit: its top bit must be clear.
    if ci[0] >= 2 {
        std::mem::swap(&mut ca, &mut cb);
        ci = ci.map(|i| 3 - i);
    }
    if ai[0] >= 2 {
        std::mem::swap(&mut aa, &mut ab);
        ai = ai.map(|i| 3 - i);
    }
    let mut bits: u128 = 1 << 5;
    let mut at = 8;
    let mut put = |v: u128, n: u32| {
        bits |= v << at;
        at += n;
    };
    for c in 0..3 {
        put(u128::from(ca[c]), 7);
        put(u128::from(cb[c]), 7);
    }
    put(u128::from(aa[0]), 8);
    put(u128::from(ab[0]), 8);
    for set in [ci, ai] {
        for (k, i) in set.iter().enumerate() {
            put(u128::from(*i), if k == 0 { 1 } else { 2 });
        }
    }
    (bits.to_le_bytes(), ce + ae)
}

/// One BC7 block of `texels`: mode 6, or mode 5 where it comes nearer.
fn bc7_block(texels: &[[u8; 4]; 16]) -> [u8; 16] {
    let (six, err) = bc7_mode6(texels);
    if err == 0 {
        return six;
    }
    let (five, err5) = bc7_mode5(texels);
    if err5 < err && worst_off(&five, texels) <= worst_off(&six, texels) {
        five
    } else {
        six
    }
}

/// The largest difference of any channel between `texels` and `block` as the device reads it.
fn worst_off(block: &[u8; 16], texels: &[[u8; 4]; 16]) -> u8 {
    (0..16)
        .flat_map(|k| {
            let t = bc7_texel(block, k);
            (0..4).map(move |c| t[c].abs_diff(texels[k][c]))
        })
        .max()
        .unwrap_or(0)
}

/// Texel `k` of a BC7 block, as the device reads it; a block in a mode other than 5 or 6 reads
/// as nought.
fn bc7_texel(block: &[u8], k: usize) -> [u8; 4] {
    let mut raw = [0u8; 16];
    raw.copy_from_slice(&block[..16]);
    let bits = u128::from_le_bytes(raw);
    // LINT-OK: fields of at most eight bits.
    #[allow(clippy::cast_possible_truncation)]
    let field = |at: u32, n: u32| -> u8 { ((bits >> at) & ((1 << n) - 1)) as u8 };
    // LINT-OK: k is 0..16.
    #[allow(clippy::cast_possible_truncation)]
    let k = k as u32;
    if bits & 0x7F == 1 << 6 {
        let (pa, pb) = (field(63, 1), field(64, 1));
        let mut a = [0u8; 4];
        let mut b = [0u8; 4];
        for c in 0..4 {
            // LINT-OK: c is 0..4.
            #[allow(clippy::cast_possible_truncation)]
            let at = 7 + 14 * c as u32;
            a[c] = field(at, 7) << 1 | pa;
            b[c] = field(at + 7, 7) << 1 | pb;
        }
        let i = if k == 0 {
            field(65, 3)
        } else {
            field(68 + 4 * (k - 1), 4)
        };
        let w = BC7_WEIGHTS[usize::from(i)];
        return [0, 1, 2, 3].map(|c| bc7_mix(a[c], b[c], w));
    }
    if bits & 0x3F == 1 << 5 {
        // Two-bit indices, the first of each set one bit: colour's from 66, alpha's from 97.
        let index = |from: u32| {
            if k == 0 {
                field(from, 1)
            } else {
                field(from + 2 * k - 1, 2)
            }
        };
        let wc = BC7_WEIGHTS2[usize::from(index(66))];
        let wa = BC7_WEIGHTS2[usize::from(index(97))];
        let mut t = [0u8; 4];
        for (at, v) in (8u32..).step_by(14).zip(&mut t[..3]) {
            *v = bc7_mix(widen7(field(at, 7)), widen7(field(at + 7, 7)), wc);
        }
        t[3] = bc7_mix(field(50, 8), field(58, 8), wa);
        // The rotation swaps alpha with red, green or blue.
        match field(6, 2) {
            0 => {}
            r => t.swap(3, usize::from(r - 1)),
        }
        return t;
    }
    [0; 4]
}

