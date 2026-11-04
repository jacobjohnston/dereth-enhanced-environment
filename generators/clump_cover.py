# Rebuilds a ground cover kind's levels as clumps of its tufts, so a plant covers a patch of ground
# rather than a point. Each level's clump is made of its next level's thinner tuft (the last of its
# own), so it costs little more than one full tuft. The single tufts gen_pack.mjs wrote are kept
# in <pack folder>/../clump-sources and always read from there, so it can be run again.
# clump_cover.py <pack folder> <kind> <tufts a clump at each level, e.g. 4 3 2>
import json, math, os, random, shutil, struct, sys
PACK, KIND = sys.argv[1:3]
COUNTS = [int(n) for n in sys.argv[3:]]
TREES = os.path.join(PACK, 'trees')
KEPT = os.path.join(os.path.dirname(os.path.abspath(PACK)), 'clump-sources')
# How far from the clump's middle its outer tufts stand, metres, and how large they are.
RING = (0.14, 0.24)
OUTER = (0.6, 0.9)
WIDTHS = {'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'SCALAR': 1}

def source(level):
    name = f'cover_{KIND}_lod{level}'
    os.makedirs(KEPT, exist_ok=True)
    for ext in ('gltf', 'bin'):
        if not os.path.exists(os.path.join(KEPT, f'{name}.{ext}')):
            shutil.copy2(os.path.join(TREES, f'{name}.{ext}'), KEPT)
    return name

def read(name):
    g = json.load(open(os.path.join(KEPT, f'{name}.gltf')))
    raw = open(os.path.join(KEPT, f'{name}.bin'), 'rb').read()
    def accessor(i):
        a = g['accessors'][i]
        v = g['bufferViews'][a['bufferView']]
        n = a['count'] * WIDTHS[a['type']]
        fmt = '<%d%s' % (n, 'f' if a['componentType'] == 5126 else 'I')
        flat = struct.unpack_from(fmt, raw, v['byteOffset'] + a.get('byteOffset', 0))
        w = WIDTHS[a['type']]
        return [flat[k:k + w] for k in range(0, n, w)] if w > 1 else list(flat)
    p = g['meshes'][0]['primitives'][0]
    attrs = {k: accessor(i) for k, i in p['attributes'].items()}
    return g, attrs, accessor(p['indices'])

def clump(attrs, index, count, seed):
    rng = random.Random(seed)
    out = {k: [] for k in attrs}
    out_index = []
    start = rng.uniform(0, math.tau)
    for c in range(count):
        if c == 0:
            dx = dz = 0.0
            size = 1.0
        else:
            angle = start + math.tau * c / (count - 1) + rng.uniform(-0.5, 0.5)
            ring = rng.uniform(*RING)
            dx, dz = ring * math.cos(angle), ring * math.sin(angle)
            size = rng.uniform(*OUTER)
        turn = rng.uniform(0, math.tau)
        cs, sn = math.cos(turn), math.sin(turn)
        shade = rng.uniform(0.9, 1.05)
        base = len(out['POSITION'])
        for x, y, z in attrs['POSITION']:
            out['POSITION'].append((size * (cs * x + sn * z) + dx, size * y, size * (-sn * x + cs * z) + dz))
        for x, y, z in attrs.get('NORMAL', []):
            out['NORMAL'].append((cs * x + sn * z, y, -sn * x + cs * z))
        out['TEXCOORD_0'] += attrs.get('TEXCOORD_0', [])
        for r, gr, b, a in attrs.get('COLOR_0', []):
            out['COLOR_0'].append((min(r * shade, 1), min(gr * shade, 1), min(b * shade, 1), a))
        out_index += [base + i for i in index]
    return out, out_index

def write(name, g, attrs, index):
    order = list(g['meshes'][0]['primitives'][0]['attributes'].items())
    blob, views, accessors = b'', [], []
    for key, i in order:
        rows = attrs[key]
        a = dict(g['accessors'][i])
        data = struct.pack('<%df' % (len(rows) * len(rows[0])), *[v for r in rows for v in r])
        views.append({'buffer': 0, 'byteOffset': len(blob), 'byteLength': len(data), 'target': 34962})
        a.update(bufferView=len(views) - 1, count=len(rows))
        if key == 'POSITION':
            a['min'] = [min(r[k] for r in rows) for k in range(3)]
            a['max'] = [max(r[k] for r in rows) for k in range(3)]
        accessors.append(a)
        blob += data
    data = struct.pack('<%dI' % len(index), *index)
    views.append({'buffer': 0, 'byteOffset': len(blob), 'byteLength': len(data), 'target': 34963})
    accessors.append({'bufferView': len(views) - 1, 'componentType': 5125, 'count': len(index), 'type': 'SCALAR'})
    blob += data
    g['meshes'][0]['primitives'][0]['attributes'] = {key: k for k, (key, _) in enumerate(order)}
    g['meshes'][0]['primitives'][0]['indices'] = len(accessors) - 1
    g['accessors'], g['bufferViews'] = accessors, views
    g['buffers'] = [{'uri': f'{name}.bin', 'byteLength': len(blob)}]
    g['asset']['generator'] = 'gen_pack.mjs, clumped by clump_cover.py'
    json.dump(g, open(os.path.join(TREES, f'{name}.gltf'), 'w'))
    open(os.path.join(TREES, f'{name}.bin'), 'wb').write(blob)

names = [source(level) for level in range(len(COUNTS))]
for level, count in enumerate(COUNTS):
    g, _, _ = read(names[level])
    _, attrs, index = read(names[min(level + 1, len(names) - 1)])
    attrs, index = clump(attrs, index, count, 7151 + level)
    write(names[level], g, attrs, index)
    print(f'{names[level]}: {count} tufts, {len(index) // 3} triangles')
