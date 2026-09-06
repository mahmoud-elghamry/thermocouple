# Goal and requirements

**Owner: the user.** An agent may propose a change here but must not rewrite it
alone. Changes go through `docs/decisions/`.

**Keep under 120 lines.**

---

## The goal

A unit that reads **eight K-type thermocouples** on a machine and **stops the
machine** when any channel goes over its setpoint.

It is going onto real equipment. It is not a demonstration.

## What it must do

| # | Requirement | Status |
|---|---|---|
| R-1 | Read 8 K-type thermocouples | design complete |
| R-2 | Open a dry contact when any channel exceeds the setpoint | design complete |
| R-3 | Energised to run — power loss, reset or fault must stop the machine | design complete |
| R-4 | Show the readings and the state locally | design complete (16x2 LCD, 5 buttons) |
| R-5 | Latch a trip until it is acknowledged | firmware, tested on host |
| R-6 | Detect a broken or shorted sensor and treat it as a trip | partial — see `I-011` |
| R-7 | Survive a motor/VFD panel and 50 m cable runs | **not proven — needs measurement** |
| R-8 | Keep the setpoint across a power cycle | **not done — see `I-012`** |
| R-9 | Communicate over RS-485 (Modbus RTU planned) | hardware ready, protocol not written |

## What it must not do

- Allow the machine to run when the unit itself has failed.
- Report a temperature it is not confident in.
- Depend on the isolation barrier for mains-level separation. It is not
  qualified for that.

## Response time

The trip must happen within **1 s** of the setpoint being crossed. The current
firmware scans every 500 ms. **This has never been measured on hardware** —
see `I-013`.

## Explicitly out of scope for now

- Certification to IEC 61010 / IEC 61508.
- 4-20 mA or 0-10 V analogue output.
- Any IoT or cloud path. RS-485 to a local master only.

## The open architectural question

The eight thermocouples share one isolated island. That isolates the group from
the controller but **not the channels from each other**.

The user's position (2026-09-06): all eight sensors sit on the same cylinder, so
their sheaths are on the same ground in practice, and the MAX31856 is designed
for grounded junctions. Accepted on that basis — recorded in
`docs/decisions/0003-shared-sensor-island.md`.

It still has to be confirmed by measuring the potential between the sensor
sheaths and the panel ground before the unit is trusted.
