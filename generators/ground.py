# Writes new ground pictures for the Launch (1999) files' terrain types, coloured as that era's
# ground: grass blades, leaf litter, pebbles, rock, strata, sand, snow, ice, cobbles. Each is made
# here from noise and shapes alone; only its colours come from the era's own picture, measured
# into a table.
# ground.py measure <the player's pictures (pyreal-art pictures)> <table>
#   each picture's colour groups (k-means, up to three) with their share and 16 colours from dark
#   to light, a line each: id, group, share, colours; and its fingerprint (from fingerprints.tsv
#   beside the pictures), a line each: id, "fingerprint", the fingerprint.
# ground.py make <table> <pack folder> [name ...] [--side <texels>] [--preview <png> <pictures>]
#   each ground's albedo, normal, height, roughness and occlusion in ground/launch/, square and
#   tiling, north up, and a [[terrain]] for it in the manifest naming the era picture's
#   fingerprint, so only a world whose region lays that picture draws it. --preview lays each
#   beside the era's picture, lit from a high sun.
import os, re, subprocess, sys
import numpy as np

SIDE = 1024
TOOL = 'ground.py'

# name, the terrain types it is drawn for (32 the road), the era picture its colours come from,
# its family, metres a repeat, and the family's settings.
GROUNDS = [
    ('barren-rock', [0, 24, 27, 28, 29, 30, 31], '0x0500145C', 'rock', 8.0, dict(facets=420, grit=0.5, rubble=0.7)),
    ('grassland', [1], '0x05001459', 'grass', 4.0, dict(blades=70000, length=26, lean=0.9)),
    ('ice', [2], '0x05001468', 'ice', 8.0, dict()),
    ('lush-grass', [3], '0x05001456', 'grass', 4.0, dict(blades=95000, length=32, lean=0.8)),
    ('marsh', [4], '0x05001467', 'marsh', 5.0, dict()),
    ('mud', [5], '0x05001462', 'mud', 5.0, dict()),
    ('packed-dirt', [7], '0x05001465', 'packed', 5.0, dict()),
    ('patchy-dirt', [8], '0x0500145B', 'soil', 5.0, dict(pebbles=2600, tufts=0.18)),
    ('patchy-grass', [9], '0x05001457', 'grass', 4.0, dict(blades=55000, length=24, lean=0.9, bare=0.3)),
    ('yellow-sand', [10], '0x0500145D', 'sand', 6.0, dict(waves=11)),
    ('grey-sand', [11], '0x0500145F', 'sand', 6.0, dict(waves=7)),
    ('stony-sand', [12], '0x0500145E', 'soil', 5.0, dict(pebbles=900, rings=True)),
    ('sedimentary-rock', [13], '0x050014A7', 'strata', 8.0, dict(facets=160, grit=0.3, rubble=0.45)),
    ('semi-barren-rock', [14], '0x0500145A', 'rock', 8.0, dict(facets=220, grit=0.3, rubble=0.5, leaves=2500)),
    ('snow', [15], '0x05001464', 'snow', 8.0, dict()),
    ('forest-floor', [21], '0x05001466', 'litter', 4.0, dict(leaves=9000)),
    ('sea-slime', [23], '0x05001827', 'slime', 5.0, dict()),
    ('volcanic-rock', [25], '0x0500181F', 'cinder', 6.0, dict()),
    ('red-rock', [26], '0x05001820', 'rock', 8.0, dict(facets=380, grit=0.6, rubble=0.7)),
    ('cobbles', [32], '0x05001458', 'cobble', 3.0, dict(stones=260)),
]


def read(path):
    raw = subprocess.run(['magick', path, '-depth', '8', 'rgb:-'], capture_output=True, check=True).stdout
    w, h = map(int, subprocess.run(['identify', '-format', '%w %h', path], capture_output=True, text=True, check=True).stdout.split())
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3).astype(np.float32) / 255


def write(path, a):
    a = a if a.ndim == 3 else np.dstack([a, a, a])
    h, w, c = a.shape
    subprocess.run(['magick', '-define', 'png:exclude-chunks=date,time', '-size', f'{w}x{h}', '-depth', '8', f'{"rgb" if c == 3 else "rgba"}:-', path],
                   input=(np.clip(np.nan_to_num(a), 0, 1) * 255 + 0.5).astype(np.uint8).tobytes(), check=True)


def luma(c):
    return (c * np.array([0.3, 0.59, 0.11], np.float32)).sum(-1)


# Measuring.

def groups(px, rng, most=3, least=0.02):
    """k-means colour groups of `px` (n by 3), largest first: (share, 16 colours dark to light)."""
    k = most
    centres = px[rng.choice(len(px), k, replace=False)]
    for _ in range(30):
        who = ((px[:, None] - centres[None]) ** 2).sum(-1).argmin(1)
        centres = np.array([px[who == i].mean(0) if (who == i).any() else centres[i] for i in range(k)])
    out = []
    for i in range(k):
        mine = px[who == i]
        share = len(mine) / len(px)
        if share < least:
            continue
        order = mine[np.argsort(luma(mine))]
        q = ((np.arange(16) + 0.5) / 16 * len(order)).astype(int)
        out.append((share, order[q]))
    return sorted(out, key=lambda g: -g[0])


def measure(src, table):
    rng = np.random.default_rng(1)
    lines = ['# The colours of the Launch ground pictures, measured by ground.py from the player\'s own files:',
             '# a line per colour group: picture, group (0 the largest), its share, 16 colours dark to light.']
    for _, _, pic, *_ in GROUNDS:
        if any(l.startswith(pic) for l in lines):
            continue
        px = read(os.path.join(src, pic + '.png')).reshape(-1, 3)
        for g, (share, cols) in enumerate(groups(px, rng)):
            hexes = ' '.join('%02X%02X%02X' % tuple((c * 255 + 0.5).astype(int)) for c in cols)
            lines.append(f'{pic}\t{g}\t{share:.3f}\t{hexes}')
    prints = dict(l.rstrip('\n').split('\t')[:2] for l in open(os.path.join(src, 'fingerprints.tsv')) if l.strip())
    for pic in dict.fromkeys(g[2] for g in GROUNDS):
        lines.append(f'{pic}\tfingerprint\t{prints[pic]}')
    open(table, 'w').write('\n'.join(lines) + '\n')


def colours_of(table):
    out = {}
    for l in open(table):
        if l.startswith('#') or not l.strip():
            continue
        pic, g, share, hexes = (l.rstrip('\n').split('\t') + [''])[:4]
        if g == 'fingerprint':
            continue
        cols = np.array([[int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)] for h in hexes.split()], np.float32)
        out.setdefault(pic, []).append((float(share), cols))
    return out


def prints_of(table):
    return {f[0]: f[2] for f in (l.rstrip('\n').split('\t') for l in open(table)) if len(f) > 2 and f[1] == 'fingerprint'}


# Shapes. Every field tiles: noise is filtered in frequency, shapes wrap around the edges.

N = SIDE


def blur(a, s):
    fy = np.fft.fftfreq(a.shape[0])[:, None]; fx = np.fft.rfftfreq(a.shape[1])[None, :]
    return np.fft.irfft2(np.fft.rfft2(a) * np.exp(-2 * (np.pi * s) ** 2 * (fx * fx + fy * fy)), s=a.shape)


def noise(rng, s):
    a = blur(rng.standard_normal((N, N)), s)
    return a / (a.std() + 1e-9)


def unit(a):
    lo, hi = np.percentile(a, [0.5, 99.5])
    return np.clip((a - lo) / (hi - lo + 1e-9), 0, 1)


def strokes(rng, count, length, width, lean, angle=None, spread=0.6, bend=0.25):
    """Blades: thin curved strokes rising from root to tip. Answers the height (the tallest stroke
    over each texel, tip highest) and each texel's stroke shade (0 to 1)."""
    angle = rng.uniform(0, 2 * np.pi) if angle is None else angle
    a = angle + rng.normal(0, spread, count)
    L = length * rng.uniform(0.55, 1.3, count)
    rx, ry = rng.uniform(0, N, count), rng.uniform(0, N, count)
    curl = rng.normal(0, bend, count)
    tall = rng.uniform(0.6, 1.0, count) * lean
    shade = rng.uniform(0, 0.999, count)
    steps = int(length * 1.6)
    t = np.linspace(0, 1, steps)[None, :]
    th = a[:, None] + curl[:, None] * t
    x = rx[:, None] + np.cumsum(np.cos(th), 1) * (L[:, None] / steps)
    y = ry[:, None] + np.cumsum(np.sin(th), 1) * (L[:, None] / steps)
    h = (0.25 + 0.75 * t) * tall[:, None]
    key = np.floor(h * 1000) / 1000 + shade[:, None] * 1e-4
    best = np.zeros(N * N)
    for dx in range(-(width // 2), width - width // 2):
        for dy in (0,) if width < 3 else (-1, 0):
            ix = (np.round(x).astype(int) + dx) % N
            iy = (np.round(y).astype(int) + dy) % N
            np.maximum.at(best, (iy * N + ix).ravel(), key.ravel())
    best = best.reshape(N, N)
    hq = np.floor(best * 1000) / 1000
    return hq, np.clip((best - hq) * 1e4, 0, 1)


def stamps(rng, count, radius, shape='dome', aspect=1.0, turn=None):
    """Pebbles, leaves or stones laid at random, wrapping: the height of the highest over each
    texel and its own shade."""
    r = radius * rng.uniform(0.6, 1.4, count)
    cx, cy = rng.uniform(0, N, count), rng.uniform(0, N, count)
    th = rng.uniform(0, np.pi, count) if turn is None else np.full(count, turn)
    lift = rng.uniform(0.5, 1.0, count)
    shade = rng.uniform(0, 0.999, count)
    best = np.zeros(N * N)
    side = int(np.ceil(radius * 1.4 * max(aspect, 1))) + 1
    g = np.arange(-side, side + 1)
    gx, gy = np.meshgrid(g, g)
    gx, gy = gx.ravel()[None, :], gy.ravel()[None, :]
    c, s = np.cos(th)[:, None], np.sin(th)[:, None]
    u = (gx * c + gy * s) / r[:, None]
    v = (-gx * s + gy * c) / (r[:, None] / aspect)
    d = u * u + v * v
    inside = d < 1
    if shape == 'dome':
        h = np.sqrt(np.clip(1 - d, 0, 1))
    elif shape == 'leaf':
        h = 0.6 + 0.4 * (1 - np.abs(v)) - 0.15 * np.abs(u)
    else:
        h = np.clip(1 - d ** 3, 0, 1)
    h = h * lift[:, None]
    key = np.floor(h * 1000) / 1000 + shade[:, None] * 1e-4
    ix = (np.round(cx)[:, None].astype(int) + gx) % N
    iy = (np.round(cy)[:, None].astype(int) + gy) % N
    np.maximum.at(best, (iy * N + ix)[inside], key[inside])
    best = best.reshape(N, N)
    hq = np.floor(best * 1000) / 1000
    return hq, np.clip((best - hq) * 1e4, 0, 1)


def cells(rng, count, wobble=0.015):
    """Wrapping Voronoi cells: the distance to the nearest seed, to the next, which seed, and each
    texel's offset from its seed (east, north) in texels."""
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32) / N
    w = (blur(rng.standard_normal((N, N)), 14), blur(rng.standard_normal((N, N)), 14))
    wob = wobble / (w[0].std() + 1e-6)
    xw, yw = xx + w[0] * wob, yy + w[1] * wob
    sx, sy = rng.random(count).astype(np.float32), rng.random(count).astype(np.float32)
    best = np.full((N, N), 9.0, np.float32); second = best.copy(); who = np.zeros((N, N), np.int32)
    for k in range(count):
        dx = np.abs(xw - sx[k]); dx = np.minimum(dx % 1, 1 - dx % 1)
        dy = np.abs(yw - sy[k]); dy = np.minimum(dy % 1, 1 - dy % 1)
        d = dx * dx + dy * dy
        nearer = d < best
        second = np.where(nearer, best, np.minimum(second, d))
        who = np.where(nearer, k, who); best = np.where(nearer, d, best)
    lx = ((xw - sx[who] + 0.5) % 1 - 0.5) * N
    ly = ((yw - sy[who] + 0.5) % 1 - 0.5) * N
    return np.sqrt(best) * N, np.sqrt(second) * N, who, lx, ly


def ridged(rng, scales):
    """Sharp-crested noise, octave over octave."""
    out = np.zeros((N, N))
    for i, s in enumerate(scales):
        out += (1 - np.abs(noise(rng, s))) ** 2 * 0.6 ** i
    return unit(out)


# Families: each answers height (0 to 1), a shade for the colour within a group, the groups it
# places itself (green, warm, dark or light: where each shows most), and roughness.

def grass(rng, p):
    soil = 0.25 * unit(noise(rng, 6)) + 0.1 * unit(noise(rng, 1.2))
    h, sh = strokes(rng, p['blades'], p['length'], 2, p['lean'])
    if p.get('bare'):
        gaps = unit(noise(rng, 60)) < p['bare']
        h = np.where(gaps & (unit(noise(rng, 3)) > 0.35), 0, h)
    top = np.maximum(h, soil * 0.3)
    shade = np.where(h > soil * 0.3, 0.3 + 0.7 * sh * (0.4 + 0.6 * h / (h.max() + 1e-6)), soil * 0.6)
    # Dry blades, scattered in loose clumps.
    dry = np.where(h > soil * 0.3, 0.5 * sh + unit(noise(rng, 50)), -1)
    return blur(top, 0.6), blur(shade, 0.5), ({'warm': 1 - top + 0.2 * unit(noise(rng, 30))} if p.get('bare') else {'warm': dry}), 0.9


def litter(rng, p):
    base = 0.3 * unit(noise(rng, 5)) + 0.1 * unit(noise(rng, 1.0))
    h, sh = stamps(rng, p['leaves'], 9, 'leaf', aspect=2.2)
    twigs, tsh = strokes(rng, 1500, 40, 2, 0.5, spread=3.0, bend=0.6)
    top = np.maximum(np.maximum(base * 0.4, h * 0.8), twigs * 0.9)
    shade = np.where(h * 0.8 >= np.maximum(base * 0.4, twigs * 0.9), sh, np.where(twigs > 0, 0.2 + 0.3 * tsh, base))
    return blur(top, 0.6), shade, {'warm': sh * (h > 0) + 0.3 * unit(noise(rng, 50))}, 0.92


def soil(rng, p):
    base = 0.45 * unit(noise(rng, 10)) + 0.3 * unit(noise(rng, 2.5)) + 0.25 * unit(noise(rng, 0.8))
    h, sh = stamps(rng, p['pebbles'], 7 if p.get('rings') else 5, 'dome')
    top = np.maximum(base * 0.5, h * 0.9)
    shade = np.where(h * 0.9 > base * 0.5, 0.4 + 0.6 * sh * h, base * 0.8)
    named = {}
    if p.get('rings'):
        ring = (h > 0.02) & (h < 0.35)
        named['dark'] = ring.astype(np.float32) + 0.2 * unit(noise(rng, 2))
    if p.get('tufts'):
        th, tsh = strokes(rng, int(30000 * p['tufts']), 18, 2, 0.7)
        clump = unit(noise(rng, 25)) > 0.6
        th = th * clump
        top = np.maximum(top, th)
        named['green'] = th + 0.1 * unit(noise(rng, 20))
    return blur(top, 0.6), blur(shade, 0.4), named, 0.93


def packed(rng, p):
    # Trodden earth: long streaks along one way, ruts and a fine crust.
    s = blur(rng.standard_normal((N, N)), 0)
    fy = np.fft.fftfreq(N)[:, None]; fx = np.fft.rfftfreq(N)[None, :]
    streak = np.fft.irfft2(np.fft.rfft2(rng.standard_normal((N, N))) * np.exp(-2 * np.pi ** 2 * ((40 * fx) ** 2 + (1.5 * fy) ** 2)), s=(N, N))
    streak = streak / streak.std()
    h = 0.5 * unit(streak) + 0.3 * unit(noise(rng, 12)) + 0.2 * unit(noise(rng, 1.0))
    return blur(h, 0.5), h, {}, 0.9


def sand(rng, p):
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32) / N
    warp = noise(rng, 90) * 0.08
    phase = p['waves'] * yy + 2 * xx + warp
    rip = np.sin(2 * np.pi * phase) * 0.5 + 0.5
    rip = rip ** 1.6 * (0.6 + 0.4 * unit(noise(rng, 70)))
    h = 0.55 * rip + 0.3 * unit(noise(rng, 30)) + 0.15 * unit(noise(rng, 0.7))
    return blur(h, 0.6), h, {}, 0.85


def rock(rng, p):
    # Angular chunks, each tilted its own way and rough all over, split by thin cracks.
    k = p['facets']
    d1, d2, who, lx, ly = cells(rng, k, wobble=0.004)
    gx, gy = rng.normal(0, 1, k)[who], rng.normal(0, 1, k)[who]
    tilt = (gx * lx + gy * ly) / (N / np.sqrt(k)) * 0.35
    # Rubble: the more of it, the fewer joins stay open; the rest are worn into one another, and
    # loose stones lie over the rough rock.
    w = p.get('rubble', 0.0)
    open_ = unit(noise(rng, 12)) > w * 0.85
    chunk = np.where(open_, np.clip((d2 - d1) / 10, 0, 1) ** 0.5, 1)
    crack = np.where(open_, np.clip((d2 - d1) / 2.5, 0, 1), 1)
    lift = rng.uniform(0.2, 1.0, k)[who]
    rough = ridged(rng, (14, 5, 2))
    stones, _ = stamps(rng, int(5000 * w), 6, 'flat', aspect=1.4)
    stones = stones * (0.5 + 0.5 * unit(noise(rng, 2)))
    h = (1 - w) * (0.45 * lift + tilt) * chunk + w * (0.25 * lift * chunk + 0.6 * rough) + p['grit'] * 0.2 * unit(noise(rng, 1.0))
    h = np.maximum(unit(h) * (0.6 + 0.4 * crack), stones * 0.85)
    named = {}
    if p.get('leaves'):
        lh, lsh = stamps(rng, p['leaves'], 7, 'leaf', aspect=2.0)
        lh = lh * (unit(noise(rng, 40)) > 0.45)
        h = np.maximum(h, lh * 0.9)
        named['green'] = lh + 0.1 * unit(noise(rng, 20))
    shade = 0.6 * unit(h) + 0.4 * rng.uniform(0, 1, k)[who]
    return blur(h, 0.5), shade, named, 0.88


def strata(rng, p):
    # Rock in beds: rubble with its joints and shading running along faint layers.
    h, shade, named, rough = rock(rng, p)
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32) / N
    beds = np.sin(2 * np.pi * (6 * yy + xx + noise(rng, 90) * 0.06)) * 0.5 + 0.5
    return unit(h + 0.25 * beds), 0.75 * shade + 0.25 * beds, named, rough


def snow(rng, p):
    h = 0.6 * unit(noise(rng, 70)) + 0.3 * unit(noise(rng, 18)) + 0.1 * unit(noise(rng, 1.2))
    sparkle = unit(noise(rng, 0.5))
    return blur(h, 0.8), 0.7 * h + 0.3 * sparkle, {}, 0.6


def ice(rng, p):
    d1, d2, *_ = cells(rng, 30, wobble=0.004)
    crack = np.clip((d2 - d1) / 1.5, 0, 1)
    h = 0.6 * unit(noise(rng, 60)) + 0.3 * unit(noise(rng, 12)) - 0.06 * (1 - crack)
    bub, _ = stamps(rng, 1500, 2.5, 'dome')
    shade = 0.6 * unit(noise(rng, 40)) + 0.1 * (1 - crack) + 0.3 * bub
    return blur(h, 0.7), shade, {}, 0.15


def mud(rng, p):
    # Wet clods, large and small, with water lying between them.
    big, bsh = stamps(rng, 1400, 13, 'flat', aspect=1.5)
    small, _ = stamps(rng, 6000, 4, 'flat', aspect=1.3)
    lumpy = unit(noise(rng, 3))
    big, small = big * (0.6 + 0.4 * lumpy), small * (0.6 + 0.4 * lumpy)
    base = 0.3 * unit(noise(rng, 20)) + 0.1 * unit(noise(rng, 1.2))
    h = np.maximum(np.maximum(base * 0.5, big * 0.9), small * 0.6) + 0.08 * unit(noise(rng, 1.5))
    return blur(h, 0.7), 0.6 * h + 0.4 * bsh, {}, 0.5


def marsh(rng, p):
    h0 = 0.5 * unit(noise(rng, 24)) + 0.3 * unit(noise(rng, 6)) + 0.2 * unit(noise(rng, 1.0))
    reeds, rsh = strokes(rng, 22000, 22, 2, 0.8)
    reeds = reeds * (unit(noise(rng, 30)) > 0.5)
    h = np.maximum(h0 * 0.6, reeds)
    shade = np.where(reeds > h0 * 0.6, 0.3 + 0.7 * rsh, h0 * 0.7)
    return blur(h, 0.6), shade, {}, 0.6


def slime(rng, p):
    r = 1 - np.abs(noise(rng, 7))
    r2 = 1 - np.abs(noise(rng, 22))
    h = 0.5 * unit(r) ** 2 + 0.4 * unit(r2) + 0.1 * unit(noise(rng, 1.0))
    return blur(h, 0.6), h, {}, 0.35


def cinder(rng, p):
    base = 0.5 * unit(noise(rng, 8)) + 0.3 * unit(noise(rng, 2.0))
    pits, _ = stamps(rng, 6000, 2.5, 'dome')
    h = base - 0.35 * pits
    d1, d2, *_ = cells(rng, 60, wobble=0.004)
    crack = np.clip((d2 - d1) / 2.5, 0, 1)
    h = h * (0.4 + 0.6 * crack)
    glow = (1 - crack) * (unit(noise(rng, 30)) > 0.55) + 0.3 * pits * (unit(noise(rng, 15)) > 0.7)
    return blur(unit(h), 0.5), unit(h), {'warm': glow + 0.05 * unit(noise(rng, 1))}, 0.85


def cobble(rng, p):
    # Rounded setts in a dark bed, each its own height and wear.
    k = p['stones']
    d1, d2, who, lx, ly = cells(rng, k, wobble=0.006)
    edge = np.clip((d2 - d1 - 3) / 14, 0, 1)
    dome = np.sqrt(edge) * rng.uniform(0.7, 1.0, k)[who]
    h = dome + 0.12 * ridged(rng, (6, 2)) * (edge > 0)
    shade = 0.5 * rng.uniform(0, 1, k)[who] + 0.3 * dome + 0.2 * unit(noise(rng, 3))
    return blur(unit(h), 0.6), shade, {'dark': 1 - edge + 0.1 * unit(noise(rng, 2))}, 0.85


FAMILIES = dict(grass=grass, litter=litter, soil=soil, packed=packed, sand=sand, rock=rock, strata=strata,
                snow=snow, ice=ice, mud=mud, marsh=marsh, slime=slime, cinder=cinder, cobble=cobble)


def pick(groups, kind):
    """The group a family names: the greenest, the warmest, the darkest or the lightest."""
    means = [c.mean(0) for _, c in groups]
    score = {'green': lambda m: m[1] - max(m[0], m[2]), 'warm': lambda m: m[0] - m[2] + 0.5 * (m[0] - m[1]),
             'dark': lambda m: -luma(m), 'light': lambda m: luma(m)}[kind]
    return int(np.argmax([score(m) for m in means]))


def colour(h, shade, named, groups, rng):
    """Each texel's colour group and its colour within the group. A group a family names shows
    where its field is highest, at the group's own share; the rest lie by height, the darker in
    the hollows. Within a group, colour follows the rank of the shade."""
    which = np.full(h.shape, -1, np.int32)
    total = 1.0
    for kind, field in named.items():
        g = pick(groups, kind)
        if (which == g).any() or len(groups) < 2:
            continue
        free = which < 0
        share = groups[g][0] / total
        cut = np.quantile(field[free], 1 - share)
        which[free & (field >= cut)] = g
        total -= groups[g][0]
    rest = [g for g in sorted(range(len(groups)), key=lambda g: luma(groups[g][1].mean(0))) if not (which == g).any()]
    free = which < 0
    f = h + 0.25 * unit(noise(rng, 2)) + 0.25 * unit(noise(rng, 18))
    cuts = np.cumsum([groups[g][0] for g in rest]) / sum(groups[g][0] for g in rest)
    q = np.argsort(np.argsort(f[free])) / max(1, free.sum() - 1)
    which[free] = np.array(rest)[np.searchsorted(cuts[:-1], q, side='right')]
    out = np.zeros(h.shape + (3,), np.float32)
    for g, (_, cols) in enumerate(groups):
        m = which == g
        if not m.any():
            continue
        r = np.argsort(np.argsort(shade[m])) / max(1, m.sum() - 1) * 15
        lo = np.floor(r).astype(int); hi = np.minimum(lo + 1, 15); t = (r - lo)[:, None]
        out[m] = cols[lo] * (1 - t) + cols[hi] * t
    return out


def make(table, pack, names, preview=None, pictures=None):
    out = os.path.join(pack, 'ground', 'launch')
    os.makedirs(out, exist_ok=True)
    cols = colours_of(table)
    tiles = []
    for gi, (name, grounds, pic, fam, size, p) in enumerate(GROUNDS):
        if names and name not in names:
            continue
        rng = np.random.default_rng(1999 + gi)
        h, shade, named, rough = FAMILIES[fam](rng, p)
        h = unit(h)
        # A little of the light the era's own pictures were painted with: lit from the north-west.
        lit = unit((np.roll(h, 1, 1) - np.roll(h, -1, 1)) + (np.roll(h, -1, 0) - np.roll(h, 1, 0)))
        shade = 0.7 * unit(shade) + 0.3 * lit
        albedo = colour(h, shade, named, cols[pic], rng)
        # The normal: the height's slope, as deep as its family's shapes stand.
        depth = 6.0
        sx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / 2 * depth
        sy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / 2 * depth
        l = np.sqrt(sx * sx + sy * sy + 1)
        normal = np.dstack([-sx / l * 0.5 + 0.5, sy / l * 0.5 + 0.5, 1 / l * 0.5 + 0.5])
        r = np.clip(rough + 0.08 * (0.5 - h), 0, 1)
        write(f'{out}/{name}_albedo.png', albedo)
        write(f'{out}/{name}_normal.png', normal)
        write(f'{out}/{name}_height.png', h)
        write(f'{out}/{name}_roughness.png', r)
        # Occlusion: dark in what lies below the ground about it, near and broad.
        occ = 1 - np.clip((blur(h, 3) - h) * 2.5 + (blur(h, 16) - h) * 1.2, 0, 0.55)
        write(f'{out}/{name}_occlusion.png', occ)
        print(name, fam, flush=True)
        if preview:
            sun = np.array([0.3, 0.25, 0.92], np.float32)
            n = normal * 2 - 1
            lit = albedo * occ[..., None] * (0.35 + 0.65 * np.clip((n * sun).sum(-1, keepdims=True), 0, 1) / sun[2])
            src = read(os.path.join(pictures, pic + '.png'))
            big = np.repeat(np.repeat(src, 256 // src.shape[0], 0), 256 // src.shape[1], 1)
            tiles.append(np.hstack([big[:256, :256], np.ones((256, 6, 3)) * 0.15, lit[:256, :256], np.ones((256, 6, 3)) * 0.15,
                                    lit[::4, ::4][:256, :256]]))
    entries(pack, prints_of(table))
    if preview:
        rows = [np.hstack(tiles[i:i + 2] + ([np.zeros_like(tiles[0])] if len(tiles[i:i + 2]) < 2 else [])) for i in range(0, len(tiles), 2)]
        write(preview, np.vstack([np.vstack([r, np.ones((8, r.shape[1], 3)) * 0.15]) for r in rows]))


def entries(pack, prints):
    """Each ground's [[terrain]] in the manifest, in place of this tool's earlier ones."""
    path = os.path.join(pack, 'manifest.toml')
    blocks = re.split(r'\n(?=\[\[)', open(path).read())
    mine = lambda b: b.startswith('[[terrain]]') and re.search(rf'^tool = "{TOOL}"$', b, re.M)
    at = next((i for i, b in enumerate(blocks) if mine(b)), None)
    if at is None:
        at = max((i + 1 for i, b in enumerate(blocks) if b.startswith(('[[terrain]]', '[[steep]]'))), default=len(blocks))
    kept = [b for b in blocks[:at] if not mine(b)], [b for b in blocks[at:] if not mine(b)]
    made = []
    for name, grounds, pic, fam, size, p in GROUNDS:
        ground = '"road"' if grounds == [32] else '[' + ', '.join(map(str, grounds)) + ']'
        made.append(f'''[[terrain]]
ground = {ground}
base_color = "ground/launch/{name}_albedo.png"
normal = "ground/launch/{name}_normal.png"
height = "ground/launch/{name}_height.png"
roughness = "ground/launch/{name}_roughness.png"
occlusion = "ground/launch/{name}_occlusion.png"
size = {size}
fingerprint = "{prints[pic]}"
author = "Generated by ground.py"
tool = "{TOOL}"
license = "CC0-1.0"
''')
    text = '\n'.join(kept[0] + made + kept[1])
    open(path, 'w').write(text.rstrip('\n') + '\n')


def option(args, name, default):
    return args[args.index(name) + 1] if name in args else default


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'measure':
        measure(a[1], a[2])
    else:
        if '--side' in a:
            SIDE = N = int(option(a, '--side', SIDE))
        names = [x for x in a[3:] if not x.startswith('--') and x not in (option(a, '--preview', ''), option(a, '--side', ''))]
        pv = a[a.index('--preview') + 1:a.index('--preview') + 3] if '--preview' in a else [None, None]
        make(a[1], a[2], [n for n in names if n not in pv], pv[0], pv[1])
