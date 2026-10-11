"""V_BIAS guard pours over the input networks (I-105, `0032` rev 3 H1).

Each channel's clamp node (TCn_PC/NC, after 2.2 k) and ADC node (TCn_PA/NA, after
1 k) sit at about V_MID. With the GND_ISO pour around them, surface leakage from a
~1.6 V difference flows through 3.2 k into the reading (~10 Mohm gives ~4 degC).
Surrounded by V_BIAS copper instead, the same leakage sees ~0 V. One pour per bank on
F.Cu (B.Cu left bare there), over the courtyards of the 2.2 k, BAV199, 1 k, 10 n and 1 n parts, at a
higher priority than the island pour, which is cut out there; In1 stays the solid
GND_ISO plane. Idempotent:
zones named VBIAS_GUARD_* are replaced. Run with KiCad's python.
"""
import os

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.environ.get("THERMO24_BOARD", os.path.join(os.path.dirname(HERE), "thermo24.kicad_pcb"))
T, mm = pcbnew.ToMM, pcbnew.FromMM
MARGIN = 0.6


def bank_box(b, bk):
    xs, ys = [], []
    for k in range(1, 9):
        base = 100 * bk + 10 * k
        refs = [f"R{base + i}" for i in (1, 2, 3, 4)] + [f"D{base + 1}", f"D{base + 2}"] + \
               [f"C{base + i}" for i in (1, 2, 3)]
        for r in refs:
            c = b.FindFootprintByReference(r).GetCourtyard(pcbnew.F_CrtYd).BBox()
            xs += [T(c.GetLeft()), T(c.GetRight())]
            ys += [T(c.GetTop()), T(c.GetBottom())]
    return min(xs) - MARGIN, min(ys) - MARGIN, max(xs) + MARGIN, max(ys) + MARGIN


def cut_island(islands, lname, x1, y1, x2, y2):
    """The island pour must not refill where an unconnected V_BIAS island is dropped:
    cut the strip out of its outline (no-op when already cut)."""
    isl = islands[f"ISLAND_{lname}.Cu"]
    cut = pcbnew.SHAPE_POLY_SET()
    cut.NewOutline()
    for x, y in ((x1, y1), (x2, y1), (x2, y2), (x1, y2)):
        cut.Append(mm(x), mm(y))
    isl.Outline().BooleanSubtract(cut)


def main():
    b = pcbnew.LoadBoard(BOARD)
    zones = list(b.Zones())            # read everything first: after a Remove the zone list is stale
    island = next(z for z in zones if z.GetZoneName() == "ISLAND_F.Cu")
    islands = {z.GetZoneName(): z for z in zones if z.GetZoneName().startswith("ISLAND_")}
    old = [z for z in zones if z.GetZoneName().startswith("VBIAS_GUARD")]
    prio = max([z.GetAssignedPriority() for z in zones if z not in old] + [0]) + 1
    for z in old:
        b.Remove(z)
    net = b.FindNet("V_BIAS")
    for bk in (1, 2, 3):
        x1, y1, x2, y2 = bank_box(b, bk)
        for layer, lname in ((pcbnew.F_Cu, "F"), (pcbnew.B_Cu, "B")):
            if lname == "B":              # parts are on F.Cu; B.Cu stays bare there (a B pour left
                cut_island(islands, lname, x1, y1, x2, y2)      # one-item islands: isolated copper)
                continue
            z = pcbnew.ZONE(b)
            z.SetLayer(layer)
            z.SetNet(net)
            z.SetZoneName(f"VBIAS_GUARD_{'ABC'[bk - 1]}_{lname}")
            z.SetAssignedPriority(prio)
            z.SetLocalClearance(island.GetLocalClearance())
            z.SetMinThickness(island.GetMinThickness())
            z.SetPadConnection(island.GetPadConnection())
            z.SetThermalReliefGap(island.GetThermalReliefGap())
            z.SetThermalReliefSpokeWidth(island.GetThermalReliefSpokeWidth())
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
            o = z.Outline()
            o.NewOutline()
            for x, y in ((x1, y1), (x2, y1), (x2, y2), (x1, y2)):
                o.Append(mm(x), mm(y))
            b.Add(z)
            cut_island(islands, lname, x1, y1, x2, y2)
        print(f"vbias_pour: bank {'ABC'[bk - 1]} x {x1:.1f}-{x2:.1f} y {y1:.1f}-{y2:.1f}, priority {prio}")
    pcbnew.SaveBoard(BOARD, b)


if __name__ == "__main__":
    import guard      # I-115: refuse while KiCad or another tool holds the board
    with guard.claim(BOARD, "vbias_pour.py"):
        main()
