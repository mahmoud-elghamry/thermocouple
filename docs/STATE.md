# Current state

**Read this second, after `AGENTS.md`. Update it before you finish a session.**

**Hard limit: 60 lines.** If it does not fit, the detail belongs in
`docs/ISSUES.md`.

---

**Last updated:** 2026-09-07

## Last session

Full review across structure, firmware, schematic and board. The hardware
record held up: the MCU pin map in the netlist matches `mcal/board.c` exactly,
the energised-to-run chain is right (`R30` gate stopper, `R31` 100k pull-down,
`Q1` source on `GND_CTRL`, `D3` flyback), the eight CS lines carry 10k
fail-safe pull-ups on the isolated side, and the input filters keep the
10:1 differential-to-common-mode capacitor ratio that CMRR depends on.

Three findings were not on the record. `I-030` (blocker): the 8-channel
application links the **MAX6675** bank driver, so the MAX31856 board has no
firmware at all. `I-031`: the two apps drive `PB3` with opposite polarity and
both images are tracked. `I-032`: no crystal, and at the factory `CKSEL`
default the 8 MHz build runs at 1 MHz, which turns the 500 ms scan into 4 s.
Also `I-033` (root `README.md` still names the superseded board as final) and
`I-034` (the ERC report predates the last board run).

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

1. **`I-030`** — write the MAX31856 bank driver. Until it exists the board
   cannot be brought up at all, and `I-011`/`I-012`/`I-014` are fixes to a
   driver that does not target this hardware.
2. **`I-028`** — decide where the 24 V comes from. A panel supply needs no
   change; the engine's own battery needs a wider-input regulator. It is the
   only open item that can still change the circuit.
3. **`I-002`** — redraw the schematic as a real drawing: 171 symbols, 543
   labels, **zero wires**. Independent of the layer count.
4. **`I-012`** — store the setpoint in EEPROM. The user states plainly that it
   must be operator-settable and survive a power cycle; today any reset returns
   it to 200 degC.
5. **`I-025`** — 2-layer versus ordering 4-layer abroad. Layout only.
6. **`I-032`** — fix the clock: fuse map first, crystal decision second.
7. **`I-014`** — the rest of the firmware safety items.

## Careful

`generate_board.py` clears every track, via, zone and drawing. Anything routed
by hand in KiCad is erased on the next run, so fixes belong in the pipeline.
One session on the hardware at a time; close KiCad before running anything that
writes the board.
