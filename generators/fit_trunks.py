#!/usr/bin/env python3
# Brings each model's trunk to the size and place of the retail object's collision, so a character
# stops at the bark on every client. Only the opaque wood near the ground moves, fading back to the
# model as it is higher up; canopies, limbs and roots hanging well clear of the trunk stay.
#
# fit_trunks.py <stage> <out> <retail-trunks.txt>   writes changed trees/ files to <out>/trees/
import json, math, os, re, shutil, struct, sys

stage, out, table = sys.argv[1:4]
# How much of the band above the ground measures a trunk (metres), and the widest gap in the wood
# there that still counts as the same trunk (a share of the retail radius, at least this far).
BAND = (0.0, 0.8)
GAP = 0.6
# Least and most a trunk is scaled, and how close counts as already fitting.
LEAST, MOST = 0.2, 2.0
CLOSE = 0.08
# Shorter than this, a trunk thinner than its collision is left as it is (metres).
SMALLEST = 5.0


def retail_shapes():
    shapes = {}
    for line in open(table):
        m = re.match(r"TREECOL (\w+) parts \d+ cyl \[(.*?)\]", line)
        if not m or not m.group(2):
            continue
        cyls = [tuple(map(float, re.match(r'"?(-?[\d.]+),(-?[\d.]+),(-?[\d.]+)r([\d.]+)', c.strip()).groups()))
                for c in m.group(2).split('", ')]
        lo = [min(c[i] - c[3] for c in cyls) for i in (0, 1)]
        hi = [max(c[i] + c[3] for c in cyls) for i in (0, 1)]
        # glTF's first axis is the world's first; its third is the world's second, turned.
        shapes["0x" + m.group(1)] = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (hi[0] - lo[0]) / 2, (hi[1] - lo[1]) / 2)
    return shapes


def smooth(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def positions(g, prim):
    a = g["accessors"][prim["attributes"]["POSITION"]]
    v = g["bufferViews"][a["bufferView"]]
    return a, v.get("byteOffset", 0) + a.get("byteOffset", 0), v.get("byteStride", 12)


def wood(g, mesh):
    return [p for p in mesh["primitives"] if g["materials"][p["material"]].get("alphaMode", "OPAQUE") == "OPAQUE"]


def measure(lists):
    """The trunk near the ground: its middle, the radius it reaches, and where the trunk's wood ends."""
    band = [p for pts in lists for p in pts if BAND[0] <= p[1] <= BAND[1]]
    if len(band) < 3:
        return None
    # The trunk stands at the model's foot: nearest wood first, up to the first wide gap.
    radii = sorted(math.hypot(p[0], p[2]) for p in band)
    end = radii[0]
    for r in radii[1:]:
        if r - end > GAP:
            break
        end = r
    kept = [p for p in band if math.hypot(p[0], p[2]) <= end]
    return (sum(p[0] for p in kept) / len(kept), sum(p[2] for p in kept) / len(kept), end)


def fit_file(path, base, shape, tall, report):
    g = json.load(open(path))
    bin_path = os.path.join(os.path.dirname(path), g["buffers"][0]["uri"])
    data = bytearray(open(bin_path, "rb").read())
    prims = [p for mesh in g["meshes"] for p in wood(g, mesh)]
    lists = []
    for prim in prims:
        a, off, st = positions(g, prim)
        lists.append([struct.unpack_from("<3f", data, off + i * st) for i in range(a["count"])])
    (mx, mz, end) = base
    cx, cy, rx, ry = shape
    sx = min(max(rx / max(end, 1e-3), LEAST), MOST)
    sz = min(max(ry / max(end, 1e-3), LEAST), MOST)
    # The world's second axis is glTF's third turned round.
    tx, tz = cx, -cy
    fade = min(max(end * 3.0, 4.0), tall * 0.3)
    changed = False
    for prim, pts in zip(prims, lists):
        a, off, st = positions(g, prim)
        lo, hi = [1e9] * 3, [-1e9] * 3
        for i, p in enumerate(pts):
            x, y, z = p
            near = 1.0 - smooth(0.0, fade, y)
            r = math.hypot(x, z)
            trunk = 1.0 - smooth(end + GAP * 0.5, end + GAP * 1.5, r)
            k = near * trunk
            if k > 0:
                x = x + ((mx + (x - mx) * sx + tx - mx) - x) * k
                z = z + ((mz + (z - mz) * sz + tz - mz) - z) * k
                struct.pack_into("<3f", data, off + i * st, x, y, z)
                changed = True
            q = (x, y, z)
            lo = [min(lo[j], q[j]) for j in range(3)]
            hi = [max(hi[j], q[j]) for j in range(3)]
        a["min"], a["max"] = lo, hi
    return g, data, bin_path, changed


def main():
    shapes = retail_shapes()
    os.makedirs(os.path.join(out, "trees"), exist_ok=True)
    manifest = open(os.path.join(stage, "manifest.toml")).read()
    for block in re.split(r"(?=^\[\[model\]\])", manifest, flags=re.M)[1:]:
        id_ = re.search(r'id = "(0x\w+)"', block).group(1)
        files = re.findall(r'file = "(trees/[^"]+)"', block)
        if id_ not in shapes or not files or not re.search(r"^foliage|", block):
            continue
        first = os.path.join(stage, files[0])
        g = json.load(open(first))
        data = open(os.path.join(os.path.dirname(first), g["buffers"][0]["uri"]), "rb").read()
        lists, top = [], 0.0
        for mesh in g["meshes"]:
            for prim in wood(g, mesh):
                a, off, st = positions(g, prim)
                pts = [struct.unpack_from("<3f", data, off + i * st) for i in range(a["count"])]
                lists.append(pts)
                top = max([top] + [p[1] for p in pts])
        base = measure(lists)
        cx, cy, rx, ry = shapes[id_]
        if base is None:
            print(f"{id_} no wood at the ground; left")
            continue
        mx, mz, end = base
        off_by = math.hypot(cx - mx, -cy - mz)
        # A low plant's collision can be far wider than anything it should grow to.
        if top < SMALLEST and rx > end:
            print(f"{id_} low plant, tall {top:.1f}; left")
            continue
        if abs(rx - end) < CLOSE and abs(ry - end) < CLOSE and off_by < CLOSE:
            print(f"{id_} already fits: {end:.2f} against {rx:.2f}")
            continue
        print(f"{id_} trunk {end:.2f} at {mx:.2f},{mz:.2f} to {rx:.2f}x{ry:.2f} at {cx:.2f},{cy:.2f} (tall {top:.1f})")
        for f in files:
            path = os.path.join(stage, f)
            g, d, bin_path, changed = fit_file(path, base, shapes[id_], top, None)
            if changed:
                json.dump(g, open(os.path.join(out, f), "w"))
                open(os.path.join(out, "trees", os.path.basename(bin_path)), "wb").write(d)


main()
