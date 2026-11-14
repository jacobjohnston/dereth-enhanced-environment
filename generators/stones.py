# stones.py: shapes built surfaces (masonry, flagstone, cobble, brick) as solid stones. It finds the
# picture's dark mortar as wide as it is painted, and rounds each stone between: domed, its edges
# worn, a height and lean of its own, pitted where the picture is, sunk into joints as deep as wide.
import numpy as np
from scipy import ndimage
from masonry import blur

def unit(a):
    return a / (a.std() + 1e-6)

def wrapped(fn, a, pad):
    """`fn` of `a` as the picture repeats: worked on `a` padded by its own other side, then cut back."""
    h, w = a.shape
    p = min(pad, h, w)
    return fn(np.pad(a, p, mode='wrap'))[p:p + h, p:p + w]

def labels(mask):
    """Each connected patch of `mask`, joined across the picture's edges as it repeats; 0 off it."""
    lab, n = ndimage.label(mask)
    parent = np.arange(n + 1)
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for a, b in ((lab[0], lab[-1]), (lab[:, 0], lab[:, -1])):
        for x, y in zip(a, b):
            if x and y:
                rx, ry = root(x), root(y)
                if rx != ry:
                    parent[max(rx, ry)] = min(rx, ry)
    roots = np.array([root(i) for i in range(n + 1)])
    _, dense = np.unique(roots, return_inverse=True)
    return dense.reshape(-1)[lab].reshape(lab.shape) if n else lab

def inside(mask, px):
    """How far each texel of `mask` lies from its edge, in map texels, as the picture repeats."""
    return wrapped(ndimage.distance_transform_edt, mask, int(40 * px) + 8).astype(np.float32)

def mortar(L, px, size, edges=None, courses=False, straight=False):
    """The mortar: what is darker than the stones about it, at the threshold that leaves the most
    of the picture in whole stones. Its stones' labels, and how well it read as stones (0 to 1)."""
    h, w = L.shape
    s = blur(L, 0.7 * px)
    z = unit(blur(L, size * px) - s)
    tried = []
    for t in (0.15, 0.3, 0.45, 0.6, 0.8, 1.0, 1.25):
        j = z > t
        if edges is not None:
            j |= edges
        # Specks are pits, not joints: a joint runs on.
        lab = labels(j)
        area = np.bincount(lab.ravel())
        area[0] = 0
        j = area[lab] > (6 * px) ** 2
        j = wrapped(lambda a: ndimage.binary_closing(a, iterations=max(1, int(0.6 * px))), j, 8)
        cov = float(j.mean())
        cells = labels(~j)
        frac = np.bincount(cells.ravel()) / cells.size
        frac[0] = 0
        good = (frac > (8 * px) ** 2 / cells.size) & (frac < 0.35)
        score = float(frac[good].sum()) / max(1e-6, 1 - cov)
        score -= 1.5 * max(0, cov - 0.42) + 1.5 * max(0, 0.05 - cov)
        tried.append((score, j, cells, good))
    score, j, cells, good = max(tried, key=lambda t: t[0])
    laid = coursed(L, px, size, wrapped(lambda a: ndimage.binary_dilation(a, iterations=max(1, int(1.2 * px))), j, 8)) if courses else None
    if laid is not None:
        # The courses' straight joints, with what of the found mortar runs along them.
        # A wall's joints run straight as its courses do; a floor's keep what runs along them.
        near = inside(~laid, px) <= 1.2 * px
        j = laid if straight else laid | (j & near)
        cells = labels(~j)
        frac = np.bincount(cells.ravel()) / cells.size
        frac[0] = 0
        good = frac > (4 * px) ** 2 / cells.size
        score = max(score, 0.9)
    # A piece too small to be a stone is mortar rubble; the mortar's outline smoothed of jags.
    j = j | ~good[cells]
    j = blur(j.astype(np.float32), 0.8 * px) > 0.5
    if edges is not None:
        j |= edges
    # A patch of it on its own, away from the rest, is a chip in a stone, not a joint; a speck is
    # neither, and stays stone.
    lab = labels(j)
    area = np.bincount(lab.ravel())
    area[0] = 0
    j &= area[lab] > (3.5 * px) ** 2
    chip = (area[lab] < 0.012 * j.size) & j
    cells = labels(~(j & ~chip) & ~chip)
    return j & ~chip, chip, cells, max(0.0, score)

def runs(flags):
    """The runs of True in a ring of flags, as (start, length)."""
    n = len(flags)
    if flags.all() or not flags.any():
        return []
    start = int(np.argmin(flags))
    out, at = [], None
    for k in range(n + 1):
        i = (start + k) % n
        if flags[i] and at is None:
            at = k
        elif not flags[i] and at is not None:
            out.append(((start + at) % n, k - at))
            at = None
    return out

def coursed(L, px, size, found):
    """A wall laid in courses: its bed joints straight across where whole rows are dark, its head
    joints straight up where a course's columns are, each where the `found` mortar bears it out;
    None where it has no plain courses."""
    h, w = L.shape
    z = unit(blur(L, size * px) - blur(L, 0.7 * px))
    rows = blur(np.repeat(z.mean(1, keepdims=True), 4, 1), 0.4 * px)[:, 0]
    r = (rows - np.median(rows)) / (rows.std() + 1e-6)
    beds = [b for b in runs(r > 0.9) if b[1] <= 6 * px]
    if len(beds) < 2 or len(beds) * 4 * px > h:
        return None
    # A course twice as tall as the rest has a bed joint faint in the picture: at its darkest row.
    for _ in range(4):
        gaps = [((b1[0] - b0[0]) % h or h) for b0, b1 in zip(beds, beds[1:] + beds[:1])]
        tall = int(np.argmax(gaps))
        if gaps[tall] < 1.6 * np.median(gaps):
            break
        y0, n0 = beds[tall]
        span = (y0 + n0 + int(2 * px) + np.arange(max(1, gaps[tall] - n0 - int(4 * px)))) % h
        y = int(span[np.argmax(r[span])])
        width = int(np.median([n for _, n in beds]))
        beds = sorted(beds + [((y - width // 2) % h, width)])
    # Two bed joints a sliver apart are one: the sliver is mortar.
    merged = []
    for y, n in sorted(beds):
        if merged and y - (merged[-1][0] + merged[-1][1]) < 4 * px:
            merged[-1] = (merged[-1][0], y + n - merged[-1][0])
        else:
            merged.append((y, n))
    beds = merged
    if len(beds) < 2:
        return None
    j = np.zeros((h, w), bool)
    for y, n in beds:
        j[(y + np.arange(n)) % h] = True
    # Between each bed joint and the next, the course's own head joints.
    for (y0, n0), (y1, _) in zip(beds, beds[1:] + [(beds[0][0] + h, 0)]):
        ys = (y0 + n0 + np.arange(max(0, y1 - y0 - n0))) % h
        if len(ys) < 4 * px:
            continue
        cols = blur(np.repeat(z[ys].mean(0, keepdims=True), 4, 0), 0.4 * px)[0]
        c = (cols - np.median(cols)) / (cols.std() + 1e-6)
        # A course has its head joints: the plainest, or failing them the fainter.
        for least, sure in ((1.6, 0.6), (1.0, 0.4)):
            heads = [np.ix_(ys, (x + np.arange(n)) % w) for x, n in runs(c > least)
                     if n <= 5 * px and float(found[np.ix_(ys, (x + np.arange(n)) % w)].mean()) > sure]
            if heads:
                break
        for span in heads:
            j[span] = True
    cov = float(j.mean())
    if not 0.06 < cov < 0.4:
        return None
    # The courses must stand for the mortar found: most of each lies along the other.
    # (Where the courses are surely mortar, the rest found is stains on the stones.)
    sure, told = float(found[j].mean()), float((inside(~j, px) <= 1.5 * px)[found].mean())
    if not (sure >= 0.7 and told >= 0.65 or sure >= 0.82 and told >= 0.4):
        return None
    return j

def stones(L, px, rng, flat=False, edges=None, size=None, courses=False):
    """The picture as stones in mortar: height (1 the highest face), the depth of its whole range in
    retail texels, occlusion, the mortar, and how well it read as stones (0 to 1)."""
    h, w = L.shape
    size = size or float(np.clip(min(h, w) / px / 14, 4, 14))
    j, chip, cells, found = mortar(L, px, size, edges, courses, not flat)
    if not flat:
        return wall(L, px, rng, j, chip, cells, found)
    d = inside(~(j | chip), px)
    n = int(cells.max()) + 1
    r = ndimage.maximum(d, cells, np.arange(n)).astype(np.float32)
    r[0] = 1
    rc = np.maximum(r[cells], 1)
    # Worn edges: a quarter round over about a third of the way in, as a stone's own size has it.
    bevel = np.clip(0.32 * rc, 1.2 * px, 0.75 * rc)
    e = np.clip(d / bevel, 0, 1)
    edge = 1 - (1 - e) ** 2
    # Each stone domed over its whole face, a floor's less than a wall's.
    x = np.clip(d / rc, 0, 1)
    dome = 1 - (1 - x) ** 2
    lift = rng.uniform(-1, 1, n).astype(np.float32)
    tx, ty = rng.uniform(-1, 1, n).astype(np.float32), rng.uniform(-1, 1, n).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    idx = cells.ravel()
    area = np.bincount(idx, minlength=n).astype(np.float32) + 1e-6
    # A stone's middle, its texels taken nearest it where it wraps the picture's edge.
    def middle(c, span):
        ang = c / span * 2 * np.pi
        a = np.arctan2(np.bincount(idx, np.sin(ang).ravel(), n), np.bincount(idx, np.cos(ang).ravel(), n))
        return (a % (2 * np.pi)) / (2 * np.pi) * span
    cx, cy = middle(xx, w), middle(yy, h)
    ox = (xx - cx[cells] + w / 2) % w - w / 2
    oy = (yy - cy[cells] + h / 2) % h - h / 2
    lean = (ox * tx[cells] + oy * ty[cells]) / (np.sqrt(area[cells] / np.pi) + 1)
    # The joint about a ninth as deep as the stones are broad, for the whole range.
    breadth = float((r[1:] * area[1:]).sum() / area[1:].sum()) / px if n > 1 else 14
    depth = float(np.clip(0.2 * breadth, 1.5, 12))
    # Pits and grain are as deep in texels on a big stone as on a small one.
    grain = 2.5 / depth
    face = 0.84 + (0.04 if flat else 0.07) * lift[cells] + (0.03 if flat else 0.05) * np.clip(lean, -1.2, 1.2)
    face += (0.09 if flat else 0.16) * (dome - 1)
    # Pits and wear from the picture: its small dark spots sink, its grain stands a little.
    fine = unit(blur(L, 0.45 * px) - blur(L, 2.5 * px))
    pits = np.clip(-fine - 1.1, 0, 2.5)
    face += (0.035 * np.clip(fine, -2, 2) - 0.045 * pits) * grain
    stone = 0.3 + (face - 0.3) * edge
    # A chip falls a third of the way to the mortar; the mortar to its deepest along its middle.
    dj = inside(j | chip, px)
    stone = np.where(chip, 0.72 - 0.08 * np.clip(dj / (1.2 * px), 0, 1), stone)
    joint = 0.3 - 0.12 * np.clip(dj / (1.5 * px), 0, 1) + 0.025 * np.clip(fine, -2, 2) * grain
    hgt = np.where(j, joint, stone)
    hgt = blur(hgt.astype(np.float32), 0.4 * px)
    hgt = np.clip(hgt / max(1e-3, float(hgt.max())), 0, 1)
    # The joint about a ninth as deep as the stones are broad, for the whole range.
    occ = 1 - np.clip((blur(hgt, 2.5 * px) - hgt) * 2.6, 0, 0.75)
    occ = occ * (1 - 0.25 * j * np.clip(dj / (1.5 * px), 0, 1))
    return hgt.astype(np.float32), depth, occ.astype(np.float32), j, found

def wall(L, px, rng, j, chip, cells, found):
    """A wall's stones, softly: each face a gentle dome highest mid-stone, its arrises rolled round
    over a fifth of its short half-width, its joint a little below its edge, its pits and grain in a
    sixth value, a height for the normal alone."""
    h, w = L.shape
    j = j | chip
    d = inside(~j, px)
    n = int(cells.max()) + 1
    r = np.maximum(ndimage.maximum(d, cells, np.arange(n)).astype(np.float32), 1)
    r[0] = 1
    rc = r[cells]
    # The dome over the whole face from the distance to the joint, softened so no ridge runs along
    # a long stone: 0 at its edge, 1 at its middle.
    solid = (~j).astype(np.float32)
    soft = blur(d * solid, 0.3 * float(np.median(r[1:])) if n > 1 else 2 * px) / np.maximum(
        blur(solid, 0.3 * float(np.median(r[1:])) if n > 1 else 2 * px), 1e-3)
    top = np.maximum(ndimage.maximum(soft, cells, np.arange(n)).astype(np.float32), 1e-3)
    x = np.clip(soft / top[cells], 0, 1) * solid
    dome = 0.5 - 0.5 * np.cos(np.pi * x)
    # The arris rolled round over a fifth of the short half-width (the stone's inradius).
    arris = np.maximum(0.22 * rc, 0.8 * px)
    roll = np.sin(0.5 * np.pi * np.clip(d / arris, 0, 1))
    lift = rng.uniform(-0.04, 0.04, n).astype(np.float32)
    edge = 0.78 + lift[cells]
    face = edge + 0.2 * dome
    # The mortar about a ninth of the range below the stones' edges, a little hollow along its middle.
    dj = inside(j, px)
    floor = 0.67 - 0.02 * np.sin(0.5 * np.pi * np.clip(dj / (1.5 * px), 0, 1))
    hgt = np.where(j, floor, floor + (face - floor) * roll)
    # Pits and grain soft in the height (a couple of steps in 255), and in the normal gently.
    fine = np.clip(unit(blur(L, 0.5 * px) - blur(L, 2.5 * px)), -2, 2)
    hgt = blur(hgt.astype(np.float32), 0.35 * px) + 0.005 * blur(fine, 0.8 * px)
    hgt = np.clip(hgt / float(hgt.max()), 0, 1)
    soft_fine = blur(fine, 0.6 * px)
    detail = (0.004 * soft_fine - 0.006 * np.clip(-soft_fine - 0.8, 0, 1)) * solid
    # As steep at the arris as a stone's own roll: about 35 degrees across it.
    span = float(np.median(np.maximum(0.22 * r[1:], 0.8 * px))) / px if n > 1 else 2
    depth = float(np.clip(0.7 * span / 0.12, 1.5, 12))
    occ = 1 - np.clip((blur(hgt, 2.0 * px) - hgt) * 4, 0, 0.5)
    occ = occ * (1 - 0.15 * j * np.clip(dj / (1.5 * px), 0, 1))
    return hgt.astype(np.float32), depth, occ.astype(np.float32), j, found, detail.astype(np.float32)
