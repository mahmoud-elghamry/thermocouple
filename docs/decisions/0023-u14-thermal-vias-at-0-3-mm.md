# 0023 — U14's thermal vias at 0.3 mm, placed by the generator

* Status: accepted
* Date: 2026-09-28
* Deciders: owner ("ما تعملهم 0.3 mm")
* Supersedes: `0017`

## Context

`0017` kept the six 0.2 mm thermal vias of KiCad's
`SOIC-8-1EP_..._ThermalVias` footprint under the LM5164 (`U14`), and lowered
the board's minimum hole to 0.2 mm. The 0.2 mm came with the library
footprint, not from a calculation. It made them the only holes on the board
below the usual 0.3 mm fab standard, which may cost extra and has to be
checked on every quote.

## Decision

Use the plain `SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.3mm` footprint. Instead,
`board/stitching.py` `add_u14_thermal_vias()` puts **six 0.3 / 0.6 mm vias** on
the exposed pad (GND_CTRL):

* positions x ±0.6, y −1.2 / 0 / +1.2 from the pad centre
* the footprint had x ±0.7, moved in so a 0.6 mm via stays inside the
  2.41 mm pad
* that keeps TI's layout and heat path (same count, bigger holes)

`min_through_hole_diameter` goes back to 0.3 mm. There is no hole on the board
below 0.3 mm now.

## Rejected

* **Keep 0.2 mm (`0017`).** It works, but it is a fab option paid for nothing:
  0.3 mm vias carry the same heat.
* **No vias under the pad.** At about 0.3 W that is probably survivable, but
  the panel sits by an engine and the vias cost nothing.

## Consequences

Vias in the pad are open (not filled). A little solder can wick into them at
reflow. The 0.2 mm ones had the same property, and TI's layout accepts it.
