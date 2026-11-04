// Rebuilds only the named shaped models into a pack folder's trees/, as gen_pack.mjs builds them,
// with the seed and size gen_pack.mjs gives each, and without touching the rest of the pack.
//   node reshape.mjs <pack folder> [--shift <n>] <id> [<id> ...]
// --shift: how many fewer models stood before these in SHAPED when the pack was built (3 for the
// pack of 2026-11-01), so they keep the seeds they were built with.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as shapes from './shapes.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const [pack, ...rest] = process.argv.slice(2);
const shift = rest[0] === '--shift' ? Number(rest[1]) : 0;
const ids = rest[0] === '--shift' ? rest.slice(2) : rest;
const out = path.join(pack, 'trees');
const source = fs.readFileSync(path.join(here, 'gen_pack.mjs'), 'utf8');

// gen_pack.mjs's SHAPED and SHAPE_LEVELS, read from its text with the looks it names.
const block = (name) => source.slice(source.indexOf(`const ${name} = [`)).match(/= (\[[\s\S]*?\n\]);/)[1];
// Its imports stand empty, but for the two its opening lines use.
const looks = source
  .slice(0, source.indexOf('const SHAPED = ['))
  .replace(/^import (?:\* as )?\{? ?(\w+) ?\}? from .*$/gm, (line, name) => (['fs', 'path'].includes(name) ? '' : `const ${name} = {};`));
const SHAPED = new Function('fs', 'path', `${looks}; return ${block('SHAPED')};`)(fs, path);
const SHAPE_LEVELS = new Function(`return ${block('SHAPE_LEVELS')};`)();

function material(name, m, opaque) {
  return {
    m,
    json: {
      name,
      doubleSided: true,
      ...(opaque ? {} : { alphaMode: 'MASK', alphaCutoff: m.cutoff ?? 0.2 }),
      pbrMetallicRoughness: { baseColorTexture: { index: 0 }, baseColorFactor: m.tint, metallicFactor: 0.0, roughnessFactor: m.rough ?? 1.0 },
    },
  };
}

// As gen_pack.mjs's write().
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
  const primitives = parts.map((p) => {
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
    return { material: materials.length - 1, attributes, indices: add(p.index, 34963, 'SCALAR', 5125) };
  });
  for (const file of images) {
    if (!fs.existsSync(path.join(out, file))) throw new Error(`${name} draws ${file}, which the pack lacks`);
  }
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

for (const id of ids) {
  const i = SHAPED.findIndex(([shaped]) => shaped === id);
  if (i < 0) throw new Error(`${id} is not one of gen_pack.mjs's shaped models`);
  const [, maker, size] = SHAPED[i];
  const counts = SHAPE_LEVELS.map((level, k) => {
    const made = shapes[maker](size, level, shapes.seeded(9001 + 131 * (i - shift)));
    return write(`${id}_lod${k}`, made.filter((p) => p.mesh.index.length > 0).map((p) => ({
      material: material(p.name, p.look, p.opaque),
      position: Float32Array.from(p.mesh.position),
      normal: Float32Array.from(p.mesh.normal),
      uv: Float32Array.from(p.mesh.uv),
      color: p.mesh.color ? Float32Array.from(p.mesh.color) : null,
      index: Uint32Array.from(p.mesh.index),
    })));
  });
  console.log(`${id} ${maker}: ${counts.join(', ')} triangles`);
}
