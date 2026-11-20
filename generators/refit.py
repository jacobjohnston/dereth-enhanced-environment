# refit.py <retail pngs> <recipes file> <ids file>: refits the rock and masonry rectangles of the
# listed pictures' lines, where rock made blotches of smooth stone and plaster. Each such rectangle
# (or a rock picture, as one rectangle) becomes plaster where it is smooth and wood where it is
# boards; any other keeps its recipe, since a stone finder lays wrong courses on carved or rubble
# stone. Prints each change.
import os, sys
import numpy as np
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from masonry import blur
from recipes import ashlar, classify
from relief import read

def light(path):
    """The picture's evened brightness at its maps' size, as relief.py works it out, and its scale."""
    import subprocess
    sw, sh = map(int, subprocess.run(['identify', '-format', '%w %h', path], capture_output=True, text=True, check=True).stdout.split())
    k = min(256, max(128, max(sw, sh))) / max(sw, sh)
    w, h = max(4, 2 ** round(np.log2(sw * k))), max(4, 2 ** round(np.log2(sh * k)))
    px = w / sw
    a = read(path, w, h)
    L = (a[..., :3] * [0.3, 0.59, 0.11]).sum(-1) ** 0.8
    return L / (blur(L, 24 * px) + 0.04), px, a

def pale_mortar(L, px):
    """Whether the region's thin lines are paler than what they cross."""
    j = blur(L, 1.3 * px) - blur(L, 12 * px)
    return float((j ** 3).mean()) / (float(j.std()) ** 3 + 1e-6) > 0.5

def dressed(L, px, rng):
    """Whether ashlar finds courses of stones in the region."""
    h, *_ = ashlar(L, px, rng)
    j = h < 0.62
    lab, n = ndimage.label(~j)
    if n == 0:
        return False
    size = ndimage.sum(np.ones_like(h), lab, np.arange(1, n + 1))
    stones = int((size >= (5 * px) ** 2).sum())
    share = float(j.mean())
    return stones >= 3 and 0.02 < share < 0.3

def stones_found(L, px, rng):
    """Whether the stone finder lays real stones over the region: enough of it, and not specks."""
    from stones import stones
    h, depth, occ, j, found, *_ = stones(L, px, rng, flat=False, edges=None, courses=True)
    if found < 0.45:
        return False
    lab, n = ndimage.label(~(j > 0.5))
    if n < 3:
        return False
    size = ndimage.sum(np.ones_like(L), lab, np.arange(1, n + 1))
    big = size[size >= (4 * px) ** 2]
    return len(big) >= 3 and float(np.median(big)) >= (9 * px) ** 2 and len(big) <= 80

def choose(L, a, px, rng, was):
    """A rectangle's recipe: plaster where it is smooth (a panel, a daubed or plain wall, which rock
    turns to blotches), wood where it is brown boards with a grain, else as it was."""
    if float((L - blur(L, 8 * px)).std()) < 0.155:
        return 'plaster'
    if classify(L, a, px) == 'wood':
        return 'wood'
    return was

def main(src, table, ids_file):
    ids = {l.strip() for l in open(ids_file) if l.strip()}
    lines = open(table).read().split('\n')
    for i, line in enumerate(lines):
        f = line.split('\t')
        if f[0] not in ids:
            continue
        path = os.path.join(src, f[0] + '.png')
        L, px, a = light(path)
        hh, ww = L.shape
        rng = np.random.default_rng(int(f[0], 16))
        settings = f[4:]
        if f[2] == 'rock':
            f[1], f[2] = 'mixed', 'mixed'
            settings = settings + ['0,0,1,1,rock']
        out, changed = [], []
        for s in settings:
            if ',' in s:
                x, y, w, h, name = s.split(',')
                # Masonry whose stones are not found falls back to rock, and blotches as rock does.
                if name.split(':')[0] in ('rock', 'masonry'):
                    x0, y0 = round(float(x) * ww), round(float(y) * hh)
                    x1, y1 = round((float(x) + float(w)) * ww), round((float(y) + float(h)) * hh)
                    if x1 - x0 >= 4 and y1 - y0 >= 4:
                        name = choose(L[y0:y1, x0:x1], a[y0:y1, x0:x1], px, rng, name)
                        changed.append(name)
                s = ','.join([x, y, w, h, name])
            out.append(s)
        lines[i] = '\t'.join(f[:4] + out)
        print(f[0], ' '.join(changed) or 'no rock rectangle')
    open(table, 'w').write('\n'.join(lines))

if __name__ == '__main__':
    main(*sys.argv[1:4])
