"""The technician's kit: every part the factory does not fit (0027, I-078).

The factory fits SMD only; the technician fits every through-hole part and
wires the panel. Through-hole is read from the board itself (the footprint's
through-hole attribute), so the list cannot drift from the layout. Parts that
are not on the board at all (socket, LCD, shunts, panel fuse) are listed in
EXTRAS below.

    <KiCad python> kit_list.py OUT.csv [BOARDS]     # default 3 boards (0024)

Run with KiCad's bundled Python.
"""
from __future__ import annotations

import csv
import sys
from collections import OrderedDict
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
BOARD = ROOT / "thermocouple_8ch.kicad_pcb"

# Needed for a working unit but not placed on the board. Per board.
EXTRAS = [
    ("socket for U1", "DIP-40 IC socket, 15.24 mm row", "", "C2332", 1,
     "U1's footprint is the socket; the ATmega32A plugs in after programming"),
    ("LCD", "16x2 character LCD, HD44780-compatible, 5 V, LED backlight", "", "", 1,
     "buy locally; check the pin order against J2 before fitting (I-078)"),
    ("LCD cable", "16-way 2.54 mm cable/header to J2, length to suit the panel", "", "", 1,
     "keyed or marked pin 1"),
    ("jumper shunts", "2.54 mm shunt for JP1-JP3 (RS-485 termination/bias)", "", "C100114", 3,
     "fit where the RS-485 bus needs termination/bias; unused until a master exists (I-086)"),
    ("panel fuse", "1 A time-delay DC fuse, >= 80 V DC, >= 10 kA breaking, + holder", "", "", 1,
     "decision 0020: in the + lead at the battery end; exact part still to choose"),
]


def field(fp, name: str) -> str:
    try:
        return fp.GetFieldText(name) or ""
    except Exception:
        return ""


def main() -> None:
    out = Path(sys.argv[1])
    boards = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    board = pcbnew.LoadBoard(str(BOARD))
    groups: "OrderedDict[tuple, list[str]]" = OrderedDict()
    for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
        ref = fp.GetReference()
        if not (fp.GetAttributes() & pcbnew.FP_THROUGH_HOLE):
            continue
        if ref.startswith(("H", "TP", "FID")):
            continue            # mounting holes, test pads: nothing to buy
        # One line per thing to buy: grouped by part number, not by the
        # value printed on the schematic (five SW_PUSH are one purchase).
        key = (field(fp, "MPN") or fp.GetValue(), field(fp, "Manufacturer"),
               field(fp, "LCSC"), fp.GetFPIDAsString().split(":")[-1])
        groups.setdefault(key, []).append((ref, fp.GetValue()))
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Refs", "What", "MPN", "Manufacturer", "LCSC", "Per board",
                    f"Total for {boards}", "Note"])
        for (mpn, maker, lcsc, footprint), items in groups.items():
            refs = " ".join(r for r, _ in items)
            values = ", ".join(dict.fromkeys(val for _, val in items))
            note = "buy at DigiKey 1470-1345-5-ND (0027)" if "IA0505S" in mpn else ""
            w.writerow([refs, f"{values} ({footprint})", mpn, maker, lcsc,
                        len(items), len(items) * boards, note])
        for refs, what, mpn, lcsc, n, note in EXTRAS:
            w.writerow([refs, what, mpn, "", lcsc, n, n * boards, note])
    print(f"wrote {out}: {len(groups)} through-hole lines + {len(EXTRAS)} extras, x{boards} boards")


if __name__ == "__main__":
    main()
