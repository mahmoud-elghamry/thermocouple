"""Split the flat wired sheet into an A4 root, a channel sheet used eight
times (I-062) and four functional sheets (funcsheets.py, 0021).

    python hardware/8ch/sch_layout/hier.py FLAT.kicad_sch FLAT.net OUTDIR

FLAT is the wired single-sheet schematic that build.py produces, FLAT.net
its kicad-cli netlist. OUTDIR receives thermocouple_8ch.kicad_sch (the root)
and channel.kicad_sch.

The eight channels were drawn from one template (channel.py), so they are
one drawing placed eight times. This checks that first - every symbol of
channel n must sit exactly where channel 1's does, shifted, with as many
wires, labels and no-connects - and refuses to split otherwise. Channel 1 then becomes channel.kicad_sch, used by eight
sheet blocks TC1..TC8; each symbol in it carries eight instances with that
channel's real reference, so U2..U9, JTC1..JTC8 and the board are unchanged.

Only seven nets leave a channel (measured 2026-09-26). Inside the sheet they
become hierarchical labels; on the root, each sheet pin is wired to a label
with the net's old name, so those nets keep their names. The nets internal
to a channel are renamed, /TC1_FILT_P -> /TC1/FILT_P and so on
(docs/decisions/0019). funcsheets.py then moves the rest onto four A4 sheets
the same way, and the root becomes an A4 page of sheet blocks (0021).
"""
import copy, os, sys, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import sexpr as S
import rootlayout
import funcsheets
from netlist_fingerprint import fingerprint
from pathlib import Path

PROJECT = "thermocouple_8ch"
CHANNEL_FILE = "channel.kicad_sch"
G = 1.27
# net as it leaves the channel -> (sheet pin / hierarchical label, shape)
PINS = [("CS{n}_SENS", "CS", "input"), ("SCK_SENS", "SCK_SENS", "input"),
        ("MOSI_SENS", "MOSI_SENS", "input"), ("MISO_SENS", "MISO_SENS", "output"),
        ("+3V3_SENS", "+3V3_SENS", "passive"), ("GND_SENS", "GND_SENS", "passive"),
        ("CHASSIS_SHIELD", "CHASSIS_SHIELD", "passive")]
NS = uuid.UUID("5b1e1c7a-0f5e-4c55-9a38-7e1d8f3f0c62")


def uid(*parts):
    return str(uuid.uuid5(NS, "/".join(parts)))


def ref_of(sym):
    inst = S.find(S.find(S.find(sym, "instances"), "project"), "path")
    return S.unq(S.find(inst, "reference")[1])


def roles(netfile):
    """{channel: {role: ref}} from the netlist - the same roles as channel.py."""
    nets = {k.lstrip("/"): v for k, v in fingerprint(Path(netfile))["nets"].items()}
    pin = {p: n for n, ps in nets.items() for p in ps}
    refs = lambda net: {p.split(".")[0] for p in nets[net]}
    out = {}
    for n in range(1, 9):
        P, N, RP, RN = (f"TC{n}_FILT_P", f"TC{n}_FILT_N", f"TC{n}_RAW_P", f"TC{n}_RAW_N")
        two = lambda a, b, pre: [r for r in refs(a) & refs(b) if r.startswith(pre)]
        U = f"U{n + 1}"
        cs, miso = pin[f"{U}.9"], pin[f"{U}.11"]
        m = {"J": f"JTC{n}", "U": U, "C4": f"C{5 * n - 1}", "C5": f"C{5 * n}",
             "R1": two(RP, P, "R"), "R2": two(RN, N, "R"), "C1": two(P, N, "C"),
             "C2": two(P, "GND_SENS", "C"), "C3": two(N, "GND_SENS", "C"),
             "D7": [r for r in refs(P) if pin.get(f"{r}.3") == P and r.startswith("D")],
             "D8": [r for r in refs(N) if pin.get(f"{r}.3") == N and r.startswith("D")],
             "Rpu": two(cs, "+3V3_SENS", "R"),
             "Rs": [r for r in refs(miso) if r.startswith("R")]}
        for k, v in m.items():
            if isinstance(v, list):
                if len(v) != 1:
                    raise SystemExit(f"channel {n}: role {k} matched {v}")
                m[k] = v[0]
        out[n] = m
    return out


def points(item):
    if item[0] == "wire":
        return [(float(p[1]), float(p[2])) for p in S.find_all(S.find(item, "pts"), "xy")]
    return [S.at(item)]


def shifted(item, dx, dy):
    """Deep copy with every (at x y ...) and (xy x y) moved by dx, dy."""
    new = copy.deepcopy(item)

    def walk(node):
        for x in node:
            if isinstance(x, list):
                if x and x[0] in ("at", "xy") and len(x) >= 3:
                    x[1] = f"{float(x[1]) + dx:.4f}".rstrip("0").rstrip(".")
                    x[2] = f"{float(x[2]) + dy:.4f}".rstrip("0").rstrip(".")
                else:
                    walk(x)
    walk(new)
    return new


def key(item, dx=0.0, dy=0.0):
    """Geometry of an item, for comparing channel n with channel 1."""
    pts = tuple(sorted((round(x - dx, 2), round(y - dy, 2)) for x, y in points(item)))
    a = S.find(item, "at")
    rot = a[3] if a is not None and len(a) > 3 else "0"
    return (item[0], pts, rot)


def label_text(text, n):
    """Channel-n label -> the name it carries inside channel.kicad_sch."""
    for net, pin, _ in PINS:
        if text == net.format(n=n):
            return pin, True
    for old, new in ((f"TC{n}_", ""), (f"MISO_CH{n}", "MISO_CH")):
        if text.startswith(old):
            return new + text[len(old):], False
    raise SystemExit(f"channel {n}: label {text!r} has no mapping")


def split_channels(tree, role):
    """Assign every symbol, wire, label and no-connect to a channel or root."""
    syms = {ref_of(s): s for s in S.find_all(tree, "symbol")}
    box = {}
    for n, m in role.items():
        xs = [S.at(syms[r])[0] for r in m.values()]
        ys = [S.at(syms[r])[1] for r in m.values()]
        # tight: channel 8 labels end at x 278, the MCU block starts at 287
        box[n] = (min(xs) - 12, min(ys) - 12, max(xs) + 6, max(ys) + 12)
    owner = {r: n for n, m in role.items() for r in m.values()}
    chan = {n: [] for n in role}
    root = []
    for item in tree:
        if not isinstance(item, list) or item[0] not in ("symbol", "wire", "label", "no_connect"):
            continue
        if item[0] == "symbol":
            n = owner.get(ref_of(item))
        else:
            hits = {n for n, (x0, y0, x1, y1) in box.items()
                    for x, y in points(item) if x0 <= x <= x1 and y0 <= y <= y1}
            if len(hits) > 1 or (hits and not all(
                    box[next(iter(hits))][0] <= x <= box[next(iter(hits))][2]
                    and box[next(iter(hits))][1] <= y <= box[next(iter(hits))][3]
                    for x, y in points(item))):
                raise SystemExit(f"{item[0]} crosses a channel boundary: {points(item)}")
            n = next(iter(hits)) if hits else None
        (chan[n] if n else root).append(item)
    return chan, root, syms


def verify_identical(chan, role, syms):
    """Channel n must be channel 1 shifted, or reuse would change the drawing."""
    # Symbols must sit exactly as in channel 1. Wires need not: route.py made
    # small per-channel choices (a jog 1.27 mm over, a label turned 270 not
    # 90), so channel 1's wiring is drawn for all eight. That is proved
    # electrically afterwards - the split netlist must match the flat one pin
    # for pin (netlist_fingerprint.py --allow-renames) - not geometrically.
    u1 = S.at(syms[role[1]["U"]])
    counts = sorted(key(i)[0] for i in chan[1])
    for n in range(2, 9):
        un = S.at(syms[role[n]["U"]])
        dx, dy = un[0] - u1[0], un[1] - u1[1]
        if sorted(key(i)[0] for i in chan[n]) != counts:
            raise SystemExit(f"channel {n} has a different number of items than channel 1")
        for r, ref in role[n].items():
            a, b = S.find(syms[role[1][r]], "at"), S.find(syms[ref], "at")
            if (round(float(b[1]) - dx, 2), round(float(b[2]) - dy, 2), b[3:]) != \
                    (round(float(a[1]), 2), round(float(a[2]), 2), a[3:]):
                raise SystemExit(f"channel {n}: {ref} is not placed like {role[1][r]}")
    return u1


def channel_sheet(tree, chan, role, root_uuid):
    items = chan[1]
    xs = [x for i in items for x, _ in points(i)]
    ys = [y for i in items for _, y in points(i)]
    # centre the block on A4 (297 x 210), staying on the 1.27 mm grid
    dx = round((148.5 - (min(xs) + max(xs)) / 2) / G) * G
    dy = round((105.0 - (min(ys) + max(ys)) / 2) / G) * G
    body, libs = [], set()
    by_role = {role[1][r]: r for r in role[1]}
    for item in items:
        new = shifted(item, dx, dy)
        if new[0] == "symbol":
            libs.add(S.unq(S.find(new, "lib_id")[1]))
            r = by_role[ref_of(item)]
            paths = [["path", S.q(f"/{root_uuid}/{uid('sheet', f'TC{n}')}"),
                      ["reference", S.q(role[n][r])], ["unit", "1"]] for n in range(1, 9)]
            inst = S.find(new, "instances")
            inst[1:] = [["project", S.q(PROJECT), *paths]]
            if r == "J":
                # KiCad 10 keeps one Value per symbol, not per instance, so
                # TC1_K_TYPE..TC8_K_TYPE cannot survive reuse; the channel is
                # in the reference (JTCn) and on the silkscreen (CHn).
                for p in S.find_all(new, "property"):
                    if S.unq(p[1]) == "Value":
                        p[2] = '"K_TYPE"'
        elif new[0] == "label":
            name, crossing = label_text(S.unq(new[1]), 1)
            new[1] = S.q(name)
            if crossing:
                shape = next(s for _, p, s in PINS if p == name)
                new[0] = "hierarchical_label"
                new.insert(2, ["shape", shape])
        body.append(new)
    lib = ["lib_symbols"] + [s for s in S.find(tree, "lib_symbols")[1:]
                             if S.unq(s[1]) in libs]
    head = [["version", S.find(tree, "version")[1]], ["generator", '"eeschema"'],
            ["generator_version", '"10.0"'], ["uuid", S.q(uid("file", CHANNEL_FILE))],
            ["paper", '"A4"'], lib]
    return ["kicad_sch", *head, *body, ["embedded_fonts", "no"]]


def sheet_block(name, file, pins, x, y, w, page, root_uuid):
    """Sheet `name` at (x, y) with its pins down the left edge, each wired to
    a root label that carries the net's old name. pins: (net, pin, shape)."""
    h = (len(pins) + 1) * 2.54
    sid = uid("sheet", name)
    font = ["effects", ["font", ["size", "1.27", "1.27"]]]
    blk = ["sheet", ["at", str(x), str(y)], ["size", str(w), f"{h:.2f}"],
           ["fields_autoplaced"], ["stroke", ["width", "0.1524"], ["type", "solid"]],
           ["fill", ["color", "0", "0", "0", "0.0"]], ["uuid", S.q(sid)],
           ["property", '"Sheetname"', S.q(name), ["at", str(x), f"{y - 0.635:.3f}", "0"],
            font + [["justify", "left", "bottom"]]],
           ["property", '"Sheetfile"', S.q(file), ["at", str(x), f"{y + h + 0.635:.3f}", "0"],
            font + [["justify", "left", "top"]]]]
    extra = []
    for i, (net, pin, shape) in enumerate(pins):
        py = round(y + (i + 1) * 2.54, 2)
        blk.append(["pin", S.q(pin), shape, ["at", str(x), str(py), "180"],
                    ["uuid", S.q(uid("pin", name, pin))], font + [["justify", "left"]]])
        lx = round(x - 7.62, 2)
        extra.append(["wire", ["pts", ["xy", str(lx), str(py)], ["xy", str(x), str(py)]],
                      ["stroke", ["width", "0"], ["type", "default"]],
                      ["uuid", S.q(uid("wire", name, pin))]])
        extra.append(["label", S.q(net), ["at", str(lx), str(py), "180"],
                      font + [["justify", "right", "bottom"]],
                      ["uuid", S.q(uid("label", name, pin))]])
    blk.append(["instances", ["project", S.q(PROJECT),
                              ["path", S.q(f"/{root_uuid}"), ["page", S.q(str(page))]]]])
    return [blk] + extra


# A4 root: the four functional sheets on the right, the eight channels in two
# columns on the left. Label text runs left of each block, so the columns are
# spaced for the longest net name (RUN_PERMIT_SENSE, about 18 mm).
CHANNEL_AT = [(38.1 + 60.96 * (k // 4), 25.4 + 25.4 * (k % 4)) for k in range(8)]
FUNCTION_AT = {"ISOLATION": (165.1, 25.4), "RELAY_RS485": (165.1, 106.68),
               "MCU": (233.68, 25.4), "POWER": (233.68, 88.9)}


def main():
    flat, netfile, out = sys.argv[1:4]
    tree = S.parse(open(flat, encoding="utf-8").read())
    root_uuid = S.unq(S.find(tree, "uuid")[1])
    role = roles(netfile)
    chan, root_items, syms = split_channels(tree, role)
    verify_identical(chan, role, syms)
    print("channels 2-8: every symbol placed as in channel 1, same item counts")
    child = channel_sheet(tree, chan, role, root_uuid)
    gone = {id(i) for n in chan for i in chan[n]}
    movable = ("symbol", "wire", "label", "no_connect")
    kept = [x for x in tree if not (isinstance(x, list) and id(x) in gone)]
    items = [x for x in kept if isinstance(x, list) and x[0] in movable]
    channel_nets = {net.format(n=n) for net, _, _ in PINS for n in range(1, 9)}
    head = [["version", S.find(tree, "version")[1]], ["generator", '"eeschema"'],
            ["generator_version", '"10.0"']]
    sheets = funcsheets.split(items, rootlayout.assign(items, ref_of, points), root_uuid,
                              channel_nets, S.find(tree, "lib_symbols"), head, uid,
                              ref_of, points, shifted)
    root = [x for x in kept if not (isinstance(x, list) and x[0] in movable)]
    S.find(root, "paper")[1] = '"A4"'
    lib = S.find(root, "lib_symbols")
    del lib[1:]
    blocks, page = [], 2
    for name, file, _, crossing in sheets:
        x, y = FUNCTION_AT[name]
        blocks += sheet_block(name, file, [(n, n, "passive") for n in crossing],
                              x, y, 30.48, page, root_uuid)
        page += 1
    for n in range(1, 9):
        x, y = CHANNEL_AT[n - 1]
        blocks += sheet_block(f"TC{n}", CHANNEL_FILE,
                              [(net.format(n=n), pin, shape) for net, pin, shape in PINS],
                              x, y, 25.4, page, root_uuid)
        page += 1
    i = next(k for k, x in enumerate(root) if isinstance(x, list) and x[0] == "sheet_instances")
    root[i:i] = blocks
    os.makedirs(out, exist_ok=True)
    files = [(f"{PROJECT}.kicad_sch", root), (CHANNEL_FILE, child)]
    files += [(file, t) for _, file, t, _ in sheets]
    for name, t in files:
        with open(os.path.join(out, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(S.dump(t) + "\n")
    for name, file, t, crossing in sheets:
        print(f"  {file}: {sum(1 for x in t if x[0] == 'symbol')} symbols, "
              f"{len(crossing)} sheet pins")
    print(f"wrote {out}: channel sheet {sum(1 for x in child if x[0] == 'symbol')} symbols x 8")


if __name__ == "__main__":
    main()
