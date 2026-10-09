# Current state

**Read second, after AGENTS.md; then read all of ISSUES.md (P0 first). Hard limit: 60 lines.**
**Last updated:** 2026-10-09 (workstation, `0031`-`0033`).

## Where we are

* REV A2 passes every gate (below), FW 0.2.1; **not ordered**: 250 x 140 mm, 81 %
  empty (I-090). Shrink, keep 4 layers (`0028`). `production/8ch-reva2/` ON HOLD;
  next order is **REV A3**. Superseded files are in `_old/` (see its README).

## 2026-10-08: ONE 24-channel board (`0031`) — read it before any work

* `0031` supersedes most of `0030`; still valid there: D2 comms never in trip path, D5, D8.
* Front end **3x AD7124-8** on one isolated island in parallel; 20 M TC- bias, mid-rail reference
  wire, CJ sensors at the terminals, open-TC check one channel per scan (~4 s each).
* 20x4 LCD on standoffs + 5 buttons on the board; trip relay + alarm relay
  (30 VDC / 1 A signal); isolated RS-485/Modbus fitted (ADM2587E); 20x4 LCD bought locally; shield at panel entry (48 TC
  terminals); plate mounting; **all parts from one source** (NORI, I-103).
* `0032` = circuit + parts after Codex/Opus reviews (power `CALCULATIONS` 7, front end, floor plan).

**2026-10-09: 24-ch board, `hardware/24ch/` (README there), decisions `0032`-`0033`.**
Schematic 467 symbols, ERC 0/0, 12 pages A3/A4; 2N7002 -> C8545 and C604 -> C28260 (basic parts) in the
schematic, board not yet `pcb sync`ed (properties only). Board 170 x 145 kept (`0033` D1).
**Board now (`thermo24.kicad_pcb`, = `output/finish12-pre-gui.kicad_pcb`): KiCad DRC 0 violations, 2 unconnected:**
TC21_NA (U301 pad 15 boxed in by the TC21_PA track from pad 14 - re-route the pair) and CS_CJ5_ISO
(long island run, via (82.0,104.6) -> (37.9,33.7)). Exact geometry + plan: `production/review-20261008/codex-route-brief.md`.
Two KiCad windows may be open with NO edits (close, don't save); `output/work*.kicad_pcb` = scratch.
NOT yet applied to the board: `rules.py` now writes NORI pad-to-track 0.2 mm + relay_area/b0505_area/spare-pin
rules - run `rules.py` (full, with outer pours) after the last 2 routes, then `finish.py drc`.
Fab NORI (`0033` D2, I-106); parts $104.9/board, 52 extended codes (`gen/cost.py`). Not committed.

## Start here - next steps

1. **I-107:** route the last 2 by hand coordinates (`gen/finish.py add`, or Codex), never `place.py`/`route24.py`
   on the board. Then `rules.py` (full pours, NORI rule), DRC 0, EP vias out of the paste windows (I-110),
   `pcb sync` (part codes), silkscreen for installers (I-108), `gen/fab.py`.
2. Independent review of the routed board (Codex/Opus), then files to NORI; owner asks NORI I-106 (1,2,5).
3. **I-108:** LCD drawing -> buttons + panel cut-out. Owner: engine-ground DC/AC at cranking (I-101).
4. Firmware for the 24-ch board after hardware (I-100, I-104, I-097).

## Measured, not claimed (REV A2, before the shrink)

| Check | Result |
|---|---|
| Workstation, 2026-10-09 | 8ch snapshot `production/validation-20261009-043553-906505`: ERC/DRC 0/0, netlist identical; firmware 4 builds / 3 suites PASS. Separate 24ch report above. |
| `validate.ps1` 2026-10-06 22:09, after the cleanup | ERC 0/0; netlist IDENTICAL 202/163/647; 129/129 MPN match; DRC 0/0/0/0 (`production/validation-20261006-220958-ac80be`) |
| `firmware/build.ps1` 2026-10-06, after the cleanup | 3 suites PASS; 4 images built (8ch FW 0.2.1, 5918 B on 2026-10-01) |
| Cloud gates, 2026-10-07 | `make all test`: 4 targets/3 suites pass; ERC/DRC 0/0; netlist 202/163/647 identical; 129 MPN match; source unchanged (`production/validation-20261007-080427-e91cea`) |
| Board area (pcbnew, 2026-10-06) | 250.1 x 140.1 mm; 193 parts, courtyards 67 cm² = 19 % |

No physical qualification/SPICE. Git works; GitHub API HTTP 403.

## Preserve for hardware work
* Konnect is the only KiCad MCP (`0013`); run `board_provenance.py --check` before any board write, `--record` after.
* `route.py` re-drills vias to a 0.15 ring after the SES import (I-075). Check the exported drill file, not only DRC.
* `build.py` starts from `05d6abd` + `sch_layout/reva2.py`. kicad-tool clones inherit their MPN (I-054).
* `kicad-tool pcb sync` needs `KICAD10_FOOTPRINT_DIR`. Freerouting is deterministic for a given input.
* Never change a baseline to make a gate pass. Never edit `hardware/single-channel/` or anything in `_old/`.
