// Builds the trees pack: trees generated with EZ-Tree, fitted to the retail objects they replace,
// and ground cover from the Quaternius Stylized Nature MegaKit.
// Bundle with esbuild, `--alias:eztree=<EZ-Tree repo>/src/lib`, then run:
//   node <bundle> <pack folder> <picture folder> <kit glTF folder>
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

// How far below the ground a trunk starts, so it stays planted on a slope.
const SINK = 0.6;
// Where a conifer's lowest branches start up its trunk, high enough to walk under.
const START = 0.4;
// A conifer's branches' angle from the trunk's axis, a little below level.
const ANGLE = 105;
const SWEEP = Math.sin((ANGLE * Math.PI) / 180);
// How much wider a trunk is at the ground, and how much of the trunk's height the flare reaches.
const FLARE = 0.45;
const FLARE_SHARE = 0.15;

const BROWN = { color: 'Conifer_Bark.png', normal: 'Conifer_Bark_Normal.png', tint: [0.52, 0.36, 0.24, 1] };
const ELM_GREY = { color: 'Conifer_Bark.png', normal: 'Conifer_Bark_Normal.png', tint: [0.47, 0.44, 0.41, 1] };
const PALE = { color: 'Pale_Bark.png', normal: 'Pale_Bark_Normal.png', tint: [0.8, 0.78, 0.72, 1] };
const GREEN = { color: 'Conifer_Needles.png', tint: [0.72, 0.8, 0.5, 1], cutoff: 0.3 };
const AUTUMN = { color: 'Conifer_Needles_Autumn.png', tint: [0.8, 0.78, 0.7, 1], cutoff: 0.3 };
const TEAL = { color: 'Conifer_Needles_Teal.png', tint: [0.7, 0.85, 0.85, 1], cutoff: 0.3 };
const SNOW = { color: 'Conifer_Needles_Snow.png', tint: [1, 1, 1, 1], cutoff: 0.3, snow: true };
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

// Each retail conifer: id, across, tall, the trunk's radius at its foot, its needles, its bark.
const CONIFERS = [
  ['0x02000258', 16.1, 23.96, 1.0, GREEN],
  ['0x02000257', 4.6, 6.75, 0.45, GREEN],
  ['0x02000256', 9.2, 13.5, 0.8, GREEN],
  ['0x020002D3', 13.4, 35.82, 1.4, GREEN],
  ['0x020002D9', 13.4, 35.82, 1.4, AUTUMN],
  ['0x020002DA', 23.5, 62.69, 2.4, AUTUMN],
  ['0x020002DB', 13.4, 44.42, 1.4, TEAL],
  ['0x020002D8', 13.4, 33.42, 1.4, TEAL],
  ['0x020003A2', 4.6, 6.75, 0.45, SNOW],
  ['0x020003A3', 9.2, 13.5, 0.8, SNOW],
  ['0x020003A4', 16.1, 23.96, 1.0, SNOW],
  ['0x020003A7', 13.4, 33.42, 1.4, SNOW],
  ['0x020012FB', 13.4, 35.82, 1.4, SNOW],
  ['0x0200129A', 15.3, 54.07, 2.0, GREEN, REDWOOD],
  ['0x0200129B', 15.3, 40.57, 1.8, GREEN, REDWOOD],
  ['0x020012FE', 6.5, 21.49, 0.8, GREEN, REDWOOD],
  ['0x02001C39', 16.4, 35.82, 1.4, GREEN],
];

// Each retail round tree: id, across, tall, the EZ-Tree preset, its bark and leaves, the radius of
// its trunk at its foot where it follows retail's, and how many times the preset's leaves it has.
const ROUND = [
  ['0x02000246', 6.2, 8.05, oak, BROWN, OAK, undefined, 1.4],
  ['0x02000240', 4.7, 5.63, oak, BROWN, OAK, undefined, 1.4],
  ['0x0200062C', 7.9, 11.25, ash, PALE, ASH, undefined, 2],
  ['0x0200062B', 7.9, 11.25, aspen, PALE, ASPEN, undefined, 3.2, 1.45],
  ['0x020002F6', 8.9, 4.76, bush, BROWN, OLIVE],
  ['0x020004BE', 13.5, 21.3, ashLarge, ASHEN, ASH, 1.25, 1.7],
  ['0x020012FF', 13.5, 21.3, ashLarge, ASHEN, YELLOW, 1.25, 1.7],
  ['0x02000322', 8.85, 9.75, oak, BROWN, DARK, 0.59],
];

// Each retail banyan: id, across, tall, its trunk's radius at its foot.
const BANYANS = [
  ['0x020003EE', 32.8, 39.25, 1.33],
  ['0x020003EF', 32.8, 25.68, 1.33],
  ['0x020003ED', 32.8, 19.9, 1.33],
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

const GREEN_CAP = [0.34, 0.46, 0.24, 1];
const PALE_CAP = [0.74, 0.66, 0.56, 1];
const FLESH = [0.46, 0.42, 0.3, 1];
const mush = (across, tall, stem, depth, cap) => ({ across, tall, stem, depth, cap, flesh: FLESH });

// Everything else, each from a maker in shapes.mjs: id, maker, its size.
const SHAPED = [
  ['0x0100069A', 'hayPile', { across: 1.7, tall: 0.3 }],
  ['0x02000285', 'emberBed', { across: 1.25, rise: 2.04, tall: 0.26 }],
  ['0x02000354', 'emberBed', { across: 0.86, rise: 0.17, tall: 0.1 }],
  ['0x020007D4', 'parasol', { across: 41.8, tall: 28.69, trunk: 0.85, bark: CREAM, leaves: LIME }],
  ['0x020007D9', 'parasol', { across: 17.1, tall: 15.36, trunk: 0.6, lean: 0.14, bark: CREAM, leaves: VIVID }],
  ['0x020003EB', 'parasol', { across: 17.1, tall: 15.36, trunk: 0.6, lean: 0.14, bark: CREAM, leaves: VIVID }],
  ['0x020003EA', 'parasol', { across: 22.9, tall: 20.48, trunk: 0.72, lean: 0.14, bark: CREAM, leaves: VIVID }],
  ['0x020002D7', 'elm', { across: 26.5, tall: 17.63, trunk: 1.34, bark: ELM_GREY, leaves: OAK }],
  ['0x02000251', 'elm', { across: 53, tall: 35.27, trunk: 1.83, bark: ELM_GREY, leaves: OAK }],
  ['0x020002DC', 'elm', { across: 26.5, tall: 17.63, trunk: 0.95, bark: ELM_GREY, leaves: OAK }],
  ['0x020012FC', 'crowned', { across: 8.5, tall: 10.38, trunk: 0.8, bark: CREAM, leaves: YELLOW }],
  ['0x020012FD', 'crowned', { across: 8.5, tall: 18.38, trunk: 0.8, bark: CREAM, leaves: YELLOW }],
  ['0x0200009D', 'crowned', { across: 8.5, tall: 18.38, trunk: 0.8, bark: CREAM, leaves: YELLOW }],
  ['0x020002F2', 'shrub', { across: 3.6, tall: 3.84, bark: BROWN, leaves: OAK }],
  ['0x020002F5', 'shrub', { across: 3.5, tall: 3.85, bark: BROWN, leaves: ASH }],
  ['0x020002F4', 'shrub', { across: 4.9, tall: 3.85, bark: BROWN, leaves: OAK }],
  ['0x02001C36', 'shrub', { across: 3.6, tall: 3.84, bark: BROWN, leaves: OAK }],
  ['0x02001C34', 'shrub', { across: 4.3, tall: 7.8, bark: BROWN, leaves: OLIVE }],
  ['0x02001C31', 'shrub', { across: 4.7, tall: 5.63, bark: BROWN, leaves: OAK }],
  ['0x020002F3', 'shrub', { across: 3.0, tall: 6.55, bark: BROWN, leaves: DARK }],
  ['0x02000A35', 'clumpTree', { across: 14.2, tall: 26.8, trunk: 2.2 }],
  ['0x020004C7', 'snag', { across: 8.85, tall: 9.75, trunk: 0.5, spikes: 12 }],
  ['0x02000AB6', 'snag', { across: 9, tall: 26.48, trunk: 1.9, spikes: 6, fork: true }],
  ['0x0200071F', 'snag', { across: 9.1, tall: 12.4, trunk: 1.2, spikes: 12, ash: 1 }],
  ['0x02000847', 'snag', { across: 18.1, tall: 18.79, trunk: 2.0, spikes: 11, ash: 1 }],
  ['0x020007BC', 'gnarl', { across: 11, tall: 6.5, trunk: 0.5, arms: 7, arching: true, bark: { ...GNARLED, tint: [0.5, 0.41, 0.16, 1] } }],
  ['0x02000BAC', 'gnarl', { across: 3.6, tall: 3.84, trunk: 0.14, arms: 12, bark: GREY }],
  ['0x020004B1', 'palm', { across: 5.35, tall: 9.97, trunk: 0.34 }],
  ['0x020007DA', 'palm', { across: 12.7, tall: 14.2, trunk: 0.24, fronds: 7, fan: true, leaf: [0.24, 0.62, 0.42, 1], bark: [0.42, 0.38, 0.24, 1], lean: 0.04 }],
  ['0x02000214', 'palm', { across: 9.6, tall: 8.48, trunk: 0.62, fronds: 18, lean: 0.03, bark: [0.3, 0.22, 0.15, 1] }],
  ['0x02000E71', 'jungle', { across: 8.7, tall: 5.96, blades: 8, wide: 0.34 }],
  ['0x02000E72', 'jungle', { across: 10, tall: 6.54, blades: 12, wide: 0.5 }],
  ['0x02000A38', 'stalk', { across: 7.5, tall: 10.6, trunk: 1.15 }],
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
  ['0x020014A8', 'coral', { across: 32, tall: 42.59, tint: [0.14, 0.58, 0.7, 1] }],
  ['0x020014A5', 'coral', { across: 32, tall: 42.59, tint: [0.72, 0.16, 0.08, 1] }],
  ['0x020014A7', 'coral', { across: 32, tall: 42.59, tint: [0.12, 0.6, 0.2, 1] }],
  ['0x02000CA5', 'pod', { across: 1.7, tall: 2.29, picture: 'Gen_Pod_Green.png' }],
  ['0x02000A37', 'blossom', { across: 1.22, tall: 1.09, petal: 'Gen_Petal_Orange.png' }],
  ['0x02000B2F', 'blossom', { across: 1.22, tall: 1.09, petal: 'Gen_Petal_Red.png' }],
  ['0x02000B2D', 'blossom', { across: 1.22, tall: 1.09, petal: 'Gen_Petal_Magenta.png' }],
  ['0x02000B2E', 'blossom', { across: 1.22, tall: 1.09, petal: 'Gen_Petal_Purple.png' }],
  ['0x020004BC', 'bladed', { across: 0.61, tall: 1.5, leaf: [0.66, 0.74, 0.14, 1] }],
  ['0x020004BB', 'bladed', { across: 0.61, tall: 1.5, leaf: [0.14, 0.42, 0.1, 1], stalkTint: [0.2, 0.05, 0.05, 1] }],
  ['0x020014AF', 'star', { across: 3.72, tall: 1.44, tint: [0.82, 0.34, 0.24, 1] }],
  ['0x020014B0', 'star', { across: 3.72, tall: 1.44, tint: [0.26, 0.78, 0.46, 1] }],
  ['0x020014B2', 'anemone', { across: 1.95, tall: 2.42, tint: [0.22, 0.7, 0.3, 1] }],
  ['0x020014B4', 'anemone', { across: 1.95, tall: 2.42, tint: [0.24, 0.32, 0.8, 1] }],
  ['0x020010C8', 'budStalk', { across: 0.27, tall: 1.66 }],
  ['0x020010CE', 'budStalk', { across: 0.27, tall: 1.06 }],
  ['0x020010C9', 'webbed', { across: 1.38, tall: 1.67 }],
  ['0x020010CF', 'webbed', { across: 1.38, tall: 0.8 }],
  ['0x020010C6', 'tuft', { across: 1, tall: 2, tint: [0.66, 0.46, 0.34, 1], blades: 46 }],
  ['0x020010CC', 'tuft', { across: 1, tall: 2, tint: [0.82, 0.07, 0.09, 1] }],
  ['0x020010C4', 'tuft', { across: 1, tall: 2, tint: [0.54, 0.36, 0.25, 1], blades: 16 }],
  ['0x020010D0', 'tuft', { across: 4.73, tall: 2, tint: [0.62, 0.43, 0.32, 1], clumps: 4, blades: 18 }],
  ['0x020010CB', 'frond', { across: 1.5, tall: 1.25 }],
  ['0x02000A59', 'shrub', { across: 0.4, tall: 0.42, bark: BROWN, leaves: DARK }],
  ['0x020004B2', 'cycad', { across: 4.4, tall: 2.43, trunk: 0.58, crest: 1.72 }],
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

const GREENS = [0.62, 0.68, 0.42, 1];
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

function conifer(tall, across, trunk, seed) {
  const o = structuredClone(pine);
  o.seed = seed;
  o.bark.textured = false;
  o.bark.textureScale = { x: 4, y: 1 };
  o.branch.length[0] = tall;
  o.branch.length[1] = across / 2 / SWEEP / (1 - START);
  o.branch.radius[0] = trunk;
  o.branch.radius[1] = Math.max(0.06, trunk * 0.18);
  o.branch.children[0] = Math.round(Math.max(28, tall * 3));
  o.branch.start[1] = START;
  o.branch.angle[1] = ANGLE;
  o.branch.sections[0] = Math.max(4, Math.round(tall / 3.4));
  o.branch.sections[1] = 4;
  o.branch.segments[0] = 12;
  o.branch.segments[1] = 4;
  o.leaves.count = tall < 10 ? 10 : 13;
  o.leaves.size = Math.min(2.2, Math.max(0.7, across * 0.13));
  return o;
}

// A generated tree's two parts, flared at the foot and sunk into the ground; a tree `fit` to
// `across` by `tall` is stretched to it.
function treeParts(geometry, bark, leaves, flareTall, fit, level, seed) {
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
  if (leaves.m.snow) snowOn(parts[1], high, seed);
  const ball = shapes.footMesh(Math.max(0.12, footR), [1, 0.65, 0.42, 0.28][level], seed);
  parts.push({
    material: bark,
    position: Float32Array.from(ball.position),
    normal: Float32Array.from(ball.normal),
    uv: Float32Array.from(ball.uv),
    index: Uint32Array.from(ball.index),
  });
  return parts;
}

// Vertex colours over a picture of snow lying on needles: brightest toward the top of the tree and
// on the upper edge of each card.
function snowOn(part, high, seed) {
  const random = shapes.seeded(seed);
  const n = part.position.length / 3;
  part.color = new Float32Array(n * 4);
  for (let q = 0; q + 3 < n; q += 4) {
    let lo = Infinity;
    let hi = -Infinity;
    for (let v = 0; v < 4; v++) {
      const y = part.position[(q + v) * 3 + 1];
      lo = Math.min(lo, y);
      hi = Math.max(hi, y);
    }
    const jitter = random() * 0.25;
    for (let v = 0; v < 4; v++) {
      const y = part.position[(q + v) * 3 + 1];
      const rise = (y - (lo + hi) / 2) / Math.max(0.01, (hi - lo) / 2);
      const s = Math.max(0, Math.min(1, 0.3 + (y / high) * 0.9 + rise * 0.35 + jitter));
      // A little blue, since the crowns take a warm light.
      part.color.set([0.34 + 0.54 * s, 0.46 + 0.48 * s, 0.38 + 0.62 * s, 1], (q + v) * 4);
    }
  }
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

function buildTree(id, options, barkLook, leafLook, flareTall, fit, trunk, seed = 1) {
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
  const files = [];
  const counts = TREE_LEVELS.map((level, i) => {
    const name = `${id}_lod${i}`;
    files.push(name);
    return write(name, treeParts(tree.createGeometry(level.detail), bark, leaves, flareTall, fit, i, seed));
  });
  console.log(`${id}: ${counts.join(', ')} triangles`);
  return files;
}

// A tube into `wood` from `a` to `b`, tapering from `ra` to `rb`, its bark repeating every 3.4 m.
function addTube(wood, a, b, ra, rb, sides) {
  const axis = [b[0] - a[0], b[1] - a[1], b[2] - a[2]];
  const long = Math.hypot(...axis);
  const d = axis.map((v) => v / long);
  const side = Math.abs(d[1]) > 0.9 ? [1, 0, 0] : [0, 1, 0];
  const u = [d[1] * side[2] - d[2] * side[1], d[2] * side[0] - d[0] * side[2], d[0] * side[1] - d[1] * side[0]];
  const ul = Math.hypot(...u);
  const e = u.map((v) => v / ul);
  const f = [d[1] * e[2] - d[2] * e[1], d[2] * e[0] - d[0] * e[2], d[0] * e[1] - d[1] * e[0]];
  const base = wood.position.length / 3;
  for (const [end, c, r] of [[0, a, ra], [1, b, rb]]) {
    for (let j = 0; j <= sides; j++) {
      const t = (j / sides) * Math.PI * 2;
      const n = [0, 1, 2].map((k) => Math.cos(t) * e[k] + Math.sin(t) * f[k]);
      wood.position.push(c[0] + n[0] * r, c[1] + n[1] * r, c[2] + n[2] * r);
      wood.normal.push(...n);
      wood.uv.push((j / sides) * Math.max(1, Math.round(ra * 4)), (end * long) / 3.4);
    }
  }
  for (let j = 0; j < sides; j++) {
    const p = base + j;
    const q = p + sides + 1;
    wood.index.push(p, p + 1, q, p + 1, q + 1, q);
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
  // A run of tubes through `points`, its radius falling from `from` to `to`.
  const run = (points, from, to, sides) => {
    const last = points.length - 1;
    for (let k = 0; k < last; k++) {
      const r = (t) => from + (to - from) * t;
      addTube(wood, points[k], points[k + 1], r(k / last), r((k + 1) / last), sides);
    }
  };
  shapes.foot(wood, trunk, level.sides / 10, seed);
  const fork = tall * 0.5;
  // The stems share the middle's strength, so they lean in and fuse as they rise.
  run([[0, -1, 0], [0, fork * 0.6, 0], [0, fork, 0], [0, tall * 0.72, 0]], trunk, trunk * 0.45, level.sides);
  const stems = level.sides >= 7 ? 9 : level.sides >= 5 ? 5 : 0;
  for (let k = 0; k < stems; k++) {
    const a = ((k + random() * 0.6) / Math.max(stems, 1)) * Math.PI * 2;
    const out = trunk * (1.5 + random() * 0.9);
    const up = fork * (0.55 + random() * 0.4);
    const at = (r, y) => [Math.cos(a) * r, y, Math.sin(a) * r];
    run([at(out, -1), at(out * 0.72, up * 0.3), at(trunk * 0.55, up * 0.7), at(trunk * 0.2, up)],
      trunk * (0.34 + random() * 0.14), trunk * 0.14, Math.max(4, level.sides - 3));
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
    run(points, trunk * 0.42, trunk * 0.07, Math.max(4, level.sides - 3));
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

fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(out, { recursive: true });
let manifest = '[pack]\nname = "Enhanced Environment Models"\nformat = 2\n';
// How much the wind moves each maker's shapes; rigid things stand still.
const WIND = { hayPile: 0, emberBed: 0, mushroom: 0, cactus: 0, pod: 0, crystal: 0, snag: 0, coral: 0.2, anemone: 0.15, gnarl: 0.3 };
const treeEntry = (id, files, credit = CREDITS.tree, foliage = true, wind = 1) => {
  manifest += `\n[[model]]\nid = "${id}"\nfoliage = ${foliage}\nwind = ${wind}\n${credit}`;
  files.forEach((file, i) => {
    manifest += `\n[[model.lod]]\nfile = "trees/${file}.gltf"\n`;
    if (TREE_LEVELS[i].distance) manifest += `distance = ${TREE_LEVELS[i].distance}.0\n`;
  });
};
CONIFERS.forEach(([id, across, tall, trunk, needles, bark = BROWN], i) => {
  treeEntry(id, buildTree(id, conifer(tall, across, trunk, 258 + 97 * i), bark, needles, tall * FLARE_SHARE, undefined, undefined, 258 + 97 * i));
});
ROUND.forEach(([id, across, tall, preset, bark, leaves, trunk, thicker = 1, bigger = 1], i) => {
  const o = structuredClone(preset);
  o.seed = 4001 + 211 * i;
  o.bark.textured = false;
  o.leaves.count = Math.round(o.leaves.count * thicker);
  o.leaves.size *= bigger;
  treeEntry(id, buildTree(id, o, bark, leaves, tall * FLARE_SHARE, [across, tall], trunk, 4001 + 211 * i));
});
BANYANS.forEach(([id, across, tall, trunk], i) => {
  treeEntry(id, buildBanyan(id, across, tall, trunk, 7013 + 443 * i));
});
SHAPED.forEach(([id, maker, size], i) => {
  // Plants small enough to skip the sun lit through them and the distant trees' farther blocks.
  const small = ['blossom', 'bladed', 'star', 'anemone', 'budStalk', 'webbed', 'tuft', 'frond', 'hayPile', 'emberBed'].includes(maker) || size.tall < 3;
  treeEntry(id, buildShaped(id, maker, size, 9001 + 131 * i), CREDITS.shape, !small, WIND[maker] ?? 1);
});
COVER.forEach((c, k) => {
  const levels = buildCover(c, k);
  manifest += `\n[[ground_cover]]\nground = [${c.ground.join(', ')}]\ndensity = ${c.density}\nscale = [${c.scale.join(', ')}]\n${CREDITS.cover}`;
  for (const l of levels) {
    manifest += `\n[[ground_cover.lod]]\nfile = "trees/${l.name}.gltf"\ndistance = ${l.distance}.0\n`;
  }
});
fs.writeFileSync(path.join(pack, 'manifest.toml'), manifest);
for (const picture of used) {
  if (shapes.PICTURES[picture]) {
    fs.writeFileSync(path.join(out, picture), shapes.PICTURES[picture]());
  } else {
    fs.copyFileSync(path.join(pictures, picture), path.join(out, picture));
  }
}
