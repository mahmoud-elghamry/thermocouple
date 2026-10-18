"""Copper of the LM5164 stage (U601) on the 8-ch board, as hardware/24ch/gen/buck24.py draws it (TI LM5164
section 7.4): the parts already sit in the 24-ch arrangement (place.py BUCK_NEAR), so every point here is taken
from a pad. Strips the stage's own nets first (the router and maze.py made them thin and long), draws:

    VIN   TP603 - C602.1 - C603.1 - U601.2   0.8 mm row        GND   C602.2 - C603.2 - U601.1, vias
    SW    U601.8 - C604.2 - L601.1           1.0 mm            BST   U601.7 - C604.1  0.4 mm
    FB    U601.5 - R602 - R603 - C609        one column        +5V   L601.2 - C605/C606/C607, via
The +24V feed from the input protection (D601/D602/C601) to TP603 is left to `--feed` (hand points).
Run with KiCad's python:  python buck8.py
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.environ.get("THERMO8_BOARD", os.path.join(os.path.dirname(HERE), "thermo8.kicad_pcb"))
mm, T = pcbnew.FromMM, pcbnew.ToMM
STAGE_NETS = {"BST_5V", "SW_5V", "FB_5V", "RIPPLE_INJ", "RON_SET", "VIN_UVLO"}
STAGE_REFS = ("U601", "C602", "C603", "TP603", "R605", "R606", "R601", "C604", "L601", "R602", "R603",
              "C609", "C608", "R604", "C605", "C606", "C607")


def main():
    b = pcbnew.LoadBoard(BOARD)
    nets = {str(k).rsplit("/", 1)[-1]: v for k, v in b.GetNetsByName().items()}
    stage_pads = [p for r in STAGE_REFS for p in b.FindFootprintByReference(r).Pads()]
    gone = []
    for t in b.GetTracks():
        n = t.GetNetname().rsplit("/", 1)[-1]
        pts = [t.GetPosition()] if t.Type() == pcbnew.PCB_VIA_T else [t.GetStart(), t.GetEnd()]
        if n in STAGE_NETS or (n in ("+24V_PROT", "GND", "+5V") and any(
                p.GetNetCode() == t.GetNetCode() and p.HitTest(q, 0) for p in stage_pads for q in pts)):
            gone.append(t)
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
    assert all(abs(p[1] - u["2"][1]) < 0.05 for p in vin), ("VIN pads not level with U601.2", vin, u["2"])
    assert gnd[0][1] < u["1"][1] and abs(gnd[0][1] - gnd[1][1]) < 0.05, ("GND pads", gnd)
    sw_c, bst_c = pad("C604", "2"), pad("C604", "1")
    assert abs(sw_c[1] - u["8"][1]) < 0.6 and bst_c[1] > sw_c[1], ("C604 orientation", sw_c, bst_c)
    l1, l2 = pad("L601", "1"), pad("L601", "2")
    r604_sw, r604_rip = pad("R604", "1"), pad("R604", "2")
    c5 = {r: (pad(r, "1"), pad(r, "2")) for r in ("C605", "C606", "C607")}
    tp = pad("TP603", "1")
    track("+24V_PROT", [tp, vin[0], vin[1], u["2"]], 0.8)
    track("+24V_PROT", [(pad("R605", "1")[0], vin[0][1]), pad("R605", "1")], 0.3)
    corner = (u["1"][0] - 1.5, gnd[1][1])
    track("GND", [gnd[0], gnd[1], corner, u["1"]], 0.8)
    via("GND", (gnd[0][0] + gnd[1][0]) / 2, gnd[0][1] - 1.6)
    via("GND", corner[0], corner[1] - 1.3)
    track("GND", [corner, (corner[0], corner[1] - 1.3)], 0.6)
    track("SW_5V", [u["8"], (l1[0], u["8"][1])], 1.0)
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
    for ref, num, net, dx in (("R602", "1", "+5V", 1.1), ("R603", "2", "GND", 1.1), ("C608", "2", "+5V", 1.2),
                              ("R606", "2", "GND", -1.1), ("R601", "2", "GND", 1.1)):
        p = pad(ref, num)
        track(net, [p, (p[0] + dx, p[1])], 0.3)
        via(net, p[0] + dx, p[1])
    pcbnew.SaveBoard(BOARD, b)
    print(f"buck8: removed {len(gone)} tracks/vias, stage copper drawn")


if __name__ == "__main__":
    os.environ.setdefault("THERMO24_WRITER_CLAIM", os.path.join(os.path.dirname(HERE), "output", ".writer.json"))
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "24ch", "gen"))
    import guard      # I-115: refuse while KiCad or another tool holds the board
    with guard.claim(str(BOARD), "buck8.py"):
        main()
