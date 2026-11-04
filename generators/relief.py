# Works out a normal, height, occlusion and roughness picture from each of the player's pictures in a
# folder, and adds a [[material]] for it to a pack folder's manifest that keeps the player's own
# picture (`keep_retail_picture`), with the picture's average colour as the fallback a client without
# depth mapping draws (fallback.py). Nothing of the picture's pixels goes into the pack. Pictures of
# artwork (the designs in tables/recipes.tsv), and pictures that can be seen through, are left out.
# relief.py <the player's pictures> <pack folder> [recipes file]
import glob, os, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from masonry import blur, block_height, survey, thatch_height
from recipes import RECIPES as SHAPES, slime
import grit as GRIT
import fallback as FALLBACK
SRC, PACK = sys.argv[1:3]
TABLES = os.path.join(HERE, '..', 'tables')
# Pictures of artwork (carvings, emblems, painted scenes), whose relief would trace the drawing.
DESIGNS = set()
RECIPES = {}
for line in open(sys.argv[3] if len(sys.argv) > 3 else os.path.join(TABLES, 'recipes.tsv')):
    if line.strip() and not line.startswith('#'):
        id, material, recipe, damp, *rest = line.rstrip('\n').split('\t')
        RECIPES[id] = recipe, float(damp), ' '.join(rest).split()
        if material == 'design':
            DESIGNS.add(id)
out = os.path.join(PACK, 'materials'); os.makedirs(out, exist_ok=True)
def read(path, w, h):
    raw = subprocess.run(['magick', path, '-virtual-pixel', 'tile', '-filter', 'Catrom', '-distort', 'Resize', f'{w}x{h}!', '-depth', '8', 'rgba:-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 4).astype(np.float32) / 255
def write(path, a):
    h, w, c = a.shape
    subprocess.run(['magick', '-define', 'png:exclude-chunks=date,time', '-size', f'{w}x{h}', '-depth', '8', 'rgba:-', path], input=(np.clip(np.nan_to_num(a), 0, 1) * 255 + 0.5).astype(np.uint8).tobytes(), check=True)
def setting(settings, name, default):
    return next((float(x[len(name):]) for x in settings if x.startswith(name)), default)
def mixed(settings, Lb, px, rng):
    """A picture of several materials: each rectangle shaped by its own recipe, a hair's blend between."""
    h, w = Lb.shape
    H, K, O, R = [np.zeros((h, w), np.float32) for _ in range(4)]
    made = {}
    for rect in settings:
        if ',' not in rect:
            continue
        x, y, rw, rh, name = rect.split(',')
        x0, y0 = round(float(x) * w), round(float(y) * h)
        x1, y1 = round((float(x) + float(rw)) * w), round((float(y) + float(rh)) * h)
        if name not in made:
            made[name] = SHAPES[name](Lb, px, rng)
        s, k, o, r = made[name]
        H[y0:y1, x0:x1] = s[y0:y1, x0:x1]
        K[y0:y1, x0:x1] = k
        O[y0:y1, x0:x1] = o[y0:y1, x0:x1]
        R[y0:y1, x0:x1] = (r if np.isscalar(r) else r[y0:y1, x0:x1])
    return blur(H, 0.25 * px), K, O, R
rng = np.random.default_rng(5)
tables = ''
flipped = []
for path in sorted(glob.glob(os.path.join(SRC, '0x*.png'))):
    id = os.path.basename(path)[:-4]
    recipe, damp, settings = RECIPES.get(id, ('none', 0, []))
    if recipe == 'none' or id in DESIGNS: continue
    sw, sh = map(int, subprocess.run(['identify', '-format', '%w %h', path], capture_output=True, text=True, check=True).stdout.split())
    if min(sw, sh) < 32: continue
    # 256 along its longer side, for grit finer than most retail pictures hold; 512 only for the
    # largest. The whole pack must fit in the client under the package scan's cap for one file.
    side = 512 if max(sw, sh) >= 512 else 256
    k = side / max(sw, sh)
    w, h = 2 ** round(np.log2(max(4, sw * k))), 2 ** round(np.log2(max(4, sh * k)))
    px = w / sw
    a = read(path, w, h)
    # The fallback colour would draw over what shows through it.
    if (a[..., 3] < 0.98).mean() > 0.01: continue
    L = (a[..., :3] * [0.3, 0.59, 0.11]).sum(-1) ** 0.8
    if L.max() < 0.02: continue
    L = L / (blur(L, 24 * px) + 0.04)
    g = [blur(L, s * px) for s in (0.45, 1.3, 4, 12)]
    # Crevices read dark: broad forms weigh more than fine ones, as their slopes are gentler.
    hgt = 0.7 * (g[0] - g[1]) + 1.6 * (g[1] - g[2]) + 2.6 * (g[2] - g[3])
    # Thin pale lines over a dark field are mortar, not ridges: they sink.
    joints = g[1] - g[3]
    Lb = L
    if 'noflip' not in settings and ('flip' in settings or float((joints ** 3).mean()) / (float(joints.std()) ** 3 + 1e-6) > 1.6):
        hgt = -hgt
        flipped.append(id)
        Lb = 2 * float(L.mean()) - L
    contrast = np.sqrt(blur((g[0] - g[2]) ** 2, 4 * px))
    n = rng.standard_normal((h, w)).astype(np.float32)
    grit = blur(n, 0.9) - blur(n, 3.0)
    grit = grit / (grit.std() + 1e-6) * (0.25 + np.minimum(1.5, contrast / (contrast.mean() + 1e-4)))
    dx = lambda f: (np.roll(f, -1, 1) - np.roll(f, 1, 1)) / 2
    dy = lambda f: (np.roll(f, -1, 0) - np.roll(f, 1, 0)) / 2
    hx, hy = dx(hgt) * px, dy(hgt) * px
    rms = float(np.sqrt((hx * hx + hy * hy).mean())) + 1e-6
    gain = min(0.55 / rms, 7)
    gx, gy = dx(grit) * 0.09, dy(grit) * 0.09
    nx, ny = -(hx * gain + gx), hy * gain + gy
    cut = a[..., 3].min() < 0.5
    # Solid things are shaped as they are built, rather than read from the picture's brightness.
    built = None
    shape = None
    if recipe == 'mixed':
        shape = mixed(settings, Lb, px, rng)
    elif recipe in SHAPES and recipe != 'thatch' or (recipe == 'thatch' and 'made' in settings):
        # What is pale on flesh stands proud, however thin.
        shape = SHAPES[recipe](L if recipe == 'organic' else Lb, px, rng)
    elif not cut and recipe != 'design':
        if recipe == 'thatch':
            built = thatch_height(L, px), 1.6, None
        elif survey(Lb, px)[0] > 0.62:
            made, joint = block_height(Lb, px, rng)
            built = made, 1.2, joint
    if built:
        k = built[1] * px
        nx, ny = -dx(built[0]) * k + -gx * 0.5, dy(built[0]) * k + gy * 0.5
    r = np.clip(0.72 + 0.2 * (1 - L / L.max()) + 0.05 * grit, 0, 1)
    if shape:
        s, strength, so, sr = shape
        # How far one map texel is on the surface says how steep a sunk edge stands.
        repeat = next((float(x[7:]) for x in settings if x.startswith('repeat=')), 3.3)
        k = strength * px * np.clip(0.03 / (repeat / w) / 2.4, 0.5, 2.0)
        fine = 0.35 if recipe in ('plaster', 'metal') else 0.5
        nx, ny = -dx(s) * k + -gx * fine, dy(s) * k + gy * fine
        r = np.clip(sr + 0.05 * grit, 0, 1)
    if cut:
        solid = blur((a[..., 3] > 0.5).astype(np.float32), 1.5) > 0.98
        nx, ny = nx * solid, ny * solid
    l = np.sqrt(nx * nx + ny * ny + 1)
    one = np.ones((h, w), np.float32)
    write(f'{out}/{id}_normal.png', np.dstack([nx / l / 2 + 0.5, ny / l / 2 + 0.5, 1 / l / 2 + 0.5, one]))
    o = 1 - np.clip((blur(hgt, 3 * px) - hgt) / (hgt.std() + 1e-5) * 0.3, 0, 0.5)
    if built:
        o = 1 - np.clip((blur(built[0], 2.5 * px) - built[0]) * 3.2, 0, 0.95)
    if shape:
        o = so
    write(f'{out}/{id}_occlusion.png', np.dstack([o, o, o, one]))
    write(f'{out}/{id}_roughness.png', np.dstack([r, r, r, one]))
    soft = blur(hgt, 0.8 * px)
    lo, hi = np.percentile(soft, [3, 97])
    # What is not built takes about half the depth a block's joint does.
    d = one if cut else 1 - 0.5 * (1 - np.clip((soft - lo) / (hi - lo + 1e-5), 0, 1) ** 0.7)
    if built:
        d = np.clip(built[0] / (built[0].max() + 1e-5), 0, 1)
    if shape and not cut:
        d = np.clip(shape[0], 0, 1)
    write(f'{out}/{id}_height.png', np.dstack([d, d, d, one]))
    wet = ''
    if recipe == 'organic':
        w = slime(np.clip(shape[0], 0, 1), px, rng)
        write(f'{out}/{id}_damp.png', np.dstack([w, w, w, one]))
        wet = f'damp_map = "materials/{id}_damp.png"\ndamp_floors = true\n'
    FALLBACK.write(f'{out}/{id}_fallback.png', FALLBACK.average(os.path.join(SRC, f'{id}.png')))
    tables += f'''
[[material]]
texture = "{id}"
base_color = "materials/{id}_fallback.png"
keep_retail_picture = true
normal = "materials/{id}_normal.png"
roughness = "materials/{id}_roughness.png"
occlusion = "materials/{id}_occlusion.png"
height = "materials/{id}_height.png"
damp = {damp}
{wet}grit = "grit/{GRIT.tile_of(recipe, settings)}.png"
grit_repeat = [{GRIT.repeats(setting(settings, 'repeat=', 3.3))}, {GRIT.repeats(setting(settings, 'repeatv=', 3.3))}]
author = "Worked out from the player's own picture by relief.py"
tool = "relief.py"
license = "CC0-1.0"
'''
os.makedirs(os.path.join(PACK, 'grit'), exist_ok=True)
for name, fn in GRIT.TILES.items():
    GRIT.write(os.path.join(PACK, 'grit', name + '.png'), GRIT.tile(fn))
open(os.path.join(PACK, 'manifest.toml'), 'a').write(tables)
print(tables.count('[[material]]'), 'materials; mortar flipped:', ' '.join(flipped))
