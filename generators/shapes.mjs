// Shapes EZ-Tree cannot grow, and the pictures they are drawn with, all made from code. Each maker
// takes a size, a level of detail and a random source, and returns parts: { name, look, opaque, mesh }.
import zlib from 'node:zlib';

const TAU = Math.PI * 2;
const add = (a, b, s = 1) => [a[0] + b[0] * s, a[1] + b[1] * s, a[2] + b[2] * s];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const unit = (a) => {
  const l = Math.hypot(...a) || 1;
  return [a[0] / l, a[1] / l, a[2] / l];
};

export function seeded(seed) {
  let rng = seed >>> 0 || 1;
  return () => {
    rng ^= rng << 13;
    rng ^= rng >>> 17;
    rng ^= rng << 5;
    rng >>>= 0;
    return rng / 2 ** 32;
  };
}

const newMesh = () => ({ position: [], normal: [], uv: [], index: [] });

// A tube through `points`, its radius `radius(t)`, its picture running on along it. `rib` and `ribs`
// flute its sides; `facet` gives each side a flat face.
function sweep(mesh, points, radius, sides, { rib = 0, ribs = 0, wraps = 1, perMeter = 1 / 3.4, facet = false } = {}) {
  const n = points.length;
  const tangent = (k) => unit(add(points[Math.min(k + 1, n - 1)], points[Math.max(k - 1, 0)], -1));
  let t0 = tangent(0);
  let e = unit(cross(t0, Math.abs(t0[1]) > 0.9 ? [1, 0, 0] : [0, 1, 0]));
  const rings = [];
  let v = 0;
  for (let k = 0; k < n; k++) {
    const t = tangent(k);
    e = unit(add(e, t, -dot(e, t)));
    const f = cross(t, e);
    if (k > 0) v += Math.hypot(...add(points[k], points[k - 1], -1)) * perMeter;
    const r = radius(k / (n - 1));
    const ring = [];
    for (let j = 0; j <= sides; j++) {
      const a = (j / sides) * TAU;
      const d = [0, 1, 2].map((c) => Math.cos(a) * e[c] + Math.sin(a) * f[c]);
      ring.push({ p: add(points[k], d, r * (1 + rib * Math.cos(ribs * a))), n: d, u: (j / sides) * wraps, v });
    }
    rings.push(ring);
    t0 = t;
  }
  for (let k = 0; k + 1 < n; k++) {
    for (let j = 0; j < sides; j++) {
      const cell = [rings[k][j], rings[k + 1][j], rings[k][j + 1], rings[k + 1][j + 1]];
      if (facet) {
        const fn = unit(cross(add(cell[2].p, cell[0].p, -1), add(cell[1].p, cell[0].p, -1)));
        const base = mesh.position.length / 3;
        for (const c of cell) {
          mesh.position.push(...c.p);
          mesh.normal.push(...fn);
          mesh.uv.push(c.u, c.v);
        }
        mesh.index.push(base, base + 2, base + 1, base + 2, base + 3, base + 1);
      }
    }
  }
  if (facet) return;
  const base = mesh.position.length / 3;
  for (const ring of rings) {
    for (const c of ring) {
      mesh.position.push(...c.p);
      mesh.normal.push(...c.n);
      mesh.uv.push(c.u, c.v);
    }
  }
  const row = sides + 1;
  for (let k = 0; k + 1 < n; k++) {
    for (let j = 0; j < sides; j++) {
      const p = base + k * row + j;
      mesh.index.push(p, p + 1, p + row, p + 1, p + row + 1, p + row);
    }
  }
}

// A surface turned about the height axis: `profile` is [radius, height] pairs, `wobble(a)` scales the
// radius round it, and `uv(r, a, y)` places the picture.
function lathe(mesh, profile, sides, wobble, uv) {
  const base = mesh.position.length / 3;
  const n = profile.length;
  for (let k = 0; k < n; k++) {
    const [r, y] = profile[k];
    const before = profile[Math.max(k - 1, 0)];
    const after = profile[Math.min(k + 1, n - 1)];
    const nr = after[1] - before[1];
    const ny = before[0] - after[0];
    const l = Math.hypot(nr, ny) || 1;
    for (let j = 0; j <= sides; j++) {
      const a = (j / sides) * TAU;
      const rr = r * wobble(a);
      mesh.position.push(Math.cos(a) * rr, y, Math.sin(a) * rr);
      mesh.normal.push((Math.cos(a) * nr) / l, ny / l, (Math.sin(a) * nr) / l);
      mesh.uv.push(...uv(rr, a, y));
    }
  }
  const row = sides + 1;
  for (let k = 0; k + 1 < n; k++) {
    for (let j = 0; j < sides; j++) {
      const p = base + k * row + j;
      mesh.index.push(p, p + row, p + 1, p + 1, p + row, p + row + 1);
    }
  }
}

// A leaf or petal along `spine`, its stalk end first, `width(t)` across and folded a little along
// its middle, drawn with the picture's `region` foot to tip. `up` is the way its face looks.
function ribbon(mesh, spine, width, region, up, fold = 0.12) {
  const n = spine.length;
  const base = mesh.position.length / 3;
  for (let k = 0; k < n; k++) {
    const t = k / (n - 1);
    const along = unit(add(spine[Math.min(k + 1, n - 1)], spine[Math.max(k - 1, 0)], -1));
    const side = unit(cross(along, up));
    const face = unit(cross(side, along));
    const w = width(t);
    const v = region.y1 + (region.y0 - region.y1) * t;
    for (const s of [-1, 0, 1]) {
      const p = add(add(spine[k], side, s * w * 0.5), face, s === 0 ? -w * fold : 0);
      mesh.position.push(...p);
      mesh.normal.push(...unit(add(face, side, s * 0.35)));
      mesh.uv.push(region.x0 + ((s + 1) / 2) * (region.x1 - region.x0), v);
    }
  }
  for (let k = 0; k + 1 < n; k++) {
    for (const j of [0, 1]) {
      const p = base + k * 3 + j;
      mesh.index.push(p, p + 1, p + 3, p + 1, p + 4, p + 3);
    }
  }
}

// A pair of leaf cards at `at`, crossed and tilted so they face the sky.
export function cards(mesh, at, size, random) {
  const yaw = random() * Math.PI * 2;
  for (const q of [0, Math.PI / 2]) {
    const tilt = 0.25 + random() * 0.85;
    const a = yaw + q;
    const w = [Math.cos(a), 0, Math.sin(a)];
    const h = [Math.sin(a) * Math.cos(tilt), Math.sin(tilt), -Math.cos(a) * Math.cos(tilt)];
    const n = unit(add(cross(w, h), [0, 1, 0], 0.5));
    const base = mesh.position.length / 3;
    for (const [u, v] of [[0, 1], [1, 1], [1, 0], [0, 0]]) {
      mesh.position.push(...add(add(at, w, (u - 0.5) * size), h, (0.5 - v) * size));
      mesh.normal.push(...n);
      mesh.uv.push(u, v);
    }
    mesh.index.push(base, base + 1, base + 2, base, base + 2, base + 3);
  }
}

// A crossed pair of leaf cards at `at`, each tilted between `lo` and `hi` radians from level: near 0
// they lie flat, below 0 they hang from `at` toward the ground.
function tilted(mesh, at, size, random, lo, hi) {
  const yaw = random() * Math.PI * 2;
  for (const q of [0, Math.PI / 2]) {
    const tilt = lo + random() * (hi - lo);
    const a = yaw + q;
    const w = [Math.cos(a), 0, Math.sin(a)];
    const h = [Math.sin(a) * Math.cos(tilt), Math.sin(tilt), -Math.cos(a) * Math.cos(tilt)];
    const n = unit(add(cross(w, h), [0, 1, 0], 0.5));
    // A hanging card hangs from its top edge; a flat one lies about its middle.
    const from = tilt < 0 ? add(at, h, size * 0.5) : at;
    const base = mesh.position.length / 3;
    for (const [u, v] of [[0, 1], [1, 1], [1, 0], [0, 0]]) {
      mesh.position.push(...add(add(from, w, (u - 0.5) * size), h, (0.5 - v) * size));
      mesh.normal.push(...n);
      mesh.uv.push(u, v);
    }
    mesh.index.push(base, base + 1, base + 2, base, base + 2, base + 3);
  }
}

const atlas = (x, y, w, h) => ({ x0: x / 2048, y0: y / 2048, x1: (x + w) / 2048, y1: (y + h) / 2048 });
const FERN = atlas(30, 930, 561, 1091);
const LONG = atlas(107, 95, 268, 785);
const WHOLE = { x0: 0, y0: 0, x1: 1, y1: 1 };

const leaves = (tint) => ({ color: 'Plant_Leaves.png', tint, cutoff: 0.25 });
const generated = (color, tint, extra = {}) => ({ color, tint, normal: 'Gen_Grit_Normal.png', ...extra });
const BARK = { color: 'Conifer_Bark.png', normal: 'Conifer_Bark_Normal.png', tint: [0.3, 0.25, 0.2, 1] };

// A leaf or frond arching out from `from` toward `a`, rising at `rise` and falling away by `droop`.
function arch(from, a, long, rise, droop, rows) {
  const out = [];
  for (let k = 0; k <= rows; k++) {
    const t = k / rows;
    out.push([
      from[0] + Math.cos(a) * long * t * (1 - 0.15 * t * droop),
      from[1] + long * (rise * t - droop * t * t),
      from[2] + Math.sin(a) * long * t * (1 - 0.15 * t * droop),
    ]);
  }
  return out;
}

export function palm({ across, tall, trunk, fronds = 15, lean = 0.1, bark = [1, 1, 1, 1], fan = false, leaf = [0.62, 0.8, 0.4, 1], pruned = false }, lod, random) {
  const wood = newMesh();
  const crown = newMesh();
  const a0 = random() * TAU;
  const top = tall - across * 0.16;
  const points = [];
  const rings = Math.max(3, Math.round(9 * lod.seg));
  for (let k = 0; k <= rings; k++) {
    const t = k / rings;
    const off = across * lean * t * t;
    points.push([Math.cos(a0) * off, -0.8 + (top + 0.8) * t, Math.sin(a0) * off]);
  }
  sweep(wood, points, (t) => trunk * (0.62 + 0.38 * (1 - t) + 0.7 * (1 - t) ** 8), Math.max(5, Math.round(12 * lod.seg)), { wraps: 2, perMeter: 0.5 });
  foot(wood, trunk, lod.seg, a0);
  const head = points[points.length - 1];
  const count = Math.max(4, Math.round(fronds * lod.keep));
  const rows = Math.max(3, Math.round(9 * lod.seg));
  for (let i = 0; i < count; i++) {
    const a = ((i + random() * 0.6) / count) * TAU;
    const long = (across / 2) * (0.92 + random() * 0.14);
    const rise = 0.15 + ((i * 7) % count) / count * 0.75;
    if (fan) {
      ribbon(crown, arch(head, a, long, 0.1 + rise * 0.3, 0.45, rows), () => long * 0.44 * lod.grow ** 0.5, LONG, [0, 1, 0]);
    } else {
      ribbon(crown, arch(head, a, long, rise, 0.9, rows), (t) => long * 0.5 * lod.grow ** 0.5 * (0.8 + 0.2 * t), FERN, [0, 1, 0]);
    }
  }
  return [
    { name: 'Trunk', look: generated(pruned ? 'Gen_PalmPruned.png' : 'Gen_PalmBark.png', bark), opaque: true, mesh: wood },
    { name: 'Fronds', look: leaves(leaf), mesh: crown },
  ];
}

export function jungle({ across, tall, blades = 11, wide = 0.42, stem = 0.28, rise: lift = 0.28, droop = 0.62, leaf = [0.3, 0.62, 0.24, 1] }, lod, random) {
  const wood = newMesh();
  const crown = newMesh();
  const head = [(random() - 0.5) * stem, tall * lift, (random() - 0.5) * stem];
  sweep(wood, [[0, -0.6, 0], [head[0] * 0.3, tall * 0.1, head[2] * 0.3], head], (t) => stem * (1.5 - t), Math.max(4, Math.round(8 * lod.seg)));
  foot(wood, stem, lod.seg, 1);
  const count = Math.max(3, Math.round(blades * lod.keep));
  const rows = Math.max(3, Math.round(8 * lod.seg));
  for (let i = 0; i < count; i++) {
    const a = ((i + random() * 0.7) / count) * TAU;
    const long = (across / 2) * (0.85 + random() * 0.2);
    // A parabola through the plant's height that falls to `droop` of the head's height at its tip.
    const high = (tall - head[1]) * (0.5 + random() * 0.3);
    const end = -head[1] * droop * (0.6 + random() * 0.4);
    const r = ((2 * high) / long) * (1 + Math.sqrt(1 - end / high));
    const d = r - end / long;
    const spine = Array.from({ length: rows + 1 }, (_, k) => {
      const t = k / rows;
      return [head[0] + Math.cos(a) * long * t, head[1] + long * (r * t - d * t * t), head[2] + Math.sin(a) * long * t];
    });
    ribbon(crown, spine, () => long * wide * 1.4 * lod.grow ** 0.5, WHOLE, [0, 1, 0]);
  }
  return [
    { name: 'Stem', look: BARK, opaque: true, mesh: wood },
    { name: 'Leaves', look: { color: 'Gen_Mottled.png', tint: leaf, cutoff: 0.4 }, mesh: crown },
  ];
}

// A squat, tapering trunk ringed with the scales of old leaf bases, under a crown of arching fronds
// that fall nearly to the ground.
export function cycad({ across, tall, trunk, crest, bark = [0.4, 0.15, 0.08, 1], leaf = [0.7, 0.95, 0.45, 1], fronds = 11 }, lod, random) {
  const wood = newMesh();
  const crown = newMesh();
  const seed = random() * TAU;
  // Each scale ring flares out at its foot and tucks in under the next; the crest rounds over the top.
  const bands = Math.max(3, Math.round(9 * lod.seg));
  const girth = (y) => trunk * (1 - 0.3 * Math.max(0, y) / crest + 0.08 * Math.sin((Math.max(0, y) / crest) * Math.PI));
  const profile = [[0.01, -0.5], [trunk * 1.05, -0.45]];
  for (let k = 0; k < bands; k++) {
    const y0 = (crest * k) / bands;
    const y1 = (crest * (k + 1)) / bands;
    profile.push([girth(y0) * (lod.seg > 0.5 ? 1.08 : 1), y0], [girth(y1) * 0.94, y1 - (y1 - y0) * 0.12]);
  }
  const head = tall * 0.8;
  profile.push([girth(crest) * 0.7, crest + (head - crest) * 0.5], [0.01, head]);
  const lobes = (a) => 1 + 0.05 * Math.cos(4 * a + seed) + 0.03 * Math.cos(7 * a + seed * 2);
  lathe(wood, profile, Math.max(6, Math.round(14 * lod.seg)), lobes, (r, a, y) => [(a / TAU) * 3, y * 0.9]);
  const count = Math.max(4, Math.round(fronds * lod.keep));
  const rows = Math.max(3, Math.round(9 * lod.seg));
  for (let i = 0; i < count; i++) {
    const a = ((i + random() * 0.6) / count) * TAU;
    // Older fronds arch out and fall to the ground's edge; the young ones stand higher and shorter.
    const young = ((i * 5) % count) / count;
    const droop = 1.2 - young * 0.4;
    const long = ((across / 2) * (0.88 + random() * 0.14) * (1 - young * 0.25)) / (1 - 0.15 * droop);
    const rise = droop - (head - tall * 0.3 * (1 + young)) / long;
    const from = [Math.cos(a) * trunk * 0.15, head - 0.05, Math.sin(a) * trunk * 0.15];
    ribbon(crown, arch(from, a, long, rise, droop, rows), (t) => long * 0.42 * lod.grow ** 0.5 * (0.75 + 0.25 * Math.sin(Math.PI * t)), FERN, [0, 1, 0]);
  }
  return [
    { name: 'Trunk', look: generated('Gen_PalmBark.png', bark), opaque: true, mesh: wood },
    { name: 'Fronds', look: leaves(leaf), mesh: crown },
  ];
}

export function mushroom({ across, tall, stem, depth, cap, flesh }, lod) {
  const stalk = newMesh();
  const top = newMesh();
  const under = newMesh();
  const R = across / 2;
  const rim = tall - depth * 0.72;
  const sides = Math.max(8, Math.round(28 * lod.seg));
  const rows = Math.max(3, Math.round(9 * lod.seg));
  const wobble = (a) => 1 + 0.05 * Math.sin(3 * a + 1) + 0.055 * Math.abs(Math.sin(4 * a + 2));
  const points = [];
  for (let k = 0; k <= 5; k++) points.push([0, -0.8 + (rim + depth * 0.3 + 0.8) * (k / 5), 0]);
  sweep(stalk, points, (t) => stem * (0.82 + 0.75 * (1 - t) ** 4), Math.max(6, Math.round(14 * lod.seg)), { wraps: 2, perMeter: 0.25 });
  const profile = [[R * 0.9, rim - depth * 0.1]];
  for (let k = 0; k <= rows; k++) {
    const a = (k / rows) * (Math.PI / 2);
    profile.push([R * Math.cos(a) ** 0.6, rim + depth * 0.72 * Math.sin(a) ** 1.1]);
  }
  profile[profile.length - 1][0] = 0.001;
  const planar = (r, a) => [0.5 + (0.48 * (r / R) * Math.cos(a)), 0.5 + (0.48 * (r / R) * Math.sin(a))];
  lathe(top, profile, sides, wobble, planar);
  lathe(under, [[stem * 0.7, rim + depth * 0.32], [R * 0.5, rim + depth * 0.12], [R * 0.9, rim - depth * 0.1]], sides, wobble, planar);
  return [
    { name: 'Stem', look: generated('Gen_Stem.png', flesh), opaque: true, mesh: stalk },
    { name: 'Cap', look: generated('Gen_Cap.png', cap), opaque: true, mesh: top },
    { name: 'Gills', look: generated('Gen_Gills.png', flesh), opaque: true, mesh: under },
  ];
}

export function cactus({ across, tall, radius, arms }, lod, random) {
  const skin = newMesh();
  const sides = Math.max(6, Math.round(24 * lod.seg));
  const options = { rib: lod.seg > 0.5 ? 0.075 : 0, ribs: 10, wraps: 5, perMeter: 0.5 };
  const round = (r) => (t) => r * Math.min(1, Math.sqrt(Math.max(0.02, (1 - t) / 0.12)));
  const rows = Math.max(4, Math.round(10 * lod.seg));
  const body = [];
  for (let k = 0; k <= rows; k++) body.push([0, -0.8 + (tall + 0.8) * (k / rows), 0]);
  sweep(skin, body, round(radius), sides, options);
  const a0 = random() * TAU;
  const armPaths = [];
  for (let k = 0; k < arms; k++) {
    const a = a0 + (k / arms) * TAU;
    const y = tall * (0.38 + 0.14 * k);
    const out = across / 2 - radius * 0.7;
    const up = tall * (0.3 - 0.04 * k);
    const at = (r, h) => [Math.cos(a) * r, h, Math.sin(a) * r];
    const path = [at(0, y), at(out * 0.45, y + 0.02), at(out * 0.8, y + radius * 0.25), at(out, y + radius * 0.9), at(out, y + up * 0.55), at(out, y + up * 0.85), at(out, y + up)];
    sweep(skin, path, round(radius * 0.62), Math.max(6, Math.round(16 * lod.seg)), options);
    armPaths.push([path, radius * 0.62]);
  }
  const thorns = newMesh();
  if (lod.seg > 0.5) {
    const every = lod.seg > 0.9 ? 0.3 : 0.62;
    const ribsOn = lod.seg > 0.9 ? 10 : 5;
    spinesOn(thorns, body, radius, every, ribsOn, random);
    for (const [path, r] of armPaths) spinesOn(thorns, path, r, every, ribsOn, random);
  }
  return [
    { name: 'Skin', look: generated('Gen_Cactus.png', [1, 1, 1, 1]), opaque: true, mesh: skin },
    { name: 'Spines', look: generated('Gen_Stem.png', [0.86, 0.8, 0.48, 1]), opaque: true, mesh: thorns },
  ];
}

// Short sharp spines along the ribs of the tube through `path`, every `every` meters.
function spinesOn(mesh, path, radius, every, ribs, random) {
  for (let k = 0; k + 1 < path.length; k++) {
    const d = add(path[k + 1], path[k], -1);
    const long = Math.hypot(...d);
    const t = unit(d);
    const e = unit(cross(t, Math.abs(t[1]) > 0.9 ? [1, 0, 0] : [0, 1, 0]));
    const f = cross(t, e);
    const count = Math.max(1, Math.floor(long / every));
    for (let n = 0; n < count; n++) {
      const at = add(path[k], t, ((n + 0.5) * long) / count);
      if (at[1] < 0) continue;
      for (let r = 0; r < ribs; r++) {
        const a = ((r + (n % 2) * 0.5) / ribs) * TAU;
        const out = [0, 1, 2].map((c) => Math.cos(a) * e[c] + Math.sin(a) * f[c]);
        const from = add(at, out, radius * 1.03);
        const point = unit(add(add(out, t, 0.35), [random() - 0.5, random() - 0.5, random() - 0.5], 0.25));
        sweep(mesh, [from, add(from, point, Math.max(0.1, radius * 0.34))], (q) => Math.max(0.012, radius * 0.035) * (1 - q) + 0.001, 3);
      }
    }
  }
}

export function reed({ across, tall, blades = 5 }, lod, random) {
  const crown = newMesh();
  const count = Math.max(2, Math.round(blades * Math.max(lod.keep, 0.5)));
  const rows = Math.max(3, Math.round(8 * lod.seg));
  for (let i = 0; i < count; i++) {
    const a = ((i + random() * 0.5) / count) * TAU;
    const long = (across / 2) * (0.7 + random() * 0.35);
    const high = tall * (0.75 + random() * 0.25);
    const spine = [];
    for (let k = 0; k <= rows; k++) {
      const t = k / rows;
      spine.push([Math.cos(a) * long * t * t, -0.4 + (high + 0.4) * (t - 0.06 * t * t), Math.sin(a) * long * t * t]);
    }
    ribbon(crown, spine, () => across * 0.16 * lod.grow ** 0.5, LONG, [Math.cos(a), 0.1, Math.sin(a)]);
  }
  return [{ name: 'Leaves', look: leaves([0.42, 0.68, 0.36, 1]), mesh: crown }];
}

export function flower({ across, tall, picture }, lod, random) {
  const wood = newMesh();
  const crown = newMesh();
  const a0 = random() * TAU;
  const head = [Math.cos(a0) * across * 0.1, tall * 0.84, Math.sin(a0) * across * 0.1];
  const points = [];
  const rows = Math.max(3, Math.round(8 * lod.seg));
  for (let k = 0; k <= rows; k++) {
    const t = k / rows;
    points.push([head[0] * t * t, -0.5 + (head[1] + 0.5) * t, head[2] * t * t]);
  }
  sweep(wood, points, (t) => across * 0.032 * (1.5 - t * 0.7), Math.max(4, Math.round(7 * lod.seg)), { wraps: 1 });
  const petalsMesh = newMesh();
  const count = lod.seg > 0.5 ? 8 : 5;
  for (let i = 0; i < count; i++) {
    const a = (i / count) * TAU;
    const long = across / 2;
    ribbon(petalsMesh, arch(head, a, long, 0.62, 0.32, Math.max(3, rows - 2)), () => long * 0.5, WHOLE, [0, 1, 0], 0.1);
  }
  for (let i = 0; i < 2; i++) {
    const a = a0 + Math.PI * i + 1;
    ribbon(crown, arch(points[Math.round(rows * 0.3)], a, across * 0.45, 1.1, 0.85, rows), () => across * 0.13, LONG, [0, 1, 0]);
  }
  const heart = newMesh();
  const hr = across * 0.07;
  lathe(heart, [[hr, -hr * 0.4], [hr * 0.8, hr * 0.5], [0.01, hr]], 8, () => 1, (r, a, y) => [a / TAU, y]);
  for (let i = 0; i < heart.position.length; i += 3) {
    heart.position[i] += head[0];
    heart.position[i + 1] += head[1];
    heart.position[i + 2] += head[2];
  }
  return [
    { name: 'Heart', look: generated('Gen_Stem.png', [1, 0.8, 0.16, 1]), opaque: true, mesh: heart },
    { name: 'Stalk', look: generated('Gen_Stem.png', [0.2, 0.5, 0.16, 1]), opaque: true, mesh: wood },
    { name: 'Petals', look: { color: picture, tint: [1, 1, 1, 1], cutoff: 0.4 }, mesh: petalsMesh },
    { name: 'Leaves', look: leaves([0.4, 0.66, 0.34, 1]), mesh: crown },
  ];
}

// A tree of faceted ice: a leaning spike on a broken foot, with prongs and a few icicles.
export function crystal({ across, tall, prongs = 4 }, lod, random) {
  const ice = newMesh();
  const look = generated('Gen_Ice.png', [0.3, 0.62, 1, 1], { rough: 0.18 });
  const sides = lod.seg > 0.5 ? 6 : 4;
  const a0 = random() * TAU;
  const lean = across * 0.26;
  const main = [];
  for (let k = 0; k <= 4; k++) {
    const t = k / 4;
    main.push([Math.cos(a0) * lean * t + (k % 2 ? 0.15 : -0.1), -0.6 + (tall + 0.6) * t, Math.sin(a0) * lean * t]);
  }
  const girth = Math.max(across * 0.1, tall * 0.045);
  sweep(ice, main, (t) => girth * (1.15 - t) ** 1.2 + 0.01, sides, { facet: true, perMeter: 0.14 });
  for (let k = 0; k < prongs; k++) {
    const a = a0 + (k / prongs) * TAU + random();
    const from = main[1 + (k % 2)];
    const long = (across / 2) * (0.75 + random() * 0.3);
    const rise = tall * (0.16 + random() * 0.28);
    const end = [from[0] + Math.cos(a) * long, from[1] + rise, from[2] + Math.sin(a) * long];
    const mid = [(from[0] + end[0]) / 2, from[1] + rise * 0.35, (from[2] + end[2]) / 2];
    sweep(ice, [from, mid, end], (t) => girth * 0.8 * (1 - t) ** 1.1 + 0.01, Math.max(4, sides - 1), { facet: true, perMeter: 0.14 });
    if (lod.seg > 0.5) {
      for (let c = 0; c < 3; c++) {
        const s = 0.35 + 0.2 * c;
        const top = [from[0] + (end[0] - from[0]) * s, from[1] + rise * s * 0.7, from[2] + (end[2] - from[2]) * s];
        sweep(ice, [top, [top[0], top[1] - tall * (0.05 + random() * 0.08), top[2]]], (t) => girth * 0.13 * (1 - t) + 0.005, 3, { facet: true, perMeter: 0.14 });
      }
    }
  }
  const base = newMesh();
  lathe(base, [[across * 0.2, -0.6], [across * 0.17, tall * 0.05], [across * 0.08, tall * 0.11], [0.01, tall * 0.13]], sides + 1, (a) => 0.8 + 0.3 * Math.sin(a * 3 + a0), (r, a, y) => [a / TAU, y * 0.14]);
  return [
    { name: 'Ice', look, opaque: true, mesh: ice },
    { name: 'Foot', look: generated('Gen_Ice.png', [0.82, 0.92, 1, 1], { rough: 0.3 }), opaque: true, mesh: base },
  ];
}

// A great coral: thick arms forking into broad spotted paddles.
export function coral({ across, tall, tint }, lod, random) {
  const body = newMesh();
  const crown = newMesh();
  const sides = Math.max(4, Math.round(10 * lod.seg));
  const rows = Math.max(3, Math.round(6 * lod.seg));
  const paddles = Math.max(1, Math.round(4 * lod.keep));
  const grow = (from, dir, long, radius, level) => {
    const bend = unit(add(dir, [(random() - 0.5) * 0.5, 0.15, (random() - 0.5) * 0.5]));
    const mid = add(from, dir, long * 0.5);
    const end = add(mid, bend, long * 0.5);
    sweep(body, [from, mid, end], (t) => radius * (1 - t * 0.3), sides, { wraps: 2, perMeter: 0.3 });
    if (level === 0) {
      for (let k = 0; k < paddles; k++) {
        const a = (k / paddles) * TAU + random();
        const size = across * 0.26 * (0.75 + random() * 0.45);
        ribbon(crown, arch(end, a, size, 1.7 + random() * 0.9, 0.4, rows), () => size * 0.5 * lod.grow ** 0.5, WHOLE, [Math.cos(a) * 0.4, 0.8, Math.sin(a) * 0.4], 0.06);
      }
      return;
    }
    const forks = level === 2 ? 4 : 3;
    for (let k = 0; k < forks; k++) {
      const a = (k / forks) * TAU + random();
      const next = unit(add(bend, [Math.cos(a), 0.3, Math.sin(a)], 0.42));
      grow(end, next, long * 0.72, radius * 0.62, level - 1);
    }
  };
  grow([0, -1, 0], [0, 1, 0], tall * 0.32, across * 0.055, 2);
  foot(body, across * 0.055, lod.seg, 4);
  return [
    { name: 'Coral', look: generated('Gen_Coral.png', tint, { rough: 0.55 }), opaque: true, mesh: body },
    { name: 'Paddles', look: { color: 'Gen_Paddle.png', tint, cutoff: 0.4, rough: 0.55 }, mesh: crown },
  ];
}

// Pictures, each worked out from nothing, so the pack needs no file for them.
export const SIZE = 512;

export function noiseOf(seed) {
  const random = seeded(seed);
  const cells = 32;
  const grid = Float32Array.from({ length: cells * cells }, () => random());
  const smooth = (t) => t * t * (3 - 2 * t);
  const once = (u, v, f) => {
    const x = (((u * f) % f) + f) % f;
    const y = (((v * f) % f) + f) % f;
    const xi = Math.floor(x);
    const yi = Math.floor(y);
    const at = (i, j) => grid[((j % f) * Math.floor(cells / f) + (i % f) * cells * Math.floor(cells / f)) % grid.length];
    const fx = smooth(x - xi);
    const fy = smooth(y - yi);
    const a = at(xi, yi) + (at(xi + 1, yi) - at(xi, yi)) * fx;
    const b = at(xi, yi + 1) + (at(xi + 1, yi + 1) - at(xi, yi + 1)) * fx;
    return a + (b - a) * fy;
  };
  return (u, v) => (once(u, v, 4) * 0.5 + once(u, v, 8) * 0.3 + once(u, v, 16) * 0.2);
}

// Fine grain, tiling: pits and specks far smaller than a picture's own features.
function grainOf(seed) {
  const once = (f, salt) => {
    const cell = (i, j) => {
      let h = (((i % f) + f) % f) * 73856093 ^ (((j % f) + f) % f) * 19349663 ^ (seed + salt) * 83492791;
      h ^= h >>> 13;
      h = Math.imul(h, 0x5bd1e995);
      h ^= h >>> 15;
      return (h >>> 0) / 2 ** 32;
    };
    return (u, v) => {
      const x = u * f;
      const y = v * f;
      const xi = Math.floor(x);
      const yi = Math.floor(y);
      const sx = x - xi;
      const sy = y - yi;
      const a = cell(xi, yi) + (cell(xi + 1, yi) - cell(xi, yi)) * sx;
      const b = cell(xi, yi + 1) + (cell(xi + 1, yi + 1) - cell(xi, yi + 1)) * sx;
      return a + (b - a) * sy;
    };
  };
  const [coarse, mid, fine] = [once(48, 1), once(112, 2), once(256, 3)];
  return (u, v) => coarse(u, v) * 0.34 + mid(u, v) * 0.36 + fine(u, v) * 0.3;
}
export const GRAIN = grainOf(211);

export function png(pixel, grit = 0.62) {
  const raw = Buffer.alloc((SIZE * 4 + 1) * SIZE);
  for (let y = 0; y < SIZE; y++) {
    const row = y * (SIZE * 4 + 1);
    for (let x = 0; x < SIZE; x++) {
      const u = (x + 0.5) / SIZE;
      const v = (y + 0.5) / SIZE;
      const p = pixel(u, v);
      // Every picture takes the grain, so nothing comes out looking like clean plastic.
      const speck = 1 + grit * (GRAIN(u, v) - 0.5) * 2;
      for (let c = 0; c < 3; c++) p[c] = (p[c] ?? 1) * speck;
      for (let c = 0; c < 4; c++) {
        raw[row + 1 + x * 4 + c] = Math.max(0, Math.min(255, Math.round((p[c] ?? 1) * 255)));
      }
    }
  }
  const chunk = (type, data) => {
    const body = Buffer.concat([Buffer.from(type), data]);
    const out = Buffer.alloc(body.length + 8);
    out.writeUInt32BE(data.length, 0);
    body.copy(out, 4);
    out.writeUInt32BE(zlib.crc32(body), body.length + 4);
    return out;
  };
  const head = Buffer.alloc(13);
  head.writeUInt32BE(SIZE, 0);
  head.writeUInt32BE(SIZE, 4);
  head[8] = 8;
  head[9] = 6;
  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    chunk('IHDR', head),
    chunk('IDAT', zlib.deflateSync(raw, { level: 9 })),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

const mix = (a, b, t) => a + (b - a) * t;
const mixed = (a, b, t) => [mix(a[0], b[0], t), mix(a[1], b[1], t), mix(a[2], b[2], t), 1];

// A petal: dark at its foot, its colour toward its tip, veined, and cut to a point.
function petal(foot, tip, seed) {
  const noise = noiseOf(seed);
  return () => png((u, v) => {
    const up = 1 - v;
    const half = 0.5 * Math.sin(Math.PI * Math.min(1, up ** 0.62)) ** 0.7;
    const off = Math.abs(u - 0.5);
    const vein = 0.86 + 0.14 * Math.cos((off * 46) + noise(u, v) * 2);
    const c = mixed(foot, tip, up ** 1.2 * (0.72 + noise(u, v) * 0.5));
    return [c[0] * vein, c[1] * vein, c[2] * vein, off < half ? 1 : 0];
  });
}

export const PICTURES = {
  'Gen_PalmBark.png': () => {
    const noise = noiseOf(11);
    return png((u, v) => {
      const ring = 0.84 + 0.16 * Math.sin(v * Math.PI * 2 * 14 + noise(u, 0.3) * 3) ** 2;
      const g = ring * (0.76 + noise(u, v) * 0.36);
      return [g * 0.8, g * 0.78, g * 0.72, 1];
    });
  },
  'Gen_Cap.png': () => {
    const noise = noiseOf(13);
    return png((u, v) => {
      const r = Math.hypot(u - 0.5, v - 0.5) * 2;
      const band = 0.5 + 0.5 * Math.sin(r * 24 + noise(u, v) * 3);
      const crust = Math.abs(Math.sin(r * 24 + noise(u, v) * 3)) < 0.16 ? 0.5 : 1;
      const blotch = 0.56 + 0.88 * noise(u * 2 + 0.3, v * 2);
      const g = (0.5 + 0.5 * band) * blotch * crust;
      return [g, g, g * 0.88, 1];
    });
  },
  'Gen_Gills.png': () => {
    const noise = noiseOf(17);
    return png((u, v) => {
      const a = Math.atan2(v - 0.5, u - 0.5);
      const g = (0.42 + 0.38 * Math.cos(a * 110)) * (0.65 + noise(u, v) * 0.7);
      return [g * 0.9, g * 0.82, g * 0.68, 1];
    });
  },
  'Gen_Stem.png': () => {
    const noise = noiseOf(19);
    return png((u, v) => {
      const g = (0.62 + 0.2 * Math.sin(u * TAU * 22 + noise(u, v) * 5)) * (0.55 + noise(u * 2, v * 2) * 0.9);
      return [g, g * 0.96, g * 0.86, 1];
    });
  },
  'Gen_Cactus.png': () => {
    const noise = noiseOf(23);
    return png((u, v) => {
      const groove = 0.66 + 0.34 * Math.cos(u * TAU * 2);
      const areole = Math.cos(u * TAU * 2) > 0.72 && Math.sin(v * TAU * 16) > 0.7 ? 1 : 0;
      const g = groove * (0.72 + noise(u, v) * 0.5);
      return [mix(g * 0.46, 0.86, areole), mix(g * 0.46, 0.82, areole), mix(g * 0.16, 0.52, areole), 1];
    });
  },
  'Gen_Ice.png': () => {
    const noise = noiseOf(29);
    return png((u, v) => {
      const streak = noise(u * 0.5, v * 3);
      const crack = Math.abs(noise(u * 2, v) - 0.5) < 0.012 ? 1.5 : 1;
      const g = (0.62 + streak * 0.5) * crack;
      return [g * 0.8, g * 0.94, 1, 1];
    });
  },
  'Gen_Coral.png': () => {
    const noise = noiseOf(31);
    return png((u, v) => {
      const pit = Math.sin(u * TAU * 16 + noise(u, v) * 4) * Math.sin(v * TAU * 16 + noise(v, u) * 4);
      const g = (0.6 + 0.34 * pit) * (0.62 + noise(u * 2, v * 2) * 0.76);
      return [g, g, g, 1];
    });
  },
  'Gen_Petal_Magenta.png': petal([0.72, 0.2, 0.66], [1, 0.3, 0.9], 37),
  'Gen_Petal_Crimson.png': petal([0.66, 0.08, 0.18], [0.95, 0.14, 0.26], 41),
};

// The rounded ball of roots a trunk stands in. It reaches well below the ground, so a tree on a
// slope stays planted on its low side, and spreads at most about half the trunk again at the ground.
export function foot(mesh, trunk, seg = 1, seed = 1, wraps = 2) {
  const R = trunk * 1.45;
  const H = trunk * 2.4;
  const d = Math.max(trunk * 1.7, Math.min(1.1, trunk * 5));
  const profile = [[0.01, -d], [R * 0.55, -d * 0.85], [R * 0.85, -d * 0.45], [R, -d * 0.08], [R * 0.92, H * 0.1], [R * 0.7, H * 0.38], [R * 0.54, H * 0.7], [trunk * 0.85, H]];
  const lobes = (a) => 1 + 0.1 * Math.cos(5 * a + seed) + 0.05 * Math.cos(9 * a + seed * 2);
  const from = mesh.normal.length;
  lathe(mesh, profile, Math.max(6, Math.round(16 * seg)), lobes, (r, a, y) => [(a / TAU) * wraps, y / 3.4]);
  for (let i = from; i < mesh.normal.length; i += 3) {
    const n = unit([mesh.normal[i], mesh.normal[i + 1] * 0.3, mesh.normal[i + 2]]);
    mesh.normal.splice(i, 3, ...n);
  }
  seatFoot(mesh, from, mesh.position, mesh.index, from / 3);
}

// Draws a foot (`foot`'s vertices from `from` on) in to the trunk it stands under: at each height it
// narrows toward the trunk's own middle and width, measured from `trunk`'s triangles (those on
// vertices under `upTo`), fully by its top, so the two meet with no ledge, sleeve or bulge, and it
// follows a leaning trunk. Under the ground it keeps its spread.
export function seatFoot(foot, from, trunk, index, upTo = Infinity) {
  let top = 0;
  for (let i = from + 1; i < foot.position.length; i += 3) top = Math.max(top, foot.position[i]);
  if (top <= 0) return;
  let reach = 0;
  for (let i = from; i < foot.position.length; i += 3) reach = Math.max(reach, Math.hypot(foot.position[i], foot.position[i + 2]));
  const rings = [];
  for (let k = 1; k <= 12; k++) {
    const y = (top * k) / 12;
    const pts = [];
    for (let t = 0; t + 2 < index.length; t += 3) {
      const tri = [index[t], index[t + 1], index[t + 2]];
      if (tri.some((v) => v >= upTo)) continue;
      for (const [a, b] of [[tri[0], tri[1]], [tri[1], tri[2]], [tri[2], tri[0]]]) {
        const ya = trunk[a * 3 + 1], yb = trunk[b * 3 + 1];
        if ((ya - y) * (yb - y) >= 0) continue;
        const f = (y - ya) / (yb - ya);
        const x = trunk[a * 3] + (trunk[b * 3] - trunk[a * 3]) * f;
        const z = trunk[a * 3 + 2] + (trunk[b * 3 + 2] - trunk[a * 3 + 2]) * f;
        if (Math.hypot(x, z) <= reach * 1.6 + 0.5) pts.push([x, z]);
      }
    }
    if (pts.length < 3) continue;
    const cx = pts.reduce((s, p) => s + p[0], 0) / pts.length;
    const cz = pts.reduce((s, p) => s + p[1], 0) / pts.length;
    const d = pts.map((p) => Math.hypot(p[0] - cx, p[1] - cz)).sort((m, n) => m - n);
    rings.push([y, cx, cz, d[Math.floor(0.9 * (d.length - 1))]]);
  }
  if (!rings.length) return;
  const at = (y) => {
    if (y <= rings[0][0]) return rings[0];
    for (let k = 1; k < rings.length; k++) {
      if (y <= rings[k][0]) {
        const [y0, ...a] = rings[k - 1], [y1, ...b] = rings[k], f = (y - y0) / (y1 - y0);
        return [y, a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f];
      }
    }
    return rings[rings.length - 1];
  };
  for (let i = from; i < foot.position.length; i += 3) {
    const y = foot.position[i + 1];
    if (y <= 0) continue;
    const [, cx, cz, r] = at(y);
    const u = Math.min(1, y / top);
    const keep = 1 - u * u * (3 - 2 * u);
    const dx = foot.position[i] - cx, dz = foot.position[i + 2] - cz;
    const d = Math.hypot(dx, dz);
    const inner = r * 0.97;
    if (d <= inner || d < 1e-6) continue;
    const k = (inner + (d - inner) * keep) / d;
    foot.position[i] = cx + dx * k;
    foot.position[i + 2] = cz + dz * k;
  }
}

// A foot alone, as its own part, for a tree grown elsewhere.
export function footMesh(trunk, seg, seed) {
  const mesh = newMesh();
  foot(mesh, trunk, seg, seed);
  return mesh;
}

// Colours each vertex of `mesh` by `fn(normal)`; the picture is multiplied by them.
function shade(mesh, fn) {
  mesh.color = [];
  for (let i = 0; i < mesh.normal.length; i += 3) {
    mesh.color.push(...fn(mesh.normal[i + 1], mesh.position[i + 1], mesh.position[i], mesh.position[i + 2]), 1);
  }
}

// A crown of crossed leaf cards over a flattened dome from `low` to `top`, as thick as `layers`
// makes it, the cards no bigger than `largest`.
function canopy(mesh, { rim, low, top, lod, random, seed = 1, largest = 2.4, layers = 3.2, power = 3 }) {
  const size = Math.min(largest, rim * 0.34);
  const count = Math.max(40, Math.min(900, Math.round(((Math.PI * rim * rim) / (size * size)) * layers)));
  const kept = Math.round(count * lod.keep);
  for (let c = 0; c < kept; c++) {
    const r = rim * Math.sqrt(random());
    const a = random() * TAU;
    const fall = r / rim;
    const clump = Math.sin(a * 5 + seed) * Math.sin(r * 0.55 + seed) * (top - low) * 0.09;
    const under = random() < 0.28 ? -(top - low) * (0.1 + random() * 0.16) : 0;
    const y = top - (top - low) * fall ** power + clump + under;
    cards(mesh, [Math.cos(a) * r, y, Math.sin(a) * r], size * lod.grow ** 0.8 * (0.8 + random() * 0.4), random);
  }
}

// A solid mass of leaves inside a crown, an ellipsoid about `y`.
function leafMass(mesh, rim, y, high, seed) {
  const profile = [];
  for (let k = 0; k <= 7; k++) {
    const a = -Math.PI / 2 + (k / 7) * Math.PI;
    profile.push([Math.max(0.01, rim * Math.cos(a)), y + high * Math.sin(a)]);
  }
  const lumps = (a) => 1 + 0.025 * Math.sin(5 * a + seed) + 0.02 * Math.sin(11 * a + seed);
  lathe(mesh, profile, 16, lumps, (r, a, h) => [0.5 + (0.5 * r * Math.cos(a)) / rim, 0.5 + (0.5 * r * Math.sin(a)) / rim + h * 0.02]);
}

const massLook = (look) => ({ color: 'Gen_LeafMass.png', tint: look.mass ?? look.tint });

// Leaf cards over the upper surface of a leaf mass, a little outside it, none under `floor`.
function shellCards(mesh, { rim, y, high, floor, size, count, lod, random }) {
  const kept = Math.round(count * lod.keep);
  for (let c = 0; c < kept; c++) {
    const up = random() * 2 - 1;
    const a = random() * TAU;
    const out = Math.sqrt(1 - up * up);
    const at = 1.02 + random() * 0.16;
    const py = y + high * up * at;
    if (py < floor) continue;
    cards(mesh, [Math.cos(a) * out * rim * at, py, Math.sin(a) * out * rim * at], size * lod.grow ** 0.8 * (0.8 + random() * 0.4), random);
  }
}

// Limbs radiating from a trunk at `from`..`to` of its height, curving as they go.
function limbs(mesh, { count, from, to, reach, trunk, lift, random, sides = 5, head = [0, 0, 0] }) {
  for (let k = 0; k < count; k++) {
    const a = ((k + random() * 0.7) / count) * TAU;
    const y = from + (to - from) * random();
    const long = reach * (0.62 + random() * 0.38);
    const bend = long * 0.12 * (random() - 0.5);
    const at = (t) => [
      head[0] * (y / to) + Math.cos(a) * long * t - Math.sin(a) * bend * Math.sin(t * Math.PI),
      y + lift * long * (t - 0.5 * t * t) * (1 + (random() - 0.5) * 0.1),
      head[2] * (y / to) + Math.sin(a) * long * t + Math.cos(a) * bend * Math.sin(t * Math.PI),
    ];
    sweep(mesh, [at(0), at(0.33), at(0.66), at(1)], (t) => trunk * 0.32 * (1 - t * 0.8), sides);
  }
}

const flared = (trunk, flare = 1) => (t) => trunk * (0.55 + 0.45 * (1 - t) + flare * (1 - t) ** 6);

// A tree with a bare, pale, flared trunk and a wide flat crown.
export function parasol({ across, tall, trunk, lean = 0, bark, leaves: look, low = 0.66 }, lod, random) {
  const wood = newMesh();
  const crown = newMesh();
  const a0 = random() * TAU;
  const rings = Math.max(4, Math.round(9 * lod.seg));
  const head = [Math.cos(a0) * across * lean, 0, Math.sin(a0) * across * lean];
  const points = [];
  for (let k = 0; k <= rings; k++) {
    const t = k / rings;
    points.push([head[0] * t * t, -0.8 + (tall * 0.74 + 0.8) * t, head[2] * t * t]);
  }
  const sides = Math.max(5, Math.round(12 * lod.seg));
  sweep(wood, points, flared(trunk), sides, { wraps: 2 });
  foot(wood, trunk, lod.seg, a0);
  limbs(wood, { count: 9, from: tall * Math.min(0.56, low + 0.1), to: tall * 0.74, reach: across / 2, trunk, lift: 0.3, random, head });
  // `low`: the share of its height its crown's rim comes down to.
  canopy(crown, { rim: across / 2, low: tall * low, top: tall, lod, random, seed: a0, power: 2.4, layers: 5 });
  return [
    { name: 'Bark', look: bark, opaque: true, mesh: wood },
    { name: 'Leaves', look, mesh: crown },
  ];
}

// A short trunk under a dense, low dome of leaves.
export function dome({ across, tall, trunk, bark, leaves: look }, lod, random) {
  const wood = newMesh();
  const crown = newMesh();
  const s = random() * TAU;
  sweep(wood, [[0, -0.8, 0], [0, tall * 0.2, 0], [0, tall * 0.5, 0]], flared(trunk), Math.max(5, Math.round(12 * lod.seg)), { wraps: 2 });
  foot(wood, trunk, lod.seg, s);
  limbs(wood, { count: 8, from: tall * 0.28, to: tall * 0.5, reach: across * 0.42, trunk, lift: 0.5, random });
  const mass = newMesh();
  leafMass(mass, across * 0.44, tall * 0.5, tall * 0.42, s);
  shellCards(crown, { rim: across * 0.44, y: tall * 0.5, high: tall * 0.42, floor: tall * 0.12, size: across * 0.075, count: 1100, lod, random });
  return [
    { name: 'Mass', look: massLook(look), opaque: true, mesh: mass },
    { name: 'Bark', look: bark, opaque: true, mesh: wood },
    { name: 'Leaves', look, mesh: crown },
  ];
}

// An elm: a clear trunk forking into limbs that rise as a vase, under a broad crown whose edge droops.
export function elm({ across, tall, trunk, bark, leaves: look, low }, lod, random) {
  // `low`: the share of its height its crown comes down to, lower than an elm's own.
  const floor = low ?? 0.52;
  const y = low ? tall * (0.98 + low) / 2 : tall * 0.74;
  const high = low ? tall * (0.98 - low) / 2 : tall * 0.24;
  const wood = newMesh();
  const crown = newMesh();
  const s = random() * TAU;
  const fork = tall * 0.36;
  const sides = Math.max(5, Math.round(12 * lod.seg));
  sweep(wood, [[0, -0.8, 0], [0, fork * 0.6, 0], [0, fork * 1.1, 0]], flared(trunk, 0.6), sides, { wraps: 2 });
  foot(wood, trunk, lod.seg, s);
  const forks = 5;
  for (let k = 0; k < forks; k++) {
    const a = ((k + random() * 0.5) / forks) * TAU;
    const out = (r, h) => [Math.cos(a) * across * r, tall * h, Math.sin(a) * across * r];
    const start = 0.3 + random() * 0.05;
    sweep(wood, [[0, tall * start, 0], out(0.07, 0.48), out(0.17, 0.62), out(0.3, 0.72)],
      (t) => trunk * 0.5 * (1 - t * 0.78), Math.max(4, sides - 4));
  }
  limbs(wood, { count: 10, from: tall * 0.5, to: tall * 0.7, reach: across * 0.42, trunk: trunk * 0.7, lift: 0.28, random });
  shellCards(crown, { rim: across * 0.44, y, high, floor: tall * floor, size: across * 0.095, count: 900, lod, random });
  shellCards(crown, { rim: across * 0.32, y: low ? y : tall * 0.76, high: low ? high * 0.7 : tall * 0.15, floor: tall * (floor + 0.04), size: across * 0.08, count: 700, lod, random });
  // The drooping edge, thin enough to see the sky through.
  const kept = Math.round(150 * lod.keep);
  for (let c = 0; c < kept; c++) {
    const a = random() * TAU;
    const r = across * (0.36 + random() * 0.12);
    cards(crown, [Math.cos(a) * r, tall * (floor - 0.02 + random() * 0.18), Math.sin(a) * r], across * 0.06 * lod.grow ** 0.8, random);
  }
  return [
    { name: 'Bark', look: bark, opaque: true, mesh: wood },
    { name: 'Leaves', look, mesh: crown },
  ];
}

// A tall bare trunk with a dense crown on top, and leaves nowhere else.
export function crowned({ across, tall, trunk, bark, leaves: look, flare = 0.9, droop = false }, lod, random) {
  const wood = newMesh();
  const crown = newMesh();
  const s = random() * TAU;
  // `droop`: a short flared trunk under tiers of leaves that hang down, from a third of its height.
  if (droop) {
    const rings = Math.max(4, Math.round(9 * lod.seg));
    const points = Array.from({ length: rings + 1 }, (_, k) => [0, -0.8 + (tall * 0.9 + 0.8) * (k / rings), 0]);
    sweep(wood, points, (t) => trunk * (0.25 + 0.3 * (1 - t) + flare * (1 - t) ** 4), Math.max(5, Math.round(12 * lod.seg)), { wraps: 2 });
    foot(wood, trunk * 0.8, lod.seg, s);
    const tiers = 4;
    for (let k = 0; k < tiers; k++) {
      const f = k / (tiers - 1);
      const y = tall * (0.42 + 0.48 * f);
      const reach = (across / 2) * (0.95 - 0.5 * f);
      const arms = Math.max(4, Math.round((7 - k) * Math.max(lod.seg, 0.6)));
      for (let a = 0; a < arms; a++) {
        const q = s + (a / arms) * TAU + k * 0.6 + random() * 0.4;
        const end = [Math.cos(q) * reach, y + tall * 0.05, Math.sin(q) * reach];
        sweep(wood, [[0, y - tall * 0.06, 0], [end[0] * 0.5, y + tall * 0.06, end[2] * 0.5], end], (t) => trunk * 0.22 * (1 - t * 0.7), 4);
        const count = Math.max(3, Math.round(11 * lod.keep));
        for (let c = 0; c < count; c++) {
          const t = 0.35 + 0.65 * random();
          const at = [end[0] * t + (random() - 0.5) * reach * 0.3, y + tall * 0.05 * t + (random() - 0.5) * tall * 0.04, end[2] * t + (random() - 0.5) * reach * 0.3];
          tilted(crown, at, across * 0.16 * lod.grow ** 0.7 * (0.8 + random() * 0.4), random, -1.25, -0.55);
        }
      }
    }
    // A cap of leaves over the top tier.
    shellCards(crown, { rim: across * 0.18, y: tall * 0.92, high: tall * 0.06, floor: tall * 0.86, size: across * 0.14, count: 50, lod, random });
    return [
      { name: 'Bark', look: bark, opaque: true, mesh: wood },
      { name: 'Leaves', look, mesh: crown },
    ];
  }
  const rings = Math.max(4, Math.round(9 * lod.seg));
  const points = [];
  for (let k = 0; k <= rings; k++) points.push([0, -0.8 + (tall * 0.84 + 0.8) * (k / rings), 0]);
  sweep(wood, points, (t) => trunk * (0.3 + 0.3 * (1 - t) + flare * (1 - t) ** 6), Math.max(5, Math.round(12 * lod.seg)), { wraps: 2 });
  foot(wood, trunk * 0.8, lod.seg, s);
  limbs(wood, { count: 7, from: tall * 0.66, to: tall * 0.84, reach: across * 0.42, trunk: trunk * 0.5, lift: 0.5, random, sides: 4 });
  shellCards(crown, { rim: across * 0.42, y: tall * 0.84, high: tall * 0.1, floor: tall * 0.7, size: across * 0.2, count: 170, lod, random });
  // A layer inside, so the crown is leaves all through.
  shellCards(crown, { rim: across * 0.27, y: tall * 0.84, high: tall * 0.07, floor: tall * 0.7, size: across * 0.15, count: 130, lod, random });
  return [
    { name: 'Bark', look: bark, opaque: true, mesh: wood },
    { name: 'Leaves', look, mesh: crown },
  ];
}

// A dense clump of leaves on a few stems; `leafy` below 1 thins it to a few clumps on stems reaching
// `reach` of its height, as the older young trees are.
export function shrub({ across, tall, bark, leaves: look, leafy = 1, stems = 4, reach = 0.6, lobes = 0 }, lod, random) {
  const wood = newMesh();
  const crown = newMesh();
  // `lobes`: an upright bush of that many leafy clumps on bare stems, its crown from a fifth of its
  // height, as retail's bushes are.
  if (lobes) {
    const floor = tall * 0.2;
    for (let k = 0; k < lobes; k++) {
      const a = (k / lobes) * TAU + random() * 0.8;
      const out = across * (k === 0 ? 0 : 0.16 + 0.1 * random());
      const r = across * (0.13 + 0.06 * random());
      const h = tall * (0.12 + 0.05 * random());
      // Spread from the crown's floor to its top, so the bush is leafy all the way up.
      const cy = floor + h * 0.7 + ((k * 5) % lobes / Math.max(1, lobes - 1)) * (tall - floor - 1.7 * h);
      const at = [Math.cos(a) * out, cy, Math.sin(a) * out];
      sweep(wood, [[at[0] * 0.1, -0.5, at[2] * 0.1], [at[0] * 0.5, floor, at[2] * 0.5], at], (t) => Math.max(0.04, across * 0.022) * (1 - t * 0.6), 4);
      const clump = newMesh();
      shellCards(clump, { rim: r, y: 0, high: h, floor: -h * 0.85, size: Math.min(1, across * 0.16), count: Math.round(90 * leafy), lod, random });
      merge(crown, clump, at);
    }
    foot(wood, Math.max(0.02, across * 0.05), lod.seg, 1);
    return [
      { name: 'Bark', look: bark, opaque: true, mesh: wood },
      { name: 'Leaves', look, mesh: crown },
    ];
  }
  for (let k = 0; k < stems; k++) {
    const a = (k / stems) * TAU;
    sweep(wood, [[0, -0.5, 0], [Math.cos(a) * across * 0.1, tall * 0.25, Math.sin(a) * across * 0.1], [Math.cos(a) * across * 0.22, tall * reach, Math.sin(a) * across * 0.22]], (t) => Math.max(0.05, across * 0.03) * (1 - t * 0.7), 4);
  }
  foot(wood, Math.max(0.02, across * 0.05), lod.seg, 1);
  shellCards(crown, { rim: across * 0.4, y: tall * 0.54, high: tall * 0.42, floor: tall * 0.1, size: Math.min(1.5, across * 0.3), count: Math.round(210 * leafy), lod, random });
  shellCards(crown, { rim: across * 0.25, y: tall * 0.54, high: tall * 0.28, floor: tall * 0.1, size: Math.min(1.2, across * 0.24), count: Math.round(150 * leafy), lod, random });
  return [
    { name: 'Bark', look: bark, opaque: true, mesh: wood },
    { name: 'Leaves', look, mesh: crown },
  ];
}

// A dead tree with no leaves, snapped into sharp spikes: burnt black, and with `ash` a pale coat on
// everything that faces up.
export function snag({ across, tall, trunk, spikes = 9, fork = false, ash = 0, char = 0.018, dust = 0, tint }, lod, random) {
  const wood = newMesh();
  const a0 = random() * TAU;
  const sides = Math.max(5, Math.round(11 * lod.seg));
  const high = fork ? 0.4 : 0.92;
  const rings = Math.max(4, Math.round(8 * lod.seg));
  const points = [];
  for (let k = 0; k <= rings; k++) {
    const t = k / rings;
    points.push([(random() - 0.5) * trunk * 0.3 * t, -0.8 + (tall * high + 0.8) * t, (random() - 0.5) * trunk * 0.3 * t]);
  }
  // A forked trunk narrows to its spikes' bases, which rise from inside it toward its rim, so it ends in them with no ledge.
  sweep(wood, points, (t) => (fork ? trunk * (0.42 + 0.58 * (1 - t) ** 0.8) : trunk * ((1 - t) ** 0.8 * 0.95 + 0.02)) + trunk * 0.5 * (1 - t) ** 6, sides, { rib: 0.05, ribs: 7, wraps: 2 });
  foot(wood, trunk * 0.9, lod.seg, a0);
  const spike = (from, dir, long, radius, level) => {
    const path = [from];
    let at = from;
    let d = dir;
    for (let s = 0; s < 3; s++) {
      d = unit(add(d, [(random() - 0.5) * 0.7, 0.12, (random() - 0.5) * 0.7]));
      at = add(at, d, long / 3);
      path.push(at);
    }
    sweep(wood, path, (t) => radius * (1 - t) + 0.008, Math.max(3, Math.round(sides * 0.5)), { wraps: 1 });
    if (level > 0) {
      const forks = 2;
      for (let f = 0; f < forks; f++) {
        const a = random() * TAU;
        spike(path[1 + f], unit(add(d, [Math.cos(a), 0.35, Math.sin(a)], 0.85)), long * 0.45, radius * 0.45, level - 1);
      }
    }
  };
  const count = Math.max(3, Math.round(spikes * Math.max(lod.keep, 0.45)));
  for (let k = 0; k < count; k++) {
    const a = a0 + (k * 2.4) + random() * 0.5;
    const t = fork ? 1 : 0.3 + 0.65 * (k / count);
    const base = points[Math.round(rings * (fork ? 0.8 : t))];
    const from = fork ? [base[0] + Math.cos(a) * trunk * 0.3, base[1], base[2] + Math.sin(a) * trunk * 0.3] : base;
    const reach = (across / 2) * (fork ? 0.8 : 1.05 - 0.55 * t) * (0.75 + random() * 0.3);
    const lift = fork ? 2.4 + random() * 1.4 : 0.2 + random() * 0.5;
    const dir = unit([Math.cos(a), lift, Math.sin(a)]);
    const radius = trunk * (fork ? 0.36 : 0.2);
    const climb = fork ? (tall * (1 - high) * (0.7 + random() * 0.3)) / Math.max(0.5, dir[1]) : reach / Math.hypot(dir[0], dir[2]);
    spike(from, dir, climb, radius, lod.seg > 0.6 ? 1 : 0);
  }
  shade(wood, (up, y) => {
    const low = y < trunk * 3 ? 0.15 : 1;
    const coat = Math.max(0, Math.min(1, (up + 0.4) / 0.6)) * ash * low;
    const g = char + dust * Math.max(0, up);
    return [g + (0.42 - g) * coat, g * 0.94 + (0.41 - g * 0.94) * coat, g * 0.88 + (0.39 - g * 0.88) * coat];
  });
  // The client draws no vertex colours, so `tint` gives the wood its colour.
  return [{ name: 'Wood', look: { color: 'Gen_Char.png', tint: tint ?? [1, 1, 1, 1] }, opaque: true, mesh: wood }];
}

PICTURES['Gen_Char.png'] = () => {
  const noise = noiseOf(59);
  return png((u, v) => {
    const ridge = Math.abs(noise(u, v * 0.5) - 0.5) * 2;
    const g = (0.58 + 0.42 * Math.min(1, ridge * 9)) * (0.72 + noise(v, u) * 0.56);
    return [g, g, g, 1];
  });
};

// A green stalk on a broad flared foot, growing out of water, with flat umbrellas of leaves.
export function stalk({ across, tall, trunk, leaf = [0.15, 0.34, 0.13, 1] }, lod, random) {
  const wood = newMesh();
  const crown = newMesh();
  const rows = Math.max(4, Math.round(9 * lod.seg));
  const a0 = random() * TAU;
  const points = [];
  for (let k = 0; k <= rows; k++) {
    const t = k / rows;
    points.push([Math.cos(a0) * across * 0.06 * t * t, -0.8 + (tall * 0.8 + 0.8) * t, Math.sin(a0) * across * 0.06 * t * t]);
  }
  const options = { rib: 0.05, ribs: 7, wraps: 2, perMeter: 0.2 };
  const sides = Math.max(5, Math.round(12 * lod.seg));
  const stalkR = (t) => trunk * (0.11 + 0.14 * (1 - t) + 0.8 * (1 - t) ** 5);
  sweep(wood, points, stalkR, sides, options);
  foot(wood, trunk * 0.55, lod.seg, a0);
  const heads = [points[rows]];
  for (let k = 0; k < 2; k++) {
    const a = a0 + 2 + k * 2.4;
    const from = points[Math.round(rows * 0.6)];
    const end = [from[0] + Math.cos(a) * across * 0.3, tall * (0.72 + 0.1 * k), from[2] + Math.sin(a) * across * 0.3];
    sweep(wood, [from, [(from[0] + end[0]) / 2, (from[1] + end[1]) / 2 + tall * 0.03, (from[2] + end[2]) / 2], end], () => trunk * 0.14, Math.max(4, sides - 4), options);
    heads.push(end);
  }
  const blades = Math.max(4, Math.round(8 * lod.keep ** 0.6));
  heads.forEach((head) => {
    for (let i = 0; i < blades; i++) {
      const a = (i / blades) * TAU + random();
      const long = across * 0.34 * (0.85 + random() * 0.3);
      ribbon(crown, arch(head, a, long, 0.14, 0.22, Math.max(3, Math.round(6 * lod.seg))), () => long * 0.42 * lod.grow ** 0.5, LONG, [0, 1, 0]);
    }
  });
  return [
    { name: 'Stalk', look: generated('Gen_Stalk.png', [1, 1, 1, 1]), opaque: true, mesh: wood },
    { name: 'Leaves', look: leaves(leaf), mesh: crown },
  ];
}

// A low, gnarled thing: a stout foot throwing out thick twisting arms, arching over or reaching up,
// with tufts of dark leaves on those that have them.
export function gnarl({ across, tall, trunk, arms = 6, arching = false, tufts = 0, bark }, lod, random) {
  const wood = newMesh();
  const crown = newMesh();
  const sides = Math.max(4, Math.round(10 * lod.seg));
  const a0 = random() * TAU;
  const head = [0, tall * 0.26, 0];
  sweep(wood, [[0, -0.8, 0], [0, tall * 0.12, 0], head], (t) => trunk * (0.72 + 0.28 * (1 - t) + 0.5 * (1 - t) ** 5), sides, { rib: 0.1, ribs: 5, wraps: 2 });
  foot(wood, trunk, lod.seg, a0);
  for (let k = 0; k < arms; k++) {
    const a = a0 + (k / arms) * TAU + random() * 0.5;
    const reach = (across / 2) * (0.7 + random() * 0.35);
    const path = [head];
    const twist = (random() - 0.5) * 1.6;
    for (let s = 1; s <= 6; s++) {
      const t = s / 6;
      const turn = a + twist * t;
      const r = reach * t;
      const y = arching
        ? head[1] + (tall - head[1]) * Math.sin(Math.PI * Math.min(1, t * 0.86)) * (0.8 + random() * 0.15) - head[1] * 0.2 * t
        : head[1] + (tall - head[1]) * t ** 0.8 * (0.82 + random() * 0.18);
      path.push([Math.cos(turn) * r + (random() - 0.5) * trunk * 0.4, y, Math.sin(turn) * r + (random() - 0.5) * trunk * 0.4]);
    }
    sweep(wood, path, (t) => trunk * 0.5 * (1 - t * 0.86), Math.max(4, sides - 3), { rib: 0.08, ribs: 3, wraps: 1 });
    const count = Math.round(tufts * lod.keep);
    for (let c = 0; c < count; c++) {
      const p = path[3 + Math.floor(random() * 4)];
      cards(crown, [p[0] + (random() - 0.5) * across * 0.1, p[1] + (random() - 0.2) * tall * 0.08, p[2] + (random() - 0.5) * across * 0.1], across * 0.13 * lod.grow ** 0.8, random);
    }
  }
  const parts = [{ name: 'Bark', look: bark, opaque: true, mesh: wood }];
  if (crown.index.length) parts.push({ name: 'Leaves', look: { color: 'Leaves_oak.png', tint: [0.12, 0.13, 0.22, 1], cutoff: 0.3 }, mesh: crown });
  return parts;
}

PICTURES['Gen_Stalk.png'] = () => {
  const noise = noiseOf(61);
  return png((u, v) => {
    const streak = noise(u, v * 0.25);
    const g = 0.55 + streak * 0.75;
    return [g * 0.3, g * 0.42, g * 0.14, 1];
  });
};
PICTURES['Gen_Paddle.png'] = () => {
  const noise = noiseOf(67);
  return png((u, v) => {
    const up = 1 - v;
    // Serrated edges, and a skin thick with pale speckles over dark pits.
    const tooth = 0.05 * Math.abs(Math.sin(up * TAU * 11));
    const half = 0.5 * Math.sin(Math.PI * Math.min(1, 0.06 + up * 0.94) ** 0.8) ** 0.6 - tooth;
    const x = u * 34 + (Math.floor(v * 34) % 2) * 0.5;
    const y = v * 34;
    const r = Math.hypot(x - Math.floor(x) - 0.5, y - Math.floor(y) - 0.5);
    const speck = r < 0.3 ? 1.7 : r < 0.44 ? 0.34 : 1;
    const g = (0.62 + noise(u * 2, v * 2) * 0.6) * speck;
    return [g, g, g, Math.abs(u - 0.5) < half ? 1 : 0];
  }, 0.75);
};

PICTURES['Gen_LeafMass.png'] = () => {
  const noise = noiseOf(71);
  return png((u, v) => {
    const g = 0.16 + 0.42 * noise(u * 2, v * 2) * (0.6 + noise(v, u) * 0.8);
    return [g, g, g, 1];
  });
};

// Shifts everything in `mesh` from vertex `from` on by `by`.
function moved(mesh, from, by) {
  for (let i = from; i < mesh.position.length; i += 3) {
    mesh.position[i] += by[0];
    mesh.position[i + 1] += by[1];
    mesh.position[i + 2] += by[2];
  }
}

// An alien seed pod: a lumpy egg with a furred husk breaking open round flames of blotched flesh,
// its tips drawn out, dark ribs running up it from the ground.
export function pod({ across, tall, picture }, lod, random) {
  const body = newMesh();
  const flames = newMesh();
  const ribs = newMesh();
  const R = across / 2;
  const s = random() * TAU;
  const profile = [[0.01, -0.5], [R * 0.6, -0.08], [R * 0.93, tall * 0.14], [R, tall * 0.28], [R * 0.9, tall * 0.44], [R * 0.68, tall * 0.6], [R * 0.4, tall * 0.74], [0.01, tall * 0.86]];
  const lumps = (a) => 1 + 0.1 * Math.cos(3 * a + s) + 0.05 * Math.cos(5 * a + s * 2) + 0.04 * Math.abs(Math.sin(4 * a));
  const heightUv = (a, y) => [a / TAU, Math.max(0.002, Math.min(0.998, 1 - y / tall))];
  lathe(body, profile, Math.max(7, Math.round(14 * lod.seg)), lumps, (r, a, y) => heightUv(a, y));
  const sides = lod.seg > 0.5 ? 6 : 4;
  const tips = [[s + 0.4, 0.32, 1], [s + 2.5, 0.44, 0.84], [s + 4.4, 0.42, 0.72]];
  for (const [a, out, high] of tips) {
    const from = [Math.cos(a) * R * out, tall * 0.5, Math.sin(a) * R * out];
    const top = [Math.cos(a) * R * out * 0.75, tall * high, Math.sin(a) * R * out * 0.75];
    const mid = [(from[0] + top[0]) / 2 + Math.cos(a) * R * 0.08, (from[1] + top[1]) / 2, (from[2] + top[2]) / 2 + Math.sin(a) * R * 0.08];
    sweep(flames, [from, mid, top], (t) => R * 0.5 * (1 - t) ** 0.75 + 0.005, sides);
  }
  for (let i = 0; i < flames.position.length / 3; i++) {
    flames.uv[i * 2 + 1] = Math.max(0.002, Math.min(0.998, 1 - flames.position[i * 3 + 1] / tall));
  }
  const at = (a, y) => {
    let r = 0.01;
    for (let k = 0; k + 1 < profile.length; k++) {
      const [r0, y0] = profile[k];
      const [r1, y1] = profile[k + 1];
      if (y >= y0 && y <= y1) r = r0 + ((r1 - r0) * (y - y0)) / Math.max(0.001, y1 - y0);
    }
    return [Math.cos(a) * r * lumps(a) * 1.01, y, Math.sin(a) * r * lumps(a) * 1.01];
  };
  const count = lod.seg > 0.5 ? 7 : 4;
  for (let k = 0; k < count; k++) {
    const a = s + (k / count) * TAU + random() * 0.3;
    const end = 0.42 + random() * 0.32;
    const path = [];
    for (let q = 0; q <= 6; q++) path.push(at(a + 0.25 * Math.sin(q), -0.1 + tall * end * (q / 6)));
    sweep(ribs, path, (t) => across * 0.034 * (1 - t * 0.7), 3);
  }
  const look = { color: picture, normal: 'Gen_Pod_Normal.png', tint: [1, 1, 1, 1], rough: 0.85 };
  return [
    { name: 'Body', look, opaque: true, mesh: body },
    { name: 'Flames', look, opaque: true, mesh: flames },
    { name: 'Ribs', look: { ...BARK, tint: [0.012, 0.012, 0.03, 1] }, opaque: true, mesh: ribs },
  ];
}

// A tree of bat's wings: a straight trunk running on into a spike, and four pairs of arched arms,
// each pair holding a dark membrane that frays into hanging strands.
export function wingTree({ across, tall, trunk }, lod) {
  const wood = newMesh();
  const wings = newMesh();
  // Four arms a quarter turn apart, an X seen from above, reaching the model's corners.
  const long = (across / 2) * 1.33;
  const head = tall * 0.68;
  const rise = tall * 0.21;
  const rings = Math.max(4, Math.round(9 * lod.seg));
  const stem = [];
  for (let k = 0; k <= rings; k++) stem.push([0, -0.8 + (tall + 0.8) * (k / rings), 0]);
  sweep(wood, stem, (t) => trunk * (1 - t) ** 0.8 + 0.01, Math.max(5, Math.round(11 * lod.seg)), { rib: 0.05, ribs: 7, wraps: 2 });
  foot(wood, trunk * 0.72, lod.seg, 0.8);
  const rows = Math.max(4, Math.round(11 * lod.seg));
  for (let w = 0; w < 4; w++) {
    const a = Math.PI / 4 + (w * Math.PI) / 2;
    const dir = [Math.cos(a), Math.sin(a)];
    const out = (r, y) => [dir[0] * r, y, dir[1] * r];
    // Each arm climbs from the trunk to its peak and hooks over at the end.
    const arm = (t) => out(long * t, head + rise * (Math.min(1, t / 0.86) ** 0.8 - 0.3 * Math.max(0, t - 0.86) / 0.14));
    const line = Array.from({ length: rows + 1 }, (_, k) => arm(k / rows));
    sweep(wood, line, (t) => trunk * 0.24 * (1 - t * 0.55), 6, { wraps: 1, rib: 0.16, ribs: 3 });
    // Its web hangs beneath it, longest toward the end, in the plane of the arm.
    const side = [-dir[1], dir[0]];
    const layers = lod.seg > 0.9 ? [trunk * 0.07, -trunk * 0.07] : [0];
    layers.forEach((shift, l) => {
      const base = wings.position.length / 3;
      for (let k = 0; k <= rows; k++) {
        const t = 0.06 + 0.94 * (k / rows);
        const top = arm(t);
        const hang = tall * (0.05 + 0.42 * t ** 1.3) * (1 - 0.3 * Math.max(0, t - 0.86) / 0.14);
        for (let r = 0; r <= 3; r++) {
          mesh3(wings, top[0] + side[0] * shift, top[1] - (hang * r) / 3, top[2] + side[1] * shift, side, (t * long) / 4.4 + w * 0.29 + l * 0.37, r / 3);
        }
      }
      for (let k = 0; k < rows; k++) {
        for (let r = 0; r < 3; r++) {
          const p = base + k * 4 + r;
          wings.index.push(p, p + 4, p + 1, p + 1, p + 4, p + 5);
        }
      }
    });
  }
  charRoots(wood, tall * 0.16, 0.42);
  return [
    { name: 'Bark', look: ALIEN_BARK, opaque: true, mesh: wood },
    { name: 'Membrane', look: { color: 'Gen_Wing.png', tint: [1, 1, 1, 1], cutoff: 0.4 }, mesh: wings },
  ];
}

// Chars the wood of `mesh` from the ground up to about `high`, unevenly round the trunk.
function charRoots(mesh, high, floor = 0.26) {
  shade(mesh, (up, y, x, z) => {
    const a = Math.atan2(z, x);
    const top = high * (1 + 0.16 * Math.sin(a * 5) + 0.1 * Math.sin(a * 11 + 1));
    const t = Math.max(0, Math.min(1, (y - top * 0.45) / (top * 0.55)));
    const g = floor + (1 - floor) * t * t * (3 - 2 * t);
    return [g, g * (0.96 + 0.04 * t), g * (0.92 + 0.08 * t)];
  });
}

function mesh3(mesh, x, y, z, side, u, v) {
  mesh.position.push(x, y, z);
  const n = unit([side[0], 0.5, side[1]]);
  mesh.normal.push(n[0], n[1], n[2]);
  mesh.uv.push(u, v);
}

const ALIEN_BARK = { color: 'Conifer_Bark.png', normal: 'Conifer_Bark_Normal.png', tint: [0.46, 0.31, 0.13, 1] };

// A tree of upright limbs rising from a splayed foot, each ending in a shaggy dark puff.
export function puffTree({ across, tall, trunk }, lod, random) {
  const wood = newMesh();
  const crown = newMesh();
  const R = across / 2;
  const a0 = random() * TAU;
  const fork = tall * 0.34;
  sweep(wood, [[0, -0.8, 0], [0, fork * 0.5, 0], [0, fork, 0]], (t) => trunk * (0.72 + 0.28 * (1 - t) + 0.55 * (1 - t) ** 4), Math.max(5, Math.round(12 * lod.seg)), { rib: 0.1, ribs: 5, wraps: 2 });
  foot(wood, trunk * 0.95, lod.seg, a0);
  const limbs = 5;
  for (let k = 0; k < limbs; k++) {
    const a = a0 + (k / limbs) * TAU + random() * 0.4;
    const r = R * (0.42 + random() * 0.32);
    const high = tall * (0.76 + 0.16 * ((k * 3) % limbs) / limbs);
    const at = (t) => [Math.cos(a) * r * t ** 0.8, fork * 0.8 + (high - fork * 0.8) * t, Math.sin(a) * r * t ** 0.8];
    const path = Array.from({ length: 6 }, (_, q) => at(q / 5));
    sweep(wood, path, (t) => trunk * 0.46 * (1 - t * 0.74), 5, { wraps: 1 });
    const puffs = Math.max(4, Math.round(16 * lod.keep));
    for (let c = 0; c < puffs; c++) {
      const t = 0.5 + 0.56 * random();
      const p = at(Math.min(1, t));
      const spread = across * 0.13 * (0.4 + 0.6 * Math.sin(Math.min(1, (t - 0.5) / 0.56) * Math.PI));
      const q = random() * TAU;
      cards(crown, [p[0] + Math.cos(q) * spread * random(), p[1] + (t > 1 ? tall * 0.05 : 0), p[2] + Math.sin(q) * spread * random()], across * 0.2 * lod.grow ** 0.7 * (0.8 + random() * 0.4), random);
    }
  }
  charRoots(wood, tall * 0.2);
  return [
    { name: 'Bark', look: ALIEN_BARK, opaque: true, mesh: wood },
    { name: 'Puffs', look: { color: 'Gen_Shag.png', tint: [1, 1, 1, 1], cutoff: 0.4 }, mesh: crown },
  ];
}

// An alien take on a Joshua tree: a dark trunk swollen like a bulb, forking into upturned arms, each
// carrying a round glossy clump.
export function clumpTree({ across, tall, trunk, leaf = [0.26, 0.5, 0.3, 1] }, lod, random) {
  const wood = newMesh();
  const crown = newMesh();
  const sides = Math.max(5, Math.round(11 * lod.seg));
  const a0 = random() * TAU;
  const fork = tall * 0.3;
  const stem = Array.from({ length: 7 }, (_, k) => [(random() - 0.5) * trunk * 0.1 * (k / 6), -0.8 + (fork + 0.8) * (k / 6), (random() - 0.5) * trunk * 0.1 * (k / 6)]);
  sweep(wood, stem, (t) => trunk * (0.52 + 0.8 * Math.sin(Math.PI * Math.min(1, 0.3 + t * 0.85)) ** 3 * (1 - t * 0.5)), sides, { rib: 0.08, ribs: 6, wraps: 2, perMeter: 0.4 });
  foot(wood, trunk * 0.62, lod.seg, a0);
  const clump = (at, rim) => {
    const count = Math.max(6, Math.round(90 * lod.keep));
    for (let c = 0; c < count; c++) {
      const up = random() * 1.5 - 0.5;
      const a = random() * TAU;
      // Some of the leaves lie further in, so the clump is leaves all through.
      const o = Math.sqrt(Math.max(0, 1 - Math.min(1, up * up))) * rim * (c % 3 === 0 ? 0.55 : 1.04);
      cards(crown, [at[0] + Math.cos(a) * o, at[1] + up * rim * 0.88, at[2] + Math.sin(a) * o], rim * 0.56 * lod.grow ** 0.7, random);
    }
  };
  const arm = (from, dir, long, radius, level) => {
    const up = unit(add(dir, [0, 1, 0], 0.42));
    const mid = add(from, dir, long * 0.5);
    const end = add(mid, up, long * 0.55);
    sweep(wood, [from, mid, end], (t) => radius * (1 - t * 0.28), Math.max(4, sides - 3), { wraps: 1, perMeter: 0.5 });
    if (level === 0) {
      clump(add(end, [0, across * 0.07, 0]), across * (0.12 + random() * 0.05));
      return;
    }
    const forks = level === 2 ? 3 : 2;
    const a1 = random() * TAU;
    for (let k = 0; k < forks; k++) {
      const a = a1 + (k / forks) * TAU;
      arm(end, unit([Math.cos(a), 0.4 + random() * 0.4, Math.sin(a)]), long * (0.72 + random() * 0.14), radius * 0.66, level - 1);
    }
  };
  arm(stem[6], unit([Math.cos(a0) * 0.08, 1, Math.sin(a0) * 0.08]), tall * 0.2, trunk * 0.56, 2);
  return [
    { name: 'Bark', look: { ...ALIEN_BARK, tint: [0.2, 0.09, 0.055, 1] }, opaque: true, mesh: wood },
    { name: 'Leaves', look: { color: 'Leaves_oak.png', tint: leaf, cutoff: 0.3 }, mesh: crown },
  ];
}

// A pod's whole skin by height: furred husk, its zigzag edge, then blotched flesh of `low` to
// `high`, and at the very top `tip`.
function podSkin(seed, low, high, tip) {
  const noise = noiseOf(seed);
  return () => png((u, v) => {
    const up = 1 - v;
    const tooth = Math.abs(((u * 4 + 0.3) % 1) - 0.5) * 2;
    const line = 0.3 + 0.2 * tooth + (noise(u, 0.5) - 0.5) * 0.04;
    if (up < line) {
      const fur = 0.58 + 0.62 * noise(u * 3, v * 0.5) * Math.abs(Math.sin(u * TAU * 46 + noise(u, v) * 7));
      const edge = Math.max(0, 1 - (line - up) / 0.035);
      const g = fur * (1 - 0.82 * edge) * (0.68 + 0.5 * up);
      return [g * 0.42, g * 0.28, g * 0.3, 1];
    }
    // Blotched flesh, split by soft wandering creases, with fine fibres running up it.
    const warp = noise(u * 2 + 0.3, v * 2) * 0.09;
    const blotch = noise(u * 3 + warp, v * 2 + warp);
    const crease = Math.min(1, (Math.abs(noise(u * 2 + warp, v * 2 - warp) - 0.5) * 2) / 0.09);
    const fibre = 0.86 + 0.14 * Math.sin(u * TAU * 24 + noise(u, v) * 7);
    const spot = noise(u * 4, v * 4) > 0.64 ? 0.22 : 0;
    const c = mixed(low, high, Math.min(1, Math.max(0, (blotch - 0.34) * 2.6) + spot));
    const g = (0.2 + 0.8 * crease) * fibre * Math.min(1, Math.max(0.16, (up - line) / 0.035));
    const out = [c[0] * g, c[1] * g, c[2] * g, 1];
    const t = Math.max(0, Math.min(1, (up - 0.84) / 0.08));
    return [mix(out[0], tip[0], t), mix(out[1], tip[1], t), mix(out[2], tip[2], t), 1];
  });
}

PICTURES['Gen_Pod_Crimson.png'] = podSkin(83, [0.22, 0.03, 0.09], [0.72, 0.1, 0.27], [0.33, 0.25, 0.22]);
PICTURES['Gen_Pod_Amber.png'] = podSkin(89, [0.3, 0.2, 0.04], [0.88, 0.5, 0.08], [0.34, 0.46, 0.17]);
PICTURES['Gen_Wing.png'] = () => {
  const noise = noiseOf(97);
  const wander = noiseOf(101);
  return png((u, v) => {
    // A dark web between the arms, that frays below them into wisps: clumps of their own lengths,
    // each thinning and wandering toward its end.
    const reach = 0.46 + 0.72 * noise(u * 8, 0.3) ** 1.2;
    const f = Math.max(0, (v - 0.2) / Math.max(0.05, reach - 0.2));
    const x = u + (wander(u * 3, v * 2) - 0.5) * 0.05 * (0.3 + f);
    const wisp = Math.abs(Math.sin(x * TAU * 37));
    const clump = noise(x * 12, v * 3);
    const hole = v < 0.2 && noise(u * 16, v * 16) > 0.76;
    const gone = hole || f >= 1 || wisp > 1 - f * 0.58 || clump < 0.16 + f * 0.2;
    const g = 0.5 + 1.1 * noise(u * 16, v * 8);
    return [g * 0.1, g * 0.11, g * 0.27, gone ? 0 : 1];
  }, 0.9);
};
PICTURES['Gen_Shag.png'] = () => {
  const noise = noiseOf(103);
  return png((u, v) => {
    const dx = u - 0.5;
    const dy = v - 0.5;
    const a = Math.atan2(dy, dx);
    const r = Math.hypot(dx, dy) * 2;
    const spikes = 0.52 + 0.46 * Math.abs(Math.sin(a * 13 + noise(u, v) * 3)) ** 3 + 0.14 * noise(u * 2, v * 2);
    const strand = Math.abs(Math.sin(a * 41)) > 0.45 || r < 0.32;
    const g = 0.75 + 0.5 * noise(u * 3, v * 3);
    return [g * 0.2, g * 0.2, g * 0.42, r < spikes && strand ? 1 : 0];
  });
};

// A stem through `path`, flared at its foot.
function stemOf(mesh, path, radius, lod, picture = {}) {
  sweep(mesh, path, (t) => radius * (0.7 + 0.8 * (1 - t) ** 5), Math.max(4, Math.round(8 * lod.seg)), { wraps: 1, perMeter: 0.8, ...picture });
}

function curved(from, a, lean, high, rows) {
  return Array.from({ length: rows + 1 }, (_, k) => {
    const t = k / rows;
    return [from[0] + Math.cos(a) * lean * t * t, from[1] + (high - from[1]) * t, from[2] + Math.sin(a) * lean * t * t];
  });
}

// A knobbed stalk carrying an open blossom, and long curling feelers rising from its heart.
export function blossom({ across, tall, petal: picture }, lod, random) {
  const stalk = newMesh();
  const petals = newMesh();
  const feelers = newMesh();
  const a0 = random() * TAU;
  const rows = Math.max(4, Math.round(9 * lod.seg));
  const path = curved([0, -0.3, 0], a0, across * 0.06, tall * 0.68, rows);
  const girth = across * 0.075;
  sweep(stalk, path, (t) => girth * (0.72 + 1.2 * (1 - t) ** 4 + 0.26 * Math.sin(t * 27)), Math.max(5, Math.round(10 * lod.seg)), { wraps: 2, perMeter: 2 });
  const head = path[rows];
  const count = lod.seg > 0.5 ? 6 : 4;
  for (let i = 0; i < count; i++) {
    const a = a0 + (i / count) * TAU + random() * 0.3;
    const long = across * 0.46 * (0.85 + random() * 0.3);
    ribbon(petals, arch(head, a, long, 1.7, 1.05, Math.max(3, rows - 3)), (t) => long * 0.56 * Math.sin(Math.PI * (0.12 + 0.82 * t)), WHOLE, [0, 1, 0], 0.16);
  }
  // Two stout feelers rise near upright from its heart, then hook out and down to a purple point.
  const tips = newMesh();
  const steps = Math.max(6, Math.round(12 * lod.seg));
  for (let i = 0; i < 2; i++) {
    const a = a0 + i * Math.PI + 0.9;
    const reach = across * 0.42;
    const curl = Array.from({ length: steps + 1 }, (_, k) => {
      const t = k / steps;
      const out = reach * (0.08 * t + 0.92 * Math.max(0, (t - 0.45) / 0.55) ** 1.3);
      const up = head[1] + (tall * 1.12 - head[1]) * Math.sin(Math.min(1, t / 0.62) * Math.PI * 0.5) - tall * 0.26 * Math.max(0, (t - 0.68) / 0.32) ** 1.5;
      return [head[0] + Math.cos(a) * out, up, head[2] + Math.sin(a) * out];
    });
    const cut = Math.round(steps * 0.66);
    sweep(feelers, curl.slice(0, cut + 1), (t) => across * 0.034 * (1 - t * 0.45), Math.max(4, Math.round(6 * lod.seg)));
    sweep(tips, curl.slice(cut), (t) => across * 0.034 * 0.55 * (1 - t) + 0.002, Math.max(4, Math.round(6 * lod.seg)));
  }
  return [
    { name: 'Stalk', look: generated('Gen_Stem.png', [0.72, 0.56, 0.1, 1]), opaque: true, mesh: stalk },
    { name: 'Petals', look: { color: picture, tint: [1, 1, 1, 1], cutoff: 0.4 }, mesh: petals },
    { name: 'Feelers', look: generated('Gen_Stem.png', [0.05, 0.045, 0.06, 1]), opaque: true, mesh: feelers },
    { name: 'Tips', look: generated('Gen_Stem.png', [0.36, 0.08, 0.42, 1]), opaque: true, mesh: tips },
  ];
}

// A banded stalk with three great spade-shaped blades hanging from its tip.
export function bladed({ across, tall, leaf, stalkTint = [0.3, 0.26, 0.1, 1] }, lod, random) {
  const stalk = newMesh();
  const blades = newMesh();
  const a0 = random() * TAU;
  const rows = Math.max(3, Math.round(7 * lod.seg));
  const path = curved([0, -0.3, 0], a0, across * 0.12, tall * 0.86, rows);
  sweep(stalk, path, (t) => across * 0.2 * (0.42 + 0.8 * (1 - t) ** 3), Math.max(4, Math.round(8 * lod.seg)), { wraps: 2, perMeter: 1 });
  // The blades meet in a peak over the stalk's tip, hiding it, and hang nearly straight down.
  const head = add(path[rows], [0, tall * 0.13, 0]);
  const leafRows = Math.max(4, Math.round(10 * lod.seg));
  for (let i = 0; i < 3; i++) {
    const a = a0 + i * 2.09 + (random() - 0.5) * 0.5;
    const reach = across * (0.4 + 0.1 * random());
    const drop = tall * (0.72 - i * 0.08);
    const spine = Array.from({ length: leafRows + 1 }, (_, k) => {
      const t = k / leafRows;
      const out = reach * Math.sin(Math.min(1, t * 1.25) * (Math.PI / 2));
      return [head[0] + Math.cos(a) * out, head[1] - drop * t ** 1.3, head[2] + Math.sin(a) * out];
    });
    const wide = across * (1.0 + 0.15 * random());
    ribbon(blades, spine, (t) => wide * (t < 0.38 ? 0.04 + 0.96 * Math.sin((t / 0.38) * (Math.PI / 2)) : ((1 - t) / 0.62) ** 0.85), WHOLE, [Math.cos(a), 0.3, Math.sin(a)]);
  }
  return [
    { name: 'Stalk', look: generated('Gen_PalmBark.png', stalkTint), opaque: true, mesh: stalk },
    { name: 'Blades', look: { color: 'Gen_Mottled.png', tint: leaf, cutoff: 0.4 }, mesh: blades },
  ];
}

// A flat star of spotted paddles in two layers, hugging the ground.
export function star({ across, tall, tint }, lod, random) {
  const crown = newMesh();
  const rows = Math.max(3, Math.round(5 * lod.seg));
  for (const [count, reach, rise, turn] of [[9, 1, 0.35, 0], [7, 0.72, 0.85, 0.4]]) {
    for (let i = 0; i < count; i++) {
      const a = turn + (i / count) * TAU + random() * 0.15;
      const long = (across / 2) * reach * (0.9 + random() * 0.15);
      ribbon(crown, arch([0, -0.05, 0], a, long, rise + ((tall * 0.5) / long) * reach, 0.4, rows), () => long * 0.42, WHOLE, [0, 1, 0], 0.1);
    }
  }
  return [{ name: 'Paddles', look: { color: 'Gen_Paddle.png', tint, cutoff: 0.4, rough: 0.6 }, mesh: crown }];
}

// A soft banded bulb, crowned with a ring of spikes.
export function anemone({ across, tall, tint }, lod, random) {
  const bulb = newMesh();
  const spikes = newMesh();
  const R = across / 2;
  const high = tall * 0.8;
  const s = random() * TAU;
  lathe(bulb, [[0.01, -0.3], [R * 0.74, -0.05], [R, high * 0.3], [R * 0.98, high * 0.66], [R * 0.72, high * 0.92], [R * 0.36, high], [0.01, high]], Math.max(7, Math.round(16 * lod.seg)), (a) => 1 + 0.06 * Math.cos(3 * a + s) + 0.03 * Math.cos(7 * a), (r, a, y) => [a / TAU, Math.max(0.01, Math.min(0.99, 1 - y / high + 0.12 * Math.sin(a * 3 + s) * 0.3))]);
  const count = lod.seg > 0.5 ? 18 : 9;
  for (let k = 0; k < count; k++) {
    const a = (k / count) * TAU + random() * 0.2;
    const r = R * (0.34 + 0.26 * (k % 2));
    const from = [Math.cos(a) * r, high * 0.92, Math.sin(a) * r];
    const to = [Math.cos(a) * r * 1.2, tall * (0.92 + random() * 0.08), Math.sin(a) * r * 1.2];
    sweep(spikes, [from, to], (t) => across * 0.032 * (1 - t) + 0.004, 3);
  }
  return [
    { name: 'Bulb', look: generated('Gen_Bands.png', tint, { rough: 0.45 }), opaque: true, mesh: bulb },
    { name: 'Spikes', look: generated('Gen_Stem.png', tint), opaque: true, mesh: spikes },
  ];
}

// A tangle of thin crooked twigs, in `clumps` clumps, each forking on its way up.
export function tuft({ across, tall, tint, clumps = 1, blades = 70, splay = 0.08 }, lod, random) {
  const twigs = newMesh();
  const each = Math.max(5, Math.round(blades * 2.4 * lod.seg ** 1.4));
  const girth = lod.grow ** 0.8 * Math.max(0.009, tall * 0.0074);
  const rows = lod.seg > 0.6 ? 6 : 3;
  for (let c = 0; c < clumps; c++) {
    const a1 = random() * TAU;
    const off = clumps > 1 ? (across / 2) * 0.68 : 0;
    const ring = (c / clumps) * TAU + a1 * 0.1;
    const at = [Math.cos(ring) * off, -0.12, Math.sin(ring) * off];
    const span = clumps > 1 ? across * 0.11 : across / 2;
    for (let i = 0; i < each; i++) {
      const a = random() * TAU;
      const r = span * Math.sqrt(random()) * 0.76;
      const from = [at[0] + Math.cos(a) * r, -0.12, at[2] + Math.sin(a) * r];
      const high = tall * (0.3 + 0.62 * random() ** 1.5);
      const out = span * (0.05 + splay * (0.5 + random()));
      const path = [from];
      let dx = 0;
      let dz = 0;
      for (let q = 1; q <= rows; q++) {
        const t = q / rows;
        dx += (random() - 0.5) * span * 0.3;
        dz += (random() - 0.5) * span * 0.3;
        path.push([from[0] + Math.cos(a) * out * t * t + dx, from[1] + (high + 0.12) * t, from[2] + Math.sin(a) * out * t * t + dz]);
      }
      sweep(twigs, path, (t) => girth * (1 - t * 0.75), 3, { wraps: 1, perMeter: 2.2 });
      if (lod.seg > 0.6) {
        for (let f = 0; f < 2; f++) {
          const b = random() * TAU;
          const fork = path[1 + Math.floor(random() * (rows - 1))];
          const mid = add(fork, [Math.cos(b), 0.7, Math.sin(b)], tall * (0.05 + 0.08 * random()));
          const tip = add(mid, [Math.cos(b + 0.8), 1.2, Math.sin(b + 0.8)], tall * (0.03 + 0.08 * random()));
          sweep(twigs, [fork, mid, tip], (t) => girth * 0.6 * (1 - t * 0.7), 3, { wraps: 1, perMeter: 2.2 });
        }
      }
    }
  }
  return [{ name: 'Twigs', look: generated('Gen_Stem.png', tint), opaque: true, mesh: twigs }];
}

// A low, shaggy bush of arching ragged fronds, its lowest hanging to the ground.
export function frond({ across, tall, tint = [1, 1, 1, 1], fronds = 42 }, lod, random) {
  const crown = newMesh();
  const core = newMesh();
  const count = Math.max(6, Math.round(fronds * lod.seg));
  const rows = Math.max(2, Math.round(6 * lod.seg));
  for (let i = 0; i < count; i++) {
    const a = (i * 2.4) + random() * 0.5;
    const up = i / (count - 1);
    const from = [Math.cos(a) * across * 0.05, tall * (0.14 + 0.3 * up), Math.sin(a) * across * 0.05];
    const long = (across / 2) * (0.84 + 0.2 * random()) * (1.08 - 0.2 * up);
    ribbon(crown, arch(from, a, long, 0.15 + 0.95 * up + 0.2 * random(), 1 + 0.4 * up, rows), (t) => long * 0.62 * lod.grow ** 0.5 * (1 - 0.2 * t), WHOLE, [0, 1, 0], 0.16);
    if (lod.seg > 0.5) sweep(core, [[from[0] * 0.3, -0.1, from[2] * 0.3], from], () => across * 0.016, 3, { wraps: 1 });
  }
  return [
    { name: 'Fronds', look: { color: 'Gen_Frond.png', tint, cutoff: 0.4 }, mesh: crown },
    { name: 'Core', look: generated('Gen_Stem.png', [0.22, 0.13, 0.08, 1]), opaque: true, mesh: core },
  ];
}

// `parts` laid into `into` by name, moved by `at` and scaled by `scale` about their foot.
function gather(into, parts, at, scale) {
  for (const p of parts) {
    let g = into.find((q) => q.name === p.name);
    if (!g) {
      g = { ...p, mesh: newMesh() };
      into.push(g);
    }
    const base = g.mesh.position.length / 3;
    for (let i = 0; i < p.mesh.position.length; i += 3) {
      g.mesh.position.push(at[0] + p.mesh.position[i] * scale, at[1] + p.mesh.position[i + 1] * scale, at[2] + p.mesh.position[i + 2] * scale);
    }
    g.mesh.normal.push(...p.mesh.normal);
    g.mesh.uv.push(...p.mesh.uv);
    if (p.mesh.color) (g.mesh.color ??= []).push(...p.mesh.color);
    g.mesh.index.push(...p.mesh.index.map((k) => k + base));
  }
  return into;
}

// A fern: fronds of the leaf sheet's fern arching up and out from one crown, the inner ones
// steepest.
export function fern({ across, tall, fronds = 16, tint = [1, 1, 0.82, 1] }, lod, random) {
  const crown = newMesh();
  const count = Math.max(5, Math.round(fronds * lod.seg));
  const rows = Math.max(3, Math.round(7 * lod.seg));
  for (let i = 0; i < count; i++) {
    const a = i * 2.4 + random() * 0.4;
    const inner = 1 - i / count;
    const long = (across / 2) * (0.78 + 0.27 * random());
    const rise = Math.min(4, (tall / long) * (0.55 + 0.85 * inner));
    const droop = 0.5 + 0.6 * (1 - inner);
    ribbon(crown, arch([0, -0.03, 0], a, long, rise, droop, rows), (t) => long * 0.56 * lod.grow ** 0.5 * (0.55 + 0.45 * Math.sin(Math.PI * Math.min(1, t * 1.2))), FERN, [0, 1, 0], 0.14);
  }
  return [{ name: 'Fronds', look: leaves(tint), mesh: crown }];
}

// A clump of `count` ferns over a patch `across` wide, the middle one tallest.
export function ferns({ across, tall, count = 5, tint }, lod, random) {
  const out = [];
  const n = Math.max(2, Math.round(count * (lod.seg > 0.5 ? 1 : 0.6)));
  for (let k = 0; k < n; k++) {
    const a = k * 2.4 + random() * 0.6;
    const r = k === 0 ? 0 : across * (0.18 + 0.2 * random());
    const scale = k === 0 ? 1 : 0.62 + 0.26 * random();
    const one = fern({ across: across * 0.45, tall, tint }, lod, random);
    gather(out, one, [Math.cos(a) * r, 0, Math.sin(a) * r], scale);
  }
  return out;
}

// A few tall stems, each holding one trumpet of `petal` petals, over strap leaves at their foot.
export function lilies({ across, tall, stems = 3, petal: picture }, lod, random) {
  const stalks = newMesh();
  const petals = newMesh();
  const hearts = newMesh();
  const blades = newMesh();
  const rows = Math.max(3, Math.round(8 * lod.seg));
  const sides = Math.max(3, Math.round(6 * lod.seg));
  for (let s = 0; s < stems; s++) {
    const a = s * 2.2 + random() * 0.8;
    const high = tall * (0.78 + 0.18 * random()) * (s === 0 ? 1 : 0.88);
    const lean = across * (0.18 + 0.12 * random());
    const path = curved([Math.cos(a) * across * 0.04, -0.1, Math.sin(a) * across * 0.04], a, lean, high, rows);
    sweep(stalks, path, (t) => across * 0.022 * (1.2 - 0.5 * t), sides, { wraps: 1, perMeter: 3 });
    // The trumpet opens up and out, its six petals curling back at their tips.
    const head = path[rows];
    const face = a + 0.3;
    const count = lod.seg > 0.5 ? 6 : 4;
    for (let i = 0; i < count; i++) {
      const b = face + (i / count) * TAU;
      const long = across * (0.24 + 0.05 * random());
      ribbon(petals, arch(head, b, long, 1.15, 1.25, Math.max(3, rows - 3)), (t) => long * 0.42 * Math.sin(Math.PI * (0.1 + 0.85 * t)), WHOLE, [0, 1, 0], 0.18);
    }
    if (lod.seg > 0.4) {
      for (let i = 0; i < 4; i++) {
        const b = face + i * 1.6;
        const tip = add(head, [Math.cos(b) * across * 0.05, across * 0.16, Math.sin(b) * across * 0.05]);
        sweep(hearts, [head, tip], () => across * 0.006, 3);
      }
    }
  }
  const leafCount = Math.max(4, Math.round(9 * lod.seg));
  for (let i = 0; i < leafCount; i++) {
    const a = i * 2.4 + random() * 0.5;
    const long = tall * (0.32 + 0.16 * random());
    ribbon(blades, arch([0, -0.05, 0], a, long, 1.6, 1.1, Math.max(3, rows - 2)), (t) => long * 0.13 * (1 - t * 0.8), LONG, [0, 1, 0]);
  }
  return [
    { name: 'Stalks', look: generated('Gen_Stem.png', [0.22, 0.46, 0.16, 1]), opaque: true, mesh: stalks },
    { name: 'Petals', look: { color: picture, tint: [1, 1, 1, 1], cutoff: 0.4 }, mesh: petals },
    { name: 'Hearts', look: generated('Gen_Stem.png', [0.9, 0.72, 0.2, 1]), opaque: true, mesh: hearts },
    { name: 'Leaves', look: leaves([0.36, 0.6, 0.3, 1]), mesh: blades },
  ];
}

// A lupin's spike: a stalk thick with small `petal` flowers over its upper part, smaller toward
// the tip, from a ring of fingered leaves at its foot.
export function spike({ across, tall, petal: picture }, lod, random) {
  const stalk = newMesh();
  const florets = newMesh();
  const blades = newMesh();
  const a0 = random() * TAU;
  const rows = Math.max(4, Math.round(10 * lod.seg));
  const path = curved([0, -0.1, 0], a0, across * 0.08, tall, rows);
  sweep(stalk, path, (t) => across * 0.05 * (1.3 - 0.8 * t), Math.max(3, Math.round(6 * lod.seg)), { wraps: 1, perMeter: 3 });
  // Whorls of florets from a quarter of the way up to near the tip.
  const whorls = Math.max(6, Math.round(28 * lod.seg));
  for (let w = 0; w < whorls; w++) {
    const t = 0.25 + 0.72 * (w / (whorls - 1));
    const k = t * rows;
    const lo = path[Math.floor(k)];
    const hi = path[Math.min(rows, Math.ceil(k))];
    const f = k - Math.floor(k);
    const at = [lo[0] + (hi[0] - lo[0]) * f, lo[1] + (hi[1] - lo[1]) * f, lo[2] + (hi[2] - lo[2]) * f];
    const size = across * 0.34 * (1.2 - 0.85 * (t - 0.25) / 0.72) * (0.85 + 0.3 * random());
    const around = lod.seg > 0.5 ? 6 : 4;
    for (let i = 0; i < around; i++) {
      const b = a0 + w * 0.7 + (i / around) * TAU + (random() - 0.5) * 0.6;
      ribbon(florets, arch(at, b, size, 0.7, 0.8, 2), (u) => size * 0.95 * Math.sin(Math.PI * (0.15 + 0.8 * u)), WHOLE, [0, 1, 0], 0.22);
    }
  }
  // Fingered leaves lying out from the foot, each a fan of narrow leaflets.
  const fans = Math.max(3, Math.round(6 * lod.seg));
  for (let i = 0; i < fans; i++) {
    const a = a0 + (i / fans) * TAU + random() * 0.4;
    const reach = across * (0.32 + 0.1 * random());
    const at = [Math.cos(a) * reach * 0.6, tall * 0.08, Math.sin(a) * reach * 0.6];
    sweep(stalk, [[0, -0.02, 0], at], () => across * 0.012, 3);
    const fingers = lod.seg > 0.5 ? 7 : 4;
    for (let j = 0; j < fingers; j++) {
      const b = a + (j - (fingers - 1) / 2) * 0.42;
      const long = reach * 0.55;
      ribbon(blades, arch(at, b, long, 0.25, 0.6, 3), (t) => long * 0.24 * Math.sin(Math.PI * (0.08 + 0.84 * t)), LONG, [0, 1, 0]);
    }
  }
  return [
    { name: 'Stalk', look: generated('Gen_Stem.png', [0.26, 0.42, 0.18, 1]), opaque: true, mesh: stalk },
    { name: 'Florets', look: { color: picture, tint: [1, 1, 1, 1], cutoff: 0.4 }, mesh: florets },
    { name: 'Leaves', look: leaves([0.3, 0.52, 0.26, 1]), mesh: blades },
  ];
}

// A bed of embers lying `rise` over its foot: a shallow mound heaped with lumps of coal. Its
// colour's alpha marks it to the shader, which glows it from the picture's red.
export function emberBed({ across, rise, tall = 0.12 }, lod, random) {
  const bed = newMesh();
  const R = across / 2;
  const sides = Math.max(8, Math.round(22 * lod.seg));
  const uvOf = (r, a) => [0.5 + (0.48 * r * Math.cos(a)) / R, 0.5 + (0.48 * r * Math.sin(a)) / R];
  lathe(bed, [[R, rise - 0.02], [R * 0.75, rise + tall * 0.55], [R * 0.4, rise + tall * 0.9], [0.01, rise + tall]], sides, () => 1, uvOf);
  const lumps = Math.max(8, Math.round(70 * lod.seg ** 1.5));
  for (let i = 0; i < lumps; i++) {
    const a = random() * TAU;
    const r = R * 0.92 * Math.sqrt(random());
    const y = rise + tall * (1 - (r / R) ** 2) * 0.8;
    const size = R * (0.07 + random() * 0.09);
    const c = [Math.cos(a) * r, y, Math.sin(a) * r];
    nodule(bed, c, size, random);
  }
  return [{ name: 'Embers', look: generated('Gen_Ember.png', [1, 1, 1, 0.25]), opaque: true, mesh: bed }];
}

// A low heap of straw: a rough mound, and loose strands lying over it and spilling round its foot.
export function hayPile({ across, tall, tint = [0.78, 0.62, 0.36, 1] }, lod, random) {
  const mound = newMesh();
  const straw = newMesh();
  const R = across / 2;
  const a0 = random() * TAU;
  const bulge = (a) => 0.84 + 0.1 * Math.sin(a * 3 + a0) + 0.07 * Math.sin(a * 7 + a0 * 2);
  const high = (r) => tall * Math.max(0, 1 - (r / R) ** 1.8) ** 0.75;
  const sides = Math.max(8, Math.round(26 * lod.seg));
  lathe(mound, [[R * 0.98, -0.03], [R * 0.86, high(R * 0.86)], [R * 0.66, high(R * 0.66)], [R * 0.4, high(R * 0.4)], [R * 0.16, high(R * 0.16)], [0.01, tall]], sides, bulge, (r, a) => [0.5 + (0.48 * r * Math.cos(a)) / R, 0.5 + (0.48 * r * Math.sin(a)) / R]);
  const strands = Math.max(24, Math.round(1100 * lod.seg ** 1.5));
  const girth = Math.max(0.005, 0.0065 * lod.grow);
  for (let i = 0; i < strands; i++) {
    const a = random() * TAU;
    // Most lie on the heap, a few spill onto the floor round it.
    const spill = random() < 0.16;
    const r = spill ? R * (0.92 + random() * 0.28) : R * bulge(a) * Math.sqrt(random()) * 0.96;
    const y = spill ? 0.012 : high(r / bulge(a)) * 0.98;
    const from = [Math.cos(a) * r, y, Math.sin(a) * r];
    const turn = a + (random() - 0.5) * 2.6 + (random() < 0.5 ? 1.57 : -1.57);
    const long = 0.12 + random() * 0.34;
    const lift = spill ? random() * 0.02 : (random() - 0.2) * 0.1;
    const mid = add(from, [Math.cos(turn), lift, Math.sin(turn)], long * 0.5);
    const tip = add(mid, [Math.cos(turn + (random() - 0.5)), lift - 0.25, Math.sin(turn + (random() - 0.5))], long * 0.5);
    tip[1] = Math.max(tip[1], 0.006);
    sweep(straw, [from, mid, tip], (t) => girth * (1 - t * 0.6), 3, { wraps: 1, perMeter: 2 });
  }
  const tone = noiseOf(211);
  shade(straw, (up, y, x, z) => {
    const g = 0.55 + 0.9 * tone(x * 1.7 + 0.5, z * 1.7 + 0.5);
    return [g, g * (0.96 + 0.1 * tone(z * 3, x * 3)), g * 0.86];
  });
  return [
    { name: 'Heap', look: generated('Gen_Straw.png', [tint[0] * 0.62, tint[1] * 0.62, tint[2] * 0.62, 1]), opaque: true, mesh: mound },
    { name: 'Straw', look: generated('Gen_Straw.png', tint), opaque: true, mesh: straw },
  ];
}

// A small warty lump added to `mesh` at `at`.
function nodule(mesh, at, r, random = () => 0.5) {
  const from = mesh.position.length;
  const w = random() * TAU;
  lathe(mesh, [[0.01, -r], [r * 0.9, -r * 0.5], [r, r * 0.1], [r * 0.72, r * 0.72], [0.01, r * 0.92]], 7, (a) => 0.84 + 0.2 * Math.sin(a * 3 + w), (x, a, y) => [(a / TAU) * 2, 0.5 + (0.5 * y) / r]);
  moved(mesh, from, at);
}

const NODULE = generated('Gen_Wart.png', [1, 1, 1, 1]);
const DARK_STEM = generated('Gen_Blue_Stem.png', [1, 1, 1, 1]);

// A crooked, knobbled blue-black stem with a long ridged pink bud on top, warts round its neck.
export function budStalk({ across, tall }, lod, random) {
  const stem = newMesh();
  const bud = newMesh();
  const knots = newMesh();
  const a0 = random() * TAU;
  const rows = Math.max(4, Math.round(11 * lod.seg));
  const neck = tall * 0.63;
  const bow = across * 0.24;
  const path = Array.from({ length: rows + 1 }, (_, k) => {
    const t = k / rows;
    const off = bow * Math.sin(t * Math.PI * 1.35) + (k && k < rows ? (random() - 0.5) * across * 0.05 : 0);
    return [Math.cos(a0) * off, -0.25 + (neck + 0.25) * t, Math.sin(a0) * off];
  });
  sweep(stem, path, (t) => across * 0.21 * (0.82 + 0.75 * (1 - t) ** 7 + 0.15 * Math.sin(t * 27) + 0.09 * Math.sin(t * 61)), Math.max(5, Math.round(9 * lod.seg)), { wraps: 2, perMeter: 1.2, rib: 0.17, ribs: 4 });
  const head = path[rows];
  const lean = a0 + 2.2;
  const long = tall * 0.39;
  const budRows = Math.max(4, Math.round(9 * lod.seg));
  const spine = Array.from({ length: budRows }, (_, k) => {
    const t = k / (budRows - 1);
    return [head[0] + Math.cos(lean) * across * 0.34 * t * t, head[1] - tall * 0.015 + long * t, head[2] + Math.sin(lean) * across * 0.34 * t * t];
  });
  const R = across * 0.43;
  sweep(bud, spine, (t) => 0.004 + R * Math.sin(Math.PI * (0.06 + 0.94 * t) ** 0.6) ** 0.9 * (1 - t * 0.12), Math.max(5, Math.round(8 * lod.seg)), { wraps: 1, perMeter: 1 / long, rib: 0.13, ribs: 5, facet: lod.seg > 0.6 });
  if (lod.seg > 0.4) {
    const warts = Math.round(8 * lod.seg);
    for (let k = 0; k < warts; k++) {
      const a = a0 + k * 2.4;
      const out = across * (0.26 + 0.13 * random());
      nodule(knots, [head[0] + Math.cos(a) * out, head[1] - tall * 0.03 + (random() - 0.5) * across * 0.34, head[2] + Math.sin(a) * out], across * (0.1 + 0.07 * random()), random);
    }
  }
  return [
    { name: 'Stem', look: DARK_STEM, opaque: true, mesh: stem },
    { name: 'Bud', look: generated('Gen_Bud.png', [1, 1, 1, 1]), opaque: true, mesh: bud },
    { name: 'Nodules', look: NODULE, opaque: true, mesh: knots },
  ];
}

// A twisted blue-black stem under a flat bat-wing web: pale ribs out to five uneven points with a
// clutch of warts on each, the skin slack and scooped between them.
export function webbed({ across, tall }, lod, random) {
  const stem = newMesh();
  const web = newMesh();
  const ribs = newMesh();
  const knots = newMesh();
  const R = across / 2;
  const a0 = random() * TAU;
  const top = tall * 0.95;
  const droop = Math.min(R * 0.42, tall * 0.34);
  const rows = Math.max(4, Math.round(9 * lod.seg));
  const path = Array.from({ length: rows + 1 }, (_, k) => {
    const t = k / rows;
    const off = across * 0.055 * Math.sin(t * Math.PI);
    return [Math.cos(a0) * off, -0.25 + (top + 0.25) * t, Math.sin(a0) * off];
  });
  sweep(stem, path, (t) => across * 0.058 * (0.86 + 0.8 * (1 - t) ** 6 + 0.1 * Math.sin(t * 25)), Math.max(5, Math.round(9 * lod.seg)), { wraps: 2, perMeter: 1.2, rib: 0.16, ribs: 4 });
  const points = 5;
  const tips = Array.from({ length: points }, (_, k) => ({ a: a0 + ((k + (random() - 0.5) * 0.3) / points) * TAU, long: R * (0.84 + 0.2 * random()) }));
  const on = (tip, r) => [Math.cos(tip.a) * tip.long * r, top - droop * r ** 1.35, Math.sin(tip.a) * tip.long * r];
  const rings = lod.seg > 0.6 ? 4 : 2;
  const planar = (p) => [0.5 + (0.48 * p[0]) / R, 0.5 + (0.48 * p[2]) / R];
  tips.forEach((tip, k) => {
    const next = tips[(k + 1) % points];
    const grid = [];
    for (let q = 0; q <= rings; q++) {
      const r = q / rings;
      const a = on(tip, r);
      const b = on(next, r);
      // The edge between two points scoops well in, the skin sagging as it goes.
      const m = add(add(a, b, 1).map((c) => c / 2), [0, 0, 0], 0);
      const pull = 1 - 0.46 * r ** 2.2;
      grid.push([a, [m[0] * pull, top - droop * (r * pull) ** 1.35 - droop * 0.14 * r, m[2] * pull], b]);
    }
    for (let q = 0; q < rings; q++) {
      for (let c = 0; c < 2; c++) {
        const quad = [grid[q][c], grid[q + 1][c], grid[q][c + 1], grid[q + 1][c + 1]];
        // Each panel is flat, for an angular, leathery surface.
        // Across its corners, as a panel at the hub has one edge of no length.
        const n = unit(cross(add(quad[2], quad[1], -1), add(quad[3], quad[0], -1)));
        const up = n[1] < 0 ? n.map((v) => -v) : n;
        const base = web.position.length / 3;
        for (const p of quad) {
          web.position.push(...p);
          web.normal.push(...up);
          web.uv.push(...planar(p));
        }
        web.index.push(base, base + 2, base + 1, base + 2, base + 3, base + 1);
      }
    }
    if (lod.seg > 0.3) {
      const line = Array.from({ length: 5 }, (_, q) => add(on(tip, q / 4), [0, across * 0.012, 0], 1));
      sweep(ribs, line, (t) => across * 0.022 * (1 - t * 0.6), 4, { wraps: 1 });
    }
    if (lod.seg > 0.4) {
      const at = on(tip, 1);
      for (let n = 0; n < 4; n++) {
        const b = random() * TAU;
        nodule(knots, add(at, [Math.cos(b), (random() - 0.6) * 0.8, Math.sin(b)], across * 0.036 * (n ? 1 : 0)), across * (0.024 + 0.018 * random()), random);
      }
    }
  });
  if (lod.seg > 0.4) nodule(knots, [0, top + across * 0.01, 0], across * 0.04, random);
  return [
    { name: 'Stem', look: DARK_STEM, opaque: true, mesh: stem },
    { name: 'Web', look: { color: 'Gen_Web.png', tint: [1, 1, 1, 1], normal: 'Gen_Grit_Normal.png', cutoff: 0.4 }, mesh: web },
    { name: 'Ribs', look: generated('Gen_Stem.png', [0.86, 0.6, 0.62, 1]), opaque: true, mesh: ribs },
    { name: 'Nodules', look: NODULE, opaque: true, mesh: knots },
  ];
}

PICTURES['Gen_Pod_Green.png'] = podSkin(107, [0.05, 0.12, 0.04], [0.3, 0.42, 0.1], [0.26, 0.3, 0.14]);
PICTURES['Gen_Petal_Orange.png'] = petal([0.75, 0.5, 0.1], [0.95, 0.58, 0.08], 109);
PICTURES['Gen_Petal_Red.png'] = petal([0.75, 0.25, 0.06], [0.9, 0.2, 0.05], 113);
PICTURES['Gen_Petal_Purple.png'] = petal([0.38, 0.14, 0.72], [0.56, 0.22, 0.95], 127);
PICTURES['Gen_Bands.png'] = () => {
  const noise = noiseOf(149);
  return png((u, v) => {
    const b = 0.5 + 0.5 * Math.sin(v * TAU * 3.5 + noise(u, v) * 3);
    const g = 0.42 + 0.58 * b ** 0.8;
    const s = b ** 3 * 0.7;
    return [mix(g, 1, s), mix(g, 1, s), mix(g, 1, s), 1];
  });
};
PICTURES['Gen_Web.png'] = () => {
  const noise = noiseOf(151);
  const blot = noiseOf(157);
  return png((u, v) => {
    const dx = u - 0.5;
    const dy = v - 0.5;
    const a = Math.atan2(dy, dx) + (noise(u, v) - 0.5) * 0.3;
    const r = Math.hypot(dx, dy) * 2;
    // Leathery skin, blotched dark and pale, with fine veins running out from the hub and a few
    // torn pinholes toward its edge.
    const vein = Math.abs(Math.sin(a * 17)) < 0.09 + 0.07 * blot(u * 3, v * 3);
    const cross = Math.abs(Math.sin(r * 33 + noise(u * 2, v * 2) * 6)) < 0.05;
    const patch = blot(u * 2, v * 2) * 0.6 + blot(u * 8, v * 8) * 0.4;
    const g = 0.42 + 1.12 * Math.max(0, patch - 0.2);
    let c = [g * 0.66, g * 0.4, g * 0.44];
    if (vein) c = c.map((x) => x * 0.56);
    if (cross) c = [c[0] * 1.22 + 0.05, c[1] * 1.2 + 0.05, c[2] * 1.2 + 0.05];
    const torn = r > 0.62 && blot(u * 16, v * 16) > 0.74;
    return [c[0], c[1], c[2], torn ? 0 : 1];
  }, 0.85);
};
PICTURES['Gen_Ember.png'] = () => {
  const noise = noiseOf(233);
  return png((u, v) => {
    const crack = 1 - Math.abs(2 * noise(u * 9, v * 9) - 1);
    const fine = 1 - Math.abs(2 * noise(u * 23 + 3, v * 23 + 5) - 1);
    const patch = noise(u * 3 + 7, v * 3 + 1);
    const heat = Math.min(1, 0.16 + 0.75 * crack ** 5 + 0.35 * fine ** 8 + 0.4 * patch ** 3);
    return [heat, heat * 0.2, heat * 0.05, 1];
  }, 0.75);
};
PICTURES['Gen_Straw.png'] = () => {
  const noise = noiseOf(223);
  return png((u, v) => {
    const a = noise(u * 2, v * 2) * 9;
    const x = u * Math.cos(a) + v * Math.sin(a);
    const fibre = 0.5 + 0.5 * Math.sin(x * TAU * 60 + noise(u * 8, v * 8) * 8);
    const g = 0.42 + 0.72 * fibre ** 1.6 + 0.22 * noise(u * 16, v * 16);
    return [g, g * 0.97, g * 0.84, 1];
  }, 0.75);
};
PICTURES['Gen_Bud.png'] = () => {
  const noise = noiseOf(173);
  const blot = noiseOf(179);
  return png((u, v) => {
    const flow = noise(u * 2, v * 2) * 4;
    const streak = blot(u * 16, v * 2 + flow * 0.1);
    const crease = Math.abs(Math.sin(u * TAU * 2.5 + flow * 0.5)) < 0.1;
    const patch = blot(u * 4, v * 4);
    const g = (0.38 + 0.62 * streak ** 1.4 + 0.4 * patch) * (crease ? 0.6 : 1);
    const pale = Math.max(0, (v - 0.84) / 0.16);
    return [g * 0.52 + pale * 0.4, g * 0.27 + pale * 0.42, g * 0.33 + pale * 0.38, 1];
  }, 0.85);
};
PICTURES['Gen_Blue_Stem.png'] = () => {
  const noise = noiseOf(181);
  return png((u, v) => {
    const fibre = noise(u * 24 + noise(u, v) * 0.3, v * 2);
    const streak = fibre > 0.62 ? (fibre - 0.62) * 3.2 : 0;
    const g = 0.5 + 0.9 * noise(u * 8, v * 8);
    return [g * 0.06 + streak * 0.3, g * 0.075 + streak * 0.34, g * 0.2 + streak * 0.62, 1];
  }, 0.8);
};
PICTURES['Gen_Wart.png'] = () => {
  const noise = noiseOf(191);
  return png((u, v) => {
    const n = noise(u * 8, v * 8);
    const pit = noise(u * 16, v * 16) < 0.38;
    const g = (0.3 + 1.0 * n ** 1.3) * (pit ? 0.34 : 1);
    return [g * 0.2, g * 0.38, g * 0.17, 1];
  }, 0.85);
};
// A ragged frond: a dark stalk and barbs of their own lengths, pale strands among dark.
PICTURES['Gen_Frond.png'] = () => {
  const noise = noiseOf(193);
  const random = seeded(197);
  const lengths = Float32Array.from({ length: 64 }, () => 0.55 + 0.5 * random());
  const shades = Float32Array.from({ length: 64 }, () => random());
  return png((u, v) => {
    const up = 1 - v;
    const off = Math.abs(u - 0.5) * 2;
    const at = up - off * 0.32 + (noise(u, v) - 0.5) * 0.015;
    const b = (Math.floor(at * 64) % 64 + 64) % 64;
    const across = (at * 64) % 1;
    const half = Math.sin(Math.PI * Math.min(1, 0.04 + up * 0.97) ** 0.55) * lengths[b];
    const thin = 0.12 + 0.62 * off;
    const gap = (u < 0.5 ? across : (across + 0.5) % 1) < thin * 0.82;
    if (off < 0.06) return [0.2, 0.12, 0.08, up < 0.97 ? 1 : 0];
    const pale = shades[b] > 0.66;
    const g = (pale ? 0.72 : 0.2 + 0.2 * shades[b]) * (0.6 + 0.8 * noise(u * 8, v * 8));
    return [g * 0.74, g * 0.48, g * 0.33, off < half && !gap ? 1 : 0];
  }, 0.75);
};
// A broad pointed leaf, dark and heavily mottled, with a pale rib and veins.
PICTURES['Gen_Mottled.png'] = () => {
  const noise = noiseOf(163);
  return png((u, v) => {
    const up = 1 - v;
    const off = Math.abs(u - 0.5);
    const half = 0.5 * Math.sin(Math.PI * Math.min(1, 0.05 + up * 0.95) ** 0.72) ** 0.55 - 0.018 * Math.abs(Math.sin(up * TAU * 14));
    const rib = off < 0.022;
    const vein = Math.abs(Math.sin((up - off * 0.9) * TAU * 7)) < 0.09;
    const patch = noise(u * 2 + off, v * 3);
    const pale = patch > 0.56 ? 0.8 : patch < 0.42 ? 0 : 0.28;
    const g = 0.28 + 0.72 * pale;
    const light = rib ? 1 : vein ? g + 0.32 : g;
    return [light, light, light * 0.82, off < half ? 1 : 0];
  }, 0.8);
};

// A pod's relief: creases and swellings that catch the light.
function podHeight(u, v, noise) {
  const fibre = Math.sin(u * TAU * 24 + noise(u, v) * 7) * 0.05;
  const crease = Math.min(1, (Math.abs(noise(u * 2, v * 2) - 0.5) * 2) / 0.09);
  return noise(u * 3, v * 3) * 0.75 + crease * 0.32 + fibre;
}
PICTURES['Gen_Grit_Normal.png'] = () => {
  const e = 1 / 512;
  return png((u, v) => {
    const dx = GRAIN(u + e, v) - GRAIN(u - e, v);
    const dy = GRAIN(u, v + e) - GRAIN(u, v - e);
    const n = unit([-dx * 16, dy * 16, 1]);
    return [n[0] * 0.5 + 0.5, n[1] * 0.5 + 0.5, n[2] * 0.5 + 0.5, 1];
  }, 0);
};
PICTURES['Gen_Pod_Normal.png'] = () => {
  const noise = noiseOf(157);
  const e = 1 / 256;
  return png((u, v) => {
    const dx = podHeight(u + e, v, noise) - podHeight(u - e, v, noise);
    const dy = podHeight(u, v + e, noise) - podHeight(u, v - e, noise);
    const pit = GRAIN(u + e, v) - GRAIN(u - e, v);
    const pit2 = GRAIN(u, v + e) - GRAIN(u, v - e);
    const n = unit([-dx * 7 - pit * 5, dy * 7 + pit2 * 5, 1]);
    return [n[0] * 0.5 + 0.5, n[1] * 0.5 + 0.5, n[2] * 0.5 + 0.5, 1];
  }, 0);
};

// A trunk leaning as `lean` turns it, forking at `fork` of its height into `lobes` limbs, each
// crowned by a dome of long strands of narrow leaves hanging toward the ground.
export function weeper({ across, tall, trunk, bark, leaves: look, lobes = 2, fork = 0.36, hang = 0.42 }, lod, random) {
  const wood = newMesh();
  const crown = newMesh();
  const a0 = random() * TAU;
  const sides = Math.max(5, Math.round(12 * lod.seg));
  const split = [Math.cos(a0) * across * 0.04, tall * fork, Math.sin(a0) * across * 0.04];
  sweep(wood, [[0, -0.8, 0], [split[0] * 0.3, tall * fork * 0.5, split[2] * 0.3], split], flared(trunk, 0.7), sides, { wraps: 2 });
  foot(wood, trunk, lod.seg, a0);
  const rows = Math.max(3, Math.round(7 * lod.seg));
  for (let k = 0; k < lobes; k++) {
    const a = a0 + Math.PI / 2 + (k / lobes) * TAU + (random() - 0.5) * 0.4;
    const out = across * (0.24 + random() * 0.05);
    const rise = tall * (0.72 + random() * 0.08);
    const rim = across * (0.22 + random() * 0.04);
    const head = [split[0] + Math.cos(a) * out, rise, split[2] + Math.sin(a) * out];
    const bend = [split[0] + Math.cos(a) * out * 0.45, tall * (fork + 0.18), split[2] + Math.sin(a) * out * 0.45];
    sweep(wood, [split, bend, head], (t) => trunk * 0.62 * (1 - t * 0.6), Math.max(4, sides - 3), { wraps: 2 });
    limbs(wood, { count: 5, from: rise - rim * 0.2, to: rise, reach: rim * 0.9, trunk: trunk * 0.35, lift: 0.4, random, sides: 4, head: [head[0], 0, head[2]] });
    // The strands: hung from the dome's upper surface, falling outward and down.
    const count = Math.max(14, Math.round(280 * lod.keep));
    for (let c = 0; c < count; c++) {
      const up = random() * 1.5 - 0.5;
      const q = random() * TAU;
      const side = Math.sqrt(Math.max(0, 1 - up * up));
      const from = [head[0] + Math.cos(q) * side * rim, head[1] + up * rim * 0.7, head[2] + Math.sin(q) * side * rim];
      const long = tall * hang * (0.45 + 0.55 * random()) * (0.4 + 0.6 * side);
      const outward = rim * (0.12 + 0.3 * side);
      const spine = Array.from({ length: rows + 1 }, (_, s) => {
        const t = s / rows;
        return [from[0] + Math.cos(q) * outward * Math.sin(t * 1.4), from[1] + rim * 0.12 * Math.sin(t * Math.PI) - long * t * t, from[2] + Math.sin(q) * outward * Math.sin(t * 1.4)];
      });
      ribbon(crown, spine, (t) => across * 0.05 * lod.grow ** 0.6 * (0.7 + 0.3 * Math.sin(Math.PI * Math.min(1, t + 0.2))), WHOLE, [Math.cos(q), 0, Math.sin(q)], 0.05);
    }
  }
  return [
    { name: 'Bark', look: bark, opaque: true, mesh: wood },
    { name: 'Leaves', look, mesh: crown },
  ];
}

// A strand of narrow leaves along a thin stem, the leaves angled toward its free end at the top.
PICTURES['Gen_Willow.png'] = () => {
  const noise = noiseOf(211);
  const random = seeded(223);
  const tilts = Float32Array.from({ length: 40 }, () => 0.42 + 0.26 * random());
  const lengths = Float32Array.from({ length: 40 }, () => 0.3 + 0.16 * random());
  const shades = Float32Array.from({ length: 40 }, () => random());
  const gap = 1 / 18;
  return png((u, v) => {
    const off = u - 0.5;
    if (Math.abs(off) < 0.012 && v > 0.03) return [0.34, 0.42, 0.18, 1];
    const side = off < 0 ? 0 : 1;
    for (let k = Math.floor(v / gap) - 1; k <= Math.floor(v / gap) + 9; k++) {
      const i = ((k * 2 + side) % 40 + 40) % 40;
      const base = k * gap + side * gap * 0.5;
      const a = tilts[i];
      // Along the leaf from its foot on the stem, and across it.
      const dx = Math.abs(off);
      const dy = base - v;
      const s = dx * Math.sin(a) + dy * Math.cos(a);
      const w = dx * Math.cos(a) - dy * Math.sin(a);
      const len = lengths[i];
      if (s < 0 || s > len) continue;
      const half = 0.05 * Math.sin(Math.PI * Math.min(1, s / len)) ** 0.8;
      if (Math.abs(w) > half) continue;
      const rib = Math.abs(w) < 0.005 ? 0.16 : 0;
      const g = (0.6 + 0.3 * shades[i]) * (0.82 + 0.36 * noise(u * 4, v * 4)) + rib;
      return [g * 0.62, g * 0.82, g * 0.36, 1];
    }
    return [0.3, 0.4, 0.16, 0];
  }, 0.5);
};

// `from`'s triangles added to `into`, moved by `by`.
function merge(into, from, by) {
  const base = into.position.length / 3;
  for (let i = 0; i < from.position.length; i += 3) into.position.push(from.position[i] + by[0], from.position[i + 1] + by[1], from.position[i + 2] + by[2]);
  into.normal.push(...from.normal);
  into.uv.push(...from.uv);
  into.index.push(...from.index.map((k) => k + base));
}

// A short trunk under a dense round crown that comes low, with fruit hung on its surface.
export function fruitTree({ across, tall, trunk, bark, leaves: look, fruit = 32, size = 0.15, low = 0.24, leafy = 1, mass: solid = true }, lod, random) {
  const wood = newMesh();
  const crown = newMesh();
  const mass = newMesh();
  const apples = newMesh();
  const s = random() * TAU;
  const rim = across * 0.46;
  const y = tall * (1 + low) / 2;
  const high = tall * (1 - low) / 2;
  sweep(wood, [[0, -0.8, 0], [0, tall * 0.22, 0], [0, tall * 0.5, 0]], flared(trunk), Math.max(5, Math.round(12 * lod.seg)), { wraps: 2 });
  foot(wood, trunk, lod.seg, s);
  limbs(wood, { count: 7, from: tall * 0.3, to: tall * 0.5, reach: rim * 0.85, trunk, lift: 0.6, random });
  // A crown of a few overlapping lobes, so it does not read as one ball.
  const lobes = [[0, high * 0.15, 0, 0.72]];
  for (let k = 0; k < 5; k++) {
    const q = s + k * 1.26 + random() * 0.5;
    lobes.push([Math.cos(q) * rim * 0.5, (random() - 0.45) * high * 0.7, Math.sin(q) * rim * 0.5, 0.5 + random() * 0.14]);
  }
  for (const [x, dy, z, k] of lobes) {
    const part = newMesh();
    // A sparser crown has a smaller mass inside, so the sky shows through its edge.
    // `mass: false` leaves out the solid mass inside, so no ball shows through the leaves.
    if (solid) leafMass(part, rim * 0.82 * k * (0.3 + 0.7 * leafy), y + dy, high * 0.8 * k * (0.3 + 0.7 * leafy), s + x);
    for (let i = 0; i < part.position.length; i += 3) {
      part.position[i] += x;
      part.position[i + 2] += z;
    }
    merge(mass, part, [0, 0, 0]);
    const cardsHere = newMesh();
    shellCards(cardsHere, { rim: rim * 0.86 * k, y: y + dy, high: high * 0.86 * k, floor: tall * low, size: across * 0.11, count: Math.round(620 * k * leafy), lod, random });
    merge(crown, cardsHere, [x, 0, z]);
  }
  // Fruit hangs on a lobe's leafy surface, where no other lobe covers it, and never under the crown.
  const shell = lobes.map(([x, dy, z, k]) => [x, y + dy, z, rim * 0.86 * k, high * 0.86 * k]);
  const inside = (p, [x, cy, z, r, h]) => ((p[0] - x) / r) ** 2 + ((p[1] - cy) / h) ** 2 + ((p[2] - z) / r) ** 2 < 0.92;
  const count = Math.round(fruit * lod.keep);
  const sides = lod.seg > 0.5 ? 7 : 5;
  for (let c = 0, tries = 0; c < count && tries < count * 20; tries++) {
    const [x, cy, z, lr, lh] = shell[Math.floor(random() * shell.length)];
    const up = random() * 1.1 - 0.6;
    const q = random() * TAU;
    const out = Math.sqrt(Math.max(0, 1 - up * up));
    const at = [x + Math.cos(q) * out * lr * 1.01, cy + up * lh * 1.01, z + Math.sin(q) * out * lr * 1.01];
    if (at[1] < tall * low + lh * 0.25 || shell.some((o) => o[0] !== x && inside(at, o))) continue;
    c++;
    const r = size * (0.85 + random() * 0.3);
    const from = apples.position.length / 3;
    lathe(apples, [[0.01, -r * 0.9], [r * 0.8, -r * 0.6], [r, 0], [r * 0.85, r * 0.6], [0.01, r * 0.75]], sides, () => 1, (rr, a, h) => [a / TAU, 0.5 - h / (r * 2.2)]);
    for (let i = from * 3; i < apples.position.length; i += 3) {
      apples.position[i] += at[0];
      apples.position[i + 1] += at[1];
      apples.position[i + 2] += at[2];
    }
  }
  return [
    { name: 'Mass', look: massLook(look), opaque: true, mesh: mass },
    { name: 'Bark', look: bark, opaque: true, mesh: wood },
    { name: 'Leaves', look, mesh: crown },
    { name: 'Fruit', look: generated('Gen_Apple.png', [1, 1, 1, 1], { rough: 0.55 }), opaque: true, mesh: apples },
  ];
}

// An apple's skin: red, blushed and streaked, paler toward its foot, with fine pale dots.
PICTURES['Gen_Apple.png'] = () => {
  const noise = noiseOf(227);
  return png((u, v) => {
    const streak = noise(u * 6, v * 0.8);
    const blush = Math.min(1, Math.max(0, (v - 0.55) * 2.4 + (noise(u * 2, v) - 0.5)));
    const dot = noise(u * 32, v * 32) > 0.8 ? 0.18 : 0;
    const r = 0.62 + 0.2 * streak;
    return [mix(r, 0.82, blush * 0.5) + dot, mix(0.08 + 0.06 * streak, 0.62, blush) + dot, mix(0.06, 0.18, blush) + dot * 0.6, 1];
  }, 0.3);
};

// A thin trunk lifting flat pads of broad leaves in tiers, the lowest spreading widest.
export function tiers({ across, tall, trunk, bark, leaves: look, levels = 3 }, lod, random) {
  const wood = newMesh();
  const crown = newMesh();
  const a0 = random() * TAU;
  const sides = Math.max(5, Math.round(12 * lod.seg));
  const rings = Math.max(4, Math.round(8 * lod.seg));
  const lean = [Math.cos(a0) * across * 0.02, 0, Math.sin(a0) * across * 0.02];
  const points = Array.from({ length: rings + 1 }, (_, k) => {
    const t = k / rings;
    return [lean[0] * t * t, -0.8 + (tall * 0.86 + 0.8) * t, lean[2] * t * t];
  });
  sweep(wood, points, flared(trunk, 0.8), sides, { wraps: 2 });
  foot(wood, trunk, lod.seg, a0);
  const rows = Math.max(3, Math.round(6 * lod.seg));
  // A pad: a flattened disc of crossed broad-leaf cards, its rim drooping a little.
  const pad = (centre, reach, leaves) => {
    const count = Math.max(6, Math.round(leaves * lod.keep));
    for (let i = 0; i < count; i++) {
      const a = random() * TAU;
      const r = reach * Math.sqrt(random());
      const y = centre[1] - (r / reach) ** 2 * reach * 0.22 + (random() - 0.5) * reach * 0.14;
      cards(crown, [centre[0] + Math.cos(a) * r, y, centre[2] + Math.sin(a) * r], reach * 0.42 * lod.grow ** 0.8 * (0.8 + random() * 0.4), random);
    }
  };
  // Each tier a ring of limbs ending in pads, under a pad at the top.
  for (let level = 0; level < levels; level++) {
    const f = level / Math.max(1, levels - 1);
    const y = tall * (0.62 + 0.3 * f);
    const reach = (across / 2) * (0.92 - 0.42 * f);
    const limbsHere = Math.max(3, Math.round((7 - level * 2) * Math.max(0.6, lod.seg)));
    for (let k = 0; k < limbsHere; k++) {
      const a = a0 + (k / limbsHere) * TAU + level * 0.7 + random() * 0.5;
      const long = reach * (0.62 + 0.3 * random());
      // The limb leaves the trunk a little under its pad.
      const from = points[Math.min(rings, Math.round((rings * (y - tall * 0.1 + 0.8)) / (tall * 0.86 + 0.8)))];
      const end = [from[0] + Math.cos(a) * long, y + tall * 0.04 * random(), from[2] + Math.sin(a) * long];
      const mid = [(from[0] + end[0]) / 2, Math.max(from[1], end[1]) + tall * 0.03, (from[2] + end[2]) / 2];
      sweep(wood, [from, mid, end], (t) => trunk * 0.38 * (1 - t * 0.7), Math.max(4, sides - 5));
      pad(end, across * (0.17 - 0.04 * f), 30);
    }
  }
  pad(points[rings], across * 0.17, 36);
  return [
    { name: 'Bark', look: bark, opaque: true, mesh: wood },
    { name: 'Leaves', look, mesh: crown },
  ];
}

// A broad leaf: oval to a drawn-out point, with a pale midrib and paired veins.
PICTURES['Gen_BroadLeaf.png'] = () => {
  const noise = noiseOf(229);
  return png((u, v) => {
    const up = 1 - v;
    const off = Math.abs(u - 0.5);
    const half = 0.48 * Math.sin(Math.PI * Math.min(1, 0.02 + up * 0.98) ** 0.75) ** 0.9;
    const rib = off < 0.014;
    const vein = Math.abs(((up - off * 1.1) * 11) % 1 - 0.5) < 0.05 && off < half * 0.9;
    const g = (0.72 + 0.3 * noise(u * 3, v * 3)) * (vein ? 1.14 : 1) * (1 - 0.18 * (off / 0.5));
    if (rib) return [0.8, 0.86, 0.52, up < 0.98 ? 1 : 0];
    return [g * 0.56, g * 0.76, g * 0.32, off < half ? 1 : 0];
  }, 0.4);
};

// A tiny upright evergreen: a few narrow columns of dark needles.
export function sprig({ across, tall, leaves: look, columns = 3 }, lod, random) {
  const crown = newMesh();
  const wood = newMesh();
  const count = Math.max(2, Math.round(columns * Math.max(lod.keep, 0.6)));
  for (let k = 0; k < count; k++) {
    const a = random() * TAU;
    const r = across * 0.22 * (k === 0 ? 0 : 0.6 + 0.4 * random());
    const high = tall * (k === 0 ? 1 : 0.72 + 0.22 * random());
    const at = [Math.cos(a) * r, 0, Math.sin(a) * r];
    const spine = Array.from({ length: 5 }, (_, s) => [at[0] * (1 + s * 0.06), -0.04 + (high + 0.04) * (s / 4), at[2] * (1 + s * 0.06)]);
    sweep(wood, spine, (t) => across * 0.035 * (1 - t * 0.8), 4);
    for (const q of [0, Math.PI / 2]) {
      const face = [Math.cos(a + q), 0, Math.sin(a + q)];
      ribbon(crown, spine, (t) => across * 0.42 * (0.55 + 0.45 * Math.sin(Math.PI * (0.15 + 0.7 * t))), WHOLE, face, 0.1);
    }
  }
  return [
    { name: 'Stem', look: BARK, opaque: true, mesh: wood },
    { name: 'Needles', look, mesh: crown },
  ];
}

// A swollen, ribbed body like a gourd, throwing out knobbed tendrils that arch up and fall back to
// curl near the ground, with a few small leaves along them.
export function vine({ across, tall, trunk, arms = 7, bark, leaf = [0.32, 0.08, 0.05, 1] }, lod, random) {
  const wood = newMesh();
  const crown = newMesh();
  const a0 = random() * TAU;
  const sides = Math.max(6, Math.round(14 * lod.seg));
  // A tall ribbed body, its arms from its upper half, as retail's stump is.
  const body = tall * 0.55;
  const profile = [[0.01, -0.6], [trunk * 1.6, -0.5], [trunk * 1.9, body * 0.1], [trunk * 1.75, body * 0.4], [trunk * 1.4, body * 0.72], [trunk * 1.0, body * 0.92], [trunk * 0.6, body]];
  const ribs = (a) => 1 + 0.12 * Math.abs(Math.cos(3.5 * a + a0)) - 0.06;
  lathe(wood, profile, sides, ribs, (r, a, y) => [(a / TAU) * 3, y / 2.2]);
  const rows = Math.max(5, Math.round(12 * lod.seg));
  for (let k = 0; k < arms; k++) {
    const a = a0 + (k / arms) * TAU + (random() - 0.5) * 0.5;
    const reach = (across / 2) * (0.7 + random() * 0.25);
    const top = tall * (0.82 + random() * 0.18);
    const twist = (random() - 0.5) * 1.2;
    const from = [Math.cos(a) * trunk * 1.2, body * (0.55 + 0.4 * random()), Math.sin(a) * trunk * 1.2];
    const path = Array.from({ length: rows + 1 }, (_, s) => {
      const t = s / rows;
      const turn = a + twist * t;
      const r = reach * Math.sin(t * Math.PI * 0.5) ** 0.6;
      // Up and out, over the top, then down to a curl near the ground.
      const h = from[1] + (top - from[1]) * Math.sin(Math.min(1, t * 1.6) * Math.PI * 0.5) - (top - tall * 0.66) * Math.max(0, (t - 0.6) / 0.4) ** 1.6;
      const curl = t > 0.85 ? (t - 0.85) / 0.15 : 0;
      return [Math.cos(turn) * r - Math.cos(turn) * reach * 0.12 * curl, h + reach * 0.08 * curl, Math.sin(turn) * r - Math.sin(turn) * reach * 0.12 * curl];
    });
    // Knobbed: the radius swells at each joint.
    sweep(wood, path, (t) => trunk * 0.7 * (1 - t * 0.75) * (1 + 0.28 * Math.max(0, Math.sin(t * Math.PI * 9)) ** 3) + 0.01, Math.max(4, sides - 6), { rib: 0.06, ribs: 4, wraps: 1 });
    const count = Math.round(6 * lod.keep);
    for (let c = 0; c < count; c++) {
      const p = path[2 + Math.floor(random() * (rows - 3))];
      cards(crown, [p[0], p[1] + across * 0.01, p[2]], across * 0.07 * lod.grow ** 0.7, random);
    }
  }
  const parts = [{ name: 'Bark', look: bark, opaque: true, mesh: wood }];
  if (crown.index.length) parts.push({ name: 'Leaves', look: { color: 'Leaves_oak.png', tint: leaf, cutoff: 0.3 }, mesh: crown });
  return parts;
}

// A dead tree or bush, bare to the twigs, its colour all in its bark's tint. `stems` above 1 makes a
// bush of stems from the ground; `level` grows its limbs near level from all up the trunk, as a dead
// pine's are; `lean` tips the trunk; `snapped` breaks its top; `moss` lays clumps on its limbs.
export function deadwood({ across, tall, trunk, bark, stems = 1, depth = 3, level = false, lean = 0, toward, uprooted = 0, snapped = false, moss = 0, limbs: count = 7, mossLook }, lod, random) {
  const wood = newMesh();
  const tufts = newMesh();
  const soil = newMesh();
  const turn = random() * TAU;
  // `toward` fixes the way it leans, as an angle from glTF's x toward its z: 0 falls east.
  const a0 = toward ?? turn;
  const sides = Math.max(5, Math.round(11 * lod.seg));
  const deep = Math.max(1, depth - (lod.seg < 0.5 ? 2 : lod.seg < 0.9 ? 1 : 0));
  const twig = (from, dir, long, radius, d) => {
    const path = [from];
    let at = from;
    let w = dir;
    for (let s = 0; s < 3; s++) {
      w = unit(add(w, [(random() - 0.5) * 0.55, 0.06, (random() - 0.5) * 0.55]));
      at = add(at, w, long / 3);
      path.push(at);
    }
    sweep(wood, path, (t) => radius * (1 - t * 0.6) + 0.006, d >= deep - 1 ? 3 : Math.max(3, Math.round(sides * 0.5)), { wraps: 1 });
    if (moss && d <= 1 && random() < moss) {
      const p = path[1 + Math.floor(random() * 2)];
      for (let c = 0; c < 3; c++) cards(tufts, [p[0] + (random() - 0.5) * long * 0.2, p[1] + radius * 1.5, p[2] + (random() - 0.5) * long * 0.2], Math.max(0.35, long * 0.32) * lod.grow ** 0.6, random);
    }
    if (d >= deep) return;
    const forks = d === 0 ? 3 : 2 + (random() < 0.5 ? 1 : 0);
    for (let f = 0; f < forks; f++) {
      const a = random() * TAU;
      const p = path[1 + Math.min(2, Math.floor(random() * 3))];
      twig(p, unit(add(w, [Math.cos(a), level ? 0.05 : 0.45, Math.sin(a)], 0.9)), long * 0.58, radius * 0.55, d + 1);
    }
  };
  for (let st = 0; st < stems; st++) {
    const b = a0 + (st / stems) * TAU;
    const spread = stems > 1 ? across * 0.08 : 0;
    const tip = snapped ? 0.82 : 1;
    const rings = Math.max(4, Math.round(9 * lod.seg));
    // An uprooted tree stands on its root plate, tipped with it: the plate's low edge stays buried.
    const lift = uprooted && st === 0 ? Math.max(0, (uprooted * lean) / Math.hypot(1, lean) - 0.25) : 0;
    const high = tall * (stems > 1 ? 0.5 : level ? 0.95 : 0.55) * tip - lift;
    const points = Array.from({ length: rings + 1 }, (_, k) => {
      const t = k / rings;
      const off = (uprooted ? lean * high * t : lean * high * t ** 1.3) + spread * t;
      const y = uprooted ? lift - uprooted * 0.2 * (1 - t) ** 3 + high * t : -0.8 + (high + 0.8) * t;
      return [Math.cos(b) * off + (random() - 0.5) * trunk * 0.25 * t, y, Math.sin(b) * off + (random() - 0.5) * trunk * 0.25 * t];
    });
    const r = stems > 1 ? trunk : trunk;
    const stemR = (t) => r * ((1 - t) * (snapped ? 0.55 : 0.82) + (snapped ? 0.42 : 0.12)) + r * 0.45 * (1 - t) ** 6;
    sweep(wood, points, stemR, sides, { rib: 0.05, ribs: 7, wraps: 2 });
    if (snapped) {
      // The jagged break at its top.
      const top = points[rings];
      for (let k = 0; k < 4; k++) {
        const q = b + k * 1.7;
        sweep(wood, [top, [top[0] + Math.cos(q) * r * 0.25, top[1] + tall * (0.04 + random() * 0.07), top[2] + Math.sin(q) * r * 0.25]], (t) => r * 0.3 * (1 - t) + 0.01, 3);
      }
    }
    if (st === 0 && uprooted) rootPlate(wood, soil, [0, lift, 0], unit([Math.cos(b) * lean, 1, Math.sin(b) * lean]), b, uprooted, trunk, lod, random);
    else if (st === 0) foot(wood, trunk * 0.95, lod.seg, a0);
    const per = Math.max(3, Math.round(count * Math.max(lod.keep, 0.5)));
    for (let k = 0; k < per; k++) {
      const a = b + k * 2.4 + random() * 0.6;
      const t = level ? 0.28 + 0.7 * (k / per) : stems > 1 ? 0.35 + 0.6 * (k / per) : 0.55 + 0.45 * (k / per);
      const from = points[Math.min(rings, Math.round(rings * t))];
      const up = level ? 0.08 + random() * 0.18 : 0.6 + random() * 0.6;
      const dir = unit([Math.cos(a), up, Math.sin(a)]);
      const reach = (across / 2) * (level ? 1.05 - 0.6 * t : 0.6 + 0.25 * random());
      twig(from, dir, reach / Math.max(0.3, Math.hypot(dir[0], dir[2])) * (level ? 0.7 : 0.62), r * (level ? 0.22 : 0.36), 0);
    }
  }
  const parts = [{ name: 'Wood', look: bark, opaque: true, mesh: wood }];
  if (soil.index.length) parts.push({ name: 'Soil', look: { ...bark, tint: [0.3, 0.22, 0.15, 1] }, opaque: true, mesh: soil });
  if (tufts.index.length) parts.push({ name: 'Moss', look: mossLook ?? { color: 'Gen_Moss.png', tint: [1, 1, 1, 1], cutoff: 0.4 }, mesh: tufts });
  return parts;
}

// The root plate of a tree that has fallen over, centred at `c` and tipped square to the trunk's
// foot `d`: a ball of earth under it and torn roots fanning out of the trunk over it, `R` across.
function rootPlate(wood, soil, c, d, b, R, trunk, lod, random) {
  const level = [Math.cos(b), 0, Math.sin(b)];
  const e1 = unit(add(level, d, -dot(level, d)));
  const e2 = cross(d, e1);
  const at = (a, out, up) => add(add(c, add([0, 0, 0].map((_, i) => Math.cos(a) * e1[i] + Math.sin(a) * e2[i]), [0, 0, 0], 0), out), d, up);
  const ball = [[-0.3, 0.15], [-0.22, 0.6], [-0.1, 0.84], [0.02, 0.9], [0.1, 0.62]].map(([up, r]) => [add(c, d, up * R), r * R]);
  ball.push([add(c, d, trunk * 0.9), trunk * 0.95]);
  const rs = ball.map((q) => q[1]);
  const radius = (t) => {
    const x = t * (rs.length - 1);
    const k = Math.min(rs.length - 2, Math.floor(x));
    return rs[k] + (rs[k + 1] - rs[k]) * (x - k);
  };
  sweep(soil, ball.map((q) => q[0]), radius, Math.max(7, Math.round(15 * lod.seg)), { rib: 0.16, ribs: 7, wraps: Math.max(2, Math.round((TAU * R * 0.8) / 3.4)) });
  const n = Math.max(5, Math.round(10 * lod.seg));
  const sides = Math.max(4, Math.round(7 * lod.seg));
  for (let k = 0; k < n; k++) {
    const a = (k / n) * TAU + (random() - 0.5) * 0.5;
    const reach = R * (0.85 + random() * 0.35);
    const path = [0, 0.25, 0.5, 0.75, 1].map((s) => at(a + (random() - 0.5) * 0.15 * s, s === 0 ? trunk * 0.5 : trunk * 0.4 + s * reach, s === 0 ? trunk * 1.2 : trunk * 0.3 - R * 0.14 * s * s + (random() - 0.5) * trunk * 0.3 * s));
    sweep(wood, path, (t) => trunk * (0.48 * (1 - t) ** 1.5 + 0.07), sides, { wraps: 1 });
    if (lod.seg >= 0.5) {
      const from = path[2];
      const s = random() < 0.5 ? -1 : 1;
      const twig = [0, 0.5, 1].map((q) => add(add(from, [0, 0, 0].map((_, i) => (Math.cos(a + s * 0.7) * e1[i] + Math.sin(a + s * 0.7) * e2[i]) * q * reach * 0.35), 1), d, -R * 0.12 * q));
      sweep(wood, twig, (t) => trunk * (0.16 * (1 - t) + 0.04), 3, { wraps: 1 });
    }
  }
}

// A clump of moss seen from the side: a ragged dark mass, its fringe hanging in wisps.
PICTURES['Gen_Moss.png'] = () => {
  const noise = noiseOf(233);
  return png((u, v) => {
    const dx = u - 0.5;
    const dy = v - 0.42;
    const r = Math.hypot(dx * 1.1, dy * (dy > 0 ? 0.7 : 1.4)) * 2;
    const edge = 0.62 + 0.3 * noise(u * 4, v * 4) + (dy > 0 ? 0.25 * Math.abs(Math.sin(u * TAU * 9 + noise(u, v) * 4)) : 0);
    const g = 0.55 + 0.6 * noise(u * 8, v * 8);
    return [g * 0.3, g * 0.34, g * 0.13, r < edge ? 1 : 0];
  }, 0.7);
};

// A short trunk bent and twisted, carrying dense flat pads of leaves at several heights, the lowest
// reaching out furthest.
// heading turns the trunk's lean to match retail's collision (radians in the model's x, z plane).
export function bonsai({ across, tall, trunk, bark, leaves: look, pads = 7, lean = 0.24, flat = false, heading }, lod, random) {
  const wood = newMesh();
  const crown = newMesh();
  const turned = random() * TAU;
  const a0 = heading ?? turned;
  const rings = Math.max(4, Math.round(9 * lod.seg));
  const sides = Math.max(5, Math.round(12 * lod.seg));
  const top = tall * 0.58;
  const points = Array.from({ length: rings + 1 }, (_, k) => {
    const t = k / rings;
    const off = across * lean * Math.sin(t * Math.PI * 0.85);
    const turn = a0 + t * 1.2;
    return [Math.cos(turn) * off, -0.8 + (top + 0.8) * t, Math.sin(turn) * off];
  });
  const centre = (y) => {
    const k = Math.min(rings - 1e-6, Math.max(0, (rings * (y + 0.8)) / (top + 0.8)));
    const i = Math.floor(k), f = k - i;
    return [points[i][0] + (points[i + 1][0] - points[i][0]) * f, points[i][2] + (points[i + 1][2] - points[i][2]) * f];
  };
  // The trunk stands on the model's middle where it meets the ground.
  const [gx, gz] = centre(0);
  for (const p of points) {
    p[0] -= gx;
    p[2] -= gz;
  }
  sweep(wood, points, flared(trunk, 0.8), sides, { wraps: 2, rib: 0.06, ribs: 5 });
  foot(wood, trunk, lod.seg, a0);
  const at = (y) => points[Math.min(rings, Math.max(0, Math.round((rings * (y + 0.8)) / (top + 0.8))))];
  for (let k = 0; k < pads; k++) {
    const f = k / Math.max(1, pads - 1);
    const b = a0 + k * 2.4 + random() * 0.5;
    const y = tall * (0.32 + 0.6 * f);
    const out = across * (0.3 - 0.16 * f) * (0.8 + 0.3 * random());
    const from = at(Math.min(top, y - tall * 0.12));
    const centre = [from[0] + Math.cos(b) * out, y, from[2] + Math.sin(b) * out];
    sweep(wood, [from, [(from[0] + centre[0]) / 2, (from[1] + centre[1]) / 2 + tall * 0.03, (from[2] + centre[2]) / 2], centre], (t) => trunk * 0.4 * (1 - t * 0.6), Math.max(4, sides - 5));
    const pad = newMesh();
    const rim = across * (0.24 - 0.08 * f);
    if (flat) {
      // A thin layer of leaves lying near level, its rim dipping a little.
      const count = Math.round(420 * (1 - 0.35 * f) * lod.keep);
      for (let c = 0; c < count; c++) {
        const a = random() * TAU;
        const r = rim * Math.sqrt(random());
        const edge = (r / rim) ** 2;
        tilted(pad, [Math.cos(a) * r, -tall * 0.06 * edge + (random() - 0.5) * tall * 0.05, Math.sin(a) * r], across * 0.1 * lod.grow ** 0.8 * (0.8 + random() * 0.4), random, -0.1 - 0.4 * edge, 0.2);
      }
    } else {
      shellCards(pad, { rim, y: 0, high: tall * 0.08, floor: -tall * 0.06, size: across * 0.09, count: Math.round(300 * (1 - 0.35 * f)), lod, random });
    }
    merge(crown, pad, centre);
  }
  return [
    { name: 'Bark', look: bark, opaque: true, mesh: wood },
    { name: 'Leaves', look, mesh: crown },
  ];
}

// A pruned palm's trunk: the stubs of cut fronds in crossing rows, dark in the clefts between them.
PICTURES['Gen_PalmPruned.png'] = () => {
  const noise = noiseOf(239);
  return png((u, v) => {
    const a = (((u * 4 + v * 9) % 1) + 1) % 1;
    const b = (((u * 4 - v * 9) % 1) + 1) % 1;
    const cleft = Math.min(Math.abs(a - 0.5), Math.abs(b - 0.5)) * 2;
    const stub = Math.min(1, cleft * 3.2) ** 0.7;
    const g = (0.22 + 0.7 * stub) * (0.8 + 0.4 * noise(u * 3, v * 3));
    return [g * 0.86, g * 0.8, g * 0.68, 1];
  });
};
