# Dark iron that shines as iron does: a [[material]] for each retail picture of iron, or of wood bound
# with iron, that keeps relief.py's relief of the player's own picture and says where it is a metal.
# Iron is smooth, so a lamp's light glints off it, and smoother still where the picture paints it
# worn bright (rivets, band edges, hinge straps). A picture wholly of iron is `metal`; one of wood
# bound with iron names a metal map, white where the picture is iron (grey, where wood is warm, and
# the rivets the bands hold), so its wood stays wood. The iron is brightened a little toward what it
# mirrors and stays dark. Nothing of any picture's pixels goes into the pack. Replaces relief.py's
# material for these pictures.
# Needs Python with numpy and ImageMagick (`magick`).
# iron.py <pack folder> <the player's pictures> [--rough <iron's roughness>] [--brighten <times>]
import os, re, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import relief
from masonry import blur

TOOL = 'iron.py'
TABLES = os.path.join(HERE, '..', 'tables')
# Each picture: whether it is wholly iron or wood bound with iron.
IRON = {
    # The iron double doors' leaves (0x020005DA, 0x020005F1).
    '0x05001777': 'iron',
    # The riveted iron posts and lintel of 0x020005F1, and the plates of many dungeons.
    '0x05002635': 'iron',
    '0x05000EE2': 'iron',
    # The banded posts and lintel of 0x020005DA and of the wooden doors (0x0200024F), and the
    # beams of many dungeons.
    '0x05002620': 'banded',
    '0x05002638': 'banded',
    # The wooden doors' leaf, its hinges, ring and foot iron.
    '0x05000D25': 'banded',
    # Props: the wall torch's plate and collar (0x020001E5), the hanging chain (0x01000E0E), the
    # standing torch's stand (0x020005D9), the cask's hoops (0x020000A5), the house door's
    # hinges (0x020019FF) and the chandelier's chain (0x02000081).
    '0x050010C4': 'iron',
    '0x05001417': 'iron',
    '0x0500141A': 'iron',
    '0x05002A9F': 'banded',
    '0x05000A91': 'banded',
    '0x05002F96': 'banded',
    '0x05000B18': 'iron',
}
# Iron's roughness where the picture is plain, how much smoother it is where painted worn bright,
# and the smoothest and roughest it may be.
ROUGH, BRIGHT, SMOOTHEST, ROUGHEST = 0.4, 0.16, 0.12, 0.8
# How many times brighter than its picture iron is drawn: a metal's own light is dimmed, so this
# keeps it darker than its picture while it mirrors more.
BRIGHTEN = 2.0
# The warmth (red over blue, against red) below which a texel is iron, above which wood: iron's
# grey and green against the wood's orange.
COLD, WARM = 0.18, 0.4


def option(args, name, default):
    return float(args[args.index(name) + 1]) if name in args else default


def recipes():
    listed = {}
    for line in open(os.path.join(TABLES, 'recipes.tsv')):
        if line.strip() and not line.startswith('#'):
            id, material, recipe, damp, *rest = line.rstrip('\n').split('\t')
            listed[id] = material, recipe, float(damp), ' '.join(rest).split()
    return listed


def iron(pack, pictures, id, kind, entry, print_, rough, brighten):
    """The picture's relief by relief.py, its iron made smooth and metal, and its [[material]]."""
    out = os.path.join(pack, 'materials')
    _, block, why = relief.make((os.path.join(pictures, id + '.png'), out, entry, None, 256, 128, '', print_))
    if not block:
        print(id, why)
        return ''
    at = lambda part: os.path.join(out, f'{id}_{part}.png')
    w, h = size(at('roughness'))
    a = relief.read(os.path.join(pictures, id + '.png'), w, h)[..., :3]
    px = w / a.shape[1]
    r = relief.read(at('roughness'), w, h)[..., 0]
    # Worn bright: the picture's own highlights, against its middle.
    L = (a * [0.3, 0.59, 0.11]).sum(-1)
    mid, top = np.percentile(L, 50), np.percentile(L, 99)
    bright = np.clip((L - mid) / (top - mid + 1e-5), 0, 1)
    smooth = np.clip(rough - BRIGHT * bright + 0.5 * (r - np.median(r)), SMOOTHEST, ROUGHEST)
    if kind == 'iron':
        metal = np.ones_like(L)
    else:
        warmth = (a[..., 0] - a[..., 2]) / (a[..., 0] + 0.03)
        metal = 1 - np.clip((warmth - COLD) / (WARM - COLD), 0, 1)
        # A speck of grey grain in the wood is wood; a warm rivet held in a band is iron.
        near = lambda m: blur(m, 1.5 * px)
        metal = metal * np.clip((near(metal) - 0.25) / 0.2, 0, 1)
        metal = np.maximum(metal, np.clip((near(metal) - 0.55) / 0.2, 0, 1))
        metal = blur(metal, 0.5 * px)
    relief.grey(at('roughness'), r + (smooth - r) * metal)
    tail = f'brighten = {brighten:g}\n'
    if kind == 'iron':
        tail = 'metal = true\n' + tail
    else:
        relief.grey(at('metal'), metal)
        tail = f'metal_map = "materials/{id}_metal.png"\n' + tail
    block = block.replace('keep_retail_picture = true\n', 'keep_retail_picture = true\n' + tail)
    block = re.sub(r'^author = .*$', f'author = "Worked out from the player\'s own picture by {TOOL} with relief.py"', block, flags=re.M)
    block = re.sub(r'^tool = .*$', f'tool = "{TOOL} relief.py"', block, flags=re.M)
    return block.strip('\n')


def size(path):
    w, h = subprocess.run(['identify', '-format', '%w %h', path], capture_output=True, text=True, check=True).stdout.split()
    return int(w), int(h)


def main(args):
    pack, pictures = args[:2]
    rough, brighten = option(args, '--rough', ROUGH), option(args, '--brighten', BRIGHTEN)
    path = os.path.join(pack, 'manifest.toml')
    blocks = re.split(r'\n(?=\[\[)', open(path).read())
    texture = lambda b: (re.search(r'^texture = "(0x[0-9A-Fa-f]{8})"$', b, re.M) or [None, None])[1]
    listed = recipes()
    made = 0
    for i, b in enumerate(blocks):
        id = texture(b) if b.startswith('[[material]]') else None
        if id not in IRON or not re.search(rf'^tool = "(relief\.py|{TOOL} relief\.py)"$', b, re.M):
            continue
        if not os.path.exists(os.path.join(pictures, id + '.png')):
            print(id, 'is not among the pictures; its material is kept')
            continue
        print_ = ''.join(re.findall(r'^fingerprint = .*\n', b + '\n', re.M))
        new = iron(pack, pictures, id, IRON[id], listed.get(id), print_, rough, brighten)
        if new:
            # Each in its place, so the manifest's other entries keep their order.
            blocks[i] = new + '\n'
            made += 1
    text = '\n'.join(blocks)
    open(path, 'w').write(text)
    print(made, 'iron materials of', len(IRON))


if __name__ == '__main__':
    main(sys.argv[1:])
