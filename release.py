#!/usr/bin/env python3
# The release's version and its changelog, worked out from git, and its compressed download.
#   python3 release.py version                       the version in VERSION, written by hand for each
#                                                    release (major.minor.patch)
#   python3 release.py compress                      dist/enhanced-environment.dat.xz, the .dat
#                                                    compressed with xz (`xz -d` restores it)
#   python3 release.py notes <previous tag> <out>    what changed since the previous release
#   python3 release.py changelog <notes> <old> <out> the notes above the previous CHANGELOG.md
# <previous tag> may be '-' for the first release, and <old> '-' when there is no changelog yet.
import hashlib, json, lzma, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'generators'))
import variants
MANIFEST = 'pack/manifest.toml'
DAT = os.path.join(HERE, 'dist', 'enhanced-environment.dat')
XZ = DAT + '.xz'
# How many entries a kind lists by name before it only counts the rest.
LISTED = 25
# What each kind of entry is called, one and many.
KINDS = {'model': ('model', 'models'), 'material': ('material', 'materials'),
         'ground_cover': ('ground cover', 'ground covers'), 'light': ('light', 'lights'),
         'moon': ('moon', 'moons'), 'terrain': ('ground material', 'ground materials'),
         'steep': ('slope material', 'slope materials'), 'fall': ('waterfall model', 'waterfall models')}


def git(*args):
    return subprocess.run(['git', *args], cwd=HERE, capture_output=True, text=True, check=True).stdout


def version():
    text = open(os.path.join(HERE, 'VERSION')).read().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+', text):
        sys.exit(f'VERSION should be major.minor.patch, such as 0.5.3, not {text!r}')
    return text


def entries(text):
    """Each manifest entry by what it stands for (kind, id and which of the id's entries, its variants
    after the main tables'), with its text and the files it names."""
    out, seen = {}, {}
    for block in re.split(r'\n(?=\[(?:\[(?!model\.lod)[a-z_]+\]|pack)\])', variants.flat(text)):
        head = block.lstrip().split('\n', 1)[0].strip('[]')
        if head == 'pack':
            continue
        name = re.search(r'^(?:id|texture|object|ground|surface|file) = (.+)$', block, re.M)
        lod = re.search(r'^file = "([^"]+)"', block, re.M)
        key = (head, (name[1] if head != 'ground_cover' else os.path.basename(lod[1]).split('_lod')[0] if lod else '?').strip('"'))
        seen[key] = n = seen.get(key, -1) + 1
        out[key + (n,)] = (block.strip(), set(re.findall(r'= "([^"]+\.(?:png|gltf|bin|fall))"', block)))
    return out


def named_by_models(files):
    """`files`, with the buffers and pictures the glTF models among them name, as they are now."""
    out = set(files)
    for f in files:
        if f.endswith('.gltf') and os.path.isfile(os.path.join(HERE, 'pack', f)):
            doc = json.load(open(os.path.join(HERE, 'pack', f)))
            d = os.path.dirname(f)
            for ref in [b['uri'] for b in doc.get('buffers', [])] + [i.get('uri', '') for i in doc.get('images', [])]:
                out.add(os.path.normpath(os.path.join(d, ref)))
    return out


def listed(keys):
    names = sorted(k[1] for k in keys)
    shown = ', '.join(f'`{n}`' for n in names[:LISTED])
    return shown + (f' and {len(names) - LISTED} more' if len(names) > LISTED else '')


def notes(previous, out):
    v = version()
    now = entries(open(os.path.join(HERE, MANIFEST)).read())
    was = entries(git('show', f'{previous}:{MANIFEST}')) if previous != '-' else {}
    changed_files = set()
    if previous != '-':
        changed_files = {f[len('pack/'):] for f in git('diff', '--name-only', f'{previous}..HEAD', '--', 'pack').split()}
    lines = [f'## {v}', '']
    kinds = sorted({k[0] for k in now} | {k[0] for k in was})
    pack = []
    for kind in kinds:
        added = [k for k in now if k[0] == kind and k not in was]
        gone = [k for k in was if k[0] == kind and k not in now]
        moved = [k for k in now if k[0] == kind and k in was
                 and (now[k][0] != was[k][0] or named_by_models(now[k][1]) & changed_files)]
        for what, keys in (('added', added), ('changed', moved), ('removed', gone)):
            if keys:
                one, many = KINDS.get(kind, (kind, kind))
                pack.append(f'- {len(keys)} {one if len(keys) == 1 else many} {what}: {listed(keys)}')
    lines += ['### The pack', ''] + (pack or ['- Nothing in the pack changed.']) + ['']
    log = git('log', '--no-merges', '--format=- %s (%h)', f'{previous}..HEAD' if previous != '-' else 'HEAD').strip()
    lines += ['### Commits', '', log or '- None.', '']
    if os.path.isfile(DAT):
        digest = hashlib.sha256(open(DAT, 'rb').read()).hexdigest()
        lines += [f'`enhanced-environment.dat`: {os.path.getsize(DAT) // 2 ** 20} MB, SHA-256 `{digest}`', '']
    if os.path.isfile(XZ):
        lines += [f'`enhanced-environment.dat.xz`: {os.path.getsize(XZ) // 2 ** 20} MB, the same file compressed', '']
    open(out, 'w').write('\n'.join(lines))


HEADING = '# Changelog\n\nEvery release of the Enhanced Environment pack, newest first.\n\n'


def compress():
    # xz's strongest preset: 8% smaller than zstd -19 --long, and it decodes in seconds.
    with open(DAT, 'rb') as src, lzma.open(XZ, 'wb', preset=9 | lzma.PRESET_EXTREME) as out:
        shutil.copyfileobj(src, out, 2 ** 20)


def changelog(new, old, out):
    body = open(old).read() if old != '-' and os.path.isfile(old) else ''
    body = body[len(HEADING):] if body.startswith(HEADING) else body
    open(out, 'w').write(HEADING + open(new).read().rstrip() + '\n\n' + body.lstrip())


if __name__ == '__main__':
    command, *args = sys.argv[1:]
    if command == 'version':
        print(version())
    elif command == 'notes':
        notes(*args)
    elif command == 'changelog':
        changelog(*args)
    elif command == 'compress':
        compress()
    else:
        sys.exit(f'unknown command {command}')
