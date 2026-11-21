#!/usr/bin/env python3
# Packs pack/ into dist/enhanced-environment.dat with ee-pack (packer/), after checking that everything
# in it says who made it, with what and under which license, and that none of it is the original game's art.
#   python3 build.py [--check] [--provenance-only] [--layout N]
# --check: say whether dist/enhanced-environment.dat is what pack/ packs into, and write nothing.
# --layout: 1, each record stored as it is (the default), or 2, each compressed with zstd.
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.join(HERE, 'pack')
PACKER = os.path.join(HERE, 'packer')
OUT = os.path.join(HERE, 'dist', 'enhanced-environment.dat')

# What an entry's tool must name: a generator in generators/, or a hand.
HAND = 'By hand'
# The licenses an entry may carry: ours, and those of the outside work the README credits.
LICENSES = {'CC0-1.0', 'MIT'}
# What an author must not be: the original game's art is the player's, not ours to ship.
REFUSED = re.compile(r'retail|turbine|asheron', re.I)
# Folders whose files are kept for entries to come, though nothing names them yet.
KEPT = ('grit/',)


def entries(path):
    """The manifest's tables, each with its [[model.lod]] tables under `lod`: its plain layout only."""
    out, cur, target = [], None, None
    for line in open(path):
        line = line.split(' #')[0].rstrip()
        if not line.strip():
            continue
        m = re.match(r'^\[\[(\w+)\.lod\]\]$', line) or re.match(r'^\[\[?(\w+)\]\]?$', line)
        if m and line.endswith('.lod]]'):
            target = {}
            cur.setdefault('lod', []).append(target)
        elif m:
            cur = target = {'kind': m.group(1)}
            out.append(cur)
        else:
            k, _, v = line.partition('=')
            v = v.strip()
            target[k.strip()] = json.loads(v) if v[:1] in '"[' else v
    return out


def drawn_as_eor():
    """The older eras' pictures Pyreal draws as End of Retail's, as (era, picture): tables/drawn-as-eor.tsv."""
    out = set()
    for line in open(os.path.join(HERE, 'tables', 'drawn-as-eor.tsv')):
        if line.strip() and not line.startswith('#'):
            out |= {tuple(x.split(':')) for x in line.rstrip('\n').split('\t')[4].split() if x != '-'}
    return out


def provenance():
    """Why the pack may not be shipped, one line a reason."""
    why = []
    es = entries(os.path.join(PACK, 'manifest.toml'))
    eor = drawn_as_eor()
    pack = next((e for e in es if e['kind'] == 'pack'), {})
    if pack.get('format') != '1':
        why.append('manifest: [pack] must be format = 1')
    named = {'manifest.toml'}
    for e in es:
        if e['kind'] == 'pack':
            continue
        label = f"{e['kind']} {e.get('id') or e.get('texture') or e.get('surface') or e.get('object') or e.get('ground')}"
        tool, author, lic = e.get('tool'), e.get('author'), e.get('license')
        if not (tool and author and lic):
            why.append(f'{label}: no author, tool or license')
            continue
        if REFUSED.search(author):
            why.append(f'{label}: its author is the original game: {author!r}')
        named_licenses = set(re.findall(r'[A-Za-z0-9.-]+-\d\.\d|MIT', lic))
        if not named_licenses or not named_licenses <= LICENSES:
            why.append(f'{label}: license {lic!r}, not one of {sorted(LICENSES)}')
        scripts = re.findall(r'[\w-]+\.(?:py|mjs)', tool)
        if tool != HAND and (not scripts or not all(
                os.path.isfile(os.path.join(HERE, 'generators', s)) for s in scripts)):
            why.append(f'{label}: its tool {tool!r} names no script in generators/')
        if e['kind'] in ('material', 'solid') and 'base_color' not in e:
            why.append(f'{label}: no base_color, which format 1 needs')
        era = re.match(r'materials/(\d{4})/', e.get('base_color', ''))
        if e['kind'] == 'material' and era and (era[1], e.get('texture')) in eor:
            why.append(f'{label}: Pyreal draws End of Retail\'s picture for it in {era[1]} (tables/drawn-as-eor.tsv)')
        if (e['kind'] == 'material' and tool == 'relief.py' and not float(e.get('damp') or 0)
                and not {'normal', 'height', 'metal', 'metal_map', 'damp_map'} & set(e)):
            why.append(f'{label}: adds nothing to the retail picture, which the client draws as it is')
        for k, v in e.items():
            if isinstance(v, str) and re.match(r'^[\w./-]+\.(png|gltf|bin)$', v):
                named.add(v)
        for lod in e.get('lod', []):
            named.add(lod['file'])
            doc = json.load(open(os.path.join(PACK, lod['file'])))
            d = os.path.dirname(lod['file'])
            for ref in [b['uri'] for b in doc.get('buffers', [])] + [i.get('uri', '') for i in doc.get('images', [])]:
                if not ref or ref.startswith('data:'):
                    why.append(f'{label}: {lod["file"]} carries data inside it, not in a file of the pack')
                    continue
                named.add(os.path.normpath(os.path.join(d, ref)))
    for f in sorted(named):
        if not os.path.isfile(os.path.join(PACK, f)):
            why.append(f'{f}: named, but not in pack/')
    for root, _, files in os.walk(PACK):
        for name in files:
            f = os.path.relpath(os.path.join(root, name), PACK)
            if f not in named and not f.startswith(KEPT) and name != '.DS_Store':
                why.append(f'{f}: in pack/ but nothing names it')
    return why


def unsynced(folder):
    """Make `folder`, kept out of Dropbox's sync on a Mac: what is built there is made again at will."""
    os.makedirs(folder, exist_ok=True)
    if sys.platform == 'darwin':
        subprocess.run(['xattr', '-w', 'com.apple.fileprovider.ignore#P', '1', folder], capture_output=True)


def packer():
    """The packer, built from packer/ in release when it is not already."""
    unsynced(os.path.join(PACKER, 'target'))
    # Run in packer/, so rustup takes the toolchain packer/rust-toolchain.toml names.
    built = subprocess.run(['cargo', 'build', '--release', '--locked', '--manifest-path',
                            os.path.join(PACKER, 'Cargo.toml'), '--message-format=json-render-diagnostics'],
                           cwd=PACKER, stdout=subprocess.PIPE, check=True, text=True)
    for line in built.stdout.splitlines():
        message = json.loads(line)
        if message.get('reason') == 'compiler-artifact' and message.get('executable'):
            return message['executable']
    sys.exit('build.py: cargo built no ee-pack')


def main(args):
    layout = args[args.index('--layout') + 1] if '--layout' in args else '1'
    why = provenance()
    if why:
        print('The pack is not shipped as it stands:', *why, sep='\n  ', flush=True)
        return 1
    print('provenance: every entry is generated or made by hand, and credited', flush=True)
    if '--provenance-only' in args:
        return 0
    unsynced(os.path.dirname(OUT))
    command = [packer(), PACK, '--out', OUT, '--layout', layout] + (['--check'] if '--check' in args else [])
    return subprocess.run(command).returncode


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
