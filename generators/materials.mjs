// New pictures for the buildings' most-seen retail materials, worked out from code alone: no retail
// pixel goes into them, only each material's average colour, written down below. Each field gives,
// for a point of a repeating square: its relief `h` (0 a crevice, 1 proud), its brightness against
// the material's colour `tone`, and optionally its own `colour`.
import fs from 'node:fs';
import path from 'node:path';
import { png, noiseOf, GRAIN, SIZE } from './shapes.mjs';

const hex = (s) => [1, 3, 5].map((k) => parseInt(s.slice(k, k + 2), 16) / 255);
const smooth = (a, b, x) => {
  const t = Math.max(0, Math.min(1, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};
const hash = (a, b, seed) => {
  let h = Math.imul(a + 1, 73856093) ^ Math.imul(b + 1, 19349663) ^ Math.imul(seed + 1, 83492791);
  h ^= h >>> 13;
  h = Math.imul(h, 0x5bd1e995);
  h ^= h >>> 15;
  return (h >>> 0) / 2 ** 32;
};

// Courses of dressed stone or brick: `rows` courses of `cols`, each course offset, the joints
// wandering a little, each block its own shade.
function blocks({ rows, cols, joint = 0.0035, bevel = 0.01, vary = 0.5, seed = 1, deep = 0.42, wander = 0.34 }) {
  const n = noiseOf(seed);
  // Courses of uneven height, and in each, stones of uneven width.
  const tops = [0];
  for (let r = 1; r < rows; r++) tops.push((r + (hash(r, 91, seed) - 0.5) * wander) / rows);
  tops.push(1);
  const seams = tops.slice(0, rows).map((_, r) => {
    const shift = hash(r, 53, seed);
    return Array.from({ length: cols }, (_, c) => (c + shift + (hash(c, r, seed + 3) - 0.5) * wander * 1.6) / cols);
  });
  return (u, v) => {
    const wu = u + (n(u * 3, v * 3) - 0.5) * 0.018;
    const wv = v + (n(v * 3 + 0.4, u * 3) - 0.5) * 0.012;
    const y = ((wv % 1) + 1) % 1;
    let r = rows - 1;
    while (r > 0 && y < tops[r]) r--;
    const x = ((wu % 1) + 1) % 1;
    let c = cols - 1;
    let left = 9;
    let right = 9;
    for (let k = 0; k < cols; k++) {
      const a0 = seams[r][k] % 1;
      const d0 = (x - a0 + 1) % 1;
      if (d0 < left) {
        left = d0;
        c = k;
      }
      const d1 = (a0 - x + 1) % 1;
      if (d1 < right) right = d1;
    }
    const dx = Math.min(left, right);
    const dy = Math.min(y - tops[r], tops[r + 1] - y);
    const shade = hash(c, r, seed);
    // Rounded and chipped corners, by the stone.
    const d = Math.min(dx, dy) - Math.max(0, Math.hypot(Math.max(0, 0.016 - dx), Math.max(0, 0.016 - dy)) - 0.016);
    const chipped = d - n(u * 4 + shade, v * 4) * 0.006;
    const stone = smooth(joint, joint + bevel, chipped);
    const pit = n(u * 4 + shade * 3, v * 4);
    const blotch = n(u * 2 - shade, v * 2 + shade);
    return {
      h: stone * (0.5 + 0.3 * shade + 0.34 * pit + 0.1 * blotch),
      tone: (deep + (1 - deep) * stone) * (1 - vary / 2 + vary * shade) * (0.72 + 0.56 * blotch) * (0.82 + 0.36 * pit),
      rough: 0.92,
    };
  };
}

// Boards `count` to a square, along its width or its height, their ends meeting here and there.
function planks({ count, upright = false, ends = 2, seed = 2, diagonal = false }) {
  const n = noiseOf(seed);
  return (u0, v0) => {
    let [u, v] = upright ? [v0, u0] : [u0, v0];
    if (diagonal) [u, v] = [(((u0 + v0) % 1) + 1) % 1, (((v0 - u0) % 1) + 1) % 1];
    const y = v * count;
    const r = Math.floor(y);
    const x = ((u * ends + hash(r, 7, seed)) % ends + ends) % ends;
    const c = Math.floor(x);
    const fy = y - r;
    const dy = Math.min(fy, 1 - fy) / count;
    const dx = Math.min(x - c, c + 1 - x) / ends;
    const edge = smooth(0.003, 0.012, Math.min(dx, dy));
    const shade = hash(c, r, seed);
    const off = shade * 9;
    const grain = Math.sin((y + n(u * 2 + off, v * 4) * 1.6) * 62);
    const rings = n(u * 0.5 + off, v * 8);
    return {
      h: edge * (0.72 + 0.1 * grain + 0.2 * rings),
      tone: (0.32 + 0.68 * edge) * (0.68 + 0.5 * shade) * (0.86 + 0.14 * grain) * (0.72 + 0.56 * rings),
      rough: 0.8,
    };
  };
}

// Overlapping curved roof tiles, seen with their lower lips toward the foot of the picture.
function roofTiles({ rows, cols, seed = 3 }) {
  const n = noiseOf(seed);
  return (u, v) => {
    const y = v * rows;
    const r = Math.floor(y);
    const x = ((u * cols + (r % 2) * 0.5) % cols + cols) % cols;
    const c = Math.floor(x);
    const fx = x - c - 0.5;
    const fy = y - r;
    const round = Math.sqrt(Math.max(0, 1 - (2 * fx) ** 2));
    // Each tile rises from under the one above and casts its lip over the one below.
    const bottom = 1 - 0.22 * (2 * fx) ** 2;
    const below = fy > bottom;
    const rise = below ? 0.08 : 0.35 + 0.65 * fy;
    const lip = below ? 0.5 : smooth(bottom, bottom - 0.05, fy);
    const under = below ? 0.26 : smooth(0, 0.16, fy);
    const shade = hash(c, r, seed);
    const moss = n(u * 2, v * 2);
    return {
      h: round * rise * lip + 0.02,
      tone: (0.32 + 0.82 * round) * (0.4 + 0.6 * under) * (0.58 + 0.72 * shade) * (0.72 + 0.56 * moss),
      rough: 0.62,
    };
  };
}

// Rough render, its trowel marks and hairline cracks showing.
function plaster({ seed = 4, cracks = true }) {
  const n = noiseOf(seed);
  return (u, v) => {
    const a = n(u, v);
    const b = n(u * 3 + 0.3, v * 3);
    const trowel = n(u * 2 + a, v * 0.5);
    const crack = cracks ? smooth(0.0015, 0.006, Math.abs(n(u * 2 + b * 0.05, v * 2) - 0.5)) : 1;
    return {
      h: (0.5 * a + 0.36 * b + 0.2 * trowel) * (0.72 + 0.28 * crack),
      tone: (0.72 + 0.3 * a + 0.18 * trowel) * (0.68 + 0.32 * crack),
      rough: 0.95,
    };
  };
}

// Irregular laid stones with mortar between, repeating.
function flags({ count = 7, seed = 5, joint = 0.03, mortar = 0.45 }) {
  const n = noiseOf(seed);
  const at = [];
  for (let j = 0; j < count; j++) {
    for (let i = 0; i < count; i++) at.push([(i + hash(i, j, seed)) / count, (j + hash(j, i, seed + 1)) / count]);
  }
  return (u, v) => {
    const wu = u + (n(u * 2, v * 2) - 0.5) * 0.03;
    const wv = v + (n(v * 2, u * 2) - 0.5) * 0.03;
    let d1 = 9;
    let d2 = 9;
    let id = 0;
    const ci = Math.floor(wu * count);
    const cj = Math.floor(wv * count);
    for (let j = cj - 2; j <= cj + 2; j++) {
      for (let i = ci - 2; i <= ci + 2; i++) {
        const k = ((j % count) + count) % count * count + ((i % count) + count) % count;
        const dx = at[k][0] + Math.floor(i / count) - wu;
        const dy = at[k][1] + Math.floor(j / count) - wv;
        const d = Math.hypot(dx, dy);
        if (d < d1) {
          d2 = d1;
          d1 = d;
          id = k;
        } else if (d < d2) {
          d2 = d;
        }
      }
    }
    const edge = smooth(joint * 0.5, joint * 1.5, d2 - d1);
    const shade = hash(id, 3, seed);
    const pit = n(u * 3 + shade, v * 3);
    return {
      h: edge * (0.6 + 0.3 * shade + 0.3 * pit) * (1 - 0.35 * d1 * count * 0.4),
      tone: (mortar + (1 - mortar) * edge) * (0.68 + 0.6 * shade) * (0.74 + 0.52 * pit),
      rough: 0.85,
    };
  };
}

// Layers of straw, hanging in overlapping courses.
function thatch({ rows = 3, seed = 6 }) {
  const n = noiseOf(seed);
  return (u, v) => {
    const y = v * rows;
    const fy = y - Math.floor(y);
    const r = Math.floor(y);
    const strand = Math.abs(Math.sin((u + r * 0.37 + n(u, v) * 0.03) * Math.PI * 70));
    const coarse = n(u * 4 + r, v * 0.5);
    const shadow = 0.32 + 0.68 * smooth(0, 0.42, fy);
    return {
      h: (0.28 + 0.5 * strand + 0.22 * coarse) * (0.4 + 0.6 * fy),
      tone: shadow * (0.5 + 0.6 * strand) * (0.68 + 0.6 * coarse),
      rough: 0.95,
    };
  };
}

// A timber frame round a panel, as retail's framed walls lay theirs out, with a brace across it
// where `brace` asks.
function framed({ inner, panel, wood, border = 0.09, brace = false, width = 0.055, bars = 0, seed = 7 }) {
  const woodX = planks({ count: 1, ends: 1, seed: seed + 1 });
  const woodY = planks({ count: 1, upright: true, ends: 1, seed: seed + 2 });
  const beam = (grain, u, v, shape) => {
    const f = grain(u, v);
    return { h: 0.82 + 0.18 * f.h * shape, tone: f.tone * (0.55 + 0.45 * shape), colour: wood, rough: 0.72 };
  };
  return (u, v) => {
    const dx = Math.min(u, 1 - u);
    const dy = Math.min(v, 1 - v);
    if (Math.min(dx, dy) < border) {
      const shape = smooth(0, 0.028, border - Math.min(dx, dy)) * smooth(0, 0.016, Math.min(dx, dy));
      return dx < dy ? beam(woodY, u, v * 3, 0.5 + 0.5 * shape) : beam(woodX, u * 3, v, 0.5 + 0.5 * shape);
    }
    if (brace) {
      const a = Math.abs(u - v) / Math.SQRT2;
      const b = Math.abs(u + v - 1) / Math.SQRT2;
      const d = Math.min(a, b);
      if (d < width) {
        const shape = smooth(0, 0.016, width - d);
        return { ...beam(woodX, u + v, u - v, 0.5 + 0.5 * shape), h: 0.72 + 0.14 * shape };
      }
    }
    if (bars) {
      const y = (v - border) / (1 - 2 * border);
      const seam = Math.abs(((y * bars) % 1) - 0.5);
      if (seam > 0.485) return { h: 0.28, tone: 0.5, colour: panel, rough: 0.92 };
    }
    const f = inner(u, v);
    // The panel sits back from its frame, and darkens toward it.
    const edge = smooth(0, 0.04, Math.min(dx, dy) - border);
    return { h: f.h * 0.5 * edge, tone: f.tone * (0.55 + 0.45 * edge), colour: panel, rough: f.rough };
  };
}

// Every material: its retail picture or pictures, its colour, and how it is made.
const STONE = (rows, cols, seed, extra = {}) => blocks({ rows, cols, seed, ...extra });
const MATERIALS = [
  { ids: ['0x05002678'], colour: '#3B3829', field: STONE(4, 3, 11, { vary: 0.6 }) },
  { ids: ['0x0500299E'], colour: '#52635A', field: STONE(4, 2, 12, { joint: 0.003, vary: 0.35, deep: 0.5, wander: 0.2 }) },
  { ids: ['0x050029A9'], colour: '#373F49', field: STONE(8, 4, 13, { vary: 0.7, deep: 0.34 }) },
  { ids: ['0x05002990'], colour: '#635448', field: STONE(7, 3, 14, { vary: 0.6, deep: 0.34 }) },
  { ids: ['0x0500297E'], colour: '#44413C', field: STONE(7, 3, 15, { vary: 0.6, deep: 0.34 }) },
  { ids: ['0x05001CB4'], colour: '#3F3827', field: STONE(5, 4, 16, { vary: 0.3, deep: 0.5 }) },
  { ids: ['0x0500299F'], colour: '#4F2211', field: STONE(8, 4, 17, { joint: 0.003, vary: 0.65, deep: 0.36, wander: 0.14 }) },
  { ids: ['0x05002793'], colour: '#774827', field: STONE(8, 3, 18, { joint: 0.003, vary: 0.4, deep: 0.45, wander: 0.14 }) },
  { ids: ['0x0500285E'], colour: '#48331C', field: planks({ count: 5, ends: 2, seed: 21 }) },
  { ids: ['0x050026CC'], colour: '#48331C', field: planks({ count: 4, upright: true, ends: 2, seed: 22 }) },
  { ids: ['0x05002860'], colour: '#47321B', field: planks({ count: 3, ends: 1, diagonal: true, seed: 23 }) },
  { ids: ['0x05002886'], colour: '#53240D', field: roofTiles({ rows: 5, cols: 6, seed: 31 }) },
  { ids: ['0x05002929'], colour: '#0E1A1A', field: roofTiles({ rows: 5, cols: 6, seed: 32 }) },
  { ids: ['0x0500281F'], colour: '#936A43', field: plaster({ seed: 41 }) },
  { ids: ['0x050026FC'], colour: '#584834', field: plaster({ seed: 42 }) },
  { ids: ['0x0500285B'], colour: '#451914', field: plaster({ seed: 43 }) },
  { ids: ['0x05002922'], colour: '#58533F', field: flags({ count: 6, seed: 51, joint: 0.022, mortar: 0.26 }) },
  { ids: ['0x050018A0', '0x0500291E'], colour: '#40564D', field: flags({ count: 3, seed: 52, joint: 0.02, mortar: 0.22 }) },
  { ids: ['0x05002695', '0x05002696'], colour: '#7D664F', field: flags({ count: 5, seed: 53, joint: 0.014, mortar: 1.25 }) },
  { ids: ['0x05002894'], colour: '#36221A', field: thatch({ rows: 3, seed: 61 }) },
  { ids: ['0x05002A6F'], colour: '#344134', field: flags({ count: 4, seed: 54, joint: 0.03, mortar: 0.3 }) },
  { ids: ['0x0500267A'], colour: '#615222', field: planks({ count: 4, upright: true, ends: 1, seed: 24 }) },
  { ids: ['0x0500295C'], colour: '#60462B', field: planks({ count: 4, upright: true, ends: 1, seed: 25 }) },
  { ids: ['0x0500267B'], colour: '#5A4B1E', field: planks({ count: 5, ends: 2, seed: 26 }) },
  { ids: ['0x0500267D'], colour: '#382306', field: planks({ count: 5, ends: 2, seed: 27 }) },
  { ids: ['0x050028DE'], colour: '#5D5446', field: STONE(7, 4, 19, { vary: 0.45, deep: 0.4 }) },
  { ids: ['0x050028DF'], colour: '#736853', field: STONE(3, 2, 20, { vary: 0.3, deep: 0.5, wander: 0.15 }) },
  { ids: ['0x05002A63'], colour: '#373B37', field: STONE(3, 3, 28, { vary: 0.8, deep: 0.4, wander: 0.06 }) },
  { ids: ['0x050028EB'], colour: '#564F44', field: plaster({ seed: 44 }) },
  { ids: ['0x050028D3'], colour: '#72755D', field: plaster({ seed: 45 }) },
  { ids: ['0x050029FE'], colour: '#687972', field: plaster({ seed: 46 }) },
  { ids: ['0x05002A62'], colour: '#5E7464', field: plaster({ seed: 47 }) },
  { ids: ['0x05002A31'], colour: '#717961', field: plaster({ seed: 48 }) },
  { ids: ['0x05002A6A'], colour: '#4A5F51', field: flags({ count: 5, seed: 55, joint: 0.012, mortar: 0.3 }) },
  { ids: ['0x05002A70'], colour: '#3E5142', field: flags({ count: 3, seed: 56, joint: 0.012, mortar: 0.35 }) },
  { ids: ['0x050018A1'], colour: '#222B20', field: flags({ count: 4, seed: 57, joint: 0.03, mortar: 0.3 }) },
  {
    ids: ['0x05002924'],
    colour: '#6B4A25',
    field: framed({ inner: planks({ count: 3, upright: true, ends: 1, seed: 77 }), panel: hex('#4A2612'), wood: hex('#A8884E') }),
  },
  {
    ids: ['0x05002690'],
    colour: '#6B4A25',
    field: framed({ inner: planks({ count: 3, upright: true, ends: 1, seed: 78 }), panel: hex('#44210F'), wood: hex('#7B5A2C') }),
  },
  {
    ids: ['0x0500289A'],
    colour: '#6B4A25',
    field: framed({ inner: plaster({ seed: 79 }), panel: hex('#A5947E'), wood: hex('#4A2C17') }),
  },
  {
    ids: ['0x050028AC'],
    colour: '#6B4A25',
    field: framed({ inner: plaster({ seed: 80 }), panel: hex('#BE9E76'), wood: hex('#7B6A3A') }),
  },
  {
    ids: ['0x05000D9B'],
    colour: '#6B4A25',
    field: framed({ inner: plaster({ seed: 81 }), panel: hex('#D8BC96'), wood: hex('#8F7A48'), bars: 5 }),
  },
  {
    ids: ['0x050028F5'],
    colour: '#6B4A25',
    field: framed({ inner: plaster({ seed: 82 }), panel: hex('#8A7A66'), wood: hex('#4A2C17'), brace: true }),
  },
  {
    ids: ['0x0500287D'],
    colour: '#6B4A25',
    field: framed({ inner: planks({ count: 4, ends: 1, seed: 71 }), panel: hex('#6B4A25'), wood: hex('#5E4020') }),
  },
  {
    ids: ['0x0500287C'],
    colour: '#6B4A25',
    field: framed({ inner: plaster({ seed: 72 }), panel: hex('#9A8974'), wood: hex('#6A4522') }),
  },
  {
    ids: ['0x0500297B'],
    colour: '#6B4A25',
    field: framed({ inner: plaster({ seed: 73 }), panel: hex('#B99A72'), wood: hex('#5A2C14'), bars: 4 }),
  },
  {
    ids: ['0x05002979'],
    colour: '#6B4A25',
    field: framed({ inner: plaster({ seed: 74 }), panel: hex('#8D8373'), wood: hex('#3F5A26') }),
  },
  {
    ids: ['0x0500297A'],
    colour: '#6B4A25',
    field: framed({ inner: plaster({ seed: 75 }), panel: hex('#897C6C'), wood: hex('#6A4522'), brace: true }),
  },
  {
    ids: ['0x0500297F'],
    colour: '#6B4A25',
    field: framed({ inner: plaster({ seed: 76 }), panel: hex('#897C6C'), wood: hex('#3F5A26'), brace: true }),
  },
];

const CREDIT = 'author = "Generated by materials.mjs"\ntool = "materials.mjs"\nlicense = "MIT"\n';

// Writes each material's pictures under `pack`/materials and returns its manifest tables.
export function buildMaterials(pack) {
  const out = path.join(pack, 'materials');
  fs.mkdirSync(out, { recursive: true });
  let tables = '';
  MATERIALS.forEach((m, k) => {
    const base = hex(m.colour);
    const n = SIZE * SIZE;
    const hs = new Float32Array(n);
    const rgb = new Float32Array(n * 3);
    const rough = new Float32Array(n);
    let sum = 0;
    for (let y = 0; y < SIZE; y++) {
      for (let x = 0; x < SIZE; x++) {
        const f = m.field((x + 0.5) / SIZE, (y + 0.5) / SIZE);
        const i = y * SIZE + x;
        hs[i] = f.h * (0.88 + 0.24 * GRAIN((x + 0.5) / SIZE, (y + 0.5) / SIZE));
        rough[i] = f.rough;
        const c = f.colour ?? base;
        for (let q = 0; q < 3; q++) rgb[i * 3 + q] = c[q] * f.tone;
        sum += f.tone;
      }
    }
    // The brightness is brought back to the retail picture's on average, so a wall keeps its place
    // in the scene it stands in. A framed wall carries its own colours.
    const mean = sum / n;
    const lift = Math.min(1.5, 1 / Math.max(mean, 0.05));
    const at = (px, py) => hs[((py + SIZE) % SIZE) * SIZE + ((px + SIZE) % SIZE)];
    const pixel = (fn) => (u, v) => {
      const x = Math.min(SIZE - 1, Math.floor(u * SIZE));
      const y = Math.min(SIZE - 1, Math.floor(v * SIZE));
      return fn(x, y, y * SIZE + x);
    };
    const name = `${m.ids[0]}`;
    const files = {
      albedo: png(pixel((x, y, i) => [rgb[i * 3] * lift, rgb[i * 3 + 1] * lift, rgb[i * 3 + 2] * lift, 1]), 0.48),
      normal: png(
        pixel((x, y) => {
          const dx = at(x + 1, y) - at(x - 1, y);
          const dy = at(x, y + 1) - at(x, y - 1);
          const l = Math.hypot(dx * 5, dy * 5, 1);
          return [(-dx * 5) / l / 2 + 0.5, (dy * 5) / l / 2 + 0.5, 1 / l / 2 + 0.5, 1];
        }),
        0,
      ),
      roughness: png(pixel((x, y, i) => [rough[i], rough[i], rough[i], 1]), 0),
      occlusion: png(
        pixel((x, y, i) => {
          const o = 0.35 + 0.65 * smooth(0.02, 0.42, hs[i]);
          return [o, o, o, 1];
        }),
        0,
      ),
    };
    for (const [kind, bytes] of Object.entries(files)) fs.writeFileSync(path.join(out, `${name}_${kind}.png`), bytes);
    const textures = m.ids.map((id) => `"${id}"`).join(', ');
    tables += `\n[[material]]\ntexture = [${textures}]\nbase_color = "materials/${name}_albedo.png"\nnormal = "materials/${name}_normal.png"\nroughness = "materials/${name}_roughness.png"\nocclusion = "materials/${name}_occlusion.png"\n${CREDIT}`;
    console.log(`material ${k + 1}/${MATERIALS.length} ${name}`);
  });
  return tables;
}
