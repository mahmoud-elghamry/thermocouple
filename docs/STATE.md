# Current state

**Read second, after `AGENTS.md`. Update before finishing. Hard limit: 60 lines.**

**Last updated:** 2026-09-28 (workstation)

## Last session

2026-09-27: pre-fabrication review (`I-065`..`I-069`, commit `cf69b03`).

**2026-09-28: REV A2** (`0022`), all five findings fixed. The board was
regenerated and re-routed from scratch:
`U10`/`U11` without the F suffix, plus `R61` 2k2 on U11's MISO (`I-065`);
`Q1` BSS131 240 V SOT-23 (`I-066`); `R53`/`R54` 100k/22k (`I-067`); `F1`
60 V 0.75 A 1812 PTC (`I-068`); D2 drawn unidirectional, D3 = M7 (`I-069`).
Schematic changes live in `sch_layout/reva2.py`, and `build.py` reproduces them.
Netlist contract is `netlist-baseline-reva2.json`; `BOARD_REV = "A2"`.
**Board state:** Freerouting left `C41.1` (+5V_CTRL) open, so **one via and one
track at (155.75, 42.9) were added by hand**, then `--record`. A regeneration
will reroute and must be re-checked for that pad. Arithmetic in
`CALCULATIONS.md` 4. Two-layer backup (`I-025`) is now a revision behind.

## Measured, not claimed

| Check | Result |
|---|---|
| `validate.ps1` (workstation, KiCad 10.0.6, 2026-09-28 01:07) | **passed**: ERC 0/0; netlist **IDENTICAL** 202/163/647; **DRC 0 errors, 0 warnings, 0 unconnected, 0 parity** (`production/8ch-reva2/validation-report`) |
| `check_board.py` | **all 6 ok** |
| `check_mpn_consistency.py` / `source_passives.py --check` | 129 / 129 match; 38 passive types, all with MPN |
| `build.py --in-place` (2026-09-28) | IDENTICAL against reva2, ERC 0/0 |
| `firmware/build.ps1` (workstation, 2026-09-28) | exit 0; 4 images, 3 suites pass; 8ch image 5592 B (17.1 %). No firmware change was needed |

Freerouting's own "violations" count is its plane-less model, never the verdict.
No IEC 61010 creepage analysis, SPICE, thermal, EMC or physical measurement.

## Next actions
1. **Owner: order REV A2** from `production/8ch-reva2/` (exported 2026-09-28 from
   `156ef2d`, `RELEASE.txt` + `thermocouple_8ch_reva2_gerbers.zip`); quote incl. 0.2 mm holes.
   Old packages are in `production/_OLD_DO_NOT_ORDER/`. Check LCSC stock first:
   ISO7760DWR ~109, ISO7761DWR ~366, PTC ~2 k.
2. 10 BOM lines have no LCSC code (`I-051`) - JLC global sourcing or hand-solder.
3. **Bench, when boards arrive:** ISP through J5 (`I-065`); D2 band (`I-069`);
   K1 (`I-058`); isolation (`I-004`); timing (`I-013`); `I-003`.
4. Owner: the panel's maximum ambient temperature (F1 holds up to 70 °C);
   the `0020` fuse part; `I-056`, `I-046`; `I-026` probes.

## Tooling, and the traps it sets

`Konnect` is the only KiCad MCP (`0013`); the cloud hook installs it (TOOLS.md). **`kicad-tool` clones a symbol to make a new one, so the clone inherits its MPN** (`I-054`); run `check_mpn_consistency.py` after any run that adds parts.

## Preserve for hardware work

**The layout pass needs a label-only base.** `build.py` starts from `05d6abd`
and refuses a schematic with wires, because its router only knows the wires it
drew. After a generator change, commit the generator's label-only output and
pass it as `--base`; never run the router over the wired sheet.
`populate_schematic.py --refresh-properties` moves symbols (`I-052`): re-run `build.py`.
Verify with `netlist_fingerprint.py`; never edit a baseline to pass (`I-058` did, on purpose).
