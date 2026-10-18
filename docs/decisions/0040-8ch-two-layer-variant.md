# 0040 - 8-ch two-layer variant for a local (Egyptian) fab: REV B0-2L

* Status: accepted (owner request 2026-10-14 evening; layout choices delegated to Claude)
* Date: 2026-10-14
* Products: `hardware/8ch-2l/` (new), `hardware/8ch-new/` (4-layer REV B0, unchanged)

## Context

The owner wants an 8-ch board "that anyone in Egypt can make and solder". The 4-layer REV B0 is finished
(`production/8ch-revb0-20261014-203721-5e720e`, DRC 0/0/0). Sol's desk study (2026-10-14, `8ch-new/STATE.md`
step L): Egyptian 2-layer PTH fabs publish 0.2/0.2 mm (Piclaro) to 0.15/0.15 mm (ERI, 1-6 layers); local SMT
(NORI, Fares) is credible, LFCSP/X-ray UNVERIFIED. The AD7124-8 has no coarser package.

## Decision

1. **Same circuit, same schematic** (`hardware/family/gen` config "8"): no part changes, so the firmware and
   every calculation of REV B0 hold. A second variant, not a replacement: the 4-layer stays the reference.
2. **Placement = the routed 4-layer placement spread 1.154 x 1.124 to 150 x 154 mm** (`8ch-2l/gen/place.py`):
   big parts move, small parts ride with their anchor (decoupling stays at the pins), bank A's terminal strip,
   the LCD standoff pattern, the buck stage and the relay-driver pack stay rigid, barrier parts stay centred
   on the band. Domains and bands are the 4-layer ones at the new coordinates.
3. **Copper: two layers, ground poured on both** per domain (GND_ISO / GND / GND_RS485), power as tracks
   (+5V 0.6 mm, +3V3_ISO 0.5 mm, 24 V 0.8 mm); every ground pad has its own via to the bottom pour.
4. **Local-fab rules:** track/space 0.2/0.2 mm, vias 0.7/0.3 mm (0.2 mm ring), except the island nets at
   0.15 mm: the AD7124 LFCSP's own corner pads are 0.18 mm apart, so whichever fab makes it needs 0.15 mm
   (ERI publishes it). Isolation and contact rules unchanged (functional, not IEC 61010).

## Rejected

* **Fresh 2-layer floor plan** - days of work; the spread keeps the proven neighbourhoods and the decoupling.
* **2x AD7124-4 (TSSOP-24) for hand soldering** - changes the circuit, the firmware and every bank calculation;
  the AD7124-8 LFCSP needs stencil + reflow or hot air (a local SMT house), not a soldering iron. Revisit only
  if no local assembler takes the LFCSP.
* **Grounds left out of the router** (one pin per ground net in the DSN): Freerouting stopped after pass 1.

## Consequences

* Bigger board (150 x 154 vs 130 x 137) and more vias; the inputs lose the solid inner GND_ISO plane - the
  bottom pour is cut by tracks, so 50 m cable pickup and CJ gradients must be measured, not assumed (I-128).
* Release follows the 4-layer flow (`fab.py`), once the family tools know the board (profile "8l").
* Decoupling distance: the spread puts C503 (U501 VCC) 3.9 mm and C410 (U404 VCC2) 4.0 mm from their pins,
  over the family's 3.0 mm check; accepted on this board only (`pincaps` limit 4.5 mm on those two pins,
  profile "8l"): harmless at 16 MHz / a few Mbit/s. Rejected: moving them after routing (re-route of the
  dense MCU and isolator escapes for no measurable gain).
