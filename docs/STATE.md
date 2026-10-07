# Current state

**Read second, after AGENTS.md; then read all of ISSUES.md (P0 first). Hard limit: 60 lines.**
**Last updated:** 2026-10-07 (cloud handoff, `codex/operator-requirements-20261007`).

## Where we are

* **REV A2 design is complete and passes every gate** (numbers below), firmware
  FW 0.2.1 (boot waits for ACK, I-074). Last code commit `7df6798`.
* **But it is NOT going to be ordered as is.** On 2026-10-06 an outside engineer
  pointed out the board is 250 x 140 mm with 81 % empty area (I-090). It was
  inherited from the first plan and never justified. Decision **`0028`**: shrink
  before ordering, keep 4 layers. JLCPCB, 5 pcs, 4 layers: $46.60 now, $34.90 at
  160 x 100, **$8.00 at 100 x 100**. Two layers rejected (`0028`, option C).
* Owner: **3 autonomous modules, series contacts, per-channel setpoints, manual ACK**
  (`0024`/`0029`). HMI delegated to design team; 24 V engine battery (`0016`).
  Parts may change with verified suitability/stock; NORI likely fab (`0028`).
* `production/8ch-reva2/` is **ON HOLD** (stale). The next order is **REV A3**.
* Cleanup 2026-10-06: superseded files moved to **`_old/`** (see its README):
  the 2-layer backup, `populate_schematic.py`, `init_board.py`, A0/A1 baselines,
  old Arabic docs, a REV A0 `BOM.csv`, old validation snapshots; local ignored archive.

## Start here — next steps (recorded answers are not pending questions)

1. **Design work:** I-092 dry-contact voltage/current envelope (A2 low-voltage only;
   "line" is unqualified); I-091 select LCD/buttons/mounting; I-093 cable/termination;
   actual probe model/grounding and mapping (I-026/I-085). Operator sets temperatures.
   I-100: plan per-channel UI/protection/EEPROM; currently one shared module limit.
   I-094 RS-485 form; I-095 compatible stocked parts; delivered NORI/import quote,
   assembly, exact LCD and `0020` fuse. I-089 ACK confirmation is closed.
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
| Cloud gates, 2026-10-07 | `make all test`: 4 targets/3 suites pass; ERC/DRC 0/0; netlist 202/163/647 identical; 129 MPN match; source unchanged (`production/validation-20261007-080427-e91cea`) |
| Board area (pcbnew, 2026-10-06) | 250.1 x 140.1 mm; 193 parts, courtyards 67 cm² = 19 % |

No physical qualification/SPICE; cloud: `source /workspace/.thermo-tools/activate.sh` (draft saved). Git works; GitHub API HTTP 403.

## Preserve for hardware work

* Konnect is the only KiCad MCP (`0013`); run `board_provenance.py --check` before any board write, `--record` after.
* `route.py` re-drills vias to a 0.15 ring after the SES import (I-075). Check the exported drill file, not only DRC.
* `build.py` starts from `05d6abd` + `sch_layout/reva2.py`. kicad-tool clones inherit their MPN (I-054).
* `kicad-tool pcb sync` needs `KICAD10_FOOTPRINT_DIR`. Freerouting is deterministic for a given input.
* Never change a baseline to make a gate pass. Never edit `hardware/single-channel/` or anything in `_old/`.
