// Builds the trees pack: trees generated with EZ-Tree, fitted to the retail objects they replace,
// and ground cover from the Quaternius Stylized Nature MegaKit.
// Bundle with esbuild, `--alias:eztree=<EZ-Tree repo>/src/lib`, then run:
//   node <bundle> <pack folder> <picture folder> <kit glTF folder> [--only <id>,<id>]
// Afterward run clump_cover.py (see COVER), then foliage.py <pack folder>, which finishes the
// pictures copied here.
import fs from 'node:fs';
import path from 'node:path';
import { Tree } from 'eztree/index.js';
import * as shapes from './shapes.mjs';
import pine from 'eztree/presets/pine_large.json';
import oak from 'eztree/presets/oak_medium.json';
import ashLarge from 'eztree/presets/ash_large.json';
import ash from 'eztree/presets/ash_medium.json';
import aspen from 'eztree/presets/aspen_medium.json';
import bush from 'eztree/presets/bush_1.json';

const [pack, pictures, kit] = process.argv.slice(2);
const out = path.join(pack, 'trees');
// `--only <id>,<id>`: grow those models alone into the pack folder, leaving the rest of it, and
// write their manifest blocks to <pack>/regrown.toml.
const only = process.argv.includes('--only') ? process.argv[process.argv.indexOf('--only') + 1].split(',') : null;

// How far below the ground a trunk starts, so it stays planted on a slope.
const SINK = 0.6;
// Where a conifer's lowest branches start up its trunk: low, so its needles come near the ground as
// retail's do. Lower, the long bare branches under the needles show as a cone of bark.
const START = 0.15;
// A conifer's branches' angle from the trunk's axis, a little below level.
const ANGLE = 105;
const SWEEP = Math.sin((ANGLE * Math.PI) / 180);
// How much wider a trunk is at the ground, and how much of the trunk's height the flare reaches.
const FLARE = 0.3;
const FLARE_SHARE = 0.15;

const BROWN = { color: 'Conifer_Bark.png', normal: 'Conifer_Bark_Normal.png', tint: [0.52, 0.36, 0.24, 1] };
const ELM_GREY = { color: 'Conifer_Bark.png', normal: 'Conifer_Bark_Normal.png', tint: [0.47, 0.44, 0.41, 1] };
const PALE = { color: 'Pale_Bark.png', normal: 'Pale_Bark_Normal.png', tint: [0.8, 0.78, 0.72, 1] };
const GREEN = { color: 'Conifer_Needles.png', tint: [0.72, 0.8, 0.5, 1], cutoff: 0.3 };
const AUTUMN = { color: 'Conifer_Needles_Autumn.png', tint: [0.8, 0.78, 0.7, 1], cutoff: 0.3 };
const TEAL = { color: 'Conifer_Needles_Teal.png', tint: [0.7, 0.85, 0.85, 1], cutoff: 0.3 };
// Snow lies on a share of the cards, more toward the top; `snow` is the needles under it.
const SNOW = { color: 'Conifer_Needles_Snow.png', tint: [1, 1, 1, 1], cutoff: 0.3, snow: { color: 'Conifer_Needles.png', tint: [0.36, 0.38, 0.42, 1], cutoff: 0.3 } };
const OAK = { color: 'Leaves_oak.png', tint: [0.72, 0.78, 0.5, 1], cutoff: 0.3, mass: [0.3, 0.46, 0.2, 1] };
const ASH = { color: 'Leaves_ash.png', tint: [0.78, 0.85, 0.55, 1], cutoff: 0.3, mass: [0.3, 0.46, 0.22, 1] };
const YELLOW = { color: 'Leaves_ash_yellow.png', tint: [1, 1, 0.78, 1], cutoff: 0.3, mass: [0.56, 0.54, 0.16, 1] };
const REDWOOD = { color: 'Conifer_Bark.png', normal: 'Conifer_Bark_Normal.png', tint: [0.74, 0.37, 0.24, 1] };
const CREAM = { color: 'Pale_Bark.png', normal: 'Pale_Bark_Normal.png', tint: [1, 0.97, 0.86, 1] };
const GNARLED = { color: 'Conifer_Bark.png', normal: 'Conifer_Bark_Normal.png', tint: [0.46, 0.33, 0.2, 1] };
const ASHEN = { color: 'Conifer_Bark.png', normal: 'Conifer_Bark_Normal.png', tint: [0.46, 0.43, 0.38, 1] };
const OLIVE = { color: 'Leaves_oak.png', tint: [0.72, 0.68, 0.34, 1], cutoff: 0.3, mass: [0.36, 0.38, 0.16, 1] };
const DARK = { color: 'Leaves_oak.png', tint: [0.42, 0.5, 0.3, 1], cutoff: 0.3, mass: [0.16, 0.28, 0.14, 1] };
const CHAR = { color: 'Conifer_Bark.png', normal: 'Conifer_Bark_Normal.png', tint: [0.2, 0.17, 0.15, 1] };
const GREY = { color: 'Conifer_Bark.png', normal: 'Conifer_Bark_Normal.png', tint: [0.42, 0.36, 0.3, 1] };
const VIVID = { color: 'Leaves_ash.png', tint: [0.86, 1, 0.56, 1], cutoff: 0.3 };
const LIME = { color: 'Leaves_ash.png', tint: [1, 1, 0.5, 1], cutoff: 0.3 };
const BANYAN_BARK = { color: 'Pale_Bark.png', normal: 'Pale_Bark_Normal.png', tint: [0.5, 0.45, 0.39, 1] };
const SWAMP = { color: 'Conifer_Bark.png', normal: 'Conifer_Bark_Normal.png', tint: [0.3, 0.25, 0.2, 1] };
const ASPEN = { color: 'Leaves_aspen.png', tint: [1, 0.72, 0.42, 1], cutoff: 0.3 };
const RUSSET = { color: 'Leaves_aspen.png', tint: [0.07, 0.026, 0.022, 1], cutoff: 0.3, mass: [0.035, 0.013, 0.011, 1] };
const RICH = { color: 'Leaves_oak.png', tint: [0.2, 0.36, 0.13, 1], cutoff: 0.3, mass: [0.06, 0.15, 0.05, 1] };
const FIR = { color: 'Conifer_Needles.png', tint: [0.26, 0.38, 0.3, 1], cutoff: 0.3 };
// Snow lying on a snowy conifer's foot.
const SNOW_FOOT = { color: 'Pale_Bark.png', normal: 'Pale_Bark_Normal.png', tint: [0.95, 0.96, 1, 1] };
const WILLOW = { color: 'Gen_Willow.png', tint: [0.7, 0.75, 0.7, 1], cutoff: 0.35 };
const BROAD = { color: 'Gen_BroadLeaf.png', tint: [0.8, 0.85, 0.7, 1], cutoff: 0.35 };
const APPLE = { color: 'Leaves_oak.png', tint: [0.194, 0.211, 0.236, 1], cutoff: 0.3, mass: [0.074, 0.118, 0.11, 1] };
const CHARRED = { color: 'Gen_Char.png', normal: 'Gen_Grit_Normal.png', tint: [1, 1, 1, 1] };

// `look` with its tint, and the mass under its leaves, multiplied by `by`: the ratio measured between
// end of retail's crown and the pack's, so the leaves take retail's colour (the developer's review, 2026-11-20).
const toned = (look, by) => {
  const times = (c) => [...c.slice(0, 3).map((v, k) => Math.min(1, Math.round(v * by[k] * 1000) / 1000)), 1];
  return { ...look, tint: times(look.tint), ...(look.mass ? { mass: times(look.mass) } : {}) };
};

// Needles in end of retail's own colour: the grey needle picture (grey_needles.py) times retail's
// crown colour (linear, over its needles' area) over the picture's mean, twice as bright, so lit by
// the client they read as retail's dark green at a distance (needle colour round, 2026-11-21).
const NEEDLE_GREY_MEAN = 0.1513;
const NEEDLE_GAIN = 2;
const crown = (c) => ({
  color: 'Conifer_Needles_Grey.png',
  tint: [...c.map((v) => Math.min(1, Math.round((v / NEEDLE_GREY_MEAN) * NEEDLE_GAIN * 1000) / 1000)), 1],
  cutoff: 0.3,
});

// Each retail conifer: id, across, tall, the trunk's radius at its foot, its needles, its bark, and
// how: where its branches start when not at START, or the floor of its crown read from end of
// retail's (the developer's second review, 2026-11-21), snow on its foot, and the other trees of a group.
const CONIFERS = [
  ['0x02000258', 16.1, 23.96, 1.0, crown([0.05, 0.0532, 0.0128]), BROWN, { floor: 0.2 }],
  ['0x02000257', 4.6, 6.75, 0.25, crown([0.0274, 0.0399, 0.0119]), BROWN, { floor: 0.19, wider: 0.68, taper: 0.7 }],
  ['0x02000256', 9.2, 13.5, 0.8, crown([0.0274, 0.0399, 0.0119]), BROWN, { floor: 0.17 }],
  ['0x020002D3', 13.4, 35.82, 1.4, crown([0.024, 0.0292, 0.0085]), BROWN, { floor: 0.14 }],
  ['0x020002D9', 13.4, 35.82, 1.4, toned(AUTUMN, [0.23, 0.228, 0.291]), BROWN, { floor: 0.17 }],
  ['0x020002DA', 23.5, 62.69, 2.4, crown([0.0339, 0.0186, 0.0069])],
  ['0x020002DB', 13.4, 44.42, 1.4, crown([0.0084, 0.0275, 0.0272]), BROWN, { floor: 0.13 }],
  ['0x020002D8', 13.4, 33.42, 1.4, crown([0.0109, 0.0259, 0.0147]), BROWN, { floor: 0.14 }],
  ['0x020003A2', 4.6, 6.75, 0.45, toned(SNOW, [0.72, 0.78, 0.84]), BROWN, { floor: 0.15, wider: 0.68, taper: 0.7, reseed: 11, children: 64, snowy: 0.4 }],
  ['0x020003A3', 9.2, 13.5, 0.8, toned(SNOW, [0.419, 0.463, 0.547]), BROWN, { floor: 0.18, wider: 0.6, taper: 0.75 }],
  ['0x020003A4', 16.1, 23.96, 1.0, toned(SNOW, [0.448, 0.473, 0.527]), BROWN, { floor: 0.15, snowFoot: true }],
  ['0x020003A7', 13.4, 33.42, 1.4, toned(SNOW, [0.581, 0.655, 0.74])],
  ['0x020012FB', 13.4, 35.82, 1.4, toned(SNOW, [0.768, 0.803, 0.858]), BROWN, { floor: 0.1, snowFoot: true }],
  ['0x0200129A', 12, 54.07, 2.0, crown([0.0483, 0.0687, 0.0213]), REDWOOD, { floor: 0.46 }],
  ['0x0200129B', 10, 40.57, 1.8, crown([0.0421, 0.0543, 0.0173]), REDWOOD, { floor: 0.33 }],
  ['0x020012FE', 6.5, 21.49, 0.8, crown([0.0475, 0.0642, 0.0205]), REDWOOD, { floor: 0.45, children: 16 }],
  ['0x02001C39', 13, 32, 1.2, crown([0.0277, 0.0399, 0.0122]), BROWN, { floor: 0.2, group: [[-3, -9, 0.82], [2, 9, 0.92]] }],
  // The older tall pine and fir, which end of retail drew another way (the remodelled props review).
  ['0x020003A1', 10.4, 56.0, 1.2, TEAL, BROWN, { older: true, start: 0.1 }],
  ['0x02000F06', 14.8, 29.6, 1.0, FIR, BROWN, { older: true, start: 0.2 }],
];

// Each retail round tree: id, across, tall, the EZ-Tree preset, its bark and leaves, the radius of
// its trunk at its foot where it follows retail's, and how many times the preset's leaves it has.
// The two-lobed ashes and the leafy oak are shaped models now (the developer's review, 2026-11-20).
const ROUND = [
  // The small oak, the sapling and the spreading bush are shaped models now (the developer's second review,
  // 2026-11-21); their rows stay so the rows after them keep their seeds.
  ['0x02000246', 'shaped'],
  ['0x02000240', 'shaped'],
  ['0x0200062C', 'shaped'],
  // 0.4.4's bright orange (the developer, 2026-11-21).
  ['0x0200062B', 7.9, 11.25, aspen, PALE, ASPEN, undefined, 3.2, 1.45],
  ['0x020002F6', 'shaped'],
];

// Each retail banyan: id, across, tall, and the radius its limbs and roots are sized from.
const BANYANS = [
  // Scaled to retail's height as drawn (the developer's sizes review, 2026-11-21).
  ['0x020003EE', 32.8 * 0.76, 39.25 * 0.76, 1.33 * 0.76],
  ['0x020003EF', 32.8 * 0.92, 25.68 * 0.92, 1.33 * 0.92],
  ['0x020003ED', 32.8 * 0.64, 19.9 * 0.64, 1.33 * 0.64],
];
// Each level: sides of the wood, how many roots reach the ground and how many hang, the share of
// leaf cards kept and how much those grow.
const BANYAN_LEVELS = [
  { sides: 10, rootSides: 5, pillars: 11, strands: 14, keep: 1, grow: 1 },
  { sides: 7, rootSides: 4, pillars: 8, strands: 5, keep: 0.5, grow: 1.35 },
  { sides: 5, rootSides: 3, pillars: 4, strands: 0, keep: 0.28, grow: 1.8 },
  { sides: 4, rootSides: 3, pillars: 2, strands: 0, keep: 0.14, grow: 2.5 },
];
// How far below the ground a root reaches, so it stays planted on a slope, meters.
const ROOT_SINK = 3.5;
// The trunk's girth, metres: its stems stand within about this of its axis, so with the inner trunk it
// is as wide as retail's trunk (2.2 m across, 3.1 m at its foot).
const BANYAN_GIRTH = 1.5;
// The inner trunk's radius, a share of the girth, so the stems round it are near its size.
const BANYAN_CORE = 0.36;
// Where retail's trunk stands from the tree's middle, measured from its mesh: glTF x and z, metres.
const BANYAN_AT = [0.4, -0.59];

const GREEN_CAP = [0.34, 0.46, 0.24, 1];
const PALE_CAP = [0.74, 0.66, 0.56, 1];
const FLESH = [0.46, 0.42, 0.3, 1];
const mush = (across, tall, stem, depth, cap) => ({ across, tall, stem, depth, cap, flesh: FLESH });

// Everything else, each from a maker in shapes.mjs: id, maker, its size.
// A shaped model drawn only on the record it was made for, not on every era's.
const OLDER = { older: true };
// End of Retail's own record of an id that has an OLDER row: drawn on that record alone, from files of its own.
const EOR = { eor: true };

const SHAPED = [
  ['0x0100069A', 'haystack', { across: 1.7, tall: 0.4 }],
  // As tall as retail's mound, whose shape the game walks on; wider at its foot so it stays a heap.
  ['0x0200040F', 'haystack', { across: 4.8, tall: 2.5, slope: 2.6, round: 1, lumpy: 0.35, ragged: 0.35, aside: 0.03, straws: 0.6 }],
  ['0x02000285', 'emberBed', { across: 1.25, rise: 2.04, tall: 0.26 }],
  ['0x02000354', 'emberBed', { across: 0.86, rise: 0.17, tall: 0.1 }],
  ['0x020007D4', 'tiers', { across: 41.8, tall: 28.69, trunk: 0.85, bark: CREAM, leaves: toned(BROAD, [0.962, 1, 0.747]) }],
  ['0x020007D9', 'bonsai', { across: 17.1, tall: 15.36, trunk: 0.6, bark: { ...PALE, tint: [0.9, 0.89, 0.85, 1] }, leaves: toned(VIVID, [0.73, 0.547, 1]), flat: true, lean: 0.14, heading: 0.45 }],
  ['0x020003EB', 'bonsai', { across: 17.1, tall: 15.36, trunk: 0.6, bark: GNARLED, leaves: toned(VIVID, [0.744, 0.554, 1]), lean: 0.14, heading: 0.45 }],
  ['0x020003EA', 'bonsai', { across: 22.9, tall: 20.48, trunk: 0.82, bark: { ...PALE, tint: [0.9, 0.89, 0.85, 1] }, leaves: toned(VIVID, [0.723, 0.534, 1]), flat: true, lean: 0.12, heading: 0.45 }],
  ['0x020002D7', 'elm', { across: 26.5, tall: 17.63, trunk: 1.34, bark: ELM_GREY, leaves: toned(OAK, [0.351, 0.362, 0.962]), low: 0.06 }],
  ['0x02000251', 'elm', { across: 53, tall: 35.27, trunk: 1.83, bark: ELM_GREY, leaves: toned(OAK, [0.328, 0.344, 0.868]), low: 0.01 }],
  ['0x020002DC', 'elm', { across: 26.5, tall: 17.63, trunk: 0.95, bark: ELM_GREY, leaves: toned(OAK, [0.296, 0.316, 0.719]), low: 0.01 }],
  ['0x020012FC', 'crowned', { across: 8.5, tall: 8.04, trunk: 0.8, bark: CREAM, leaves: toned(YELLOW, [0.561, 0.57, 0.169]), droop: true }],
  ['0x020012FD', 'crowned', { across: 8.5, tall: 18.38, trunk: 0.8, bark: CREAM, leaves: toned(YELLOW, [0.562, 0.606, 0.708]) }],
  ['0x0200009D', 'crowned', { across: 8.5, tall: 18.38, trunk: 0.8, bark: CREAM, leaves: toned(YELLOW, [0.481, 0.477, 0.389]) }],
  ['0x020002F2', 'shrub', { across: 3.6, tall: 3.84, bark: BROWN, leaves: toned(OAK, [0.19, 0.143, 0.324]), lobes: 8, leafy: 0.6 }],
  ['0x020002F5', 'shrub', { across: 3.5, tall: 3.85, bark: BROWN, leaves: toned(ASH, [0.205, 0.312, 0.564]), lobes: 8 }],
  ['0x020002F4', 'shrub', { across: 4.9, tall: 3.85, bark: BROWN, leaves: toned(OAK, [0.171, 0.248, 0.608]), lobes: 8 }],
  ['0x02001C36', 'shrub', { across: 3.6, tall: 3.84, bark: BROWN, leaves: toned(OAK, [0.197, 0.146, 0.322]) }],
  ['0x02001C34', 'shrub', { across: 4.3, tall: 7.8, bark: BROWN, leaves: toned(OLIVE, [0.231, 0.192, 0.509]) }],
  ['0x02001C31', 'shrub', { across: 4.7, tall: 5.63, bark: BROWN, leaves: toned(OAK, [0.165, 0.131, 0.372]) }],
  ['0x020002F3', 'shrub', { across: 3.0, tall: 6.55, bark: BROWN, leaves: toned(DARK, [0.162, 0.207, 0.447]) }],
  // `seed`: the seed it was first grown from, before rows above it moved its place.
  ['0x02000A35', 'clumpTree', { across: 14.2, tall: 26.8, trunk: 2.2, leaf: [0.035, 0.083, 0.026, 1] }, { seed: 11621 }],
  ['0x020004C7', 'deadwood', { across: 8.85, tall: 9.75, trunk: 0.42, depth: 4, limbs: 8, bark: { ...CHARRED, tint: [0.046, 0.046, 0.044, 1] } }],
  ['0x02000AB6', 'snag', { across: 9, tall: 26.48, trunk: 1.9, spikes: 6, fork: true, tint: [0.024, 0.023, 0.021, 1] }],
  // Fallen trees on their root plates, leaning east as retail's do.
  ['0x0200071F', 'deadwood', { across: 9.1, tall: 12.4, trunk: 0.6, level: true, lean: 0.6, toward: 0, uprooted: 1.8, snapped: true, limbs: 14, depth: 2, moss: 0.7, bark: { ...BROWN, tint: [0.587, 0.374, 0.309, 1] } }],
  ['0x02000847', 'deadwood', { across: 18.1, tall: 18.79, trunk: 0.95, level: true, lean: 0.18, toward: 0, uprooted: 2, snapped: true, limbs: 16, depth: 3, moss: 0.5, bark: { ...BROWN, tint: [0.401, 0.228, 0.239, 1] } }],
  // Drawn as retail draws it (the developer's third review, 2026-11-21).
  ['0x020007BC', 'retail'],
  ['0x02000BAC', 'deadwood', { across: 3.6, tall: 3.84, trunk: 0.07, stems: 4, limbs: 4, depth: 3, bark: { ...GREY, tint: [0.078, 0.078, 0.095, 1] } }],
  ['0x020004B1', 'palm', { across: 5.35, tall: 9.97, trunk: 0.34, leaf: [0.763, 1, 0.17, 1], bark: [1, 0.98, 0.93, 1] }],
  ['0x020007DA', 'palm', { across: 12.7, tall: 14.2, trunk: 0.24, fronds: 7, fan: true, leaf: [0.373, 0.524, 1, 1], bark: [0.42, 0.38, 0.24, 1], lean: 0.04 }],
  ['0x02000214', 'palm', { across: 9.6, tall: 8.48, trunk: 0.62, fronds: 18, lean: 0.03, bark: [0.3, 0.22, 0.15, 1], leaf: [0.166, 0.779, 0.356, 1] }],
  ['0x02000E71', 'jungle', { across: 8.7, tall: 5.96, blades: 5, wide: 0.2, stem: 0.42, rise: 0.36, droop: 0.72, leaf: [0.225, 0.466, 0.237, 1] }],
  ['0x02000E72', 'jungle', { across: 10, tall: 6.54, blades: 7, wide: 0.24, stem: 0.46, rise: 0.34, droop: 0.72, leaf: [0.129, 0.369, 0.092, 1] }],
  ['0x02000A38', 'stalk', { across: 7.5, tall: 10.6, trunk: 1.15, leaf: [0.36, 0.22, 0.12, 1] }],
  ['0x020010C7', 'wingTree', { across: 6.32, tall: 5.72, trunk: 0.72 }],
  ['0x020010CD', 'wingTree', { across: 6.32, tall: 8.87, trunk: 0.86 }],
  ['0x020010C5', 'puffTree', { across: 13.2, tall: 20, trunk: 1.5 }],
  ['0x02000B3B', 'mushroom', mush(7.43, 6.4, 0.8, 2.4, GREEN_CAP)],
  ['0x02000B39', 'mushroom', mush(7.25, 4.46, 0.5, 1.5, GREEN_CAP)],
  ['0x02000B38', 'mushroom', mush(4.94, 7.78, 0.32, 1.3, GREEN_CAP)],
  ['0x02000B3A', 'mushroom', mush(7.5, 7.36, 0.75, 2.6, GREEN_CAP)],
  ['0x02000C68', 'mushroom', mush(4.59, 7.78, 0.3, 1.2, PALE_CAP)],
  ['0x02000C69', 'mushroom', mush(7.25, 4.46, 0.5, 1.5, PALE_CAP)],
  ['0x02000C6B', 'mushroom', mush(7.43, 6.4, 0.8, 2.4, PALE_CAP)],
  ['0x02000C6A', 'mushroom', mush(7.5, 7.36, 0.75, 2.6, PALE_CAP)],
  ['0x02000247', 'cactus', { across: 2.6, tall: 7.63, radius: 0.42, arms: 2 }],
  ['0x0200032C', 'cactus', { across: 5.6, tall: 11.4, radius: 0.72, arms: 2 }],
  ['0x02000CA4', 'pod', { across: 2.18, tall: 3.44, picture: 'Gen_Pod_Crimson.png' }],
  ['0x02000CA6', 'pod', { across: 2.3, tall: 4.48, picture: 'Gen_Pod_Amber.png' }],
  ['0x02000583', 'reed', { across: 3.5, tall: 8.75 }],
  ['0x020004C1', 'flower', { across: 6.34, tall: 13.02, picture: 'Gen_Petal_Magenta.png' }],
  ['0x020004C2', 'flower', { across: 4.1, tall: 12.1, picture: 'Gen_Petal_Crimson.png' }],
  ['0x020007E1', 'crystal', { across: 6.5, tall: 15.49, prongs: 2 }],
  ['0x020007E4', 'crystal', { across: 8.6, tall: 10.8, prongs: 3 }],
  ['0x020007E2', 'crystal', { across: 12.4, tall: 17.78, prongs: 5 }],
  ['0x020007E3', 'crystal', { across: 9.2, tall: 17.74, prongs: 3 }],
  // The sea ferns, sea stars and anemones are drawn as retail draws them (the developer's review, 2026-11-20);
  // their rows stay so the rows after them keep their seeds. anemone.py paints the anemones' pictures.
  ['0x020014A8', 'retail'],
  ['0x020014A5', 'retail'],
  ['0x020014A7', 'retail'],
  ['0x02000CA5', 'pod', { across: 1.7, tall: 2.29, picture: 'Gen_Pod_Green.png' }],
  // The drooping flowers are drawn as retail draws them (the developer's second review, 2026-11-21).
  ['0x02000A37', 'retail'],
  ['0x02000B2F', 'retail'],
  ['0x02000B2D', 'retail'],
  ['0x02000B2E', 'retail'],
  ['0x020004BC', 'bladed', { across: 0.61, tall: 1.5, leaf: [0.66, 0.74, 0.14, 1] }],
  ['0x020004BB', 'bladed', { across: 0.61, tall: 1.5, leaf: [0.14, 0.42, 0.1, 1], stalkTint: [0.2, 0.05, 0.05, 1] }],
  ['0x020014AF', 'retail'],
  ['0x020014B0', 'retail'],
  ['0x020014B2', 'retail'],
  ['0x020014B4', 'retail'],
  ['0x020010C8', 'budStalk', { across: 0.27, tall: 1.66 }],
  ['0x020010CE', 'budStalk', { across: 0.27, tall: 1.06 }],
  ['0x020010C9', 'webbed', { across: 1.38, tall: 1.67 }],
  ['0x020010CF', 'webbed', { across: 1.38, tall: 0.8 }],
  ['0x020010C6', 'tuft', { across: 1, tall: 2, tint: [0.66, 0.46, 0.34, 1], blades: 46 }],
  ['0x020010CC', 'tuft', { across: 1, tall: 2, tint: [0.82, 0.07, 0.09, 1] }],
  ['0x020010C4', 'tuft', { across: 1, tall: 2, tint: [0.54, 0.36, 0.25, 1], blades: 16 }],
  ['0x020010D0', 'tuft', { across: 4.73, tall: 2, tint: [0.62, 0.43, 0.32, 1], clumps: 4, blades: 18 }],
  ['0x020010CB', 'frond', { across: 1.5, tall: 1.25 }],
  ['0x02000A59', 'sprig', { across: 0.4, tall: 0.42, leaves: { color: 'Conifer_Needles.png', tint: [0.962, 1, 1, 1], cutoff: 0.3 } }],
  ['0x020004B2', 'cycad', { across: 4.4, tall: 2.43, trunk: 0.58, crest: 1.72 }],
  // The 1999 and 2005 plants End of Retail drew as other plants under the same ids (the developer's
  // review of the remodelled props, 2026-11-20): drawn only on the older records, so End of
  // Retail keeps its own. The graphics objects are the same plants scattered by themselves.
  ['0x02000253', 'fern', { across: 1.3, tall: 1.05 }, OLDER],
  ['0x01000B74', 'fern', { across: 1.3, tall: 1.05 }, OLDER],
  ['0x02000254', 'ferns', { across: 5.0, tall: 3.0, count: 6 }, OLDER],
  ['0x01000B78', 'ferns', { across: 5.0, tall: 3.0, count: 6 }, OLDER],
  ['0x020007A2', 'lilies', { across: 0.66, tall: 0.88, stems: 3, petal: 'Gen_Petal_Red.png' }, OLDER],
  ['0x020007A3', 'spike', { across: 0.57, tall: 1.6, petal: 'Gen_Petal_Purple.png' }, OLDER],
  ['0x020007A4', 'spike', { across: 0.57, tall: 1.6, petal: 'Gen_Petal_Magenta.png' }, OLDER],
  // Round 2: the older young tree, its red-brown twin and the giant tree, grown again.
  ['0x020002F1', 'shrub', { across: 4.3, tall: 7.75, bark: BROWN, leaves: ASH, leafy: 0.3, stems: 6, reach: 0.85 }, OLDER],
  ['0x02000BAD', 'shrub', { across: 4.3, tall: 7.75, bark: BROWN, leaves: RUSSET, leafy: 0.3, stems: 6, reach: 0.85 }, OLDER],
  ['0x02000BAE', 'shrub', { across: 8.0, tall: 4.78, bark: BROWN, leaves: RUSSET, leafy: 0.35, stems: 7, reach: 0.8 }, OLDER],
  ['0x02000325', 'elm', { across: 13.4, tall: 12.9, trunk: 0.6, bark: BROWN, leaves: RICH, low: 0.22 }, OLDER],
  // The developer's review of the pack's trees, 2026-11-20: the two-lobed ashes as weeping trees of a new
  // leaf, and the leafy oak as the fruit tree it is.
  ['0x020004BE', 'weeper', { across: 13.5, tall: 21.3, trunk: 0.75, hang: 0.22, bark: ASHEN, leaves: { ...WILLOW, tint: [0.527, 0.604, 0.401, 1] } }],
  ['0x020012FF', 'weeper', { across: 13.5, tall: 21.3, trunk: 0.75, hang: 0.22, bark: ASHEN, leaves: { ...WILLOW, tint: [0.488, 0.238, 0.153, 1] } }],
  // The developer's second review, 2026-11-21: the small oak, the sapling and the spreading bush as dense
  // crowns of lobes, from a little above the ground.
  ['0x02000246', 'fruitTree', { across: 5, tall: 8.05, trunk: 0.3, bark: BROWN, leaves: toned(OAK, [0.283, 0.229, 0.49]), fruit: 0, low: 0.1 }],
  ['0x02000240', 'fruitTree', { across: 3.9, tall: 5.63, trunk: 0.24, bark: BROWN, leaves: toned(OAK, [0.214, 0.179, 0.447]), fruit: 0, low: 0.1 }],
  ['0x020002F6', 'fruitTree', { across: 8.9, tall: 4.76, trunk: 0.3, bark: BROWN, leaves: toned(OLIVE, [0.22, 0.188, 0.501]), fruit: 0, low: 0.2, leafy: 0.45 }],
  ['0x0200062C', 'fruitTree', { across: 7.9, tall: 11.25, trunk: 0.3, bark: PALE, leaves: toned(ASH, [0.358, 0.27, 0.248]), fruit: 0, low: 0.35 }],
  ['0x02000322', 'fruitTree', { across: 8.85, tall: 9.75, trunk: 0.42, bark: BROWN, leaves: toned(APPLE, [0.634, 0.778, 1]), leafy: 0.6, mass: false }],
  // End of Retail's bare trees on the young tree's and the spreading bush's shapes, as bare as the gnarled
  // stump 0x02000BAC (the giant tree report, 2026-11-24).
  ['0x02000BAD', 'deadwood', { across: 4.3, tall: 7.75, trunk: 0.12, stems: 1, limbs: 7, depth: 3, bark: { ...GREY, tint: [0.078, 0.078, 0.095, 1] } }, EOR],
  ['0x02000BAE', 'deadwood', { across: 8.0, tall: 4.78, trunk: 0.12, stems: 3, limbs: 6, depth: 3, bark: { ...GREY, tint: [0.078, 0.078, 0.095, 1] } }, EOR],
  // The clump tree's red-trunked kin.
  ['0x02000A67', 'clumpTree', { across: 15.1, tall: 20, trunk: 2.2, leaf: [0.035, 0.083, 0.026, 1], bark: [0.36, 0.11, 0.06, 1] }],
  ['0x02000F8E', 'clumpTree', { across: 17.3, tall: 39.5, trunk: 2.0, leaf: [0.035, 0.083, 0.026, 1], bark: [0.36, 0.11, 0.06, 1] }],
];
// Each level: the share of its sides and rows kept, of its leaves kept, and how much those grow.
const SHAPE_LEVELS = [
  { seg: 1, keep: 1, grow: 1 },
  { seg: 0.65, keep: 0.6, grow: 1.5 },
  { seg: 0.42, keep: 0.36, grow: 2.4 },
  { seg: 0.28, keep: 0.2, grow: 4 },
];

const TREE_LEVELS = [
  { detail: {}, distance: 60 },
  { detail: { sectionStride: 2, segmentFactor: 0.75, leafStride: 2, leafScale: 1.25 }, distance: 180 },
  { detail: { sectionStride: 3, segmentFactor: 0.5, leafStride: 3, leafScale: 1.7, billboard: 'single' }, distance: 500 },
  { detail: { sectionStride: 8, segmentFactor: 0.25, leafStride: 9, leafScale: 3.0, billboard: 'single' } },
];

// The grass's tint: over foliage.py's grass picture, the original game's olive grassland.
const GREENS = [0.8, 0.66, 0.34, 1];
// Each kind of ground cover. Grounds: 1 Grassland, 3 LushGrass, 4 Marsh, 9 PatchyGrassland,
// 21 forestfloor, 28 Moss, 29 DarkMoss. Afterward `clump_cover.py <pack> grass 4 3 2` makes each
// grass plant a clump of tufts.
const COVER = [
  { name: 'grass', source: 'Grass_Common_Tall', tall: 0.5, tint: GREENS, ground: [1, 3, 9, 28], density: 2.5, scale: [0.7, 1.3], reach: 38 },
  { name: 'wispy', source: 'Grass_Wispy_Tall', tall: 0.7, tint: GREENS, ground: [1, 3, 4, 9], density: 0.3, scale: [0.7, 1.3], reach: 38 },
  { name: 'floor', source: 'Grass_Common_Short', tall: 0.3, tint: [0.42, 0.5, 0.3, 1], ground: [21, 29], density: 1.6, scale: [0.7, 1.3], reach: 32 },
  { name: 'clover', source: 'Clover_1', tall: 0.22, tint: [0.85, 0.95, 0.6, 1], ground: [3, 21, 28], density: 0.2, scale: [0.7, 1.4], reach: 30 },
  { name: 'fern', source: 'Fern_1', tall: 0.42, tint: [1, 1, 0.8, 1], ground: [3, 21, 29], density: 0.1, scale: [0.7, 1.4], reach: 45 },
  { name: 'flowers', source: 'Flower_3_Group', tall: 0.5, tint: [0.85, 0.85, 0.75, 1], ground: [1, 3], density: 0.012, scale: [0.8, 1.2], reach: 40 },
];
// The share of a plant's blades each of its levels keeps, and how far along its reach each ends.
const COVER_LEVELS = [
  { keep: 1, reach: 0.35 },
  { keep: 0.5, reach: 0.65 },
  { keep: 0.22, reach: 1 },
];

const CREDITS = {
  shape: 'author = "Generated by shapes.mjs; leaves by Quaternius; bark by ambientCG"\ntool = "shapes.mjs"\nlicense = "MIT; leaves and bark CC0-1.0"\n',
  tree: 'author = "EZ-Tree by Daniel Greenheck; bark by ambientCG"\ntool = "EZ-Tree, fitted to the retail sizes by gen_pack.mjs"\nlicense = "MIT; bark CC0-1.0"\n',
  cover: 'author = "Quaternius"\ntool = "Stylized Nature MegaKit, reduced by gen_pack.mjs"\nlicense = "CC0-1.0"\n',
};

const used = new Set();

function material(name, m, opaque) {
  used.add(m.color);
  if (m.normal) used.add(m.normal);
  return {
    name,
    m,
    json: {
      name,
      doubleSided: true,
      ...(opaque ? {} : { alphaMode: 'MASK', alphaCutoff: m.cutoff ?? 0.2 }),
      pbrMetallicRoughness: {
        baseColorTexture: { index: 0 },
        baseColorFactor: m.tint,
        metallicFactor: 0.0,
        roughnessFactor: m.rough ?? 1.0,
      },
    },
  };
}

// Write `parts` ({ material, position, normal, uv, color?, index }) as a glTF file `name`.
function write(name, parts) {
  const chunks = [];
  const views = [];
  const accessors = [];
  let bytes = 0;
  const add = (array, target, type, componentType, extra = {}) => {
    const b = Buffer.from(array.buffer, array.byteOffset, array.byteLength);
    const pad = (4 - (b.length % 4)) % 4;
    views.push({ buffer: 0, byteOffset: bytes, byteLength: b.length, target });
    chunks.push(b, Buffer.alloc(pad));
    bytes += b.length + pad;
    const count = array.length / { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 }[type];
    accessors.push({ bufferView: views.length - 1, componentType, count, type, ...extra });
    return accessors.length - 1;
  };
  const images = [];
  const picture = (file) => {
    if (!images.includes(file)) images.push(file);
    return { index: images.indexOf(file) };
  };
  const materials = [];
  const primitives = parts.filter((p) => p.index.length > 0).map((p) => {
    const min = [Infinity, Infinity, Infinity];
    const max = [-Infinity, -Infinity, -Infinity];
    for (let i = 0; i < p.position.length; i += 3) {
      for (let k = 0; k < 3; k++) {
        min[k] = Math.min(min[k], p.position[i + k]);
        max[k] = Math.max(max[k], p.position[i + k]);
      }
    }
    const json = structuredClone(p.material.json);
    json.pbrMetallicRoughness.baseColorTexture = picture(p.material.m.color);
    if (p.material.m.normal) json.normalTexture = { ...picture(p.material.m.normal), scale: 1.3 };
    materials.push(json);
    const attributes = {
      POSITION: add(p.position, 34962, 'VEC3', 5126, { min, max }),
      NORMAL: add(p.normal, 34962, 'VEC3', 5126),
      TEXCOORD_0: add(p.uv, 34962, 'VEC2', 5126),
    };
    if (p.color) attributes.COLOR_0 = add(p.color, 34962, 'VEC4', 5126);
    return {
      material: materials.length - 1,
      attributes,
      indices: add(p.index, 34963, 'SCALAR', 5125),
    };
  });
  const doc = {
    asset: { version: '2.0', generator: 'gen_pack.mjs' },
    scene: 0,
    scenes: [{ nodes: [0] }],
    nodes: [{ mesh: 0 }],
    meshes: [{ primitives }],
    materials,
    images: images.map((uri) => ({ uri })),
    textures: images.map((_, source) => ({ source })),
    buffers: [{ uri: `${name}.bin`, byteLength: bytes }],
    bufferViews: views,
    accessors,
  };
  fs.writeFileSync(path.join(out, `${name}.bin`), Buffer.concat(chunks));
  fs.writeFileSync(path.join(out, `${name}.gltf`), JSON.stringify(doc, null, 1));
  return primitives.reduce((sum, p) => sum + accessors[p.indices].count / 3, 0);
}

function conifer(tall, across, trunk, seed, start = START, older = false, floor, children, wider = 0.46) {
  const o = structuredClone(pine);
  o.seed = seed;
  o.bark.textured = false;
  o.bark.textureScale = { x: 4, y: 1 };
  o.branch.length[0] = tall;
  o.branch.length[1] = across / 2 / SWEEP / (1 - start);
  o.branch.radius[0] = trunk;
  o.branch.radius[1] = Math.max(0.06, trunk * 0.18);
  o.branch.children[0] = Math.round(Math.max(28, tall * 3));
  o.branch.start[1] = start;
  o.branch.angle[1] = ANGLE;
  o.branch.sections[0] = Math.max(4, Math.round(tall / 3.4));
  o.branch.sections[1] = 4;
  o.branch.segments[0] = 12;
  o.branch.segments[1] = 4;
  // Needles all along each branch, as thick as retail's crowns; the older models keep their own.
  o.leaves.count = older ? (tall < 10 ? 10 : 13) : tall < 10 ? 15 : 20;
  if (!older) o.leaves.start = 0;
  o.leaves.size = Math.min(2.2, Math.max(0.7, across * 0.13));
  // A crown with a floor read from retail's: more, shorter-needled branches from that floor up, so the
  // needles close into a cone where fewer, larger tufts read as a spiral up the trunk.
  // Its cone is as wide as retail's, `wider` of its height, and its branches near level.
  if (floor !== undefined) {
    const wide = Math.min(across, tall * wider);
    o.branch.start[1] = floor;
    o.branch.angle[1] = 96;
    o.branch.length[1] = wide / 2 / (1 - floor);
    o.branch.children[0] = children ?? Math.round(Math.max(48, tall * 4.5));
    o.leaves.count = tall < 15 ? 22 : 18;
    o.leaves.size = Math.min(2.4, Math.max(0.7, wide * 0.16));
  }
  return o;
}

// A generated tree's two parts, flared at the foot and sunk into the ground; a tree `fit` to
// `across` by `tall` is stretched to it.
function treeParts(geometry, bark, leaves, flareTall, fit, level, seed, under, trim) {
  const of = (g, m, flare) => ({
    material: m,
    position: Float32Array.from(g.getAttribute('position').array),
    normal: Float32Array.from(g.getAttribute('normal').array),
    uv: Float32Array.from(g.getAttribute('uv').array),
    index: Uint32Array.from(g.index.array),
    flare,
  });
  const parts = [of(geometry.branches, bark, true), of(geometry.leaves, leaves, false)];
  if (parts[0].position.length / 3 > 65535 || parts[1].position.length / 3 > 65535) {
    throw new Error('too many vertices for EZ-Tree\'s indices');
  }
  const stretch = fit ? fitting(parts, fit) : [1, 1, 1];
  let high = 0;
  let footR = 0;
  for (let i = 0; i < parts[0].position.length; i += 3) {
    high = Math.max(high, parts[0].position[i + 1] * stretch[1]);
  }
  for (let i = 0; i < parts[0].position.length; i += 3) {
    if (parts[0].position[i + 1] * stretch[1] < high * 0.02) {
      footR = Math.max(footR, Math.hypot(parts[0].position[i] * stretch[0], parts[0].position[i + 2] * stretch[2]));
    }
  }
  for (const p of parts) {
    for (let i = 0; i < p.position.length; i += 3) {
      for (let k = 0; k < 3; k++) p.position[i + k] *= stretch[k];
      const up = p.flare ? Math.max(0, 1 - p.position[i + 1] / flareTall) : 0;
      p.position[i] *= 1 + FLARE * up * up;
      p.position[i + 2] *= 1 + FLARE * up * up;
      p.position[i + 1] -= SINK;
    }
    // three.js counts a picture's second coordinate from its foot, glTF from its top.
    for (let i = 1; i < p.uv.length; i += 2) p.uv[i] = 1 - p.uv[i];
  }
  if (trim) {
    parts[1] = cone(parts[1], high, trim);
    parts[0] = pruned(parts[0], high, trim.floor, Math.max(0.3, footR * 1.3));
  }
  if (under) parts.push(...snowOn(parts.splice(1, 1)[0], high, seed, under, trim?.snowy ?? 0));
  // Sized from the trunk under its flare, so the flare is not spread twice.
  const ball = shapes.footMesh(Math.max(0.12, footR / (1 + FLARE)), [1, 0.65, 0.42, 0.28][level], seed);
  // The root ball drawn in to the trunk it stands under, so the two meet with no ledge.
  shapes.seatFoot(ball, 0, parts[0].position, parts[0].index);
  parts.push({
    material: trim?.foot ?? bark,
    position: Float32Array.from(ball.position),
    normal: Float32Array.from(ball.normal),
    uv: Float32Array.from(ball.uv),
    index: Uint32Array.from(ball.index),
  });
  return parts;
}

// A conifer's cards shaped to a cone: each grown a little at the foot of the crown and shrunk toward
// its top by `taper`, so it ends in a point, and none reaching under `floor` of its height.
function cone(part, high, { floor = 0, taper = 1 }) {
  const n = part.position.length / 3;
  const gone = new Uint8Array(Math.ceil(n / 4));
  for (let q = 0; q < gone.length; q++) {
    const c = [0, 0, 0];
    const k = Math.min(4, n - q * 4);
    for (let v = 0; v < k; v++) for (let a = 0; a < 3; a++) c[a] += part.position[(q * 4 + v) * 3 + a] / k;
    const up = (c[1] + SINK) / high;
    const s = 1.2 - taper * Math.max(0, Math.min(1, up)) ** 1.3;
    let low = Infinity;
    for (let v = 0; v < k; v++) for (let a = 0; a < 3; a++) {
      const i = (q * 4 + v) * 3 + a;
      part.position[i] = c[a] + (part.position[i] - c[a]) * s;
      if (a === 1) low = Math.min(low, (part.position[i] + SINK) / high);
    }
    if (low < floor) gone[q] = 1;
  }
  const index = [];
  for (let t = 0; t < part.index.length; t += 3) {
    if (!gone[Math.floor(part.index[t] / 4)]) index.push(part.index[t], part.index[t + 1], part.index[t + 2]);
  }
  return { ...part, index: Uint32Array.from(index) };
}

// The wood under a crown's floor cut away but for the trunk, so no bare branch hangs below it.
function pruned(part, high, floor, trunk) {
  const keep = (v) => (part.position[v * 3 + 1] + SINK) / high >= floor * 0.95 || Math.hypot(part.position[v * 3], part.position[v * 3 + 2]) < trunk;
  const index = [];
  for (let t = 0; t < part.index.length; t += 3) {
    if (keep(part.index[t]) || keep(part.index[t + 1]) || keep(part.index[t + 2])) index.push(part.index[t], part.index[t + 1], part.index[t + 2]);
  }
  return { ...part, index: Uint32Array.from(index) };
}

// A conifer's cards as two parts, since the client draws no vertex colours: snow on a share of them,
// rising toward the top of the tree, and bare needles on the rest; `more` adds to the share.
function snowOn(part, high, seed, under, more = 0) {
  const random = shapes.seeded(seed);
  const n = part.position.length / 3;
  const snowy = new Uint8Array(Math.ceil(n / 4));
  for (let q = 0; q < snowy.length; q++) {
    let y = 0;
    for (let v = 0; v < 4; v++) y += part.position[(Math.min(n - 1, q * 4 + v)) * 3 + 1] / 4;
    snowy[q] = random() < Math.max(0.3, Math.min(0.95, 0.35 + more + (y / high) * 0.5)) ? 1 : 0;
  }
  const split = (want, material) => {
    const remap = new Map();
    const index = [];
    for (let t = 0; t < part.index.length; t += 3) {
      if (snowy[Math.floor(part.index[t] / 4)] !== want) continue;
      for (let k = 0; k < 3; k++) {
        const v = part.index[t + k];
        if (!remap.has(v)) remap.set(v, remap.size);
        index.push(remap.get(v));
      }
    }
    const pick = (array, width) => {
      const out = new Float32Array(remap.size * width);
      for (const [from, to] of remap) for (let k = 0; k < width; k++) out[to * width + k] = array[from * width + k];
      return out;
    };
    return { material, position: pick(part.position, 3), normal: pick(part.normal, 3), uv: pick(part.uv, 2), index: Uint32Array.from(index) };
  };
  return [split(0, under), split(1, part.material)];
}

function fitting(parts, [across, tall]) {
  const lo = [Infinity, Infinity, Infinity];
  const hi = [-Infinity, -Infinity, -Infinity];
  for (const p of parts) {
    for (let i = 0; i < p.position.length; i += 3) {
      for (let k = 0; k < 3; k++) {
        lo[k] = Math.min(lo[k], p.position[i + k]);
        hi[k] = Math.max(hi[k], p.position[i + k]);
      }
    }
  }
  const wide = (hi[0] - lo[0] + hi[2] - lo[2]) / 2;
  return [across / wide, tall / hi[1], across / wide];
}

function buildTree(id, options, barkLook, leafLook, flareTall, fit, trunk, seed = 1, trim) {
  let tree = new Tree();
  tree.options.copy(options);
  if (trunk) {
    // Stretching it to the retail size stretches its trunk: grow it so the trunk comes out right.
    const g = tree.createGeometry({});
    const measured = { position: g.branches.getAttribute('position').array };
    const leaves = { position: g.leaves.getAttribute('position').array };
    const [across] = fitting([measured, leaves], fit);
    const grown = structuredClone(options);
    grown.branch.radius[0] = trunk / across;
    tree = new Tree();
    tree.options.copy(grown);
  }
  const bark = material('Bark', barkLook, true);
  const leaves = material('Leaves', leafLook, false);
  const under = leafLook.snow ? material('Needles', leafLook.snow, false) : null;
  const how = trim && { ...trim, foot: trim.snowFoot ? material('Snow', SNOW_FOOT, true) : undefined };
  // A group grows more trees from other seeds, each scaled and moved: [x, z, scale].
  const others = (trim?.group ?? []).map(([x, z, k], g) => {
    const t = new Tree();
    t.options.copy({ ...structuredClone(tree.options), seed: tree.options.seed + 31 * (g + 1) });
    return { t, x, z, k };
  });
  const files = [];
  const counts = TREE_LEVELS.map((level, i) => {
    const name = `${id}_lod${i}`;
    files.push(name);
    const parts = treeParts(tree.createGeometry(level.detail), bark, leaves, flareTall, fit, i, seed, under, how);
    for (const { t, x, z, k } of others) {
      for (const p of treeParts(t.createGeometry(level.detail), bark, leaves, flareTall, fit, i, seed, under, how)) {
        for (let v = 0; v < p.position.length; v += 3) {
          p.position[v] = p.position[v] * k + x;
          p.position[v + 1] = (p.position[v + 1] + SINK) * k - SINK;
          p.position[v + 2] = p.position[v + 2] * k + z;
        }
        parts.push(p);
      }
    }
    return write(name, parts);
  });
  console.log(`${id}: ${counts.join(', ')} triangles`);
  return files;
}

// One tube into `wood` along `path`, its radius falling from `from` to `to`: a ring at each point,
// carried along the path so it never twists, shared by the spans either side, its bark running on.
function addRun(wood, path, from, to, sides) {
  const n = path.length;
  const sub = (p, q) => [p[0] - q[0], p[1] - q[1], p[2] - q[2]];
  const unit = (v) => { const l = Math.hypot(...v) || 1; return v.map((x) => x / l); };
  const cross = (p, q) => [p[1] * q[2] - p[2] * q[1], p[2] * q[0] - p[0] * q[2], p[0] * q[1] - p[1] * q[0]];
  const along = [0];
  for (let k = 1; k < n; k++) along.push(along[k - 1] + Math.hypot(...sub(path[k], path[k - 1])));
  const long = along[n - 1];
  const slope = (to - from) / long;
  const wraps = Math.max(1, Math.round(from * 4));
  const d0 = unit(sub(path[1], path[0]));
  let e = unit(cross(d0, Math.abs(d0[1]) > 0.9 ? [1, 0, 0] : [0, 1, 0]));
  const base = wood.position.length / 3;
  for (let k = 0; k < n; k++) {
    const d = unit(sub(path[Math.min(n - 1, k + 1)], path[Math.max(0, k - 1)]));
    const dot = e[0] * d[0] + e[1] * d[1] + e[2] * d[2];
    e = unit([e[0] - d[0] * dot, e[1] - d[1] * dot, e[2] - d[2] * dot]);
    const f = cross(d, e);
    const r = from + slope * along[k];
    for (let j = 0; j <= sides; j++) {
      const t = (j / sides) * Math.PI * 2;
      const c = [0, 1, 2].map((i) => Math.cos(t) * e[i] + Math.sin(t) * f[i]);
      wood.position.push(path[k][0] + c[0] * r, path[k][1] + c[1] * r, path[k][2] + c[2] * r);
      wood.normal.push(...unit([c[0] - d[0] * slope, c[1] - d[1] * slope, c[2] - d[2] * slope]));
      wood.uv.push((j / sides) * wraps, along[k] / 3.4);
    }
  }
  for (let k = 0; k < n - 1; k++) {
    for (let j = 0; j < sides; j++) {
      const p = base + k * (sides + 1) + j;
      const q = p + sides + 1;
      wood.index.push(p, p + 1, q, p + 1, q + 1, q);
    }
  }
}

// A banyan of one level: a trunk of fused stems, heavy limbs spreading near level under a wide
// flattened crown, and aerial roots dropping from the limbs, the thickest down into the ground.
function banyanParts(across, tall, trunk, seed, level, bark, leaves) {
  let rng = seed >>> 0 || 1;
  const random = () => {
    rng ^= rng << 13;
    rng ^= rng >>> 17;
    rng ^= rng << 5;
    rng >>>= 0;
    return rng / 2 ** 32;
  };
  const wood = { position: [], normal: [], uv: [], index: [] };
  const crown = { position: [], normal: [], uv: [], index: [] };
  // One tube along a smooth curve through `points`, its radius falling from `from` to `to`, with a
  // few rings a span, so a bend leaves no crease across the wood.
  const run = (points, from, to, sides) => {
    const per = sides >= 7 ? 4 : sides >= 5 ? 3 : 1;
    const path = [];
    for (let k = 0; k < points.length - 1; k++) {
      const p0 = points[Math.max(0, k - 1)], p1 = points[k], p2 = points[k + 1], p3 = points[Math.min(points.length - 1, k + 2)];
      for (let s = 0; s < per; s++) {
        const t = s / per;
        path.push([0, 1, 2].map((j) => 0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3)));
      }
    }
    path.push(points[points.length - 1]);
    addRun(wood, path, from, to, sides);
  };
  const stems = level.sides >= 7 ? 9 : level.sides >= 5 ? 5 : 0;
  // With no stems the inner trunk alone is as wide as the trunk.
  const core = BANYAN_GIRTH * (stems ? BANYAN_CORE : 0.7);
  shapes.foot(wood, core, level.sides / 10, seed);
  const fork = tall * 0.5;
  // The stems share the middle's strength, so they lean in and fuse as they rise.
  run([[0, -1, 0], [0, fork * 0.6, 0], [0, fork, 0], [0, tall * 0.72, 0]], core, core * 0.9, level.sides);
  for (let k = 0; k < stems; k++) {
    const a = ((k + random() * 0.6) / Math.max(stems, 1)) * Math.PI * 2;
    const out = BANYAN_GIRTH * (0.58 + random() * 0.2);
    const up = fork * (0.75 + random() * 0.3);
    const at = (r, y) => [Math.cos(a) * r, y, Math.sin(a) * r];
    run([at(out * 1.35, -1), at(out * 0.8, up * 0.3), at(core * 1.2, up * 0.7), at(core * 0.8, up)],
      BANYAN_GIRTH * (0.2 + random() * 0.08), BANYAN_GIRTH * 0.1, Math.max(4, level.sides - 3));
  }
  // The limbs, each rising a little and then running level, with the places roots drop from.
  const anchors = [];
  const limbs = 11;
  for (let k = 0; k < limbs; k++) {
    const a = ((k + random() * 0.7) / limbs) * Math.PI * 2;
    const from = fork * (0.82 + random() * 0.5);
    const long = (across / 2) * (0.62 + random() * 0.34);
    const rise = tall * 0.05 * (0.6 + random());
    const at = (t, side = 0) => [
      Math.cos(a) * long * t - Math.sin(a) * side,
      from + rise * Math.min(1, t * 2.2) - rise * 0.5 * t * t,
      Math.sin(a) * long * t + Math.cos(a) * side,
    ];
    const bend = long * 0.1 * (random() - 0.5);
    const wave = long * 0.05;
    const dip = (p, by) => [p[0], p[1] + wave * by * (random() - 0.3), p[2]];
    const points = [at(0), dip(at(0.25, bend), 1), dip(at(0.5, -bend), 1.4), dip(at(0.75, bend), 1.4), at(1, -bend * 0.5)];
    run(points, Math.min(trunk * 0.42, core * 0.55), trunk * 0.07, Math.max(4, level.sides - 3));
    for (const t of [0.35, 0.55, 0.75, 0.95]) anchors.push({ at: at(t, bend * (0.5 - t)), t });
    if (level.sides < 5) continue;
    // Its side boughs, which the crown hides from most views.
    for (const t of [0.42, 0.7]) {
      const start = at(t);
      const turn = a + (random() < 0.5 ? -1 : 1) * (0.7 + random() * 0.5);
      const reach = long * 0.42 * (0.7 + random() * 0.5);
      const end = [start[0] + Math.cos(turn) * reach, start[1] + rise * 0.3, start[2] + Math.sin(turn) * reach];
      const sag = [(start[0] + end[0]) / 2 + (random() - 0.5) * reach * 0.3, start[1] + rise * (random() - 0.2), (start[2] + end[2]) / 2 + (random() - 0.5) * reach * 0.3];
      run([start, sag, end], trunk * 0.17, trunk * 0.045, 3);
      anchors.push({ at: end, t: t + 0.25 });
      anchors.push({ at: [(start[0] + end[0]) / 2, (start[1] + end[1]) / 2, (start[2] + end[2]) / 2], t });
    }
  }
  // Shuffled, so the roots a lower level keeps stand all round the tree.
  for (let i = anchors.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [anchors[i], anchors[j]] = [anchors[j], anchors[i]];
  }
  const anchor = (k) => anchors[k % anchors.length].at;
  const wander = (p, by) => [p[0] + (random() - 0.5) * by, p[1], p[2] + (random() - 0.5) * by];
  for (let k = 0; k < level.pillars; k++) {
    const top = anchor(k);
    const drop = top[1] + ROOT_SINK;
    const girth = trunk * (0.035 + 0.13 * random() * random());
    const mid = (t) => wander([top[0], top[1] - drop * t, top[2]], trunk * 0.8);
    run([top, mid(0.3), mid(0.65), mid(0.85), wander([top[0], -ROOT_SINK, top[2]], trunk * 0.6)],
      girth * 0.55, girth * 1.25, level.rootSides);
  }
  for (let k = 0; k < level.strands; k++) {
    const top = anchor(level.pillars + k);
    const end = top[1] * (0.18 + random() * 0.6);
    const fall = top[1] - end;
    const mid = (t) => wander([top[0], top[1] - fall * t, top[2]], 0.6);
    run([top, mid(0.5), [top[0], end, top[2]]], 0.05 + random() * 0.05, 0.015, 3);
  }
  // The crown: a flattened dome of crossed leaf cards, thicker toward its top, and a thin skirt of
  // them under its rim.
  const rim = across / 2;
  const low = tall * 0.6;
  const cards = 520;
  for (let c = 0; c < cards; c++) {
    const r = rim * Math.sqrt(random()) * (0.98 + random() * 0.04);
    const a = random() * Math.PI * 2;
    const x = Math.cos(a) * r;
    const z = Math.sin(a) * r;
    const fall = r / rim;
    // Clumps: the surface rises and falls about the crown, so it does not read as one smooth lid.
    const clump = Math.sin(a * 5 + seed) * Math.sin(r * 0.55 + seed) * tall * 0.035;
    const layer = random() < 0.3 ? -tall * (0.05 + random() * 0.09) : 0;
    const cy = tall * 0.97 - (tall * 0.97 - low) * fall * fall * fall + clump + layer;
    if (random() >= level.keep) continue;
    shapes.cards(crown, [x, cy, z], Math.min(across * 0.11, 3.2) * level.grow * (0.75 + random() * 0.5), random);
  }
  // The whole tree moved so its trunk stands where retail's does.
  for (const p of [wood, crown]) {
    for (let i = 0; i < p.position.length; i += 3) {
      p.position[i] += BANYAN_AT[0];
      p.position[i + 2] += BANYAN_AT[1];
    }
  }
  const part = (p, m) => ({
    material: m,
    position: Float32Array.from(p.position),
    normal: Float32Array.from(p.normal),
    uv: Float32Array.from(p.uv),
    index: Uint32Array.from(p.index),
  });
  return [part(wood, bark), part(crown, leaves)];
}

function buildBanyan(id, across, tall, trunk, seed) {
  const bark = material('Bark', BANYAN_BARK, true);
  const leaves = material('Leaves', VIVID, false);
  const files = [];
  const counts = BANYAN_LEVELS.map((level, i) => {
    const name = `${id}_lod${i}`;
    files.push(name);
    return write(name, banyanParts(across, tall, trunk, seed, level, bark, leaves));
  });
  console.log(`${id}: ${counts.join(', ')} triangles`);
  return files;
}

function buildShaped(id, maker, size, seed) {
  const files = [];
  const counts = SHAPE_LEVELS.map((level, i) => {
    const name = `${id}_lod${i}`;
    files.push(name);
    const made = shapes[maker](size, level, shapes.seeded(seed));
    const parts = made
      .filter((p) => p.mesh.index.length > 0)
      .map((p) => ({
        material: material(p.name, p.look, p.opaque),
        position: Float32Array.from(p.mesh.position),
        normal: Float32Array.from(p.mesh.normal),
        uv: Float32Array.from(p.mesh.uv),
        color: p.mesh.color ? Float32Array.from(p.mesh.color) : null,
        index: Uint32Array.from(p.mesh.index),
      }));
    return write(name, parts);
  });
  console.log(`${id} ${maker}: ${counts.join(', ')} triangles`);
  return files;
}

const COMPONENTS = { 5126: Float32Array, 5125: Uint32Array, 5123: Uint16Array, 5121: Uint8Array };
const WIDTHS = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 };

// A kit model's primitives as arrays, its height at `tall` and its foot just under the ground.
function readKit(source, tall) {
  const doc = JSON.parse(fs.readFileSync(path.join(kit, `${source}.gltf`), 'utf8'));
  const bin = fs.readFileSync(path.join(kit, doc.buffers[0].uri));
  const read = (i) => {
    const a = doc.accessors[i];
    const v = doc.bufferViews[a.bufferView];
    const n = WIDTHS[a.type] * a.count;
    const Kind = COMPONENTS[a.componentType];
    const start = bin.byteOffset + (v.byteOffset ?? 0) + (a.byteOffset ?? 0);
    return Kind.from(new Kind(bin.buffer.slice(start, start + n * Kind.BYTES_PER_ELEMENT)));
  };
  // A colour stored in whole numbers is a share of their range.
  const unit = (i) => {
    const whole = { 5126: 1, 5123: 65535, 5121: 255 }[doc.accessors[i].componentType];
    return Float32Array.from(read(i), (v) => Math.min(1, 0.72 + (0.5 * v) / whole));
  };
  const prims = doc.meshes[0].primitives.map((p) => ({
    name: doc.materials[p.material].name,
    position: Float32Array.from(read(p.attributes.POSITION)),
    normal: Float32Array.from(read(p.attributes.NORMAL)),
    uv: Float32Array.from(read(p.attributes.TEXCOORD_0)),
    color: p.attributes.COLOR_0 === undefined ? null : unit(p.attributes.COLOR_0),
    index: Uint32Array.from(read(p.indices)),
  }));
  let low = Infinity;
  let high = -Infinity;
  for (const p of prims) {
    for (let i = 1; i < p.position.length; i += 3) {
      low = Math.min(low, p.position[i]);
      high = Math.max(high, p.position[i]);
    }
  }
  const s = tall / (high - low);
  for (const p of prims) {
    for (let i = 0; i < p.position.length; i += 3) {
      p.position[i] *= s;
      p.position[i + 1] = (p.position[i + 1] - low) * s - 0.03;
      p.position[i + 2] *= s;
    }
    // Lit as the ground under it is lit, whichever way each blade faces.
    for (let i = 0; i < p.normal.length; i += 3) {
      p.normal[i] = 0;
      p.normal[i + 1] = 1;
      p.normal[i + 2] = 0;
    }
  }
  return prims;
}

// `p` with `keep` of its separate blades, chosen by `seed`.
function thin(p, keep, seed) {
  if (keep >= 1) return p;
  const n = p.position.length / 3;
  const parent = Int32Array.from({ length: n }, (_, i) => i);
  const find = (x) => {
    while (parent[x] !== x) {
      parent[x] = parent[parent[x]];
      x = parent[x];
    }
    return x;
  };
  for (let t = 0; t < p.index.length; t += 3) {
    parent[find(p.index[t + 1])] = find(p.index[t]);
    parent[find(p.index[t + 2])] = find(p.index[t]);
  }
  let rng = seed >>> 0 || 1;
  const random = () => {
    rng ^= rng << 13;
    rng ^= rng >>> 17;
    rng ^= rng << 5;
    rng >>>= 0;
    return rng / 2 ** 32;
  };
  const kept = new Map();
  const keeps = (root) => {
    if (!kept.has(root)) kept.set(root, random() < keep);
    return kept.get(root);
  };
  const remap = new Map();
  const index = [];
  const take = (v) => {
    if (!remap.has(v)) remap.set(v, remap.size);
    return remap.get(v);
  };
  for (let t = 0; t < p.index.length; t += 3) {
    if (keeps(find(p.index[t]))) index.push(take(p.index[t]), take(p.index[t + 1]), take(p.index[t + 2]));
  }
  const pick = (array, width) => {
    if (!array) return null;
    const out = new Float32Array(remap.size * width);
    for (const [from, to] of remap) {
      for (let k = 0; k < width; k++) out[to * width + k] = array[from * width + k];
    }
    return out;
  };
  return {
    ...p,
    position: pick(p.position, 3),
    normal: pick(p.normal, 3),
    uv: pick(p.uv, 2),
    color: pick(p.color, 4),
    index: Uint32Array.from(index),
  };
}

function buildCover(c, k) {
  const prims = readKit(c.source, c.tall);
  const look = (name) => ({
    color: { Grass: 'Plant_Grass.png', Leaves: 'Plant_Leaves.png', Flowers: 'Plant_Flowers.png' }[name],
    tint: name === 'Flowers' ? [1, 1, 1, 1] : c.tint,
    cutoff: 0.25,
  });
  const levels = COVER_LEVELS.map((level, i) => {
    const name = `cover_${c.name}_lod${i}`;
    const parts = prims.map((p, j) => ({
      ...thin(p, level.keep, 7919 * (k + 1) + 31 * j + i),
      material: material(p.name, look(p.name), false),
    }));
    const count = write(name, parts.filter((p) => p.index.length > 0));
    return { name, count, distance: Math.round(c.reach * level.reach) };
  });
  console.log(`cover ${c.name}: ${levels.map((l) => l.count).join(', ')} triangles`);
  return levels;
}

if (!only) fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(out, { recursive: true });
let manifest = '[pack]\nname = "Enhanced Environment Models"\nformat = 2\n';
// How much the wind moves each maker's shapes; rigid things stand still.
const WIND = { haystack: 0, emberBed: 0, mushroom: 0, cactus: 0, pod: 0, crystal: 0, snag: 0, deadwood: 0, coral: 0.2, anemone: 0.15, gnarl: 0.3, vine: 0.2 };
// Models kept as 0.4.4's gen_pack.mjs (141f440b) grew them, with today's foot (the developer's reviews, 2026-11-21);
// their rows here would grow them differently, so they are grown only when named in `--only`.
const KEPT = ['0x02000240', '0x02000246', '0x02000251', '0x020002D7', '0x020002DC', '0x020007D4', '0x020002F3', '0x02001C36',
  '0x020003A3', '0x020003A4', '0x020003A7', '0x020012FB', '0x020004BE', '0x020002D9'];
const wanted = (id) => (only ? only.includes(id) : !KEPT.includes(id));
// The ids written so far: a later row for one is written under [variant], as variants.py settles it.
const written = new Set();
const treeEntry = (id, files, credit = CREDITS.tree, foliage = true, wind = 1, older = false) => {
  // Every era draws the plants, whatever shape its own files give them, but those made for an
  // older record or End of Retail's alone; `pyreal-art fingerprint` names that record from its era's files.
  const table = written.has(id) ? 'variant.model' : 'model';
  written.add(id);
  manifest += `\n[[${table}]]\nid = "${id}"\ndraws_on = "${older ? 'matching' : 'any'}"\nfoliage = ${foliage}\nwind = ${wind}\n${credit}`;
  files.forEach((file, i) => {
    manifest += `\n[[${table}.lod]]\nfile = "trees/${file}.gltf"\n`;
    if (TREE_LEVELS[i].distance) manifest += `distance = ${TREE_LEVELS[i].distance}.0\n`;
  });
};
CONIFERS.forEach(([id, across, tall, trunk, needles, bark = BROWN, how = {}], i) => {
  if (!wanted(id)) return;
  const trim = how.floor === undefined ? undefined : { floor: how.floor, taper: how.taper, snowFoot: how.snowFoot, group: how.group, snowy: how.snowy };
  // `how.reseed` grows it from another seed, where its own grows lopsided.
  const seed = 258 + 97 * i + (how.reseed ?? 0);
  treeEntry(id, buildTree(id, conifer(tall, across, trunk, seed, how.start, how.older, how.floor, how.children, how.wider), bark, needles, tall * FLARE_SHARE, undefined, undefined, seed, trim), CREDITS.tree, true, 1, how.older);
});
ROUND.forEach(([id, across, tall, preset, bark, leaves, trunk, thicker = 1, bigger = 1], i) => {
  if (across === 'shaped' || !wanted(id)) return;
  const o = structuredClone(preset);
  o.seed = 4001 + 211 * i;
  o.bark.textured = false;
  o.leaves.count = Math.round(o.leaves.count * thicker);
  o.leaves.size *= bigger;
  treeEntry(id, buildTree(id, o, bark, leaves, tall * FLARE_SHARE, [across, tall], trunk, 4001 + 211 * i));
});
BANYANS.forEach(([id, across, tall, trunk], i) => {
  if (!wanted(id)) return;
  treeEntry(id, buildBanyan(id, across, tall, trunk, 7013 + 443 * i));
});
SHAPED.forEach(([id, maker, size, how = {}], i) => {
  // An EOR row is grown under `<id>_eor`, so `--only` names it apart from the id's OLDER row.
  const name = how.eor ? `${id}_eor` : id;
  if (maker === 'retail' || !wanted(name)) return;
  // Plants small enough to skip the sun lit through them and the distant trees' farther blocks.
  const small = ['blossom', 'bladed', 'star', 'anemone', 'budStalk', 'webbed', 'tuft', 'frond', 'fern', 'ferns', 'lilies', 'spike', 'haystack', 'emberBed'].includes(maker) || size.tall < 3;
  treeEntry(id, buildShaped(name, maker, size, how.seed ?? 9001 + 131 * i), CREDITS.shape, !small, WIND[maker] ?? 1, how.older || how.eor);
});
COVER.forEach((c, k) => {
  if (only) return;
  const levels = buildCover(c, k);
  manifest += `\n[[ground_cover]]\nground = [${c.ground.join(', ')}]\ndensity = ${c.density}\nscale = [${c.scale.join(', ')}]\n${CREDITS.cover}`;
  for (const l of levels) {
    manifest += `\n[[ground_cover.lod]]\nfile = "trees/${l.name}.gltf"\ndistance = ${l.distance}.0\n`;
  }
});
fs.writeFileSync(path.join(pack, only ? 'regrown.toml' : 'manifest.toml'), manifest);
for (const picture of used) {
  if (shapes.PICTURES[picture]) {
    fs.writeFileSync(path.join(out, picture), shapes.PICTURES[picture]());
  } else if (!only || !fs.existsSync(path.join(out, picture))) {
    fs.copyFileSync(path.join(pictures, picture), path.join(out, picture));
  }
}
