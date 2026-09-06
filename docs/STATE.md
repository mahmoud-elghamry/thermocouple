# Current state

**Read this second, after `AGENTS.md`. Update it before you finish a session.**

**Hard limit: 60 lines.** If it does not fit, the detail belongs in
`docs/ISSUES.md`.

---

**Last updated:** 2026-09-07

## Last session

Closed `I-001`. The nine open connections were three separate causes, not nine
routing problems: `add_plane_stitching` filtered on `+3V3_SENS` and skipped five
of the six plane nets, `finish()` poured the outer grounds after the stitching
pass so their isolated pieces did not exist yet, and `C56`/`C57`/`R33` sat in a
1 mm strip. Added `stitch_pour_islands`, reordered the finishing steps, added a
0.6 mm via fallback, moved that row 1 mm. `docs/decisions/0007`.

**Fabrication output is generated** in `production/8ch/` — eleven Gerber layers,
Excellon drill and map, `.gbrjob`, placement CSV and an IPC-D-356 netlist.

## Where the work is

`hardware/8ch/` is placed, routed, checked and has fabrication output. It is
releasable as an **engineering prototype**. Nothing in the `AGENTS.md` hard
constraints is closed by this: the sensor island still isolates the group and
not the channels, the barrier has never been measured, and no EMC or real-sensor
testing has been done.

## Measured, not claimed

From `hardware/8ch/drc-report.rpt` and `erc-report.rpt`, 2026-09-07:

| Check | Start | Now |
|---|---|---|
| DRC clearance / shorting / crossing / hole | 304 / 19 / 22 / 6 | **0 / 0 / 0 / 0** |
| DRC unconnected items | 46 | **0** |
| DRC warnings | 13 | 9 (6 silk overlap, 2 silk over pad, 1 dangling via) |
| Schematic ↔ PCB parity | — | **0** |
| ERC errors | 7 | **0** |
| ERC warnings | 189 | 171 (all `endpoint_off_grid`, from `I-002`) |

`check_board.py` passes all six: island membership, isolation barrier,
decoupling proximity, cold-junction distance, filter symmetry, routing
completeness. Zero courtyard overlaps, zero parts off the board edge.

## Next actions, in order

1. **`I-028`** — decide where the 24 V comes from. A panel supply needs no
   change; the engine's own battery needs a wider-input regulator. It is the
   only open item that can still change the circuit.
2. **`I-002`** — redraw the schematic as a real drawing: 171 symbols, 543
   labels, **zero wires**. Independent of the layer count.
3. **`I-012`** — store the setpoint in EEPROM. The user states plainly that it
   must be operator-settable and survive a power cycle; today any reset returns
   it to 200 degC.
4. **`I-025`** — 2-layer versus ordering 4-layer abroad. Layout only.
5. **`I-014`** — the rest of the firmware safety items.

## Corrected on 2026-09-07

Two facts in the record were wrong, both from assuming instead of asking:
there is **no VFD** (it is an engine), and the eight sensors are on **eight
different cylinders of one engine**, not one cylinder. The board lives in its
own panel 50 m away, so vibration and ambient heat are not constraints and the
socketed MCU is fine. `docs/decisions/0009`.

## Careful

`generate_board.py` clears every track, via, zone and drawing. Anything routed
by hand in KiCad is erased on the next run, so fixes belong in the pipeline.
One session on the hardware at a time; close KiCad before running anything that
writes the board.
