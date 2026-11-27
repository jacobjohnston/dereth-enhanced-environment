#!/usr/bin/env python3
# End of Retail's setups that build a pack model's retail object again under another id (its parts, or parts
# of the same shape), drawn as that model: scaled where the setup scales the parts, with its leaves toned where
# the setup's picture differs (the giant tree report, 2026-11-24). Each gets a [[model]] after the pack's
# others, draws_on "matching", so `pyreal-art fingerprint` names End of Retail's record of it; a changed model
# gets files of its own, `<id>_eor_lod<n>`. Run it after the models it copies are finished; a second run
# changes nothing.
# twins.py <pack folder>
import json, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import variants

# id: (the pack model it is drawn as, its scale, the factor on that model's leaf colour or None).
TWINS = {
    # The giant elm's parts at 1.5 times their size.
    '0x02000325': ('0x02000251', 1.5, None),
    # The tall spruce's parts.
    '0x02000F06': ('0x020002D3', 1, None),
    # The giant spruce's shape in teal needles: 0x05002B83's mean colour over 0x05002B84's.
    '0x020003A1': ('0x020002DA', 1, (0.312, 1.475, 3.241)),
    # The shrubs' and bushes' shapes; their pictures 0x05002B8C and 0x05003343 are alike.
    '0x020002F1': ('0x02001C34', 1, None),
    '0x02001C35': ('0x020002F6', 1, None),
    '0x02001003': ('0x020002F5', 1, None),
    # The conifer group with one more small part.
    '0x02001C3A': ('0x02001C39', 1, None),
    '0x020007BE': ('0x02000E71', 1, None),
    '0x020007DB': ('0x02000E72', 1, None),
    '0x02000AC0': ('0x02000B38', 1, None),
    '0x02000AC4': ('0x02000B3A', 1, None),
    '0x02000AC6': ('0x02000B3B', 1, None),
    '0x02000AC8': ('0x02000CA6', 1, None),
    '0x02000AC9': ('0x02000CA5', 1, None),
}
# Not here: the braziers 0x02000104, 0x02000286-0287, 0x020005B5, 0x02000625-062A build 0x02000285 again, but its
# embers lie over the retail brazier only for the ids Pyreal's art_pack::lays_over names.
TOOL = 'twins.py'


def blocks(text):
    """The manifest cut before each table, as (its header, its text)."""
    cuts = [m.start() for m in re.finditer(r'(?m)^\[\[?[\w.]+\]\]?$', text)]
    return [(text[a:b].split('\n', 1)[0], text[a:b]) for a, b in zip(cuts, cuts[1:] + [len(text)])], text[:cuts[0]]


def field(block, key):
    m = re.search(rf'(?m)^{key} = (.*)$', block)
    return m and m.group(1)


def copy(trees, src, dst, scale, tone):
    """`src`'s glTF and buffer as `dst`, grown by `scale` about its foot, its leaves' colour times `tone`."""
    g = json.load(open(os.path.join(trees, src + '.gltf')))
    for b in g['buffers']:
        shutil.copyfile(os.path.join(trees, b['uri']), os.path.join(trees, dst + '.bin'))
        b['uri'] = dst + '.bin'
    for node in g['nodes']:
        if 'mesh' in node:
            node['scale'] = [c * scale for c in node.get('scale', [1, 1, 1])]
            if 'translation' in node:
                node['translation'] = [c * scale for c in node['translation']]
    if tone:
        for m in g['materials']:
            if m.get('name') == 'Leaves':
                f = m['pbrMetallicRoughness']['baseColorFactor']
                f[:3] = [min(1, round(c * k, 3)) for c, k in zip(f, tone)]
    json.dump(g, open(os.path.join(trees, dst + '.gltf'), 'w'))


def main(pack):
    path = os.path.join(pack, 'manifest.toml')
    listed, head = blocks(variants.flat(open(path).read()))
    # Drop this script's own entries (each [[model]] with its levels), so a second run writes the same.
    kept, mine, stamped = [], False, {}
    for h, b in listed:
        if h == '[[model]]':
            mine = field(b, 'tool') == f'"{TOOL}"'
            if mine and field(b, 'fingerprint'):
                stamped[json.loads(field(b, 'id'))] = field(b, 'fingerprint')
        elif h != '[[model.lod]]':
            mine = False
        if not mine:
            kept.append((h, b))
    models = {}
    for k, (h, b) in enumerate(kept):
        if h == '[[model]]' and field(b, 'draws_on') == '"any"':
            models[json.loads(field(b, 'id'))] = k
    out = []
    for i, (twin, scale, tone) in TWINS.items():
        k = models[twin]
        b = kept[k][1]
        entry = f'[[model]]\nid = "{i}"\n' + (f'fingerprint = {stamped[i]}\n' if i in stamped else '') + 'draws_on = "matching"\n'
        for key in ('foliage', 'wind', 'author'):
            entry += f'{key} = {field(b, key)}\n'
        entry += f'tool = "{TOOL}"\nlicense = {field(b, "license")}\n\n'
        n = 0
        for h, lod in kept[k + 1:]:
            if h != '[[model.lod]]':
                break
            file = json.loads(field(lod, 'file'))
            if scale != 1 or tone:
                name = f'{i}_eor_lod{n}'
                copy(os.path.join(pack, 'trees'), os.path.basename(file)[:-5], name, scale, tone)
                lod = lod.replace(file, f'trees/{name}.gltf')
            entry += lod
            n += 1
        out.append(entry)
        print(f'{i}: {twin}' + (f' x{scale}' if scale != 1 else '') + (' toned' if tone else '') + f', {n} levels')
    # After the last model's levels.
    last = max(k for k, (h, _) in enumerate(kept) if h in ('[[model]]', '[[model.lod]]'))
    text = head + ''.join(b for _, b in kept[:last + 1])
    text = text.rstrip('\n') + '\n\n' + '\n'.join(e.rstrip('\n') + '\n' for e in out) + '\n' + ''.join(b for _, b in kept[last + 1:])
    open(path, 'w').write(variants.settle(text))


if __name__ == '__main__':
    main(sys.argv[1])
