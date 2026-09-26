# Current state

**Read second, after `AGENTS.md`. Update before finishing. Hard limit: 60 lines.**

**Last updated:** 2026-09-26 (workstation)

## Last session

**REV A1 is routed, clean and packaged** - `production/8ch-reva1/` (gitignored):
Gerbers (11 layers), drill, IPC-D-356, CPL, BOM, `RELEASE.txt`, upload zip.
Board commit `2f1325b`; the silkscreen fix after it is uncommitted.
Decisions `0017` (U14 0.2 mm vias), `0018` (J3 keeps COM/NO/NC, moves to K1).
Generator fixes: R59/R60 at 270; MAX31856 GND pins get fixed vias; `route.py`
re-stitches after closing gaps; silkscreen placed by measured boxes, with the
dry-contact marking required and next to J3 (`generate_board.py --silk-only`).
Workstation KiCad now 10.0.6 = cloud. Closed today: `I-060/061/063/006/024/016/032/051`.

## Measured, not claimed

| Check | Result |
|---|---|
| `validate.ps1` (workstation, KiCad 10.0.6) | **passed**: ERC 0/0; netlist **IDENTICAL** 201/162/645; **DRC 0 errors, 0 warnings, 0 unconnected, 0 parity** |
| `check_board.py` | **all 6 ok** |
| Drill file | 0.20 mm x 6 (U14 only), every other hole >= 0.30 mm |
| `make -C firmware all test` (cloud, 2026-09-24) | exit 0; 4 images, 3 suites pass |

Freerouting's own "violations" count is its plane-less model, never the verdict.
No IEC 61010 creepage analysis, SPICE, thermal, EMC or physical measurement.

## Next actions
1. **Owner:** order 4-layer (`I-025`); get the fab quote incl. 0.2 mm holes.
   10 BOM lines have no LCSC code (`I-051`, closed) - JLC global sourcing or hand-solder.
2. **Split the schematic into A4 sheets** (`I-062`) - no re-route, no new Gerbers.
3. **Bench, when boards arrive:** K1 (`I-058`), isolation (`I-004`), timing (`I-013`), `I-003`.
4. `I-028` external panel fuse; ask the owner about `I-056`, `I-046`; `I-045` layout items.

## Tooling, and the traps it sets

`Konnect` is the only KiCad MCP (`0013`); the cloud hook installs it (TOOLS.md). **`kicad-tool` clones a symbol to make a new one, so the clone inherits its MPN** (`I-054`); run `check_mpn_consistency.py` after any run that adds parts.

## Preserve for hardware work

**The layout pass needs a label-only base.** `build.py` starts from `05d6abd`
and refuses a schematic with wires, because its router only knows the wires it
drew. After a generator change, commit the generator's label-only output and
pass it as `--base`; never run the router over the wired sheet.
`populate_schematic.py --refresh-properties` moves symbols (`I-052`): re-run `build.py`.
Verify with `netlist_fingerprint.py`; never edit a baseline to pass (`I-058` did, on purpose).
