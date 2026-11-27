# The Bottle of Crystal Champagne painted anew (setup 0x020012B6): its label side 0x050025C3 and its
# bare side 0x050025C4, drawn from shapes and noise alone in place of the player's picture, which End
# of Retail holds in 32 dark colours. Green glass with its highlights, a crinkled silver foil cap, a
# black collar with a gold coin seal, and on the label side a gold oval frame round a cream
# plaque lettered "Dom Pyrignon, Vintage P.Y. 10" in Pinyon Script (fonts/, SIL Open Font License).
# Each part lies where the retail picture paints it, so the bottle's picture coordinates still fit.
# Its relief, roughness and clear map (glass clear, the rest solid, the foil, seal and frame metal)
# are made from the same shapes.
# Needs Python with numpy, scipy and Pillow, and ImageMagick (`magick`).
# champagne.py <pack folder> <the player's pictures>
# The player's pictures are only read for their fingerprints (fingerprints.tsv beside them).
import os, re, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import variants
import relief
from masonry import blur

TOOL = 'champagne.py'
FONT = os.path.join(HERE, 'fonts', 'PinyonScript-Regular.ttf')
# The picture's side in texels: twice retail's 256.
SIDE = 512
# The bottle is 1.19 m tall and 0.66 m across; the picture wraps its body, about 1.2 m round.
METRES = 1.2
CLEAR, REFRACTION = 0.2, 1.5
# The parts, in parts of the picture (x across, y down): the foil cap, the collar under it, the
# seal on the collar (centre and radii), and the label's plaque (centre and radii).
FOIL = (0.29, 0.0, 0.40, 0.275)
COLLAR = (0.205, 0.265, 0.555, 0.105)
SEAL = (0.47, 0.315, 0.075, 0.03)
PLAQUE = (0.49, 0.715, 0.27, 0.085)
LABEL = ('Dom Pyrignon', 'Vintage P.Y. 10')
PICTURES = {'0x050025C3': True, '0x050025C4': False}


def noise(rng, s):
    """Smooth noise with blobs about s texels across, unit spread."""
    a = blur(rng.standard_normal((SIDE, SIDE)).astype(np.float32), s)
    return a / (a.std() + 1e-9)


def ease(d, width):
    """0 outside, 1 a width inside, rounded between."""
    t = np.clip(d / width, 0, 1)
    return t * t * (3 - 2 * t)


def rect(X, Y, r, soft=1.5):
    x, y, w, h = r
    d = np.minimum(np.minimum(X - x * SIDE, (x + w) * SIDE - X), np.minimum(Y - y * SIDE, (y + h) * SIDE - Y))
    return ease(d, soft)


def oval(X, Y, cx, cy, rx, ry):
    """Signed distance into an ellipse, roughly in texels: positive inside."""
    q = np.sqrt(((X - cx * SIDE) / (rx * SIDE)) ** 2 + ((Y - cy * SIDE) / (ry * SIDE)) ** 2)
    return (1 - q) * min(rx, ry) * SIDE


def streak(X, Y, a, b, half):
    """A soft band along the line from a to b (parts of the picture), its 0..1 strength."""
    p, q = np.array(a) * SIDE, np.array(b) * SIDE
    d = q - p
    t = np.clip(((X - p[0]) * d[0] + (Y - p[1]) * d[1]) / (d @ d), 0, 1)
    dist = np.hypot(X - (p[0] + t * d[0]), Y - (p[1] + t * d[1]))
    return np.exp(-(dist / (half * SIDE)) ** 2) * np.sin(np.pi * np.clip(t, 0, 1)) ** 1.5


def cartouche(X, Y):
    """The label's outline (0..1), its gold frame (0..1), the plaque inside it (0..1) and the
    frame's own height (0..1, a rounded moulding): a plain oval ring round the plaque."""
    cx, cy, rx, ry = PLAQUE
    plaque = ease(oval(X, Y, cx, cy, rx, ry), 1.5)
    d = oval(X, Y, cx, cy, rx + 0.03, ry + 0.024)
    outline = ease(d, 1.5)
    frame = np.clip(outline - plaque, 0, 1)
    # The moulding rises from both edges of the ring to its middle.
    width = 0.027 * SIDE
    dome = np.sin(np.pi * np.clip(d / width, 0, 1))
    return outline, frame, plaque, dome * frame


def lettering():
    """The label's words, dark ink on the plaque: 0..1 coverage, drawn four times over and shrunk."""
    k = 4
    im = Image.new('L', (SIDE * k, SIDE * k), 0)
    d = ImageDraw.Draw(im)
    cx, cy, rx, ry = PLAQUE
    for text, y, tall in ((LABEL[0], cy - 0.012, 0.075), (LABEL[1], cy + 0.05, 0.034)):
        font = ImageFont.truetype(FONT, int(tall * SIDE * k))
        box = d.textbbox((0, 0), text, font=font)
        w = box[2] - box[0]
        # The name fills most of the plaque; the vintage sits under it.
        if w > 1.7 * rx * SIDE * k:
            font = ImageFont.truetype(FONT, int(tall * SIDE * k * 1.7 * rx * SIDE * k / w))
            box = d.textbbox((0, 0), text, font=font)
        x = cx * SIDE * k - (box[0] + box[2]) / 2
        d.text((x, y * SIDE * k - (box[1] + box[3]) / 2), text, font=font, fill=255)
    return np.asarray(im.resize((SIDE, SIDE), Image.LANCZOS), np.float32) / 255


def paint(labelled, rng):
    """The picture's colour, its height in metres, its roughness and where it is clear."""
    Y, X = np.mgrid[0:SIDE, 0:SIDE].astype(np.float32) + 0.5
    u, v = X / SIDE, Y / SIDE
    # Glass: deep green, paler toward the shoulders, darker toward the edges, with its highlights.
    deep, pale = np.array([0.006, 0.09, 0.018]), np.array([0.04, 0.4, 0.08])
    light = 0.3 + 0.4 * np.exp(-((u - 0.5) / 0.32) ** 2) * (1 - 0.6 * np.clip(v - 0.4, 0, 1)) + 0.025 * noise(rng, 40)
    colour = deep + (pale - deep) * np.clip(light, 0, 1)[..., None]
    shine = np.maximum.reduce([streak(X, Y, (0.36, 0.38), (0.05, 0.63), 0.03),
                               streak(X, Y, (0.61, 0.38), (0.75, 0.6), 0.025),
                               0.6 * streak(X, Y, (0.55, 0.9), (0.8, 0.97), 0.02)])
    colour = colour + (np.array([0.7, 0.97, 0.75]) - colour) * (0.85 * shine)[..., None]
    hgt = np.zeros((SIDE, SIDE), np.float32)
    rough = np.full((SIDE, SIDE), 0.05, np.float32)
    solid = np.zeros((SIDE, SIDE), np.float32)
    shiny = np.zeros((SIDE, SIDE), np.float32)

    def lay(mask, rgb, h, r, metal=0.0):
        nonlocal colour, hgt, rough, solid, shiny
        colour = colour * (1 - mask[..., None]) + rgb * mask[..., None]
        hgt = np.maximum(hgt, h * mask)
        rough = rough * (1 - mask) + r * mask
        solid = np.maximum(solid, mask)
        shiny = shiny * (1 - mask) + metal * mask

    # The collar: glossy black with a pale line where it turns to the light, and its coin seal.
    collar = rect(X, Y, COLLAR)
    band = 0.03 + 0.25 * np.exp(-((v - 0.29) / 0.008) ** 2) + 0.06 * np.exp(-((u - 0.47) / 0.12) ** 2)
    lay(collar, np.dstack([band, band, band * 1.05]), 0.0008, 0.15)
    sx, sy, srx, sry = SEAL
    coin = ease(oval(X, Y, sx, sy, srx, sry), 1.2)
    rim = coin * (1 - ease(oval(X, Y, sx, sy, srx * 0.72, sry * 0.72), 1.2))
    gold = np.array([0.78, 0.6, 0.2]) * (0.75 + 0.25 * np.clip(1 - (v - sy + sry) / (2 * sry), 0, 1))[..., None]
    lay(coin, gold * (1 - 0.25 * rim)[..., None] + 0.2 * rim[..., None], 0.0012 + 0.0005 * rim, 0.25, metal=1.0)
    # The foil: crinkled silver, bright down its middle as a cylinder lit from the front.
    foil = rect(X, Y, FOIL)
    fx = (u - (FOIL[0] + FOIL[2] / 2)) / (FOIL[2] / 2)
    # Pleats run down the foil where it was pressed round the cork, crinkled across.
    pleats = blur(rng.standard_normal((1, SIDE)).astype(np.float32).repeat(SIDE, 0), 2.0)
    pleats = pleats / (pleats.std() + 1e-9)
    crinkle = 0.55 * pleats + 0.3 * noise(rng, 1.5) + 0.15 * noise(rng, 5)
    grey = np.clip(0.35 + 0.5 * np.cos(np.clip(fx, -1, 1) * 1.4) ** 3 + 0.12 * crinkle, 0, 1)
    lay(foil, np.dstack([grey, grey, grey * 1.03]), 0.0006 + 0.0003 * np.clip(crinkle, -1, 1), 0.2, metal=1.0)
    if labelled:
        outline, frame, plaque, dome = cartouche(X, Y)
        # The frame: a polished gold moulding, a little darker in its hollows.
        lit = 0.8 + 0.2 * dome + 0.03 * noise(rng, 3)
        lay(frame, np.array([0.86, 0.68, 0.3]) * lit[..., None], 0.0005 + 0.0012 * dome, 0.25, metal=1.0)
        # The plaque: cream paper, its edge browned, and the words in sepia ink.
        paper = 0.92 + 0.04 * noise(rng, 2) - 0.25 * (1 - ease(oval(X, Y, *PLAQUE), 6))
        ink = lettering()
        cream = np.array([0.93, 0.84, 0.62]) * np.clip(paper, 0, 1)[..., None]
        sepia = np.array([0.2, 0.12, 0.06])
        lay(plaque, cream * (1 - ink[..., None]) + sepia * ink[..., None], 0.001 - 0.0002 * ink, 0.75)
    clear = np.clip(blur(1 - solid, 0.6), 0, 1)
    return np.clip(colour, 0, 1).astype(np.float32), hgt, np.clip(rough, 0, 1), clear, np.clip(blur(shiny, 0.6), 0, 1)


def write_maps(out, id, colour, hgt, rough, clear, metal):
    at = lambda part: os.path.join(out, f'{id}_{part}.png')
    one = np.ones(hgt.shape, np.float32)
    relief.write(at('albedo'), np.dstack([colour, one]))
    relief.grey(at('height'), np.clip(1 - (float(hgt.max()) - hgt) / relief.DEEPEST, 0, 1))
    m = METRES / SIDE
    sx = (np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)) / 2 / m
    sy = (np.roll(hgt, -1, 0) - np.roll(hgt, 1, 0)) / 2 / m
    s = np.minimum(1, relief.STEEPEST / (np.sqrt(sx * sx + sy * sy) + 1e-6))
    nx, ny = -sx * s, sy * s
    n = np.sqrt(nx * nx + ny * ny + 1)
    relief.write(at('normal'), np.dstack([nx / n / 2 + 0.5, ny / n / 2 + 0.5, 1 / n / 2 + 0.5, one]))
    relief.grey(at('occlusion'), 1 - np.clip((blur(hgt, 3) - hgt) / 0.0005 * 0.35, 0, 0.35))
    relief.grey(at('roughness'), rough)
    # Red where it is clear; green where what is not clear is a metal (the foil, the seal, the frame).
    relief.write(at('clear'), np.dstack([clear, metal, 0 * clear, one]))


def block(id, print_):
    m = f'materials/{id}'
    return f'''[[material]]
texture = "{id}"
{print_}base_color = "{m}_albedo.png"
normal = "{m}_normal.png"
roughness = "{m}_roughness.png"
occlusion = "{m}_occlusion.png"
height = "{m}_height.png"
damp = 0.0
clear = {CLEAR:g}
refraction = {REFRACTION:g}
clear_map = "{m}_clear.png"
author = "Generated by {TOOL}"
tool = "{TOOL}"
license = "CC0-1.0"
'''


def main(args):
    pack, pictures = args[:2]
    out = os.path.join(pack, 'materials')
    prints = {}
    at = os.path.join(pictures, 'fingerprints.tsv')
    if os.path.exists(at):
        prints = dict(l.rstrip('\n').split('\t')[:2] for l in open(at) if l.strip())
    path = os.path.join(pack, 'manifest.toml')
    blocks = re.split(r'\n(?=\[\[)', variants.flat(open(path).read()))
    texture = lambda b: (re.search(r'^texture = "(0x[0-9A-Fa-f]{8})"$', b, re.M) or [None, None])[1]
    # End of Retail's own materials only, directly in materials/.
    where = lambda b: re.search(r'^base_color = "materials/[^/"]+"$', b, re.M)
    for id, labelled in PICTURES.items():
        rng = np.random.default_rng(int(id, 16))
        write_maps(out, id, *paint(labelled, rng))
        print_ = f'fingerprint = "{prints[id]}"\n' if id in prints else ''
        new = block(id, print_)
        mine = [i for i, b in enumerate(blocks) if b.startswith('[[material]]') and texture(b) == id and where(b)]
        for i in mine:
            # The material this replaces: its pictures go with it.
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
    print(len(PICTURES), 'champagne pictures')


if __name__ == '__main__':
    main(sys.argv[1:])
