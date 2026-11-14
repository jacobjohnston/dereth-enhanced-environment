# Stores the pack's models in fewer bytes, as glTF's KHR_mesh_quantization allows: positions as
# 16-bit integers inside the model's box, which its node scales and moves back; normals as 8-bit
# integers; picture coordinates as 16-bit integers where they lie within -1..1; colours as 16-bit
# integers where they lie within 0..1, and none where they are all white; indices as 16-bit numbers.
# What would not fit, or would move a point more than POSITION_ERROR, stays as it was. Run it last,
# after gen_pack.mjs, clump_cover.py, foliage.py, boulders.py, cactus.py and reshape.mjs, since they
# read and write the models as floats; a second run changes nothing.
# Needs only Python.
# quantise.py <pack folder>
import array, json, math, os, struct, sys

# The most a position may move, metres: a model whose box needs more keeps its float positions.
POSITION_ERROR = 0.001
FLOAT, U32, U16, I16, I8 = 5126, 5125, 5123, 5122, 5120
WIDTHS = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}
VERTEX, INDEX = 34962, 34963


def floats(doc, raw, i):
    a = doc['accessors'][i]
    v = doc['bufferViews'][a['bufferView']]
    w = WIDTHS[a['type']]
    stride = v.get('byteStride', 4 * w)
    start = v.get('byteOffset', 0) + a.get('byteOffset', 0)
    if stride == 4 * w:
        return array.array('f', raw[start:start + 4 * w * a['count']]).tolist()
    return [x for e in range(a['count']) for x in struct.unpack_from(f'<{w}f', raw, start + e * stride)]


def packed(doc, raw, i):
    """Accessor `i`'s bytes as they stand, tightly packed when its view has no stride."""
    a = doc['accessors'][i]
    v = doc['bufferViews'][a['bufferView']]
    start = v.get('byteOffset', 0) + a.get('byteOffset', 0)
    return raw[start:start + v['byteLength'] - a.get('byteOffset', 0)], v.get('byteStride')


def ints(values, scale, code):
    lo, hi = {I8: (-127, 127), I16: (-32767, 32767), U16: (0, 65535)}[code]
    return [min(hi, max(lo, round(x * scale))) for x in values]


def padded(values, width, per):
    """`values`, `width` a vertex, with zeros after each vertex up to `per`."""
    if per == width:
        return values
    out = []
    for k in range(0, len(values), width):
        out += values[k:k + width] + [0] * (per - width)
    return out


def box(doc, raw, ids):
    """The middle and half the largest side of the positions of accessors `ids`."""
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    for i in ids:
        p = floats(doc, raw, i)
        for c in range(3):
            lo[c] = min(lo[c], min(p[c::3]))
            hi[c] = max(hi[c], max(p[c::3]))
    middle = [(lo[c] + hi[c]) / 2 for c in range(3)]
    half = max(hi[c] - lo[c] for c in range(3)) / 2 or 1.0
    return middle, half


def quantise(path):
    """Rewrite the model at `path` in fewer bytes: the largest position error, metres, or None when
    nothing changed."""
    doc = json.load(open(path))
    folder = os.path.dirname(path)
    if len(doc.get('buffers', [])) != 1 or any('bufferView' in i for i in doc.get('images', [])):
        print(f'{path}: not one buffer of vertices alone; left as it is')
        return None
    raw = open(os.path.join(folder, doc['buffers'][0]['uri']), 'rb').read()
    acc = doc['accessors']
    nodes = doc.get('nodes', [])
    # A mesh's positions share one box, so one node transform restores them all.
    moves = {}
    for m, mesh in enumerate(doc['meshes']):
        ids = [p['attributes']['POSITION'] for p in mesh['primitives']]
        users = [n for n in nodes if n.get('mesh') == m]
        others = [p for k, x in enumerate(doc['meshes']) if k != m for p in x['primitives']]
        if (any(acc[i]['componentType'] != FLOAT for i in ids) or not users
                or any('children' in n or 'skin' in n for n in users)
                or any('targets' in p for p in mesh['primitives'])
                or any(p['attributes'].get('POSITION') in ids for p in others)):
            continue
        middle, half = box(doc, raw, ids)
        if half / 32767 / 2 <= POSITION_ERROR:
            moves[m] = (middle, half)
    out, views, accessors, done = bytearray(), [], [], {}
    worst = 0.0
    changed = False

    def put(data, accessor, target, stride=None):
        while len(out) % 4:
            out.append(0)
        view = {'buffer': 0, 'byteOffset': len(out), 'byteLength': len(data), 'target': target}
        if stride:
            view['byteStride'] = stride
        views.append(view)
        out.extend(data)
        accessor['bufferView'] = len(views) - 1
        accessor.pop('byteOffset', None)
        accessors.append(accessor)
        return len(accessors) - 1

    def keep(i, target):
        data, stride = packed(doc, raw, i)
        return put(data, dict(acc[i]), target, stride)

    for m, mesh in enumerate(doc['meshes']):
        for p in mesh['primitives']:
            attrs = {}
            for name, i in p['attributes'].items():
                if i in done:
                    attrs[name] = done[i]
                    continue
                a = dict(acc[i])
                code = a['componentType']
                if code != FLOAT:
                    attrs[name] = done[i] = keep(i, VERTEX)
                    continue
                v = floats(doc, raw, i)
                w = WIDTHS[a['type']]
                if name == 'POSITION' and m in moves:
                    middle, half = moves[m]
                    q = ints([(x - middle[k % 3]) / half for k, x in enumerate(v)], 32767, I16)
                    for k, x in enumerate(v):
                        worst = max(worst, abs(middle[k % 3] + half * q[k] / 32767 - x))
                    a.update(componentType=I16, normalized=True,
                             min=[min(q[c::3]) for c in range(3)], max=[max(q[c::3]) for c in range(3)])
                    attrs[name] = done[i] = put(struct.pack(f'<{len(q) // 3 * 4}h', *padded(q, 3, 4)), a, VERTEX, 8)
                elif name in ('NORMAL', 'TANGENT'):
                    q = ints(v, 127, I8)
                    a.update(componentType=I8, normalized=True)
                    attrs[name] = done[i] = put(struct.pack(f'<{len(q) // w * 4}b', *padded(q, w, 4)), a, VERTEX,
                                                4 if w == 3 else None)
                elif name.startswith('TEXCOORD') and min(v) >= -1 and max(v) <= 1:
                    code = U16 if min(v) >= 0 else I16
                    q = ints(v, 65535 if code == U16 else 32767, code)
                    a.update(componentType=code, normalized=True)
                    attrs[name] = done[i] = put(struct.pack(f'<{len(q)}{"H" if code == U16 else "h"}', *q), a, VERTEX)
                elif name.startswith('COLOR') and all(x == 1 for x in v):
                    pass  # all white, which is what a model without colours is drawn as
                elif name.startswith('COLOR') and min(v) >= 0 and max(v) <= 1:
                    q = ints(v, 65535, U16)
                    a.update(componentType=U16, normalized=True)
                    attrs[name] = done[i] = put(struct.pack(f'<{len(q)}H', *q), a, VERTEX)
                else:
                    attrs[name] = done[i] = keep(i, VERTEX)
                    continue
                changed = True
            p['attributes'] = attrs
            if 'indices' in p:
                i = p['indices']
                a = dict(acc[i])
                if i in done:
                    p['indices'] = done[i]
                elif a['componentType'] == U32 and a['count'] and max(indices(doc, raw, i)) < 65535:
                    q = indices(doc, raw, i)
                    a.update(componentType=U16)
                    a.pop('min', None), a.pop('max', None)
                    p['indices'] = done[i] = put(struct.pack(f'<{len(q)}H', *q), a, INDEX)
                    changed = True
                else:
                    p['indices'] = done[i] = keep(i, INDEX)
    if not changed:
        return None
    for m, (middle, half) in moves.items():
        for n in nodes:
            if n.get('mesh') == m:
                place(n, middle, half)
    doc['accessors'], doc['bufferViews'] = accessors, views
    doc['buffers'][0]['byteLength'] = len(out)
    used = doc.setdefault('extensionsUsed', [])
    if 'KHR_mesh_quantization' not in used:
        # Not in extensionsRequired: Pyreal refuses a model that requires any extension.
        used.append('KHR_mesh_quantization')
    gen = doc['asset'].get('generator', '')
    if 'quantise.py' not in gen:
        doc['asset']['generator'] = f'{gen}, quantised by quantise.py' if gen else 'quantise.py'
    open(os.path.join(folder, doc['buffers'][0]['uri']), 'wb').write(out)
    json.dump(doc, open(path, 'w'), indent=1)
    return worst


def indices(doc, raw, i):
    a = doc['accessors'][i]
    v = doc['bufferViews'][a['bufferView']]
    start = v.get('byteOffset', 0) + a.get('byteOffset', 0)
    return array.array('I', raw[start:start + 4 * a['count']]).tolist()


def place(node, middle, half):
    """Make `node` scale its mesh's positions by `half` and move them to `middle`, after its own
    transform."""
    if 'matrix' in node:
        m = node['matrix']
        t = [m[12 + r] + sum(m[4 * c + r] * middle[c] for c in range(3)) for r in range(3)]
        node['matrix'] = [x * half for x in m[:12]] + t + [m[15]]
        return
    q = node.get('rotation', [0, 0, 0, 1])
    s = node.get('scale', [1, 1, 1])
    v = [s[c] * middle[c] for c in range(3)]
    x, y, z, w = q
    # v turned by the quaternion q.
    u = [y * v[2] - z * v[1], z * v[0] - x * v[2], x * v[1] - y * v[0]]
    u = [2 * c for c in u]
    turned = [v[0] + w * u[0] + y * u[2] - z * u[1],
              v[1] + w * u[1] + z * u[0] - x * u[2],
              v[2] + w * u[2] + x * u[1] - y * u[0]]
    t = node.get('translation', [0, 0, 0])
    node['translation'] = [t[c] + turned[c] for c in range(3)]
    node['scale'] = [c * half for c in s]


if __name__ == '__main__':
    pack = sys.argv[1]
    before = after = count = 0
    worst = 0.0
    for root, _, files in os.walk(pack):
        for name in sorted(files):
            if not name.endswith('.gltf'):
                continue
            path = os.path.join(root, name)
            bin_path = lambda: os.path.join(root, json.load(open(path))['buffers'][0]['uri'])
            was = os.path.getsize(bin_path())
            err = quantise(path)
            if err is not None:
                count += 1
                worst = max(worst, err)
                before += was
                after += os.path.getsize(bin_path())
    print(f'{count} models quantised: {before / 1e6:.1f} MB of buffers into {after / 1e6:.1f} MB; '
          f'positions moved at most {worst * 1000:.3f} mm')
