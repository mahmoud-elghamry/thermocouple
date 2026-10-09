# 0033 - 24-ch board: size kept, NORI as fab/assembler, routing method

* Status: accepted (engineer's call, owner delegated the details 2026-10-09)
* Date: 2026-10-09
* Builds on: `0031` (one 24-ch board), `0032` (circuit and parts)

## Context

The first routing runs stalled at ~85 unconnected. The owner asked whether a
bigger board (180 x 150) would help, and asked for size, cost, assembly and
installation to be settled before more execution. He named the fab house:
NORI Solutions (norisolutions.com), who have built for the company before and
usually order from China.

## Decisions

**D1 - Board stays 170 x 145 mm, barrier bands stay where they are.**
The stall was a rule problem, not a space problem (`docs/TOOLS.md`,
"24-channel board"): router clearance larger than the AD7124 LFCSP and relay
in-part pad gaps. After the fix the best run left 25 unconnected, then 13 after
scripted fixes, all finishable without moving parts.
Rejected: (A) moving the barrier 6-7 mm into the empty area under the LCD -
it puts the LCD standoffs H6/H8 (x 49.5) and H8/H9 (y 96.5) and their metal
hardware inside or beside the 3 mm band (Codex review 2026-10-09 agreed).
(B) 180 x 150 - helps only if the LCD and control side move too (full
re-placement); NORI quote 2026-10-09 for 4-layer bare boards: 170 x 145 is
EGP 8,710 for 5 / 11,500 for 10, 180 x 150 is EGP 8,960 / **14,160** (+23 % at 10).

**D2 - NORI Solutions is the intended fab and assembler.** Their published
limits (site, 2026-10-09): 4-6 layer track/space 0.09 mm, **pad-to-track
0.2 mm minimum**, drill 0.20 mm min, 1-2 oz, HASL/ENIG; assembly SMT/THT/mixed,
0402 minimum, single or double side, turnkey or consigned parts,
**inspection AOI + visual (no X-ray)**, 2-3 weeks for samples. Consequences:
a `.kicad_dru` pad-to-track 0.2 mm rule; the LFCSP exposed pad needs an
explicit stencil (window-pane paste) and via treatment agreed with them, and
every board gets a functional test because voids under the EP cannot be seen.
JLC-style BOM/CPL from `gen/fab.py` is the file format they ask for.

**D3 - Cold-junction sensor stays ADT7310 x6 for this revision.** It is the
most expensive BOM line ($32.4 of $104.9 per board, LCSC qty-1). TMP117
(C699536, about $1.03) would save about $26/board but is I2C, not an SPI
drop-in on the shared isolated bus - a circuit change that needs its own
review. Recorded as a later cost option (I-109).

**D4 - Routing method.** Generative scripts until placement is frozen; after a
result is kept, incremental only (`gen/finish.py`, locked tracks, router
continues). Last connections through Konnect with KiCad open, or a person in
KiCad; computer-use last. Details and the parameter comparison:
`docs/TOOLS.md`, "24-channel board".

*Added 2026-10-09 - three short runs on In2.Cu.* Under U301 every F.Cu crossing of
the B.Cu SPI bus was taken, so TC21_PA (~10 mm) and two CS_CJ5_ISO pieces (~8 + 7 mm)
run on In2.Cu, the +3V3_ISO plane layer; In1 (GND_ISO) stays whole under them, so
their return path is unchanged and the 3V3 plane only gets three narrow slots.
Rejected: moving C391/C392 or U301 (re-places the ADC decoupling and re-routes the
area) and a schematic pin swap (firmware change for one route). The TC21 pair is no
longer side by side (NA takes the long loop); acceptable for a slow, filtered
thermocouple input, recorded for the review.

**D5 - Schematic pages A4 or A3 only** (owner: no A2 paper). `build.py`
splits sheets and refuses a larger page.

## Consequences

* No re-placement; routing finishes incrementally on `output/kept-c.kicad_pcb`.
* NORI questions are tracked in I-106; the order package in I-078.
