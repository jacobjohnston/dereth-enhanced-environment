#!/usr/bin/env python3
# The manifest's era variants. A [[model]] or [[material]] for an id another entry of its kind already
# has goes under [variant] ([[variant.model]] with its [[variant.model.lod]], [[variant.material]]), which
# the Dereth client doesn't read, so it finds each id once (README, "Variants"). Pyreal reads the
# variants after the main tables, as if listed after them, so moving one changes nothing it draws.
# The entry left in the main table is the first listed: the one Pyreal draws on a record whose fingerprint
# it can't tell (a record an era's files don't hold), and for every material End of Retail's.
#   python3 variants.py <manifest.toml>   settles the manifest in place; a second run changes nothing.
# A generator reads the manifest with flat() and writes it with settle().
import json, re, sys

KINDS = ('model', 'material')


def blocks(text):
    """The text before the first table, and each table cut from the next as (its header, its text)."""
    cuts = [m.start() for m in re.finditer(r'(?m)^\[\[?[\w.]+\]\]?[ \t]*$', text)]
    if not cuts:
        return text, []
    return text[:cuts[0]], [(text[a:b].split('\n', 1)[0].strip(), text[a:b]) for a, b in zip(cuts, cuts[1:] + [len(text)])]


def join(head, listed):
    text = head
    for _, b in listed:
        if text and not text.endswith('\n'):
            text += '\n'
        if text and not text.endswith('\n\n'):
            text += '\n'
        text += b
    return text.rstrip('\n') + '\n'


def flat(text):
    """`text` with its variants back as [[model]] and [[material]] tables, each after the last main entry
    of its kind (at the end where there is none): the order Pyreal reads."""
    head, listed = blocks(text)
    main, variants = [], {}
    for h, b in listed:
        if h.startswith('[[variant.'):
            plain = '[[' + h[len('[[variant.'):]
            variants.setdefault(plain.strip('[]').split('.')[0], []).append((plain, plain + b[len(h):]))
        else:
            main.append((h, b))
    if not variants:
        return text
    at = {kind: max((k + 1 for k, (h, _) in enumerate(main) if h.strip('[]').split('.')[0] == kind), default=len(main))
          for kind in variants}
    for kind in sorted(variants, key=lambda k: -at[k]):
        main[at[kind]:at[kind]] = variants[kind]
    return join(head, main)


def units(listed):
    """The tables as entries: a [[model]] with its [[model.lod]] tables, or one table."""
    out = []
    for h, b in listed:
        if h == '[[model.lod]]' and out and out[-1][0] == '[[model]]':
            out[-1] = (out[-1][0], out[-1][1] + [(h, b)])
        else:
            out.append((h, [(h, b)]))
    return out


def ids(kind, block):
    m = re.search(r'^(?:id|texture) = (.*)$', block, re.M)
    if not m:
        return []
    v = json.loads(m.group(1).split(' #')[0])
    return v if isinstance(v, list) else [v]



def settle(text):
    """`text` with each entry that repeats an earlier entry's id moved under [variant], after the other tables."""
    head, listed = blocks(flat(text))
    entries = units(listed)
    at = {}
    for k, (h, entry) in enumerate(entries):
        kind = h.strip('[]')
        if kind in KINDS:
            for i in ids(kind, entry[0][1]):
                at.setdefault((kind, i), []).append(k)
    keeper = {key: ks[0] for key, ks in at.items()}
    variant = set()
    for k, (h, entry) in enumerate(entries):
        kind = h.strip('[]')
        if kind not in KINDS:
            continue
        kept = [keeper[(kind, i)] == k for i in ids(kind, entry[0][1])]
        if any(kept) and not all(kept):
            sys.exit(f'variants.py: {h} {ids(kind, entry[0][1])} is the main entry for some of its pictures and a variant '
                     'for others; give the repeated pictures an entry of their own')
        if not any(kept):
            variant.add(k)
    main = [t for k, (_, e) in enumerate(entries) if k not in variant for t in e]
    moved = [('[[variant.' + h[2:], '[[variant.' + b[2:]) for k, (_, e) in enumerate(entries) if k in variant for h, b in e]
    return join(head, main + moved)


if __name__ == '__main__':
    path = sys.argv[1]
    text = open(path).read()
    out = settle(text)
    if out != text:
        open(path, 'w').write(out)
    print(f'{path}: {out.count("[[variant.")} variant tables')
