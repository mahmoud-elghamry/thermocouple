"""Print courtyard boxes (relative to the footprint origin, rotation 0) per footprint name."""
import os
import sys

import pcbnew

BOARD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "thermo24.kicad_pcb")
b = pcbnew.LoadBoard(BOARD)
seen = {}
for fp in b.GetFootprints():
    name = fp.GetFPIDAsString()
    if name in seen:
        continue
    fp.SetOrientationDegrees(0)
    pos = fp.GetPosition()
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    if cy.OutlineCount() == 0:
        cy = fp.GetCourtyard(pcbnew.B_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
    x1 = pcbnew.ToMM(bb.GetX() - pos.x); y1 = pcbnew.ToMM(bb.GetY() - pos.y)
    x2 = x1 + pcbnew.ToMM(bb.GetWidth()); y2 = y1 + pcbnew.ToMM(bb.GetHeight())
    pads = sorted((p.GetNumber(), round(pcbnew.ToMM(p.GetPosition().x - pos.x), 2),
                   round(pcbnew.ToMM(p.GetPosition().y - pos.y), 2)) for p in fp.Pads())
    seen[name] = (fp.GetReference(), round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2), pads)
for name, (ref, x1, y1, x2, y2, pads) in sorted(seen.items()):
    show = pads if "-v" in sys.argv else pads[:3]
    print(f"{name:75s} {ref:6s} x[{x1},{x2}] y[{y1},{y2}] {show}")
