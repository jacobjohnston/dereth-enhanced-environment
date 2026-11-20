# check_relief.py <retail pngs> <pack folder> [<other pack folder>] [--sub 2005/]: how well each
# material's height follows its own picture. For each picture with a height map it prints
#   align: the share of the height's narrow valleys (its joints and cracks) lying on a line or an
#          edge of the picture, within a texel and a half; low means joints the picture lacks.
#   phantom: the share of the map where the height dips a spread below its mean while the picture
#          there is plain and has no line; high means blotches and pits the picture lacks.
# With a second pack folder it prints both and whether the second is no worse: align no lower
# (0.02 slack) and phantom no higher (0.008 slack), or no height at all only where the first's
# was clearly broken (align under 0.5 or phantom over 0.05). A height map with almost no valleys counts as aligned.
import os, subprocess, sys
import numpy as np
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from masonry import blur
from relief import read

def size(path):
    return tuple(map(int, subprocess.run(['identify', '-format', '%w %h', path], capture_output=True, text=True, check=True).stdout.split()))

def z(a):
    return (a - a.mean()) / (a.std() + 1e-6)

def measure(picture, height):
    w, h = size(height)
    hm = read(height, w, h)[..., 0]
    a = read(picture, w, h)
    L = (a[..., :3] * [0.3, 0.59, 0.11]).sum(-1)
    px = w / 128
    # The picture's lines (thin dark or pale strokes) and edges (steps in its light).
    lines = np.abs(z(blur(L, 0.7 * px) - blur(L, 3 * px))) > 1.0
    gy, gx = np.gradient(blur(L, 1.0 * px))
    edges = z(np.hypot(gx, gy)) > 1.0
    near = ndimage.binary_dilation(lines | edges, iterations=max(1, round(1.5 * px)))
    # The height's joints and cracks: narrow valleys, lower than what is about them.
    valley = z(blur(hm, 0.5 * px) - blur(hm, 3 * px)) < -1.2
    align = float(near[valley].mean()) if valley.sum() > 0.003 * valley.size else 1.0
    low = z(blur(hm, 3 * px)) < -1
    plain = np.abs(z(blur(L, 3 * px))) < 0.5
    phantom = float((low & plain & ~near).mean())
    return align, phantom

def main(args):
    sub = args[args.index('--sub') + 1] if '--sub' in args else ''
    pos = [a for i, a in enumerate(args) if not a.startswith('--') and (i == 0 or args[i - 1] != '--sub')]
    src, first = pos[0], pos[1]
    second = pos[2] if len(pos) > 2 else None
    for p in sorted(os.listdir(src)):
        if not p.startswith('0x') or not p.endswith('.png'):
            continue
        id = p[:-4]
        pic = os.path.join(src, p)
        h1 = os.path.join(first, 'materials', sub + id + '_height.png')
        a1 = measure(pic, h1) if os.path.exists(h1) else None
        if second is None:
            print(id, *(f'{v:.3f}' for v in a1) if a1 else ('-', '-'))
            continue
        h2 = os.path.join(second, 'materials', sub + id + '_height.png')
        a2 = measure(pic, h2) if os.path.exists(h2) else None
        if a2 is None:
            ok = a1 is None or a1[0] < 0.5 or a1[1] > 0.05
        elif a1 is None:
            ok = a2[0] >= 0.6 and a2[1] <= 0.02
        else:
            ok = a2[0] >= a1[0] - 0.02 and a2[1] <= a1[1] + 0.008
        fmt = lambda m: f'{m[0]:.3f} {m[1]:.3f}' if m else '- -'
        print(id, fmt(a1), fmt(a2), 'ok' if ok else 'worse')

if __name__ == '__main__':
    main(sys.argv[1:])
