# Works out a normal, height, occlusion and roughness picture from each of the player's pictures in a
# folder, and writes a [[material]] for it into a pack folder's manifest that keeps the player's own
# picture (`keep_retail_picture`), with the picture's average colour as the fallback a client without
# depth mapping draws (fallback.py). Nothing of the picture's pixels goes into the pack. A picture
# tables/recipes.tsv does not list is shaped by the recipe it looks to want (recipes.classify). A
# picture of artwork (a design) or of no relief (flat) takes only its roughness and occlusion. A
# picture that can be seen through is shaped over what of it is solid, and takes no height. The
# materials of an earlier run are replaced, and their pictures removed.
# relief.py <the player's pictures> <pack folder> [recipes file] [--survey <pictures.tsv>]
#           [--most <side>] [--least <side>] [--jobs <n>] [--report <file>]
#           [--into <era> --stands-for <eras.tsv>] [--fingerprints <fingerprints.tsv>]
# --survey: the survey's pictures.tsv (pyreal-art survey --pixels): leaves out what is drawn see-through,
#   glowing or as the sky, and gives an unlisted picture its repeat and whether it is a floor.
# --most, --least: the longest and shortest a map's longer side may be (256 and 128): a map is its
#   picture's size within them, so the whole pack fits under the package scan's cap for one file.
# --report: writes each picture's recipe and map size, or why it has no material, a line each.
# --into: the materials for an older era's pictures (pyreal-art pictures), in materials/<era>/: only
#   those --stands-for (tables/eras.tsv) lists for the era, each taking the survey row of the
#   end-of-retail picture it stands for, and its recipe where the table says so. A run replaces only
#   its own era's materials, and a run without --into only those directly in materials/.
# --fingerprints: the fingerprint of each picture (pyreal-art pictures writes them), named in its
#   material so a client draws it only on that picture; fingerprints.tsv beside the pictures unless
#   named.
import glob, os, re, subprocess, sys
from concurrent.futures import ProcessPoolExecutor
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from masonry import blur
from recipes import RECIPES as SHAPES, classify, slime
from stones import inside
import grit as GRIT
import fallback as FALLBACK
TABLES = os.path.join(HERE, '..', 'tables')
TOOL = 'relief.py'
# Surface flags drawn see-through or glowing: their relief would show on nothing.
CLEAR = 0x10 | 0x100 | 0x200 | 0x10000
# A picture repeating over more than this many metres is the sky or a far backdrop.
BACKDROP = 100
# An older era's ground picture (eras.tsv's ground:<recipe>): its maps' side, finer than its 128
# texels for the grain, and the metres it repeats over, twice a 24 m cell.
GROUND_SIDE, GROUND_REPEAT = 512, 12.0
# The steepest a normal leans, as a slope.
STEEPEST = 2.5

def option(args, name, default):
    return args[args.index(name) + 1] if name in args else default

def read(path, w, h):
    raw = subprocess.run(['magick', path, '-virtual-pixel', 'tile', '-filter', 'Catrom', '-distort', 'Resize', f'{w}x{h}!', '-depth', '8', 'rgba:-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 4).astype(np.float32) / 255

def write(path, a):
    h, w, c = a.shape
    subprocess.run(['magick', '-define', 'png:exclude-chunks=date,time', '-size', f'{w}x{h}', '-depth', '8', 'rgba:-', path], input=(np.clip(np.nan_to_num(a), 0, 1) * 255 + 0.5).astype(np.uint8).tobytes(), check=True)

def grey(path, v):
    write(path, np.dstack([v, v, v, np.ones_like(v)]))

def setting(settings, name, default):
    return next((float(x[len(name):]) for x in settings if x.startswith(name)), default)

def rects(settings, w, h):
    out = []
    for rect in settings:
        if ',' in rect:
            x, y, rw, rh, name = rect.split(',')
            x0, y0 = round(float(x) * w), round(float(y) * h)
            x1, y1 = round((float(x) + float(rw)) * w), round((float(y) + float(rh)) * h)
            if x1 > x0 and y1 > y0:
                out.append((x0, y0, x1, y1, name))
    return out

def band_edges(rs, w, h, px):
    """The lines a mixed picture's rectangles meet along, as the picture repeats; None for one."""
    if len(rs) < 2:
        return None
    e = np.zeros((h, w), bool)
    for x0, y0, x1, y1, _ in rs:
        if y1 - y0 < h:
            e[y0, x0:x1] = e[y1 - 1, x0:x1] = True
        if x1 - x0 < w:
            e[y0:y1, x0] = e[y0:y1, x1 - 1] = True
    return inside(~e, px) < 0.6 * px

def mixed(settings, Lb, px, rng):
    """A picture of several materials: each rectangle shaped by its own recipe as a picture of its
    own, its edges where it meets another, and eased into the next."""
    h, w = Lb.shape
    rs = rects(settings, w, h)
    edges = band_edges(rs, w, h, px)
    A, O, R, F = [np.ones((h, w), np.float32) for _ in range(4)]
    A[:] = 0
    F[:] = 0
    deepest = 1e-3
    for x0, y0, x1, y1, name in rs:
        cut = None if edges is None else edges[y0:y1, x0:x1]
        s, depth, o, r, *fine = SHAPES[name](Lb[y0:y1, x0:x1], px, rng, cut)
        deepest = max(deepest, depth)
        A[y0:y1, x0:x1] = (s - 1) * depth
        if fine:
            F[y0:y1, x0:x1] = fine[0] * depth
        O[y0:y1, x0:x1] = o
        R[y0:y1, x0:x1] = r
    A = blur(A, 0.25 * px)
    return 1 + A / deepest, deepest, O, R, F / deepest

def fill(a, solid, px):
    """The picture's colour where it is see-through, spread from what is solid about it."""
    k = solid.astype(np.float32)
    rgb = a[..., :3] * k[..., None]
    for s in (1, 3, 9, 27, 81):
        num = np.dstack([blur(rgb[..., c], s * px) for c in range(3)])
        den = blur(k, s * px)[..., None]
        rgb = np.where(k[..., None] > 0, rgb, num / np.maximum(den, 1e-4) * (den > 1e-3))
        k = np.maximum(k, (den[..., 0] > 1e-3).astype(np.float32))
    out = a.copy()
    out[..., :3] = np.clip(rgb, 0, 1)
    return out

def survey_of(path):
    """Each surveyed picture's repeat, surface flags and whether it is laid mostly as a floor."""
    out = {}
    if not path:
        return out
    lines = open(path).read().splitlines()
    head = lines[0].split('\t')
    col = {n: i for i, n in enumerate(head)}
    for line in lines[1:]:
        f = line.split('\t')
        area = lambda kind: sum(float(f[col[f'{p}_{kind}']]) for p in ('dungeon', 'room', 'outdoors'))
        floors, walls = area('floor'), area('wall') + area('slope') + area('ceiling')
        rep = lambda c: float(f[col[c]] or 3.3)
        out[f[0]] = dict(repeat=(rep('repeat_u'), rep('repeat_v')),
                         bits=int(f[col['surface_bits']], 16), floor=floors > walls, area=floors + walls)
    return out

def make(job):
    """One picture's maps written into `out`, and its [[material]], or why it has none."""
    path, out, entry, seen, most, least, sub, print_ = job
    id = os.path.basename(path)[:-4]
    material, recipe, damp, settings = entry or ('auto', None, 0.0, [])
    if seen:
        if seen['bits'] & CLEAR and entry is None:
            return id, None, 'see-through or glowing'
        if max(seen['repeat']) > BACKDROP:
            return id, None, 'the sky or a backdrop'
    sw, sh = map(int, subprocess.run(['identify', '-format', '%w %h', path], capture_output=True, text=True, check=True).stdout.split())
    # The picture's own size within least and most along its longer side; four texels at the least.
    k = min(most, max(least, max(sw, sh))) / max(sw, sh)
    # A ground picture's maps are made at their own side.
    k = setting(settings, 'side=', 0) / max(sw, sh) or k
    w, h = max(4, 2 ** round(np.log2(sw * k))), max(4, 2 ** round(np.log2(sh * k)))
    px = w / sw
    rng = np.random.default_rng(int(id, 16))
    a = read(path, w, h)
    solid = a[..., 3] >= 0.5
    cut = (a[..., 3] < 0.98).mean() > 0.01
    if cut:
        if not solid.any():
            return id, None, 'wholly see-through'
        a = fill(a, solid, px)
    L = (a[..., :3] * [0.3, 0.59, 0.11]).sum(-1) ** 0.8
    dark = float(np.percentile(L, 99)) < 0.03
    L = L / (blur(L, 24 * px) + 0.04)
    if entry is None:
        recipe = 'cutout' if cut else classify(L, a, px, bool(seen and seen['floor']))
        material = 'auto'
        if seen:
            settings = [f'repeat={seen["repeat"][0]:.3f}', f'repeatv={seen["repeat"][1]:.3f}']
    flat = recipe == 'none' or material == 'design' or dark
    # Thin pale lines over a dark field are mortar, not ridges: they sink.
    g = [blur(L, s * px) for s in (1.3, 12)]
    joints = g[0] - g[1]
    Lb = L
    skew = float((joints ** 3).mean()) / (float(joints.std()) ** 3 + 1e-6)
    if not flat and recipe != 'organic' and 'noflip' not in settings and ('flip' in settings or skew > 1.6):
        Lb = 2 * float(L.mean()) - L
    one = np.ones((h, w), np.float32)
    if flat:
        # No relief: a design's painted shading, or nothing at all. Its roughness and occlusion only.
        hgt, depth = one, 0.0
        soft = blur(L, 2 * px)
        o = one if dark else 1 - np.clip((blur(soft, 4 * px) - soft) / (soft.std() + 1e-5) * 0.15, 0, 0.35)
        r = np.clip(0.82 + 0.1 * (1 - np.clip(L / (np.percentile(L, 98) + 1e-5), 0, 1)), 0, 1)
    elif recipe == 'mixed':
        hgt, depth, o, r, fine = mixed(settings, Lb, px, rng)
    else:
        # What is pale on flesh stands proud, however thin.
        hgt, depth, o, r, *fine = SHAPES[recipe](L if recipe == 'organic' else Lb, px, rng)
        fine = fine[0] if fine else 0
    r = r * one
    if not flat:
        # The height as it stands, in retail texels; the normal leans with its slope there.
        # A stone's pits and grain, where its recipe keeps them out of the height, bend it too.
        A = (hgt - 1 + fine) * depth
        sx = (np.roll(A, -1, 1) - np.roll(A, 1, 1)) / 2 * px
        sy = (np.roll(A, -1, 0) - np.roll(A, 1, 0)) / 2 * px
        m = np.sqrt(sx * sx + sy * sy)
        k = np.minimum(1, STEEPEST / (m + 1e-6))
        nx, ny = -sx * k, sy * k
        if cut:
            edge = blur(solid.astype(np.float32), 1.0 * px) > 0.98
            nx, ny = nx * edge, ny * edge
        l = np.sqrt(nx * nx + ny * ny + 1)
        write(f'{out}/{id}_normal.png', np.dstack([nx / l / 2 + 0.5, ny / l / 2 + 0.5, 1 / l / 2 + 0.5, one]))
    if cut:
        o = np.where(solid, o, 1)
    grey(f'{out}/{id}_occlusion.png', o)
    grey(f'{out}/{id}_roughness.png', r)
    deep = ''
    if not flat and not cut:
        grey(f'{out}/{id}_height.png', np.clip(hgt, 0, 1))
        deep = f'height = "materials/{sub}{id}_height.png"\n'
    wet = ''
    if recipe == 'organic':
        wv = slime(np.clip(hgt, 0, 1), px, rng)
        grey(f'{out}/{id}_damp.png', wv)
        wet = f'damp_map = "materials/{sub}{id}_damp.png"\ndamp_floors = true\n'
    FALLBACK.write(f'{out}/{id}_fallback.png', FALLBACK.average(path))
    normal = '' if flat else f'normal = "materials/{sub}{id}_normal.png"\n'
    grit = '' if flat else (f'grit = "grit/{GRIT.tile_of(recipe, settings)}.png"\n'
                            f'grit_repeat = [{GRIT.repeats(setting(settings, "repeat=", 3.3))}, {GRIT.repeats(setting(settings, "repeatv=", 3.3))}]\n')
    block = f'''
[[material]]
texture = "{id}"
{print_}base_color = "materials/{sub}{id}_fallback.png"
keep_retail_picture = true
{normal}roughness = "materials/{sub}{id}_roughness.png"
occlusion = "materials/{sub}{id}_occlusion.png"
{deep}damp = {damp}
{wet}{grit}author = "Worked out from the player's own picture by relief.py"
tool = "relief.py"
license = "CC0-1.0"
'''
    kind = 'flat' if flat else ('cut-out' if cut else 'relief')
    return id, block, f'{kind} {recipe if material != "auto" else "auto:" + recipe} {w}x{h}'

def main(args):
    flags = [i for i, x in enumerate(args) if x.startswith('--')]
    pos = args[:flags[0]] if flags else args
    SRC, PACK = pos[:2]
    table = pos[2] if len(pos) > 2 else os.path.join(TABLES, 'recipes.tsv')
    seen = survey_of(option(args, '--survey', None))
    most, least = int(option(args, '--most', 256)), int(option(args, '--least', 128))
    jobs = int(option(args, '--jobs', os.cpu_count() or 4))
    listed = {}
    for line in open(table):
        if line.strip() and not line.startswith('#'):
            id, material, recipe, damp, *rest = line.rstrip('\n').split('\t')
            listed[id] = material, recipe, float(damp), ' '.join(rest).split()
    era = option(args, '--into', None)
    sub = f'{era}/' if era else ''
    out = os.path.join(PACK, 'materials', sub); os.makedirs(out, exist_ok=True)
    # An earlier run's materials go, and the pictures they named with them: this era's alone.
    path = os.path.join(PACK, 'manifest.toml')
    blocks = re.split(r'\n(?=\[\[)', open(path).read())
    where = rf'^base_color = "materials/{re.escape(sub)}[^/"]+"$'
    mine = lambda b: (b.startswith('[[material]]') and re.search(rf'^tool = "{TOOL}"$', b, re.M)
                      and re.search(where, b, re.M))
    kept = [b for b in blocks if not mine(b)]
    # The new materials go where the run's old ones began, so other entries keep their order.
    at = next((sum(1 for x in blocks[:i] if not mine(x)) for i, x in enumerate(blocks) if mine(x)), len(kept))
    keep = set(re.findall(r'"(materials/[^"]+\.png)"', '\n'.join(kept)))
    for b in blocks:
        for f in re.findall(r'"(materials/[^"]+\.png)"', b) if mine(b) else []:
            if f not in keep and os.path.exists(os.path.join(PACK, f)):
                os.remove(os.path.join(PACK, f))
    # A picture another generator makes a material for keeps it.
    taken = set()
    for b in kept:
        other = b.startswith('[[material]]') and not re.search(rf'^tool = "{TOOL}"$', b, re.M)
        m = re.search(r'^texture = (.*)$', b, re.M) if other else None
        taken.update(re.findall(r'0x[0-9A-Fa-f]{8}', m.group(1)) if m else [])
    prints_at = option(args, '--fingerprints', os.path.join(SRC, 'fingerprints.tsv'))
    prints = dict(l.rstrip('\n').split('\t')[:2] for l in open(prints_at) if l.strip()) if os.path.exists(prints_at) else {}
    named = lambda id: f'fingerprint = "{prints[id]}"\n' if id in prints else ''
    # An older era's picture takes the survey row, and maybe the recipe, of the one it stands for.
    stands = {}
    if era:
        for line in open(option(args, '--stands-for', os.path.join(TABLES, 'eras.tsv'))):
            f = line.rstrip('\n').split('\t')
            if line.strip() and not line.startswith('#') and f[0] == era:
                stands[f[1]] = (f[2], f[4])
        taken = set()
    def job(p):
        id = os.path.basename(p)[:-4]
        if era:
            eor, how = stands[id]
            entry = listed.get(eor) if how == 'recipe' else None
            if how.startswith('ground:'):
                entry = ('ground', how[7:], 0.0, [f'side={GROUND_SIDE}', f'repeat={GROUND_REPEAT}', f'repeatv={GROUND_REPEAT}'])
            return (p, out, entry, seen.get(eor), most, least, sub, named(id))
        return (p, out, listed.get(id), seen.get(id), most, least, sub, named(id))
    work = [job(p) for p in sorted(glob.glob(os.path.join(SRC, '0x*.png')))
            if os.path.basename(p)[:-4] not in taken and (not era or os.path.basename(p)[:-4] in stands)]
    tables, counts, report = '', {}, []
    with ProcessPoolExecutor(jobs) as pool:
        for id, block, why in pool.map(make, work, chunksize=4):
            report.append(f'{id}\t{why}')
            kind = why.split()[0] if block else 'none: ' + why
            counts[kind] = counts.get(kind, 0) + 1
            tables += block or ''
    os.makedirs(os.path.join(PACK, 'grit'), exist_ok=True)
    # The grit tiles, where grit.py has not made them already.
    for name, fn in GRIT.TILES.items():
        tile = GRIT.tile(fn)
        if not os.path.exists(os.path.join(PACK, 'grit', name + '.png')):
            GRIT.write(os.path.join(PACK, 'grit', name + '.png'), tile)
    head, tail = '\n'.join(kept[:at]).rstrip('\n') + '\n', '\n'.join(kept[at:])
    open(path, 'w').write(head + tables + ('\n' + tail if tail else ''))
    if '--report' in args:
        open(option(args, '--report', ''), 'w').write('\n'.join(report) + '\n')
    print(tables.count('[[material]]'), 'materials:', ', '.join(f'{v} {k}' for k, v in sorted(counts.items())))

if __name__ == '__main__':
    main(sys.argv[1:])
