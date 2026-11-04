# split.py <retail pngs> <recipes file>: finds the bands and panels of each mixed picture and writes
# them into its line as rectangles, each with the recipe it looks to want. A line that already has
# rectangles keeps them, so a hand's correction stays.
import os, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from masonry import blur
from recipes import classify
SRC, FILE = sys.argv[1:3]
def read(path, side=128):
    raw = subprocess.run(['magick', path, '-virtual-pixel', 'tile', '-filter', 'Catrom', '-distort', 'Resize', f'{side}x{side}!', '-depth', '8', 'rgba:-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(side, side, 4).astype(np.float32) / 255
def cuts(a, axis, least):
    """Where the picture changes in kind across `axis`: its colour and how busy it is, either side."""
    other = 1 - axis
    L = a[..., :3].mean(-1)
    busy = np.abs(L - blur(L, 3)).astype(np.float32)
    f = np.concatenate([a[..., :3].mean(other), busy.mean(other)[:, None] * 3], 1)
    n = f.shape[0]
    span = max(4, least // 2)
    d = np.zeros(n)
    for i in range(span, n - span):
        d[i] = np.abs(f[i - span:i].mean(0) - f[i:i + span].mean(0)).sum()
    found = []
    for i in np.argsort(-d):
        if d[i] < 0.26:
            break
        if least <= i <= n - least and all(abs(i - c) >= least for c in found):
            found.append(int(i))
    return sorted(found)
out = []
for line in open(FILE):
    if line.startswith('#') or not line.strip():
        out.append(line); continue
    parts = line.rstrip('\n').split('\t')
    if parts[2] != 'mixed' or any(',' in w for w in parts[4:]):
        out.append(line); continue
    path = os.path.join(SRC, parts[0] + '.png')
    if not os.path.exists(path):
        out.append(line); continue
    a = read(path)
    L = (a[..., :3] * [0.3, 0.59, 0.11]).sum(-1) ** 0.8
    L = L / (blur(L, 24) + 0.04)
    rects = []
    rows = [0] + cuts(a, 0, 14) + [128]
    for y0, y1 in zip(rows, rows[1:]):
        band = a[y0:y1]
        cols = [0] + (cuts(band, 1, 14) if y1 - y0 >= 28 else []) + [128]
        for x0, x1 in zip(cols, cols[1:]):
            # A thin band is moulding or trim: its painted shading is its shape.
            thin = min(y1 - y0, x1 - x0) < 22
            name = 'design' if thin else classify(L[y0:y1, x0:x1], a[y0:y1, x0:x1], 1.0)
            rects.append(f'{x0 / 128:.3f},{y0 / 128:.3f},{(x1 - x0) / 128:.3f},{(y1 - y0) / 128:.3f},{name}')
    parts += rects
    out.append('\t'.join(parts) + '\n')
open(FILE, 'w').writelines(out)
print(sum(1 for l in out if '\tmixed\t' in l and ',' in l), 'mixed pictures split')
