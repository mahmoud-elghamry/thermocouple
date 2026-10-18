# 8-channel board - state

**Hard limit: 60 lines.** Index of all products: `docs/STATE.md`. Read `docs/ISSUES.md` in full too.
**Last updated:** 2026-10-14.

## Where it stands

* `hardware/8ch/` is **REV A2** (MAX31856 front end): ERC/DRC 0/0, netlist identical, firmware 4 builds /
  3 suites pass (2026-10-09 snapshot `production/validation-20261009-043553-906505`). Never ordered;
  no physical qualification or SPICE.
* Direction (`0037` D1): the company's 8-channel option is a **new board derived from the 24-ch one**
  (one bank: one AD7124-8, TMP126 pair, same isolation, supply, relays, LCD and buttons). REV A2 becomes
  reference. Not started.

## Next (for the 8-ch work)

1. Owner answers 2026-10-14: derive from the 24-ch (1 bank, AD7124-8; MAX31856 not kept); keep trip +
   alarm relays, RS-485, the five buttons + panel header, LCD header with standoffs (or a cable to the
   door) as on the 24-ch; **4 layers first**; a 2-layer version that a fab in Egypt can make is studied
   after (the old `_old/8ch-2layer` failed with 8 MAX31856: 14 unrouted +3V3_SENS, no plane, `0028`).
   Board size from a to-scale floor plan (`0031` D10), shown to the owner before any board write.
2. Plan where the new board lives (new folder; REV A2 moved to `_old/` only together with the scripts
   and CI that use it: `run_all.ps1`, `validate.ps1`, `board_provenance.py`).

## Preserve (REV A2 tools)

* Konnect is the only KiCad MCP (`0013`); `board_provenance.py --check` before any board write,
  `--record` after. `run_all.ps1 -Regenerate` re-routes the whole board.
* `route.py` re-drills vias to a 0.15 ring after the SES import (I-075): check the drill file, not only DRC.
* `build.py` starts from `05d6abd` + `sch_layout/reva2.py`. kicad-tool clones inherit their MPN (I-054).
* `kicad-tool pcb sync` needs `KICAD10_FOOTPRINT_DIR`. Freerouting is deterministic for a given input.
