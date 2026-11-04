# New rock pictures: faceted, fractured stone made from noise, coloured to match the retail picture
# by its histogram and a ramp of its colours by brightness, so no retail pixel is copied. Each comes
# with its normal, height, occlusion and roughness, made from the same shape as its colour.
# rockgen.py <pack folder> <retail pngs>
import os, re, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import grit as GRIT
PACK, SRC = sys.argv[1:3]
N = 512
# picture: repeat in metres; grain angle and stretch; facets a side and how strong; how much of its
# broken fractures, dark veins and strata; depth of its relief, metres
ROCKS = {
    '0x05000FF3': dict(repeat=3.1, angle=8, stretch=1.5, plates=9, facet=1.0, crack=0.8, veins=0.8, strata=0.0, depth=0.1, grit='rock', floor=10),
    '0x0500122C': dict(repeat=3.1, angle=40, stretch=1.6, plates=6, facet=0.6, crack=0.3, veins=0.3, strata=0.5, depth=0.07, grit='rock', floor=12, factor=(0.72, 0.72, 0.72)),
    '0x0500123D': dict(repeat=2.0, angle=-10, stretch=1.5, plates=12, facet=1.2, crack=0.7, veins=0.7, strata=0.0, depth=0.08, grit='rock'),
    # For the boulders on the atlas 0x05002C11, whose left half alone is rock: a picture for their models.
    '0x05002C11_stone': dict(source='0x05002C11', crop=0.5, model_only=True, repeat=10.0, angle=0, stretch=1.2, depth=0.07, grit='rock', coral=True, factor=(0.6, 0.6, 0.6)),
    # For the snow boulders' models: crags under snow, laid out by height as retail's coordinates expect.
    '0x05002613': dict(model_only=True, repeat=6.2, depth=0.1, grit='rock', snow=True, factor=(0.82, 0.82, 0.84)),
    '0x05000E80': dict(repeat=3.0, angle=35, stretch=1.8, plates=5, facet=0.5, crack=0.2, veins=0.2, strata=0.0, depth=0.11, grit='rock'),
}
def read(path):
    raw = subprocess.run(['magick', path, '-depth', '8', 'rgb:-'], capture_output=True, check=True).stdout
    w, h = map(int, subprocess.run(['identify', '-format', '%w %h', path], capture_output=True, text=True, check=True).stdout.split())
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3).astype(np.float32) / 255
def write(path, a):
    h, w, c = a.shape
    subprocess.run(['magick', '-define', 'png:exclude-chunks=date,time', '-size', f'{w}x{h}', '-depth', '8', 'rgba:-', path], input=(np.clip(np.nan_to_num(a), 0, 1) * 255 + 0.5).astype(np.uint8).tobytes(), check=True)
def spectral(rng, beta, lo=0.0, hi=1e9, angle=0.0, stretch=1.0):
    """Noise that repeats, its power falling with frequency, between bands in cycles a picture;
    `stretch` long along `angle` degrees."""
    f = np.fft.fftfreq(N) * N
    fy, fx = np.meshgrid(f, f, indexing='ij')
    c, s = np.cos(np.radians(angle)), np.sin(np.radians(angle))
    along, across = fx * c + fy * s, -fx * s + fy * c
    r = np.hypot(along * stretch ** 0.5, across / stretch ** 0.5)
    amp = np.where((r >= max(lo, 1)) & (r <= hi), 1 / np.maximum(r, 1) ** (beta / 2), 0)
    a = np.fft.ifft2(np.fft.fft2(rng.standard_normal((N, N))) * amp).real
    return ((a - a.mean()) / (a.std() + 1e-9)).astype(np.float32)
def plates(rng, count, warp):
    """Worley cells that repeat: each its own tilted facet, with the distance to its edge."""
    y, x = np.mgrid[0:N, 0:N] / N
    x = (x + warp[0]) % 1
    y = (y + warp[1]) % 1
    seeds = rng.random((count * count, 2))
    seeds = (seeds + np.stack(np.meshgrid(np.arange(count), np.arange(count)), -1).reshape(-1, 2)) / count
    tilt = rng.normal(0, 1, (len(seeds), 3))
    first = np.full((N, N), 9.0, np.float32); second = first.copy()
    which = np.zeros((N, N), np.int32)
    dxs = np.zeros((N, N), np.float32); dys = dxs.copy()
    for i, s in enumerate(seeds):
        dx = ((x - s[0] + 0.5) % 1) - 0.5
        dy = ((y - s[1] + 0.5) % 1) - 0.5
        d = np.hypot(dx, dy).astype(np.float32)
        closer = d < first
        second = np.where(closer, first, np.minimum(second, d))
        dxs = np.where(closer, dx, dxs); dys = np.where(closer, dy, dys)
        which = np.where(closer, i, which); first = np.where(closer, d, first)
    facet = tilt[which, 0] * 0.25 + (tilt[which, 1] * dxs + tilt[which, 2] * dys) * count * 0.8
    edge = (second - first) * count
    return facet.astype(np.float32), edge.astype(np.float32), tilt[which, 0].astype(np.float32)
def match(a, source):
    """`a`'s values moved onto the histogram of `source`."""
    order = np.argsort(a, axis=None)
    out = np.empty(a.size, np.float32)
    out[order] = np.interp(np.linspace(0, 1, a.size), np.linspace(0, 1, source.size), np.sort(source, axis=None))
    return out.reshape(a.shape)
def ramp(retail, L):
    """Colour by brightness: retail's mean colour in each band of its brightness."""
    r = (retail * [0.3, 0.59, 0.11]).sum(-1)
    edges = np.quantile(r, np.linspace(0, 1, 25))
    mids, cols = [], []
    for a, b in zip(edges, edges[1:]):
        m = (r >= a) & (r <= b)
        if m.any():
            mids.append(r[m].mean()); cols.append(retail[m].mean(0))
    return np.stack([np.interp(L, mids, [c[i] for c in cols]) for i in range(3)], -1).astype(np.float32)
def snow(id, s, rng):
    """Snow to the top, crags in the middle under caps with blue ice in their shadow, then drifts
    and a rim of ice at the foot, in retail's colours for each."""
    retail = read(os.path.join(SRC, id + '.png'))
    bright = (retail * [0.3, 0.59, 0.11]).sum(-1)
    dark = retail[bright < 0.5]
    blue = retail[(retail[..., 2] - retail[..., 0]) > 0.25]
    rim = retail[int(retail.shape[0] * 0.965):].reshape(-1, 3).mean(0)
    # Warm, to sit with the ground's snow as the world draws it, rather than retail's blue white.
    white = np.array([1.0, 0.965, 0.905], np.float32)
    v = (np.mgrid[0:N, 0:N][0] + 0.5) / N
    warp = spectral(rng, 3.0, 1, 14) * 0.03, spectral(rng, 3.0, 1, 14) * 0.03
    big, bige, bigt = plates(rng, 6, warp)
    small, smalle, smallt = plates(rng, 18, (warp[1], warp[0]))
    lumps = spectral(rng, 2.4, 2, 40)
    fine = spectral(rng, 1.5, 30, 200)
    crag = 0.5 * big + 0.3 * small + 0.25 * lumps + 0.03 * fine - 0.5 * np.exp(-(bige / 0.04) ** 2)
    lo, hi = np.percentile(crag, [1, 99])
    crag = np.clip((crag - lo) / (hi - lo), 0, 1).astype(np.float32)
    # How much snow each height holds, with heaped caps where the rock's own bumps stand up.
    want = np.interp(v, [0, 0.12, 0.3, 0.5, 0.68, 0.8, 1], [1.1, 0.7, 0.02, -0.28, -0.28, 0.7, 1.2])
    heap = spectral(rng, 2.8, 3, 18) * 0.42 + (crag - 0.5) * 0.25
    depth = want + heap
    cover = np.clip(depth * 3 + 0.5, 0, 1).astype(np.float32)
    cover = cover * cover * (3 - 2 * cover)
    # Blue ice in the shadow under each cap, as the picture's rows run down the rock.
    halo = np.clip(sum(np.roll(cover, r, axis=0) for r in (8, 16, 24)) / 3 - cover, 0, 1)[..., None]
    bright_dark = (dark * [0.3, 0.59, 0.11]).sum(-1)
    L = match(0.8 * (crag - 0.5) + 0.25 * bigt + 0.1 * fine, np.clip(bright_dark, *np.percentile(bright_dark, [15, 100])))
    colour = ramp(dark, L)
    colour = colour * (1 - halo * 0.85) + blue.mean(0) * halo * 0.85
    shade = 0.86 + 0.14 * np.clip(0.5 + 0.5 * lumps, 0, 1)[..., None]
    drifted = np.clip(white * shade, 0, 1)
    # Blue flecks low in the drifts, and a band of ice through them.
    flecks = np.clip(spectral(rng, 2.6, 6, 40) * 0.5 + 0.1, 0, 1)[..., None] * np.interp(v, [0.72, 0.8, 0.94], [0, 1, 1])[..., None]
    ice = np.clip(1 - np.abs(v - 0.86 + 0.012 * spectral(rng, 2.6, 2, 16)) / 0.02, 0, 1)[..., None]
    tint = np.clip(flecks * 0.14 + ice * 0.5, 0, 1)
    drifted = drifted * (1 - tint) + blue.mean(0) * tint
    colour = colour * (1 - cover[..., None]) + drifted * cover[..., None]
    band = np.clip((v - 0.945) / 0.015, 0, 1)[..., None]
    colour = colour * (1 - band) + rim * band
    H = np.clip((0.25 + 0.55 * crag) * (1 - cover) + cover * (0.85 + 0.1 * lumps), 0, 1).astype(np.float32)
    H = H * (1 - band[..., 0]) + 0.75 * band[..., 0]
    finish(id, s, colour, H)
def lit(s):
    """How much to dim a picture in its own sRGB, for a brightness factor given in linear light."""
    return np.array(s.get('factor', (0.84, 0.82, 0.8)), np.float32) ** (1 / 2.2)
def finish(id, s, colour, H):
    colour = colour * lit(s)
    one = np.ones((N, N), np.float32)
    out = os.path.join(PACK, 'materials')
    write(f'{out}/{id}_albedo.png', np.dstack([colour, one]))
    k = s['depth'] / (s['repeat'] / N)
    dx = (np.roll(H, -1, 1) - np.roll(H, 1, 1)) / 2
    dy = (np.roll(H, -1, 0) - np.roll(H, 1, 0)) / 2
    nx, ny = -dx * k, dy * k
    l = np.sqrt(nx * nx + ny * ny + 1)
    write(f'{out}/{id}_normal.png', np.dstack([nx / l / 2 + 0.5, ny / l / 2 + 0.5, 1 / l / 2 + 0.5, one]))
def coral(id, s, rng):
    """Pitted coral: retail's grey and its moss, by their colours and brightness."""
    retail = read(os.path.join(SRC, s['source'] + '.png'))
    retail = retail[:, :int(retail.shape[1] * s['crop'])]
    half = retail.shape[0] // 2
    # Dense irregular pits, about ten pixels apart: the low places of a narrow band of noise.
    pits = spectral(rng, 0.6, 26, 62)
    pits = pits + 0.45 * spectral(rng, 1.0, 10, 26)
    sunk = np.clip((-pits - 0.25) / 0.45, 0, 1) ** 1.3
    lumps = spectral(rng, 2.4, 3, 30)
    fine = spectral(rng, 1.4, 60, 220)
    H = np.clip(0.72 + 0.12 * lumps + 0.03 * fine - 0.62 * sunk, 0, 1).astype(np.float32)
    tone = 0.25 * lumps + 0.3 * fine - 2.2 * sunk
    bright = (retail * [0.3, 0.59, 0.11]).sum(-1)
    L = match(tone, bright)
    # Moss in drifts, as the boulders map this picture evenly.
    drift = spectral(rng, 2.6, 2, 14) * 0.5 + spectral(rng, 1.6, 12, 60) * 0.3
    moss = np.clip((drift + 0.05) * 1.6, 0, 0.85)
    colour = ramp(retail[:half], L) * (1 - moss[..., None]) + ramp(retail[half:], L) * moss[..., None]
    grass = np.clip(fine - 0.4, 0, 1)[..., None] * moss[..., None] * np.array([-0.03, 0.12, -0.04], np.float32)
    colour = colour + grass
    finish(id, s, colour, H)
def make(id, s, rng):
    if s.get('coral'):
        return coral(id, s, rng)
    if s.get('snow'):
        return snow(id, s, rng)
    retail = read(os.path.join(SRC, s.get('source', id) + '.png'))
    retail = retail[:, :int(retail.shape[1] * s.get('crop', 1))]
    grain = dict(angle=s['angle'], stretch=s['stretch'])
    warp = spectral(rng, 3.0, 1, 14) * 0.03, spectral(rng, 3.0, 1, 14) * 0.03
    big, bige, bigt = plates(rng, s['plates'], warp)
    small, smalle, smallt = plates(rng, s['plates'] * 3, (warp[1] * 1.5, warp[0] * 1.5))
    lumps = spectral(rng, 2.4, 2, 50, **grain)
    fine = spectral(rng, 1.4, 40, 220, **grain)
    ridged = 1 - np.abs(spectral(rng, 2.2, 4, 90, **grain))
    ridged = np.clip(ridged, 0, 1) ** 3
    y = np.mgrid[0:N, 0:N][0] / N
    strata = np.sin((y * 11 + warp[0] * 12 + spectral(rng, 3.0, 1, 6) * 0.1) * 2 * np.pi).astype(np.float32)
    # Fractures only here and there, never a whole net of them.
    where = np.clip((spectral(rng, 2.6, 2, 20) + 0.1) * 1.4, 0, 1)
    cracks = where * np.exp(-(bige / 0.035) ** 2) + where * 0.6 * np.exp(-(smalle / 0.05) ** 2)
    veins = np.clip((spectral(rng, 2.4, 3, 30, **grain) + 0.2) * 1.2, 0, 1) * ridged
    h = (0.52 * s['facet'] * big + 0.30 * s['facet'] * small + 0.26 * lumps + 0.10 * ridged
         + 0.2 * s['strata'] * strata + 0.02 * fine)
    h = h - s['crack'] * 0.8 * cracks - s['veins'] * 0.25 * veins
    lo, hi = np.percentile(h, [1, 99])
    H = np.clip((h - lo) / (hi - lo), 0, 1).astype(np.float32)
    # Colour mottled for itself, as stone is, with the shape only part of it.
    mott = spectral(rng, 1.7, 3, 160, **grain)
    blotch = spectral(rng, 2.6, 2, 24, **grain)
    tone = (0.34 * mott + 0.24 * blotch + 0.5 * (H - 0.5) + 0.14 * s['facet'] * bigt + 0.14 * s['facet'] * smallt
            - 0.6 * s['veins'] * veins - 0.8 * s['crack'] * cracks + 0.15 * s['strata'] * strata)
    if s.get('spots'):
        tone = tone * 0.5 - s['spots'] * 1.6 * np.clip(spectral(rng, 1.8, 14, 40) - 0.3, 0, 1)
    # Retail's rare darkest and palest pixels stay out: they read as burns on a whole rock.
    bright = (retail * [0.3, 0.59, 0.11]).sum(-1)
    L = match(tone, np.clip(bright, *np.percentile(bright, [s.get('floor', 7), 99])))
    colour = ramp(retail, L)
    drift = spectral(rng, 2.8, 1, 16)[..., None] * 0.012
    colour = (colour + drift * np.array([1, 0.2, -0.8], np.float32)) * lit(s)
    if s.get('moss'):
        colour = colour + np.clip(spectral(rng, 2.4, 3, 30) - 0.5, 0, 1)[..., None] * s['moss'] * np.array([-0.08, 0.1, -0.08], np.float32) * (0.4 + colour.mean(-1, keepdims=True))
    one = np.ones((N, N), np.float32)
    out = os.path.join(PACK, 'materials'); os.makedirs(out, exist_ok=True)
    write(f'{out}/{id}_albedo.png', np.dstack([colour, one]))
    k = s['depth'] / (s['repeat'] / N)
    dx = (np.roll(H, -1, 1) - np.roll(H, 1, 1)) / 2
    dy = (np.roll(H, -1, 0) - np.roll(H, 1, 0)) / 2
    nx, ny = -dx * k, dy * k
    l = np.sqrt(nx * nx + ny * ny + 1)
    write(f'{out}/{id}_normal.png', np.dstack([nx / l / 2 + 0.5, ny / l / 2 + 0.5, 1 / l / 2 + 0.5, one]))
    # Shallow, so its walk through the depth casts no black specks of self-shadow.
    d = 0.62 + 0.38 * H
    write(f'{out}/{id}_height.png', np.dstack([d, d, d, one]))
    o = 1 - np.clip(cracks * 0.4 + (0.5 - H) * 0.4, 0, 0.6)
    write(f'{out}/{id}_occlusion.png', np.dstack([o, o, o, one]))
    r = np.clip(0.86 + 0.08 * fine - 0.1 * H, 0, 1)
    write(f'{out}/{id}_roughness.png', np.dstack([r, r, r, one]))
def manifest():
    path = os.path.join(PACK, 'manifest.toml')
    t = open(path).read()
    for id, s in ROCKS.items():
        if s.get('model_only'):
            continue
        t = re.sub(r'\[\[material\]\]\ntexture = "' + id + r'"\n.*?(?=\n\[\[|\Z)', '', t, flags=re.S)
        n = GRIT.repeats(s['repeat'])
        t = t.rstrip() + f'''

[[material]]
texture = "{id}"
base_color = "materials/{id}_albedo.png"
normal = "materials/{id}_normal.png"
roughness = "materials/{id}_roughness.png"
occlusion = "materials/{id}_occlusion.png"
height = "materials/{id}_height.png"
damp = 0.0
grit = "grit/{s['grit']}.png"
grit_repeat = [{n}, {n}]
author = "Generated by rockgen.py"
tool = "rockgen.py"
license = "CC0-1.0"
'''
    open(path, 'w').write(t)
rng = np.random.default_rng(31)
for id, s in ROCKS.items():
    make(id, s, rng)
    print(id)
manifest()
