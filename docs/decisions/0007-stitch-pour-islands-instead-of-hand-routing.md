# 0007 — Stitch the pour islands instead of finishing the board by hand

**Date:** 2026-09-07
**Decided by:** Claude
**Status:** accepted

## Context

`I-001` had between nine and sixteen connections open on `hardware/8ch`,
varying from run to run. The issue described them as short links to plane nets
that would have to be finished by hand in KiCad.

Reading the DRC report item by item showed they were not one problem but three,
and only one of them was routing:

| Count | What it actually was |
|---|---|
| 7 | `Zone 'CONTROL_GND_F'` and `Zone 'SENSOR_GND_F'` listed against themselves — separate pieces of the same outer ground pour, cut apart by the routing that runs through them |
| 4 | Surface-mount pads on `+5V_CTRL` with no via down to the plane |
| 1 | A real routing gap on `SCK_SENS` at `U8` pin 10 |

Two causes sat behind the first eleven:

1. `add_plane_stitching` was filtering on `!= "+3V3_SENS"` and therefore only
   stitched one of the six plane nets. `+5V_CTRL` pads were never considered.
2. `finish()` added the outer ground pours **after** the stitching pass, so the
   pieces did not exist yet when anything went looking for them.

## Decision

Fix the pipeline rather than the board:

- Stitch every plane net, not just `+3V3_SENS`.
- Pour and fill before stitching, so the pieces exist when the pass runs.
- Add `stitch_pour_islands`, which drops one via into each isolated piece of an
  outer pour. A via is only placed where the inner plane for that net actually
  is, so it cannot land somewhere it reaches nothing.
- Fall back from a 0.8 mm via to a 0.6 mm one where the first will not fit.
  0.6 mm is still above the 0.5 mm floor in the project rules.
- Move `C56`/`C57`/`R33` up by 1 mm. At `y = 88` the strip between the relay
  courtyard and `U15` left 1 mm of clear board, which was not enough to bring
  `+5V_CTRL` from `C57` down to `U15` pin 2.

## Alternatives rejected

**Finish it by hand in KiCad**, as `I-001` originally proposed. Rejected
because `generate_board.py` clears every track, via, zone and drawing, so
hand-drawn copper is erased by the next regeneration. A fix that does not
survive `run_all.ps1` is not a fix; it is a one-off artefact that makes the
board and its generator disagree.

**Delete the isolated pieces instead of connecting them.** Rejected because the
pieces that survive `ISLAND_REMOVAL_MODE_ALWAYS` are the ones anchored by a
pad — removing them would disconnect that pad.

**Force the vias in and accept the violations.** Rejected: an earlier attempt at
exactly that put 88 shorts and 16 hole-clearance errors on the board.

## Consequences

`hardware/8ch/drc-report.rpt`, 2026-09-07: **0 errors, 0 unconnected items,
0 schematic-parity issues.** Nine warnings remain — six silkscreen overlaps,
two silkscreen-over-pad, one dangling via (`I-024`).

Fabrication output is generated in `production/8ch/`. The board is releasable
as an **engineering prototype**; every constraint in `AGENTS.md` still stands,
and none of them is closed by a clean DRC.
