# Current state

**Read this second, after `AGENTS.md`. Update it before you finish a session.**

**Hard limit: 60 lines.** If it does not fit, the detail belongs in
`docs/ISSUES.md`.

---

**Last updated:** 2026-09-07

## Last session

Full review, then sixteen issues closed. **No hardware file was touched** - the
board is frozen at REV A0 (`docs/decisions/0010`) and the schematic is
unchanged.

`I-030` was the big one: the eight-channel application linked the **MAX6675**
bank driver, so the MAX31856 board had no firmware at all. It has one now. With
it: EEPROM setpoint behind a CRC, and a blank unit refuses to run rather than
invent a limit (`I-012`); stuck and impossible readings detected (`I-011`); the
SPI timeout no longer slips the byte stream (`I-014`); a fuse map (`I-015`) -
which found that the factory `CKSEL` default runs the part at 1 MHz, making
every delay eight times too long and the trip four times too slow, silently.

Sourcing the passives (`I-007`) turned up `I-035`, a blocker: **100 nF C0G does
not exist in 0805** - that is `C1` and its seven siblings. `I-002` was attempted
and reverted; see below.

## Measured, not claimed

`hardware/8ch/` is placed, routed and has fabrication output - an **engineering
prototype**. None of the `AGENTS.md` hard constraints is closed by that: the
barrier has never been measured and nothing has been built or EMC tested.

| Check | Now |
|---|---|
| DRC errors / unconnected / parity | **0 / 0 / 0** |
| DRC warnings | 9 (8 silkscreen, 1 dangling via) |
| ERC errors / warnings | **0** / 171, all `endpoint_off_grid` (`I-002`) |
| `check_board.py` | all six pass |
| Netlist vs REV A0 contract | **167 components, 154 nets, 555 pins - IDENTICAL** |
| Firmware, 4 images, host tests | builds `-Werror`, **all checks passed** |

## Next actions, in order

1. **`I-035`** — decide the differential filter capacitor. The catalog already
   resolves it to X7R with the reasoning; what is needed is a decision and the
   `Value` text corrected in the schematic.
2. **`I-028`** — decide where the 24 V comes from. A panel supply needs no
   change; the engine's own battery needs a wider-input regulator. It is the
   only open item that can still change the circuit.
3. **`I-002`** — redraw the schematic as a real drawing: 171 symbols, 543
   labels, **zero wires**. Independent of the layer count.
4. **`I-012`** — store the setpoint in EEPROM. The user states plainly that it
   must be operator-settable and survive a power cycle; today any reset returns
   it to 200 degC.
5. **`I-025`** — 2-layer versus ordering 4-layer abroad. Layout only.
6. **`I-013`** — measure the trip time on hardware. The budget says 623 ms;
   nothing has confirmed it.

## `I-002` — for whoever picks it up

Delegated once and reverted: it produced seven hierarchical sheets with 612
wires and **a netlist of zero components**, because the symbols were written
without the instance data KiCad needs. Four things are known now:

- `kicad-tool sch edit` has `wire add` and `junction add`. Generate through it;
  do not write `.kicad_sch` as text - that is where the attempt went wrong.
- A wire between two pins that already share a label cannot change the netlist,
  so the work can be verified step by step.
- **The obstacle is the grid, not the wires.** Pins land on 28.19, 6.92 because
  symbols sit at integer millimetres. Re-place them on the 1.27 mm grid first;
  that is also what clears the 171 warnings.
- `prune_dangling_labels()` drops any label not on a pin, so re-running
  `populate_schematic.py --refresh-properties` after a move is self-healing.

Gate: `netlist_fingerprint.py netlist-baseline-reva0.json <new>.net` must print
`IDENTICAL`. Never edit the baseline to make it pass.

## Careful

`generate_board.py` clears every track, via, zone and drawing. Anything routed
by hand in KiCad is erased on the next run, so fixes belong in the pipeline.
One session on the hardware at a time; close KiCad before running anything that
writes the board.
