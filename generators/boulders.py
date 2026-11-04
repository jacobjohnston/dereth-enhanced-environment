# New boulders that follow an original rock's overall shape: which points of a grid lie inside it,
# a surface of our own drawn through how far each lies from the edge, smoothed until the original's
# facets and edges are gone, roughened with our own noise and wrapped in our own rock pictures. None
# of the original's vertices, faces or picture coordinates is kept, only what is inside it at the
# grid's grain.
# boulders.py <out folder> <meshes folder, from dereth-art mesh> <id>:<picture> [...]
import json, os, sys
import numpy as np
from scipy import ndimage

TOOL = 'boulders.py'
# How many rounds of smoothing the surface takes at the finest level: more is rounder.
SMOOTH = 24
# Grid cells across the rock at the finest level, and at least across its thinnest side.
CELLS, THINNEST = 36, 8
# How far our noise moves the surface, a share of the rock's size, and its grain in metres.
ROUGH = 0.02
ROUGH_SCALE = 0.9
# Metres one repeat of a rock picture covers.
REPEAT = 4.0
# Pictures laid out by height, top to foot, instead of on the box's faces.
BY_HEIGHT = {'0x05002613': 6.2}
# The levels of detail: a share of the finest grid's cells, and how far each is drawn.
LEVELS = ((1.0, 60.0), (0.5, 200.0), (0.25, None))
ISO = 0.0


def triangles(meshes, id):
    groups = json.load(open(os.path.join(meshes, f'{id}.json')))
    return np.array([c[0] for g in groups for c in g['corners']], float).reshape(-1, 3, 3)


def inside(points, tri, foot):
    """Whether each point lies inside the rock: an upward line from it crosses its surface an odd
    number of times. Many rocks are open underneath, so nothing below the foot is inside."""
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    d = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1])
    keep = np.abs(d) > 1e-12
    a, b, c, d = a[keep], b[keep], c[keep], d[keep]
    count = np.zeros(len(points), int)
    for s in range(0, len(points), 4096):
        p = points[s:s + 4096]
        x, y = p[:, None, 0], p[:, None, 1]
        l1 = ((b[:, 1] - c[:, 1]) * (x - c[:, 0]) + (c[:, 0] - b[:, 0]) * (y - c[:, 1])) / d
        l2 = ((c[:, 1] - a[:, 1]) * (x - c[:, 0]) + (a[:, 0] - c[:, 0]) * (y - c[:, 1])) / d
        l3 = 1 - l1 - l2
        z = l1 * a[:, 2] + l2 * b[:, 2] + l3 * c[:, 2]
        hit = (l1 >= 0) & (l2 >= 0) & (l3 >= 0) & (z > p[:, None, 2])
        count[s:s + 4096] = hit.sum(1)
    return (count % 2 == 1) & (points[:, 2] >= foot)


def depth(occupied):
    """How far inside each cell lies (negative outside), in cells, smoothed of the grid's steps."""
    out = ndimage.distance_transform_edt(~occupied) - 0.5
    within = ndimage.distance_transform_edt(occupied) - 0.5
    return ndimage.gaussian_filter(np.where(occupied, within, -out), 1.0)


def taubin(v, f, times):
    """`v` smoothed `times` rounds over the mesh, shrinking as little as it rounds."""
    n = len(v)
    pairs = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    pairs = np.unique(np.sort(np.concatenate([pairs, pairs[:, ::-1]]), 1), axis=0)
    deg = np.bincount(pairs.ravel(), minlength=n).astype(float)
    for _ in range(times):
        for k in (0.5, -0.53):
            mean = np.zeros_like(v)
            np.add.at(mean, pairs[:, 0], v[pairs[:, 1]])
            np.add.at(mean, pairs[:, 1], v[pairs[:, 0]])
            v = v + k * (mean / np.maximum(deg, 1)[:, None] - v)
    return v


def surface_nets(f, origin, step):
    """A vertex in each cell the surface `f` = ISO crosses, at the mean of its crossings, and a quad
    across each grid edge it crosses."""
    s = f > ISO
    n = np.array(f.shape)
    offs = np.array([(i, j, k) for i in (0, 1) for j in (0, 1) for k in (0, 1)])
    corners = np.stack([s[i:n[0] - 1 + i, j:n[1] - 1 + j, k:n[2] - 1 + k] for i, j, k in offs])
    active = corners.any(0) & ~corners.all(0)
    cells = np.argwhere(active)
    index = -np.ones(active.shape, int)
    index[active] = np.arange(len(cells))
    acc = np.zeros((len(cells), 3)); cnt = np.zeros(len(cells))
    for a in range(8):
        for b in range(a + 1, 8):
            if np.abs(offs[a] - offs[b]).sum() != 1:
                continue
            pa, pb = cells + offs[a], cells + offs[b]
            fa, fb = f[tuple(pa.T)], f[tuple(pb.T)]
            cross = (fa > ISO) != (fb > ISO)
            t = np.clip((ISO - fa) / np.where(cross, fb - fa, 1), 0, 1)
            p = pa + t[:, None] * (pb - pa)
            acc[cross] += p[cross]; cnt[cross] += 1
    verts = origin + step * acc / cnt[:, None]
    quads = []
    for u in range(3):
        v, w = (u + 1) % 3, (u + 2) % 3
        lo = [slice(None)] * 3; hi = [slice(None)] * 3
        lo[u] = slice(0, n[u] - 1); hi[u] = slice(1, n[u])
        start = s[tuple(lo)]
        edges = np.argwhere(start != s[tuple(hi)])
        edges = edges[(edges[:, v] > 0) & (edges[:, w] > 0) & (edges[:, v] < n[v] - 1) & (edges[:, w] < n[w] - 1)]
        ring = []
        for dv, dw in ((-1, -1), (0, -1), (0, 0), (-1, 0)):
            c = edges.copy(); c[:, v] += dv; c[:, w] += dw
            ring.append(index[tuple(c.T)])
        ring = np.stack(ring, 1)
        out = start[tuple(edges.T)]
        ring[~out] = ring[~out][:, ::-1]
        quads.append(ring)
    q = np.concatenate(quads)
    q = q[(q >= 0).all(1)]
    return verts, np.concatenate([q[:, [0, 1, 2]], q[:, [0, 2, 3]]])


def noise(p, seed):
    """Smooth value noise in three dimensions, about 0, of unit grain."""
    lattice = np.random.default_rng(seed).random((32, 32, 32)) * 2 - 1
    i = np.floor(p).astype(int); fr = p - i
    fr = fr * fr * (3 - 2 * fr)
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                wgt = (fr[:, 0] if dx else 1 - fr[:, 0]) * (fr[:, 1] if dy else 1 - fr[:, 1]) * (fr[:, 2] if dz else 1 - fr[:, 2])
                out = out + wgt * lattice[(i[:, 0] + dx) % 32, (i[:, 1] + dy) % 32, (i[:, 2] + dz) % 32]
    return out


def normals(v, f):
    n = np.zeros_like(v)
    fn = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    for k in range(3):
        np.add.at(n, f[:, k], fn)
    return n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12)


def picture_uv(v, n, picture, lo, hi):
    if picture in BY_HEIGHT:
        # Around the rock, and from its top (0) to its foot (1).
        mid = (lo + hi) / 2
        around = np.arctan2(v[:, 1] - mid[1], v[:, 0] - mid[0]) / (2 * np.pi) + 0.5
        reach = np.hypot(*(hi - lo)[:2]) * np.pi / 2
        return np.stack([around * max(round(reach / BY_HEIGHT[picture]), 1), (hi[2] - v[:, 2]) / (hi[2] - lo[2])], 1)
    axis = np.abs(n).argmax(1)
    u = np.where(axis == 0, v[:, 1], v[:, 0])
    w = np.where(axis == 2, v[:, 1], v[:, 2])
    return np.stack([u, w], 1) / REPEAT


def rock(picture):
    """A rock's material and its pictures, as `write_gltf` takes them."""
    return ({'name': 'Rock', 'pbrMetallicRoughness': {'metallicFactor': 0.0, 'roughnessFactor': 0.9}},
            f'../materials/{picture}_albedo.png', f'../materials/{picture}_normal.png')


def write_gltf(path, parts, tool=TOOL):
    """`parts` as one glTF model and its buffer: each (material, colour picture, normal picture or
    None, vertices, normals, picture coordinates, triangles), in the client's axes, z up."""
    name = os.path.splitext(os.path.basename(path))[0]
    chunks, views, acc, prims, materials, images = [], [], [], [], [], []
    offset = 0
    def add(data, **a):
        nonlocal offset
        chunks.append(data.tobytes())
        views.append({'buffer': 0, 'byteOffset': offset, 'byteLength': len(chunks[-1])})
        offset += len(chunks[-1])
        acc.append({'bufferView': len(views) - 1, **a})
        return len(acc) - 1
    def image(uri):
        if uri not in images:
            images.append(uri)
        return images.index(uri)
    for material, colour, normal, v, n, uv, f in parts:
        # The client's models stand z up; glTF stands y up.
        pos = (v[:, [0, 2, 1]] * [1, 1, -1]).astype(np.float32)
        nor = (n[:, [0, 2, 1]] * [1, 1, -1]).astype(np.float32)
        attributes = {
            'POSITION': add(pos, componentType=5126, count=len(v), type='VEC3', min=pos.min(0).tolist(), max=pos.max(0).tolist()),
            'NORMAL': add(nor, componentType=5126, count=len(v), type='VEC3'),
            'TEXCOORD_0': add(uv.astype(np.float32), componentType=5126, count=len(v), type='VEC2'),
        }
        indices = add(f.astype(np.uint32).ravel(), componentType=5125, count=int(f.size), type='SCALAR')
        m = json.loads(json.dumps(material))
        m['pbrMetallicRoughness']['baseColorTexture'] = {'index': image(colour)}
        if normal:
            m['normalTexture'] = {'index': image(normal)}
        prims.append({'attributes': attributes, 'indices': indices, 'material': len(materials)})
        materials.append(m)
    doc = {'asset': {'version': '2.0', 'generator': tool},
           'scenes': [{'nodes': [0]}], 'scene': 0, 'nodes': [{'mesh': 0}],
           'meshes': [{'primitives': prims}], 'materials': materials,
           'textures': [{'source': i} for i in range(len(images))],
           'images': [{'uri': u} for u in images],
           'buffers': [{'uri': f'{name}.bin', 'byteLength': offset}],
           'bufferViews': views, 'accessors': acc}
    open(os.path.join(os.path.dirname(path), f'{name}.bin'), 'wb').write(b''.join(chunks))
    open(path, 'w').write(json.dumps(doc, indent=1))


def level(tri, lo, hi, share, seed):
    extent = hi - lo
    size = extent.max()
    # Never fewer than four cells across its thinnest side, or a thin slab vanishes.
    thin = max(4, THINNEST * share) * size / max(extent.min(), 1e-3)
    cells = min(max(share * CELLS, thin), 2 * CELLS)
    step = size / cells
    pad = 3
    origin = lo - pad * step
    shape = np.ceil((hi - lo) / step).astype(int) + 2 * pad + 1
    grid = origin + step * np.stack(np.meshgrid(*[np.arange(k) for k in shape], indexing='ij'), -1).reshape(-1, 3)
    # Jittered off the grid, so no upward line runs along an edge of the original.
    jitter = np.array([1e-4, 2.3e-4, 0]) * step
    f = depth(inside(grid + jitter, tri, lo[2]).reshape(shape))
    v, faces = surface_nets(f, origin, step)
    v = taubin(v, faces, max(int(SMOOTH * share), 2))
    n = normals(v, faces)
    v = v + n * (ROUGH * size * noise(v / ROUGH_SCALE + 7.3, seed))[:, None]
    v[:, 2] = np.maximum(v[:, 2], lo[2] - 0.02 * size)
    return v, normals(v, faces), faces


def make(out, meshes, id, picture):
    tri = triangles(meshes, id)
    lo, hi = tri.reshape(-1, 3).min(0), tri.reshape(-1, 3).max(0)
    os.makedirs(os.path.join(out, 'trees'), exist_ok=True)
    counts = []
    for lod, (share, _) in enumerate(LEVELS):
        v, n, f = level(tri, lo, hi, share, int(id, 16) & 0xFFFF)
        uv = picture_uv(v, n, picture, lo, hi)
        write_gltf(os.path.join(out, 'trees', f'{id}_lod{lod}.gltf'), [(*rock(picture), v, n, uv, f)])
        counts.append(len(f))
    return counts


if __name__ == '__main__':
    out, meshes = sys.argv[1:3]
    for id, picture in (a.split(':') for a in sys.argv[3:]):
        print(id, picture, make(out, meshes, id, picture), 'triangles')
