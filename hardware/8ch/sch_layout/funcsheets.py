"""Move the root's functional blocks onto their own A4 sheets (0021).

After hier.py has taken the channels out, the root still holds the power
input, the MCU, the isolators and the relay + RS-485 blocks. Each goes to one
A4 sheet used once. A net that one sheet shares with another sheet, or with
the channel sheets, becomes a hierarchical label and a sheet pin wired to a
root label carrying its old name, so it keeps that name. A net inside one
sheet gets the sheet path: /RELAY_RS485/RELAY_COM. apply_rules.py patterns
and board/units.bare() carry those paths; see decisions/0021.

Each block (rootlayout.GROUPS) moves as one piece by whole 1.27 mm grid steps,
so no pin leaves the grid and no connection changes. build.py's netlist gate
proves that.
"""
import re
import sexpr as S

G = 1.27
# sheet name -> (file, blocks, page); the channel sheets follow these pages
SHEETS = [
    ("POWER", "power.kicad_sch", ["PWR"]),
    ("MCU", "mcu.kicad_sch", ["MCU"]),
    ("ISOLATION", "isolation.kicad_sch", ["ISO", "ISOPWR"]),
    ("RELAY_RS485", "relay_rs485.kicad_sch", ["RELAY", "RS485"]),
]
NAMES = tuple(name for name, _, _ in SHEETS)
# A4 drawing area inside the frame, and the title block in its corner
X0, Y0, X1, Y1 = 17.78, 22.86, 284.0, 196.0
TITLE = (177.0, 166.0)
MARGIN = 5.0      # symbol bodies reach past the pins their wires end on
GAP = 10.16


def natural(name):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", name)]


def pin_order(name):
    """Supplies first, then the signals in natural order."""
    return (0 if name.startswith(("+", "GND")) else 1, natural(name))


def extent(items, points):
    pts = [p for it in items for p in points(it)]
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    return min(xs) - MARGIN, min(ys) - MARGIN, max(xs) + MARGIN, max(ys) + MARGIN


def split(items, groups, root_uuid, channel_nets, lib_symbols, head, uid,
          ref_of, points, shifted):
    """items/groups: the root's movable items and the block each belongs to.

    Returns [(name, file, tree, crossing nets in pin order)] in page order.
    """
    by_sheet = {name: [it for it, g in zip(items, groups) if g in blocks]
                for name, _, blocks in SHEETS}
    placed = [it for its in by_sheet.values() for it in its]
    if len(placed) != len(items):
        raise SystemExit("an item on the root belongs to no functional sheet")
    names = {s: {S.unq(it[1]) for it in its if it[0] == "label"}
             for s, its in by_sheet.items()}
    out = []
    for name, file, blocks in SHEETS:
        others = set(channel_nets).union(*(names[t] for t in names if t != name))
        crossing = sorted(names[name] & others, key=pin_order)
        sid = uid("sheet", name)
        # stack the blocks left-aligned, then centre the stack on the page
        # above the title block, in whole grid steps
        stack, y = [], 0.0
        for block in blocks:
            its = [it for it, g in zip(items, groups) if g == block]
            x0, y0, x1, y1 = extent(its, points)
            stack.append((its, -x0, y - y0, x1 - x0))
            y += y1 - y0 + GAP
        w, h = max(s[3] for s in stack), y - GAP
        cx = X0 + max(0.0, (X1 - X0 - w) / 2)
        cy = Y0 + max(0.0, (TITLE[1] - Y0 - h) / 2)
        if cx + w > X1 or cy + h > Y1 or (cx + w > TITLE[0] and cy + h > TITLE[1]):
            raise SystemExit(f"{name}: {w:.0f} x {h:.0f} mm does not fit A4")
        body, libs = [], set()
        for its, ox, oy, _ in stack:
            dx = round((cx + ox) / G) * G
            dy = round((cy + oy) / G) * G
            for it in its:
                new = shifted(it, dx, dy)
                if new[0] == "symbol":
                    libs.add(S.unq(S.find(new, "lib_id")[1]))
                    path = S.find(S.find(S.find(new, "instances"), "project"), "path")
                    path[1] = S.q(f"/{root_uuid}/{sid}")
                elif new[0] == "label" and S.unq(new[1]) in crossing:
                    new[0] = "hierarchical_label"
                    new.insert(2, ["shape", "passive"])
                body.append(new)
        lib = ["lib_symbols"] + [s for s in lib_symbols[1:] if S.unq(s[1]) in libs]
        tree = ["kicad_sch", *head, ["uuid", S.q(uid("file", file))], ["paper", '"A4"'],
                lib, *body, ["embedded_fonts", "no"]]
        out.append((name, file, tree, crossing))
    return out

