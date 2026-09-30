# 0026 — The U14 power stage is placed and drawn by the generator, not autorouted

* Status: accepted
* Date: 2026-10-01
* Deciders: owner (approved the P0 plan), agent
* Relates to: `I-076`, `I-075`, `0012`, `0016`

## Context

Freerouting routed the LM5164 stage like any other net:

* C63 sat 19.5 mm of track from VIN, and C54 12.1 mm;
* SW reached L1 through 0.2 mm sections.

TI's layout guidance (LM5164 datasheet section 7.4) is the opposite: input
capacitors at the VIN/GND pins, a short, wide SW node, and the bootstrap
capacitor at BST/SW. On a board that measures microvolts, a large switching
loop is the most likely source of noise.

## Decision

`board/powerstage.py` draws the high-current copper before routing, and
`placement.py` places the parts for it:

* **VIN:** C63 and C54 stand at 90 degrees beside pins 1-2. One straight
  0.8 mm track runs C54, C63, U14.2.
* **GND:** each capacitor's GND pad has its own via to the plane, plus a track
  to U14.1.
* **SW:** L1 is level with pin 8, and a straight 1.0 mm track runs from pin 8
  across C62's SW pad into L1.
* **BST:** a 0.4 mm track goes to C62.

`route.py` marks those nets "protect" in the DSN. Only this copper exists on
them at export, so the router connects the rest around it and cannot move it.

The generator stays reproducible: this is a *generative* change (`0012`), not a
hand edit.

## Rejected

* **Hand-route in KiCad after routing:** it is lost at the next regeneration and
  cannot be reproduced.
* **Keep autorouting and add constraints:** Freerouting has no notion of a
  switching loop. Tighter rules would only move the detour.
* **Replace the buck with a module:** that is decision `0016`'s territory, and it
  costs more for no reason once the layout is right.

## Consequences

The results are in `CALCULATIONS.md` 5.2. The board still needs its rails, SW
ringing and sensor noise measured (I-076, P2). A future change to U14's
surroundings must keep `powerstage.py` and `placement.py` consistent. The
module raises an error if the VIN pads stop lining up.
