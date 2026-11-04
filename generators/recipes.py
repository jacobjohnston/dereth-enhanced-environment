# recipes.py: shapes a retail picture as the material it is. Each recipe takes the picture's evened
# brightness L, its scale px (map texels to a retail texel), and a generator, and answers its height
# (1 the surface, less sunk), how strongly that bends the light, its occlusion and its roughness.
import numpy as np
from masonry import blur, block_height, cells_of, joints_of, survey, thatch_height
def dir_blur(a, s, axis):
    h, w = a.shape
    f = np.fft.fftfreq(h)[:, None] if axis == 0 else np.fft.rfftfreq(w)[None, :]
    return np.fft.irfft2(np.fft.rfft2(a) * np.exp(-2 * (np.pi * s * f) ** 2), s=a.shape)
def grain_axis(L):
    """The axis the picture's grain runs along, and how plainly: it changes least that way."""
    gx = float(((np.roll(L, -1, 1) - np.roll(L, 1, 1)) ** 2).mean())
    gy = float(((np.roll(L, -1, 0) - np.roll(L, 1, 0)) ** 2).mean())
    return (0, gx / (gy + 1e-9)) if gx >= gy else (1, gy / (gx + 1e-9))
def unit(a):
    return a / (a.std() + 1e-6)
def crevices(hgt, spread, most=0.6):
    """Dark in what lies below the height about it."""
    return 1 - np.clip((blur(hgt, spread) - hgt) * 2.4, 0, most)
def runs_on(lines, px, least):
    """Only the lines that run on for at least `least` retail texels, straight or on a slant."""
    n = max(2, int(least * px / 2))
    a = lines.astype(np.float32)
    best = np.zeros_like(a)
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        run = sum(np.roll(a, (k * dy, k * dx), (0, 1)) for k in range(-n, n + 1)) / (2 * n + 1)
        best = np.maximum(best, run)
    return lines & (best > 0.55)
def thin_joints(L, px):
    """The narrow dark lines between pieces that run on, without the blotches beside them."""
    d = unit(blur(L, 5 * px) - blur(L, 0.6 * px))
    return runs_on((d > 1.05) & (blur((d > 1.05).astype(np.float32), 1.1 * px) > 0.34), px, 10)
def faces(L, px, rng, bevel_px, offset, detail, level, sunk=0.5):
    """Flat pieces between the joints: a piece's face its own height, with a narrow edge."""
    j = thin_joints(L, px)
    lab = cells_of(j)
    b = np.clip((blur((~j).astype(np.float32), bevel_px * px) - 0.5) / 0.42, 0, 1)
    b = b * b * (3 - 2 * b)
    n = int(lab.max()) + 2
    off = rng.uniform(-offset, offset, n).astype(np.float32)
    idx = np.where(lab >= 0, lab, n - 1)
    fine = np.clip(unit(blur(L, 0.5 * px) - blur(L, 2.4 * px)), -2.5, 2.5) * detail / 2.5
    return np.clip(level + off[idx] + fine, 0.2, 1.0) - (1 - b) * sunk, j
def masonry(L, px, rng):
    found, cover, pieces = survey(L, px)
    if found < 0.35 or pieces < 3:
        return plaster(L, px, rng) if float((L - blur(L, 8 * px)).std()) < 0.075 else rock(L, px, rng)
    h, _ = block_height(L, px, rng)
    return h, 1.2, crevices(h, 2.5 * px), 0.85
def flagstone(L, px, rng):
    if survey(L, px)[0] < 0.25:
        return rock(L, px, rng)
    # Laid flat and worn: a face stays flat, and a joint sinks as far as it is painted dark.
    d = unit(blur(L, 5 * px) - blur(L, 0.6 * px))
    joint = np.clip((d - 0.7) / 1.8, 0, 1)
    fine = np.clip(unit(blur(L, 0.5 * px) - blur(L, 2.4 * px)), -2.5, 2.5) * 0.012
    broad = np.clip(unit(blur(L, 6 * px) - blur(L, 24 * px)), -2, 2) * 0.012
    h = blur((0.94 + fine + broad - 0.38 * joint).astype(np.float32), 0.3 * px)
    return h, 1.0, crevices(h, 2 * px, 0.45), 0.8
def wood(L, px, rng):
    axis, plain = grain_axis(L)
    if plain < 1.3:
        # Laid across its picture: the seams alone tell the boards apart.
        return flagstone(L, px, rng)[0], 1.1, flagstone(L, px, rng)[2], 0.72
    other = 1 - axis
    along = dir_blur(L, 10 * px, axis)
    seam = unit(dir_blur(along, 4 * px, other) - dir_blur(along, 0.6 * px, other)) > 1.25
    # A dark streak in the grain is no seam: a seam runs on along the board.
    seam = runs_on(seam & (dir_blur(seam.astype(np.float32), 10 * px, axis) > 0.55), px, min(L.shape) / px * 0.4)
    # A board's end is a seam across the grain, kept where it runs on.
    across = dir_blur(L, 3 * px, other)
    end = unit(dir_blur(across, 4 * px, axis) - dir_blur(across, 0.6 * px, axis)) > 2.2
    end = runs_on(end, px, 6)
    j = seam | end
    lab = cells_of(j)
    b = np.clip((blur((~j).astype(np.float32), 0.9 * px) - 0.5) / 0.42, 0, 1)
    n = int(lab.max()) + 2
    off = rng.uniform(-0.05, 0.05, n).astype(np.float32)
    idx = np.where(lab >= 0, lab, n - 1)
    fine = dir_blur(L, 3 * px, axis)
    grain = unit(dir_blur(fine, 0.35 * px, other) - dir_blur(fine, 1.6 * px, other))
    h = 0.84 + off[idx] + np.clip(grain, -2.5, 2.5) * 0.022 - (1 - b) * 0.42
    return h, 1.4, crevices(h, 1.6 * px), 0.72
def roof(L, px, rng):
    h, w = L.shape
    rows = (L.mean(1) - blur(L, 8 * px).mean(1)).astype(np.float64)
    ac = np.fft.irfft(np.abs(np.fft.rfft(rows)) ** 2)
    lo, hi = max(4, int(4 * px)), max(5, h // 2)
    period = lo + int(np.argmax(ac[lo:hi + 1]))
    if ac[period] < 0.4 * ac[0] or rows.std() < 0.6 * float((L - blur(L, 8 * px)).std()):
        # Courses that do not run straight, as scales: their painted shading tells it better.
        return design(L, px, rng)
    # Each course runs down to its lower edge, proud of the next: a step, not a bevel.
    phase = np.angle((rows * np.exp(-2j * np.pi * np.arange(h) / period)).sum())
    dark = (phase + np.pi) / (2 * np.pi) * period
    frac = ((np.arange(h) - dark) / period) % 1
    course = np.repeat((0.4 + 0.58 * frac)[:, None], w, 1).astype(np.float32)
    bulge = np.clip(unit(blur(L, 1.2 * px) - blur(L, 8 * px)), -2, 2) * 0.05
    j = joints_of(L, px)
    v = dir_blur(j.astype(np.float32), 3 * px, 0) > 0.5
    made = blur((course + bulge) * np.where(v, 0.55, 1.0), 0.35 * px)
    return made, 1.3, crevices(made, 2 * px), 0.78
def thatch(L, px, rng):
    h = thatch_height(L, px)
    return h, 1.6, crevices(h, 2.5 * px) * 0.5 + 0.5, 0.9
def plaster(L, px, rng):
    # Painted light and dirt are no shape: only thin dark lines that run on are cracks.
    d = unit(blur(L, 2.5 * px) - blur(L, 0.5 * px))
    crack = runs_on(d > 1.9, px, 7)
    swell = np.clip(unit(blur(L, 10 * px) - blur(L, 30 * px)), -2, 2) * 0.015
    # Its own fine grain, as gently as the wall's trowel left it.
    fine = np.clip(unit(blur(L, 0.4 * px) - blur(L, 1.5 * px)), -2, 2) * 0.03
    h = np.clip(0.95 + swell + fine - 0.14 * blur(crack.astype(np.float32), 0.45 * px), 0, 1)
    return h, 1.1, crevices(h, 1.2 * px, 0.35), 0.92
def rock(L, px, rng):
    g = [blur(L, s * px) for s in (0.45, 1.3, 4, 12, 30)]
    hgt = 0.4 * (g[0] - g[1]) + 1.2 * (g[1] - g[2]) + 2.6 * (g[2] - g[3]) + 2.4 * (g[3] - g[4])
    lo, hi = np.percentile(hgt, [2, 98])
    q = np.clip((hgt - lo) / (hi - lo + 1e-5), 0, 1)
    h = 0.3 + 0.7 * q ** 0.8
    return blur(h.astype(np.float32), 0.35 * px), 1.5, crevices(h, 3 * px) * 0.6 + 0.4, 0.9
def metal(L, px, rng):
    d = unit(blur(L, 0.8 * px) - blur(L, 3 * px))
    rivet = blur((d > 2.2).astype(np.float32), 0.6 * px)
    j = joints_of(L, px)
    h = np.clip(0.9 + 0.1 * rivet - 0.4 * blur(j.astype(np.float32), 0.5 * px), 0, 1)
    return h, 1.1, crevices(h, 1.5 * px), np.clip(0.42 + 0.3 * (1 - L / L.max()), 0, 1)
def design(L, px, rng):
    # Its shading is painted as relief: read gently, for it was never meant to catch a raking light.
    g = [blur(L, s * px) for s in (0.45, 1.3, 4, 12)]
    hgt = 0.5 * (g[0] - g[1]) + 1.4 * (g[1] - g[2]) + 1.8 * (g[2] - g[3])
    lo, hi = np.percentile(hgt, [2, 98])
    h = 0.55 + 0.45 * np.clip((hgt - lo) / (hi - lo + 1e-5), 0, 1)
    return blur(h.astype(np.float32), 0.35 * px), 1.1, crevices(h, 2.5 * px) * 0.5 + 0.5, 0.85
def organic(L, px, rng):
    # Lobes of flesh and the pale sinews painted over them, which stand proud; soft all over.
    lobes = np.clip(unit(blur(L, 5 * px) - blur(L, 26 * px)), -2.2, 2.2)
    sinew = np.clip(unit(blur(L, 1.2 * px) - blur(L, 6 * px)), -1.6, 2.4)
    h = np.clip(0.52 + 0.17 * lobes + 0.13 * sinew, 0.05, 1)
    h = blur(h.astype(np.float32), 0.7 * px)
    return h, 1.5, crevices(h, 4 * px, 0.5), 0.4
def slime(h, px, rng):
    """Where a soft surface is wet: its hollows, in pools broken up by patches, and a film elsewhere."""
    low = np.clip((blur(h, 4 * px) - h) * 3.5 + (float(h.mean()) - blur(h, 10 * px)) * 2 + 0.5, 0, 1)
    n = blur(rng.standard_normal(h.shape).astype(np.float32), 9 * px)
    patches = np.clip(unit(n) * 0.3 + 0.7, 0, 1)
    return blur(np.clip(0.3 + 0.7 * low * patches, 0, 1).astype(np.float32), 1.2 * px)
RECIPES = dict(organic=organic, masonry=masonry, flagstone=flagstone, wood=wood, roof=roof, thatch=thatch, plaster=plaster, rock=rock, metal=metal, design=design)
def classify(L, a, px):
    """Which recipe a rectangle of a mixed picture looks to want."""
    s, cover, pieces = survey(L, px)
    if s > 0.62 and pieces >= 4 and cover > 0.08:
        return 'masonry'
    red, blue = float(a[..., 0].mean()), float(a[..., 2].mean())
    if grain_axis(L)[1] > 1.7 and float(L.std()) > 0.05 and red > blue * 1.25:
        return 'wood'
    if float((L - blur(L, 8 * px)).std()) < 0.075:
        return 'plaster'
    return 'rock'
