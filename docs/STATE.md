# Current state

**Read second, after AGENTS.md; then read all of ISSUES.md (P0 first). Hard limit: 60 lines.**
**Last updated:** 2026-10-09 (workstation, `0031`-`0034`).

## Where we are

* REV A2 (8ch, reference) passes every gate (below), FW 0.2.1; never ordered. Next order is the
  24-ch **REV A3**. Superseded files are in `_old/` (see its README).

## 2026-10-08: ONE 24-channel board (`0031`) — read it before any work

* `0031` supersedes most of `0030`; still valid there: D2 comms never in trip path, D5, D8.
* Front end **3x AD7124-8** on one isolated island in parallel; 20 M TC- bias, mid-rail reference
  wire, CJ sensors at the terminals, open-TC check one channel per scan (~4 s each).
* 20x4 LCD (bought locally) + 5 buttons (+ panel header, `0034` D2); trip + alarm relay (30 VDC / 1 A signal);
  isolated RS-485/Modbus (ADM2587E); shield at panel entry; **all parts from one source** (NORI, I-103).
* `0032` = circuit + parts after Codex/Opus reviews (power `CALCULATIONS` 7, front end, floor plan).

**2026-10-09: 24-ch board, `hardware/24ch/` (README there), decisions `0032`-`0033`.**
Schematic 467 symbols, ERC 0/0, 12 pages A3/A4. Board 170 x 145 (`0033` D1). Fab NORI (I-106); parts ~$105 (`gen/cost.py`).
**Board ROUTED + silkscreen; fab set `production/24ch-reva3-20261009/` (gen/fab.py, 11:1x): its `drc-report.rpt`
= 0 DRC violations, 0 unconnected pads, 0 footprint errors (schematic parity). Board = `output/finish23-silk.kicad_pcb` + saved fills.**
Done today: last 2 routes by hand/maze (TC21 pair: old PA loop is now NA, PA + 2 CS_CJ5_ISO pieces on In2.Cu,
`0033` D4), `rules.py` full (outer pours, NORI pad-to-track 0.2 on pads, relay_area only for contacts),
65 tracks nudged to 0.2 (`finish.py nori`) + 5 by hand, 33 router stubs deleted (`finish.py dangling`),
`pcb sync` (C8545/C28260), EP vias off the paste (I-110), installer silkscreen (`gen/silk.py`, 0 silk warnings).
BOM 93 lines, CPL 441 parts; only the 5 buttons lack an LCSC code (I-108).

## Start here - next steps

**2026-10-09 Astra review** (`docs/reference/review-20261009-astra.md`) -> `0034` + ISSUES I-111..I-120.
The fab set above is NOT orderable until these board repairs are done (`0034` D3, local only):
1. **I-111** move decoupling/bootstrap/input caps beside their pins (LM5164 first, then ISO7761,
   AD7124, MCU), re-route those nets; measure pin-to-cap distances; DRC 0/0/0.
2. **I-112** three fiducials; **I-113** silk RUN PERMIT C-NO, CHASSIS; **0034 D2** button header
   (schematic `c_mcu.py` + `pcb sync`) and tact-switch LCSC codes; **I-114** CJ sensors closer if room.
3. **I-115** gates (`build.py` exit codes, unique release folder + hashes), **I-116** accessory BOM,
   then `gen/fab.py`. NORI order spec in I-106 (ENIG, tented vias, coating question).
4. Firmware after hardware: I-118 heartbeat, I-119 port list, I-104, I-100; open TC trips (`0034` D1).
5. Bench/field tests I-120; engine-ground measurement at the first engine test (I-101).

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
