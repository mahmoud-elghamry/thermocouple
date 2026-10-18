"""Gate for I-111: every IC supply/critical pin has its capacitor beside it.

ERC/DRC cannot see a decoupling cap 20 mm from its pin; this measures it.
For each (ref, pin, limit_mm) below: the nearest capacitor pad on the same net,
centre to centre. Prints a table and exits non-zero if any pin is over its limit.
Run with KiCad's python:  python pincaps.py [board]
"""

from profiles import ACTIVE as P, ROOT
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = sys.argv[1] if len(sys.argv) > 1 else str(P["pcb"])
T = pcbnew.ToMM

VIA_MM, PLANE_REACH = 1.5, 12.0     # "plane" check: own via beside pin and cap; cap no farther than this
CHECK = P.require("pin_checks")


def main():
    b = pcbnew.LoadBoard(BOARD)
    caps = [(fp.GetReference(), p) for fp in b.GetFootprints() if fp.GetReference().startswith("C")
            for p in fp.Pads()]
    parts = caps + [(fp.GetReference(), p) for fp in b.GetFootprints() if fp.GetReference().startswith("R")
                    for p in fp.Pads()]
    vias = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
    bad = 0
    for ref, pin, lim, what in CHECK:
        fp = b.FindFootprintByReference(ref)
        p = [q for q in fp.Pads() if q.GetNumber() == pin]
        if not p:
            print(f"{ref}.{pin}: no such pad"); bad += 1
            continue
        p = p[0]
        net = p.GetNetname()
        if ref == P.require("buck_ref") and pin in ("7", "8"):
            net_ok = P.require("bootstrap_nets")
            same = [(r, q) for r, q in caps if q.GetNetname().rsplit("/", 1)[-1] in net_ok]
        elif ref == P.require("buck_ref") and pin == "5":     # the FB network is the divider, not only a capacitor
            same = [(r, q) for r, q in parts if q.GetNetname() == net]
        else:
            same = [(r, q) for r, q in caps if q.GetNetname() == net]
        x, y = T(p.GetPosition().x), T(p.GetPosition().y)
        if lim == "plane":
            def via_d(q):
                return min((math.hypot(T(v.GetPosition().x - q.GetPosition().x), T(v.GetPosition().y - q.GetPosition().y))
                            for v in vias if v.GetNetCode() == p.GetNetCode()), default=float("inf"))
            pin_v = via_d(p)
            cap_v, r = min(((via_d(q), r) for r, q in same
                            if math.hypot(T(q.GetPosition().x) - x, T(q.GetPosition().y) - y) <= PLANE_REACH),
                           default=(float("inf"), "-"))
            ok = pin_v <= VIA_MM and cap_v <= VIA_MM
            bad += not ok
            print(f"{'ok ' if ok else 'BAD'} {ref}.{pin:3} {net.rsplit('/', 1)[-1]:12} pin via {pin_v:4.1f} mm, "
                  f"{r} via {cap_v:4.1f} mm (limit {VIA_MM}, cap within {PLANE_REACH}) {what}")
            continue
        d, r = min(((math.hypot(T(q.GetPosition().x) - x, T(q.GetPosition().y) - y), r) for r, q in same),
                   default=(float("inf"), "-"))
        ok = d <= lim
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} {ref}.{pin:3} {net.rsplit('/', 1)[-1]:12} nearest {r:6} {d:6.1f} mm "
              f"(limit {lim}) {what}")
    print(f"pincaps: {bad} over the limit")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
