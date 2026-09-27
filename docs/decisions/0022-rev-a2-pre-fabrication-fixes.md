# 0022 — REV A2: the pre-fabrication review's fixes, and a new revision for them

* Status: accepted
* Date: 2026-09-28
* Deciders: owner (asked the agent to choose; "شوف الأنسب")
* Relates to: `I-065`, `I-066`, `I-067`, `I-068`, `I-069`; amends `0014`, `0016`

## Context

The 2026-09-27 review checked the REV A1 netlist pin by pin against the
datasheets. It found two high findings that had to be settled before ordering
(`I-065`, `I-066`) and three medium ones (`I-067`..`I-069`). REV A1 had a
finished fabrication package in `production/8ch-reva1/`, but it had not been
ordered.

The arithmetic behind every value here is in `CALCULATIONS.md` section 4.

## Decisions

### I-065 — both fixes: (a) R61 2k2 and (b) isolators without the F suffix

Neither fix does the job alone:

* **(b) alone** keeps every CS deselected in reset, because ISO776x without F
  drives an open input HIGH (ISO7761 datasheet, function table). But U11's MISO
  output is still push-pull and still wired straight to the AVR's MISO, so
  ISP still fights it.
* **(a) alone** lets ISP work. But with F parts all eight MAX31856 would still
  be selected while the AVR sits in reset. They would then receive the ISP's
  SCK/MOSI traffic as register writes and drive MISO_SENS against each other.

So both. (b) costs nothing: same package, same pinout, same datasheet. It also
makes the isolators agree with R17-R24, the CS pull-ups that were already
there "so CS defaults high". (a) is one 0805.

**R61 = 2k2, not the 1k first proposed.** The ISO7761 recommends at most
4 mA of output current at 5 V. 1k would allow 5 mA of contention, 2k2 allows
2.3 mA. The cost is 33 ns of RC delay on a 500 kHz SPI and 0.5 V on MISO against
the AVR's pull-up. Both are far inside the limits.

Rejected: **pull-ups on CS1-8_CTRL**. Eight parts, where a part-number change does
the same thing. **Programming only in an external programmer**: it works because
U1 is socketed, but it leaves the reset-state contention and makes every
firmware update a board-out job.

### I-066 — Q1 becomes a BSS131 (240 V, SOT-23)

Q1's drain sits at the battery rail whenever the relay is off. A shorted Q1
energises the relay with no MCU, which is RUN_PERMIT granted by a dead part.
So Q1 must survive the worst voltage D2 lets through, 96.8 V.

| Candidate | V(BR)DSS | Against 96.8 V | Verdict |
|---|---|---|---|
| 2N7000 (fitted) | 60 V | below D2's 66.7 V minimum breakdown | the finding |
| BSS123 | 100 V | 3 % margin | rejected: the margin is thin exactly where the failure is unsafe |
| **BSS131** (Infineon, AEC-Q101) | **240 V** | **2.5x** | **chosen**: VGS(th) at most 1.8 V, RDS(on) at most 20 Ohm at 4.5 V, which is 0.33 V at 16.7 mA |
| BSS127 | 600 V | - | rejected: 21-70 mA and 160-600 Ohm, too weak for the coil |

The cost is about $0.10 against $0.02. One real cost: the BSS131 is ESD Class 0.
It is only exposed through R30 from the MCU, but it needs ESD handling at
assembly. No TO-92 part of this rating was sought: the package change is free,
because the board is regenerated for R61 anyway.

### I-067 — R53/R54 become 100k/22k

Same 4.3 V at 24 V (4.22 V before). At a 58 V dump the current into PC2's clamp
falls from 1.2 mA to 0.28 mA, under the ~1 mA Microchip allows. The input still
reads a valid high down to 16.6 V (17.0 V before). Rejected: **a clamp diode at
PC2**. It works too, but it is a part, where changing two values does the same.

### I-068 — F1 becomes 1812L075/60GR (60 V, 0.75 A hold, 1812)

60 V covers the 58 V suppressed load dump, the design basis of `0016`. The
0.75 A hold still holds the 0.39 A cranking-floor current up to 70 °C
(0.45 A), where a 0.5 A part of the same series is down to 0.35 A at 60 °C.
Stock at LCSC is thin (2265) and the maker is LUTE, not Littelfuse. The
Littelfuse-numbered 60 V parts at LCSC were 0.5 A.

The price of the higher hold is that faults between 0.75 A and 1.5 A may
not trip it. A fault after the regulator cannot get there: the LM5164 limits
its own peak current to 1.25-1.75 A at 5 V, which is at most ~0.4 A from 24 V.
A fault before the regulator is a failed TVS or capacitor, and those go on to a
hard short, which trips the PTC (0.2 s at 8 A) and the panel fuse (`0020`).

Rejected: **1812L050/72GR** (72 V, 0.5 A). It has more voltage margin but may trip
while cranking in a warm panel. **Removing F1**: the panel fuse covers the lead,
but not a board fault well below 1 A.

### I-069 — D2 drawn unidirectional, D3 ordered as "M7"

D2 is now `Device:D_Zener`, which shows its polarity on the schematic. The pins
and the footprint are unchanged. D3's value and MPN are now **M7** (MDD, LCSC
`C95872`), the SMA 1N4007. The BOM can no longer be filled with the through-hole
DO-41 part by name. D2's `Manufacturer` now matches its LCSC code (R+O). U12's
description now warns against the "IA0505S-1WR3" of another maker.

### A new revision: REV A2

The circuit changed, and REV A1 has a complete, uploadable package. A board
that says "REV A1" with a different netlist is the fab mix-up waiting to
happen. So: `BOARD_REV = "A2"`, the netlist contract is
`netlist-baseline-reva2.json` (202 / 163 / 647), and the release goes to
`production/8ch-reva2/`. **`production/8ch-reva1/` must not be ordered.**

## How it was done

These are generative changes (`0012`), because a new part and two new
footprints mean re-placing. The schematic changes live in
`hardware/8ch/sch_layout/reva2.py`, which `fixes.py` applies to the label-only
base. `build.py` therefore still reproduces the whole schematic from source.
Then: `kicad-tool pcb sync`, `generate_board.py`, `route.py`, and the gates.
`populate_schematic.py` was updated to match, for the record.

## Consequences

* The board was re-routed from scratch; everything about it is re-verified,
  not inherited from REV A1 (`docs/STATE.md` has the reports).
* `hardware/8ch-2layer/` (parked, `I-025`) is now a revision behind.
* The ISO776x without F and the LUTE PTC have low LCSC stock. That is fine for a
  prototype run; check it before a production order.
