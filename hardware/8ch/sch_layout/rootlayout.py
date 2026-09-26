"""Which functional block each root item belongs to (I-062, 0021).

Once the channels have left the root, every remaining symbol belongs to one
block of extra.py by reference, and every wire, label and no-connect to the
nearest block within REACH. funcsheets.py then moves each block, as one piece,
onto its A4 sheet. The block extents were measured 2026-09-26 on the flat
sheet; the groups are the ones extra.py lays out.
"""
import sexpr as S

GROUPS = {
    "ISO": "U10 U11 C41 C42 C43 C44 R25 R26 R36 R37 R38 R39 TP5 R40 R41 R42 R43 R27 TP6",
    "ISOPWR": "U12 C45 C46 C47 U13 C48 TP4 TP3",
    "MCU": "U1 R28 C52 Y1 C60 C61 C51 C49 C50 J2 RV1 R29 SW1 SW2 SW3 SW4 SW5 J5 J6 TP7",
    "PWR": "J1 #FLG1 #FLG2 F1 D1 #FLG3 D2 C53 C54 C63 R59 R60 U14 R55 C62 R58 C67 L1 "
           "C68 R57 R56 #FLG5 C55 C64 C65 TP2 TP1",
    "RS485": "U15 R33 C56 C57 C58 C59 #FLG4 JP1 R34 JP2 R35 JP3 R44 D5 D6 J4 TP8 TP9",
    "RELAY": "K1 D3 R53 R54 Q1 R30 R31 D4 R32 J3",
}
REACH = 25.0   # an item belongs to the nearest block within this many mm


def assign(items, ref_of, points):
    """The block name of every item, in order."""
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
            out.append(owner[ref_of(it)])
            continue
        pts = points(it)
        g = min(box, key=lambda k: distance(k, pts))
        if distance(g, pts) > REACH:
            raise SystemExit(f"{it[0]} at {pts} belongs to no block")
        out.append(g)
    return out
