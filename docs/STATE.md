# Current state

**Read second, after `AGENTS.md`. Update before finishing. Hard limit: 60 lines.**

**Last updated:** 2026-09-26 (workstation)

## Last session

**`I-061` closed: the REV A1 board is regenerated and routed, uncommitted.**
Owner decisions: U14 keeps 0.2 mm thermal vias (`0017`); J3 keeps COM/NO/NC and
moves to K1 (`0018`). Fixed on the way: R59/R60 turned 270 (R60's GND pad was
walled in); MAX31856 GND pins get fixed vias like the supply pins
(`stitching.py` - left to the pour, one floated per run); `route.py` re-stitches
after closing gaps. Earlier: `I-002` wired the sheet, `I-058` fixed K1's pins.

## Measured, not claimed

| Check | Result |
|---|---|
| `check_board.py` (KiCad 10.0.3) | **all 6 ok**, incl. routing completeness |
| DRC on a copy, `--refill-zones --schematic-parity` | **0 errors, 0 unconnected, 0 parity**; 14 silk warnings (`I-006`) |
| `validate.ps1` (`powershell.exe`; no pwsh here) | **stops at ERC: 1 `lib_symbol_issues`** - KiCad 10.0.3 lacks U12's library (`I-063`) |
| ERC / netlist (cloud, 10.0.6, 2026-09-24) | 0/0; **IDENTICAL** 201 / 162 / 645; sheet unchanged since (sha256) |
| `make -C firmware all test` (cloud) | exit 0; 4 images, 3 suites pass |

Freerouting's own "157 violations" is its plane-less model, never the verdict.
No Gerber release, SPICE, thermal, EMC or physical measurement; Proteus not run.

## Next actions
1. **Owner: review and commit** the board + `placement.py`/`route.py`/`stitching.py`/`apply_rules.py`.
2. **`I-063`**: update the workstation to KiCad >= 10.0.6, re-run `validate.ps1`.
3. **Bench-check K1 before power-up** (`I-058`): 2-5 ~2.9 kOhm, 1-4 shut, 1-3 open.
4. Fab prep: `I-051` (15 parts), `I-025` (4-layer source), 0.2 mm quote, then Gerbers.
5. `I-028`: external panel fuse. Ask the owner about `I-056`, `I-046`. Later `I-062`.

## Tooling, and the traps it sets

`Konnect` is the only KiCad MCP (`0013`); the cloud hook installs it (TOOLS.md). **`kicad-tool` clones a symbol to make a new one, so the clone inherits its MPN** (`I-054`); run `check_mpn_consistency.py` after any run that adds parts.

## Preserve for hardware work

**The layout pass needs a label-only base.** `build.py` starts from `05d6abd`
and refuses a schematic with wires, because its router only knows the wires it
drew. After a generator change, commit the generator's label-only output and
pass it as `--base`; never run the router over the wired sheet.
`populate_schematic.py --refresh-properties` moves symbols (`I-052`): re-run `build.py`.
Verify with `netlist_fingerprint.py`; never edit a baseline to pass (`I-058` did, on purpose).
