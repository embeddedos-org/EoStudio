#!/usr/bin/env python3
"""Inventory the components of a KiCad schematic (.kicad_sch).

Reads the S-expression schematic directly (no KiCad needed) and prints
one line per symbol: reference, value, footprint, datasheet.

Usage:
    sch_inventory.py board/main.kicad_sch
    sch_inventory.py board/main.kicad_sch --json

Exit codes: 0 on success; 2 if the file cannot be parsed (never guess).
"""
import json
import re
import sys


def parse_sexp(text):
    """Minimal S-expression parser for KiCad schematics."""
    tokens = re.findall(r'\(|\)|"[^"]*"|[^\s()]+', text)
    stack = []
    root = []
    cur = root
    for tok in tokens:
        if tok == '(':
            node = []
            cur.append(node)
            stack.append(cur)
            cur = node
        elif tok == ')':
            if not stack:
                raise ValueError("unbalanced parens")
            cur = stack.pop()
        else:
            cur.append(tok.strip('"'))
    if stack:
        raise ValueError("unbalanced parens")
    return root


def find_symbols(node, out):
    if isinstance(node, list):
        if node and node[0] == 'symbol':
            out.append(node)
        for child in node:
            find_symbols(child, out)
    return out


def prop(symbol, name):
    for child in symbol:
        if isinstance(child, list) and child[:2] == ['property', name]:
            for grand in child[2:]:
                if isinstance(grand, str):
                    return grand
    return ""


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    as_json = '--json' in sys.argv[1:]
    if not args:
        print("usage: sch_inventory.py <schematic.kicad_sch> [--json]", file=sys.stderr)
        return 2
    path = args[0]
    try:
        text = open(path, encoding='utf-8').read()
    except OSError as e:
        print(f"error: cannot read {path}: {e}", file=sys.stderr)
        return 2
    try:
        sexp = parse_sexp(text)
    except ValueError as e:
        print(f"error: cannot parse {path}: {e}", file=sys.stderr)
        return 2
    symbols = find_symbols(sexp, [])
    rows = []
    for sym in symbols:
        # Skip unit variants (symbol instances); keep the library symbols
        # that carry Reference/Value/Footprint properties.
        ref = prop(sym, "Reference")
        if not ref or ref.startswith("#"):
            continue
        rows.append({
            "reference": ref,
            "value": prop(sym, "Value"),
            "footprint": prop(sym, "Footprint"),
            "datasheet": prop(sym, "Datasheet"),
        })
    rows.sort(key=lambda r: r["reference"])
    if as_json:
        print(json.dumps(rows, indent=2))
    else:
        for r in rows:
            print(f"{r['reference']:8s} {r['value']:24s} {r['footprint']:40s} {r['datasheet']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
