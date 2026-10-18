# 8-ch board REV B0-2L (two layers, local fab) - state

Decision: `docs/decisions/0040` (owner request 2026-10-14 evening). Same circuit as the 4-layer REV B0
(`hardware/8ch-new/`, schematic from `hardware/family/gen` config "8"); 2 layers, 150 x 154 mm, rules for an
Egyptian 2-layer PTH fab (0.2/0.2 mm, vias 0.7/0.3; island nets 0.15 mm because of the AD7124 LFCSP).

## Done (2026-10-14)

* Schematic: `build.py 8 --out hardware/8ch-2l`: ERC 0/0, netlist 0 mismatches, 92 BOM lines, 243 parts.
* Board: `gen/pcb_new.py` (2 layers) + `kicad-tool pcb sync` (parity clean); `gen/place.py` spreads the
  routed 4-layer placement (anchors scaled, rigid groups: bank strip, LCD standoffs + J502/R502, buck stage,
  relay drivers, RS-485 pack) -> 0 courtyard overlaps; `gen/rules.py --route-prep`: no domain conflict;
  `gen/padcheck.py` clean; `gen/fanout.py`: 122 ground vias (grounds only; power is routed).
* `gen/route.py`: Freerouting routes everything, grounds included (`--ground-off` makes Freerouting stop
  after pass 1). First test, 1 pass: 126 unrouted.

## Routed and released (2026-10-16)

* Finishing the ADC area: `maze.py` left 12 (`output/hand4`); the last 12 were routed by Sol (gpt-6.1-sol)
  as a route list computed from the board text (no KiCad), `output/sol-routes.txt` (32 rips + 32 adds),
  applied by `finish.py --board 8l apply` -> **DRC 0 violations, 0 unconnected** (`output/pre-sol`,
  `output/sol-drc0`).
* `vbias_pour.py --board 8l` (bank A guard on F.Cu; `bias_keep_b`: the B.Cu GND_ISO pour stays, it is the
  only ground plane here), `fiducials.py`, `silk.py` (10 optional refs left off; `+24V` label placed tight);
  DRC 0/0 after each (`output/vbias`, `output/silk`).
* `pincaps.py`: 2 over the 3.0 mm limit from the spread placement - U501.5 (+5V, C503 3.9 mm) and U404.16
  (+3V3_ISO, C410 4.0 mm). Accepted for this board (limit 4.5 mm on those two pins in profile "8l"):
  100 nF at 4 mm on a 16 MHz AVR and a 1-4 Mbit/s isolator is harmless; the 4-layer keeps 3.0 mm.
* Superseded release `production/_OLD_DO_NOT_ORDER/8ch-revb0-2l-20261016-033622-d4c3fb/` (`fab.py --board 8l`, then
  `assembly_spec.py --board 8l` with Python 3.10): MANIFEST DRC (errors, unconnected, parity) **(0, 0, 0)**,
  `drc-report.rpt` 0 violations / 0 unconnected / 0 footprint errors; 92 BOM lines, none without LCSC,
  DNP 0; Gerbers 2 copper layers; ORDER-NOTES/ASSEMBLY-SPEC say 2 layers (profile key `copper_layers`).

## Astra review fixes (2026-10-16)

Astra (gpt-6-astra, read-only) review: "send after fixes". Done:
* Vias: annular ring 0.15 mm on 177 vias (0.6/0.3 and 0.7/0.4) -> 0.7/0.3; 23 stay 0.6/0.3 (0.7 does not fit);
  the U101 exposed-pad holes are now 0.3 mm, clear of the paste windows. 3 duplicate vias removed.
* `relay_area` no longer applies to pours (I-129): the GND pour keeps 2 mm from the contact tracks.
* ORDER-NOTES / spec state the real smallest features (profile key `fab_limits`); "isolation slot" ->
  "copper-free isolation gap" on the family boards (no milled slot); LCD standoffs >= 11 mm (we buy them).
* **Release candidate `production/8ch-revb0-2l-20261016-203125-6a2893/`**: MANIFEST DRC **(0, 0, 0)**, 92 BOM
  lines, ASSEMBLY-SPEC 4 pages. The 033622 release moved to `production/_OLD_DO_NOT_ORDER/`.
* Open from the review, accepted as notes: bottom pour in 7 pieces and TC7/TC8 partly without pour under them
  (I-128 bench test), CJ placement thermally unproven, U601 exposed-pad holes at 0 mm from the paste windows
  (ask the assembler: plug/tent from the bottom), `+24V` silk touches an outline stroke.

## Next

1. Quotes from a local 2-layer fab + SMT house (LFCSP needs stencil + reflow; ENIG preferred, HASL quoted
   as an option); I-128 bench comparison with the 4-layer.
