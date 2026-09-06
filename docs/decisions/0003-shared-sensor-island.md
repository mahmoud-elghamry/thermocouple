---
status: superseded by 0008
date: 2026-09-06
deciders: Zain
---

> **Superseded on 2026-09-07.** The premise below - that all eight
> thermocouples share one cylinder - is wrong. They are on the same machine but
> on **eight different cylinders**. See `0008`.

# Accept one shared isolated island for all eight channels

## Context

Eight MAX31856 front ends sit on a single isolated ground (`GND_SENS`), fed by
one isolated DC-DC and separated from the controller by ISO7760 / ISO7761.

This isolates the **group** from the controller. It does **not** isolate the
channels from each other. With grounded-tip thermocouples on long cables, any
potential difference between two sensor sheaths appears directly across the
shared island, and the earlier planning work rejected this arrangement for field
use on exactly that basis.

## Decision

Accept the shared island for this build.

The user's reasoning, **as misread on 2026-09-06**: all eight thermocouples are
mounted on the same cylinder, so their sheaths are bonded to the same metal and
sit at the same potential in practice. They are in fact on eight *different*
cylinders, which invalidates this - see `0008`. The MAX31856 is designed to work with grounded junctions, and 50 m is
at the edge of, not beyond, its usable range.

## What this does not settle

- **The equal-potential assumption has not been measured.** Before the unit is
  trusted, measure the potential between each sensor sheath and the panel ground
  with the motor and VFD running.
- Per-channel isolation, or 4-20 mA head transmitters, remain the alternatives
  if that measurement shows a difference that matters.
- Nothing here changes the noise, EMC or accuracy work that still has to happen
  on real sensors and real cable.

## Alternatives rejected for now

- **Per-channel isolation.** Eight isolated supplies and eight isolator groups.
  Correct in the general case; not justified if the sheaths really are common.
- **4-20 mA head transmitters.** The most robust option over 50 m, but it moves
  the measurement out of this unit and changes the product.
