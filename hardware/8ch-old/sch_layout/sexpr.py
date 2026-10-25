"""Minimal S-expression reader/writer for KiCad files (I-062).

Enough to move whole items between schematic files without touching what is
inside them. Not kiutils on purpose: docs/TOOLS.md forbids installing it,
because it breaks kicad-tool.

A node is a Python list: ["wire", ["pts", ...], ...]. Atoms stay strings;
quoted strings keep their quotes, so writing a tree back reproduces the
input's tokens exactly. KiCad reformats the file on its next save anyway.
"""
import re

_TOKEN = re.compile(r'\s*(?:(\()|(\))|("(?:[^"\\]|\\.)*")|([^\s()"]+))', re.S)


def parse(text):
    stack, top = [], None
    pos, end = 0, len(text.rstrip())
    while pos < end:
        m = _TOKEN.match(text, pos)
        if not m:
            raise ValueError(f"cannot tokenise at {pos}: {text[pos:pos + 40]!r}")
        pos = m.end()
        opened, closed, quoted, atom = m.groups()
        if opened:
            node = []
            if stack:
                stack[-1].append(node)
            stack.append(node)
        elif closed:
            top = stack.pop()
        else:
            stack[-1].append(quoted if quoted is not None else atom)
    if stack:
        raise ValueError("unbalanced parentheses")
    return top


def dump(node, indent=0):
    """Write a node the way KiCad does: one child list per line, tabs."""
    pad = "\t" * indent
    i = 0
    while i < len(node) and not isinstance(node[i], list):
        i += 1
    if i == len(node):
        return f"{pad}({' '.join(node)})"
    lines = [f"{pad}({' '.join(node[:i])}"]
    for x in node[i:]:
        lines.append(dump(x, indent + 1) if isinstance(x, list) else f"{pad}\t{x}")
    lines.append(f"{pad})")
    return "\n".join(lines)


def unq(s):
    return s[1:-1].replace('\\"', '"') if s.startswith('"') else s


def q(s):
    return '"' + s.replace('"', '\\"') + '"'


def find(node, key):
    """First child list whose head is key, or None."""
    for x in node:
        if isinstance(x, list) and x and x[0] == key:
            return x
    return None


def find_all(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


def prop(symbol, name):
    """Value of a symbol property, unquoted."""
    for p in find_all(symbol, "property"):
        if unq(p[1]) == name:
            return unq(p[2])
    return None


def at(node):
    a = find(node, "at")
    return (float(a[1]), float(a[2])) if a else None
