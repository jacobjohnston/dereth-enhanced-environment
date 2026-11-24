# Works out a normal, height, occlusion and roughness picture from each of the player's pictures in a
# folder, and writes a [[material]] for it into a pack folder's manifest that keeps the player's own
# picture (`keep_retail_picture`), with the picture's average colour as the fallback a client without
# depth mapping draws (fallback.py). Nothing of the picture's pixels goes into the pack. A picture
# tables/recipes.tsv does not list is shaped by the recipe it looks to want (recipes.classify). A
# picture of artwork (a design) or of no relief (flat) has no material: the client draws it as retail does. A
# picture that can be seen through is shaped over what of it is solid, and takes no height. The
# materials of an earlier run are replaced, and their pictures removed.
# relief.py <the player's pictures> <pack folder> [recipes file] [--survey <pictures.tsv>]
#           [--most <side>] [--least <side>] [--jobs <n>] [--report <file>]
#           [--into <era> --stands-for <eras.tsv>] [--fingerprints <fingerprints.tsv>] [--like <folder>]
# --survey: the survey's pictures.tsv (pyreal-art survey --pixels): leaves out what is drawn see-through,
#   glowing or as the sky, and gives an unlisted picture its repeat and whether it is a floor.
# --most, --least: the longest and shortest a map's longer side may be (256 and 128): a map is its
#   picture's size within them, so the whole pack fits under the package scan's cap for one file.
# --report: writes each picture's recipe and map size, or why it has no material, a line each.
# --into: the materials for an older era's pictures (pyreal-art pictures), in materials/<era>/: only
#   those --stands-for (tables/eras.tsv) lists for the era, each taking the survey row of the
#   end-of-retail picture it stands for, and its recipe where the table says so. A run replaces only
#   its own era's materials, and a run without --into only those directly in materials/.
# --like: the pictures a recipe's like=ID names (a picture shaped from another era's picture of the
#   same layout, so the two match).
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
# How deep the client's deepest relief reaches, metres (a height map's 0).
DEEPEST = 0.12

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

def mixed(settings, Lb, px, rng, L=None, a=None):
    """A picture of several materials: each rectangle shaped by its own recipe as a picture of its
    own, its edges where it meets another, and eased into the next. A rectangle named recipe:flip
    takes its own pale lines for mortar, recipe:noflip keeps its own light, whatever the whole
    picture's, :grid lays a flagstone's joints straight, :open makes no crease where it meets
    another rectangle, :even drops shading that runs the whole way across, :rough=K adds its own cracks and grime, :moss lays moss over it flat, :ivy=K raises leaves K proud of it, :bare=K raises what is not green K proud of the green, :course makes ashlar one course, :block makes it one stone, :warm=K raises brown wood K proud of grey, :iron=K raises grey iron on wood (hinges, straps) K proud of it, :tiles=K raises a coloured tile pattern K proud of its tan field, :shade takes its shape from its light, :smooth[=K] drops its pits (blurring K texels), :grassy lays grass where it is green, :sheet=K raises a pale sheet (parchment) K proud of the stone about it and its ink proud of the sheet, :glaze=K makes it smooth (roughness K), :d=K scales its depth by K, and :at=K sets it K of the picture's range lower."""
    h, w = Lb.shape
    rs = rects(settings, w, h)
    edges = band_edges(rs, w, h, px)
    A, O, R, F = [np.ones((h, w), np.float32) for _ in range(4)]
    A[:] = 0
    F[:] = 0
    deepest = 1e-3
    lower = np.zeros((h, w), np.float32)
    for x0, y0, x1, y1, name in rs:
        name, *turns = name.split(':')
        # recipe:open meets what is beside it with no crease of its own; recipe:d=K scales its depth.
        cut = None if edges is None or 'open' in turns else edges[y0:y1, x0:x1]
        scale = next((float(t[2:]) for t in turns if t.startswith('d=')), 1.0)
        part = Lb[y0:y1, x0:x1]
        if ('flip' in turns or 'noflip' in turns) and L is not None:
            part = L[y0:y1, x0:x1]
            part = 2 * float(part.mean()) - part if 'flip' in turns else part
        if 'even' in turns:
            # recipe:even: shading that runs the whole way across (a ledge's cast shadow) is no shape.
            from scipy.ndimage import gaussian_filter1d
            row = gaussian_filter1d(part.mean(1), 1.5 * px, mode='nearest')[:, None]
            part = part * (float(part.mean()) / np.maximum(row, 1e-3))
        grid = dict(grid=True) if 'grid' in turns else {}
        grid.update(course=True) if 'course' in turns else None
        grid.update(block=True) if 'block' in turns else None
        s, depth, o, r, *fine = SHAPES[name](part, px, rng, cut, **grid)
        sm = next((float(t[7:] or 0.6) for t in turns if t.startswith('smooth')), 0.0)
        if sm:
            # recipe:smooth[=K]: the stones' faces without their pits and grain, the joints kept.
            s, fine = blur(s.astype(np.float32), sm * px), []
        if 'shade' in turns:
            # recipe:shade: a carving's shape is its light, its dark grooves sunk and its pale work proud.
            g = blur(part, 0.8 * px)
            lo, hi = np.percentile(g, 5), np.percentile(g, 95)
            s = 0.4 + 0.6 * np.clip((g - lo) / max(float(hi - lo), 1e-3), 0, 1)
        sheet = next((float(t[6:] or 0.4) for t in turns if t.startswith('sheet')), 0.0)
        if sheet and L is not None:
            # recipe:sheet=K: a pale sheet (parchment) stands K proud of the stone about it, its dark ink proud of the sheet.
            from scipy.ndimage import grey_closing
            g = L[y0:y1, x0:x1]
            k = max(3, round(11 * px)) | 1
            shut = grey_closing(g, size=(k, k), mode='constant', cval=0.0)
            wide = blur(shut, 1.5 * px)
            lo, hi = np.percentile(wide, 15), np.percentile(wide, 85)
            m = np.clip(blur(np.clip((wide - (lo + hi) / 2) / max(0.15 * float(hi - lo), 1e-3), 0, 1).astype(np.float32), 0.6 * px), 0, 1)
            ink = np.clip(shut - g, 0, None)
            ink = np.clip(blur(ink, 0.4 * px) / max(float(np.percentile(ink[m > 0.5], 98)) if (m > 0.5).any() else 1e-3, 1e-3), 0, 1) * m
            s = s * (1 - sheet) * (1 - m) + (1 - 0.5 * sheet + 0.5 * sheet * ink) * m
        rough = next((float(t[6:]) for t in turns if t.startswith('rough=')), 0.0)
        if rough:
            # recipe:rough=K lays the picture's own cracks and grime over the recipe's shapes.
            g = SHAPES['surface'](part, px, rng)[0]
            s = np.clip(s + rough * (g - float(g.mean())), 0, 1)
        ivy = next((float(t[4:] or 0.25) for t in turns if t.startswith('ivy')), 0.0)
        bare = next((float(t[5:] or 0.25) for t in turns if t.startswith('bare')), 0.0)
        if ('moss' in turns or ivy or bare) and a is not None:
            # recipe:moss: moss grown over the part has no shape of its own; it lies at the part's face.
            c = a[y0:y1, x0:x1, :3]
            m = np.clip((c[..., 1] - 0.5 * (c[..., 0] + c[..., 2]) - 0.03) / 0.05, 0, 1)
            m = np.clip(blur(m.astype(np.float32), 0.5 * px), 0, 1) if bare else np.clip(blur(m.astype(np.float32), 1.0 * px) * 1.5, 0, 1)
            face = float(np.percentile(s[m < 0.5], 70)) if (m < 0.5).any() else float(s.mean())
            # recipe:ivy=K: leaves grown over the part stand K proud of it instead.
            s = np.clip(s - ivy, 0, 1) * (1 - m) + (1.0 if ivy else face) * m
            # recipe:bare=K: what is not green (roots through grass) stands K proud of the green.
            s = s * (1 - m) + np.clip(s - bare, 0, 1) * m if bare else s
        if 'grassy' in turns and a is not None:
            # recipe:grassy: where the part is green, grass's blades and tufts in place of its own shape.
            c = a[y0:y1, x0:x1, :3]
            m = np.clip((c[..., 1] - 0.5 * (c[..., 0] + c[..., 2]) - 0.02) / 0.05, 0, 1)
            m = np.clip(blur(m.astype(np.float32), 1.5 * px), 0, 1)
            gh = SHAPES['grass'](part, px, rng)[0]
            s = s * (1 - m) + (float(np.percentile(s, 60)) - 0.25 + 0.3 * gh) * m
        warm = next((float(t[5:] or 0.25) for t in turns if t.startswith('warm')), 0.0)
        if warm and a is not None:
            # recipe:warm=K: brown wood (a brace across plaster) stands K proud of what is grey.
            c = a[y0:y1, x0:x1, :3]
            m = np.clip(blur(np.clip((c[..., 0] - c[..., 2] - 0.08) / 0.08, 0, 1).astype(np.float32), 0.7 * px), 0, 1)
            s = s * m + np.clip(s - warm, 0, 1) * (1 - m)
        iron = next((float(t[5:] or 0.3) for t in turns if t.startswith('iron')), 0.0)
        if iron and a is not None:
            # recipe:iron=K: grey iron on wood (hinges, straps) stands K proud of it, level; thin dark seams are no iron.
            from scipy.ndimage import binary_opening
            c = a[y0:y1, x0:x1, :3]
            cold = (c[..., 0] - c[..., 2]) / (c[..., 0] + 0.03) < 0.29
            cold = binary_opening(cold, iterations=max(1, round(1.2 * px)))
            m = np.clip(blur(cold.astype(np.float32), 0.6 * px) * 1.4, 0, 1)
            s = np.clip(s - iron, 0, 1) * (1 - m) + m
        tiles = next((float(t[6:] or 0.12) for t in turns if t.startswith('tiles')), 0.0)
        if tiles and a is not None:
            # recipe:tiles=K: a coloured tile pattern (blue, green, purple) stands K proud of its tan field, filled solid.
            from scipy import ndimage
            c = a[y0:y1, x0:x1, :3]
            cold = (c[..., 0] - c[..., 2]) / (c[..., 0] + 0.03) < 0.33
            it = max(1, round(2 * px))
            cold = ndimage.binary_fill_holes(ndimage.binary_closing(cold, iterations=it))
            cold = ndimage.binary_opening(cold, iterations=max(1, it // 2))
            lab, n = ndimage.label(cold)
            if n:
                cold = np.r_[False, ndimage.sum(cold, lab, range(1, n + 1)) > 40 * px * px][lab]
            m = np.clip(blur(cold.astype(np.float32), 0.6 * px), 0, 1)
            s = np.clip(s - tiles, 0, 1) * (1 - m) + s * m
        # The picture's range is set by its deepest rectangle as made, so one turned down stays shallow.
        deepest = max(deepest, depth, depth * scale)
        depth *= scale
        A[y0:y1, x0:x1] = (s - 1) * depth
        if fine:
            F[y0:y1, x0:x1] = fine[0] * depth
        O[y0:y1, x0:x1] = o
        R[y0:y1, x0:x1] = r
        # recipe:glaze=K: a glazed or polished part, its roughness K all over.
        R[y0:y1, x0:x1] = next((float(t[6:]) for t in turns if t.startswith('glaze=')), R[y0:y1, x0:x1])
        # recipe:at=K sits behind its neighbours: a face under a ledge, a field behind a frame.
        lower[y0:y1, x0:x1] = next((float(t[3:]) for t in turns if t.startswith('at=')), 0.0)
    A = blur(A - lower * deepest, 0.25 * px)
    return np.maximum(1 + A / deepest, 0), deepest, O, R, F / deepest

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
    path, out, entry, seen, most, least, sub, print_, *rest = job
    skip = bool(rest and rest[0])
    id = os.path.basename(path)[:-4]
    material, recipe, damp, settings = entry or ('auto', None, 0.0, [])
    if entry and (recipe == 'none' or material == 'design') and not damp and skip:
        return id, None, 'flat: drawn as retail draws it'
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
    like = next((t[5:] for t in settings if t.startswith('like=')), None)
    if like:
        # like=ID: shaped from picture ID (in --like), another era's of the same layout as this one.
        at = os.path.join(os.environ.get('RELIEF_LIKE', ''), like + '.png')
        if not os.path.exists(at):
            return id, None, f'no picture {like} to be shaped like'
        a = read(at, w, h)
    solid = a[..., 3] >= 0.5
    seen_through = (a[..., 3] < 0.98).mean() > 0.01
    # solid: the see-through specks are gaps between stones in a solid wall, which take a height.
    cut = seen_through and 'solid' not in settings
    if seen_through:
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
    if flat and not damp and skip:
        # Drawn as retail draws it, so no material; iron.py and arms.py still take flat maps of their own.
        return id, None, 'flat: drawn as retail draws it'
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
        hgt, depth, o, r, fine = mixed(settings, Lb, px, rng, L, a)
    else:
        # What is pale on flesh stands proud, however thin.
        # Slabs in a plain grid, whose joints the stones' own blotches would hide (0x050026F7).
        grid = dict(grid=True) if 'grid' in settings else {}
        hgt, depth, o, r, *fine = SHAPES[recipe](L if recipe == 'organic' else Lb, px, rng, **grid)
        fine = fine[0] if fine else 0
    r = r * one
    clear = None
    if 'clearmap' in settings and setting(settings, 'clear=', 0.0):
        # clearmap: clear but where the picture is warm (a cork, a gold band), or under opaque=x:y:w:h[:oval].
        R, G, B = a[..., 0], a[..., 1], a[..., 2]
        opaque = np.clip((R - B - 0.04) / 0.08, 0, 1) * np.clip((R - G + 0.08) / 0.08, 0, 1) * (np.maximum(R, G) > 0.08)
        opaque = np.clip(blur(opaque.astype(np.float32), 1.5 * px) * 2, 0, 1)  # a band's dark stripes stay in it
        v, u = (np.mgrid[0:h, 0:w] + 0.5) / np.array([h, w])[:, None, None]
        for x, y, rw, rh, *oval in (s[7:].split(':') for s in settings if s.startswith('opaque=')):
            du, dv = (u - float(x)) / float(rw) - 0.5, (v - float(y)) / float(rh) - 0.5
            opaque = np.maximum(opaque, du * du + dv * dv <= 0.25 if oval else (abs(du) <= 0.5) & (abs(dv) <= 0.5))
        clear = np.clip(blur(1 - opaque.astype(np.float32), 0.6 * px), 0, 1)
    # glaze=K: glazed pottery, glass or polished stone, its roughness K all over (only the clear part with a clearmap).
    if setting(settings, 'glaze=', 0.0):
        g = one * setting(settings, 'glaze=', 0.0)
        r = g if clear is None else r * (1 - clear) + g * clear
    # depth=K: the whole picture shallower (or deeper), in its height map as well as its normal.
    k = setting(settings, 'depth=', 1.0)
    if not flat and k != 1.0:
        hgt = 1 - (1 - hgt) * k
        depth *= k
    # mm=N: a small prop's picture, its relief at most N millimetres deep at the deepest depth mapping.
    mm = setting(settings, 'mm=', 0.0)
    if not flat and mm > 0:
        k = min(1.0, mm / 1000 / DEEPEST / max(1 - float(np.percentile(hgt, 0.5)), 1e-3))
        hgt = 1 - (1 - hgt) * k
        depth *= k
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
    # clear=K, refraction=K, wet=K: what it is made of (glass, crystal, a film of water), as the manifest says them.
    matter = ''.join(f'{k} = {setting(settings, k + "=", 0.0):g}\n' for k in ('clear', 'refraction', 'wet') if setting(settings, k + '=', 0.0))
    # ice: glacier ice, as the ice spires are (deep where thick, bent, mirroring the sky).
    matter += 'ice = true\n' if 'ice' in settings else ''
    if clear is not None:
        write(f'{out}/{id}_clear.png', np.dstack([clear, 0 * clear, 0 * clear, np.ones_like(clear)]))
        matter += f'clear_map = "materials/{sub}{id}_clear.png"\n'
    block = f'''
[[material]]
texture = "{id}"
{print_}base_color = "materials/{sub}{id}_fallback.png"
keep_retail_picture = true
{normal}roughness = "materials/{sub}{id}_roughness.png"
occlusion = "materials/{sub}{id}_occlusion.png"
{deep}damp = {damp}
{wet}{grit}{matter}author = "Worked out from the player's own picture by relief.py"
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
    os.environ['RELIEF_LIKE'] = option(args, '--like', '')
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
        # Pyreal draws End of Retail's picture for these beside this era (tables/drawn-as-eor.tsv): none.
        for line in open(os.path.join(TABLES, 'drawn-as-eor.tsv')):
            if line.strip() and not line.startswith('#'):
                for x in line.rstrip('\n').split('\t')[4].split():
                    if x.startswith(era + ':'):
                        stands.pop(x.split(':')[1], None)
        # Only another generator's material for this era's own picture keeps it (arms.py's 2005 blade).
        taken = set()
        for b in kept:
            other = b.startswith('[[material]]') and not re.search(rf'^tool = "{TOOL}"$', b, re.M)
            m = re.search(r'^texture = (.*)$', b, re.M) if other and re.search(where, b, re.M) else None
            taken.update(re.findall(r'0x[0-9A-Fa-f]{8}', m.group(1)) if m else [])
    # An older era's own hand recipes (tables/recipes-<era>.tsv), for its pictures whose layout
    # differs from the end-of-retail picture they stand for: they come before that picture's.
    own = {}
    own_at = os.path.join(TABLES, f'recipes-{era}.tsv') if era else None
    if own_at and os.path.exists(own_at):
        for line in open(own_at):
            if line.strip() and not line.startswith('#'):
                id, material, recipe, damp, *rest = line.rstrip('\n').split('\t')
                own[id] = material, recipe, float(damp), ' '.join(rest).split()
    # A flat picture iron.py or arms.py makes its material from keeps relief.py's, for them to replace.
    from iron import IRON
    from arms import ARMS
    builds = set(IRON) | set(ARMS)
    def job(p):
        id = os.path.basename(p)[:-4]
        if era:
            eor, how = stands[id]
            entry = own.get(id) or (listed.get(eor) if how == 'recipe' else None)
            if how.startswith('ground:'):
                # ground:<recipe> [settings...]: the recipe, and any settings of its own after it.
                recipe, *more = how[7:].split()
                entry = ('ground', recipe, 0.0, [f'side={GROUND_SIDE}', f'repeat={GROUND_REPEAT}', f'repeatv={GROUND_REPEAT}', *more])
            return (p, out, entry, seen.get(eor), most, least, sub, named(id), id not in builds)
        return (p, out, listed.get(id), seen.get(id), most, least, sub, named(id), id not in builds)
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
