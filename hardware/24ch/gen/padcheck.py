"""List pad pairs closer than their net classes' clearance (what Freerouting calls violations)."""
import json
import os
from collections import Counter

import pcbnew

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
b = pcbnew.LoadBoard(os.path.join(HW, "thermo24.kicad_pcb"))
pro = json.load(open(os.path.join(HW, "thermo24.kicad_pro"), encoding="utf-8"))
clr = {c["name"]: c["clearance"] for c in pro["net_settings"]["classes"]}
pat = {p["pattern"]: p["netclass"] for p in pro["net_settings"]["netclass_patterns"]}
pads = []
for fp in b.GetFootprints():
    for p in fp.Pads():
        bb = p.GetBoundingBox()
        pads.append((fp.GetReference(), p.GetNumber(), p.GetNetname(),
                     pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()),
                     pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom()), p.IsOnLayer(pcbnew.F_Cu)))
bad = Counter()
ex = []
for i, a in enumerate(pads):
    for c in pads[i + 1:]:
        if a[2] == c[2] or not a[2] or not c[2]:
            continue
        dx = max(c[3] - a[5], a[3] - c[5], 0)
        dy = max(c[4] - a[6], a[4] - c[6], 0)
        if dx > 3 or dy > 3:
            continue
        need = max(clr.get(pat.get(a[2], "Default"), 0.2), clr.get(pat.get(c[2], "Default"), 0.2))
        gap = (dx * dx + dy * dy) ** 0.5
        if gap < need - 0.01:
            key = f"{a[0]}~{c[0]}" if a[0] == c[0] else f"{a[0]}/{c[0]}"
            bad[(a[0] if a[0] == c[0] else "cross", pat.get(a[2], "Default"), pat.get(c[2], "Default"))] += 1
            if len(ex) < 15:
                ex.append((key, a[1], c[1], round(gap, 2), need))
for k, v in bad.most_common(30):
    print(v, k)
print(ex)
