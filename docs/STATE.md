# Current state

**Read second, after `AGENTS.md`. Update before finishing. Hard limit: 60 lines.**

**Last updated:** 2026-09-26 (workstation)

## Last session

**Schematic now six A4 files** (`0021`, amends `0019`): root (index of blocks),
`power`, `mcu`, `isolation`, `relay_rs485`, `channel` (TC1-TC8). 56 sheet-internal
nets gained the sheet path (`/POWER/+24V_RAW`); `apply_rules.py` patterns and
`board/units.bare()` follow. **All 162 board nets keep their netclass** (compared
before/after). Board nets renamed in place, copper unchanged; package + PDFs
(`views/schematic.pdf` 13 pages, `schematic_short.pdf` root + 4 + TC1) re-exported
11:02. **`I-028` (a) settled** (`0020`): external 1 A time-delay DC fuse, >= 80 V DC,
>= 10 kA, at the battery end; inrush in `CALCULATIONS.md` 1.9. New low `I-064`:
board overlaps its PCB-editor page frame (cosmetic). Earlier today: `I-062`,
`I-045`, `I-027`, REV A0 -> A1 silkscreen; committed `08c8d86`, `d9845ae`.

## Measured, not claimed

| Check | Result |
|---|---|
| `validate.ps1` (workstation, KiCad 10.0.6, 10:59) | **passed**: ERC 0/0; netlist **IDENTICAL** 201/162/645; **DRC 0 errors, 0 warnings, 0 unconnected, 0 parity** |
| `check_board.py` | **all 6 ok**; 162/162 nets keep their netclass across the 0021 rename |
| `check_mpn_consistency.py` (now inside `validate.ps1`) | 128 / 128 match (all sheets) |
| `build.py` from `05d6abd` (scratch, 11:05) | reproduces all six sheets (equal apart from UUIDs): IDENTICAL, ERC 0/0 |
| Drill file | 0.20 mm x 6 (U14 only), every other hole >= 0.30 mm |
| `firmware/build.ps1` (workstation, 2026-09-26) | exit 0; 4 images, 3 suites pass; 8ch image 5592 B (17.1 %) |

Freerouting's own "violations" count is its plane-less model, never the verdict.
No IEC 61010 creepage analysis, SPICE, thermal, EMC or physical measurement.

## Next actions
1. **Owner:** order 4-layer (`I-025`); get the fab quote incl. 0.2 mm holes.
   10 BOM lines have no LCSC code (`I-051`, closed) - JLC global sourcing or hand-solder.
2. **Owner: commit** the `0021` split and the `0020` fuse spec.
3. **Bench, when boards arrive:** K1 (`I-058`), isolation (`I-004`), timing (`I-013`), `I-003`.
4. Choose the `0020` fuse part and put it on the panel drawing; owner: `I-056`, `I-046`; `I-026` buy ungrounded probes (board ready).

## Tooling, and the traps it sets

`Konnect` is the only KiCad MCP (`0013`); the cloud hook installs it (TOOLS.md). **`kicad-tool` clones a symbol to make a new one, so the clone inherits its MPN** (`I-054`); run `check_mpn_consistency.py` after any run that adds parts.

## Preserve for hardware work

**The layout pass needs a label-only base.** `build.py` starts from `05d6abd`
and refuses a schematic with wires, because its router only knows the wires it
drew. After a generator change, commit the generator's label-only output and
pass it as `--base`; never run the router over the wired sheet.
`populate_schematic.py --refresh-properties` moves symbols (`I-052`): re-run `build.py`.
Verify with `netlist_fingerprint.py`; never edit a baseline to pass (`I-058` did, on purpose).
