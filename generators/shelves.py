# Bookshelves' relief shaped by hand: the painted cabinet (setup 0x02000EFE, its front 0x050020E5 and side 0x050020E6),
# the wooden bookcase of the Training Academy and many dungeons (0x05000B15, setups 0x02000183, 0x02000BAF, 0x02000C56)
# and the stone-framed bookshelf (0x05001A3E, setups 0x0200096C, 0x02001205), whose books are painted as the wooden one's.
# The player's picture is kept and drawn as it is; only its height, normal, roughness and occlusion are made here,
# from shapes laid where the picture paints things: the shelves sunk behind the frame, the shelf boards flush with
# it, and what stands on them shaped as it is, a chest and a stack of papers as boxes, jars, urns and book spines as
# upright rounds, a spyglass as a lying round, a hanging cloth in folds and glass orbs as domes. The picture's own
# grain rides over the shapes, faintly.
# Needs Python with numpy and scipy, and ImageMagick (`magick`).
# shelves.py <pack folder> <the player's pictures>
import os, re, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import variants
import relief
import grit as GRIT
import fallback as FALLBACK
from masonry import blur

TOOL = 'shelves.py'
SIDE = 512
BACK = -0.10
# Each picture: the metres it spans across and down, and its shapes in parts of the picture (x, y, width, height)
# with depths in metres from the frame's face (0; negative is deeper). Later shapes stand in front of earlier ones.
# A book leaning over runs from a to b, its spine rounded across; a book standing upright (spine) is rounded across
# and over its top. A shelf of books (spines) finds its books where a picture (its own, or the one named) is brighter
# than the shelf's dark back, and rounds each across and over its top.

def shelf_books():
    """The books of the wooden bookcase (and of the stone-framed one, painted the same): uprights by their sides and
    tops, standing on each shelf's floor, and books leaning or lying along their slant."""
    out = []
    floors = (0.305, 0.607, 0.915)
    upright = (
        [(0.128, 0.145, 0.07), (0.156, 0.175, 0.09), (0.188, 0.203, 0.10), (0.203, 0.218, 0.11), (0.233, 0.25, 0.10),
         (0.57, 0.605, 0.109), (0.609, 0.636, 0.11), (0.64, 0.672, 0.109), (0.688, 0.72, 0.117),
         (0.725, 0.75, 0.078), (0.752, 0.778, 0.095), (0.78, 0.80, 0.10), (0.80, 0.83, 0.065), (0.832, 0.858, 0.09),
         (0.858, 0.874, 0.10)],
        [(0.13, 0.152, 0.41), (0.158, 0.186, 0.405), (0.19, 0.215, 0.41), (0.219, 0.248, 0.43), (0.25, 0.279, 0.44),
         (0.282, 0.309, 0.45), (0.312, 0.339, 0.45), (0.342, 0.369, 0.45), (0.372, 0.398, 0.44), (0.40, 0.42, 0.45),
         (0.552, 0.572, 0.47), (0.578, 0.60, 0.46), (0.62, 0.648, 0.46), (0.655, 0.68, 0.445), (0.683, 0.70, 0.44),
         (0.702, 0.725, 0.40), (0.73, 0.752, 0.45), (0.758, 0.788, 0.45), (0.80, 0.828, 0.45), (0.832, 0.862, 0.405)],
        [(0.13, 0.152, 0.70), (0.158, 0.19, 0.685), (0.192, 0.21, 0.70), (0.212, 0.236, 0.70), (0.25, 0.279, 0.735),
         (0.281, 0.30, 0.74), (0.302, 0.33, 0.74), (0.332, 0.356, 0.74), (0.368, 0.395, 0.74), (0.40, 0.43, 0.735),
         (0.437, 0.465, 0.715), (0.468, 0.50, 0.70), (0.60, 0.625, 0.72), (0.628, 0.65, 0.73), (0.655, 0.68, 0.70), (0.683, 0.70, 0.71),
         (0.703, 0.737, 0.76), (0.74, 0.762, 0.725), (0.77, 0.80, 0.72), (0.80, 0.83, 0.74), (0.835, 0.862, 0.70)],
    )
    for floor, row in zip(floors, upright):
        for x0, x1, top in row:
            out.append(('spine', x0, top, x1 - x0, floor - top, -0.025))
    out += [
        # The top shelf: two large tomes lying one on the other, two books leaning to the left and one to the right,
        # and one lying across the tops on the right.
        ('box', 0.27, 0.188, 0.128, 0.057, -0.025),
        ('box', 0.262, 0.248, 0.128, 0.057, -0.028),
        ('book', (0.405, 0.14), (0.455, 0.30), 0.01, -0.03),
        ('book', (0.515, 0.08), (0.47, 0.30), 0.01, -0.035),
        ('book', (0.555, 0.09), (0.515, 0.29), 0.01, -0.035),
        ('book', (0.563, 0.082), (0.74, 0.082), 0.014, -0.022),
        # The middle shelf: one lying across the tops on the left, and two leaning to the right.
        ('book', (0.273, 0.402), (0.414, 0.402), 0.0146, -0.022),
        ('book', (0.43, 0.42), (0.475, 0.60), 0.011, -0.03),
        ('book', (0.47, 0.43), (0.52, 0.605), 0.011, -0.03),
        # The bottom shelf: one lying across the tops on the left, and one leaning to the left.
        ('book', (0.273, 0.70), (0.422, 0.70), 0.0142, -0.022),
        ('book', (0.572, 0.785), (0.525, 0.905), 0.011, -0.03),
    ]
    return out

PICTURES = {
    '0x050020E5': ((2.15, 2.5), [
        # The top shelf's back runs up behind the painted border, which hangs on it.
        ('recess', 0.12, 0.03, 0.73, 0.17, BACK),
        ('recess', 0.12, 0.245, 0.73, 0.165, BACK),
        ('recess', 0.12, 0.45, 0.73, 0.17, BACK),
        ('board', 0.12, 0.20, 0.73, 0.045),
        ('board', 0.12, 0.41, 0.73, 0.04),
        ('board', 0.12, 0.62, 0.73, 0.035),
        ('recess', 0.12, 0.655, 0.73, 0.245, -0.008),
        # The top shelf: a green chest, a spyglass and a stack of papers.
        ('box', 0.14, 0.045, 0.26, 0.15, -0.025),
        ('rod', (0.585, 0.185), (0.75, 0.11), 0.03, -0.055),
        ('box', 0.70, 0.15, 0.13, 0.05, -0.035),
        # The middle shelf: a cloth hung on the back, a tall candle, a short one and a squat one, and two books leaning in the corner.
        ('cloth', 0.15, 0.255, 0.60, 0.145, BACK + 0.012),
        ('round', 0.14, 0.30, 0.06, 0.105, -0.035),
        ('round', 0.225, 0.328, 0.039, 0.077, -0.045),
        ('round', 0.278, 0.365, 0.059, 0.04, -0.05),
        ('book', (0.816, 0.309), (0.773, 0.387), 0.013, -0.045),
        ('book', (0.841, 0.32), (0.802, 0.398), 0.013, -0.05),
        # The bottom shelf: two copper urns, a row of books, one lying on its side and four glass orbs.
        ('round', 0.14, 0.455, 0.13, 0.16, -0.015),
        ('round', 0.71, 0.455, 0.10, 0.16, -0.02),
        ('round', 0.30, 0.465, 0.035, 0.15, -0.03),
        ('round', 0.335, 0.465, 0.035, 0.15, -0.03),
        ('round', 0.37, 0.465, 0.035, 0.15, -0.03),
        ('round', 0.405, 0.465, 0.035, 0.15, -0.03),
        ('book', (0.452, 0.468), (0.53, 0.598), 0.024, -0.03),
        ('orb', 0.575, 0.585, 0.022, -0.06),
        ('orb', 0.615, 0.585, 0.022, -0.06),
        ('orb', 0.655, 0.585, 0.022, -0.06),
        ('orb', 0.69, 0.59, 0.018, -0.065),
    ]),
    # The side: a plain parchment panel set back in its frame and a row of glass orbs on a ledge.
    '0x050020E6': ((2.1, 2.5), [
        ('recess', 0.08, 0.20, 0.84, 0.54, -0.02),
        ('recess', 0.08, 0.74, 0.84, 0.12, -0.05),
        ('board', 0.08, 0.86, 0.84, 0.03),
    ] + [('orb', 0.115 + 0.077 * i, 0.80, 0.03, -0.03) for i in range(11)]),
    # The wooden bookcase: three shelves of books between flush boards, in a wooden frame.
    '0x05000B15': ((1.649, 2.0), [
        ('grain', 0, 0, 1, 1, 0.0025),
        ('plate', 0, 0, 0.125, 0.06, 0.003),
        ('plate', 0.875, 0, 0.125, 0.06, 0.003),
        ('plate', 0, 0.93, 0.125, 0.07, 0.003),
        ('plate', 0.875, 0.93, 0.125, 0.07, 0.003),
        ('recess', 0.125, 0.0625, 0.75, 0.2578, BACK),
        ('recess', 0.125, 0.3828, 0.75, 0.2422, BACK),
        ('recess', 0.125, 0.6797, 0.75, 0.25, BACK),
        ('board', 0.125, 0.3203, 0.75, 0.0625),
        ('board', 0.125, 0.625, 0.75, 0.0547),
    ] + shelf_books() + [('bolt', x, y, 0.014, 0.006) for y in (0.026, 0.352, 0.652, 0.967) for x in (0.268, 0.51, 0.76)]),
    # The stone-framed bookshelf: the same books, painted darker, between boards edged in red.
    '0x05001A3E': ((1.649, 2.0), [
        ('recess', 0.125, 0.065, 0.75, 0.255, BACK),
        ('recess', 0.125, 0.38, 0.75, 0.245, BACK),
        ('recess', 0.125, 0.69, 0.75, 0.24, BACK),
        ('board', 0.125, 0.32, 0.75, 0.06),
        ('board', 0.125, 0.625, 0.75, 0.065),
    ] + shelf_books()),
}
# The grit tile each takes: wood, the side's parchment panel, the stone frame.
GRITS = {'0x050020E5': 'fibre', '0x050020E6': 'plaster', '0x05000B15': 'fibre', '0x05001A3E': 'stone'}
# Roughness: wood and paint, the orbs' glass, and books' satin covers.
WOOD, GLASS, BOOKS = 0.7, 0.08, 0.45
# A shelf of books: where a book is (the picture's brightest channel above this, its back being near black), how
# round a spine is across (metres), and how round over its top.
BOOK_LIGHT, SPINE, TOP = 0.18, 0.015, 0.008
# The folder of the player's pictures, for shelves of books.
PICS = ''


def shape(H, R, X, Y, m, s):
    """Lays one shape into the height H (metres) and roughness R; X, Y are each texel's place in metres."""
    kind = s[0]
    mx, my = m
    def rect(x, y, w, h):
        return (X >= x * mx) & (X < (x + w) * mx) & (Y >= y * my) & (Y < (y + h) * my)
    if kind == 'recess':
        x, y, w, h, z = s[1:]
        H[rect(x, y, w, h)] = z
    elif kind == 'board':
        # A shelf board flush with the frame, its front edge rounded over.
        x, y, w, h = s[1:]
        t = np.clip((Y - y * my) / (h * my), 0, 1)
        k = rect(x, y, w, h)
        H[k] = -0.012 * (1 - np.sin(np.pi * t[k])) ** 2
    elif kind == 'box':
        # A box's face, its edges eased back a little.
        x, y, w, h, z = s[1:]
        k = rect(x, y, w, h)
        d = np.minimum.reduce([X - x * mx, (x + w) * mx - X, Y - y * my, (y + h) * my - Y])
        H[k] = np.maximum(H[k], z - 0.012 * (1 - np.clip(d[k] / 0.015, 0, 1)) ** 2)
    elif kind == 'round':
        # An upright round (a jar, an urn, a book's spine): deepest at its sides, frontmost at its middle.
        x, y, w, h, z = s[1:]
        k = rect(x, y, w, h)
        dx = (X - (x + w / 2) * mx) / (w / 2 * mx)
        r = w / 2 * mx
        H[k] = np.maximum(H[k], z - r + r * np.sqrt(np.clip(1 - dx[k] ** 2, 0, 1)))
    elif kind == 'rod':
        # A lying round from a to b (a spyglass), its radius in metres.
        (ax, ay), (bx, by), r, z = s[1:]
        p, q = np.array([ax * mx, ay * my]), np.array([bx * mx, by * my])
        d = q - p
        t = np.clip(((X - p[0]) * d[0] + (Y - p[1]) * d[1]) / (d @ d), 0, 1)
        dist = np.hypot(X - (p[0] + t * d[0]), Y - (p[1] + t * d[1]))
        k = dist < r
        H[k] = np.maximum(H[k], z - r + r * np.sqrt(1 - (dist[k] / r) ** 2))
    elif kind == 'book':
        # A book leaning over, from a to b: its spine rounded across, its ends square.
        (ax, ay), (bx, by), hw, z = s[1:]
        p, q = np.array([ax * mx, ay * my]), np.array([bx * mx, by * my])
        d = q - p
        t = ((X - p[0]) * d[0] + (Y - p[1]) * d[1]) / (d @ d)
        across = np.abs((X - p[0]) * d[1] - (Y - p[1]) * d[0]) / np.sqrt(d @ d)
        r = hw * mx
        k = (t >= 0) & (t <= 1) & (across < r)
        H[k] = np.maximum(H[k], z - r + r * np.sqrt(1 - (across[k] / r) ** 2))
    elif kind == 'spine':
        # A book standing upright: its spine rounded across and over its top.
        x, y, w, h, z = s[1:]
        k = rect(x, y, w, h)
        r = w / 2 * mx
        dx = np.abs(X - (x + w / 2) * mx)
        dy = Y - y * my
        bulge = lambda d, q: q - np.sqrt(np.clip(q * q - (q - np.minimum(d, q)) ** 2, 0, None))
        H[k] = np.maximum(H[k], z - (r - np.sqrt(np.clip(r * r - dx[k] ** 2, 0, None))) - bulge(dy[k], TOP))
        R[k] = BOOKS
    elif kind == 'spines':
        # A shelf of books found in a picture: each spine rounded across, and over its top, standing at z.
        from scipy import ndimage
        x, y, w, h, z, source = s[1:]
        k = rect(x, y, w, h)
        a = relief.read(os.path.join(PICS, (source or ID) + '.png'), *H.shape[::-1])
        book = a[..., :3].max(-1) > BOOK_LIGHT
        n = max(1, H.shape[1] // 128)
        book = ndimage.binary_closing(book, structure=np.ones((3 * n, 1)))
        book = ndimage.binary_opening(book, structure=np.ones((1, n)))
        book &= k
        px = mx / H.shape[1]
        across = np.minimum(ndimage.distance_transform_edt(book, sampling=(1e6, px)), SPINE)
        over = np.minimum(ndimage.distance_transform_edt(book, sampling=(px * my / mx * H.shape[1] / H.shape[0], 1e6)), TOP)
        bulge = lambda d, r: r - np.sqrt(np.clip(r * r - (r - d) ** 2, 0, None))
        zz = z - bulge(across, SPINE) - bulge(over, TOP)
        H[book] = np.maximum(H[book], zz[book])
        R[book] = BOOKS
    elif kind == 'bolt':
        # A domed bolt head, its centre and radius in parts of the picture's width, standing h proud.
        cx, cy, rr, hh = s[1:]
        r = rr * mx
        dist = np.hypot(X - cx * mx, Y - cy * my)
        k = dist < r
        H[k] = H[k] + hh * np.sqrt(1 - (dist[k] / r) ** 2)
        R[k] = 0.35
    elif kind == 'plate':
        # An iron plate on the frame, standing h proud, with its slot sunk.
        x, y, w, h, hh = s[1:]
        k = rect(x, y, w, h)
        H[k] = H[k] + hh
        R[k] = 0.4
    elif kind == 'grain':
        # More of the picture's own grain over a part of it (a wooden frame's).
        x, y, w, h, amount = s[1:]
        k = rect(x, y, w, h)
        a = relief.read(os.path.join(PICS, ID + '.png'), *H.shape[::-1])
        L = (a[..., :3] * [0.3, 0.59, 0.11]).sum(-1)
        g = L - blur(L, 6)
        H[k] = H[k] + amount * g[k] / (float(g.std()) + 1e-6)
    elif kind == 'orb':
        # A glass orb, its centre and radius in parts of the picture's width.
        cx, cy, rr, z = s[1:]
        r = rr * mx
        dist = np.hypot(X - cx * mx, Y - cy * my)
        k = dist < r
        H[k] = np.maximum(H[k], z - r + r * np.sqrt(1 - (dist[k] / r) ** 2))
        R[k] = GLASS
    elif kind == 'cloth':
        # A cloth hung flat on the back, in soft upright folds.
        x, y, w, h, z = s[1:]
        k = rect(x, y, w, h)
        H[k] = np.maximum(H[k], z + 0.006 * np.sin(X[k] / (0.09 * mx / 2.15) * 2 * np.pi))


def make(id, metres, shapes, picture):
    mx, my = metres
    w, h = SIDE, round(SIDE * 1.0)
    Y, X = np.mgrid[0:h, 0:w].astype(np.float32) + 0.5
    X, Y = X / w * mx, Y / h * my
    H = np.zeros((h, w), np.float32)
    R = np.full((h, w), WOOD, np.float32)
    for s in shapes:
        shape(H, R, X, Y, metres, s)
    # The picture's own grain, faintly, over the shapes.
    a = relief.read(picture, w, h)
    L = (a[..., :3] * [0.3, 0.59, 0.11]).sum(-1)
    H = blur(H, 0.8) + 0.0015 * (L - blur(L, 4)) / (float((L - blur(L, 4)).std()) + 1e-6)
    return H, R, mx / w


def write(out, id, H, R, m, picture):
    at = lambda part: os.path.join(out, f'{id}_{part}.png')
    one = np.ones(H.shape, np.float32)
    relief.grey(at('height'), np.clip(1 - (float(H.max()) - H) / relief.DEEPEST, 0, 1))
    sx = (np.roll(H, -1, 1) - np.roll(H, 1, 1)) / 2 / m
    sy = (np.roll(H, -1, 0) - np.roll(H, 1, 0)) / 2 / m
    s = np.minimum(1, relief.STEEPEST / (np.sqrt(sx * sx + sy * sy) + 1e-6))
    nx, ny = -sx * s, sy * s
    n = np.sqrt(nx * nx + ny * ny + 1)
    relief.write(at('normal'), np.dstack([nx / n / 2 + 0.5, ny / n / 2 + 0.5, 1 / n / 2 + 0.5, one]))
    # Shade where something stands deeper than what is about it (the back of a shelf, behind its things).
    relief.grey(at('occlusion'), 1 - np.clip((blur(H, 12) - H) / 0.03, 0, 0.45))
    relief.grey(at('roughness'), R)
    FALLBACK.write(at('fallback'), FALLBACK.average(picture))


def block(id, print_, metres):
    m = f'materials/{id}'
    return f'''[[material]]
texture = "{id}"
{print_}base_color = "{m}_fallback.png"
keep_retail_picture = true
normal = "{m}_normal.png"
roughness = "{m}_roughness.png"
occlusion = "{m}_occlusion.png"
height = "{m}_height.png"
damp = 0.0
grit = "grit/{GRITS[id]}.png"
grit_repeat = [{GRIT.repeats(metres[0])}, {GRIT.repeats(metres[1])}]
author = "Shaped by hand over the player's own picture by {TOOL}"
tool = "{TOOL}"
license = "CC0-1.0"
'''


def main(args):
    pack, pictures = args[:2]
    out = os.path.join(pack, 'materials')
    at = os.path.join(pictures, 'fingerprints.tsv')
    prints = dict(l.rstrip('\n').split('\t')[:2] for l in open(at) if l.strip()) if os.path.exists(at) else {}
    path = os.path.join(pack, 'manifest.toml')
    blocks = re.split(r'\n(?=\[\[)', variants.flat(open(path).read()))
    texture = lambda b: (re.search(r'^texture = "(0x[0-9A-Fa-f]{8})"$', b, re.M) or [None, None])[1]
    where = lambda b: re.search(r'^base_color = "materials/[^/"]+"$', b, re.M)
    global PICS, ID
    PICS = pictures
    for id, (metres, shapes) in PICTURES.items():
        ID = id
        picture = os.path.join(pictures, id + '.png')
        H, R, m = make(id, metres, shapes, picture)
        write(out, id, H, R, m, picture)
        print_ = f'fingerprint = "{prints[id]}"\n' if id in prints else ''
        new = block(id, print_, metres)
        mine = [i for i, b in enumerate(blocks) if b.startswith('[[material]]') and texture(b) == id and where(b)]
        for i in mine:
            for f in re.findall(r'"(materials/[^"]+\.png)"', blocks[i]):
                if f not in new and os.path.exists(os.path.join(pack, f)):
                    os.remove(os.path.join(pack, f))
        if mine:
            blocks[mine[0]] = new.rstrip('\n') + blocks[mine[0]][len(blocks[mine[0]].rstrip('\n')):]
            for i in reversed(mine[1:]):
                del blocks[i]
        else:
            blocks.append(new)
    open(path, 'w').write(variants.settle('\n'.join(blocks)))
    print(len(PICTURES), 'shelf pictures shaped')


if __name__ == '__main__':
    main(sys.argv[1:])
