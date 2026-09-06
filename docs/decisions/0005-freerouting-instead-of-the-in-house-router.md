---
status: accepted
date: 2026-09-06
deciders: Zain, Claude
---

# Route with Freerouting; keep design rules in the KiCad project

## Context

`generate_board.py` carried its own A* maze router: 0.5 mm grid, orthogonal
moves only, no rip-up and retry, and clearance modelled as grid occupancy rather
than geometry. It produced 381 DRC violations, left five nets unrouted, and
emitted roughly 4000 track segments that could not be edited by hand.

Track widths, via sizes and clearances were Python constants, so nobody opening
the project in KiCad could see the rules the board had been built to, and DRC
was not checking them.

## Decision

Two changes:

1. **Routing goes to Freerouting 2.4.1** through Specctra DSN/SES.
   `pcbnew` exports the DSN, `route.py` adjusts it, Freerouting routes, and the
   session is imported back as ordinary KiCad tracks.
2. **Design rules move into the project.** `apply_rules.py` writes nine net
   classes into `thermocouple_8ch.kicad_pro` and the isolation, relay and
   chassis rules into `thermocouple_8ch.kicad_dru`.

## Result

| | Before | After |
|---|---|---|
| clearance violations | 304 | 0 |
| tracks crossing | 22 | 0 |
| shorting items | 19 | 0 |
| dangling vias | 7 | 0 |
| unrouted nets | 5 | 0 |
| unconnected items | 46 | 9 |

## What it did not fix

Freerouting converges with a handful of connections open. That is a placement
and density problem on two signal layers, not a router problem — no autorouter
finishes a board this dense at 100 %. The remainder is `I-001`.

## Operating notes

Recorded in `docs/TOOLS.md` because they cost real time to find: run
single-threaded (Freerouting's own warning says the multi-threaded optimiser
generates clearance violations), pad the clearances written into the DSN because
Freerouting rounds them down, and re-declare In1/In2 as `power` layers so
signals stay on the outer layers.

## Alternatives rejected

- **Keep and fix the in-house router.** Would mean writing rip-up and retry and
  a real clearance model — reimplementing Freerouting, badly.
- **Route entirely by hand.** Correct for a production board and still the right
  finish for the last few connections, but not a starting point for 154 nets.
