# grit.py <out folder> [preview retail png, repeat in meters, material ...]: makes the shared detail tiles,
# one a material, from noise alone and tiling exactly: red and green the bend, blue the colour's own
# speckle about a half, alpha the roughness about a half. A tile spans TILE_M on the surface.
import os, subprocess, sys
import numpy as np
SIDE = 512
TILE_M = 0.8
rng = np.random.default_rng(11)
def noise(sx, sy=None):
    """Tiling noise with blobs about sx texels across and sy along, unit spread."""
    sy = sx if sy is None else sy
    n = rng.standard_normal((SIDE, SIDE))
    fy = np.fft.fftfreq(SIDE)[:, None]; fx = np.fft.rfftfreq(SIDE)[None, :]
    a = np.fft.irfft2(np.fft.rfft2(n) * np.exp(-2 * np.pi ** 2 * ((sx * fx) ** 2 + (sy * fy) ** 2)), s=(SIDE, SIDE))
    return a / a.std()
def pits(sx, cover):
    a = noise(sx)
    return np.clip((a - np.quantile(a, 1 - cover)) / 0.6, 0, 1)
def stone():
    h = 0.5 * noise(1.2) + 0.6 * noise(3) + 0.5 * noise(8) - 2.2 * pits(2.2, 0.03)
    return h, 0.6 * noise(1.5) + 0.4 * noise(6) - 1.6 * pits(2.2, 0.03), 0.5 * noise(4)
def rock():
    r = np.abs(noise(10)) + 0.6 * np.abs(noise(4)) + 0.35 * np.abs(noise(1.6))
    return -r * 1.4, -r * 0.7 + 0.4 * noise(2), 0.6 * noise(6)
def plaster():
    h = 0.35 * noise(1.1) + 0.5 * noise(14, 5) + 0.3 * noise(3)
    return h * 0.7, 0.35 * noise(1.5) + 0.35 * noise(20), 0.3 * noise(9)
def organic():
    # A wet membrane: smooth swellings, with a few pores; nothing sharp to break a highlight.
    h = 0.7 * noise(9) + 0.5 * noise(4) + 0.12 * noise(1.5) - 0.9 * pits(2.0, 0.008)
    return h, 0.5 * noise(7) - 0.8 * pits(2.0, 0.008), 0.3 * noise(9)
def fibre():
    # Wood and straw: their grain can run either way, even within a picture, so this has none.
    h = 0.6 * noise(1.0) + 0.5 * noise(2.5) + 0.3 * noise(7) - 1.2 * pits(1.2, 0.012)
    return h * 0.6, 0.5 * noise(1.5) + 0.3 * noise(8), 0.4 * noise(3)
def clay():
    h = 0.5 * noise(1.4) + 0.4 * noise(5) - 1.6 * pits(1.8, 0.02)
    return h, 0.6 * noise(2) + 0.4 * noise(10), 0.4 * noise(5)
def metal():
    h = 0.25 * noise(1, 8) + 0.5 * noise(6) - 1.8 * pits(1.6, 0.012)
    return h * 0.6, 0.5 * noise(4) - 1.2 * pits(1.6, 0.012), 0.9 * noise(10)
TILES = dict(stone=stone, rock=rock, plaster=plaster, fibre=fibre, clay=clay, metal=metal, organic=organic)
# Which tile each material takes.
OF = dict(organic='organic', masonry='stone', flagstone='stone', design='stone', rock='rock', plaster='plaster', roof='clay', metal='metal', wood='fibre', thatch='fibre')
def tile_of(recipe, settings):
    """The tile a picture takes: a mixed picture's is that of the most of it."""
    if recipe != 'mixed':
        return OF[recipe]
    area = {}
    for r in settings:
        if ',' in r:
            x, y, w, h, name = r.split(',')
            area[OF[name]] = area.get(OF[name], 0) + float(w) * float(h)
    return max(area, key=area.get) if area else 'stone'
def repeats(meters):
    """How many whole times a tile goes into a picture's repeat, so a picture still tiles."""
    return max(1, round(meters / TILE_M))
BEND, SPECKLE, SHINE = 0.16, 0.05, 0.05
# A tile that bends less than the others.
BENDS = dict(organic=0.07)
def tile(fn):
    h, c, r = fn()
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / 2
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / 2
    k = BENDS.get(fn.__name__, BEND) / (np.sqrt((dx * dx + dy * dy).mean()) + 1e-6)
    return np.dstack([np.clip(0.5 - dx * k / 2, 0, 1), np.clip(0.5 + dy * k / 2, 0, 1), np.clip(0.5 + c * SPECKLE, 0, 1), np.clip(0.5 + r * SHINE, 0, 1)]).astype(np.float32)
def write(path, a):
    h, w = a.shape[:2]
    subprocess.run(['magick', '-define', 'png:exclude-chunks=date,time', '-size', f'{w}x{h}', '-depth', '8', 'rgba:-', path], input=(a * 255 + 0.5).astype(np.uint8).tobytes(), check=True)
if __name__ == '__main__':
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for name, fn in TILES.items():
        write(f'{out}/{name}.png', tile(fn))
    print(len(TILES), 'tiles in', out)
