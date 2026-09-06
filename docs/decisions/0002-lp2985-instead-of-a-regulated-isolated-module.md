---
status: accepted
date: 2026-09-06
deciders: Claude
supersedes: none
---

# Fix the sensor supply margin at the LDO, not at the isolated module

## Context

The measurement island is fed by `U12` (XP Power IA0505S), an **unregulated**
1 W isolated module, into `U13`, an AP2112K-3.3 LDO.

The island draws roughly 20 mA at 3.3 V — about 12 % of the module's rating. An
unregulated module at light load runs above its nominal output; the IA series
specifies up to 15 % load regulation, so 5.75 V is plausible and 6.0 V is not
far off. The AP2112K's recommended maximum input is 6.0 V.

That is a supply feeding the analogue front end of a machine-protection device
sitting at the edge of its regulator's rating. It is not acceptable.

## Decision

Replace `U13` with an **LP2985-3.3** (16 V maximum input) and raise `C48` from
1 µF to 4.7 µF to meet the LP2985's ≥ 2.2 µF output capacitor requirement.

Keep `U12` (IA0505S) unchanged.

## Why not change the module instead

The obvious fix is a regulated isolated module. Every regulated 1 W part
available in the KiCad libraries puts its pins on a 2.54 mm pitch:

| Part | Regulated | Isolation | Pin gap across the barrier |
|---|---|---|---|
| IA0505S (current) | no | 1 kVDC | **3.23 mm** |
| MEE1S0505SC | yes | 3 kVDC | 0.94 mm |
| NCS1S2405SC | yes | 1 kVDC | 7.58 mm, but has an unverified control pin |

Moving to MEE1S would have traded a 3.23 mm isolation gap for 0.94 mm. The
barrier is the reason this architecture exists; narrowing it to fix a
regulation margin is the wrong trade.

NCS1S2405SC would have been the best of both — regulated, wider gap, and fed
from the 24 V rail instead of loading the 5 V one — but its pin 3 "Control"
logic could not be confirmed. Murata's datasheet server returned HTTP 500 on
three attempts. Guessing the polarity of an enable pin on a protection board
risks a unit that never starts, or a damaged module. Left as `I-008`.

## Consequence

The LP2985 is pin-for-pin identical to the AP2112K in SOT-23-5 (1 VIN, 2 GND,
3 enable, 4 bypass, 5 VOUT), so the footprint, the placement and the routing are
unchanged. Worst-case headroom goes from 0.25 V to about 9 V.

The IA0505S output should still be measured on the first hardware — `I-003`.
