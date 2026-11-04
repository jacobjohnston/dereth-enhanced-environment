# New cactuses built as a cactus grows: a round trunk and arms of even thickness, each arm leaving the
# trunk in a rounded elbow and rising straight, every stem domed at its top and ribbed along its
# length, skinned in shapes.mjs's Gen_Cactus picture and set with spines in threes at its areoles.
# Only the original's layout is read: where its trunk and arms stand, how thick and how tall, from
# horizontal slices through it. None of its vertices, faces or picture coordinates is kept.
# cactus.py <out folder> <meshes folder, from dereth-art mesh> <id> [...]
import math, os, sys
import numpy as np
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boulders

TOOL = 'cactus.py'
# Ribs round a stem, and how deep they stand, a share of its radius.
RIBS = 14
RIB_DEPTH = 0.1
# Gen_Cactus draws 2 ribs across and 16 rows of areoles up one repeat, which covers this many metres.
PICTURE_RIBS, ROWS, FIRST_ROW = 2, 16, 1 / 64
PICTURE_METRES = 2.4
# Metres between areoles along a rib, and each spine's length and thickness at its foot.
EVERY = 0.3
LONG = 0.17
THICK = 0.012
SPINES_EACH = 3
# How finely the original is sliced to read its stems, metres.
SLICE = 0.08
# How far below the ground the trunk reaches, tapering to a point as a tree's foot does, so a
# cactus on a slope never shows its base; and the share of its radius left at its deepest ring.
SUNK = (1.0, 2.5)
TAPER = 0.3
# A stem no taller than this many times its radius is stout: its thickness follows the original's
# up its height, where a tall stem's is even.
STOUT = 7
# The levels of detail: points round a stem, metres between rings, the share of spines kept, and
# how far each is drawn.
LEVELS = ((3 * RIBS, 0.15, 1.0), (2 * RIBS, 0.3, 0.45), (RIBS, 0.7, 0.0))
SKIN = ({'name': 'Skin', 'pbrMetallicRoughness': {'metallicFactor': 0.0, 'roughnessFactor': 0.75}},
        'Gen_Cactus.png', None)
SPINE = ({'name': 'Spines', 'doubleSided': True,
          'pbrMetallicRoughness': {'baseColorFactor': [0.86, 0.8, 0.48, 1], 'metallicFactor': 0.0, 'roughnessFactor': 1.0}},
         'Gen_Stem.png', None)


def stems(tri):
    """The original's stems, read from horizontal slices: each a list of (height, centre, radius),
    the trunk first. A slice's pieces carry on the stem whose last centre they lie nearest."""
    lo, hi = tri.reshape(-1, 3).min(0), tri.reshape(-1, 3).max(0)
    xs, ys = (np.arange(lo[k] - SLICE, hi[k] + SLICE, SLICE) for k in (0, 1))
    zs = np.arange(lo[2] + SLICE, hi[2], 2 * SLICE)
    grid = np.stack(np.meshgrid(xs, ys, zs, indexing='ij'), -1).reshape(-1, 3)
    occupied = boulders.inside(grid + [1e-4, 2.3e-4, 0], tri, lo[2]).reshape(len(xs), len(ys), len(zs))
    tracks = []
    for k, z in enumerate(zs):
        label, n = ndimage.label(occupied[:, :, k])
        for c in range(1, n + 1):
            i, j = np.nonzero(label == c)
            if len(i) < 3:
                continue
            centre, radius = np.array([xs[i].mean(), ys[j].mean()]), math.sqrt(len(i) / math.pi) * SLICE
            near = [t for t in tracks if t[-1][0] >= z - 2.5 * SLICE and np.linalg.norm(t[-1][1] - centre) < max(t[-1][2], radius)]
            if near:
                min(near, key=lambda t: np.linalg.norm(t[-1][1] - centre)).append((z, centre, radius))
            else:
                tracks.append([(z, centre, radius)])
    # The trunk is the stem that stands lowest; an arm rises a while above the ground.
    tracks.sort(key=lambda t: (t[0][0], -len(t)))
    trunk = tracks[0]
    thick = np.median([p[2] for p in trunk if p[0] > 0.2] or [p[2] for p in trunk])
    arms = [t for t in tracks[1:] if len(t) >= 3 and t[-1][0] > 0.3 and np.median([p[2] for p in t]) > 0.35 * thick]
    return trunk, arms


def line(track):
    """A stem's straight centre line and even radius: a least-squares lean through its centres, and
    the median of its radii, past the swelling where an arm joins."""
    z = np.array([p[0] for p in track])
    c = np.array([p[1] for p in track])
    r = np.array([p[2] for p in track])
    # Above the ground, where the original tapers to its buried point.
    above = z > 0.2 if (z > 0.2).sum() >= 2 else np.ones(len(z), bool)
    radius = float(np.median(r[above]))
    # The lean through the slices of that thickness: not those swollen where an arm joins.
    even = above & (np.abs(r - radius) < 0.2 * radius)
    if even.sum() < 2:
        even = above
    fit = np.polyfit(z[even], c[even], 1) if even.sum() > 1 else np.array([[0, 0], c[even][0]])
    at = lambda h: np.array([*(fit[0] * h + fit[1]), h])
    if (z.max() - max(z.min(), 0)) / radius > STOUT:
        return at, (lambda h: np.full(np.shape(h), radius)), radius, z.min(), z.max()
    # A stout stem's own thickness up its height, smoothed of the slices' steps.
    zs, rs = z[above], np.convolve(np.pad(r[above], 1, mode='edge'), np.ones(3) / 3, mode='valid')
    return at, (lambda h: np.interp(h, zs, rs)), radius, z.min(), z.max()


def path(trunk, arm, ds):
    """An arm's centre line: out of the trunk level, turning up in a rounded elbow to its own line,
    then straight to its top."""
    at, _, radius, base, top = line(arm)
    on_trunk = trunk[0]
    start = on_trunk(base - 1.2 * radius)
    rise = at(base)
    out = rise[:2] - start[:2]
    out /= np.linalg.norm(out) + 1e-9
    # A cubic from the trunk's axis, level and outward, to the arm's foot, rising.
    reach = np.linalg.norm(rise[:2] - start[:2])
    b = [start, start + np.r_[out * reach * 0.6, 0], rise - np.r_[0, 0, 1.2 * radius * 0.7], rise]
    t = np.linspace(0, 1, max(int(1.6 * reach / ds), 6))[:, None]
    bend = (1 - t) ** 3 * b[0] + 3 * (1 - t) ** 2 * t * b[1] + 3 * (1 - t) * t ** 2 * b[2] + t ** 3 * b[3]
    up = np.array([at(h) for h in np.arange(base, top + radius * 0.5, ds)[1:]])
    return np.vstack([bend, up]), radius


def tube(points, radii, around):
    """A ribbed tube swept along `points`, each ring of its radius in `radii`, domed at its end: its
    vertices, normals, picture coordinates and triangles, and the frame of each ring."""
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    length = s[-1]
    radii = np.broadcast_to(radii, s.shape).astype(float)
    dome = 0.9 * np.interp(length - 0.9 * radii[-1], s, radii)
    keep = s < length - dome
    # The dome's rings spaced by angle, so it curves over evenly however coarse the stem's rings.
    end, up = points[-1], points[-1] - points[-2]
    up /= np.linalg.norm(up)
    angles = np.linspace(0, math.pi / 2, 9)
    radius = dome / 0.9
    base = np.r_[radii[keep], np.full(len(angles), radius)]
    points = np.vstack([points[keep], end - up[None] * (dome * (1 - np.sin(angles)))[:, None]])
    seg = np.diff(points, axis=0)
    s = np.r_[0, np.cumsum(np.linalg.norm(seg, axis=1))]
    length = s[-1]
    t = np.gradient(points, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    # Frames carried along the path without twisting.
    n = np.cross(t[0], [0.3, 0.5, 0.8] if abs(t[0][2]) > 0.9 else [0, 0, 1]); n /= np.linalg.norm(n)
    frames = []
    for k in range(len(points)):
        n = n - t[k] * (n @ t[k]); n /= np.linalg.norm(n)
        frames.append((n, np.cross(t[k], n)))
    r = base * np.sqrt(np.clip(1 - (np.clip(s - (length - dome), 0, None) / dome) ** 2, 0.0025, 1))
    # The dome closes to a point.
    r[-1] = 0.0
    theta = np.linspace(0, 2 * math.pi, around + 1)
    rib = 1 + RIB_DEPTH * (np.abs(np.cos(RIBS * theta / 2)) ** 1.4 - 0.5)
    N = np.array([f[0] for f in frames]); B = np.array([f[1] for f in frames])
    ring = np.cos(theta)[None, :, None] * N[:, None] + np.sin(theta)[None, :, None] * B[:, None]
    v = points[:, None] + (r[:, None] * rib[None])[..., None] * ring
    # Normals from the surface's own directions, round and along.
    d_round = np.gradient(v, axis=1)
    d_round[:, 0] = d_round[:, -1] = (v[:, 1] - v[:, -2]) / 2
    d_along = np.gradient(v, axis=0)
    # Round the ring is clockwise seen along the stem, so outward is round crossed with along.
    nor = np.cross(d_round, d_along)
    nor /= np.linalg.norm(nor, axis=2, keepdims=True) + 1e-12
    nor[-1] = t[-1]
    if r[0] == 0:
        nor[0] = -t[0]
    uv = np.stack(np.broadcast_arrays(theta[None] / (2 * math.pi) * RIBS / PICTURE_RIBS, -s[:, None] / PICTURE_METRES), -1)
    rows, cols = len(points), around + 1
    idx = np.arange(rows * cols).reshape(rows, cols)
    a, b, c, d = idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]
    faces = np.concatenate([np.stack([a, c, b], -1).reshape(-1, 3), np.stack([a, d, c], -1).reshape(-1, 3)])
    return v.reshape(-1, 3), nor.reshape(-1, 3), uv.reshape(-1, 2), faces, (s, r, N, B, points)


def areoles(sweep, radius, inside_trunk, start_after):
    """The spines' places on a stem: on each rib's crest, at the picture's rows of areoles, EVERY
    apart, each rib a row on from the next; none on the dome's very top or inside the trunk."""
    s, r, N, B, points = sweep
    rows = np.arange(FIRST_ROW * PICTURE_METRES, s[-1] - 0.25 * radius, PICTURE_METRES / ROWS)
    step = max(1, round(EVERY / (PICTURE_METRES / ROWS)))
    places = []
    for k in range(RIBS):
        theta = 2 * math.pi * k / RIBS
        for j, at in enumerate(rows):
            if (j + k % 2) % step or at < start_after:
                continue
            i = np.searchsorted(s, at)
            i = min(max(i, 1), len(s) - 1)
            w = (at - s[i - 1]) / max(s[i] - s[i - 1], 1e-9)
            centre = points[i - 1] * (1 - w) + points[i] * w
            rr = (r[i - 1] * (1 - w) + r[i] * w) * (1 + RIB_DEPTH * 0.5)
            out = math.cos(theta) * (N[i - 1] * (1 - w) + N[i] * w) + math.sin(theta) * (B[i - 1] * (1 - w) + B[i] * w)
            out /= np.linalg.norm(out)
            p = centre + out * rr
            if p[2] > 0.05 and not inside_trunk(p):
                places.append((p, out))
    return places


def spines(places, rng, keep):
    """Three-sided spikes, SPINES_EACH to an areole, splayed out and a little up."""
    pos, nor, tex, idx = [], [], [], []
    for at, out in places:
        if rng.random() >= keep:
            continue
        for k in range(SPINES_EACH):
            d = out + np.array([0, 0, 0.3]) + rng.uniform(-0.45, 0.45, 3)
            d /= np.linalg.norm(d)
            e = np.cross(d, [0.3, 0.5, 0.8]); e /= np.linalg.norm(e)
            g = np.cross(d, e)
            long = LONG * rng.uniform(0.6, 1.2)
            base = len(pos)
            for q in range(3):
                a = q / 3 * math.tau
                rr = e * math.cos(a) + g * math.sin(a)
                pos.append(at - d * 0.01 + rr * THICK); nor.append(rr); tex.append((0.5, 0.0))
            pos.append(at + d * long); nor.append(d); tex.append((0.5, 1.0))
            for q in range(3):
                idx.append((base + q, base + (q + 1) % 3, base + 3))
    return np.array(pos).reshape(-1, 3), np.array(nor).reshape(-1, 3), np.array(tex).reshape(-1, 2), np.array(idx, int).reshape(-1, 3)


def make(out, meshes, id):
    tri = boulders.triangles(meshes, id)
    trunk_track, arm_tracks = stems(tri)
    trunk = line(trunk_track)
    on_trunk, radius_at, trunk_radius, foot, top = trunk
    inside_trunk = lambda p: np.linalg.norm(p[:2] - on_trunk(p[2])[:2]) < radius_at(p[2]) * 0.98 and p[2] < top
    # Down to the original's buried point, within SUNK.
    deepest = -min(max(-foot, SUNK[0]), SUNK[1])
    seed = int(id, 16) & 0xFFFF
    os.makedirs(os.path.join(out, 'trees'), exist_ok=True)
    counts = []
    for lod, (around, ds, keep) in enumerate(LEVELS):
        heights = np.r_[deepest - 0.04, np.arange(deepest, top + radius_at(top) * 0.5, ds)]
        trunk_points = np.array([on_trunk(h) for h in heights])
        # Below the ground the trunk tapers to a closed point.
        radii = radius_at(np.maximum(heights, 0)) * np.where(heights < 0, TAPER + (1 - TAPER) * (1 - heights / deepest), 1)
        radii[0] = 0.0
        swept = [(tube(trunk_points, radii, around), trunk_radius, lambda p: False, 0.0)]
        for arm in arm_tracks:
            pts, radius = path(trunk, arm, ds)
            # Past where the arm comes out through the trunk's skin.
            leaves = next((np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))][k]
                           for k, p in enumerate(pts) if not inside_trunk(p)), 0.0)
            swept.append((tube(pts, radius, around), radius, inside_trunk, leaves))
        parts, places = [], []
        for (v, n, uv, f, sweep), radius, inside, after in swept:
            parts.append((*SKIN, v, n, uv, f))
            places += areoles(sweep, radius, inside, after)
        if keep:
            parts.append((*SPINE, *spines(places, np.random.default_rng(seed + lod), keep)))
        boulders.write_gltf(os.path.join(out, 'trees', f'{id}_lod{lod}.gltf'), parts, TOOL)
        counts.append(sum(len(p[-1]) for p in parts))
    return counts, len(arm_tracks), round(trunk_radius, 2)


if __name__ == '__main__':
    out, meshes = sys.argv[1:3]
    for id in sys.argv[3:]:
        counts, arms, radius = make(out, meshes, id)
        print(id, counts, 'triangles,', arms, 'arms, trunk radius', radius)
