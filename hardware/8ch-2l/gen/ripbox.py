"""Delete every track and via of the non-ground nets with an end inside a box, for a local re-route.

    python ripbox.py X1 Y1 X2 Y2 [--dry]        (KiCad python; board = THERMO8L_BOARD or thermo8.kicad_pcb)
Ground copper (fanout stubs, exposed-pad vias) stays. Run `finish.py --board 8l drc` afterwards.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.environ.get("THERMO8L_BOARD", os.path.join(os.path.dirname(HERE), "thermo8.kicad_pcb"))
GROUNDS = {"GND", "GND_ISO", "GND_RS485"}


def main():
    x1, y1, x2, y2 = map(float, sys.argv[1:5])
    b = pcbnew.LoadBoard(BOARD)
    T = pcbnew.ToMM

    def inside(p):
        return x1 <= T(p.x) <= x2 and y1 <= T(p.y) <= y2

    gone = []
    for t in b.GetTracks():
        if t.GetNetname().rsplit("/", 1)[-1] in GROUNDS:
            continue
        pts = [t.GetPosition()] if t.Type() == pcbnew.PCB_VIA_T else [t.GetStart(), t.GetEnd()]
        if any(inside(p) for p in pts):
            gone.append(t)
    nets = sorted({t.GetNetname().rsplit("/", 1)[-1] for t in gone})
    print(f"ripbox: {len(gone)} items on {len(nets)} nets: {', '.join(nets)}")
    if "--dry" in sys.argv:
        return
    for t in gone:
        b.Remove(t)
    pcbnew.SaveBoard(BOARD, b)


if __name__ == "__main__":
    os.environ.setdefault("THERMO24_WRITER_CLAIM", os.path.join(os.path.dirname(HERE), "output", ".writer.json"))
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "24ch", "gen"))
    import guard      # I-115
    with guard.claim(str(BOARD), "ripbox.py"):
        main()
