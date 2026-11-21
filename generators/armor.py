# Armour that is made of what it shows: a [[material]] for each retail picture a suit of armour
# draws on a player, worked out part by part. A picture's parts come from its palette: each range of
# palette entries a clothing table tints on its own is one part (a suit's leather, its studs, its
# belt, the wearer's skin at the neck), and tables/armor.tsv says what each is made of. Quilted
# leather puffs up between sunk seams, plain leather keeps gentle folds and a fine grain, studs are
# domes, a buckle or a band stands proud, chain mail is rings with dark gaps, and plate keeps its
# painted forms; studs, fittings, chain and plate are metal (a metal map), leather and skin are not.
# Each keeps the player's own picture (`keep_retail_picture`): nothing of any picture's pixels goes
# into the pack, only its height, normal, roughness, occlusion and metal maps.
# Needs Python with numpy and scipy, and ImageMagick (`magick`).
# armor.py <pack folder> <the player's pictures> <their palette indices> [--only <id,id>] [--masks <folder>]
# The pictures are pyreal-art pictures' PNGs (with fingerprints.tsv); the indices are each picture's
# <ID>.idx (Pyreal's armor_survey example): its width and height as u32, then a u16 a texel.
import os, re, subprocess, sys
import numpy as np
from scipy import ndimage
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import relief
import fallback as FALLBACK
from masonry import blur
from recipes import crevices
from relief import option

TOOL = 'armor.py'
TABLES = os.path.join(HERE, '..', 'tables')
# What each kind of part is: how much a metal (a stud keeps some of its own painted colour), its roughness, how far it stands above the leather it sits on
# and how deep its own shapes run (retail texels), and how far that is taken into the height map.
KINDS = {
    #          metal rough level shape
    'quilt':   (0, 0.62, 0.0, 1.6),
    'leather': (0, 0.58, 0.0, 0.9),
    'padding': (0, 0.85, 0.0, 1.2),
    'stud':    (0.7, 0.34, 0.6, 1.6),
    'fitting': (0.85, 0.36, 0.5, 0.9),
    'chain':   (0.85, 0.48, 0.0, 0.9),
    'plate':   (0.9, 0.40, 0.3, 1.4),
    'scale':   (0.85, 0.40, 0.0, 1.3),
    'chitin':  (0, 0.32, 0.2, 1.4),
    'fur':     (0, 0.92, 0.0, 1.2),
    'hair':    (0, 0.66, 0.0, 0.0),
    'cloth':   (0, 0.86, 0.0, 1.2),
    'silk':    (0, 0.46, 0.0, 0.8),
    'bone':    (0, 0.58, 0.3, 1.3),
    'skin':    (0, 0.70, 0.0, 0.0),
}
# The share of the height map's range a picture's relief takes: a suit's relief is millimetres deep
# where a wall's is centimetres (the depth mapping's deepest, 12 cm at High, is the map's black).
RANGE = 0.06
# A metal's roughness: how much smoother where the picture paints it worn bright, and the bounds.
BRIGHT, SMOOTHEST, ROUGHEST = 0.14, 0.14, 0.85
# How many times brighter than its picture a metal part is drawn: a metal's own light is dimmed.
BRIGHTEN = {'chain': 2.2, 'plate': 2.0, 'stud': 2.0, 'fitting': 2.0, 'scale': 2.0}
STEEPEST = 2.5
# The most retail texels a clump of a metal range covers and is still a stud.
STUD = 40
# How much busier than its range's middle a texel's fine shading is where mail is chain, not plate.
RINGS = 1.0
# How much bluer than red a texel of the default palette is where cool= takes it (pale padding).
COOL = 0.035
# How far from a reference's colour and busyness a texel may be and still be like it (like=).
LIKE = 5.5


def unit(a):
    return (a - a.mean()) / (a.std() + 1e-5)


def indices(path, w, h):
    """A picture's palette indices, enlarged to the maps' size texel by texel."""
    b = open(path, 'rb').read()
    sw, sh = np.frombuffer(b[:8], '<u4')
    a = np.frombuffer(b[8:], '<u2').reshape(sh, sw)
    ys = (np.arange(h) * sh // h)[:, None]
    xs = (np.arange(w) * sw // w)[None, :]
    return a[ys, xs]


def table():
    """tables/armor.tsv: each picture's suit, its parts by palette range, and its settings."""
    out = {}
    for line in open(os.path.join(TABLES, 'armor.tsv')):
        if line.strip() and not line.startswith('#'):
            id, suit, *rest = line.rstrip('\n').split('\t')
            out[id] = suit, ' '.join(rest).split()
    return out


def looks(a, px):
    """Each texel's local colour and how busy its fine shading is, for like=."""
    L = (a[..., :3] * [0.3, 0.59, 0.11]).sum(-1)
    busy = blur(np.abs(L - blur(L, 1.2 * px)), 2.5 * px) / (blur(L, 2.5 * px) + 0.05)
    return np.dstack([blur(a[..., c], 2.5 * px) for c in range(3)] + [busy * 0.5, np.log(busy + 0.02)])


def parts_of(spec, idx, a, px, load=None):
    """Each texel's kind: by palette range (LO-HI=kind), then rectangles (x,y,w,h=kind, shares of
    the picture), then bright= (kind of the brightest texels of a range, or of all: buckles on a
    strap), then cool= (kind of what the default palette paints bluish grey: padding under plates),
    then like= (kind of what looks like a reference picture or part of one: an untinted suit's chain)."""
    h, w = idx.shape
    kind = np.full((h, w), 'leather', dtype=object)
    L = (a[..., :3] * [0.3, 0.59, 0.11]).sum(-1)
    for s in spec:
        if '=' not in s or s.startswith(('range=', 'depth=')):
            continue
        where, k = s.split('=')
        if k not in KINDS and k not in ('metal', 'mail', 'mailscale'):
            continue
        if ',' in where:
            x, y, rw, rh = map(float, where.split(','))
            kind[round(y * h):round((y + rh) * h), round(x * w):round((x + rw) * w)] = k
        elif '-' in where:
            lo, hi = map(int, where.split('-'))
            kind[(idx >= lo) & (idx < hi)] = k
        elif where == 'all':
            kind[:] = k
    for s in spec:
        # bright=K:LO-HI:Q: the texels of that range lighter than its Q quantile, in clumps.
        if s.startswith('bright='):
            k, rng, q = s[7:].split(':')
            lo, hi = (0, 2048) if rng == 'all' else map(int, rng.split('-'))
            m = (idx >= lo) & (idx < hi)
            if m.any():
                cut = np.quantile(L[m], float(q))
                b = m & (blur(L, 0.6 * px) > cut)
                b = ndimage.binary_opening(b, iterations=max(1, round(0.6 * px)))
                kind[b] = k
    for s in spec:
        # cool=K[:N]: bluish grey in the default palette, in broad patches; N closes gaps that many texels wide (a pattern's pale spots).
        if s.startswith('cool='):
            k, *fill = s[5:].split(':')
            R, B = blur(a[..., 0], 1.5 * px), blur(a[..., 2], 1.5 * px)
            c = (B - R) > COOL
            if fill:
                c = ndimage.binary_closing(c, iterations=max(1, round(float(fill[0]) * px)))
            c = ndimage.binary_opening(c, iterations=max(1, round(1.5 * px)))
            kind[c] = k
    for s in spec:
        # like=K:ID[:x,y,w,h]: texels whose colour and busyness are like that picture's (or that part of it).
        if s.startswith('like=') and load:
            k, ref, *rect = s[5:].split(':')
            ra, rpx = load(ref)
            F = looks(ra, rpx)
            if rect:
                x, y, rw, rh = map(float, rect[0].split(','))
                fh, fw = F.shape[:2]
                F = F[round(y * fh):round((y + rh) * fh), round(x * fw):round((x + rw) * fw)]
            F = F.reshape(-1, F.shape[-1])
            inv = np.linalg.inv(np.cov(F.T) + np.eye(F.shape[1]) * 1e-4)
            d = looks(a, px) - F.mean(0)
            m = np.sqrt(np.einsum('...i,ij,...j->...', d, inv, d)) < LIKE
            m = ndimage.binary_opening(ndimage.binary_closing(m, iterations=round(1.5 * px)), iterations=round(2 * px))
            kind[m] = k
    # mail: plate where the picture is smooth, chain (or scales, for mailscale) where it is busy.
    for auto, small in (('mail', 'chain'), ('mailscale', 'scale')):
        m = kind == auto
        if m.any():
            # How much the shading flickers at the size of a ring, against how light it is there: much on
            # chain (pale rings over dark gaps), little on a plate's smooth curves; parted where the two
            # kinds of texel part best.
            Lr = (a[..., :3] * [0.3, 0.59, 0.11]).sum(-1)
            fine = blur(np.abs(Lr - blur(Lr, 1.2 * px)), 2.0 * px)
            e = np.log(fine + 1e-3) - np.log(blur(Lr, 2.0 * px) + 0.03)
            v = np.sort(e[m])
            best, cut = -1, float(np.median(v))
            for c in np.quantile(v, np.linspace(0.05, 0.95, 37)):
                lo, hi = v[v < c], v[v >= c]
                score = len(lo) * len(hi) * (hi.mean() - lo.mean()) ** 2
                if score > best:
                    best, cut = score, c
            busy = blur((e > cut * RINGS).astype(np.float32), 1.5 * px) > 0.5
            busy = ndimage.binary_opening(ndimage.binary_closing(busy, iterations=round(2 * px)), iterations=round(2 * px))
            kind[m & busy] = small
            kind[m & ~busy] = 'plate'
    # metal: each clump of a metal range a stud where small, a fitting (a band, a buckle) where large.
    m = kind == 'metal'
    if m.any():
        lab, n = ndimage.label(m)
        area = np.asarray(ndimage.sum(m, lab, np.arange(1, n + 1))) / (px * px)
        small = np.concatenate([[False], area < STUD])[lab]
        kind[m & small] = 'stud'
        kind[m & ~small] = 'fitting'
    # unskin: a picture that paints its own parts in the skin entries; its skin comes from like= or a rectangle.
    if 'unskin' not in spec:
        kind[idx < 192] = 'skin'
    return kind


def shape(k, L, px):
    """A part's own shapes from the picture's shading, 0 its lowest and 1 its highest."""
    g = lambda s: blur(L, s * px)
    if k == 'quilt':
        # Pillows of padding between sunk seams: the shading at the size of a diamond.
        s = 0.35 * np.tanh(unit(g(0.6) - g(2))) + 0.9 * np.tanh(unit(g(2) - g(7))) + 0.4 * np.tanh(unit(g(7) - g(20)))
    elif k in ('leather', 'padding'):
        s = 0.25 * np.tanh(unit(g(0.6) - g(2))) + 0.6 * np.tanh(unit(g(2) - g(6))) + 0.6 * np.tanh(unit(g(6) - g(18)))
    elif k == 'cloth':
        # Cloth: soft folds, its painted creases kept; no grain of its own (a picture's dither would read as crinkle).
        s = 0.1 * np.tanh(unit(g(0.8) - g(2))) + 0.6 * np.tanh(unit(g(2) - g(6))) + 0.9 * np.tanh(unit(g(6) - g(18)))
    elif k == 'silk':
        # Silk: smooth, all broad folds.
        s = 0.1 * np.tanh(unit(g(0.6) - g(2))) + 0.4 * np.tanh(unit(g(2) - g(6))) + 0.9 * np.tanh(unit(g(6) - g(20)))
    elif k == 'chain':
        # Rings: what is pale at the size of a ring stands, the dark between them sinks.
        s = 0.9 * np.tanh(1.2 * unit(g(0.4) - g(1.8))) + 0.5 * np.tanh(unit(g(3) - g(14)))
    elif k == 'scale':
        # Scales: each a little plate, larger than a ring, its pale face standing over the shadow below.
        s = 0.8 * np.tanh(unit(g(0.8) - g(3))) + 0.5 * np.tanh(unit(g(3) - g(12)))
    elif k == 'fur':
        # Fur: its strands' fine light over soft tufts.
        s = 0.6 * np.tanh(unit(g(0.4) - g(1.5))) + 0.5 * np.tanh(unit(g(1.5) - g(6)))
    elif k in ('plate', 'fitting', 'stud', 'chitin', 'bone'):
        s = 0.3 * np.tanh(unit(g(0.5) - g(1.6))) + 0.8 * np.tanh(unit(g(1.6) - g(6))) + 0.7 * np.tanh(unit(g(6) - g(20)))
    else:
        s = np.zeros_like(L)
    lo, hi = np.percentile(s, [1, 99])
    return np.clip((s - lo) / (hi - lo + 1e-5), 0, 1)


def domes(mask, px):
    """Each clump of `mask` a dome: highest at its middle, easing to its edge."""
    d = ndimage.distance_transform_edt(mask)
    lab, n = ndimage.label(mask)
    if not n:
        return d.astype(np.float32)
    r = np.asarray(ndimage.maximum(d, lab, np.arange(1, n + 1)), np.float32)
    rad = np.concatenate([[1.0], np.maximum(r, 1.0)])[lab]
    return np.sqrt(np.clip(d / rad, 0, 1)).astype(np.float32)


def flow(L, px):
    """The direction strands run: across the painted light and dark, straight down where nothing says."""
    src = blur(L, 0.6 * px)
    gx, gy = ndimage.sobel(src, 1), ndimage.sobel(src, 0)
    jxx, jxy, jyy = (blur(v, 3 * px) for v in (gx * gx, gx * gy, gy * gy))
    theta = 0.5 * np.arctan2(2 * jxy, jxx - jyy)
    d = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2)
    coh = (d / (jxx + jyy + 1e-9)) ** 2
    wt = np.clip(coh * 4, 0, 1)
    dx, dy = -np.sin(theta) * wt, np.cos(theta) * wt + (1 - wt)
    l = np.sqrt(dx * dx + dy * dy) + 1e-9
    return dx / l, dy / l


def lic(noise, dx, dy, length):
    """Noise smeared along the flow (line integral convolution): strands."""
    h, w = noise.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    acc, wsum = noise.copy(), np.ones_like(noise)
    for sign in (1, -1):
        x, y, vx, vy = xx.copy(), yy.copy(), dx * sign, dy * sign
        for i in range(1, length):
            x += vx; y += vy
            ndx = ndimage.map_coordinates(dx, [y, x], order=1, mode='nearest')
            ndy = ndimage.map_coordinates(dy, [y, x], order=1, mode='nearest')
            flip = np.where(ndx * vx + ndy * vy < 0, -1.0, 1.0)
            vx, vy = ndx * flip, ndy * flip
            k = 0.5 + 0.5 * np.cos(np.pi * i / length)
            acc += k * ndimage.map_coordinates(noise, [y, x], order=1, mode='wrap')
            wsum += k
    return acc / wsum


def strands(L, px, seed):
    """Hair strands a few retail texels long and a quarter of one wide, as a unit-spread field."""
    rng = np.random.default_rng(seed)
    dx, dy = flow(L, px)
    h, w = L.shape
    long = lic(ndimage.gaussian_filter(rng.uniform(-1, 1, (h, w)).astype(np.float32), 0.5), dx, dy, int(5 * px))
    short = lic(ndimage.gaussian_filter(rng.uniform(-1, 1, (h, w)).astype(np.float32), 0.4), dx, dy, int(2 * px))
    return 0.7 * unit(long) + 0.5 * unit(short)


def picture(pictures, id, most=2.0):
    """A picture at its maps' size (twice it, so a stud or a ring has room to be round; no side past 512) and its scale."""
    path = os.path.join(pictures, id + '.png')
    sw, sh = map(int, subprocess.run(['identify', '-format', '%w %h', path], capture_output=True, text=True, check=True).stdout.split())
    k = min(most, 512 / max(sw, sh))
    w, h = int(sw * k), int(sh * k)
    return relief.read(path, w, h), w / sw


def arm(pack, pictures, idx_dir, id, suit, spec, print_, masks):
    """The picture's maps and its [[material]]."""
    out = os.path.join(pack, 'materials')
    path = os.path.join(pictures, id + '.png')
    # Hair's strands are finer than a retail texel: four times the picture.
    a, px = picture(pictures, id, 4.0 if any(s.endswith('=hair') for s in spec) else 2.0)
    h, w = a.shape[:2]
    L = (a[..., :3] * [0.3, 0.59, 0.11]).sum(-1) ** 0.8
    L = L / (blur(L, 24 * px) + 0.04)
    ip = os.path.join(idx_dir, id[2:] + '.idx')
    idx = indices(ip, w, h) if os.path.exists(ip) else np.full((h, w), 1024, np.uint16)
    kind = parts_of(spec, idx, a, px, lambda ref: picture(pictures, ref))
    names = [n for n in KINDS if (kind == n).any()]
    depth = relief.setting(spec, 'depth=', 1.0)
    # The height in retail texels: each part at its level, with its own shapes over it.
    A = np.zeros((h, w), np.float32)
    rough = np.zeros((h, w), np.float32)
    metal = np.zeros((h, w), np.float32)
    lit = np.clip(L / (np.percentile(L, 99) + 1e-5), 0, 1)
    for n in names:
        m = (kind == n).astype(np.float32)
        isme, r0, level, amp = KINDS[n]
        s = domes(kind == n, px) if n == 'stud' else shape(n, L, px)
        if n in ('fitting', 'plate'):
            # A fitting's or a plate's edge eases down to what it sits on.
            s = s * 0.7 + 0.3 * np.clip(ndimage.distance_transform_edt(kind == n) / (1.5 * px), 0, 1)
        A += m * (level + amp * s) * px
        if isme:
            # Worn bright where the picture paints it light; the dark between rings is rough.
            r = r0 - BRIGHT * np.clip((lit - 0.5) * 2, 0, 1) + (0.25 * np.clip(0.4 - lit, 0, 0.4) if n == 'chain' else 0)
        else:
            r = r0 + 0.12 * (0.5 - lit) + 0.04 * unit(L - blur(L, 1.0 * px)).clip(-1, 1)
        rough += m * r
        metal += m * isme
    A = blur(A, 0.35 * px) * depth
    # Fine grain on leather bends the light without being a height of its own.
    fine = np.isin(kind, ['leather', 'quilt', 'padding', 'fur']) * 0.25 * px * np.tanh(unit(blur(L, 0.4 * px) - blur(L, 1.2 * px)))
    if (kind == 'hair').any():
        # Hair: fine strands along the picture's painted flow, bending the light only; its painted shading is not a height.
        hs = strands(L, px, int(id, 16))
        fine = fine + (kind == 'hair') * 0.3 * px * np.tanh(hs)
        rough -= (kind == 'hair') * 0.06 * np.clip(hs, -1, 1)
    B = A + fine * depth
    sx = (np.roll(B, -1, 1) - np.roll(B, 1, 1)) / 2 / px
    sy = (np.roll(B, -1, 0) - np.roll(B, 1, 0)) / 2 / px
    mag = np.sqrt(sx * sx + sy * sy)
    kk = np.minimum(1, STEEPEST / (mag + 1e-6))
    nx, ny = -sx * kk, sy * kk
    l = np.sqrt(nx * nx + ny * ny + 1)
    one = np.ones((h, w), np.float32)
    lo, hi = np.percentile(A, [0.5, 99.8])
    hgt = 1 - RANGE * np.clip((hi - A) / (hi - lo + 1e-5), 0, 1)
    occ = crevices(hgt, 2.5 * px, 0.5)
    # The wearer's skin is as it was: no shade from the suit's edge.
    skin = blur((kind == 'skin').astype(np.float32), 0.5 * px)
    occ = occ * (1 - skin) + skin
    at = lambda part: os.path.join(out, f'{id}_{part}.png')
    relief.write(at('normal'), np.dstack([nx / l / 2 + 0.5, ny / l / 2 + 0.5, 1 / l / 2 + 0.5, one]))
    relief.grey(at('height'), hgt)
    relief.grey(at('occlusion'), occ)
    relief.grey(at('roughness'), np.clip(blur(rough, 0.4 * px), SMOOTHEST, ROUGHEST))
    metal = np.clip(blur(metal, 0.4 * px), 0, 1)
    relief.grey(at('metal'), metal)
    FALLBACK.write(at('fallback'), FALLBACK.average(path))
    if masks:
        relief.grey(os.path.join(masks, f'{id}_metal.png'), metal)
        cols = {'scale': (0.3, 0.5, 0.9), 'chitin': (0.5, 0.8, 0.5), 'fur': (0.9, 0.9, 0.9), 'hair': (0.85, 0.75, 0.55), 'quilt': (0.55, 0.35, 0.2), 'leather': (0.7, 0.5, 0.3), 'padding': (0.8, 0.8, 0.6), 'stud': (1, 0.85, 0.2),
                'fitting': (1, 0.5, 0.1), 'chain': (0.5, 0.7, 1), 'plate': (0.75, 0.85, 0.95), 'skin': (1, 0.75, 0.65),
                'cloth': (0.6, 0.45, 0.8), 'silk': (0.95, 0.55, 0.85), 'bone': (0.95, 0.92, 0.8)}
        rgb = np.zeros((h, w, 4), np.float32); rgb[..., 3] = 1
        for n in names:
            rgb[kind == n, :3] = cols[n]
        relief.write(os.path.join(masks, f'{id}_parts.png'), rgb)
    metals = [n for n in names if KINDS[n][0]]
    brighten = max((BRIGHTEN[n] for n in metals), default=1.0)
    grit = 'metal' if metal.mean() > 0.5 else 'clay'
    print(id, suit, f'{w}x{h}', ' '.join(f'{n} {(kind == n).mean():.2f}' for n in names))
    return f'''[[material]]
texture = "{id}"
{print_}base_color = "materials/{id}_fallback.png"
keep_retail_picture = true
metal_map = "materials/{id}_metal.png"
brighten = {brighten:g}
normal = "materials/{id}_normal.png"
roughness = "materials/{id}_roughness.png"
occlusion = "materials/{id}_occlusion.png"
height = "materials/{id}_height.png"
damp = 0.0
grit = "grit/{grit}.png"
grit_repeat = [1, 1]
author = "Worked out from the player's own picture and its palette's parts by {TOOL}"
tool = "{TOOL}"
license = "CC0-1.0"
'''


def main(args):
    pack, pictures, idx_dir = args[:3]
    only = set(option(args, '--only', '').split(',')) - {''}
    masks = option(args, '--masks', None)
    if masks:
        os.makedirs(masks, exist_ok=True)
    listed = table()
    prints_at = os.path.join(pictures, 'fingerprints.tsv')
    prints = dict(l.rstrip('\n').split('\t')[:2] for l in open(prints_at) if l.strip()) if os.path.exists(prints_at) else {}
    path = os.path.join(pack, 'manifest.toml')
    blocks = re.split(r'\n(?=\[\[)', open(path).read())
    texture = lambda b: (re.search(r'^texture = "(0x[0-9A-Fa-f]{8})"$', b, re.M) or [None, None])[1]
    eor = lambda b: re.search(r'^base_color = "materials/[^/"]+"$', b, re.M)
    made = 0
    for id, (suit, spec) in listed.items():
        if only and id not in only:
            continue
        if not os.path.exists(os.path.join(pictures, id + '.png')):
            print(id, 'is not among the pictures; left as it is')
            continue
        # A picture another tool already covers (a weapon's, say) is left to it.
        other = [b for b in blocks if b.startswith('[[material]]') and texture(b) == id and eor(b)
                 and not re.search(rf'^tool = "(relief\.py|{TOOL})"$', b, re.M)]
        if other:
            print(id, 'already has a material of', re.search(r'^tool = "([^"]+)"', other[0], re.M)[1] + '; left as it is')
            continue
        print_ = f'fingerprint = "{prints[id]}"\n' if id in prints else ''
        new = arm(pack, pictures, idx_dir, id, suit, spec, print_, masks)
        # It takes the place of relief.py's material or its own earlier one; else it goes last.
        at = next((i for i, b in enumerate(blocks) if b.startswith('[[material]]') and texture(b) == id and eor(b)
                   and re.search(rf'^tool = "(relief\.py|{TOOL})"$', b, re.M)), None)
        if at is None:
            blocks.append(new)
        else:
            blocks[at] = new
        made += 1
    open(path, 'w').write('\n'.join(blocks))
    print(made, 'materials of armour')


if __name__ == '__main__':
    main(sys.argv[1:])
