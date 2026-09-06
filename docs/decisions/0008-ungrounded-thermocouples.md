---
status: proposed
date: 2026-09-07
deciders: Zain, Claude
supersedes: 0003
---

# Specify ungrounded-junction thermocouples

## Context

`0003` accepted one shared isolated island for all eight channels. It recorded
the user's reasoning as *"all eight thermocouples are mounted on the same
cylinder, so their sheaths are bonded to the same metal and sit at the same
potential."*

**That premise was wrong.** It was a misreading on 2026-09-06 and the user
corrected it on 2026-09-07: the eight sensors are on the **same machine but on
eight different cylinders**. Each sheath is bonded to a separate metal mass,
reaching the frame through its own bolts and brackets.

That changes the arithmetic completely. With grounded-junction probes, every
sheath is tied to the shared island through its own junction and its 100 Ω
series resistor, so a potential difference between two cylinders drives current
straight through the front end:

| Sheath-to-sheath difference | Loop current (~250 Ω) | Across one 100 Ω leg | Reading error |
|---|---|---|---|
| 1 mV | 4 µA | 0.4 µV | 0.01 °C |
| 50 mV | 0.2 mA | 20 mV | ~490 °C |
| 1 V | 4 mA | 400 mV | beyond the input range |

K-type gives about 41 µV/°C, so the budget for a 1 °C error is roughly 4 mV of
sheath-to-sheath difference. On a machine with a VFD injecting common-mode
current into the frame, separate cylinders will not hold that.

## Decision

**Specify ungrounded (insulated) junction thermocouples.**

In an ungrounded probe the measuring junction is electrically isolated from the
sheath, typically above 100 MΩ. There is then no conductive path between one
cylinder and another through this board, and the shared island stops being a
liability: the eight channels are no longer tied together by the machine.

This is a purchasing decision, not a redesign. The board does not change. The
cost is response time - an ungrounded probe lags a grounded one by a second or
two through the sheath wall, which does not matter for cylinder temperature
protection with a trip requirement of one second on a thermal process.

## What this does not settle

- **Input bias for a floating source.** With an ungrounded probe the input pair
  floats. `C2`/`C3` couple each leg to `GND_SENS` for AC but give no DC path.
  Confirm from the MAX31856 datasheet whether its internal biasing defines the
  common mode on its own; if it does not, one high-value resistor per channel
  from `TC_FILT_N` to `GND_SENS` (1 MΩ is usual) is the standard fix, and that
  *would* change the schematic. Tracked as `I-026`.
- The sheath-to-sheath measurement in `0003` is still worth making, because it
  tells you how bad the environment is and whether the shielding is working.
- Nothing here changes the EMC, noise or real-sensor testing.

## Alternatives rejected

- **Keep grounded junctions and add per-channel isolation.** Eight isolated
  supplies and eight isolator groups: roughly doubles the part count, the board
  area and the cost, to solve a problem a different probe removes for free.
- **Keep grounded junctions on the shared island.** Rejected on the arithmetic
  above. This is what `0003` accepted on a wrong premise.
- **4-20 mA head transmitters.** Still the most robust option over 50 m and
  still worth considering later, but it moves the measurement out of this unit
  and changes the product.
