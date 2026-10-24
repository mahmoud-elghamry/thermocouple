# 40-ch board REV A0 - state

Plan: `docs/decisions/0039` (accepted 2026-10-14; checkpoints delegated to Claude, picks P1-P5 there).
5 banks (40 thermocouples, all fitted) + an RTD bank (one AD7124-8: three 3-wire PT100 + an on-board
150R 0.1 % check resistor, `0039` P5), chip selects through a 74HC154 on the island (5 MCU pins), gated
TMP126 SIO driver (P2).

## Done (2026-10-14)

* Feasibility: `CALCULATIONS` sec. 10 (Sol) + 10.11 PT100 (Claude, Astra reviewed twice) + 10.12 cost
  estimate (~$1,370 for 10 boards ex shipping, UNVERIFIED until a real quote).
* Schematic from `hardware/family/gen` config "40": ERC 0/0, netlist 0 mismatches, 108 BOM lines,
  707 fitted parts (SYNC tied, `0039` P8). Astra reviewed the generated netlist: 225/225 pin assignments checked, no collision.
* Board `thermo40.kicad_pcb`, floor plan **v2 250 x 145 mm**: every part shared with the 24-ch sits where it
  sits on the finished 24-ch board (`gen/pos24.json`, snapshot of `hardware/24ch/thermo24.kicad_pcb`); bank C
  (3xx, bottom) = bank B + 74 mm, bank D (8xx, left) = 24-ch bank C, bank E = bank D turned 180 degrees, RTD bank
  top right with its decoupling at its pins. 728/728 placed, 0 overlaps, no net in two domains, padcheck 0,
  fanout 481 vias (board-size bug fixed: it used 169 x 144), AVDD vias at pin 26 by hand, **pincaps 0**, DRC 0
  violations before routing. v1 (24-ch place.py code) stopped at pass 9 - its decoupling was the 24-ch's
  pre-repair layout.

## Routed and released (2026-10-14 to 10-17)

* Routing: `gen/copy24.py` copied the finished 24-ch copper under the placement transforms (a net only when
  every pad lands on one 40-ch net within 0.02 mm), `delviol.py` dropped 16 violating items -> 271 unconnected
  (a board copy needs its own `.kicad_pro`/`.kicad_dru` beside it). Freerouting on the copy failed; `maze.py`
  -> 60 (`output/mz-pass1`).
* The 60 by Sol (gpt-6.1-sol) as route lists computed from the board text (no KiCad), applied with
  `finish.py --board 40 --pcb output/mz/thermo40.kicad_pcb apply output/sol-routesN.txt`: 60 -> 36 -> 26 -> 11
  -> 8 -> 5 -> 3, DRC 0 violations each time (`output/mz-sol1..6`). The last 3 (U1001 RTD pins): no 0.15 mm
  tracks (0.20 kept); **four passives moved** (`sol-moves9.txt`: C1096, C1091, C1095, C1097) -> **0 / 0**.
  Antigravity, GLM 5.3 and DeepSeek 4.1 Flash tried the 26-connection stage: 0, 0 and 2 routed.
* Finishing: `finish.py dangling` (196 stubs), I-129 fix in `gen/rules.py`, outer pours F/B (left out for
  routing; added with `rules.add_zone` only), `vbias_pour.py`, `fiducials.py`, `silk.py` (PT100 labels in the
  terminal body: profile key `terminal_y_at`); DRC 0/0 after each (backups `output/clean, pours, vbias, silk`).
* Release `40ch-reva0-20261017-000812-3e3a61` (now `_OLD_DO_NOT_ORDER`): **Astra review: send after fixes** - PT100
  area poor (RTD2 SP/SN 35 vs 125 mm, R1092 not Kelvin, C1096 loop 5.7 mm), vias in small IC pads
  (U410.14/21, U501.41, U802.6, U902.6), island holes need nylon hardware (I-130, accessories fixed).

## PT100 re-layout and re-release (2026-10-19)

* Sol round 10 (`output/sol-moves10.txt`, 33 passives moved; `sol-routes10.txt`, then `sol-routes10fix.txt`:
  stale pad-edge fragments KiCad kept, one shorted C1092; `sol-routes10fix2.txt`: AVDD/IOVDD plane vias 0.9 mm).
  RTD1-4 SP/SN 9.4-11.9 mm, mismatch <= 1.4 mm, 3 vias each; R1092 Kelvin (REFIN tracks own, shared run 0);
  terminal leads split at the pads; C1096 loop 1.77 mm; vias in small IC pads 0; digital/sense crossings 0.
  Then `finish.py dangling` (15 removed), `silk.py`. Backup before the round: `output/pre-r10/`.
* Release `40ch-reva0-20261019-024508-4774af` (archived): Astra re-review **after fixes** - PT100 items FIXED,
  but 7 overlapping drill-hole pairs (pre-existing since the copy; KiCad severity warning, the 24-ch has none)
  and via holes cutting small SMD lands. Sol round 11 (`sol-routes11.txt`): hole pairs < 0.25 mm 19 -> 0, via
  hole to small SMD land < 0.10 mm 61 -> 0 (own pcbnew check), SAC/SBC partly shortened (RTD1 48 -> 37 mm,
  adjacent-layer digital crossings 25 -> 17), SP/SN 9.8-14.1 mm, mismatch <= 1.9 mm; Kelvin/decoupling kept.
* **Astra final review 2026-10-24: send for quotation as is** (DRC 0/0/0 fresh, holes/lands FIXED, 51/51 hashes,
  1212/1212 fill reached). Left as SHOULD-FIX: RTD3/RTD4 SAC/SBC 17 adjacent-layer digital crossings (RTD1 now 5
  vias/leg), 0.8 mm RTD4_SAC stub at 216.9,38.3. Review: `output/astra-final/REVIEW.md`.
* **Release candidate `production/40ch-reva0-20261024-113204-9bed30/`** (board as 040422, archived; hole rules = errors, ORDER-NOTES smallest features).

## Open

* TL431 clamp tolerance corner ~3.61 V (`CALCULATIONS` 9.2) - check AD7124 AVDD absolute maximum.
* Shared DOUT over ~300 mm of board: measure edges at the bench; R1092 Kelvin done 2026-10-19.
