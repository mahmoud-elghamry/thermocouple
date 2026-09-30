# Current state

**Read second, after AGENTS.md; then read all of ISSUES.md (P0 first). Hard limit: 60 lines.**
**Last updated:** 2026-10-01 (workstation)

## Where we are

* **REV A2 module** (8 channels, `0022`/`0023`) is designed, and the gates pass.
  The order is **ON HOLD** for the four P0 rows in `ISSUES.md`:
  * I-075: U14 vias are 0.4 mm, not 0.3;
  * I-076: the buck layout is autorouted;
  * I-078: the package is not in the fab's format and 17 lines have no code;
  * I-079: the coil value in the RELEASE text was wrong.
* **System = 24 thermocouples** (owner 2026-09-29). **Direction agreed 2026-10-01**
  (`0024`): 3 identical autonomous REV A2 modules, each with its own relay.
  * **Open owner question:** one machine (contacts in series) or separate groups
    (one contact each). That is panel wiring only; the board is the same.
  * A master later (display/config) is mainly firmware over the on-board
    RS-485, plus a master device. It is never in the trip path (I-086).
* **2026-09-29 review** (another agent): valid on I-073, I-075, I-076, I-079 and
  I-085. Overstated, now marked with "Review weight" and moved to P3: I-077,
  I-080, I-081 (accepted limit), I-086. Housekeeping: I-070..072, I-082..084.
* **ISSUES.md restructured** (`0025`): priority index, short rows, closed rows in
  `ISSUES-closed.md`; 72 KB → 11 KB. Review original: `production/review-20260929/`.

## Measured, not claimed

| Check | Result |
|---|---|
| `validate.ps1` (2026-09-28 01:43, KiCad 10.0.6) | ERC 0/0; netlist IDENTICAL 202/163/647; DRC 0/0/0/0 — **but DRC does not catch I-075** |
| review `run_all.ps1` snapshot (2026-09-29) | same numbers, source hashes unchanged |
| U14 vias, read from the board (2026-09-30) | 6 vias, **0.4 mm drill / 0.6 mm pad**, GND_CTRL, x 171.4/172.6, y 108.8/110/111.2 |
| `check_board.py` / MPN / passives | 6 ok; 129/129; 38 types with MPN |
| `firmware/build.ps1` (2026-09-28) | exit 0; 4 images; 3 suites pass |
| `tests/reproductions/` (review) | I-073: 7 assertions fail; I-074: defect confirmed. Not in the normal gate yet |

No surge, EMC, thermal, isolation, ISP or contact-timing test; no SPICE.

## Next actions (in order; confirm each step with the owner before doing it)

1. **P0 hardware:** hand-place the U14 power stage (I-076); fix the via-drill
   override (I-075); regenerate, validate, and check the `.drl` itself.
2. **P0 package (I-078):** owner picks the fab and the THT split; fill the 17 codes;
   export BOM/CPL in the fab's format; review the fab's matching and rotation
   screenshots with the owner; re-export and fix RELEASE (I-079).
3. **P1 firmware:** I-073 fix + regression, I-074 policy, I-082, I-070.
4. Owner: machine grouping (I-085), panel max ambient (F1 is fine to 70 °C),
   the exact `0020` fuse.
5. Bench (P2) when boards arrive.

## Preserve for hardware work

* Konnect is the only KiCad MCP (`0013`); run the provenance check before any board write.
* `route.py` does not `--record`: run it after every route.
* kicad-tool clones inherit their MPN (I-054).
* `build.py` starts from `05d6abd` + `sch_layout/reva2.py`. Never route the wired sheet.
* `kicad-tool pcb sync` needs `KICAD10_FOOTPRINT_DIR`. Freerouting is deterministic
  for a given input.
* **Check the exported drill file, not only DRC** (I-075).
* Never change a baseline to make a gate pass.
