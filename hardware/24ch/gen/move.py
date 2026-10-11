"""Move footprints on the routed board, for a local repair (I-111, `0034` D3).

Deletes the tracks that touch a pad of each moved footprint (any net), then moves
it. What is left of those connections becomes dangling copper and unconnected
items: run `finish.py dangling`, then `maze.py` / `finish.py add` to re-route.
Never moves anything that is not named. Run with KiCad's python:
    python move.py REF X Y ROT [REF X Y ROT ...]      # mm, degrees; front side kept
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
BOARD = os.environ.get("THERMO24_BOARD", os.path.join(HW, "thermo24.kicad_pcb"))
mm = pcbnew.FromMM


def main(args):
    if len(args) % 4 or not args:
        raise SystemExit(__doc__)
    b = pcbnew.LoadBoard(BOARD)
    gone = []
    for i in range(0, len(args), 4):
        ref, x, y, rot = args[i], float(args[i + 1]), float(args[i + 2]), float(args[i + 3])
        fp = b.FindFootprintByReference(ref)
        if fp is None:
            raise SystemExit(f"move: no footprint {ref}")
        for t in b.GetTracks():
            own = [p for p in fp.Pads() if p.GetNetCode() == t.GetNetCode()]   # another net may end under a pad
            if t.Type() == pcbnew.PCB_VIA_T:
                hit = any(p.HitTest(t.GetPosition(), 0) for p in own)
            else:
                hit = any(p.HitTest(t.GetStart(), 0) or p.HitTest(t.GetEnd(), 0) for p in own)
            if hit and not any(t == g for g in gone):
                gone.append(t)
        fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        fp.SetOrientationDegrees(rot)
        print(f"move: {ref} -> ({x}, {y}) {rot} deg")
    for t in gone:
        b.Remove(t)
    pcbnew.SaveBoard(BOARD, b)
    print(f"move: removed {len(gone)} tracks/vias that touched the moved pads")


if __name__ == "__main__":
    import guard      # I-115: refuse while KiCad or another tool holds the board
    with guard.claim(str(BOARD), "move.py"):
        main(sys.argv[1:])
