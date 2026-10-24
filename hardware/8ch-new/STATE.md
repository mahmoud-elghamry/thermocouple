# 8-ch board REV B0 - state

Plan: `docs/decisions/0039` (accepted 2026-10-14; checkpoints delegated to Claude while the owner is away,
picks P1-P10 in 0039). One bank of the 24-ch design (1x AD7124-8, 2x TMP126), direct chip selects,
2x CA-IS3761HW, gated TMP126 SIO driver (P2), SYNC tied high (P8); power, relays, RS-485, MCU, LCD header,
buttons and panel-button header as the 24-ch. 4 layers first; 2-layer / local-fab study after (step L).

## Done (2026-10-14)

* Schematic from `hardware/family/gen` config "8": ERC 0/0, netlist 0 mismatches, 92 BOM lines, 243 parts.
* Floor plans: v1 130 x 125 (16 connections blocked by the LCD header row), v2 130 x 137 (LCD 13 mm lower),
  **v3 130 x 137** = v2 + decoupling from the finished 24-ch's relative layouts (MCU, buck, isolators),
  pincaps 0 before routing; then by `move.py`: drivers under the relays, D601 turned, ISP J501 and C601
  swapped (no signal crosses the 24 V feed). `gen/place.py` holds all of it.
* Routed v3: Freerouting 30 passes, then by hand (`gen/hand_routes.py` relays + chassis, `gen/buck8.py`
  LM5164 stage copper as on the 24-ch, 24 V feed 0.8 mm, AVDD via); H4 plain NPTH (P9).
* Per-board scripts are copies of the 24-ch ones with the 8-ch geometry and their own claim file
  `output/.writer.json`; the child-process claim bug (latent in the 24-ch tools, I-127) is fixed here.
* LCD-on-the-door study (scratch): 115 x 100 mm, 0 overlaps, routed to 64 violations / 15 unconnected.

## In work

* **Routed and checked 2026-10-14 evening:** `output/drc-report.rpt` (kicad-cli --schematic-parity
  --refill-zones --severity-error) = **0 violations, 0 unconnected, 0 parity**; `pincaps.py` 0 over the limit.
  Last steps: a box re-route (Freerouting) made 5 barrier violations and was dropped (`output/post-box-bad`);
  TC8_PA/NA re-done by `maze.py` (PA first); Q701's emitter (trip-relay driver) had no GND path but an
  isolated F.Cu pour piece - now a track + via to the In1 GND plane (53.54, 30.3-31.3); a GND via stitches the
  pour sliver beside J501 (14.56, 20.5). Then `vbias_pour.py` (bank A guard), `fiducials.py`, `silk.py`
  (profile 8 silk in `family/tools/profiles_new.py`; silk.py reads `bus_text`/`isp_dy`); DRC 0/0 after each.
  Backups in `output/`: drc-zero, vbias, fid (.kicad_pcb).
* 2026-10-19 (I-131): 12 hole_to_hole + 11 co-located holes and 3 vias into SMD lands fixed (Sol `output/sol-holes.txt`,
  23 rips / 3 adds; backup `output/pre-holes/`); DRC 0/0/0 with hole rules now errors, via hole to land >= 0.157 mm,
  pincaps 0. 2026-10-24 coordination with the 24-ch: I-129 relay rule (pours out of `relay_area`, gen + DRU), Sol trim
  (`output/coord/trim8.txt`, 1 track + 8 via dangling -> 0); **release `production/8ch-revb0-20261024-141437-3238f9/`**:
  DRC 0/0/0, warnings silk only, pincaps 0, holes 0, fill 496/496, MANIFEST 56/56, CPL-JLC (preview check) + POWER-ON-TEST
  + WHICH-FILE-WHERE; 113258, 042934, 5e720e archived. Older notes:
* Release `8ch-revb0-20261014-203721-5e720e` (archived; `fab.py --board 8`, then
  `assembly_spec.py` with Python 3.10): MANIFEST DRC (0, 0, 0), 92 BOM lines / 243 parts, none without LCSC,
  DNP none; ASSEMBLY-SPEC.pdf 4 pages, ORDER-NOTES, ACCESSORIES (`accessories.csv` here). Release texts:
  `family/tools/docs_new.py` (Sol, reviewed: power-on test back on the TPs, vendor text without firmware
  status). **Silk bug found and fixed before release:** the terminal labels followed pin numbers, but on
  the family boards J601/J701/J702 pin 1 is CHASSIS / NC (the 24-ch is correct) - `silk.py` now labels by
  net (`label_by_net`). Not ordered: the owner decides (I-124 is about the 24-ch; this board has the driver).
* Cost: `cost.py --board 8` priced 39 of 92 lines ($13.58 for those); jlcsearch returned no price for the
  rest although every part has its LCSC code - retry; CALCULATIONS 10.12 (~$570 / 10 boards) stays the estimate.

## Next

1. Owner review of the release candidate; cost retry; local-fab quotes (step L).
2. LCD on the board (130 x 137): owner 2026-10-14 evening "مش فارقة" - kept on the board.
3. Step L (local fab), Sol's desk study 2026-10-14: ERI (eri.sci.eg PCB lab: 1-6 layers, 0.15/0.15 mm, 0.3 mm
   holes) and Benha Electronics (up to 16 layers, PTH) publish 4-layer capability in Egypt - ask them to quote
   the 4-layer REV B0 before redesigning. A 2-layer REV B0 needs a fresh layout (~150 x 140 to 160 x 150 mm);
   the AD7124-8 has no coarser package (2x AD7124-4 TSSOP-24 would change the circuit). Local SMT: NORI, Fares
   PCB (LFCSP/X-ray UNVERIFIED). All UNVERIFIED supplier claims.
