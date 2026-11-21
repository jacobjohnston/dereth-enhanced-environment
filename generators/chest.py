# The iron chest painted anew (0x0200007C, 0x02000A23, 0x02001250): its sides, lid and lock plate
# drawn at four times retail's texels from shapes and noise alone, in place of the player's picture.
# Each part lies where the retail picture paints it (its bands, rolled rims, rivets, hinge scrolls,
# lid rings and keyhole), so the chest's picture coordinates still fit. Each part takes its colours
# from a ramp of that part's colours in the player's picture by brightness, and its rust as much of
# it as that picture rusts, as rockgen.py does, so no retail pixel is copied. Its relief, roughness
# and metal map are made from the same shapes, in millimetres at the chest's own size.
# Needs Python with numpy and scipy, and ImageMagick (`magick`).
# chest.py <pack folder> <the player's pictures> [--into 2005]
# --into: that era's pictures of the same ids (pyreal-art pictures), in materials/<era>/.
import os, re, subprocess, sys
import numpy as np
from scipy.spatial import cKDTree
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import relief
import grit as GRIT
from masonry import blur

TOOL = 'chest.py'
# How many texels of the new picture to one of retail's.
SCALE = 4
# Each picture: its size on the chest in metres, and its parts in parts of the picture (x across,
# y down): raised bands, their rolled rims, sunk grooves, the plain skirt under the bottom band, the
# dark arch under the chest, hinge scrolls (x of the stem, its top and foot), lid rings (x, y,
# radius in retail texels), a lock panel, a keyhole (x, top, foot), a bevelled edge, and rivets
# (each at the palest spot within two retail texels of where it is listed) and their radius in
# retail texels. Both eras paint one layout; the 2005 picture's scrolls, rings and rivets sit a
# little apart from end of retail's.
SIDE = dict(size=(0.90, 0.45),
            bands=[(0, 0, 1, 0.156), (0, 0.156, 0.135, 0.565), (0.865, 0.156, 0.135, 0.565), (0, 0.735, 1, 0.055)],
            rims=[(0, 0, 1, 0.022), (0.108, 0.156, 0.027, 0.565), (0.865, 0.156, 0.027, 0.565), (0, 0.735, 1, 0.03)],
            grooves=[(0, 0.718, 1, 0.017)], skirt=(0, 0.79, 1, 0.21), arch=(0.08, 0.92, 0.075), rivet_r=1.5)
LID = dict(size=(0.90, 0.55), bands=[(0, 0, 0.14, 1), (0.86, 0, 0.14, 1)],
           rims=[(0.122, 0, 0.018, 1), (0.86, 0, 0.018, 1)], grooves=[(0.14, 0.47, 0.72, 0.03)], rivet_r=1.2)
LOCK = dict(size=(0.20, 0.16), bands=[(0, 0, 1, 0.27)], rims=[(0, 0.245, 1, 0.025)], panel=(0.30, 0.30, 0.38, 0.5),
            bevel=True, rivet_r=1.6)
PICTURES = {
    None: {
        '0x05000A6F': dict(SIDE, scrolls=[(0.19, 0.2, 0.58), (0.81, 0.2, 0.58)],
                           rivets=[(0.078, 0.078), (0.242, 0.078), (0.742, 0.078), (0.906, 0.078), (0.055, 0.227), (0.055, 0.391),
                                   (0.055, 0.555), (0.93, 0.234), (0.93, 0.375), (0.93, 0.555)]),
        '0x05000A70': dict(LID, rings=[(0.19, 0.78, 3.2), (0.83, 0.78, 3.2)],
                           rivets=[(0.06, 0.3), (0.06, 0.72), (0.945, 0.312), (0.945, 0.719)]),
        '0x05000A6E': dict(LOCK, keyhole=(0.485, 0.33, 0.74), rivets=[(0.156, 0.125), (0.844, 0.125), (0.156, 0.812), (0.844, 0.781)]),
    },
    '2005': {
        '0x05000A6F': dict(SIDE, scrolls=[(0.17, 0.2, 0.55), (0.83, 0.2, 0.55)],
                           rivets=[(0.105, 0.078), (0.25, 0.078), (0.764, 0.078), (0.895, 0.078), (0.055, 0.235), (0.055, 0.39),
                                   (0.055, 0.56), (0.945, 0.235), (0.945, 0.39), (0.945, 0.56)]),
        '0x05000A70': dict(LID, rings=[(0.163, 0.76, 3.2), (0.833, 0.76, 3.2)],
                           rivets=[(0.07, 0.27), (0.07, 0.74), (0.93, 0.27), (0.93, 0.74)]),
        '0x05000A6E': dict(LOCK, keyhole=(0.485, 0.33, 0.74), rivets=[(0.125, 0.125), (0.844, 0.125), (0.125, 0.812), (0.844, 0.812)]),
    },
}
# Heights, metres: a band over the plate, a rolled rim over its band, a rivet's dome, a scroll or
# ring's most, the lock panel, a groove, the arch, the keyhole and a bevelled edge; the hammered
# plate's dents.
BAND, RIM, RIVET, FORM, PANEL, GROOVE, ARCH, SLOT, BEVEL, DENT = 0.003, 0.001, 0.0035, 0.0035, 0.0015, 0.0012, 0.002, 0.008, 0.0015, 0.0003
# How deep the client's deepest relief reaches, metres (a height map's 0).
DEEPEST = 0.12
# The parts each texel's colour is drawn from, nearest first, and the part a part takes its colours
# from where the player's picture has too few texels of it.
PARTS = ('slot', 'arch', 'rivet', 'ring', 'form', 'panel', 'rim', 'groove', 'band', 'skirt', 'plate')
# A rim's colours are drawn halfway to its band's: retail paints its light, which the relief now casts.
TOWARD = dict(rim=('band', 0.5))
STANDS_IN = dict(rivet='rim', ring='form', form='plate', panel='band', slot='groove', arch='groove', rim='band', skirt='plate', groove='plate')
# How warm (red over blue, against red) a texel of the player's picture is to be rust, and how far
# each part's ramp is drawn toward its mean: the new picture has four times the texels, so it is
# calmer than retail's speckle at the same spread.
RUSTY, CALM = 0.3, 0.5
# Roughness: iron's, how much smoother where worn bright, how much rougher where it rusts.
ROUGH, WORN, RUST_ROUGH = 0.55, 0.18, 0.3
# How many times brighter than its picture the iron is drawn (not its rust).
BRIGHTEN = 1.5


def option(args, name, default):
    return args[args.index(name) + 1] if name in args else default


def soften(a, sx, sy):
    """a blurred by sx texels across and sy down."""
    fy = np.fft.fftfreq(a.shape[0])[:, None]; fx = np.fft.rfftfreq(a.shape[1])[None, :]
    return np.fft.irfft2(np.fft.rfft2(a) * np.exp(-2 * np.pi ** 2 * ((sx * fx) ** 2 + (sy * fy) ** 2)), s=a.shape)


def noise(rng, h, w, s, tall=1.0):
    """Smooth noise with blobs about s texels across and s * tall down, unit spread."""
    a = soften(rng.standard_normal((h, w)), s, s * tall)
    return a / (a.std() + 1e-9)


def box(X, Y, r, sw, sh):
    """Signed distance into a rectangle (parts of the picture), retail texels: positive inside."""
    x, y, rw, rh = r
    return np.minimum(np.minimum(X - x * sw, (x + rw) * sw - X), np.minimum(Y - y * sh, (y + rh) * sh - Y))


def ease(d, width):
    """0 outside, 1 a width inside, rounded between."""
    t = np.clip(d / width, 0, 1)
    return t * t * (3 - 2 * t)


def stroke(X, Y, pts, half):
    """A round-topped bar along points (retail texels) of the given half widths: its 0..1 profile."""
    d, i = cKDTree(pts).query(np.dstack([X, Y]).reshape(-1, 2), distance_upper_bound=4.0)
    d = d.reshape(X.shape)
    hw = np.append(half, 1.0)[np.minimum(i, len(pts))].reshape(X.shape)
    return np.sqrt(np.clip(1 - (d / hw) ** 2, 0, 1))


def scroll(X, Y, cx, top, foot, tall):
    """A strap hinge: a stem down to a spade foot, under two curls that wind inward, `tall` times
    as many texels down as across."""
    t = np.linspace(0, 1, 160)
    stem = np.stack([np.full_like(t, cx), top + 4.0 * tall + (foot - 2.8 - top - 4.0 * tall) * t], -1)
    pts, half = [stem], [2.1 - 0.7 * t]
    for side in (1, -1):
        a = np.pi + 2 * np.pi * 1.2 * t
        r = 3.9 - 2.7 * t
        curl = np.stack([cx + side * (3.2 + 0.82 * r * np.cos(a)), top + 4.2 * tall + tall * r * np.sin(a)], -1)
        pts.append(curl), half.append(1.6 - 0.7 * t)
    p = stroke(X, Y, np.concatenate(pts), np.concatenate(half))
    # The spade foot: a diamond as wide as the stem's top.
    spade = 1 - (np.abs(X - cx) / 3.2 + np.abs(Y - (foot - 3.0)) / 3.2)
    return np.maximum(p, np.sqrt(np.clip(spade / 0.45, 0, 1)))


def shapes(spec, sw, sh, k):
    """The picture's parts at k texels to one of retail's: their heights (metres) and masks."""
    w, h = sw * k, sh * k
    Y, X = (np.mgrid[0:h, 0:w] + 0.5) / k
    aa = 0.5 / k + 0.15
    m = {p: np.zeros((h, w), np.float32) for p in PARTS}
    hgt = np.zeros((h, w), np.float32)
    band = np.zeros((h, w), np.float32)
    for r in spec.get('bands', []):
        band = np.maximum(band, ease(box(X, Y, r, sw, sh) + 0.3, 0.9))
    hgt += BAND * band
    m['band'] = band
    rim = np.zeros((h, w), np.float32)
    for r in spec.get('rims', []):
        d = box(X, Y, r, sw, sh)
        # A rolled rim: round across its width.
        rw = min(r[2] * sw, r[3] * sh) / 2
        rim = np.maximum(rim, np.sqrt(np.clip(1 - (1 - np.clip(d / rw, 0, 1)) ** 2, 0, 1)) * (d > -aa))
    hgt += RIM * rim * band
    m['rim'] = np.clip(rim * 1.6, 0, 1) * band
    groove = np.zeros((h, w), np.float32)
    for r in spec.get('grooves', []):
        groove = np.maximum(groove, ease(box(X, Y, r, sw, sh) + 0.3, 0.6))
    hgt -= GROOVE * groove
    m['groove'] = groove
    if 'skirt' in spec:
        m['skirt'] = ease(box(X, Y, spec['skirt'], sw, sh) + 0.3, 0.6)
    if 'arch' in spec:
        x0, x1, rise = spec['arch']
        u = (X / sw - (x0 + x1) / 2) / ((x1 - x0) / 2)
        top = 1 - rise * np.sqrt(np.clip(1 - u * u, 0, 1))
        arch = ease((Y / sh - top) * sh + 0.2, 0.8) * (np.abs(u) < 1)
        hgt -= ARCH * arch
        m['arch'] = arch
    form = np.zeros((h, w), np.float32)
    for cx, top, foot in spec.get('scrolls', []):
        # Rounder on the chest than in the picture, as retail's scrolls are.
        tall = 0.7 * (spec['size'][0] / sw) / (spec['size'][1] / sh)
        form = np.maximum(form, scroll(X, Y, cx * sw, top * sh, foot * sh, tall))
    ring = np.zeros((h, w), np.float32)
    for cx, cy, r in spec.get('rings', []):
        d = np.hypot(X - cx * sw, Y - cy * sh)
        ring = np.maximum(ring, np.sqrt(np.clip(1 - ((d - r) / 0.8) ** 2, 0, 1)))
        # The staple it hangs from.
        staple = box(X, Y, (cx - 1.6 / sw, cy - (r + 1.5) / sh, 3.2 / sw, 2.0 / sh), sw, sh)
        form = np.maximum(form, ease(staple + 0.2, 0.7))
    hgt += FORM * np.maximum(form, ring)
    m['form'], m['ring'] = np.clip(form * 2, 0, 1), np.clip(ring * 2, 0, 1)
    if 'panel' in spec:
        panel = ease(box(X, Y, spec['panel'], sw, sh) + 0.2, 1.2)
        hgt += PANEL * panel
        m['panel'] = panel
    if 'keyhole' in spec:
        cx, top, foot = spec['keyhole']
        cx, top, foot = cx * sw, top * sh, foot * sh
        ty = top + 1.9
        slot = np.maximum(1.9 - np.hypot(X - cx, Y - ty),
                          np.minimum(0.8 + 0.35 * np.clip((Y - ty) / (foot - ty), 0, 1) - np.abs(X - cx), np.minimum(Y - ty, foot - Y)))
        slot = ease(slot + 0.15, 0.5)
        hgt -= SLOT * slot
        m['slot'] = slot
    if spec.get('bevel'):
        e = np.minimum(np.minimum(X, sw - X), np.minimum(Y, sh - Y)) / 1.5
        hgt -= BEVEL * (1 - np.clip(e, 0, 1)) ** 2
    m['plate'] = np.ones((h, w), np.float32)
    return hgt, m, X, Y


def rivets(spec, L, hgt, m, X, Y, sw, sh):
    """Domes at each listed rivet, moved to the palest retail texel within two of it."""
    h, w = L.shape
    yy, xx = np.mgrid[0:h, 0:w]
    pale = blur(L, 0.7)
    dome = np.zeros(X.shape, np.float32)
    spots = []
    for fx, fy in spec.get('rivets', []):
        near = ((xx + 0.5 - fx * w) ** 2 + (yy + 0.5 - fy * h) ** 2) <= 4
        y, x = np.unravel_index(np.argmax(np.where(near, pale, -1)), pale.shape)
        spots.append((x + 0.5, y + 0.5))
    for cx, cy, foot in spec.get('scrolls', []):
        # A small rivet holds each hinge's stem.
        spots.append((cx * sw, (cy + 0.55 * (foot - cy)) * sh))
    r = spec['rivet_r']
    for x, y in spots:
        q = 1 - ((X - x) ** 2 + (Y - y) ** 2) / (r * r)
        dome = np.maximum(dome, np.sqrt(np.clip(q, 0, 1)))
    m['rivet'] = np.clip(dome * 3, 0, 1)
    return hgt + RIVET * dome, spots


def ramp(colours, n=24):
    """The mean colour of each of n steps of brightness, darkest first, drawn toward their mean."""
    L = colours @ [0.3, 0.59, 0.11]
    o = colours[np.argsort(L)]
    steps = np.array([c.mean(0) for c in np.array_split(o, min(n, len(o)))])
    return o.mean(0) + CALM * (steps - o.mean(0))


def through(r, u):
    """u (0..1) along a ramp."""
    x = np.linspace(0, 1, len(r))
    return np.stack([np.interp(u, x, r[:, c]) for c in range(3)], -1)


def rank(v, where):
    """Each texel's place (0..1) among the texels where `where` holds."""
    s = np.sort(v[where]) if where.any() else np.sort(v.ravel())
    return np.searchsorted(s, v, side='right') / max(1, len(s))


def paint(id, spec, src, rng):
    """The new picture and its maps, from the player's picture's layout and colours."""
    a = relief.read(src, *size(src))[..., :3]
    sh, sw = a.shape[:2]
    L = (a * [0.3, 0.59, 0.11]).sum(-1)
    warm = (a[..., 0] - a[..., 2]) / (a[..., 0] + 0.03)
    # Rust is warm and not in shadow: the arch's dark brown is shade.
    rusty = (warm >= RUSTY) & (L >= 0.08)
    # The parts at retail's own texels, to read each part's colours and rust.
    h1, m1, X1, Y1 = shapes(spec, sw, sh, 1)
    _, spots = rivets(spec, L, h1, m1, X1, Y1, sw, sh)
    own = owner(m1)
    hgt, m, X, Y = shapes(spec, sw, sh, SCALE)
    hgt, _ = rivets(spec, L, hgt, m, X, Y, sw, sh)
    h, w = hgt.shape
    k = SCALE
    # Texels are not square on the chest: noise is round in metres.
    mx, my = spec['size'][0] / w, spec['size'][1] / h
    n = lambda s: noise(rng, h, w, s, mx / my)
    # Hammered iron: dents in the plate, pits and grain on all of it.
    dents = soften((rng.random((h, w)) < 0.012).astype(np.float32), 0.9 * k, 0.9 * k * mx / my)
    dents /= dents.max() + 1e-9
    hgt -= DENT * dents * (1 - m['band']) * (1 - m['rivet'])
    pits = np.clip(-n(0.25 * k) - 1.6, 0, 1)
    hgt -= 0.0002 * pits
    mottle = 0.7 * n(4.0 * k) + 0.5 * n(1.5 * k)
    grain = n(0.35 * k) - 0.8 * pits - 1.2 * dents
    # Light from above and a little left, and the iron dark where sunk and worn bright where raised.
    sx = (np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)) / 2 / mx
    sy = (np.roll(hgt, -1, 0) - np.roll(hgt, 1, 0)) / 2 / my
    shade = np.tanh(2.5 * (0.85 * sy + 0.35 * sx))
    cavity = (hgt - blur(hgt, 1.5 * k)) / 0.0015
    v = 0.3 * mottle + 0.25 * grain + 1.2 * shade + 1.1 * np.tanh(cavity)
    # Each part's colours by its own ramp, blended where parts meet.
    iron = ~rusty
    colour = np.zeros((h, w, 3), np.float32)
    weight = np.zeros((h, w), np.float32)
    left = np.ones((h, w), np.float32)
    alone = {}
    for p in PARTS:
        q = p
        while (own == q).sum() < 6 and q in STANDS_IN:
            q = STANDS_IN[q]
        pick = (own == q) & (iron | (q in ('rivet', 'arch')))
        if pick.sum() < 4:
            pick = own == q
        wt = alone[p] = m[p] * left
        left = left * (1 - m[p])
        if wt.max() <= 0:
            continue
        r = ramp(a[pick])
        if p in TOWARD:
            o, f = TOWARD[p]
            r = (1 - f) * r + f * ramp(a[(own == o) & iron])
        colour += wt[..., None] * through(r, rank(v, m[p] > 0.5))
        weight += wt
    colour /= np.maximum(weight, 1e-6)[..., None]
    # Baked as retail bakes it: dark in the crevices round raised parts and under them, bright on
    # their worn edges.
    drop = blur(np.roll(np.roll(hgt, k // 2, 0), k // 4, 1), 0.7 * k) - hgt
    colour *= (1 - 0.55 * np.clip(-cavity, 0, 1.2) / 1.2 - 0.35 * np.clip(drop / 0.0015, 0, 1))[..., None]
    colour *= (1 + 0.2 * np.clip(cavity, 0, 1) * np.clip(shade + 0.6, 0, 1))[..., None]
    # Rust: as much of each part as the player's picture rusts, in patches and in runs below the
    # rivets and the bands' lower edges.
    under = np.zeros((h, w), np.float32)
    for x, y in spots:
        under += np.exp(-((X - x) / 1.2) ** 2) * np.clip((Y - y) / 2, 0, 1) * np.exp(-np.clip(Y - y, 0, None) / 7)
    edge = np.clip(np.roll(m['band'], 2 * k, 0) - m['band'], 0, 1)
    under += blur(edge, 0.4 * k) * 2
    streak = n(0.6 * k)
    streak = blur(streak, 0.3 * k)
    streak = np.cumsum(streak, 0) / np.sqrt(np.arange(1, h + 1))[:, None]
    field = n(2.5 * k) + 0.45 * n(0.6 * k) + 1.6 * np.tanh(under) + 0.5 * streak / (streak.std() + 1e-9)
    rust = np.zeros((h, w), np.float32)
    for p in PARTS:
        here = (own == p)
        if not here.any() or p in ('slot', 'rivet', 'arch') or p not in alone:
            continue
        frac = rusty[here].mean()
        inside = alone[p] > 0.5
        if frac <= 0.002 or not inside.any():
            continue
        t = np.quantile(field[inside], 1 - frac)
        rust = np.maximum(rust, np.clip((field - t) / 0.35, 0, 1) * alone[p])
    reds = a[rusty]
    if len(reds) >= 4:
        tone = through(ramp(reds, 8), np.clip(0.5 + 0.25 * n(0.5 * k) + 0.2 * grain, 0, 1))
        colour = colour * (1 - rust[..., None]) + tone * rust[..., None]
    # The maps.
    worn = np.clip(0.5 * np.tanh(cavity) + 0.5 * m['rim'] + 0.6 * m['rivet'], 0, 1)
    rough = np.clip(ROUGH - WORN * worn + 0.05 * grain + RUST_ROUGH * rust, 0.12, 0.9)
    metal = np.clip(1 - 1.1 * rust, 0, 1) * (1 - m['slot'])
    return colour, hgt, rough, metal, mx, my


def owner(m):
    """Which part each texel's colour is read from: the nearest part over it."""
    own = np.full(m['plate'].shape, 'plate', dtype=object)
    for p in reversed(PARTS):
        own[m[p] > 0.5] = p
    return own


def write_maps(out, id, colour, hgt, rough, metal, mx, my):
    at = lambda part: os.path.join(out, f'{id}_{part}.png')
    one = np.ones(hgt.shape, np.float32)
    relief.write(at('albedo'), np.dstack([colour, one]))
    top = float(hgt.max())
    relief.grey(at('height'), np.clip(1 - (top - hgt) / DEEPEST, 0, 1))
    sx = (np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)) / 2 / mx
    sy = (np.roll(hgt, -1, 0) - np.roll(hgt, 1, 0)) / 2 / my
    s = np.minimum(1, relief.STEEPEST / (np.sqrt(sx * sx + sy * sy) + 1e-6))
    nx, ny = -sx * s, sy * s
    n = np.sqrt(nx * nx + ny * ny + 1)
    relief.write(at('normal'), np.dstack([nx / n / 2 + 0.5, ny / n / 2 + 0.5, 1 / n / 2 + 0.5, one]))
    relief.grey(at('occlusion'), 1 - np.clip((blur(hgt, 1.5 * SCALE) - hgt) / 0.003 * 0.35, 0, 0.35))
    relief.grey(at('roughness'), rough)
    relief.grey(at('metal'), metal)


def size(path):
    w, h = subprocess.run(['identify', '-format', '%w %h', path], capture_output=True, text=True, check=True).stdout.split()
    return int(w), int(h)


def block(id, spec, sub, print_):
    m = f'materials/{sub}{id}'
    return f'''[[material]]
texture = "{id}"
{print_}base_color = "{m}_albedo.png"
normal = "{m}_normal.png"
roughness = "{m}_roughness.png"
occlusion = "{m}_occlusion.png"
height = "{m}_height.png"
metal_map = "{m}_metal.png"
brighten = {BRIGHTEN:g}
damp = 0.0
grit = "grit/{GRIT.OF["metal"]}.png"
grit_repeat = [{GRIT.repeats(spec["size"][0])}, {GRIT.repeats(spec["size"][1])}]
author = "Generated by {TOOL}"
tool = "{TOOL}"
license = "CC0-1.0"
'''


def main(args):
    pack, pictures = args[:2]
    era = option(args, '--into', None)
    sub = f'{era}/' if era else ''
    out = os.path.join(pack, 'materials', sub)
    prints = {}
    at = os.path.join(pictures, 'fingerprints.tsv')
    if os.path.exists(at):
        prints = dict(l.rstrip('\n').split('\t')[:2] for l in open(at) if l.strip())
    path = os.path.join(pack, 'manifest.toml')
    blocks = re.split(r'\n(?=\[\[)', open(path).read())
    texture = lambda b: (re.search(r'^texture = "(0x[0-9A-Fa-f]{8})"$', b, re.M) or [None, None])[1]
    where = lambda b: re.search(rf'^base_color = "materials/{re.escape(sub)}[^/"]+"$', b, re.M)
    made = 0
    for id, spec in PICTURES[era].items():
        src = os.path.join(pictures, id + '.png')
        if not os.path.exists(src):
            print(id, 'is not among the pictures; its material is kept')
            continue
        rng = np.random.default_rng(int(id, 16) + (2005 if era else 0))
        write_maps(out, id, *paint(id, spec, src, rng))
        print_ = f'fingerprint = "{prints[id]}"\n' if id in prints else ''
        new = block(id, spec, sub, print_)
        mine = [i for i, b in enumerate(blocks) if b.startswith('[[material]]') and texture(b) == id and where(b)]
        for i in mine:
            # The material this replaces: its pictures go with it.
            for f in re.findall(r'"(materials/[^"]+\.png)"', blocks[i]):
                if f not in new and os.path.exists(os.path.join(pack, f)):
                    os.remove(os.path.join(pack, f))
        if mine:
            blocks[mine[0]] = new
            for i in reversed(mine[1:]):
                del blocks[i]
        else:
            # After this era's other chest pictures, else at the end.
            near = [i for i, b in enumerate(blocks) if b.startswith('[[material]]') and texture(b) in PICTURES[era] and where(b)]
            blocks.insert(near[-1] + 1 if near else len(blocks), new)
        made += 1
    open(path, 'w').write('\n'.join(blocks))
    print(made, 'chest pictures of', len(PICTURES[era]))


if __name__ == '__main__':
    main(sys.argv[1:])
