# Current state

**Read second, after AGENTS.md; then read all of ISSUES.md (P0 first). Hard limit: 60 lines.**
**Last updated:** 2026-10-01 (workstation, after P0 hardware)

## Where we are

* **2026-10-01, P0 hardware done** (commit pending owner OK):
  * I-075 fixed at the cause: the SES import re-drilled 41 vias to 0.4 mm.
    `route.py` now restores a 0.15 mm ring, and DRC enforces it.
  * I-076 layout done (`0026`): the U14 stage is placed and drawn by
    `board/powerstage.py` and protected from the router. C63 is 3.5 mm from VIN,
    and SW is one 1.0 mm track.
  * Firmware I-073 (unsafe ACK) fixed with 5 regression tests; I-070 and I-071
    done. This was a sub-agent in a worktree; I reviewed the diff and re-ran
    `build.ps1` in the main tree.
* Committed `6f6c22d`. After it (uncommitted): I-082 and I-088 fixed (Sonnet sub-agent,
  reviewed and run here); I-078 has 5 LCSC codes added to the schematic (build IDENTICAL, ERC 0/0).
* **Still P0:** I-078 (fab not chosen yet; technician kit list; fab-format BOM/CPL) and
  I-079 (RELEASE text). Decided `0027`: 3 substitutes, the technician fits THT, 3 boards. The package in
  `production/8ch-reva2/` is **stale and ON HOLD**; re-export after I-078.
* **System = 24 thermocouples:** 3 autonomous REV A2 modules (`0024`). The owner
  still has to say: one machine (contacts in series) or separate groups.
* ISSUES.md is a priority index (`0025`); closed rows are in `ISSUES-closed.md`.

## Measured, not claimed

| Check | Result |
|---|---|
| `validate.ps1` (2026-10-01 00:44, KiCad 10.0.6) | ERC 0/0; netlist IDENTICAL 202/163/647; **DRC 0/0/0/0 with min ring 0.15** (re-run 01:25 after the value sync: `production/validation-20261001-012504-9fa3a2`) |
| `check_board.py` | all 6 ok |
| vias, from the board and the exported `.drl` | 112 x 0.3, 6 x 0.35, 47 x 0.4, 2 x 0.5 drill; min ring 0.15; U14: six 0.3 mm |
| power-stage copper (from board) | VIN-C63 3.53 mm, VIN-C54 7.03, SW-L1 5.98 at 1.0 mm, BST-C62 3.02 |
| `firmware/build.ps1` (2026-10-01, main tree, after I-088) | exit 0; 4 images (8ch 5840 B); 3 suites PASS |
| `program.ps1 -Image legacy_1ch_max31856.hex` | exit 2, refused, avrdude not called (I-082) |

No surge, EMC, thermal, isolation, ISP or contact-timing test; no SPICE.

## Next actions (confirm each step with the owner first)

1. **I-078:** the owner picks the fab and the THT split. I fill the 17 codes, export
   BOM/CPL in the fab's format, and review the fab's screenshots with the owner.
   Then re-export the package and fix RELEASE (I-079).
2. P1 firmware: I-074 startup policy (owner: latch-and-show on boot, or wait for the first valid sweep).
   Owner: is "REVA2" on the boot screen OK, and should `FW 0.2.0` be bumped?
3. Owner: machine grouping (I-085), panel max ambient, the `0020` fuse part.
4. Bench (P2) when boards arrive.

## Preserve for hardware work

* Konnect is the only KiCad MCP (`0013`); run the provenance check before any board write.
* `route.py` does not `--record`: run it after every route. It re-drills vias to a 0.15 ring after the SES import (I-075).
* kicad-tool clones inherit their MPN (I-054).
* `build.py` starts from `05d6abd` + `sch_layout/reva2.py`. Never route the wired sheet.
* `kicad-tool pcb sync` needs `KICAD10_FOOTPRINT_DIR`. Freerouting is deterministic
  for a given input.
* **Check the exported drill file, not only DRC** (I-075).
* Never change a baseline to make a gate pass.
