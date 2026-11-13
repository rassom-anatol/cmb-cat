#!/usr/bin/env python3
"""
Parse and compare KiCad s-expression files (.kicad_mod / .kicad_sch / .kicad_sym).

Exists because regex with a fixed character window silently captures fields from
neighbouring elements and silently misses them when formatting changes. Three false
findings came from that before this was written.

Usage:
    python3 tools/kisexp.py diff OLD.kicad_mod NEW.kicad_mod
    python3 tools/kisexp.py dump FILE.kicad_mod
"""
import re, sys, collections

TOK = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')

def parse(text):
    toks = TOK.findall(text)
    def build(i):
        out = []
        while i < len(toks):
            t = toks[i]
            if t == '(':
                sub, i = build(i + 1); out.append(sub)
            elif t == ')':
                return out, i + 1
            else:
                out.append(t); i += 1
        return out, i
    tree, _ = build(0)
    return tree[0] if len(tree) == 1 else tree

def walk(node):
    if isinstance(node, list):
        yield node
        for child in node:
            yield from walk(child)

def _xy(node, *keys):
    pts = []
    for c in node:
        if isinstance(c, list) and c:
            if c[0] in keys and len(c) >= 3:
                pts.append((float(c[1]), float(c[2])))
            elif c[0] == 'pts':
                pts += [(float(p[1]), float(p[2])) for p in c[1:]
                        if isinstance(p, list) and p and p[0] == 'xy']
    return tuple(pts)

def _field(node, name, idx=1):
    for c in node:
        if isinstance(c, list) and c and c[0] == name and len(c) > idx:
            return c[idx].strip('"')
    return None

def pads(root):
    """(number, type, shape, x, y, size, layers) per pad — manufacturing-critical."""
    out = []
    for n in walk(root):
        if n and n[0] == 'pad':
            at = _xy(n, 'at')
            size = next((tuple(float(v) for v in c[1:3]) for c in n
                         if isinstance(c, list) and c and c[0] == 'size'), None)
            layers = next((' '.join(sorted(x.strip('"') for x in c[1:])) for c in n
                           if isinstance(c, list) and c and c[0] == 'layers'), '')
            out.append((n[1].strip('"'), n[2], n[3], at, size, layers))
    return sorted(out)

def graphics(root):
    """(kind, layer, coords) per fp_* graphic — silk/courtyard/fab."""
    out = []
    for n in walk(root):
        if n and isinstance(n[0], str) and n[0].startswith('fp_'):
            out.append((n[0], _field(n, 'layer'), _xy(n, 'start', 'end', 'center', 'mid')))
    return sorted(out)

def extents(root):
    by = collections.defaultdict(list)
    for kind, layer, cs in graphics(root):
        by[layer] += list(cs)
    return {L: (round(max(x for x, _ in v) - min(x for x, _ in v), 4),
                round(max(y for _, y in v) - min(y for _, y in v), 4))
            for L, v in by.items() if v}

def compare(a_text, b_text):
    a, b = parse(a_text), parse(b_text)
    pa, pb = pads(a), pads(b)
    ga, gb = collections.Counter(graphics(a)), collections.Counter(graphics(b))
    return {
        'pads_identical': pa == pb,
        'pads': (len(pa), len(pb)),
        'graphics_removed': list((ga - gb).elements()),
        'graphics_added': list((gb - ga).elements()),
        'extents_a': extents(a), 'extents_b': extents(b),
    }

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'dump'
    if cmd == 'diff':
        r = compare(open(sys.argv[2]).read(), open(sys.argv[3]).read())
        print(f"pads {r['pads'][0]} -> {r['pads'][1]}, identical: {r['pads_identical']}")
        print(f"graphics removed {len(r['graphics_removed'])}, added {len(r['graphics_added'])}")
        for e in r['graphics_removed'][:10]: print(f"   - {e[0]:<10} {e[1]} {e[2]}")
        for e in r['graphics_added'][:10]:   print(f"   + {e[0]:<10} {e[1]} {e[2]}")
        if r['extents_a'] != r['extents_b']:
            print(f"extents differ:\n   old {r['extents_a']}\n   new {r['extents_b']}")
        else:
            print(f"extents identical: {r['extents_a']}")
    else:
        root = parse(open(sys.argv[2]).read())
        print(f"{len(pads(root))} pads, {len(graphics(root))} graphics")
        for L, e in sorted(extents(root).items()): print(f"   {L:<10} {e[0]} x {e[1]}")
