# Current state

**Read second, after AGENTS.md; then read all of ISSUES.md (P0 first). Hard limit: 60 lines.**
**Last updated:** 2026-10-06 (workstation). A new conversation starts at "Start here".

## Where we are

* **REV A2 design is complete and passes every gate** (numbers below), firmware
  FW 0.2.1 (boot waits for ACK, I-074). Last code commit `7df6798`.
* **But it is NOT going to be ordered as is.** On 2026-10-06 an outside engineer
  pointed out the board is 250 x 140 mm with 81 % empty area (I-090). It was
  inherited from the first plan and never justified. Decision **`0028`**: shrink
  before ordering, keep 4 layers. JLCPCB, 5 pcs, 4 layers: $46.60 now, $34.90 at
  160 x 100, **$8.00 at 100 x 100**. Two layers rejected (`0028`, option C).
* An audit of other inherited choices (2026-10-06) produced **I-091..I-099**.
  Five of them are owner questions that decide the new board's edge and area.
* `production/8ch-reva2/` is **ON HOLD** (stale). The next order is **REV A3**.
* Cleanup 2026-10-06: superseded files moved to **`_old/`** (see its README):
  the 2-layer backup, `populate_schematic.py`, `init_board.py`, A0/A1 baselines,
  old Arabic docs, a REV A0 `BOM.csv`, old validation snapshots. Deleting was
  blocked by the permission policy, so they were moved instead. `_old/` is now
  ignored by Git and retained only as a local archive.

## Start here — next steps in order (confirm each with the owner)

1. **Owner answers** (none needs the agent first):
   I-091 where the LCD/buttons go · I-092 what K1's contact drives ·
   I-093 cable shield and where it ends · I-094 RS-485: isolated / plain / DNP ·
   I-095 accept the part changes (TQFP MCU, 2x8 header, drop J6/C51/R17-R24).
   Also still open: I-089 (reset while running waits for ACK; recommended yes),
   I-085 grouping, panel max ambient, the `0020` panel fuse, the LCD model.
2. **Agent, no owner input needed:** I-096 (re-derive the 5 V budget, recheck
   F1/L1); I-097 firmware timing (scan 2 ticks, WDT 500 ms, one trip budget).
3. Choose A (~160 x 100) or B (100 x 100) per `0028`. The agent draws the floor
   plan and shows the owner **before** any board write.
4. Shrink pass: schematic changes (if any) → `build.py` → new baseline only for
   intended diffs → placement/config → route → all gates → `BOARD_REV` "A3",
   firmware `APP_TARGET_BOARD` "THERMO-8CH REVA3".
5. Then I-078: fab choice, fab-format BOM/CPL (SMD only), review the fab
   preview with the owner, re-export the package, RELEASE text (I-079).
   Order U12 from DigiKey early. Kit list: `kit_list.py`.
6. Bench (P2) when boards arrive.

## Measured, not claimed (REV A2, before the shrink)

| Check | Result |
|---|---|
| `validate.ps1` 2026-10-06 22:09, after the cleanup | ERC 0/0; netlist IDENTICAL 202/163/647; 129/129 MPN match; DRC 0/0/0/0 (`production/validation-20261006-220958-ac80be`) |
| `firmware/build.ps1` 2026-10-06, after the cleanup | 3 suites PASS; 4 images built (8ch FW 0.2.1, 5918 B on 2026-10-01) |
| Board area (pcbnew, 2026-10-06) | 250.1 x 140.1 mm; 193 parts, courtyards 67 cm² = 19 % |

No surge, EMC, thermal, isolation, ISP or contact-timing test; no SPICE.

## Preserve for hardware work

* Konnect is the only KiCad MCP (`0013`); run `board_provenance.py --check` before any board write, `--record` after.
* `route.py` re-drills vias to a 0.15 ring after the SES import (I-075). Check the exported drill file, not only DRC.
* `build.py` starts from `05d6abd` + `sch_layout/reva2.py`. kicad-tool clones inherit their MPN (I-054).
* `kicad-tool pcb sync` needs `KICAD10_FOOTPRINT_DIR`. Freerouting is deterministic for a given input.
* Never change a baseline to make a gate pass. Never edit `hardware/single-channel/` or anything in `_old/`.
