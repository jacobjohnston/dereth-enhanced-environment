# Paints Dereth's two moons as whole spheres, from nothing: for each, a surface picture (colour,
# height in alpha) and a lights picture (what burns on its night side), both laid longitude by
# latitude, longitude 0 the face turned to Dereth, north up. Nothing of retail's pictures goes in;
# their colours and where their notable features sit were read off them by eye.
# moons.py <pack folder> [width]
import os, subprocess, sys
import numpy as np

PACK = sys.argv[1]
W = int(sys.argv[2]) if len(sys.argv) > 2 else 2048
H = W // 2
OUT = os.path.join(PACK, 'sky')
os.makedirs(OUT, exist_ok=True)
DEG = np.pi / 180

lon = (np.arange(W) + 0.5) / W * 2 * np.pi - np.pi
lat = np.pi / 2 - (np.arange(H) + 0.5) / H * np.pi
LON, LAT = np.meshgrid(lon, lat)
# x east, y north, z toward Dereth.
P = np.stack([np.cos(LAT) * np.sin(LON), np.sin(LAT), np.cos(LAT) * np.cos(LON)], -1).astype(np.float32)


def unit_at(lon_deg, lat_deg):
    lo, la = lon_deg * DEG, lat_deg * DEG
    return np.array([np.cos(la) * np.sin(lo), np.sin(la), np.cos(la) * np.cos(lo)], np.float32)


# --- noise ----------------------------------------------------------------------------------
def _hash(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
    h &= 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0x5BD1E995) & 0xFFFFFFFF
    h ^= h >> 15
    h = (h * 0x27D4EB2D) & 0xFFFFFFFF
    h ^= h >> 16
    return h


def _grad(h):
    # Twelve edge directions of a cube, as Perlin's improved noise.
    g = np.array([[1, 1, 0], [-1, 1, 0], [1, -1, 0], [-1, -1, 0], [1, 0, 1], [-1, 0, 1],
                  [1, 0, -1], [-1, 0, -1], [0, 1, 1], [0, -1, 1], [0, 1, -1], [0, -1, -1]], np.float32)
    return g[h % 12]


def noise(p, seed=0):
    """Gradient noise, about -1..1, over points p (..., 3)."""
    f = np.floor(p)
    i = f.astype(np.int64)
    t = p - f
    s = t * t * t * (t * (t * 6 - 15) + 10)
    out = 0
    acc = []
    for dz in (0, 1):
        for dy in (0, 1):
            for dx in (0, 1):
                h = _hash(i[..., 0] + dx, i[..., 1] + dy, i[..., 2] + dz, seed)
                g = _grad(h)
                d = t - np.array([dx, dy, dz], np.float32)
                acc.append((g * d).sum(-1))
    x00 = acc[0] + s[..., 0] * (acc[1] - acc[0])
    x10 = acc[2] + s[..., 0] * (acc[3] - acc[2])
    x01 = acc[4] + s[..., 0] * (acc[5] - acc[4])
    x11 = acc[6] + s[..., 0] * (acc[7] - acc[6])
    y0 = x00 + s[..., 1] * (x10 - x00)
    y1 = x01 + s[..., 1] * (x11 - x01)
    return (y0 + s[..., 2] * (y1 - y0)) * 1.4


def fbm(p, octaves=6, seed=0, gain=0.5, lac=2.03):
    total, amp, norm = 0, 1.0, 0
    for o in range(octaves):
        total = total + amp * noise(p, seed + o * 101)
        norm += amp
        amp *= gain
        p = p * lac
    return total / norm


def ridged(p, octaves=6, seed=0):
    total, amp, norm = 0, 1.0, 0
    for o in range(octaves):
        total = total + amp * (1 - np.abs(noise(p, seed + o * 131)))
        norm += amp
        amp *= 0.5
        p = p * 2.03
    return total / norm


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def ramp(x, stops):
    """Colour along `stops` [(at, (r, g, b)), ...] for x."""
    at = np.array([s[0] for s in stops], np.float32)
    cols = np.array([s[1] for s in stops], np.float32) / 255
    return np.stack([np.interp(x, at, cols[:, c]) for c in range(3)], -1)


def mix(a, b, t):
    t = np.asarray(t, np.float32)
    if t.ndim == a.ndim - 1:
        t = t[..., None]
    return a + (b - a) * t


# --- placing things on the sphere ------------------------------------------------------------
def patch(centre, reach_deg):
    """Rows, columns and points within reach of `centre` (lon, lat in degrees), the columns wrapped."""
    clon, clat = centre
    la0, la1 = max(clat - reach_deg, -90), min(clat + reach_deg, 90)
    r0 = int(np.clip((90 - la1) / 180 * H - 1, 0, H - 1))
    r1 = int(np.clip((90 - la0) / 180 * H + 2, 1, H))
    dlon = 180 if (la1 >= 89 or la0 <= -89) else min(180, reach_deg / max(min(np.cos(la0 * DEG), np.cos(la1 * DEG)), 1e-3))
    c0 = int(np.floor((clon - dlon + 180) / 360 * W)) - 1
    c1 = int(np.ceil((clon + dlon + 180) / 360 * W)) + 2
    if c1 - c0 >= W:
        cols = np.arange(W)
    else:
        cols = np.arange(c0, c1) % W
    rows = np.arange(r0, r1)
    return rows, cols, P[np.ix_(rows, cols)]


def angle(p, q):
    return np.arccos(np.clip((p * q).sum(-1), -1, 1))


def paint_spot(field, centre_lonlat, radius_deg, profile, reach=4):
    """Adds profile(angle / radius) into field (H, W[, C]) about a point, out to `reach` radii."""
    rows, cols, p = patch(centre_lonlat, radius_deg * reach)
    a = angle(p, unit_at(*centre_lonlat)) / (radius_deg * DEG)
    v = profile(a)
    if field.ndim == 3:
        field[np.ix_(rows, cols)] += v
    else:
        field[np.ix_(rows, cols)] += v


def segment_distance(p, a, b):
    """Angle from points p to the great-circle segment a-b, and how far along it, radians."""
    n = np.cross(a, b)
    n /= np.linalg.norm(n)
    off = np.arcsin(np.clip((p * n).sum(-1), -1, 1))
    foot = p - n * (p * n).sum(-1, keepdims=True)
    foot /= np.maximum(np.linalg.norm(foot, axis=-1, keepdims=True), 1e-9)
    inside = ((np.cross(a, foot) * n).sum(-1) >= 0) & ((np.cross(foot, b) * n).sum(-1) >= 0)
    along = angle(foot, a)
    d = np.where(inside, np.abs(off), np.minimum(angle(p, a), angle(p, b)))
    return d, np.where(inside, along, np.where(angle(p, a) < angle(p, b), 0, angle(a, b)))


# --- writing ---------------------------------------------------------------------------------
def to_srgb_bytes(c):
    return (np.clip(np.nan_to_num(c), 0, 1) * 255 + 0.5).astype(np.uint8)


def write(name, rgb, a=None):
    h, w, _ = rgb.shape
    alpha = np.ones((h, w), np.float32) if a is None else a
    data = np.concatenate([to_srgb_bytes(rgb), to_srgb_bytes(alpha)[..., None]], -1)
    path = os.path.join(OUT, name)
    subprocess.run(['magick', '-define', 'png:exclude-chunks=date,time', '-size', f'{w}x{h}', '-depth', '8', 'rgba:-', '-define',
                    'png:compression-level=9', path], input=data.tobytes(), check=True)
    print('wrote', path)


def lamp(core_deg, halo_deg):
    def profile(a):
        core = np.exp(-0.5 * (a / 1.0) ** 2)
        halo = np.exp(-(a * core_deg / halo_deg) ** 2) * 0.35
        return core + halo
    return profile


rng = np.random.default_rng(1729)


def random_points(n, rng):
    v = rng.normal(size=(n, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    return np.degrees(np.arctan2(v[:, 0], v[:, 2])), np.degrees(np.arcsin(v[:, 1]))


# =============================================================================================
# Alb'arel: the pale moon. Olive and gold ground worn into terraces, a great storm over its upper
# face, a city of light in perfect geometry on its western face, and a ring of three circles,
# too true to be a crater, low in the east.
# =============================================================================================
def albarel():
    print("Alb'arel")
    warp = np.stack([fbm(P * 2.1 + 3.1, 4, 11), fbm(P * 2.1 - 7.7, 4, 12), fbm(P * 2.1 + 1.3, 4, 13)], -1)
    q = P + 0.38 * warp
    h = 0.5 + 0.5 * fbm(q * 2.4, 8, 21)
    # Terraces: the ground stands in steps with pale rims, as worn mesas do.
    steps = 7.0
    k = h * steps
    frac = k - np.floor(k)
    terr = 0.45 * (np.floor(k) + smooth(0.0, 0.3, frac)) / steps + 0.55 * h
    rim = np.exp(-((frac - 0.06) / 0.05) ** 2) * smooth(0.35, 0.6, h)
    worn = ridged(q * 7, 5, 27)
    fine = fbm(P * 40, 4, 31)
    grain = fbm(P * 140, 3, 37)
    tint = 0.5 + 0.5 * fbm(P * 1.7 + 9, 4, 41)
    low = ramp(terr + 0.12 * (worn - 0.6), [(0.2, (80, 76, 38)), (0.35, (112, 106, 57)), (0.47, (138, 130, 76)),
                      (0.58, (158, 148, 89)), (0.7, (184, 170, 102)), (0.85, (206, 191, 120))])
    # Some lowlands lean green, some highlands gold.
    green = np.array([0.95, 1.02, 0.94], np.float32)
    gold = np.array([1.04, 1.0, 0.88], np.float32)
    col = low * mix(np.broadcast_to(green, low.shape), np.broadcast_to(gold, low.shape), tint)
    col = mix(col, np.array([0.80, 0.78, 0.62], np.float32), rim * 0.3)
    col *= (1 + 0.08 * fine + 0.05 * grain)[..., None]
    height = terr * 0.7 + 0.08 * worn + 0.05 * fine + 0.02 * grain + 0.03 * rim

    # Craters: few, soft, old; a pair low in the west as retail shows.
    craters = [((-24, -33), 2.2), ((-30, -36), 1.3)]
    los, las = random_points(26, rng)
    craters += [((a, b), r) for a, b, r in zip(los, las, rng.uniform(0.6, 2.4, 26))]
    for c, r in craters:
        bowl = np.zeros((H, W), np.float32)
        paint_spot(bowl, c, r, lambda a: np.where(a < 1, -(1 - a * a), 0) + 0.6 * np.exp(-((a - 1) / 0.18) ** 2))
        height += bowl * 0.08
        col = mix(col, col * 0.72, np.clip(-bowl, 0, 1) * 0.6)
        col = mix(col, np.array([0.78, 0.75, 0.6], np.float32), np.clip(bowl, 0, 1) * 0.5)

    lights = np.zeros((H, W, 3), np.float32)
    teal = np.array([58, 218, 185], np.float32) / 255
    teal_dim = np.array([22, 120, 92], np.float32) / 255

    # The ring: two thick true circles, low in the east, each cut into quarters, the outer's cuts
    # at north, east, south and west, the inner's turned an eighth from them; its floor smooth.
    ring_c = unit_at(17.5, -24.8)
    east = np.cross(np.array([0, 1, 0], np.float32), ring_c)
    east /= np.linalg.norm(east)
    north = np.cross(ring_c, east)
    rows, cols, p = patch((17.5, -24.8), 9)
    a = angle(p, ring_c) / DEG
    clock = np.degrees(np.arctan2((p * east).sum(-1), (p * north).sum(-1)))
    rings = [(6.0, 0.8, 0.0, 4.5), (3.3, 0.65, 45.0, 7.0)]
    band = np.zeros(a.shape, np.float32)
    edge = np.zeros(a.shape, np.float32)
    for rad, w, turn, gap in rings:
        m = np.mod(clock - turn, 90.0)
        cut_off = smooth(gap, gap + 1.5, np.minimum(m, 90.0 - m))
        across = np.abs(a - rad)
        band = np.maximum(band, smooth(w, w * 0.75, across) * cut_off)
        edge = np.maximum(edge, np.exp(-((across - w) / 0.12) ** 2) * cut_off)
    floor = smooth(7.2, 6.4, a)
    sub = col[np.ix_(rows, cols)]
    sub = mix(sub, sub * np.array([0.84, 0.86, 0.82], np.float32), floor * 0.55)
    sub = mix(sub, np.array([0.66, 0.66, 0.58], np.float32), band * 0.85)
    sub = mix(sub, sub * 0.55, edge * 0.8)
    col[np.ix_(rows, cols)] = sub
    hh = height[np.ix_(rows, cols)]
    height[np.ix_(rows, cols)] = mix(hh, np.full_like(hh, 0.42), floor * 0.6) + band * 0.1
    # Lights stand along each quarter at even steps, none in the cuts, and one burns at the middle.
    for rad, w, turn, gap in rings:
        n = 32 if rad > 5 else 16
        for i in range(n):
            th = 360.0 * (i + 0.5) / n
            m = np.mod(th - turn, 90.0)
            if min(m, 90.0 - m) < gap + 2:
                continue
            t = np.radians(th)
            d = np.cos(rad * DEG) * ring_c + np.sin(rad * DEG) * (np.sin(t) * east + np.cos(t) * north)
            lo, la = np.degrees(np.arctan2(d[0], d[2])), np.degrees(np.arcsin(d[1]))
            paint_spot(lights, (lo, la), 0.18, lambda a: lamp(0.18, 0.5)(a)[..., None] * teal_dim * 0.35, 8)
    paint_spot(lights, (17.5, -24.8), 0.3, lambda a: lamp(0.3, 0.9)(a)[..., None] * teal * 0.45, 8)

    # The great city on the western face, where retail shows it: a ring of lights at its hub,
    # six long spokes of small lights out from it, a great crowd of lights between the two spokes
    # running north, a lesser one between the two running south, and a few small crowds about.
    def toward(c, bearing, dist):
        c = unit_at(*c)
        e = np.cross(np.array([0, 1, 0], np.float32), c)
        e /= np.linalg.norm(e)
        n = np.cross(c, e)
        b, d = np.radians(bearing), np.radians(dist)
        v = np.cos(d) * c + np.sin(d) * (np.sin(b) * e + np.cos(b) * n)
        return np.degrees(np.arctan2(v[0], v[2])), np.degrees(np.arcsin(v[1]))

    r = np.random.default_rng(17)
    beads = []  # (lon, lat, size in degrees, brightness)

    def crowd(centre, count, spread, power):
        for _ in range(count):
            b = r.uniform(0, 360)
            d = abs(r.normal(0, spread))
            lo, la = toward(centre, b, d)
            beads.append((lo, la, r.uniform(0.18, 0.28), power * r.uniform(0.4, 1.0)))

    hub = (-55, -16)
    for i in range(12):
        lo, la = toward(hub, 30 * i, 1.3)
        beads.append((lo, la, 0.24, 1.0))
    beads.append((hub[0], hub[1], 0.35, 1.0))
    for bearing, length in [(-28, 24), (28, 24), (92, 16), (152, 17), (208, 17), (268, 16)]:
        # Close-set near the hub, thinning and wandering toward the spoke's end.
        d = 2.2
        while d < length:
            out = d / length
            if r.random() > 0.55 * out:
                lo, la = toward(hub, bearing + r.normal(0, 0.3 + 1.6 * out * out), d)
                beads.append((lo, la, 0.2, (0.95 - 0.45 * out) * r.uniform(0.6, 1.0)))
            d += 0.5 + 1.6 * out * out + r.uniform(0, 0.4 * out)
        crowd(toward(hub, bearing, length), 5, 0.6, 0.8)
    crowd(toward(hub, 0, 16), 70, 2.6, 1.0)
    beads.append((*toward(hub, 0, 16), 0.4, 1.0))
    crowd(toward(hub, 180, 9), 28, 1.4, 0.9)
    for bearing, dist, count in [(60, 11, 10), (122, 10, 8), (240, 12, 9), (300, 13, 10)]:
        crowd(toward(hub, bearing, dist), count, 0.9, 0.7)
    # Lesser crowds about the rest of it, so some light shows whatever its phase.
    for centre, count, spread in [((122, -12), 18, 1.4), ((-128, 22), 20, 1.5), ((168, -30), 14, 1.2),
                                  ((-100, -42), 14, 1.2)]:
        crowd(centre, count, spread, 0.7)
    for lo, la, size, power in beads:
        paint_spot(lights, (lo, la), size, lambda a: lamp(1.0, 2.6)(a)[..., None] * mix(teal_dim * 1.6, teal, power) * power, 7)
        paint_spot(col, (lo, la), size, lambda a: (np.exp(-a * a) * 0.06)[..., None] * np.ones(3, np.float32))

    # The clouds, a layer of their own over the ground: a great mass over the upper western face,
    # drawn out in long streaks along the latitude that bend north toward its eastern end and
    # curl a little there about a weak eye; lesser cloud about the rest of it.
    eye = unit_at(16, 26)
    r_eye = angle(P, eye)
    twirl = 1.9 * np.exp(-(r_eye / (13 * DEG)) ** 2)
    c, s = np.cos(twirl)[..., None], np.sin(twirl)[..., None]
    # Every point turned about the eye by its twirl, so what lies along the streaks curls in.
    Q = P * c + np.cross(eye, P) * s + eye * (P @ eye)[..., None] * (1 - c)
    qlat, qlon = np.degrees(np.arcsin(np.clip(Q[..., 1], -1, 1))), np.degrees(np.arctan2(Q[..., 0], Q[..., 2]))
    lat_b = qlat - 14 * smooth(-10, 30, qlon)
    region = np.exp(-((lat_b - 20) / 19) ** 2) * smooth(-80, -52, qlon) * smooth(42, 22, qlon)
    warp = fbm(Q * 4 + 3.3, 4, 61)
    streaks = 0.5 + 0.5 * fbm(np.stack([qlon * 0.03, lat_b * 0.3, np.zeros_like(qlat)], -1) + 0.35 * warp[..., None], 6, 63)
    mass = 0.5 + 0.5 * fbm(Q * 2.6 + 1.7, 6, 65)
    wisp = 0.5 + 0.5 * fbm(Q * 11, 4, 53)
    main = np.clip(region * (0.65 * smooth(0.22, 0.55, mass) + 0.8 * smooth(0.28, 0.66, streaks)) * (0.75 + 0.4 * wisp) * 1.7 - 0.1, 0, 1)
    # The eye itself kept clear, a little.
    main *= 1 - 0.7 * np.exp(-(r_eye / (1.8 * DEG)) ** 2)
    scatter = np.clip(smooth(0.12, 0.45, fbm(P * 3.2 + 5, 6, 71)) * 0.8, 0, 1)
    cloud = np.clip(np.maximum(main, scatter * (1 - 0.6 * region)), 0, 1)
    # Thick cloud is brighter on top; its thin edges let the light through grey.
    shade = 0.5 + 0.5 * fbm(Q * 18, 4, 73)
    cloud_col = ramp(0.6 * shade + 0.4 * cloud, [(0.2, (168, 170, 160)), (0.55, (222, 222, 212)), (0.9, (246, 245, 238))])
    return col, height, lights, (cloud_col, cloud)


# =============================================================================================
# Rez'arel: the red moon. Rust-orange ground scattered with pale spots from end to end, many of
# them the bright works of whoever lives there; long chains of amber lamps down its western face.
# =============================================================================================
def rezarel():
    print("Rez'arel")
    warp = np.stack([fbm(P * 1.8 + 4.2, 4, 111), fbm(P * 1.8 - 2.9, 4, 112), fbm(P * 1.8 + 8.4, 4, 113)], -1)
    q = P + 0.18 * warp
    base = 0.5 + 0.5 * fbm(q * 3.0, 8, 121)
    maria = smooth(0.45, 0.2, 0.5 + 0.5 * fbm(q * 1.2 + 3, 5, 131))
    fine = fbm(P * 48, 4, 141)
    grain = fbm(P * 160, 3, 147)
    col = ramp(base, [(0.2, (140, 76, 56)), (0.4, (180, 104, 72)), (0.55, (207, 123, 82)),
                      (0.7, (232, 144, 94)), (0.85, (246, 168, 112))])
    col = mix(col, col * np.array([0.68, 0.6, 0.58], np.float32), maria * 0.75)
    col *= (1 + 0.1 * fine + 0.06 * grain)[..., None]
    height = 0.45 + 0.25 * (base - 0.5) - 0.08 * maria + 0.05 * fine + 0.02 * grain
    lights = np.zeros((H, W, 3), np.float32)
    cream = np.array([255, 236, 196], np.float32) / 255
    peach = np.array([255, 196, 140], np.float32) / 255
    warm = np.array([255, 222, 168], np.float32) / 255
    amber = np.array([255, 158, 86], np.float32) / 255

    # Pale spots end to end: craters' bright floors and rays, and among them the moon's works.
    n = 3200
    los, las = random_points(n, rng)
    sizes = 0.34 * (1 - rng.random(n)) ** -0.55
    sizes = np.minimum(sizes, 3.2)
    power = rng.uniform(0.45, 1.0, n)
    works = rng.random(n) < 0.1
    # A crowded bright field low in the east, as retail shows.
    k = 160
    clo = 40 + rng.normal(0, 7, k)
    cla = -24 + rng.normal(0, 6, k)
    los = np.concatenate([los, clo])
    las = np.concatenate([las, cla])
    sizes = np.concatenate([sizes, 0.2 * (1 - rng.random(k)) ** -0.5])
    power = np.concatenate([power, rng.uniform(0.5, 1.0, k)])
    works = np.concatenate([works, rng.random(k) < 0.25])
    spot_l = np.zeros((H, W), np.float32)
    halo_l = np.zeros((H, W), np.float32)
    for lo, la, r, pw, wk in zip(los, las, np.minimum(sizes, 3.2), power, works):
        rows, cols, p = patch((lo, la), r * 4.5)
        a = angle(p, unit_at(lo, la)) / (r * DEG)
        core = np.exp(-(a / 0.5) ** 2) * pw
        halo = np.exp(-a / 1.2) * 0.5 * pw
        spot_l[np.ix_(rows, cols)] = np.maximum(spot_l[np.ix_(rows, cols)], core)
        halo_l[np.ix_(rows, cols)] += halo
        if r > 0.5:
            height[np.ix_(rows, cols)] += 0.05 * (np.where(a < 1, -(1 - a * a), 0) + 0.5 * np.exp(-((a - 1) / 0.25) ** 2)) * min(r, 1.5)
        if wk:
            # A work: a tight cluster of small lights at the spot's heart.
            sub = np.exp(-(a / 0.12) ** 2) + 0.1 * np.exp(-(a / 0.35) ** 2)
            lights[np.ix_(rows, cols)] += sub[..., None] * warm * pw * 0.45
    col = mix(col, peach, np.clip(halo_l, 0, 0.7))
    col = mix(col, cream, np.clip(spot_l, 0, 1))
    height += 0.03 * spot_l

    # Chains of lamps down the western face, where retail shows them, and others about the moon.
    def chain(lon0, lat0, lat1, step, jitter, seed, colour=amber, power=1.0):
        r = np.random.default_rng(seed)
        la = lat0
        while la <= lat1:
            lo = lon0 + r.normal(0, jitter)
            at = (lo, la + r.normal(0, jitter * 0.5))
            paint_spot(lights, at, 0.2, lambda a: lamp(0.2, 0.45)(a)[..., None] * colour * power, 7)
            paint_spot(col, at, 0.2, lambda a: (np.exp(-(a / 1.0) ** 2) * 0.12)[..., None] * peach)
            la += step
    chain(-40, -46, 46, 9.0, 1.0, 201)
    chain(-62, -40, 42, 10.0, 1.2, 202)
    chain(-75, -18, 20, 12.0, 1.0, 203, np.array([140, 230, 200], np.float32) / 255, 0.6)
    chain(62, -30, 34, 9.5, 1.0, 204)
    chain(118, -44, 40, 10.5, 1.2, 205)
    chain(-118, -36, 44, 9.0, 1.0, 206)
    chain(178, -40, 30, 11.0, 1.0, 207)
    return col, height, lights


def main():
    # How bright each moon's lights are drawn, at their brightest.
    burn = {'albarel': 0.3, 'rezarel': 0.4}
    for name, make in [('albarel', albarel), ('rezarel', rezarel)]:
        col, height, lights, *clouds = make()
        write(f'{name}_surface.png', col, np.clip(height, 0, 1))
        for cloud_col, cloud in clouds:
            write(f'{name}_clouds.png', cloud_col, cloud)
        peak = np.percentile(lights.max(-1), 99.995)
        write(f'{name}_lights.png', (np.clip(lights / max(peak, 1e-6), 0, 1) * burn[name]) ** (1 / 2.2))


if __name__ == '__main__':
    main()
