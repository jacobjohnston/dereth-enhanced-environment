# Ice: retail's crystals keep their shape, and the pack draws their picture as glacier ice. Its normal
# holds a crystal's flat planes, each bending the light through it its own way, and its colour is a
# glacier's blue, each plane a shade of its own, for a client that draws the colour.
# ice.py <pack folder>
import os, re, subprocess, sys
import numpy as np
PACK = sys.argv[1]
PICTURE = '0x05002612'
N = 512
rng = np.random.default_rng(41)
count = 9
seeds = (rng.random((count * count, 2)) + np.stack(np.meshgrid(np.arange(count), np.arange(count)), -1).reshape(-1, 2)) / count
tilt = rng.normal(0, 0.22, (len(seeds), 2))
y, x = np.mgrid[0:N, 0:N] / N
first = np.full((N, N), 9.0)
nx, ny = np.zeros((N, N)), np.zeros((N, N))
for s, t in zip(seeds, tilt):
    d = np.hypot((x - s[0] + 0.5) % 1 - 0.5, ((y - s[1] + 0.5) % 1 - 0.5) * 2.2)
    near = d < first
    first = np.where(near, d, first)
    nx = np.where(near, t[0], nx); ny = np.where(near, t[1], ny)
# Planes that melt into each other, for no hard edge between one patch of light and the next.
f = np.fft.fftfreq(N)
soft = np.exp(-2 * (np.pi * 9) ** 2 * (f[:, None] ** 2 + f[None, :] ** 2))
nx, ny = (np.fft.ifft2(np.fft.fft2(a) * soft).real for a in (nx, ny))
l = np.sqrt(nx * nx + ny * ny + 1)
one = np.ones((N, N))
a = np.dstack([nx / l / 2 + 0.5, ny / l / 2 + 0.5, 1 / l / 2 + 0.5, one])
out = os.path.join(PACK, 'materials'); os.makedirs(out, exist_ok=True)
def write(path, a):
    subprocess.run(['magick', '-define', 'png:exclude-chunks=date,time', '-size', f'{N}x{N}', '-depth', '8', 'rgba:-', path], input=(np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes(), check=True)
write(f'{out}/{PICTURE}_normal.png', a)
# Deep glacier blue, lighter where a plane tips toward the light above and to the left.
shade = 0.86 + 0.5 * (ny - nx) / l
write(f'{out}/{PICTURE}_albedo.png', np.dstack([0.34 * shade, 0.55 * shade, 0.72 * shade, one]))
