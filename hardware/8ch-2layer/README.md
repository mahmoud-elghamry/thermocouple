# 8ch-2layer — two-layer backup of the 8-channel board

**Status 2026-09-27: routed, NOT finished.** DRC with `--schematic-parity`:
**0 violations, 0 parity errors, 14 unconnected pads - all 14 on
`/+3V3_SENS`**, the sensor supply that was an inner plane on the four-layer
board. `close_gaps.py` could not reach them. Next step if this board is ever
needed: a `+3V3_SENS` pour on B.Cu under the sensor island (or fixed vias
like `8ch`'s), then re-run. Freerouting took hours here, against ~12 min on
four layers.

**A backup, not the design.** The board that goes to fabrication is
`hardware/8ch/` (four layers). This folder exists because four-layer
fabrication may be hard to source (`I-025`). If the owner ends up needing a
board that any two-layer shop can make, this one is ready to judge.

## What differs from `hardware/8ch/`

Everything was copied from `hardware/8ch/` on 2026-09-26, with the
schematic taken as-is. Only the board generation changed:

| | `8ch` (4 layers) | `8ch-2layer` |
|---|---|---|
| Copper layers | F.Cu, In1 (three ground planes), In2 (three supply planes), B.Cu | F.Cu, B.Cu |
| Grounds `GND_SENS`/`GND_CTRL`/`GND_RS485` | inner plane + outer pours | routed tracks + pours on both faces, stitched |
| Supplies `+3V3_SENS`/`+5V_CTRL`/`+5V_RS485` | inner plane | routed tracks (net-class widths 0.6 mm) |
| Fixed channel vias to the planes | 32 | none (no plane to reach) |
| Isolation keepouts, clearances, net classes | same | same |

The edits are in `generate_board.py`, `init_board.py`, `route.py`,
`board/zones.py` and `board/stitching.py`, each marked "two-layer variant".

## Rules

* **The schematic lives in `hardware/8ch/`.** The six `.kicad_sch` files here
  are a copy, so parity checks work. Change the circuit there, then copy the
  files across; never edit them here.
* The `sch_layout/` and `populate_schematic.py` tools were deliberately left
  out of this folder.
* **What is weaker on two layers:** there is no plane pair under the analogue
  front ends, so the return path and interplane decoupling that `8ch` relies
  on are gone. The MAX31856 decoupling target of 4 mm in `check_board.py` was
  relaxed for the plane. The design review asked for 2 mm without one.
  Measurement settles it either way.
* Same gates as `8ch`: `validate.ps1`, `check_board.py`, and DRC with
  `--schematic-parity`. The results are recorded in `docs/STATE.md`.
