"""CPL-JLC.csv: the placement list with JLCPCB's rotation offsets, for the JLC website only.

KiCad and JLC's part models disagree on "rotation 0" for some packages, so JLC's preview showed them turned.
Offsets below were read from JLC's own preview of release 011858 (2026-10-21, pink pin-1 dot of the model vs
the pin-1 mark on our silkscreen); they agree with the usual community table (SOIC/TQFP 270, SOT-23 180).
CPL.csv stays the plain KiCad list for other assemblers.
    py -3 jlc_cpl.py <release folder>
Relays K701/K702 are NOT corrected here: JLC's model puts pin 1 on the other row, which no rotation fixes
(G6K coil has polarity) - their engineer must check them on the "Confirm Parts Placement" preview.
"""
import csv
import os
import sys

# package-name prefix -> degrees added to KiCad's rotation (counter-clockwise, seen from the top)
OFFSET = [
    ("TQFP-", 270),            # U501: model pin 1 at bottom-left, silk pin 1 top-left
    ("SOIC-", 270),            # U403-U405, U703: model leads on the wrong pair of sides
    ("HSOP-", 270),            # U601
    ("SOT-23", 180),           # SOT-23 and SOT-23-5: model mirrored end for end
    ("SOT-363", 180),          # TMP126 SC-70-6
    ("LED_D3.0mm", 180),       # D702, D712: model cathode on the anode pad
    ("PinHeader_1x16", 270),   # J502: model stood across the pad row
]


def offset(pkg):
    return next((d for p, d in OFFSET if pkg.startswith(p)), 0)


def main(rel):
    pkg = {r["Ref"]: r["Package"] for r in csv.DictReader(open(os.path.join(rel, "pos.csv"), encoding="utf-8"))}
    rows = list(csv.reader(open(os.path.join(rel, "CPL.csv"), encoding="utf-8")))
    changed = []
    for r in rows[1:]:
        d = offset(pkg[r[0]])
        if d:
            r[4] = f"{(float(r[4]) + d) % 360:.6f}"
            changed.append(r[0])
    with open(os.path.join(rel, "CPL-JLC.csv"), "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    print(f"CPL-JLC.csv: {len(changed)} of {len(rows) - 1} rotated:", " ".join(changed))


if __name__ == "__main__":
    main(sys.argv[1])
