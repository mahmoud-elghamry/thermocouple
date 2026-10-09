"""Silkscreen: readable labels where an installer needs them, nothing elsewhere.

Hides reference text on dense passives (the Fab layer keeps it for assembly),
shrinks the rest, and adds channel numbers, terminal legends, the barrier
outline and the board title. Idempotent: old texts it made are replaced.
Run with KiCad's python.
"""
import os

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(os.path.dirname(HERE), "thermo24.kicad_pcb")
mm = pcbnew.FromMM
KEEP = ("J", "U", "K", "SW", "D7", "TP", "H", "RV", "F", "L", "Y")


def text(b, s, x, y, size=1.0, rot=0, layer=pcbnew.F_SilkS, bold=False):
    t = pcbnew.PCB_TEXT(b)
    t.SetText(s)
    t.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(size * (0.2 if bold else 0.15)))
    t.SetTextAngleDegrees(rot)
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    b.Add(t)
    return t


def line(b, x1, y1, x2, y2, w=0.2):
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetLayer(pcbnew.F_SilkS)
    s.SetWidth(mm(w))
    s.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    s.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
    b.Add(s)


def main():
    import subprocess, sys
    subprocess.run([sys.executable, os.path.abspath(__file__), "--strip"], check=True)
    b = pcbnew.LoadBoard(BOARD)
    for fp in b.GetFootprints():
        ref = fp.Reference()
        keep = fp.GetReference().startswith(KEEP)
        ref.SetVisible(keep)
        ref.SetTextSize(pcbnew.VECTOR2I(mm(0.9), mm(0.9)))
        ref.SetTextThickness(mm(0.14))
        fp.Value().SetVisible(False)
    P = 3.81
    # channel numbers above each TC+/TC- pair (banks A, B on the bottom edge)
    for bank, x1 in ((1, 15.25), (2, 89.25)):
        for h in range(2):
            for i in range(4):
                ch = 8 * (bank - 1) + 4 * h + i + 1
                x = x1 + h * 33.5 + 2 * P * i + P / 2
                text(b, f"{ch}", x, 133.0, 1.0)
    for h in range(2):          # bank C on the left edge
        for i in range(4):
            ch = 17 + 4 * h + i
            y = 22.25 + h * 33.5 + 2 * P * i + P / 2
            text(b, f"{ch}", 12.6, y + 0.4, 1.0, 90)
    text(b, f"TC: + - per channel", 45.0, 131.0, 0.9)
    text(b, f"ENGINE REF  FEED / SENSE", 18.0, 86.0, 0.9)
    text(b, f"TRIP C-NO-NC", 94.5, 13.2, 0.9)
    text(b, f"ALARM C-NO-NC", 111.6, 13.2, 0.9)
    text(b, f"24V  0V  SH", 128.0, 13.2, 0.9)
    text(b, f"RS-485 A B GND", 66.0, 13.0, 0.8)
    text(b, f"CONTACTS: LOW-VOLTAGE SIGNAL LOAD ONLY, 30 VDC / 1 A MAX", 103.0, 41.0, 1.0, bold=True)
    text(b, f"THERMO 24-CH  REV A3", 106.0, 84.0, 1.5, bold=True)
    text(b, f"ISOLATED SENSOR SIDE", 20.0, 120.0 - 15.0, 1.0)
    # barrier outline (functional isolation, not a safety rating)
    for x1, y1, x2, y2 in ((43.5, 12.5, 43.5, 101.5), (43.5, 101.5, 169.5, 101.5),
                           (53.5, 0.5, 53.5, 23.5), (53.5, 23.5, 85.5, 23.5), (85.5, 23.5, 85.5, 0.5)):
        line(b, x1, y1, x2, y2, 0.25)
    pcbnew.SaveBoard(BOARD, b)
    print("silkscreen written")


def strip():
    """Board-level silkscreen texts and lines all belong to this script."""
    b = pcbnew.LoadBoard(BOARD)
    old = [d for d in b.GetDrawings() if d.GetLayer() == pcbnew.F_SilkS]
    for d in old:
        b.Remove(d)
    pcbnew.SaveBoard(BOARD, b)


if __name__ == "__main__":
    import sys
    strip() if "--strip" in sys.argv else main()
