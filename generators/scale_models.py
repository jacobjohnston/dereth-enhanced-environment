#!/usr/bin/env python3
# Scales trees whose models are right but too big for retail (Jacob's sizes reviews, 2026-11-21): each
# listed model's every level grows by its factor about its foot, through its node's transform, so
# nothing else about it changes. A factor is retail's height over the model's, measured from both
# meshes; the fruit tree's is retail's trunk width at 0.6 to 1.3 m over its own.
# Run it once, after gen_pack.mjs and quantise.py, on the models gen_pack.mjs has just grown.
# scale_models.py <pack folder> [id ...]   (no ids: every model in SCALES)
import glob, json, os, sys

SCALES = {
    "0x02000256": 0.90, "0x02000257": 0.89, "0x02000258": 0.91,
    "0x020002D3": 0.88, "0x020002D8": 0.87, "0x020002D9": 0.86, "0x020002DA": 0.87, "0x020002DB": 0.90,
    # The snowy pines and spruces, on 0.4.4's models.
    "0x020003A3": 0.85, "0x020003A4": 0.85, "0x020003A7": 0.85, "0x020012FB": 0.86,
    "0x02000322": 0.86,
    "0x02001C31": 0.72,
}


def scale(path, k):
    g = json.load(open(path))
    for node in g["nodes"]:
        if "mesh" not in node:
            continue
        node["scale"] = [c * k for c in node.get("scale", [1, 1, 1])]
        if "translation" in node:
            node["translation"] = [c * k for c in node["translation"]]
    json.dump(g, open(path, "w"))


if __name__ == "__main__":
    pack, ids = sys.argv[1], sys.argv[2:] or list(SCALES)
    for i in ids:
        files = sorted(glob.glob(os.path.join(pack, "trees", f"{i}_lod*.gltf")))
        for f in files:
            scale(f, SCALES[i])
        print(f"{i}: {len(files)} levels x{SCALES[i]}")
