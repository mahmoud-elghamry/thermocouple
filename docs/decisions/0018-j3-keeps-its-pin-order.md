# 0018 — J3 keeps its COM/NO/NC order; the board moves to match K1

* Status: accepted
* Date: 2026-09-25
* Deciders: owner
* Relates to: `I-058`, `I-061`

## Context

After the `I-058` fix, K1's real contact pads are NO = pad 3 (219, 79.2) and
NC = pad 4 (231, 79.2). `J3` (rot 90, entry facing the edge) presents
COM/NO/NC bottom-to-top. So the relay-to-terminal traces have to cross, and
`RELAY_NC` could only be routed by breaking the 2 mm relay-contact clearance.

## Options

* **(a) Move `J3` (and `R33`, which is in the way) so its pins line up with
  K1's pads.** Only the layout changes. The installer sees the same terminal
  order.
* **(b) Change `J3`'s pin order in the schematic.** Routing gets easier, but the
  order the installer wires to changes.

## Decision

**(a).** J3 is the dry contact of an energised-to-run safety output. A terminal
order that differs from what an installer expects is a wiring error waiting to
happen. A miswired contact can defeat the protection with no visible symptom.
Moving two parts costs less than that risk.

## Consequences

* `board/placement.py`: move `J3` (for example, pins at y 89/84/79) and `R33`.
  Check it in KiCad, then regenerate. DRC must show zero `clearance` errors on
  `RELAY_*`, and `check_board.py` must pass.
* J3's silkscreen and the installation wiring note stay as they are.
