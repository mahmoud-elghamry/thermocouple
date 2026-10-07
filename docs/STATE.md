# Current state

**Read second, after AGENTS.md; then read all of ISSUES.md (P0 first). Hard limit: 60 lines.**
**Last updated:** 2026-10-08 (workstation, `0030`).

## Where we are

* REV A2 passes every gate (below), FW 0.2.1; **not ordered**: 250 x 140 mm, 81 %
  empty (I-090). Shrink, keep 4 layers (`0028`). `production/8ch-reva2/` ON HOLD;
  next order is **REV A3**. Superseded files are in `_old/` (see its README).

## 2026-10-08: plan agreed (`0030`) — read it before any work

* 3 identical 8-ch modules **stacked**, each trips alone, contacts in series; one
  display/keypad on the top module (master by jumper, one firmware image); ACK =
  one button, 3 separate contacts; non-isolated RS-485 (one panel, one battery).
* Contact: **30 VDC / 1 A max, signal only**; gold-contact signal relay.
* Probes made to order, junction type **unknown/mixed**: per-channel BIAS
  footprint (0 Ω default) + one module reference to the engine (I-101, blocker).
* Panel fuse must be re-sized for 3 modules (I-102).
* **Work split:** W1 Claude workstation = only hardware writer (floor plan first,
  shown to owner); W2 Codex = calculations/docs + core firmware; W3 cloud =
  RS-485/master display in NEW files on `claude/*`, PR; owner merges.

## Start here — next steps

1. **W2 Codex (now):** I-102 fuse, I-096 power budget (normal + master module),
   F1/L1 vs LM5164 limit; then firmware I-100 (8 limits, EEPROM) and I-097 timing.
2. **W1 (now):** to-scale 100 x 100 floor plan (`0030` D7) shown to the owner
   **before** any board write; part picks I-092 relay, I-094 transceiver, I-095.
3. **W3 cloud:** RS-485 protocol + master display, new files only (`0030`).
4. Shrink pass: schematic → `build.py` → baseline only for intended diffs →
   placement → route → all gates → `BOARD_REV` "A3", FW "THERMO-8CH REVA3".
5. I-078 fab files and owner preview; then the bench (P2), incl. I-101.

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
