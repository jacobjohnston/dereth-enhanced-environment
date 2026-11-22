#!/usr/bin/env python3
# Draws the grown trees with fewer triangles and the same look. For each level it rebuilds each
# branch from every `step`th of its rings, drops the branches too thin to see where the level
# begins, and may draw each crossed pair of leaf cards as one card, grown so the crown keeps its
# cover. The trunk and the root ball are left as they are.
# Run after gen_pack.mjs, fit_trunks.py, taper_trunks.py and scale_models.py; it quantises what it
# writes itself, so quantise.py need not run again. A second run changes nothing.
#
# slim_trees.py <pack folder> [<id>...]   the ids default to every model in CONIFERS and ROUND
import json, math, os, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quantise  # noqa: E402

MARK = 'slimmed by slim_trees.py'
COMP = {5126: ('f', 4), 5125: ('I', 4), 5123: ('H', 2), 5122: ('h', 2), 5121: ('B', 1), 5120: ('b', 1)}
WIDTHS = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}
UNIT = {5122: 32767, 5120: 127, 5123: 65535, 5121: 255}

# Each level: rings kept a branch (every `step`th), the least width a branch keeps (a share of the
# trunk's at its foot), and each crossed pair drawn as one card grown by `pair` (both kept for 0).
# The conifers' levels: both cards of a pair kept near, where one alone shows thinner, and the
# branches dropped where the needles hide them. The open-ended last level, which the card takes
# over from, is left as it is.
LEVELS = [
    {'step': 2, 'thin': 0.0, 'pair': 0},
    {'step': 2, 'thin': 0.0, 'pair': 1.25},
    {'step': 2, 'thin': 0.3, 'pair': 1.0},
]
# The round trees' levels: their small leaves read sparser as one card, so they keep their pairs.
ROUND_LEVELS = [
    {'step': 2, 'thin': 0.0, 'pair': 0},
    {'step': 2, 'thin': 0.0, 'pair': 0},
    {'step': 2, 'thin': 0.15, 'pair': 1.0},
]
# How near two cards' middles lie in a crossed pair, metres.
PAIRED = 0.01
# The grown trees slimmed: EZ-Tree's conifers, and its round trees.
CONIFERS = ['0x02000258', '0x02000257', '0x02000256', '0x020002D3', '0x020002D9', '0x020002DA', '0x020002DB',
            '0x020002D8', '0x020003A2', '0x020003A3', '0x020003A4', '0x020003A7', '0x020012FB', '0x0200129A',
            '0x0200129B', '0x020012FE', '0x02001C39', '0x020003A1', '0x02000F06']
ROUND = ['0x02000246', '0x02000240', '0x0200062B']


def read(path):
    """The model's primitives as float lists, its node's transform applied."""
    doc = json.load(open(path))
    raw = open(os.path.join(os.path.dirname(path), doc['buffers'][0]['uri']), 'rb').read()

    def acc(i):
        a = doc['accessors'][i]
        v = doc['bufferViews'][a['bufferView']]
        c, size = COMP[a['componentType']]
        w = WIDTHS[a['type']]
        stride = v.get('byteStride', size * w)
        start = v.get('byteOffset', 0) + a.get('byteOffset', 0)
        unit = UNIT.get(a['componentType']) if a.get('normalized') else None
        out = []
        for e in range(a['count']):
            vals = struct.unpack_from(f'<{w}{c}', raw, start + e * stride)
            out.append([max(-1.0, x / unit) for x in vals] if unit else list(vals))
        return out

    node = doc['nodes'][0]
    s, t = node.get('scale', [1, 1, 1]), node.get('translation', [0, 0, 0])
    prims = []
    for p in doc['meshes'][0]['primitives']:
        a = p['attributes']
        prims.append({
            'material': p['material'],
            'position': [[x[k] * s[k] + t[k] for k in range(3)] for x in acc(a['POSITION'])],
            'normal': acc(a['NORMAL']),
            'uv': acc(a['TEXCOORD_0']),
            'index': [x[0] for x in acc(p['indices'])],
        })
    return doc, prims


def write(path, doc, prims):
    """Write `prims` as floats into the model at `path`, then quantise it."""
    out, views, accessors = bytearray(), [], []

    def put(values, fmt, kind, code, target, extra=None):
        while len(out) % 4:
            out.append(0)
        data = struct.pack(f'<{len(values)}{fmt}', *values)
        views.append({'buffer': 0, 'byteOffset': len(out), 'byteLength': len(data), 'target': target})
        out.extend(data)
        n = len(values) // WIDTHS[kind]
        accessors.append({'bufferView': len(views) - 1, 'componentType': code, 'count': n, 'type': kind,
                          **(extra or {})})
        return len(accessors) - 1

    meshes = []
    for p in prims:
        pos = [x for v in p['position'] for x in v]
        box = {'min': [min(pos[k::3]) for k in range(3)], 'max': [max(pos[k::3]) for k in range(3)]}
        meshes.append({'material': p['material'], 'attributes': {
            'POSITION': put(pos, 'f', 'VEC3', 5126, 34962, box),
            'NORMAL': put([x for v in p['normal'] for x in v], 'f', 'VEC3', 5126, 34962),
            'TEXCOORD_0': put([x for v in p['uv'] for x in v], 'f', 'VEC2', 5126, 34962),
        }, 'indices': put(p['index'], 'I', 'SCALAR', 5125, 34963)})
    doc['meshes'][0]['primitives'] = meshes
    doc['accessors'], doc['bufferViews'] = accessors, views
    doc['buffers'][0]['byteLength'] = len(out)
    doc['nodes'][0] = {'mesh': 0}
    doc['asset']['generator'] = f"{doc['asset'].get('generator', '')}, {MARK}"
    open(os.path.join(os.path.dirname(path), doc['buffers'][0]['uri']), 'wb').write(out)
    json.dump(doc, open(path, 'w'), indent=1)
    quantise.quantise(path)


def compact(p, tris):
    """`p` drawing `tris` (vertex triples) alone, its unused vertices gone."""
    remap = {}
    for t in tris:
        for v in t:
            remap.setdefault(v, len(remap))
    order = sorted(remap, key=remap.get)
    return {**p, 'position': [p['position'][v] for v in order], 'normal': [p['normal'][v] for v in order],
            'uv': [p['uv'][v] for v in order], 'index': [remap[v] for t in tris for v in t]}


def pieces(p):
    """The separate pieces of `p`: each its triangles, as vertex triples."""
    par = list(range(len(p['position'])))

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    tris = [tuple(p['index'][i:i + 3]) for i in range(0, len(p['index']), 3)]
    for a, b, c in tris:
        par[find(b)] = find(a)
        par[find(c)] = find(a)
    out = {}
    for t in tris:
        out.setdefault(find(t[0]), []).append(t)
    return list(out.values())


def tube(p, tris):
    """A grown branch's sides and rings, `(first vertex, sides, rings)`, or None for another shape:
    rings of sides + 1 vertices, the last of each where the first is, one after another."""
    vs = sorted({v for t in tris for v in t})
    first, n = vs[0], len(vs)
    if vs[-1] - first + 1 != n:
        return None
    pos = p['position']
    for sides in range(3, 33):
        if n % (sides + 1) or n // (sides + 1) < 2:
            continue
        if math.dist(pos[first], pos[first + sides]) < 1e-4 and len(tris) == 2 * sides * (n // (sides + 1) - 1):
            return first, sides, n // (sides + 1)
    return None


def width(p, first, sides):
    """A branch's width at its foot ring, metres."""
    ring = p['position'][first:first + sides]
    c = [sum(v[k] for v in ring) / sides for k in range(3)]
    return 2 * sum(math.dist(v, c) for v in ring) / sides


def rebuilt(p, first, sides, rings, step):
    """A branch's triangles drawn from every `step`th ring and its last, its picture's second
    coordinate stretched to the rings kept."""
    kept = list(range(0, rings, step))
    if kept[-1] != rings - 1:
        kept.append(rings - 1)
    # Each ring's picture coordinate along the branch, summed as the original ran.
    along = [0.0]
    for r in range(1, rings):
        along.append(along[-1] + abs(p['uv'][first + r * (sides + 1)][1] - p['uv'][first + (r - 1) * (sides + 1)][1]))
    v0 = p['uv'][first][1]
    for r in kept:
        for j in range(sides + 1):
            p['uv'][first + r * (sides + 1) + j][1] = v0 - along[r]
    tris = []
    for a, b in zip(kept, kept[1:]):
        for j in range(sides):
            v1, v2 = first + a * (sides + 1) + j, first + b * (sides + 1) + j
            tris += [(v1, v2, v1 + 1), (v1 + 1, v2, v2 + 1)]
    return tris


def slim_wood(p, level, trunk):
    """The wood with its branches rebuilt from fewer rings and the thinnest dropped; `trunk` kept as
    it is."""
    out = []
    shape = tube(p, trunk)
    foot = width(p, shape[0], shape[1]) if shape else 0.0
    for tris in pieces(p):
        shape = tube(p, tris)
        if shape is None or tris == trunk:
            out += tris
            continue
        first, sides, rings = shape
        if width(p, first, sides) < level['thin'] * foot:
            continue
        out += rebuilt(p, first, sides, rings, level['step']) if level['step'] > 1 else tris
    return compact(p, out)


def slim_leaves(p, level):
    """The cards with each crossed pair drawn as one card grown by `pair` about its middle, or as
    they were for 0."""
    quads = {}
    for i in range(0, len(p['index']), 3):
        quads.setdefault(p['index'][i] // 4, []).append(tuple(p['index'][i:i + 3]))
    middle = lambda q: [sum(p['position'][q * 4 + v][k] for v in range(4)) / 4 for k in range(3)]
    out, skip = [], set()
    for q in sorted(quads):
        if q in skip:
            continue
        out += quads[q]
        c = middle(q)
        # A crossed pair: the next card about the same middle.
        if q + 1 not in quads or math.dist(c, middle(q + 1)) >= PAIRED:
            continue
        skip.add(q + 1)
        if not level['pair']:
            out += quads[q + 1]
            continue
        for v in range(4):
            pt = p['position'][q * 4 + v]
            p['position'][q * 4 + v] = [c[a] + (pt[a] - c[a]) * level['pair'] for a in range(3)]
    return compact(p, out)


def slim(path, level):
    doc, prims = read(path)
    if MARK in doc['asset'].get('generator', ''):
        return None
    before = sum(len(p['index']) for p in prims) // 3
    out = []
    for p in prims:
        if doc['materials'][p['material']].get('alphaMode', 'OPAQUE') != 'OPAQUE':
            out.append(slim_leaves(p, level))
        else:
            # Each tree of a group is its own wood; its trunk is its largest piece.
            out.append(slim_wood(p, level, max(pieces(p), key=len)))
    out = [p for p in out if p['index']]
    write(path, doc, out)
    return before, sum(len(p['index']) for p in out) // 3


def main():
    pack = sys.argv[1]
    for id_ in sys.argv[2:] or CONIFERS + ROUND:
        counts = []
        for lod, level in enumerate(ROUND_LEVELS if id_ in ROUND else LEVELS):
            path = os.path.join(pack, 'trees', f'{id_}_lod{lod}.gltf')
            if os.path.exists(path):
                counts.append(slim(path, level))
        done = [c for c in counts if c]
        print(f'{id_}: ' + (', '.join(f'{a} to {b}' for a, b in done) + ' triangles' if done else 'already slimmed'))


main()
