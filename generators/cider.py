# The Cove Apple Wine bottle painted anew (setup 0x0200016F, graphics object 0x010005F1): its neck
# 0x05000A9A and its body 0x05000A9B, drawn from shapes and noise alone in place of the player's dark
# brown pictures. Apple-cider glass, deeper where it is thick, with soft highlights, and a crinkled
# silver foil over the top of the neck, where the retail picture paints its grey cap.
# Its relief, roughness and clear map (the glass clear, the foil solid and metal) come from the same shapes.
# Needs Python with numpy and scipy.
# cider.py <pack folder> <the player's pictures>
# The player's pictures are only read for their fingerprints (fingerprints.tsv beside them).
import os, re, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import variants
import relief
from masonry import blur

TOOL = 'cider.py'
CLEAR, REFRACTION = 0.12, 1.5
# Each picture: its side in texels (eight times retail's), the metres it spans, and how far down the foil reaches.
PICTURES = {'0x05000A9A': (128, 0.10, 0.29), '0x05000A9B': (256, 0.20, 0.0)}
# Apple cider in glass: deep amber where the glass is thick, golden where the light comes through.
DEEP, PALE = np.array([0.24, 0.09, 0.01]), np.array([0.80, 0.46, 0.07])


def noise(rng, side, s):
    """Smooth noise with blobs about s texels across, unit spread."""
    a = blur(rng.standard_normal((side, side)).astype(np.float32), s)
    return a / (a.std() + 1e-9)


def ease(d, width):
    t = np.clip(d / width, 0, 1)
    return t * t * (3 - 2 * t)


def paint(side, foil_to, rng):
    """The picture's colour, its height in metres, its roughness, where it is clear and where it is metal."""
    Y, X = np.mgrid[0:side, 0:side].astype(np.float32) + 0.5
    u, v = X / side, Y / side
    # The glass: golden through its middle, deeper toward its ends and edges, with a faint swirl in the cider.
    light = (0.62 + 0.25 * np.exp(-((u - 0.5) / 0.35) ** 2) - 0.35 * np.clip(np.abs(v - 0.5) * 2 - 0.6, 0, 1)
             + 0.04 * noise(rng, side, side / 10) + 0.015 * noise(rng, side, side / 40))
    colour = DEEP + (PALE - DEEP) * np.clip(light, 0, 1)[..., None]
    # Two soft highlights run down the glass.
    shine = np.maximum(np.exp(-((u - 0.33) / 0.035) ** 2), 0.5 * np.exp(-((u - 0.7) / 0.025) ** 2))
    shine = shine * np.sin(np.pi * np.clip((v - foil_to) / max(1 - foil_to, 1e-3), 0, 1)) ** 0.6
    colour = colour + (np.array([1.0, 0.9, 0.7]) - colour) * (0.55 * shine)[..., None]
    hgt = np.zeros((side, side), np.float32)
    rough = np.full((side, side), 0.05, np.float32)
    solid = np.zeros((side, side), np.float32)
    if foil_to:
        # The foil: crinkled silver pressed round the cork, pleated down and rolled at its lower edge.
        d = foil_to * side - Y
        foil = ease(d, 1.5)
        pleats = blur(rng.standard_normal((1, side)).astype(np.float32).repeat(side, 0), side / 64)
        pleats = pleats / (pleats.std() + 1e-9)
        crinkle = 0.55 * pleats + 0.3 * noise(rng, side, side / 80) + 0.15 * noise(rng, side, side / 25)
        lip = np.exp(-((d - 0.025 * side) / (0.02 * side)) ** 2)
        grey = np.clip(0.6 + 0.25 * np.cos((u - 0.5) * 2.4) ** 3 + 0.1 * crinkle - 0.25 * lip, 0, 1)
        silver = np.dstack([grey, grey, grey * 1.03])
        colour = colour * (1 - foil[..., None]) + silver * foil[..., None]
        hgt = (0.0005 + 0.0002 * np.clip(crinkle, -1, 1) + 0.0003 * lip) * foil
        rough = rough * (1 - foil) + 0.22 * foil
        solid = foil
        # The glass just under the foil is thick and dark.
        under = np.exp(-((v - foil_to - 0.06) / 0.06) ** 2) * (1 - foil)
        colour = colour * (1 - 0.55 * under)[..., None]
    clear = np.clip(blur(1 - solid, 0.6), 0, 1)
    return np.clip(colour, 0, 1).astype(np.float32), hgt, np.clip(rough, 0, 1), clear, np.clip(blur(solid, 0.6), 0, 1)


def write_maps(out, id, metres, colour, hgt, rough, clear, metal):
    at = lambda part: os.path.join(out, f'{id}_{part}.png')
    one = np.ones(hgt.shape, np.float32)
    relief.write(at('albedo'), np.dstack([colour, one]))
    relief.grey(at('height'), np.clip(1 - (float(hgt.max()) - hgt) / relief.DEEPEST, 0, 1))
    m = metres / hgt.shape[0]
    sx = (np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)) / 2 / m
    sy = (np.roll(hgt, -1, 0) - np.roll(hgt, 1, 0)) / 2 / m
    s = np.minimum(1, relief.STEEPEST / (np.sqrt(sx * sx + sy * sy) + 1e-6))
    nx, ny = -sx * s, sy * s
    n = np.sqrt(nx * nx + ny * ny + 1)
    relief.write(at('normal'), np.dstack([nx / n / 2 + 0.5, ny / n / 2 + 0.5, 1 / n / 2 + 0.5, one]))
    relief.grey(at('occlusion'), 1 - np.clip((blur(hgt, 3) - hgt) / 0.0005 * 0.35, 0, 0.35))
    relief.grey(at('roughness'), rough)
    # Red where it is clear; green where what is not clear is a metal (the foil).
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
    for id, (side, metres, foil_to) in PICTURES.items():
        rng = np.random.default_rng(int(id, 16))
        write_maps(out, id, metres, *paint(side, foil_to, rng))
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
    print(len(PICTURES), 'cider bottle pictures')


if __name__ == '__main__':
    main(sys.argv[1:])
