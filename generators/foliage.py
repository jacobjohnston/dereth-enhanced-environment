# Finishes the pictures gen_pack.mjs wrote into <pack folder>/trees. Halves the grass picture's
# saturation, keeping its brightness. Colours the cut-away ground of each picture whose ground is
# unlike its leaves (as a client's `matted` test finds it) as its nearest leaves, fading to their
# mean far from them, so filtering draws no light rim round each leaf. Alpha is kept. Run it after
# gen_pack.mjs and clump_cover.py; a second run changes nothing.
# Needs only Python and ImageMagick (`magick`).
# foliage.py <pack folder>
import os, subprocess, sys

# The grass picture's chroma against its brightness (linear): half the kit's 0.104.
GRASS = ('Plant_Grass.png', 0.052)
# Ground unlike the leaves by more than this (linear, any channel) is a matte, when at least one
# texel in 50 is cut away.
UNLIKE = 0.06
# How wide the picture a client tests is: its first level no wider.
TESTED = 256
# The pyramid levels over which the fill fades from the nearest leaves to the leaves' mean: ground
# within about 4 texels of a leaf is its own, ground past about 32 the mean.
NEAR, FAR = 2, 5
LUMA = (0.2126, 0.7152, 0.0722)
TO_LINEAR = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (i / 255 for i in range(256))]


def to_srgb(v):
    v = min(max(v, 0.0), 1.0)
    return round(255 * (v * 12.92 if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055))


def read(path):
    w, h = map(int, subprocess.run(['magick', 'identify', '-format', '%w %h', path], capture_output=True,
                                   text=True, check=True).stdout.split())
    raw = subprocess.run(['magick', path, '-depth', '8', 'rgba:-'], capture_output=True, check=True).stdout
    return w, h, bytearray(raw)


def write(path, w, h, rgba):
    subprocess.run(['magick', '-define', 'png:exclude-chunks=date,time', '-size', f'{w}x{h}', '-depth', '8',
                    'rgba:-', path], input=bytes(rgba), check=True)


def chroma(rgba, inside):
    """The leaves' chroma against their brightness, in linear light."""
    c = l = 0.0
    for i in range(0, len(rgba), 4):
        if rgba[i + 3] >= inside:
            r, g, b = TO_LINEAR[rgba[i]], TO_LINEAR[rgba[i + 1]], TO_LINEAR[rgba[i + 2]]
            c += max(r, g, b) - min(r, g, b)
            l += LUMA[0] * r + LUMA[1] * g + LUMA[2] * b
    return c / l if l else 0.0


def desaturate(rgba, inside, want):
    """Each texel's colour drawn toward its brightness until the leaves' chroma is `want`."""
    k = want / chroma(rgba, inside)
    if abs(k - 1) < 0.02:
        return False
    for i in range(0, len(rgba), 4):
        r, g, b = TO_LINEAR[rgba[i]], TO_LINEAR[rgba[i + 1]], TO_LINEAR[rgba[i + 2]]
        y = LUMA[0] * r + LUMA[1] * g + LUMA[2] * b
        rgba[i:i + 3] = bytes(to_srgb(y + k * (v - y)) for v in (r, g, b))
    return True


def halve(w, h, px):
    """`px` (texels of four floats) box-filtered to half its size."""
    nw, nh = max(w // 2, 1), max(h // 2, 1)
    out = []
    for y in range(nh):
        rows = [px[min(2 * y + dy, h - 1) * w:][:w] for dy in (0, 1)]
        for x in range(nw):
            q = [row[min(2 * x + dx, w - 1)] for row in rows for dx in (0, 1)]
            out.append(tuple(sum(t[c] for t in q) / 4 for c in range(4)))
    return nw, nh, out


def matted(w, h, rgba):
    """Whether the picture's cut-away texels hold a colour unlike its leaves', read as a client reads
    it: from its first level no wider than TESTED."""
    px = [tuple(rgba[i:i + 4]) for i in range(0, len(rgba), 4)]
    while w > TESTED:
        w, h, px = halve(w, h, px)
    px = [tuple(round(v) for v in t) for t in px]
    cut = sum(1 for t in px if t[3] < 8)
    if cut * 50 < len(px) or cut == len(px):
        return False
    most = max(t[3] for t in px)
    def mean(keep):
        s, n = [0.0] * 3, 0
        for t in px:
            if keep(t[3]):
                for c in range(3):
                    s[c] += TO_LINEAR[t[c]]
                n += 1
        return [v / n for v in s] if n else None
    ground, leaves = mean(lambda a: a < 8), mean(lambda a: a >= most // 2 + most // 4)
    return bool(ground and leaves) and any(abs(g - l) > UNLIKE for g, l in zip(ground, leaves))


def fill(w, h, rgba, inside):
    """Colours every texel not well inside a leaf as the leaves about it: a push-pull fill, the
    leaves' colours summed down a pyramid by halves and each other texel taking the first level
    over it that holds any. Ground farther than NEAR fades to the leaves' mean by FAR."""
    level = [(rgba[i], rgba[i + 1], rgba[i + 2], 1) if rgba[i + 3] >= inside else (0, 0, 0, 0)
             for i in range(0, len(rgba), 4)]
    pyramid = [(w, h, level)]
    while w > 1 or h > 1:
        nw, nh = (w + 1) // 2, (h + 1) // 2
        nxt = [[0, 0, 0, 0] for _ in range(nw * nh)]
        for y in range(h):
            row, base = level[y * w:(y + 1) * w], (y // 2) * nw
            for x, t in enumerate(row):
                if t[3]:
                    d = nxt[base + x // 2]
                    d[0] += t[0]; d[1] += t[1]; d[2] += t[2]; d[3] += t[3]
        w, h, level = nw, nh, nxt
        pyramid.append((w, h, level))
    # Each texel's colour, and the level it was found at.
    above = None
    for k in range(len(pyramid) - 1, 0, -1):
        lw, _, level = pyramid[k]
        resolved = []
        for i, t in enumerate(level):
            if t[3]:
                resolved.append((t[0] / t[3], t[1] / t[3], t[2] / t[3], k))
            elif above:
                resolved.append(above[1][(i // lw // 2) * above[0] + (i % lw) // 2])
            else:
                resolved.append((128, 128, 128, k))
        above = (lw, resolved)
    mean, n = [0.0] * 3, 0
    for i in range(0, len(rgba), 4):
        if rgba[i + 3] >= inside:
            for c in range(3):
                mean[c] += TO_LINEAR[rgba[i + c]]
            n += 1
    mean = [v / n for v in mean]
    w = pyramid[0][0]
    for i in range(0, len(rgba), 4):
        if rgba[i + 3] < inside:
            j = i // 4
            c = above[1][(j // w // 2) * above[0] + (j % w) // 2]
            t = min(max((c[3] - NEAR) / (FAR - NEAR), 0), 1)
            rgba[i:i + 3] = bytes(to_srgb((1 - t) * TO_LINEAR[min(max(round(c[q]), 0), 255)] + t * mean[q])
                                  for q in range(3))


def main():
    trees = os.path.join(sys.argv[1], 'trees')
    for name in sorted(os.listdir(trees)):
        if not name.endswith('.png') or name.endswith('_Normal.png'):
            continue
        path = os.path.join(trees, name)
        w, h, rgba = read(path)
        most = max(rgba[3::4])
        inside = most * 3 // 4
        did = []
        if name == GRASS[0] and desaturate(rgba, inside, GRASS[1]):
            did.append('desaturated')
        if min(rgba[3::4]) < 255 and most >= 8 and matted(w, h, rgba):
            fill(w, h, rgba, inside)
            did.append('matte filled')
        if did:
            write(path, w, h, rgba)
            print(f'{name}: {", ".join(did)}', flush=True)


if __name__ == '__main__':
    main()
