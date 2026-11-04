# Writes the pictures of a black, glassy ground: planes of broken volcanic glass, each its own tilt,
# their edges bright and their faces rippled as a glass breaks. obsidian.py <folder>
import os, subprocess, sys
import numpy as np
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
N = 1024
rng = np.random.default_rng(11)
def write(path, a):
    h, w, c = a.shape
    subprocess.run(['magick', '-define', 'png:exclude-chunks=date,time', '-size', f'{w}x{h}', '-depth', '8', 'rgba:-', path], input=(np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes(), check=True)
def blur(a, s):
    fy = np.fft.fftfreq(N)[:, None]; fx = np.fft.rfftfreq(N)[None, :]
    return np.fft.irfft2(np.fft.rfft2(a) * np.exp(-2 * (np.pi * s) ** 2 * (fx * fx + fy * fy)), s=a.shape)
yy, xx = np.mgrid[0:N, 0:N].astype(np.float32) / N
# Broken planes: the nearest of many seeds, wrapping, and how far to the next (the edge).
K = 170
sx, sy = rng.random(K).astype(np.float32), rng.random(K).astype(np.float32)
best = np.full((N, N), 9.0, np.float32); second = best.copy(); who = np.zeros((N, N), np.int32)
w = (blur(rng.standard_normal((N, N)).astype(np.float32), 18), blur(rng.standard_normal((N, N)).astype(np.float32), 18))
wob = 0.012 / (w[0].std() + 1e-6)
xw, yw = xx + w[0] * wob, yy + w[1] * wob
for k in range(K):
    dx = np.abs(xw - sx[k]); dx = np.minimum(dx, 1 - np.abs(dx) % 1)
    dy = np.abs(yw - sy[k]); dy = np.minimum(dy, 1 - np.abs(dy) % 1)
    d = dx * dx + dy * dy
    nearer = d < best
    second = np.where(nearer, best, np.minimum(second, d))
    who = np.where(nearer, k, who); best = np.where(nearer, d, best)
edge = np.sqrt(second) - np.sqrt(best)
tx, ty = rng.uniform(-0.28, 0.28, K).astype(np.float32), rng.uniform(-0.28, 0.28, K).astype(np.float32)
# Curved shell-shaped ripples on each face, centred on its own seed.
r = np.sqrt(best) * 90 + rng.uniform(0, 6, K)[who]
ripple = np.sin(r) * np.exp(-np.sqrt(best) * 9) * 0.08
gx = np.cos(rng.uniform(0, 6.28, K))[who] * ripple
gy = np.sin(rng.uniform(0, 6.28, K))[who] * ripple
fine = blur(rng.standard_normal((N, N)).astype(np.float32), 1.0)
fine = fine / fine.std()
fx_ = (np.roll(fine, -1, 1) - np.roll(fine, 1, 1)) * 0.012
fy_ = (np.roll(fine, -1, 0) - np.roll(fine, 1, 0)) * 0.012
nx, ny = tx[who] + gx + fx_, ty[who] + gy + fy_
# Edges chip: they turn hard away at a plane's rim.
rim = np.clip(1 - edge / 0.006, 0, 1)
nx *= 1 - 0.5 * rim; ny *= 1 - 0.5 * rim
l = np.sqrt(nx * nx + ny * ny + 1)
one = np.ones((N, N), np.float32)
write(f'{OUT}/obsidian_normal.png', np.dstack([nx / l / 2 + 0.5, ny / l / 2 + 0.5, 1 / l / 2 + 0.5, one]))
# Very nearly black, a little cold, with a rare smoky band and chipped rims catching a pale grey.
smoke = blur(rng.standard_normal((N, N)).astype(np.float32), 40); smoke = smoke / smoke.std()
band = np.clip(0.5 + 0.25 * np.sin((xw * 3 + yw * 5 + smoke * 0.2) * 12), 0, 1)
g = 0.012 + 0.012 * band + 0.05 * rim ** 2 + rng.uniform(0, 0.006, K)[who]
write(f'{OUT}/obsidian_albedo.png', np.dstack([g * 0.92, g * 0.95, g * 1.15, one]))
rough = np.clip(0.06 + 0.05 * band + 0.6 * rim ** 2 + 0.03 * np.abs(fine), 0, 1)
write(f'{OUT}/obsidian_roughness.png', np.dstack([rough, rough, rough, one]))
h = np.clip(0.5 + 0.4 * (np.minimum(edge, 0.05) / 0.05 - 0.5) + ripple, 0, 1)
write(f'{OUT}/obsidian_height.png', np.dstack([h, h, h, one]))
