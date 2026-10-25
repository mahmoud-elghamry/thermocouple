"""Delete the tracks and vias of NET that lie entirely inside a box (incremental repair).
    python delbox.py NET X1 Y1 X2 Y2 [--dry]       (KiCad python; board = THERMO8_BOARD or thermo8.kicad_pcb)
Only the named net; a segment is deleted only when both ends are inside the box."""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.environ.get("THERMO8_BOARD", os.path.join(os.path.dirname(HERE), "thermo8.kicad_pcb"))


def main():
    net, box, dry = sys.argv[1], [float(v) for v in sys.argv[2:6]], "--dry" in sys.argv
    x1, y1, x2, y2 = box
    inside = lambda p: x1 <= pcbnew.ToMM(p.x) <= x2 and y1 <= pcbnew.ToMM(p.y) <= y2
    b = pcbnew.LoadBoard(BOARD)
    gone = [t for t in b.GetTracks() if t.GetNetname().rsplit("/", 1)[-1] == net and
            (inside(t.GetPosition()) if t.Type() == pcbnew.PCB_VIA_T else inside(t.GetStart()) and inside(t.GetEnd()))]
    for t in gone:
        kind = "via" if t.Type() == pcbnew.PCB_VIA_T else "track"
        print(f"{'would delete' if dry else 'delete'} {kind} {net} "
              f"({pcbnew.ToMM(t.GetPosition().x):.2f},{pcbnew.ToMM(t.GetPosition().y):.2f})")
    if not dry:
        for t in gone:
            b.Remove(t)
        pcbnew.SaveBoard(BOARD, b)
    print(f"{len(gone)} items")


if __name__ == "__main__":
    os.environ.setdefault("THERMO24_WRITER_CLAIM", os.path.join(os.path.dirname(HERE), "output", ".writer.json"))
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "24ch", "gen"))
    import guard
    with guard.claim(BOARD, "delbox.py"):
        main()
