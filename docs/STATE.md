# Current state

**Read second, after `AGENTS.md`. Update before finishing. Hard limit: 60 lines.**

**Last updated:** 2026-09-24 (cloud session)

## Last session

**`I-002` is closed: the schematic is a drawing.** Every block laid out by
function and wired, one label per wired group, done through Konnect by
`hardware/8ch/sch_layout/build.py` (repeatable; TOOLS.md, "Schematic layout").
**Drawing the relay found `I-058`, a blocker:** K1's coil is on pins 2-5, but
the MOSFET drain was on pin 1 (COM) - the relay could never have energised.
Fixed in the generator, schematic and REV A1 baseline (three pins, on purpose).
`I-057` closed: U12 relinked, ERC now 0 warnings everywhere.

## Measured, not claimed (Linux, KiCad 10.0.6, avr-gcc 7.3)

| Check | Result |
|---|---|
| `make -C firmware all test` | **exit 0**; 4 images, 3 suites `all checks passed` |
| Netlist vs `netlist-baseline-reva1.json` | **IDENTICAL** - 201 / 162 / 645 (baseline moved only by `I-058`) |
| ERC | **0 errors, 0 warnings** (was 171 `endpoint_off_grid`) |
| `check_mpn_consistency.py` / `source_passives.py --check` | 128 match / 38 types with MPN |
| `validate.ps1` | **fails at DRC: 226 parity** - the board is REV A0, not regenerated |
| `sch_layout/build.py` | reproduces the committed sheet byte-for-byte except UUIDs |

No Gerber release, SPICE, thermal, EMC or physical measurement; Proteus not run.

## Next actions

1. **Regenerate the board** (`I-061`) - authorized (`0014`). Placement for all
   201 parts now exists; routing leaves `RELAY_NC` (J3 order vs the real K1
   pins), one +5V gap and `I-060` (U14 vias, owner). PCB file still REV A0.
2. **Bench-check K1 before power-up** (`I-058`): 2-5 is the coil (~2.9 kOhm),
   1-4 closed and 1-3 open de-energised.
3. `I-028` tail: **`F1` is not adequate on a battery** (PTC breaks ~40 A, a
   battery pushes thousands) - external panel fuse. Then `emc`, bench `I-004`.
4. **Ask the owner** which `I-056` doc-system fixes to do; nothing started.
5. Cosmetic: `I-059` text overlaps - a KiCad-GUI touch-up.

## Tooling, and the traps it sets

`Konnect` is the only KiCad MCP (`0013`). Cloud sessions: `session-start.sh`
installs it + toolchain + KiCad's symbol libraries (TOOLS.md, "Cloud").
**`kicad-tool` clones a symbol to make a new one, so the clone inherits its
MPN** (`I-054`); run `check_mpn_consistency.py` after any run that adds parts.

## Preserve for hardware work

**The layout pass needs a label-only base.** `build.py` starts from `05d6abd`
and refuses a schematic with wires, because its router only knows the wires it
drew. After a generator change, commit the generator's label-only output and
pass it as `--base`; never run the router over the wired sheet.
`populate_schematic.py --refresh-properties` resets symbol positions (`I-052`):
on the wired sheet it would pull parts off their wires - re-run `build.py`.
Verify every step with `netlist_fingerprint.py`; never alter a baseline to
make it pass - `I-058` changed it deliberately, by three named pins.
