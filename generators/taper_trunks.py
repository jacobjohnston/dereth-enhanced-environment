#!/usr/bin/env python3
# Tapers a grown trunk into the branches above it. gen_pack.mjs grows a round tree's trunk to the
# retail radius but leaves its branches at the preset's, so the trunk ended in a ledge where they
# go on. Its foot (fit_trunks.py's band) keeps its width; above it the trunk narrows to its
# branches' size at its top. Run after fit_trunks.py.
#
# taper_trunks.py <pack> <id>...   rewrites each id's trees/<id>_lod*.gltf and .bin in place
import glob, json, math, os, struct, sys

# The foot left as it is (fit_trunks.py's band), metres.
FOOT = 0.8
# How near the axis a trunk's ring lies, and the least points that make a ring.
NEAR = 1.6
RING = 9
# How far above the trunk's top its branches are measured, and the longest gap between its rings,
# metres.
ABOVE = 0.8
GAP = 1.2


def smooth(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def load(path):
    g = json.load(open(path))
    bin_path = os.path.join(os.path.dirname(path), g["buffers"][0]["uri"])
    return g, bytearray(open(bin_path, "rb").read()), bin_path


def wood(g):
    """The opaque primitives' positions: accessor, offset, stride, and the node's scale and move."""
    node = next(n for n in g["nodes"] if "mesh" in n)
    s, t = node.get("scale", [1, 1, 1]), node.get("translation", [0, 0, 0])
    out = []
    for p in g["meshes"][node["mesh"]]["primitives"]:
        if g["materials"][p["material"]].get("alphaMode", "OPAQUE") != "OPAQUE":
            continue
        a = g["accessors"][p["attributes"]["POSITION"]]
        v = g["bufferViews"][a["bufferView"]]
        out.append((a, v.get("byteOffset", 0) + a.get("byteOffset", 0), v.get("byteStride", 8)))
    return out, s, t


def points(g, data):
    prims, s, t = wood(g)
    assert all(a["componentType"] == 5122 and a.get("normalized") for a, _, _ in prims), "quantised shorts"
    return [[tuple(max(q / 32767, -1.0) * s[k] + t[k] for k, q in enumerate(struct.unpack_from("<3h", data, off + i * st)))
             for i in range(a["count"])] for a, off, st in prims]


def rings(pts):
    """The trunk's rings, low to high: height, centre and mean radius."""
    out = []
    for y in sorted({round(p[1], 2) for p in pts if p[1] > -1.0 and math.hypot(p[0], p[2]) < NEAR}):
        ring = [p for p in pts if abs(p[1] - y) < 0.02 and math.hypot(p[0], p[2]) < NEAR]
        if len(ring) < 4:
            continue
        cx, cz = sum(p[0] for p in ring) / len(ring), sum(p[2] for p in ring) / len(ring)
        out.append((y, cx, cz, sum(math.hypot(p[0] - cx, p[2] - cz) for p in ring) / len(ring), len(ring)))
    return out


def measure(pts):
    """The trunk's top, its radius there, and the branches' radius just above it."""
    found = rings(pts)
    # The trunk's rings have its foot's sides (its widest ring there); up from it until a long gap.
    foot = max((r for r in found if r[0] < FOOT and r[4] >= RING), key=lambda r: r[3])
    sides = foot[4]
    trunk = []
    for r in (r for r in found if r[0] >= foot[0] and sides <= r[4] <= sides + 3):
        if trunk and r[0] - trunk[-1][0] > GAP:
            break
        trunk.append(r)
    top = trunk[-1]
    above = sorted(r[3] for r in found if top[0] < r[0] <= top[0] + ABOVE)
    if not above:
        return None
    # The branches going on: the middle of them and the thickest.
    return top[0], top[3], (above[len(above) // 2] + above[-1]) / 2, trunk


def axis(trunk, y):
    """The trunk's centre at height `y`, between its rings."""
    lo = max((r for r in trunk if r[0] <= y), key=lambda r: r[0], default=trunk[0])
    hi = min((r for r in trunk if r[0] >= y), key=lambda r: r[0], default=trunk[-1])
    t = 0.0 if hi[0] == lo[0] else (y - lo[0]) / (hi[0] - lo[0])
    return lo[1] + (hi[1] - lo[1]) * t, lo[2] + (hi[2] - lo[2]) * t, lo[3] + (hi[3] - lo[3]) * t


def taper(path, top, share, trunk):
    g, data, bin_path = load(path)
    prims, s, t = wood(g)
    moved = 0
    for (a, off, st), pts in zip(prims, points(g, data)):
        lo, hi = [32767] * 3, [-32767] * 3
        for i, (x, y, z) in enumerate(pts):
            if FOOT < y <= top + 0.05:
                cx, cz, r = axis(trunk, y)
                d = math.hypot(x - cx, z - cz)
                if d <= r * 1.25:
                    k = 1.0 - (1.0 - share) * smooth(FOOT, top, y)
                    x, z = cx + (x - cx) * k, cz + (z - cz) * k
                    q = [round((v - t[j]) / s[j] * 32767) for j, v in enumerate((x, y, z))]
                    struct.pack_into("<3h", data, off + i * st, *q)
                    moved += 1
            q = struct.unpack_from("<3h", data, off + i * st)
            lo = [min(lo[j], q[j]) for j in range(3)]
            hi = [max(hi[j], q[j]) for j in range(3)]
        a["min"], a["max"] = lo, hi
    json.dump(g, open(path, "w"))
    open(bin_path, "wb").write(data)
    return moved


def main():
    pack, ids = sys.argv[1], sys.argv[2:]
    for id_ in ids:
        files = sorted(glob.glob(os.path.join(pack, "trees", f"{id_}_lod*.gltf")))
        g, data, _ = load(files[0])
        found = measure([p for ps in points(g, data) for p in ps])
        if found is None:
            print(f"{id_}: no branches above the trunk; left")
            continue
        top, radius, branches, trunk = found
        share = min(1.0, branches / radius)
        if share > 0.95:
            print(f"{id_}: trunk top {top:.2f} m at {radius:.2f}, branches {branches:.2f}; left")
            continue
        print(f"{id_}: trunk top {top:.2f} m at {radius:.2f}, branches {branches:.2f}: narrowed to {share:.2f}")
        for f in files:
            print(f"  {os.path.basename(f)}: {taper(f, top, share, trunk)} points")


main()
