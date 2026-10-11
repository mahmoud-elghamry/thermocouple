"""Three fiducials (I-112, `0034` D3): 1 mm copper dot, 2 mm mask opening, in three corners.

Board-only footprints (no schematic symbol, out of BOM and placement files). Each goes to
the free spot nearest its corner target: no copper of any net within 1.6 mm on F.Cu, no
courtyard overlap, >= 3.5 mm from the edge. The pad's local clearance keeps the pours
out of the mask opening. Idempotent: existing FID* are replaced. Run with KiCad's python.
"""
import math
import os

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.environ.get("THERMO24_BOARD", os.path.join(os.path.dirname(HERE), "thermo24.kicad_pcb"))
LIB = r"C:\Program Files\KiCad\10.0\share\kicad\footprints\Fiducial.pretty"
TARGETS = {"FID1": (10.0, 10.0), "FID2": (160.0, 12.0), "FID3": (10.0, 135.0)}   # three corners, not symmetric
T, mm = pcbnew.ToMM, pcbnew.FromMM
FREE = 1.6


def main():
    b = pcbnew.LoadBoard(BOARD)
    for f in [f for f in b.GetFootprints() if f.GetReference().startswith("FID")]:
        b.Remove(f)
    pts = []
    for f in b.GetFootprints():
        for p in f.Pads():
            bb = p.GetBoundingBox()
            pts.append((T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())))
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T or t.GetLayer() == pcbnew.F_Cu:
            bb = t.GetBoundingBox()
            pts.append((T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())))
    crts = [f.GetCourtyard(pcbnew.F_CrtYd).BBox() for f in b.GetFootprints()
            if f.GetCourtyard(pcbnew.F_CrtYd).OutlineCount()]
    crts = [(T(c.GetLeft()), T(c.GetTop()), T(c.GetRight()), T(c.GetBottom())) for c in crts]

    def free(x, y):
        if not (3.5 <= x <= 166.5 and 3.5 <= y <= 141.5):
            return False
        for r in pts:
            if math.hypot(max(r[0] - x, 0, x - r[2]), max(r[1] - y, 0, y - r[3])) < FREE:
                return False
        return not any(r[0] - 1.2 < x < r[2] + 1.2 and r[1] - 1.2 < y < r[3] + 1.2 for r in crts)

    for ref, (tx, ty) in TARGETS.items():
        spot = None
        for k in range(0, 400):
            ring = [(tx + dx * 0.25, ty + dy * 0.25) for dx in range(-k, k + 1) for dy in range(-k, k + 1)
                    if max(abs(dx), abs(dy)) == k]
            ok = [p for p in ring if free(*p)]
            if ok:
                spot = min(ok, key=lambda p: math.hypot(p[0] - tx, p[1] - ty))
                break
        if spot is None:
            raise SystemExit(f"fiducials: no free spot for {ref}")
        fp = pcbnew.FootprintLoad(LIB, "Fiducial_1mm_Mask2mm")
        fp.SetReference(ref)
        fp.SetPosition(pcbnew.VECTOR2I(mm(spot[0]), mm(spot[1])))
        fp.SetBoardOnly(True)
        fp.SetExcludedFromBOM(True)
        fp.SetExcludedFromPosFiles(True)
        fp.Reference().SetVisible(False)
        for p in fp.Pads():
            p.SetLocalClearance(mm(0.5))      # pour stays outside the 2 mm mask opening
        b.Add(fp)
        pts.append((spot[0] - 1, spot[1] - 1, spot[0] + 1, spot[1] + 1))
        print(f"fiducials: {ref} at ({spot[0]:.2f}, {spot[1]:.2f})")
    pcbnew.SaveBoard(BOARD, b)


if __name__ == "__main__":
    import guard      # I-115: refuse while KiCad or another tool holds the board
    with guard.claim(str(BOARD), "fiducials.py"):
        main()
