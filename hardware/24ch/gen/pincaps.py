"""Gate for I-111: every IC supply/critical pin has its capacitor beside it.

ERC/DRC cannot see a decoupling cap 20 mm from its pin; this measures it.
For each (ref, pin, limit_mm) below: the nearest capacitor pad on the same net,
centre to centre. Prints a table and exits non-zero if any pin is over its limit.
Run with KiCad's python:  python pincaps.py [board]
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), "thermo24.kicad_pcb")
T = pcbnew.ToMM

CHECK = [  # (ref, pin, limit mm, what)
    ("U601", "2", 3.0, "LM5164 VIN ceramic input cap"),
    ("U601", "7", 3.0, "LM5164 BST bootstrap cap (BST-SW)"),
    ("U601", "8", 3.0, "LM5164 SW side of the bootstrap cap"),
    ("U601", "5", 5.0, "LM5164 FB network"),
    ("U403", "1", 3.0, "ISO7761 VCC1"), ("U403", "16", 3.0, "ISO7761 VCC2"),
    ("U404", "1", 3.0, "ISO7761 VCC1"), ("U404", "16", 3.0, "ISO7761 VCC2"),
    ("U405", "1", 3.0, "ISO7761 VCC1"), ("U405", "16", 3.0, "ISO7761 VCC2"),
    ("U101", "26", 3.0, "AD7124 supply"), ("U201", "26", 3.0, "AD7124 supply"),
    ("U301", "26", 3.0, "AD7124 supply"), ("U301", "2", 3.0, "AD7124 supply"),
    ("U501", "5", 3.0, "ATmega VCC"), ("U501", "17", 3.0, "ATmega VCC"),
    ("U501", "38", 3.0, "ATmega VCC"), ("U501", "27", 3.0, "ATmega AVCC"),
]


def main():
    b = pcbnew.LoadBoard(BOARD)
    caps = [(fp.GetReference(), p) for fp in b.GetFootprints() if fp.GetReference().startswith("C")
            for p in fp.Pads()]
    bad = 0
    for ref, pin, lim, what in CHECK:
        fp = b.FindFootprintByReference(ref)
        p = [q for q in fp.Pads() if q.GetNumber() == pin]
        if not p:
            print(f"{ref}.{pin}: no such pad"); bad += 1
            continue
        p = p[0]
        net = p.GetNetname()
        if ref == "U601" and pin in ("7", "8"):
            net_ok = ("BST_5V", "SW_5V")
            same = [(r, q) for r, q in caps if q.GetNetname().rsplit("/", 1)[-1] in net_ok]
        else:
            same = [(r, q) for r, q in caps if q.GetNetname() == net]
        x, y = T(p.GetPosition().x), T(p.GetPosition().y)
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
