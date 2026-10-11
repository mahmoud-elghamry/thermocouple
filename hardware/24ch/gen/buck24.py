"""I-111 repair of the LM5164 stage (U601) on the routed board - local, `0034` D3.

TI LM5164 section 7.4 (as on the 8-ch board, `0026`, hardware/8ch/board/powerstage.py):
input ceramics C602/C603 beside VIN/GND, bootstrap C604 at BST/SW, a short wide SW
node in line with L601, the FB divider at FB. U601 itself does not move.

    VIN   C602.1 - C603.1 - U601.2          one straight 0.8 mm row (y of pin 2)
    GND   C602.2 - C603.2 - U601.1          0.8 mm row, vias between the pads
    SW    U601.8 - C604.2 - L601.1          straight 1.0 mm at pin 8's level
    BST   U601.7 - C604.1                   0.4 mm
    +5V   L601.2 - C605/C606/C607           0.8 mm, vias to the In2 plane
    FB    U601.5 - R602/R603/C609           one column under pin 5
    +24V  D601 - D602 - C601 (row), TP603 (THT) - B.Cu - via near D601

Steps: strips the stage's own nets, lifts three relay-signal segments and the CHASSIS
dog-leg that crossed the area (maze.py re-routes them), moves the parts (`move.py`
logic), draws the copper above. Then: finish.py dangling, maze.py, pincaps.py, DRC.
Run once, on the routed board, with KiCad's python:  python buck24.py
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
BOARD = os.environ.get("THERMO24_BOARD", os.path.join(HW, "thermo24.kicad_pcb"))
mm, T = pcbnew.FromMM, pcbnew.ToMM

STAGE_NETS = {"+24V_PROT", "BST_5V", "SW_5V", "FB_5V", "RIPPLE_INJ", "RON_SET", "VIN_UVLO"}
# (net, x1, y1, x2, y2) of segments lifted because the new placement sits on them
LIFT = [("TRIP_LOW", 119.31, 29.07, 141.82, 29.07), ("TRIP_LOW", 158.81, 46.05, 141.82, 29.07),
        ("ALM_LOW", 163.74, 46.44, 148.0, 30.7), ("ALM_LOW", 148.0, 30.7, 112.76, 30.7),
        ("TRIP_LED_A", 147.91, 32.37, 97.36, 32.37), ("TRIP_LED_A", 162.54, 47.0, 147.91, 32.37),
        ("CHASSIS", 168.49, 33.28, 162.71, 27.49), ("CHASSIS", 162.71, 27.49, 162.71, 7.29)]
LIFT_VIAS = [("TRIP_LOW", 141.82, 29.07)]
PLACE = {   # ref: (x, y, rot)
    "C602": (141.0, 23.39, 90), "C603": (144.5, 23.39, 90), "TP603": (137.7, 24.86, 0),
    "R605": (142.0, 27.3, 0), "R606": (142.0, 29.5, 180), "R601": (145.6, 29.5, 0),
    "C604": (155.0, 24.2, 90), "L601": (162.6, 25.0, 0),
    "R602": (153.57, 29.6, 180), "R603": (153.57, 31.8, 0), "C609": (151.73, 34.0, 0),
    "C608": (151.73, 36.2, 0), "R604": (157.5, 32.5, 270),
    "C605": (166.6, 33.2, 270), "C606": (163.0, 33.2, 270), "C607": (160.2, 33.0, 270),
}


def near(a, b, tol=0.02):
    return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol


def main():
    b = pcbnew.LoadBoard(BOARD)
    nets = {str(k).rsplit("/", 1)[-1]: v for k, v in b.GetNetsByName().items()}
    gone = []
    for t in b.GetTracks():
        n = t.GetNetname().rsplit("/", 1)[-1]
        if n in STAGE_NETS:
            gone.append(t)
        elif t.Type() == pcbnew.PCB_VIA_T:
            p = (T(t.GetPosition().x), T(t.GetPosition().y))
            if any(n == ln and near(p, (x, y)) for ln, x, y in LIFT_VIAS):
                gone.append(t)
        else:
            s, e = (T(t.GetStart().x), T(t.GetStart().y)), (T(t.GetEnd().x), T(t.GetEnd().y))
            for ln, x1, y1, x2, y2 in LIFT:
                if n == ln and {s, e} and ((near(s, (x1, y1)) and near(e, (x2, y2)))
                                           or (near(s, (x2, y2)) and near(e, (x1, y1)))):
                    gone.append(t)
    lifted = sum(1 for t in gone if t.GetNetname().rsplit("/", 1)[-1] not in STAGE_NETS)
    if lifted != len(LIFT) + len(LIFT_VIAS):
        raise SystemExit(f"buck24: found {lifted} of {len(LIFT) + len(LIFT_VIAS)} lifted items - board changed?")
    for ref, (x, y, rot) in PLACE.items():
        fp = b.FindFootprintByReference(ref)
        for t in b.GetTracks():
            pts = [t.GetPosition()] if t.Type() == pcbnew.PCB_VIA_T else [t.GetStart(), t.GetEnd()]
            if t not in gone and any(p.HitTest(q, 0) for p in fp.Pads()
                                     if p.GetNetCode() == t.GetNetCode() for q in pts):
                gone.append(t)
        fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        fp.SetOrientationDegrees(rot)
    for t in gone:
        b.Remove(t)

    def pad(ref, num):
        p = next(p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num).GetPosition()
        return (round(T(p.x), 3), round(T(p.y), 3))

    def track(net, pts, w, layer=pcbnew.F_Cu):
        for a, z in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
            t.SetEnd(pcbnew.VECTOR2I(mm(z[0]), mm(z[1])))
            t.SetWidth(mm(w))
            t.SetLayer(layer)
            t.SetNet(nets[net])
            b.Add(t)

    def via(net, x, y):
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        v.SetWidth(mm(0.6))
        v.SetDrill(mm(0.3))
        v.SetNet(nets[net])
        b.Add(v)

    u = {n: pad("U601", n) for n in "12345678"}
    vin, gnd = (pad("C602", "1"), pad("C603", "1")), (pad("C602", "2"), pad("C603", "2"))
    # placement check: the rows must be level with the pins they serve
    assert all(abs(p[1] - u["2"][1]) < 0.05 for p in vin), ("VIN pads not level with U601.2", vin, u["2"])
    assert gnd[0][1] < u["1"][1] and abs(gnd[0][1] - gnd[1][1]) < 0.05, ("GND pads", gnd)
    sw_c, bst_c = pad("C604", "2"), pad("C604", "1")
    assert abs(sw_c[1] - u["8"][1]) < 0.6 and bst_c[1] > sw_c[1], ("C604 orientation", sw_c, bst_c)
    l1, l2 = pad("L601", "1"), pad("L601", "2")
    r604_sw, r604_rip = pad("R604", "1"), pad("R604", "2")
    assert r604_sw[1] < r604_rip[1], ("R604 orientation", r604_sw, r604_rip)
    c5 = {r: (pad(r, "1"), pad(r, "2")) for r in ("C605", "C606", "C607")}
    assert all(a[1] < z[1] for a, z in c5.values()), ("output caps: +5V pad must be on top", c5)

    tp = pad("TP603", "1")
    track("+24V_PROT", [tp, vin[0], vin[1], u["2"]], 0.8)                       # VIN row
    track("+24V_PROT", [(pad("R605", "1")[0], vin[0][1]), pad("R605", "1")], 0.3)
    d601, d602, c601 = pad("D601", "1"), pad("D602", "1"), pad("C601", "1")
    track("+24V_PROT", [d601, (d602[0] - 2.0, d601[1]), d602, (c601[0] - 2.2, d602[1]), c601], 0.8)
    v2 = (142.9, 18.6)
    track("+24V_PROT", [d601, v2], 0.6)
    via("+24V_PROT", *v2)
    track("+24V_PROT", [tp, (tp[0], 20.9), v2], 0.6, pcbnew.B_Cu)
    corner = (u["1"][0] - 1.5, gnd[1][1])
    track("GND", [gnd[0], gnd[1], corner, u["1"]], 0.8)                          # input GND row
    via("GND", (gnd[0][0] + gnd[1][0]) / 2, gnd[0][1] - 1.6)
    via("GND", corner[0], corner[1] - 1.3)
    track("GND", [corner, (corner[0], corner[1] - 1.3)], 0.6)
    track("SW_5V", [u["8"], (l1[0], u["8"][1])], 1.0)                             # SW, through C604.2
    track("SW_5V", [sw_c, (sw_c[0], u["8"][1])], 0.6)
    track("BST_5V", [u["7"], (bst_c[0] - 0.6, u["7"][1]), bst_c], 0.4)
    track("SW_5V", [(l1[0], l1[1] + 1.5), (r604_sw[0], l1[1] + 2.45), r604_sw], 0.25)
    r605u, r606u = pad("R605", "2"), pad("R606", "1")
    track("VIN_UVLO", [u["3"], (r605u[0] + 1.2, u["3"][1]), r605u, r606u], 0.25)
    r601 = pad("R601", "1")
    track("RON_SET", [u["4"], (r601[0] + 1.3, u["4"][1]), (r601[0], u["4"][1] + 1.3), r601], 0.25)
    fb = [u["5"], pad("R602", "2"), pad("R603", "1"), pad("C609", "2")]
    assert all(abs(p[0] - u["5"][0]) < 0.05 for p in fb), ("FB column", fb)
    track("FB_5V", [u["5"], fb[-1]], 0.25)
    rip_a, rip_b = pad("C609", "1"), pad("C608", "1")
    mid = (rip_a[0], (rip_a[1] + rip_b[1]) / 2)
    track("RIPPLE_INJ", [rip_a, rip_b], 0.25)
    track("RIPPLE_INJ", [r604_rip, (r604_rip[0], mid[1]), mid], 0.25)
    out = [c5["C605"][0], c5["C606"][0], c5["C607"][0]]
    track("+5V", [l2, (l2[0], out[0][1]), out[0], out[1], (out[2][0], out[1][1]), out[2]], 0.8)
    via("+5V", (out[0][0] + out[1][0]) / 2, out[0][1])
    g = [c5["C605"][1], c5["C606"][1], c5["C607"][1]]
    track("GND", [g[0], g[1], (g[2][0], g[1][1]), g[2]], 0.8)
    via("GND", (g[0][0] + g[1][0]) / 2, g[0][1])
    via("GND", (g[1][0] + g[2][0]) / 2 - 0.3, g[1][1])
    # small-part plane connections
    for ref, num, net, dx in (("R602", "1", "+5V", 1.1), ("R603", "2", "GND", 1.1), ("C608", "2", "+5V", 1.2),
                              ("R606", "2", "GND", -1.1), ("R601", "2", "GND", 1.1)):
        p = pad(ref, num)
        track(net, [p, (p[0] + dx, p[1])], 0.3)
        via(net, p[0] + dx, p[1])
    track("CHASSIS", [(168.49, 33.28), (168.49, 7.49), pad("H5", "1")], 0.8, pcbnew.B_Cu)
    pcbnew.SaveBoard(BOARD, b)
    print(f"buck24: removed {len(gone)} tracks/vias ({lifted} lifted), moved {len(PLACE)} parts, copper drawn")


if __name__ == "__main__":
    import guard      # I-115: refuse while KiCad or another tool holds the board
    with guard.claim(str(BOARD), "buck24.py"):
        main()
