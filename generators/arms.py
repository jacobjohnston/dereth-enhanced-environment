# Arms and armour that shine as steel and gold do: a [[material]] for each retail picture of a blade,
# a mace's head, a hilt, a shield or a suit of plate, that keeps relief.py's relief of the player's
# own picture and says where it is a metal. Steel and gold are smooth, so a lamp's light glints off
# them, smoother still where the picture paints them worn bright. A picture wholly of steel or gold
# is `metal`; one where they lie beside leather names a metal map, white where the picture is grey
# (steel) or, where it is gilt, a light yellow (gold, brass), so a hilt's leather wrap, a shield's
# face and a belt stay as they are. A dark picture is brightened toward what a metal mirrors, a
# bright one less, so polished plate does not burn out. Nothing of any picture's pixels goes into the
# pack. Replaces relief.py's material for these pictures.
# Needs Python with numpy and ImageMagick (`magick`).
# arms.py <pack folder> <the player's pictures> [--survey <pictures.tsv>] [--into <era>]
#         [--rough <steel's roughness>] [--masks <folder>]
# --survey: the survey's pictures.tsv, as relief.py takes it, so the relief is relief.py's own.
# --into: an older era's pictures (pyreal-art pictures from its files), for its materials in
#   materials/<era>/; only those the era has.
# --masks: also writes each picture's metal map there, to look at.
import os, re, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import relief
from iron import recipes, size
from relief import option
from masonry import blur

TOOL = 'arms.py'
# Each picture: wholly steel, wholly gold, steel beside leather (faced), or steel and gold beside
# leather (gilt).
ARMS = {
    # Sword blades (0x010002EB on the Training Academy's walls, and the swords players wield).
    '0x05000C53': 'steel',
    # Dagger blades and spear heads (0x010002AE).
    '0x050002A2': 'steel',
    # Studded mace heads (0x010002C3).
    '0x0500029E': 'steel',
    # The dark spiked plate on its stand (0x02001255).
    '0x050025BC': 'steel',
    # Gilt guards and pommels.
    '0x05000C55': 'gold',
    # Grips: gilt bands about a leather wrap.
    '0x05000C54': 'gilt',
    # The heater shield (0x01000305): a steel rim and rivets about a leather face.
    '0x05000FDD': 'faced',
    # The white plate on its stand (0x02000ADD): steel, gilt trim, bosses and lion, leather belts.
    '0x05001D9C': 'gilt',
    '0x05001D9D': 'gilt',
    '0x05001E0E': 'gilt',
}
WHOLE = ('steel', 'gold')
# Steel's and gold's roughness where the picture is plain, how much smoother where painted worn
# bright, and the smoothest and roughest they may be.
ROUGH, BRIGHT, SMOOTHEST, ROUGHEST = 0.35, 0.16, 0.12, 0.8
# A metal's brightening: what its brightest tenth is lifted to (linear), within these bounds.
LIFT, LEAST, MOST = 0.6, 1.0, 2.0
# The warmth (red over blue, against red) below which a texel is grey steel. A warm texel is gold or
# brass where it is light and yellow (its lightness and green against red past these), else leather.
COLD, WARM = 0.18, 0.4
LIGHT, HUE = (0.1, 0.2), (0.4, 0.5)
# A grip's leather is lit as light as its gilt bands, so only the yellowest is gold there.
HUES = {'0x05000C54': (0.75, 0.85)}


def ramp(x, lo, hi):
    return np.clip((x - lo) / (hi - lo), 0, 1)


def metal_of(a, kind, px, hue=HUE):
    """Where the picture is a metal: 1 for steel and gold, 0 for leather, wood and cloth."""
    if kind in WHOLE:
        return np.ones(a.shape[:2], np.float32)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    metal = 1 - ramp((R - B) / (R + 0.03), COLD, WARM)
    if kind == 'gilt':
        L = (a * [0.3, 0.59, 0.11]).sum(-1)
        metal = np.maximum(metal, ramp(L, *LIGHT) * ramp(G / (R + 0.03), *hue))
    # A speck of grey grain in the leather is leather; a dark rivet held in steel is steel.
    near = lambda m: blur(m, 1.5 * px)
    metal = metal * np.clip((near(metal) - 0.25) / 0.2, 0, 1)
    metal = np.maximum(metal, np.clip((near(metal) - 0.55) / 0.2, 0, 1))
    return blur(metal, 0.5 * px)


def linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def arm(pack, pictures, sub, id, kind, entry, seen, print_, rough, masks):
    """The picture's relief by relief.py, its steel and gold made smooth and metal, and its [[material]]."""
    out = os.path.join(pack, 'materials', sub)
    _, block, why = relief.make((os.path.join(pictures, id + '.png'), out, entry, seen, 256, 128, sub, print_))
    if not block:
        print(id, why)
        return ''
    at = lambda part: os.path.join(out, f'{id}_{part}.png')
    w, h = size(at('roughness'))
    a = relief.read(os.path.join(pictures, id + '.png'), w, h)[..., :3]
    px = w / a.shape[1]
    r = relief.read(at('roughness'), w, h)[..., 0]
    metal = metal_of(a, kind, px, HUES.get(id, HUE))
    # Worn bright: the picture's own highlights, against its middle.
    L = (a * [0.3, 0.59, 0.11]).sum(-1)
    mid, top = np.percentile(L, 50), np.percentile(L, 99)
    bright = np.clip((L - mid) / (top - mid + 1e-5), 0, 1)
    smooth = np.clip(rough - BRIGHT * bright + 0.5 * (r - np.median(r)), SMOOTHEST, ROUGHEST)
    relief.grey(at('roughness'), r + (smooth - r) * metal)
    # Lifted toward what it mirrors: a dark metal twice, a bright one not past its own picture.
    lum = (linear(a) * [0.2126, 0.7152, 0.0722]).sum(-1)
    lit = np.percentile(lum[metal > 0.5], 90) if (metal > 0.5).any() else LIFT
    brighten = round(float(np.clip(LIFT / max(lit, 1e-3), LEAST, MOST)), 2)
    tail = f'brighten = {brighten:g}\n'
    if kind in WHOLE:
        tail = 'metal = true\n' + tail
        block = re.sub(r'^grit = "grit/[a-z]+\.png"$', 'grit = "grit/metal.png"', block, flags=re.M)
    else:
        relief.grey(at('metal'), metal)
        tail = f'metal_map = "materials/{sub}{id}_metal.png"\n' + tail
    if masks:
        relief.grey(os.path.join(masks, f'{id}_metal.png'), metal)
    block = block.replace('keep_retail_picture = true\n', 'keep_retail_picture = true\n' + tail)
    block = re.sub(r'^author = .*$', f'author = "Worked out from the player\'s own picture by {TOOL} with relief.py"', block, flags=re.M)
    block = re.sub(r'^tool = .*$', f'tool = "{TOOL} relief.py"', block, flags=re.M)
    print(id, kind, f'{w}x{h}', f'brighten {brighten:g}', f'metal {metal.mean():.2f}')
    return block.strip('\n')


def main(args):
    pack, pictures = args[:2]
    rough = float(option(args, '--rough', ROUGH))
    era = option(args, '--into', None)
    sub = f'{era}/' if era else ''
    masks = option(args, '--masks', None)
    if masks:
        os.makedirs(masks, exist_ok=True)
    seen = relief.survey_of(option(args, '--survey', None))
    path = os.path.join(pack, 'manifest.toml')
    blocks = re.split(r'\n(?=\[\[)', open(path).read())
    texture = lambda b: (re.search(r'^texture = "(0x[0-9A-Fa-f]{8})"$', b, re.M) or [None, None])[1]
    # Only this era's materials: those directly in materials/, or in materials/<era>/.
    where = rf'^base_color = "materials/{re.escape(sub)}[^/"]+"$'
    listed = recipes()
    made = 0
    for i, b in enumerate(blocks):
        id = texture(b) if b.startswith('[[material]]') else None
        if id not in ARMS or not re.search(rf'^tool = "(relief\.py|{TOOL} relief\.py)"$', b, re.M):
            continue
        if not re.search(where, b, re.M):
            continue
        if not os.path.exists(os.path.join(pictures, id + '.png')):
            print(id, 'is not among the pictures; its material is kept')
            continue
        print_ = ''.join(re.findall(r'^fingerprint = .*\n', b + '\n', re.M))
        new = arm(pack, pictures, sub, id, ARMS[id], listed.get(id), seen.get(id), print_, rough, masks)
        if new:
            # Each in its place, so the manifest's other entries keep their order.
            blocks[i] = new + '\n'
            made += 1
    open(path, 'w').write('\n'.join(blocks))
    print(made, 'materials of arms and armour')


if __name__ == '__main__':
    main(sys.argv[1:])
