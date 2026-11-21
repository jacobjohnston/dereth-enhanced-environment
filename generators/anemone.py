#!/usr/bin/env python3
# Paints the two sea anemones' pictures, which the client draws on retail's own anemone models
# (Jacob's review, 2026-11-20). Each 512 picture's right half is the model's: the bulb lies in its
# lower quarter and the spikes in its upper. The bulb takes the pack's banded skin (shapes.mjs's
# Gen_Bands.png, drawn here through Node) in the colour the pack's own anemones had. The spikes are
# cut out of the upper quarter: one wavering strand of our own in each column retail's spikes stand
# in, as tall as retail's, in the mean colours of retail's spike texels, bright at the core and paler
# at the edge. No retail texel is copied. The left half, which no model draws, repeats the bulb.
# Each picture becomes the base colour of relief.py's material for it, in place of its fallback and the
# retail picture. The bulb also takes the pack's old anemones' relief (Jacob's pick, 2026-11-21): the
# grain shapes.mjs draws Gen_Grit_Normal.png from as its height and normal at a quarter of their depth
# (Jacob, 2026-11-21: theirs at full depth, then half, read too strong here), with their gloss; the spikes keep relief.py's maps. Run it after relief.py, which writes those materials.
# Needs Python, Node and ImageMagick (`magick`).
# anemone.py <retail pictures folder> <pack folder>
import math, os, random, subprocess, sys, tempfile

src, pack = sys.argv[1:3]
SIZE = 512
# Each picture: its id, and the pack anemone's tint (linear) laid on the bands.
ANEMONES = [("0x05002C17", (0.22, 0.7, 0.3)), ("0x05002C12", (0.24, 0.32, 0.8))]
# A spike texel is one brighter than this (0..1, sRGB).
LIT = 0.18
# The bulb: its relief's depth (a quarter of the old anemones' 1.3) and roughness.
STEEP, GLOSS = 0.325, 0.45


def read(path, size=SIZE):
    raw = subprocess.run(["magick", path, "-resize", f"{size}x{size}!", "-depth", "8", "rgba:-"],
                         capture_output=True, check=True).stdout
    return [tuple(raw[i:i + 4]) for i in range(0, len(raw), 4)]


def write(path, pixels):
    raw = bytes(max(0, min(255, round(c))) for p in pixels for c in p)
    subprocess.run(["magick", "-size", f"{SIZE}x{SIZE}", "-depth", "8", "rgba:-", path], input=raw, check=True)


def columns(retail):
    """The spike columns in the upper right quarter: each one's left, right, and top row."""
    half = SIZE // 2
    cover = [sum(retail[y * SIZE + x][3] for y in range(half)) / (255 * half) for x in range(half, SIZE)]
    out, start = [], None
    for i, c in enumerate(cover + [0]):
        if c > 0.08 and start is None:
            start = i
        elif c <= 0.08 and start is not None:
            top = min(y for y in range(half) if any(retail[y * SIZE + half + x][3] > 128 for x in range(start, i)))
            out.append((start, i - 1, top))
            start = None
    return out


def noise(seed):
    rng = random.Random(seed)
    grid = [[rng.random() for _ in range(17)] for _ in range(17)]

    def at(u, v, f):
        x, y = (u * f) % 16, (v * f) % 16
        i, j = int(x), int(y)
        fx, fy = x - i, y - j
        fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        a = grid[j][i] + (grid[j][i + 1] - grid[j][i]) * fx
        b = grid[j + 1][i] + (grid[j + 1][i + 1] - grid[j + 1][i]) * fx
        return a + (b - a) * fy
    return lambda u, v: at(u, v, 4) * 0.5 + at(u, v, 9) * 0.3 + at(u, v, 16) * 0.2


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        f.write(subprocess.run(["node", "--input-type=module", "-e",
                                f"import * as s from {repr('file://' + os.path.join(here, 'shapes.mjs'))}; process.stdout.write(s.PICTURES['Gen_Bands.png']());"],
                               capture_output=True, check=True).stdout)
        f.flush()
        bands = read(f.name, SIZE // 2)
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        f.write(subprocess.run(["node", "--input-type=module", "-e",
                                f"import * as s from {repr('file://' + os.path.join(here, 'shapes.mjs'))}; process.stdout.write(s.png((u, v) => {{ const g = s.GRAIN(u, v); return [g, g, g, 1]; }}, 0));"],
                               capture_output=True, check=True).stdout)
        f.flush()
        grain = [p[0] / 255 for p in read(f.name, SIZE // 2)]
    os.makedirs(os.path.join(pack, "materials"), exist_ok=True)
    for k, (pid, tint) in enumerate(ANEMONES):
        retail = read(os.path.join(src, f"{pid}.png"))
        # The spikes' colours: retail's lit texels in the upper right quarter, by brightness.
        lit = sorted((sum(p[:3]) / 765, p) for y in range(SIZE // 2) for x in range(SIZE // 2, SIZE)
                     for p in [retail[y * SIZE + x]] if p[3] > 128 and sum(p[:3]) / 765 > LIT)
        strands = columns(retail)
        third = max(1, len(lit) // 3)
        edge = [sum(p[1][c] for p in lit[:third]) / third for c in range(3)]
        core = [sum(p[1][c] for p in lit[-third:]) / third for c in range(3)]
        n = noise(311 + k)
        # The tint is linear; on sRGB texels it scales by its own power.
        gain = [t ** (1 / 2.2) for t in tint]
        out = []
        for y in range(SIZE):
            for x in range(SIZE):
                u, v = x / SIZE, y / SIZE
                if x >= SIZE // 2 and y < SIZE // 2:
                    # The nearest strand: its middle wavers, and it narrows to a point at its top.
                    best = 9.0
                    for j, (left, right, top) in enumerate(strands):
                        mid = (left + right) / 2 + (n(j * 0.37, v * 1.5) - 0.5) * (right - left) * 0.5
                        rise = min(1.0, max(0.0, (SIZE // 2 - 10 - y) / max(1, SIZE // 2 - 10 - top)))
                        half = (right - left) / 2 * (1 - rise ** 1.6) * 0.92
                        best = min(best, abs(x - SIZE // 2 - mid) / half if half > 0.5 and y >= top else 9.0)
                    t = max(0.0, 1 - best)
                    g = 0.85 + 0.3 * n(u * 6, v * 6)
                    out.append([(edge[c] + (core[c] - edge[c]) * t) * g for c in range(3)] + [255 if best < 1 else 0])
                else:
                    b = bands[(y % (SIZE // 2)) * (SIZE // 2) + (x % (SIZE // 2))]
                    out.append([b[c] * gain[c] for c in range(3)] + [255])
        write(os.path.join(pack, "materials", f"{pid}_albedo.png"), out)
        relief(pack, pid, grain)
        print(pid, "spike edge", [round(c) for c in edge], "core", [round(c) for c in core], "columns", strands)


def relief(pack, pid, grain):
    """The bulb's height, normal and roughness from the grain; the spike quarter keeps relief.py's."""
    base = os.path.join(pack, "materials", pid)
    normal, rough = read(f"{base}_normal.png"), read(f"{base}_roughness.png")
    half = SIZE // 2
    h = lambda x, y: grain[(y % half) * half + (x % half)]
    n_out, h_out, r_out = [], [], []
    for y in range(SIZE):
        for x in range(SIZE):
            if x >= half and y < half:
                n_out.append(list(normal[y * SIZE + x][:3]) + [255])
                h_out.append([255, 255, 255, 255])
                r_out.append(list(rough[y * SIZE + x][:3]) + [255])
                continue
            dx = (h(x + 1, y) - h(x - 1, y)) * half / 512 * 16 * STEEP
            dy = (h(x, y + 1) - h(x, y - 1)) * half / 512 * 16 * STEEP
            k = 1 / math.sqrt(dx * dx + dy * dy + 1)
            n_out.append([(-dx * k * 0.5 + 0.5) * 255, (dy * k * 0.5 + 0.5) * 255, (k * 0.5 + 0.5) * 255, 255])
            g = 255 - (1 - h(x, y)) * 255 * 0.25
            h_out.append([g, g, g, 255])
            r_out.append([GLOSS * 255] * 3 + [255])
    write(f"{base}_normal.png", n_out)
    write(f"{base}_height.png", h_out)
    write(f"{base}_roughness.png", r_out)


main()


def claim(pack):
    """Points relief.py's material for each picture at ours, and drops its unused fallback."""
    path = os.path.join(pack, "manifest.toml")
    text = open(path).read()
    for pid, _ in ANEMONES:
        head = f'[[material]]\ntexture = "{pid}"\n'
        at = text.index(head)
        end = text.find("\n[[", at + len(head))
        block = text[at:end]
        new = block.replace(f'base_color = "materials/{pid}_fallback.png"\nkeep_retail_picture = true\n',
                            f'base_color = "materials/{pid}_albedo.png"\n')
        new = new.replace('author = "Worked out from the player\'s own picture by relief.py"\ntool = "relief.py"',
                          'author = "Worked out from the player\'s own picture by relief.py; base colour by anemone.py"\ntool = "relief.py, anemone.py"')
        new = new.replace("base colour by anemone.py\"", "base colour and the bulb's relief by anemone.py\"")
        if "\nheight = " not in new:
            new = new.replace(f'occlusion = "materials/{pid}_occlusion.png"\n',
                              f'occlusion = "materials/{pid}_occlusion.png"\nheight = "materials/{pid}_height.png"\n')
        text = text[:at] + new + text[end:]
        fallback = os.path.join(pack, "materials", f"{pid}_fallback.png")
        if os.path.exists(fallback):
            os.remove(fallback)
    open(path, "w").write(text)


claim(pack)
