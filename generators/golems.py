# Golems drawn as what they are made of: a [[material]] for each family of the golems' retail pictures
# that keeps the picture (`keep_retail_picture`) and says what it is: the metal golems' metal, the
# ice golems' ice and the gem golems' crystal, clear in their own colour and bending what lies
# behind them, the mud golems' mud wet as a puddle, and how smooth obsidian and stone are. One picture serves several golems, told
# apart by palette (iron, gold, platinum and pyreal), so a family takes one material. Writes a flat
# base colour for each, for a reader that draws no retail picture; nothing of any picture's pixels
# goes into the pack. Replaces any other generator's material for these pictures.
# The mud golems' pictures, given the player's own (the golem palette's) in a folder, are shaped by
# relief.py's organic recipe into deep lobes and grooves, wet and glossy as fresh mud: nothing of
# their pixels goes into the pack. Without the folder an earlier run's mud maps are kept.
# The 1999 golems are one model with one picture (FAMILIES_1999), told apart by the palette their
# palette template lays over it, so each of their materials names the palettes it is drawn in.
# Needs Python with numpy and ImageMagick (`magick`).
# golems.py <pack folder> [<the golems' pictures>]
import glob, os, re, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

TOOL = 'golems.py'
# The mud golems' pictures, each shaped from the player's own.
MUD = ['0x050018B7', '0x050018B8', '0x050018B9']
# How strongly mud's relief bends it, and how rough its wet face is in its grooves and on its lobes.
MUD_BEND = 2.0
MUD_ROUGH = (0.03, 0.09)
# How much of relief.py's depth the mud keeps, and the share of each side of a picture over which
# it flattens toward the edge: the golems' parts are small, so a view along one slides far across
# its picture, and over the edge it would show the picture's dark border.
MUD_DEPTH = 0.65
MUD_EDGE = 0.18

# Each family: its name, its retail pictures, its flat colour and what it is made of.
FAMILIES = [
    ('golem-metal', ['0x050018CB', '0x050018CC', '0x050018CD', '0x050018BF', '0x050018C0', '0x050018C8'],
     (0.55, 0.53, 0.5), 'metal = true\nbrighten = 4.5\ngloss = 0.72'),
    ('golem-ice', ['0x050018D0', '0x050018D1'], (0.45, 0.62, 0.85), 'clear = 0.5\nrefraction = 1.31'),
    ('golem-gem', ['0x050018C9', '0x0500190C'], (0.75, 0.74, 0.8), 'clear = 0.7\nrefraction = 2.0'),
    ('golem-obsidian', ['0x050018CE', '0x050018CF'], (0.12, 0.11, 0.15), 'gloss = 0.84'),
    ('golem-mud', MUD, (0.45, 0.25, 0.14), 'wet = 0.85'),
    ('golem-stone', ['0x050018BA', '0x050018BB', '0x050018BC', '0x05002C05', '0x05002C06'],
     (0.33, 0.3, 0.24), 'gloss = 0.15'),
]


# The 1999 golems' one picture, and each family: its name, the palettes its golems wear (from
# clothing 0x100000C3's palette templates; the mud golem has none, so its picture's own), its flat
# colour and what it is made of. The wood golem keeps its retail look.
GOLEM_1999 = '0x05001310'
FAMILIES_1999 = [
    ('golem-1999-metal', ['0x04000BA1', '0x04000B9F'], (0.45, 0.25, 0.12), 'metal = true\nbrighten = 2.5\ngloss = 0.72'),
    ('golem-1999-ice', ['0x04000BA3'], (0.45, 0.62, 0.85), 'clear = 0.5\nrefraction = 1.31'),
    # Not clear: a clear material takes its tint from its picture's hue alone, and the water's would
    # match the ice's; wet keeps its dark blue.
    ('golem-1999-water', ['0x04000BA2'], (0.1, 0.3, 0.45), 'wet = 0.9'),
    ('golem-1999-obsidian', ['0x04000BA0'], (0.12, 0.11, 0.15), 'gloss = 0.84'),
    ('golem-1999-stone', ['0x04000B9E', '0x04000BA7', '0x04000BA4', '0x04000BA5'], (0.33, 0.3, 0.24), 'gloss = 0.15'),
    ('golem-1999-mud', ['0x04000B9D'], (0.3, 0.22, 0.15), 'wet = 0.85'),
]

def write_flat(path, rgb):
    px = bytes(int(c * 255 + 0.5) for c in rgb) + b'\xff'
    subprocess.run(['magick', '-define', 'png:exclude-chunks=date,time', '-size', '4x4', '-depth', '8', 'rgba:-', path],
                   input=px * 16, check=True)


def mud(pack, pictures):
    """Each mud picture's relief, wet and glossy, as a material of its own; none without the pictures."""
    import relief
    out = os.path.join(pack, 'materials')
    tables = ''
    for id in MUD:
        path = os.path.join(pictures, id + '.png')
        if not os.path.exists(path):
            continue
        _, block, why = relief.make((path, out, ('mud', 'organic', 0.0, []), None, 256, 128))
        if not block:
            print(id, why)
            continue
        # Glossy where the water lies in its grooves, a little less on its lobes.
        h = relief.read(os.path.join(out, f'{id}_height.png'), *relief_size(out, id))[..., 0]
        y, x = (np.mgrid[0:h.shape[0], 0:h.shape[1]] + 0.5) / [[[h.shape[0]]], [[h.shape[1]]]]
        edge = np.clip(np.minimum(np.minimum(x, 1 - x), np.minimum(y, 1 - y)) / MUD_EDGE, 0, 1)
        h = 1 - MUD_DEPTH * (1 - h) * (edge * edge * (3 - 2 * edge))
        relief.grey(os.path.join(out, f'{id}_height.png'), h)
        relief.grey(os.path.join(out, f'{id}_roughness.png'), MUD_ROUGH[0] + (MUD_ROUGH[1] - MUD_ROUGH[0]) * h)
        for f in glob.glob(os.path.join(out, f'{id}_damp.png')):
            os.remove(f)
        block = re.sub(r'^(damp|damp_map|damp_floors|grit|grit_repeat) = .*\n', '', block, flags=re.M)
        block = block.replace('keep_retail_picture = true\n', f'keep_retail_picture = true\nnormal_scale = {MUD_BEND}\nwet = 0.85\n')
        block = re.sub(r'^author = .*$', f'author = "Worked out from the player\'s own picture by {TOOL} with relief.py"', block, flags=re.M)
        block = re.sub(r'^tool = .*$', f'tool = "{TOOL} relief.py"', block, flags=re.M)
        tables += block
    return tables


def relief_size(out, id):
    w, h = subprocess.run(['identify', '-format', '%w %h', os.path.join(out, f'{id}_height.png')],
                          capture_output=True, text=True, check=True).stdout.split()
    return int(w), int(h)


def main(pack, pictures=None):
    out = os.path.join(pack, 'materials'); os.makedirs(out, exist_ok=True)
    path = os.path.join(pack, 'manifest.toml')
    blocks = re.split(r'\n(?=\[\[)', open(path).read())
    ours = {t for _, ts, _, _ in FAMILIES for t in ts} | {GOLEM_1999}
    texture = lambda b: set(re.findall(r'0x[0-9A-Fa-f]{8}', (re.search(r'^texture = (.*)$', b, re.M) or [None, ''])[1]))
    gone = [b for b in blocks if b.startswith('[[material]]') and (texture(b) & ours or re.search(rf'^tool = "{TOOL}', b, re.M))]
    if not pictures:
        # Without the pictures, the mud shaped by an earlier run stays.
        gone = [b for b in gone if not re.search(rf'^tool = "{TOOL} relief.py"$', b, re.M)]
    kept = [b for b in blocks if b not in gone]
    # The pictures only the materials that go named go with them.
    keep = set(re.findall(r'"(materials/[^"]+\.png)"', '\n'.join(kept)))
    for b in gone:
        for f in re.findall(r'"(materials/[^"]+\.png)"', b):
            if f not in keep and os.path.exists(os.path.join(pack, f)):
                os.remove(os.path.join(pack, f))
    shaped = mud(pack, pictures) if pictures else ''
    tables = shaped
    for name, ts, rgb, what in FAMILIES:
        if name == 'golem-mud' and (shaped or any(f'tool = "{TOOL} relief.py"' in b for b in kept)):
            continue
        base = f'materials/{name}_fallback.png'
        write_flat(os.path.join(pack, base), rgb)
        tables += (f'\n[[material]]\ntexture = [{", ".join(chr(34) + t + chr(34) for t in ts)}]\n'
                   f'base_color = "{base}"\nkeep_retail_picture = true\n{what}\n'
                   f'author = "Generated by {TOOL}"\ntool = "{TOOL}"\nlicense = "CC0-1.0"\n')
    for name, palettes, rgb, what in FAMILIES_1999:
        base = f'materials/{name}_fallback.png'
        write_flat(os.path.join(pack, base), rgb)
        tables += (f'\n[[material]]\ntexture = "{GOLEM_1999}"\n'
                   f'palettes = [{", ".join(chr(34) + p + chr(34) for p in palettes)}]\n'
                   f'base_color = "{base}"\nkeep_retail_picture = true\n{what}\n'
                   f'author = "Generated by {TOOL}"\ntool = "{TOOL}"\nlicense = "CC0-1.0"\n')
    open(path, 'w').write('\n'.join(kept).rstrip('\n') + '\n' + tables)
    print(len(FAMILIES) + len(FAMILIES_1999), 'materials for', len(ours), 'pictures;', len(gone), 'replaced')


if __name__ == '__main__':
    main(*sys.argv[1:3])
