---
status: accepted
date: 2026-09-06
deciders: Claude
---

# Leave DRDY and FAULT unconnected; read faults over SPI

## Context

Each MAX31856 has two diagnostic outputs, `DRDY` and `FAULT`. On this board all
sixteen are unconnected, and an earlier design review flagged that as a defect.

Bringing them to the MCU means crossing the isolation barrier. Both isolators
are fully allocated: ISO7760 uses all six channels forward (SCK, MOSI, CS1-CS4)
and ISO7761 uses five forward (CS5-CS8) plus one reverse for MISO. There is one
spare channel and it runs the wrong way.

## Decision

Leave them unconnected, with explicit no-connect markers in the schematic, and
rely on the MAX31856 fault register (0x0F), which the firmware reads with every
sample.

## Why

Connecting them would need a third isolator plus fault-OR logic — the FAULT
outputs are push-pull, so they cannot simply be wired together.

The gain would be latency: microseconds instead of the 500 ms scan interval.
The stated trip requirement is 1 s. The register already carries every fault the
pin would signal.

And a hardware FAULT line would cross the **same** isolator group as the SPI
bus, so it adds no independent path. If the isolator or the SPI link fails, both
routes fail together.

## What this depends on

This decision is only safe while the firmware actually trips on a fault rather
than ignoring it. That is tracked as `I-011` — the firmware currently has no
detection for a stuck or frozen reading, which is the failure this register is
supposed to catch.

If the trip requirement ever drops below about 100 ms, revisit this.
