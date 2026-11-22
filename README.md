# Dereth Enhanced Environment Assets

This repository holds the assets, tools and releases of the Enhanced Environment art pack for the
[Dereth](https://github.com/dereth-network/dereth) client. The pack adds new models, ground,
materials and moons. The client draws them in place of the game's own when Enhanced Graphics is on.

![Holtburg with the Enhanced Environment pack: EZ-Tree pines and spruces, ground cover and relief ground](docs/screenshot.webp)

## What is in the pack

`pack/manifest.toml` lists every asset, what it replaces and who made it.

| Assets | Scripts | Folder |
|---|---|---|
| Shaped models: plants, mushrooms, palms, dead trees, embers and hay | `shapes.mjs`, `gen_pack.mjs`, `reshape.mjs`, `fit_trunks.py`, `foliage.py` | `pack/trees/` |
| Trees and bushes | `gen_pack.mjs`, `fit_trunks.py`, `taper_trunks.py`, `foliage.py`, `grey_needles.py` (the conifers' needle picture), then `scale_models.py` once on the trees it lists | `pack/trees/` |
| Boulders and rocks | `boulders.py` | `pack/trees/` |
| Cactuses | `cactus.py` | `pack/trees/` |
| The sea anemones' pictures, drawn on the game's own anemones | `anemone.py`, after `gen_pack.mjs` | `pack/materials/` |
| Ground cover | `gen_pack.mjs`, then `clump_cover.py`, then `foliage.py` | `pack/trees/` |
| Relief materials for walls, floors, roofs, rock, carved stone, wood and books | `relief.py`, `masonry.py`, `recipes.py`, `split.py`, `fallback.py` | `pack/materials/` |
| Rock materials | `rockgen.py` | `pack/materials/` |
| Ice | `ice.py` | `pack/materials/` |
| Iron that shines: the doors' iron leaves and frames, and the iron bands and hinges on wood, each with a metal map where wood and iron share a picture | `iron.py`, with `relief.py` | `pack/materials/` |
| The iron chest painted anew in each era: its sides, lid and lock plate at four times retail's texels, laid out as retail's so its picture coordinates fit, with bands, rivets, hinge scrolls, lid rings and rust, and relief in millimetres from the same shapes | `chest.py` | `pack/materials/` |
| Arms and armour that shine: blades, mace heads, gilt guards, grips, the heater shield and the Training Academy's two suits of plate, each with a metal map where steel or gold share a picture with leather | `arms.py`, with `relief.py` | `pack/materials/` |
| Stone for surfaces with no picture: the Bael'Zharon statues' dark red, chiselled, laid along the world's axes over the surface's own colour | `solids.py` | `pack/materials/solid/` |
| Fine-detail grit tiles | `grit.py` | `pack/grit/` |
| Obsidian ground | `obsidian.py` | `pack/ground/` |
| Moons | `moons.py` | `pack/sky/` |
| Lights | By hand | `pack/manifest.toml` |

Every model then goes through `quantise.py`, last of all, after the scripts above. It stores
positions, normals, picture coordinates, colours and indices as smaller integers, and moves no
point more than a millimetre. A second run changes nothing. The scripts above read and write the
models as floats, so run `quantise.py pack` again after any of them.

Each model and material names the fingerprint of the original record it was made from, so a client
drawing an older era's files draws it only where that era's record is the same. Run
`pyreal-art fingerprint pack --dat-dir <your end-of-retail files>` after any of the scripts above.
It writes the fingerprint of each entry that has none, read from your own files. A fingerprint is
a fact about the original, as an id or a size is: a short hash of a picture's light and dark, or of
a model's part sizes. The plants (`gen_pack.mjs`) say `draws_on = "any"`, so every era draws them.
The few made for 1999 and 2005 plants and trees that end of retail drew another way under the same ids
say `draws_on = "matching"`, and their fingerprints come from the 2005 files, so end of retail keeps
its own.

The materials for the 1999 and 2005 files are in `materials/1999/` and `materials/2005/`. They are
made from those files' own pictures where no material made from end of retail's pictures matches
them. `tables/eras.tsv` lists those pictures. `tables/drawn-as-eor.tsv` lists the rooms' pictures
and the props Pyreal draws with end of retail's own art beside an older world, and the older
materials the pack leaves out for them; Pyreal checks it against its own lists when it packs this
pack, and `build.py` refuses a material it leaves out. A picture with no relief has no material
either: the client draws it as retail does. To make them again:

```bash
pyreal-art pictures <a list of the era's pictures in tables/eras.tsv> --dat-dir <that era's files> --out <folder>
python3 generators/relief.py <folder> pack --survey <pictures.tsv> --into 2005
```

`--into` names the era, and the run replaces that era's materials alone. Each material names its
picture's fingerprint, which `pyreal-art pictures` writes beside the pictures.

End of retail's own ground is made the same way, in `materials/eor/`: the survey sees only what
models draw, so the terrain pictures no surveyed material covers are listed in `tables/eras.tsv`
as era `eor`, marked `ground:<recipe>`. Their maps are 512 texels, with a fine grain from the
ground recipes (grass, soil, sand, snow, stony) laid over each picture's own forms. Make them with
`--into eor` from end of retail's files, with no `--survey`. The 1999 and 2005 worlds lay end of
retail's ground pictures, toned toward 1999 by the client's Ground Coloring, so they take these
too and have no ground of their own.

A change to relief is checked against the maps it replaces before it is kept:

```bash
python3 generators/check_relief.py <the player's pictures> <old pack folder> <new pack folder> [--sub 2005/]
```

It says, for each picture, whether the new height is no worse than the old: its joints and cracks
lie on the picture's own lines as well as before, it dips no more where the picture is plain, and
it is flat only where the old height was clearly broken. `generators/refit.py` refits the rock and
masonry rectangles of hand recipes whose maps blotch smooth stone and plaster.

Every script is in `generators/`. Each one describes its own use at the top of the file.

## Copyright

The repository holds no picture, model or sound of the original game. Each asset is made by a
script in `generators/`, made by hand, or made with the openly licensed work in Credits. Some
assets use facts about the original game. These facts are object ids, sizes, collision positions,
overall shapes and colours. The relief materials are worked out from the player's own copy of each
original picture. The client draws them over that picture. They are of no use without the player's
own copy of the game.

`build.py` enforces these rules. It refuses the pack when an entry names no author, tool or
license. It refuses a license outside CC0-1.0 and MIT, a tool missing from `generators/`, and the
original game as an author. It also refuses any file in `pack/` that no entry names.

## Building

```bash
python3 build.py                     # checks the pack, then writes dist/enhanced-environment.dat
python3 build.py --check             # says whether dist/enhanced-environment.dat is what pack/ packs into
python3 build.py --provenance-only   # runs the checks alone
python3 build.py --layout 2          # writes each record compressed with zstd
```

Packing needs Python 3 and a Rust toolchain. `build.py` builds `ee-pack`, the packer in `packer/`,
with `cargo build --release --locked`, then packs with it. `packer/rust-toolchain.toml` names the
Rust version, and `packer/Cargo.lock` the version of every crate. The packer is Pyreal's own
packing code, copied into this repository: it reads the pack as the client reads it, and writes
the same file Pyreal's `pyreal-art pack` writes, byte for byte. It needs nothing else of Pyreal.

`--layout` picks how each record is stored. Layout 1, the default, stores it as it is. Layout 2
stores it compressed with zstd where that is shorter, which is how Pyreal carries its base pack.
The same `pack/` always packs into the same bytes. `--check` therefore shows that a release
matches this repository exactly. Packing reads none of the player's game files.

The generators need Node 20 or newer, Python 3 with numpy and scipy, and ImageMagick (`magick`).
Some generators read the player's own pictures or meshes of the original game, as `dereth-art`
writes them.

## Layout

| Path | What |
|---|---|
| `pack/manifest.toml` | The metadata definition. It says what each asset replaces, lists its levels of detail and credits it. It uses format 1, which the client's `core/assets/src/art_pack.rs` describes. |
| `pack/trees/` | The models (glTF 2.0) and their pictures. |
| `pack/ground/` | The ground pictures. |
| `pack/materials/` | The material pictures. |
| `pack/sky/` | The moon pictures. |
| `pack/grit/` | The shared fine-detail tiles. |
| `generators/` | The scripts that make the assets. |
| `tables/` | The measurements and recipes the generators read. |
| `licenses/` | The licenses of the outside work used here. |
| `docs/` | The README's screenshot. |
| `build.py` | The pack's checks and build. |
| `packer/` | The packer, `ee-pack`, which `build.py` builds and runs. |
| `release.py`, `VERSION` | The release's version and changelog. |
| `.github/workflows/` | The release on every push to `main`, and the pull request check. |

PNG, `.bin` and `.dat` files go through Git LFS (`.gitattributes`).

## Credits

This pack uses openly licensed work. EZ-Tree's MIT license asks that its notice travels with its
work. That notice is in `licenses/EZ-Tree-MIT.txt`. The CC0 works ask for no credit. This section
credits each work.

| Work | By | License | Used for |
|---|---|---|---|
| [ambientCG](https://ambientcg.com) bark | The ambientCG authors and contributors | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) | The bark of the trees and some shaped trees |
| [EZ-Tree](https://github.com/dgreenheck/ez-tree) | Daniel Greenheck | [MIT](https://github.com/dgreenheck/ez-tree/blob/main/LICENSE) | Growing the trees, and its leaf and needle pictures |
| [Stylized Nature MegaKit](https://quaternius.com) | [Quaternius](https://quaternius.com) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) | The ground cover, and the leaves of some shaped plants |

The bark reached this pack through EZ-Tree. EZ-Tree bundles ambientCG's bark textures and credits
each one in its
[texture attribution](https://github.com/dgreenheck/ez-tree/blob/main/src/app/public/textures/LICENSE.md).

## Releases

GitHub builds and releases the pack on every push to `main` that changes it
(`.github/workflows/release.yml`). The workflow packs `pack/` and checks the result with
`build.py --check`. It publishes a release when the pack differs from the last release's file.
Each release carries `enhanced-environment.dat`, its `.sha256` and `CHANGELOG.md`. It also carries
`enhanced-environment.dat.xz`, the same file compressed with xz for a smaller download, and its
`.sha256`. `xz -d enhanced-environment.dat.xz` or 7-Zip gives back the `.dat`.

The version is `VERSION`'s major and minor numbers, then the count of commits since `VERSION` last
changed. `python3 release.py version` prints it. A hand edit to `VERSION` starts a new minor or
major version.

`release.py notes` writes each release's notes. They list the entries added, changed and removed
since the last release, the commits since then, and the `.dat` file's size and SHA-256.
`CHANGELOG.md` holds every release's notes, newest first.

Every pull request runs `build.py --provenance-only` (`.github/workflows/check.yml`). That check
needs none of the LFS files.

The client opens a release's `.dat` with `--art-pack` or from the launcher's Library.

## License

This repository is dedicated to the public domain under [CC0 1.0](LICENSE). Anyone may use it for
any purpose, with or without credit. The packer in `packer/` is copied from Pyreal and is MIT, as
Pyreal is (`packer/LICENSE`). The outside work above keeps its own license. ambientCG's and
Quaternius's work is CC0. EZ-Tree's work is MIT (`licenses/EZ-Tree-MIT.txt`).
