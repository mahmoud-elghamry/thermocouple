"""Pack the root sheet onto A3 once the channels have left it (I-062).

Each block of extra.py moves as one piece - symbols with the wires, labels and
no-connects around them - by a whole number of 1.27 mm grid steps, so no pin
leaves the grid and no connection changes. The netlist gate proves the
latter. Block extents measured 2026-09-26 on the A2 sheet.
"""
import sexpr as S

G = 1.27
GROUPS = {
    "ISO": "U10 U11 C41 C42 C43 C44 R25 R26 R36 R37 R38 R39 TP5 R40 R41 R42 R43 R27 TP6",
    "ISOPWR": "U12 C45 C46 C47 U13 C48 TP4 TP3",
    "MCU": "U1 R28 C52 Y1 C60 C61 C51 C49 C50 J2 RV1 R29 SW1 SW2 SW3 SW4 SW5 J5 J6 TP7",
    "PWR": "J1 #FLG1 #FLG2 F1 D1 #FLG3 D2 C53 C54 C63 R59 R60 U14 R55 C62 R58 C67 L1 "
           "C68 R57 R56 #FLG5 C55 C64 C65 TP2 TP1",
    "RS485": "U15 R33 C56 C57 C58 C59 #FLG4 JP1 R34 JP2 R35 JP3 R44 D5 D6 J4 TP8 TP9",
    "RELAY": "K1 D3 R53 R54 Q1 R30 R31 D4 R32 J3",
}
# grid steps; the channel sheets take the left column (x 12..62)
SHIFT = {
    "ISO": (-205, 0),        # x 335..420 -> 75..160, top row
    "ISOPWR": (-204, 0),     # x 429..521 -> 170..262, top row
    "RS485": (-140, -58),    # -> x 259..396, y 54..108; J4 label clears the frame
    "MCU": (-162, -20),      # -> x 74..208, y 120..250
    "RELAY": (-214, -66),    # -> x 219..294, y 124..156
    "PWR": (-6, -31),        # -> bottom strip y 250..283, clear of the title block
}
REACH = 25.0   # an item belongs to the nearest block within this many mm


def compact(items, ref_of, points, shifted):
    """Return the root items with every block moved by SHIFT."""
    owner = {r: g for g, refs in GROUPS.items() for r in refs.split()}
    box = {}
    for it in items:
        if it[0] == "symbol":
            g = owner.get(ref_of(it))
            if g is None:
                raise SystemExit(f"{ref_of(it)} is in no root block")
            x, y = S.at(it)
            b = box.setdefault(g, [x, y, x, y])
            box[g] = [min(b[0], x), min(b[1], y), max(b[2], x), max(b[3], y)]

    def distance(g, pts):
        b = box[g]
        return max(max(b[0] - x, 0, x - b[2]) + max(b[1] - y, 0, y - b[3]) for x, y in pts)

    out = []
    for it in items:
        if it[0] == "symbol":
            g = owner[ref_of(it)]
        else:
            pts = points(it)
            g = min(box, key=lambda k: distance(k, pts))
            if distance(g, pts) > REACH:
                raise SystemExit(f"{it[0]} at {pts} belongs to no block")
        dx, dy = SHIFT[g]
        out.append(shifted(it, dx * G, dy * G))
    return out
