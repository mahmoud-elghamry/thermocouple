"""Create an empty 2-layer 150 x 154 mm board for the 8-channel unit REV B0-2L (local 2-layer fab).

Run with KiCad's python:  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" pcb_new.py
Refuses to overwrite an existing board unless --force is given.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(os.path.dirname(HERE), "thermo8.kicad_pcb")
W, H = 150.0, 154.0    # the 4-layer floor plan spread 1.154 x 1.124; keep equal to gen/place.py
mm = pcbnew.FromMM


def main():
    if os.path.exists(BOARD) and "--force" not in sys.argv:
        raise SystemExit(f"{BOARD} exists; use --force to recreate it")
    b = pcbnew.BOARD()
    b.SetCopperLayerCount(2)
    ds = b.GetDesignSettings()
    ds.m_TrackMinWidth = mm(0.2)
    ds.m_ViasMinSize = mm(0.6)
    ds.m_MinThroughDrill = mm(0.3)
    ds.m_MinClearance = mm(0.2)
    ds.m_CopperEdgeClearance = mm(0.5)
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetClearance(mm(0.2))
    nc.SetTrackWidth(mm(0.25))
    nc.SetViaDiameter(mm(0.6))
    nc.SetViaDrill(mm(0.3))
    pts = [(0, 0), (W, 0), (W, H), (0, H)]
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        seg = pcbnew.PCB_SHAPE(b)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(mm(0.1))
        # board y grows downward; the floor plan's y grows upward
        seg.SetStart(pcbnew.VECTOR2I(mm(x1), mm(H - y1)))
        seg.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(H - y2)))
        b.Add(seg)
    b.SaveAs(BOARD) if hasattr(b, "SaveAs") else pcbnew.SaveBoard(BOARD, b)
    print("created", BOARD)


if __name__ == "__main__":
    main()
