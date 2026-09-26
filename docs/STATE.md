# Current state

**Read second, after `AGENTS.md`. Update before finishing. Hard limit: 60 lines.**

**Last updated:** 2026-09-26 (workstation)

## Last session

**`I-062` done: A3 root + `channel.kicad_sch` (A4) used by TC1-TC8** (`0019`).
40 channel nets renamed `/TCn_X` -> `/TCn/X`, nothing else; JTC1-8 -> `K_TYPE`;
baseline regenerated from the proven netlist (`--allow-renames`: 645 pins on the
same nets). **`I-045` closed:** `C45` (U12's input cap) was 55 mm away beside
U10 - `C45`/`C46` moved under U12, 18/10 mm -> 4.2 mm; board re-routed.
**Two gates fixed that passed on the wrong input:** `close_gaps.py` (read a
09-07 report) and `check_mpn_consistency.py` (root only after the split);
`populate_schematic.py` now refuses the hierarchical root. `I-027`: BIAS is
tied to T- on every channel - datasheet check still to do (analog.com
blocked). Fab package re-exported 09:45. **All uncommitted.**

## Measured, not claimed

| Check | Result |
|---|---|
| `validate.ps1` (workstation, KiCad 10.0.6, 09:49) | **passed**: ERC 0/0; netlist **IDENTICAL** 201/162/645; **DRC 0 errors, 0 warnings, 0 unconnected, 0 parity** |
| `check_board.py` | **all 6 ok**; all 40 channel nets in `SensorSignal` |
| `check_mpn_consistency.py` (now inside `validate.ps1`) | 128 / 128 match (both sheets) |
| `build.py` from `05d6abd` (scratch) | reproduces the hierarchy: IDENTICAL, ERC 0/0, 3 min |
| Drill file | 0.20 mm x 6 (U14 only), every other hole >= 0.30 mm |
| `firmware/build.ps1` (workstation, 2026-09-26) | exit 0; 4 images, 3 suites pass; 8ch image 5592 B (17.1 %) |

Freerouting's own "violations" count is its plane-less model, never the verdict.
No IEC 61010 creepage analysis, SPICE, thermal, EMC or physical measurement.

## Next actions
1. **Owner:** order 4-layer (`I-025`); get the fab quote incl. 0.2 mm holes.
   10 BOM lines have no LCSC code (`I-051`, closed) - JLC global sourcing or hand-solder.
2. **Owner: commit** today's work (`I-062`, `I-045`, the gate fixes).
3. **Bench, when boards arrive:** K1 (`I-058`), isolation (`I-004`), timing (`I-013`), `I-003`.
4. `I-027`: MAX31856 datasheet into `docs/reference/datasheets/`, quote BIAS. `I-028` panel fuse; owner: `I-056`, `I-046`.

## Tooling, and the traps it sets

`Konnect` is the only KiCad MCP (`0013`); the cloud hook installs it (TOOLS.md). **`kicad-tool` clones a symbol to make a new one, so the clone inherits its MPN** (`I-054`); run `check_mpn_consistency.py` after any run that adds parts.

## Preserve for hardware work

**The layout pass needs a label-only base.** `build.py` starts from `05d6abd`
and refuses a schematic with wires, because its router only knows the wires it
drew. After a generator change, commit the generator's label-only output and
pass it as `--base`; never run the router over the wired sheet.
`populate_schematic.py --refresh-properties` moves symbols (`I-052`): re-run `build.py`.
Verify with `netlist_fingerprint.py`; never edit a baseline to pass (`I-058` did, on purpose).
