# recipes.py: shapes a retail picture as the material it is. Each recipe takes the picture's evened
# brightness L, its scale px (map texels to a retail texel), a generator and the lines a mixed
# picture's bands meet along (or None), and answers its height (1 the surface, less sunk), the depth
# of that height's whole range in retail texels, its occlusion and its roughness.
import numpy as np
from masonry import blur, cells_of, joints_of, survey, thatch_height
from stones import inside, labels, stones, unit
# books: what is calm (of the median), a book's widest half (texels), what is dark, how plain a
# side is, a spine's front, how far books stand out of line, their roughness, depth and how far in.
BOOK_CALM, BOOK_WIDE, BOOK_DARK, BOOK_SIDE, BOOK_FRONT, BOOK_STAGGER, BOOK_ROUGH, BOOK_DEPTH, BOOK_SINK = 0.35, 4, 0.5, 1.2, 0.82, 0.05, 0.62, 5.0, 0.6
def dir_blur(a, s, axis):
    h, w = a.shape
    f = np.fft.fftfreq(h)[:, None] if axis == 0 else np.fft.rfftfreq(w)[None, :]
    return np.fft.irfft2(np.fft.rfft2(a) * np.exp(-2 * (np.pi * s * f) ** 2), s=a.shape)
def grain_axis(L):
    """The axis the picture's grain runs along, and how plainly: it changes least that way."""
    gx = float(((np.roll(L, -1, 1) - np.roll(L, 1, 1)) ** 2).mean())
    gy = float(((np.roll(L, -1, 0) - np.roll(L, 1, 0)) ** 2).mean())
    return (0, gx / (gy + 1e-9)) if gx >= gy else (1, gy / (gx + 1e-9))
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
def size_of(L, px):
    """How much larger than a 128-texel picture's this one's features stand, in its own texels."""
    return float(np.clip(min(L.shape) / px / 128, 0.5, 4)) ** 0.75
def built(L, px, rng, edges, flat, grid=False):
    h, depth, occ, j, found, *detail = stones(L, px, rng, flat=flat, edges=edges, courses=True, grid=grid)
    if found < 0.45:
        return None
    # Mortar is rougher than the faces, and a dark face rougher than a pale one.
    r = np.clip(0.8 + 0.12 * j + 0.08 * (1 - np.clip(L / (np.percentile(L, 98) + 1e-5), 0, 1)), 0, 1)
    return (h, depth, occ, r, *detail)
def masonry(L, px, rng, edges=None):
    made = built(L, px, rng, edges, False)
    if made is None:
        return plaster(L, px, rng) if float((L - blur(L, 8 * px)).std()) < 0.075 else rock(L, px, rng)
    return made
def flagstone(L, px, rng, edges=None, grid=False):
    made = built(L, px, rng, edges, True, grid)
    return rock(L, px, rng) if made is None else made
def wood(L, px, rng, edges=None):
    axis, plain = grain_axis(L)
    other = 1 - axis
    if plain < 1.3 and edges is None:
        # Laid across its picture: the seams alone tell the boards apart, as a floor's stones.
        made = built(L, px, rng, edges, True)
        if made is not None:
            h, depth, occ, _ = made[:4]
            return h, depth * 0.7, occ, 0.72
    along = dir_blur(L, 10 * px, axis)
    seam = unit(dir_blur(along, 4 * px, other) - dir_blur(along, 0.6 * px, other)) > 1.25
    # A dark streak in the grain is no seam: a seam runs on along the board.
    seam = runs_on(seam & (dir_blur(seam.astype(np.float32), 10 * px, axis) > 0.55), px, min(L.shape) / px * 0.4)
    # A board's end is a seam across the grain, kept where it runs on.
    across = dir_blur(L, 3 * px, other)
    end = unit(dir_blur(across, 4 * px, axis) - dir_blur(across, 0.6 * px, axis)) > 2.2
    end = runs_on(end, px, 6)
    j = seam | end
    if edges is not None:
        j = j | edges
    j = blur(j.astype(np.float32), 0.5 * px) > 0.35
    lab = labels(~j)
    d = inside(~j, px)
    # Each board's edges eased round over a texel and a half, its face cupped a little.
    e = 1 - (1 - np.clip(d / (1.5 * px), 0, 1)) ** 2
    n = int(lab.max()) + 1
    r = np.ones(n, np.float32)
    if n > 1:
        from scipy import ndimage
        r = np.maximum(ndimage.maximum(d, lab, np.arange(n)).astype(np.float32), 1)
    cup = np.clip(d / r[lab], 0, 1)
    off = rng.uniform(-0.04, 0.04, n).astype(np.float32)
    fine = dir_blur(L, 3 * px, axis)
    grain = np.clip(unit(dir_blur(fine, 0.4 * px, other) - dir_blur(fine, 1.8 * px, other)), -2.5, 2.5)
    knots = np.clip(-unit(blur(L, 1.5 * px) - blur(L, 6 * px)) - 1.6, 0, 2)
    face = 0.88 + off[lab] + 0.04 * (1 - (1 - cup) ** 2) + 0.035 * grain - 0.04 * knots
    h = np.where(j, 0.4, 0.4 + (face - 0.4) * e)
    h = blur(h.astype(np.float32), 0.35 * px)
    h = np.clip(h / float(np.percentile(h, 99.5)), 0, 1)
    breadth = float(np.median(r[1:])) / px * 2 if n > 1 else 16
    depth = float(np.clip(0.1 * breadth, 1.4, 5)) * (1 if n > 1 else 0.8)
    rough = np.clip(0.7 + 0.12 * j + 0.04 * grain, 0, 1)
    return h, depth, crevices(h, 1.6 * px), rough
def roof(L, px, rng, edges=None):
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
    return made, 1.6 * size_of(L, px), crevices(made, 2 * px), 0.78
def thatch(L, px, rng, edges=None):
    h = thatch_height(L, px)
    return h, 2.0 * size_of(L, px), crevices(h, 2.5 * px) * 0.5 + 0.5, 0.9
def plaster(L, px, rng, edges=None):
    # Painted light and dirt are no shape: only thin dark lines that run on are cracks.
    d = unit(blur(L, 2.5 * px) - blur(L, 0.5 * px))
    crack = runs_on(d > 1.9, px, 7)
    swell = np.clip(unit(blur(L, 10 * px) - blur(L, 30 * px)), -2, 2) * 0.03
    # Its own fine grain, as gently as the wall's trowel left it.
    fine = np.clip(unit(blur(L, 0.4 * px) - blur(L, 1.5 * px)), -2, 2) * 0.03
    h = np.clip(0.9 + swell + fine - 0.25 * blur(crack.astype(np.float32), 0.45 * px), 0, 1)
    return h, 1.4 * size_of(L, px), crevices(h, 1.2 * px, 0.35), 0.92
def rock(L, px, rng, edges=None):
    # Big forms with hard edges between them, from the picture's broad light and shade, cut by its
    # cracks: not the cloud its every blotch would make.
    g = [blur(L, s * px) for s in (0.5, 1.5, 4, 10, 28)]
    forms = np.tanh(1.3 * unit(g[2] - g[4]))
    middle = np.tanh(1.1 * unit(g[1] - g[3]))
    fine = np.clip(unit(g[0] - g[2]), -2.5, 2.5)
    crack = blur(thin_joints(L, px).astype(np.float32), 0.6 * px)
    hgt = 0.5 * forms + 0.25 * middle + 0.05 * fine - 0.6 * crack
    lo, hi = np.percentile(hgt, [1, 99.5])
    h = np.clip((hgt - lo) / (hi - lo + 1e-5), 0, 1)
    h = blur(h.astype(np.float32), 0.35 * px)
    depth = float(np.clip(0.035 * min(L.shape) / px, 2, 14))
    return h, depth, crevices(h, 3 * px) * 0.6 + 0.4, np.clip(0.86 + 0.06 * crack - 0.03 * fine, 0, 1)
def metal(L, px, rng, edges=None):
    d = unit(blur(L, 0.8 * px) - blur(L, 3 * px))
    rivet = blur((d > 2.2).astype(np.float32), 0.6 * px)
    j = joints_of(L, px)
    h = np.clip(0.9 + 0.1 * rivet - 0.4 * blur(j.astype(np.float32), 0.5 * px), 0, 1)
    return h, 1.3 * size_of(L, px), crevices(h, 1.5 * px), np.clip(0.42 + 0.3 * (1 - L / L.max()), 0, 1)
def design(L, px, rng, edges=None):
    # Its shading is painted as relief: read gently, for it was never meant to catch a raking light.
    g = [blur(L, s * px) for s in (0.45, 1.3, 4, 12)]
    hgt = 0.5 * (g[0] - g[1]) + 1.4 * (g[1] - g[2]) + 1.8 * (g[2] - g[3])
    lo, hi = np.percentile(hgt, [2, 98])
    h = 0.55 + 0.45 * np.clip((hgt - lo) / (hi - lo + 1e-5), 0, 1)
    if edges is not None:
        # A band of trim stands out from what it meets, its edge eased.
        h = h * (0.6 + 0.4 * np.clip(inside(~edges, px) / (1.2 * px), 0, 1))
    return blur(h.astype(np.float32), 0.35 * px), 1.5 * size_of(L, px), crevices(h, 2.5 * px) * 0.5 + 0.5, 0.85
def surface(L, px, rng, edges=None):
    # A picture of no recipe: its broad shading as gentle forms, its fine detail as grain.
    g = [blur(L, s * px) for s in (0.45, 1.5, 5, 16)]
    hgt = 0.25 * unit(g[0] - g[1]) + 0.45 * np.tanh(unit(g[1] - g[2])) + 0.5 * np.tanh(unit(g[2] - g[3]))
    lo, hi = np.percentile(hgt, [1, 99.5])
    h = 0.3 + 0.7 * np.clip((hgt - lo) / (hi - lo + 1e-5), 0, 1)
    h = blur(h.astype(np.float32), 0.35 * px)
    rough = np.clip(0.78 + 0.12 * (1 - np.clip(L / (np.percentile(L, 98) + 1e-5), 0, 1)), 0, 1)
    return h, 1.4 * size_of(L, px), crevices(h, 2.5 * px) * 0.6 + 0.4, rough
def cutout(L, px, rng, edges=None):
    # Leaves, fronds, grilles and the like: soft, their veins and folds from the picture's shading.
    g = [blur(L, s * px) for s in (0.45, 1.5, 5)]
    hgt = 0.35 * unit(g[0] - g[1]) + 0.65 * np.tanh(unit(g[1] - g[2]))
    lo, hi = np.percentile(hgt, [1, 99.5])
    h = 0.4 + 0.6 * np.clip((hgt - lo) / (hi - lo + 1e-5), 0, 1)
    return blur(h.astype(np.float32), 0.35 * px), 1.1 * size_of(L, px), crevices(h, 2 * px) * 0.5 + 0.5, 0.72
def organic(L, px, rng, edges=None):
    # Lobes of flesh and the pale sinews painted over them, which stand proud; soft all over.
    lobes = np.clip(unit(blur(L, 5 * px) - blur(L, 26 * px)), -2.2, 2.2)
    sinew = np.clip(unit(blur(L, 1.2 * px) - blur(L, 6 * px)), -1.6, 2.4)
    h = np.clip(0.52 + 0.17 * lobes + 0.13 * sinew, 0.05, 1)
    h = blur(h.astype(np.float32), 0.7 * px)
    return h, 2.0 * size_of(L, px), crevices(h, 4 * px, 0.5), 0.4
def slime(h, px, rng):
    """Where a soft surface is wet: its hollows, in pools broken up by patches, and a film elsewhere."""
    low = np.clip((blur(h, 4 * px) - h) * 3.5 + (float(h.mean()) - blur(h, 10 * px)) * 2 + 0.5, 0, 1)
    n = blur(rng.standard_normal(h.shape).astype(np.float32), 9 * px)
    patches = np.clip(unit(n) * 0.3 + 0.7, 0, 1)
    return blur(np.clip(0.3 + 0.7 * low * patches, 0, 1).astype(np.float32), 1.2 * px)
def speckle(shape, s, rng):
    """Tiling noise with blobs about `s` map texels across, unit spread."""
    return unit(blur(rng.standard_normal(shape).astype(np.float32), s))
def laid(L, px, grain, depth, shade, rough):
    """Ground: the picture's broad patches as low forms, under a grain finer than its texels."""
    g = [blur(L, s * px) for s in (0.6, 2, 6)]
    hgt = 0.25 * np.tanh(unit(g[0] - g[1])) + 0.35 * np.tanh(unit(g[1] - g[2])) + grain
    lo, hi = np.percentile(hgt, [1, 99.5])
    h = 0.3 + 0.7 * np.clip((hgt - lo) / (hi - lo + 1e-5), 0, 1)
    h = blur(h.astype(np.float32), 0.5)
    r = np.clip(rough + 0.05 * unit(blur(L, 1.5 * px) - L), 0, 1)
    return h, depth * size_of(L, px), 1 - shade * np.clip((blur(h, 2.5) - h) * 4, 0, 0.5), r
def grass(L, px, rng, edges=None):
    # Blades: thin twisting ridges a texel or two across, in tufts.
    blades = (1 - np.abs(np.tanh(speckle(L.shape, 1.4, rng)))) ** 3
    tufts = np.clip(speckle(L.shape, 6, rng) * 0.5 + 0.7, 0, 1)
    return laid(L, px, 0.9 * blades * tufts + 0.15 * speckle(L.shape, 0.7, rng), 1.0, 0.7, 0.9)
def soil(L, px, rng, edges=None):
    # Crumbs and pebbles over a fine tilth.
    pebbles = np.clip(speckle(L.shape, 3, rng) - 1.3, 0, None) * 1.2
    crumbs = 0.3 * speckle(L.shape, 1.3, rng) + 0.3 * speckle(L.shape, 4, rng)
    return laid(L, px, pebbles + crumbs, 1.2, 0.8, 0.92)
def sand(L, px, rng, edges=None):
    # Soft ripples, wandering, with a fine grain.
    h, w = L.shape
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    phase = 9 * y / h + 2 * x / w + 0.6 * speckle(L.shape, 40, rng) / 6.283
    ripples = 0.45 * np.sin(6.283 * phase) * np.clip(speckle(L.shape, 30, rng) * 0.4 + 0.7, 0, 1)
    return laid(L, px, ripples + 0.08 * speckle(L.shape, 1.0, rng), 0.8, 0.4, 0.85)
def snow(L, px, rng, edges=None):
    # Drifted and wind-scoured: soft swells, a little crust.
    swell = 0.4 * speckle(L.shape, 12, rng) + 0.12 * speckle(L.shape, 1.2, rng)
    return laid(L, px, swell, 0.6, 0.3, 0.6)
def stony(L, px, rng, edges=None):
    # Broken rock: sharp-edged facets and grit.
    facets = -np.abs(speckle(L.shape, 6, rng)) * 0.6 - np.abs(speckle(L.shape, 2.2, rng)) * 0.3
    return laid(L, px, facets + 0.06 * speckle(L.shape, 1, rng), 1.6, 0.9, 0.9)
def books(L, px, rng, edges=None):
    # Books standing in a row: each spine rounded, the gaps between them deep, the dark space over
    # them deeper still, and all a little back from the shelf that holds them.
    from scipy import ndimage
    # Smoothed up the row, so a spine's painted bands and lettering do not break it.
    soft = dir_blur(blur(L, 0.4 * px), 1.2 * px, 0)
    dark = soft < BOOK_DARK * float(np.median(soft))
    lab, n = ndimage.label(dark)
    if n:
        size = ndimage.sum(np.ones_like(soft), lab, np.arange(1, n + 1))
        dark &= np.r_[False, size >= (2 * px) ** 2 * 2][lab]
    # Where two books meet with no gap between: a line darker than the spines on either side.
    valley = unit(dir_blur(dir_blur(soft, 1.5 * px, 1) - soft, 1.5 * px, 0)) > BOOK_SIDE
    # The back of the case: dark, and calm across, where a row of spines is never calm.
    busy = blur((soft - dir_blur(soft, 2 * px, 1)) ** 2, 1.5 * px)
    calm = (busy < BOOK_CALM * float(np.median(busy))) & (soft < float(np.median(soft)))
    # Their outline eased, so the tops of the books run straight rather than ragged.
    j = (blur((dark | calm).astype(np.float32), 0.8 * px) > 0.5) | valley
    if edges is not None:
        j = j | edges
    # Across the row only: a spine rounds from side to side, not from its top down.
    d = ndimage.distance_transform_edt(~j, sampling=(8, 1)).astype(np.float32)
    lab, n = ndimage.label(~j)
    idx = np.arange(1, n + 1)
    r = np.ones(n + 1, np.float32)
    if n:
        r[1:] = np.maximum(ndimage.maximum(d, lab, idx).astype(np.float32), 1)
        # Wider than a book: the back of the case where it is dark, else books laid flat, which
        # round from top to bottom instead.
        wide = np.r_[False, r[1:] > BOOK_WIDE * px][lab]
        shade = np.r_[1.0, ndimage.mean(soft, lab, idx)][lab]
        back = wide & (shade < float(np.percentile(soft, 40)))
        j = j | back
        flat = wide & ~back
        dv = ndimage.distance_transform_edt(~j, sampling=(1, 8)).astype(np.float32)
        lab, n = ndimage.label(~j)
        idx = np.arange(1, n + 1)
        d = np.where(flat, dv, d)
        r = np.ones(n + 1, np.float32)
        if n:
            r[1:] = np.maximum(ndimage.maximum(d, lab, idx).astype(np.float32), 1)
    t = np.clip(d / r[lab], 0, 1)
    off = rng.uniform(-BOOK_STAGGER, BOOK_STAGGER, n + 1).astype(np.float32)
    # Bands and lettering stand a little off the spine.
    bands = np.clip(unit(blur(L, 0.4 * px) - blur(L, 2 * px)), -1, 2.5)
    spine = BOOK_FRONT - 0.2 + 0.2 * np.sqrt(1 - (1 - t) ** 2) + off[lab] + 0.012 * bands
    back = inside(j & ~valley, px)
    gap = 0.32 - 0.26 * np.clip(back / (2 * px), 0, 1)
    # Eased up the row, where the picture's texels would leave a spine's outline wavering.
    hgt = blur(dir_blur(np.where(j, gap, spine), 1.0 * px, 0).astype(np.float32), 0.5 * px)
    hgt = 1 - BOOK_SINK * (1 - hgt)
    rough = np.where(j, 0.95, BOOK_ROUGH - 0.12 * np.clip(bands - 1, 0, 1))
    # Light reaches little of the case behind them.
    occ = crevices(hgt, 1.5 * px, 0.8) * (0.4 + 0.6 * np.clip((1 - (1 - hgt) / BOOK_SINK) / BOOK_FRONT, 0, 1))
    return hgt, BOOK_DEPTH * size_of(L, px), occ, np.clip(rough, 0, 1)
def pages(L, px, rng, edges=None):
    # The leaves of a book seen edge-on, between the edges of its covers, which stand proud: the
    # picture's bands of leaves, and finer lines than its texels between them.
    axis = 1 if L.shape[1] >= L.shape[0] else 0
    along = dir_blur(L, 6 * px, axis)
    cover = along < 0.5 * float(np.median(along))
    leaves = np.clip(unit(along - blur(along, 1.5 * px)), -2, 2)
    n = L.shape[1 - axis]
    lines = rng.standard_normal(n).astype(np.float32)
    lines = lines[None, :] if axis == 0 else lines[:, None]
    hgt = np.where(cover, 1.0, 0.72 + 0.05 * leaves + 0.03 * lines) * np.ones_like(L)
    hgt = blur(hgt.astype(np.float32), 0.3 * px)
    return hgt, 0.8 * size_of(L, px), crevices(hgt, 1.2 * px, 0.4), np.where(cover, 0.7, 0.9)
RECIPES = dict(grass=grass, soil=soil, sand=sand, snow=snow, stony=stony, organic=organic, masonry=masonry, flagstone=flagstone, wood=wood, roof=roof, thatch=thatch,
               plaster=plaster, rock=rock, metal=metal, design=design, surface=surface, cutout=cutout,
               books=books, pages=pages)
def classify(L, a, px, floor=False):
    """Which recipe a picture tables/recipes.tsv does not list looks to want. Never stones: a stone
    finder takes too much else for them (planks, scales, cloth), and wrong mortar is worse than none."""
    red, green, blue = (float(a[..., c].mean()) for c in range(3))
    brown = red > green > blue and red > blue * 1.3
    if grain_axis(L)[1] > 2.0 and float(L.std()) > 0.05 and brown:
        return 'wood'
    if float((L - blur(L, 8 * px)).std()) < 0.06:
        return 'plaster'
    return 'surface'
