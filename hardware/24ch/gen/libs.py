"""Load symbol definitions from KiCad libraries and flatten 'extends'."""
import copy
import os
from sexp import parse, find, findall, Sym

KICAD_SYM = r"C:\Program Files\KiCad\10.0\share\kicad\symbols"
_cache = {}


def _lib(path):
    if path not in _cache:
        with open(path, encoding="utf-8") as f:
            tree = parse(f.read())
        _cache[path] = {s[1]: s for s in findall(tree, "symbol")}
    return _cache[path]


def _path(lib, local_dir):
    p = os.path.join(local_dir, lib + ".kicad_sym") if local_dir else None
    if p and os.path.exists(p):
        return p
    return os.path.join(KICAD_SYM, lib + ".kicad_sym")


def load(lib_id, local_dir=None):
    """Return a flattened symbol node renamed to 'Lib:Name'."""
    lib, name = lib_id.split(":")
    syms = _lib(_path(lib, local_dir))
    node = copy.deepcopy(syms[name])
    ext = find(node, "extends")
    if ext:
        parent = copy.deepcopy(syms[ext[1]])
        pname = ext[1]
        props = {p[1]: p for p in findall(node, "property")}
        body = []
        for x in parent[2:]:
            if isinstance(x, list) and x[0] == "property" and x[1] in props:
                body.append(props.pop(x[1]))
            elif isinstance(x, list) and x[0] == "symbol":
                x[1] = name + x[1][len(pname):]
                body.append(x)
            else:
                body.append(x)
        body += list(props.values())
        node = [Sym("symbol"), name] + body
    node[1] = lib_id
    return node


def pins(node):
    """{number: (name, x, y, angle, unit, type)} in library coordinates (y up)."""
    out = {}
    for sub in findall(node, "symbol"):
        tail = sub[1].rsplit("_", 2)
        unit = int(tail[-2]) if len(tail) >= 3 and tail[-2].isdigit() else 0
        for p in findall(sub, "pin"):
            at = find(p, "at")
            num = find(p, "number")[1]
            nm = find(p, "name")[1]
            out.setdefault(num, (nm, float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0, unit, str(p[1])))
    return out


def bbox(node):
    xs, ys = [], []
    for num, (nm, x, y, a, u, t) in pins(node).items():
        xs.append(x); ys.append(y)
    for sub in findall(node, "symbol"):
        for rect in findall(sub, "rectangle"):
            s, e = find(rect, "start"), find(rect, "end")
            xs += [float(s[1]), float(e[1])]; ys += [float(s[2]), float(e[2])]
        for poly in findall(sub, "polyline"):
            for xy in findall(find(poly, "pts") or [], "xy"):
                xs.append(float(xy[1])); ys.append(float(xy[2]))
        for circ in findall(sub, "circle"):
            c, r = find(circ, "center"), find(circ, "radius")
            xs += [float(c[1]) - float(r[1]), float(c[1]) + float(r[1])]
            ys += [float(c[2]) - float(r[1]), float(c[2]) + float(r[1])]
    if not xs:
        return (-2.54, -2.54, 2.54, 2.54)
    return (min(xs), min(ys), max(xs), max(ys))
