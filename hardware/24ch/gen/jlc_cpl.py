"""CPL-JLC.csv: the placement list adjusted for JLCPCB's part models, for the JLC website only.

Two differences between KiCad and JLC's models, both read from JLC's own preview of release 011858 (2026-10-21):
* rotation 0 differs for some packages (pink pin-1 dot of the model vs the pin-1 mark on our silkscreen);
  the offsets agree with the usual community table (SOIC/TQFP 270, SOT-23 180);
* JLC centres its model on Mid X/Y, while KiCad's through-hole footprints (terminals, headers, LEDs,
  electrolytic, switches, DC-DC) have their origin on pin 1 - the models sat off their holes. For every
  footprint with a drilled pad, Mid X/Y is moved to the centre of its pads.
CPL.csv stays the plain KiCad list for other assemblers. Runs in KiCad's python (needs pcbnew):
    "C:/Program Files/KiCad/10.0/bin/python.exe" jlc_cpl.py <release folder>
Checked part by part on JLC's preview of the corrected file (2026-10-21): every polarised part matched its silk
pin-1 mark except the G6K relays, which needed 270 as well (KiCad's footprint is the datasheet top view turned
90 degrees; the G6K coil has polarity, so the assembly remark also asks their engineer to check K701/K702).
"""
import csv
import os
import sys

import pcbnew

# package-name prefix -> degrees added to KiCad's rotation (counter-clockwise, seen from the top)
OFFSET = [
    ("TQFP-", 270),            # U501: model pin 1 at bottom-left, silk pin 1 top-left
    ("SOIC-", 270),            # U403-U405, U703: model leads on the wrong pair of sides
    ("HSOP-", 270),            # U601
    ("SOT-23", 180),           # SOT-23 and SOT-23-5: model mirrored end for end
    ("SOT-363", 180),          # TMP126 SC-70-6
    ("LED_D3.0mm", 180),       # D702, D712: model cathode on the anode pad
    ("PinHeader_", 270),       # J502, J501, JP731-JP733: model stood across the pad row (owner spotted J501)
    ("Relay_DPDT_Omron_G6K", 270),  # K701/K702: model pins in rows, our pads in columns; model pin 1 bottom-left
    ("Converter_DCDC_Murata_CRE1", 270),  # U401 B0505S: model stood across its pin row (owner spotted it);
                                          # pin 1 must land on the right-hand pad (GND), else input and output swap
]


def offset(pkg):
    return next((d for p, d in OFFSET if pkg.startswith(p)), 0)


def pad_centre_shift(board):
    """ref -> (dx, dy) mm from the footprint origin to the centre of its pads, for through-hole footprints."""
    out = {}
    for fp in board.GetFootprints():
        pads = list(fp.Pads())
        if not any(p.GetDrillSize().x > 0 for p in pads):
            continue
        xs = [p.GetPosition().x for p in pads]
        ys = [p.GetPosition().y for p in pads]
        o = fp.GetPosition()
        dx = pcbnew.ToMM((min(xs) + max(xs)) // 2 - o.x)
        dy = pcbnew.ToMM((min(ys) + max(ys)) // 2 - o.y)
        if abs(dx) > 0.01 or abs(dy) > 0.01:
            out[fp.GetReference()] = (dx, dy)
    return out


def main(rel):
    board = pcbnew.LoadBoard(os.path.join(rel, "source-snapshot", "thermo24.kicad_pcb"))
    shift = pad_centre_shift(board)
    pkg = {r["Ref"]: r["Package"] for r in csv.DictReader(open(os.path.join(rel, "pos.csv"), encoding="utf-8"))}
    rows = list(csv.reader(open(os.path.join(rel, "CPL.csv"), encoding="utf-8")))
    turned, moved = [], []
    for r in rows[1:]:
        d = offset(pkg[r[0]])
        if d:
            r[4] = f"{(float(r[4]) + d) % 360:.6f}"
            turned.append(r[0])
        if r[0] in shift:
            dx, dy = shift[r[0]]
            r[1] = f"{float(r[1][:-2]) + dx:.6f}mm"
            r[2] = f"{float(r[2][:-2]) - dy:.6f}mm"    # CPL y is up, board y is down
            moved.append(r[0])
    with open(os.path.join(rel, "CPL-JLC.csv"), "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    print(f"CPL-JLC.csv: {len(turned)} of {len(rows) - 1} turned:", " ".join(turned))
    print(f"centred on their pads ({len(moved)}):", " ".join(f"{m}{tuple(round(v, 2) for v in shift[m])}" for m in moved))


if __name__ == "__main__":
    main(sys.argv[1])
