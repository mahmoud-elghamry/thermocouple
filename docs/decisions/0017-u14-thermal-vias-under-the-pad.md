# 0017 — Keep U14's thermal vias; lower the board hole minimum to 0.2 mm

* Status: accepted
* Date: 2026-09-25
* Deciders: owner
* Relates to: `I-060`, `I-061`, `docs/decisions/0016`

## Context

The LM5164 (`U14`, `0016`) uses the footprint
`SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.3mm_ThermalVias`. Its six thermal vias
are 0.2 mm drills. The board minimum was 0.3 mm, so the first REV A1
regeneration gave 6 `drill_out_of_range` DRC errors.

## Options

* **(a) Keep the vias under the pad; lower `min_through_hole_diameter` to
  0.2 mm.** This is TI's reference layout and gives the better heat path.
  JLCPCB and PCBWay make 0.2 mm on 4 layers, sometimes at extra cost.
* **(b) Use the plain `..._EP2.41x3.3mm` footprint with 0.3 mm vias beside the
  pad.** Cheaper, but the heat path is worse.

## Decision

**(a).** The dissipation is small, about 0.3 W at 5 V / 0.4 A. But the panel
sits beside an engine, and the regulator feeds everything. The owner chose the
recommended layout.

Only the minimum changes: `apply_rules.py` sets `min_through_hole_diameter`
to 0.2. The routed-via sizes stay 0.6/0.3 mm, so the only 0.2 mm holes on the
board are the six under U14.

## Consequences

* Check the fab quote for the 0.2 mm drill before ordering. If it costs a lot,
  revisit (b); the footprint swap is one line in `populate_schematic.py`.
* The change reaches `.kicad_pro` on the next `apply_rules.py` run, which is
  part of the regeneration.
