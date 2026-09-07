# Goal and requirements

**Owner: the user.** An agent may propose a change here but must not rewrite it
alone. Changes go through `docs/decisions/`.

**Keep under 120 lines.**

---

## The goal

A unit that reads **eight K-type thermocouples** on an engine - one per cylinder
- and **stops the engine** when any channel goes over its setpoint.

It is going onto real equipment. It is not a demonstration.

## Where it runs

Corrected 2026-09-07 after two agents assumed and got it wrong. Read this before
designing anything.

| | |
|---|---|
| The machine | An **engine**, eight cylinders. **There is no VFD anywhere.** |
| The sensors | One per cylinder, on the **cylinder body** - not exhaust gas |
| The unit | In its **own panel**, roughly **50 m** of cable from the engine |
| Vibration and heat | **Not design constraints.** The board is not on the engine |
| The 24 V supply | **Undecided.** A panel supply needs no change; the engine's own battery needs a wider-input regulator - see `I-028` |

Because the unit sits in a panel and the sensors sit on one engine block, the
eight sheaths are bonded to the same metal. The shared isolated island floats up
to engine-block potential as a whole and the barrier carries the difference
between the engine and the panel.

## What it must do

| # | Requirement | Status |
|---|---|---|
| R-1 | Read 8 K-type thermocouples | design complete |
| R-2 | Open a dry contact when any channel exceeds the setpoint | design complete |
| R-3 | Energised to run — power loss, reset or fault must stop the machine | design complete |
| R-4 | Show the readings and the state locally | design complete (16x2 LCD, 5 buttons) |
| R-5 | Latch a trip until it is acknowledged | firmware, tested on host |
| R-6 | Detect a broken or shorted sensor and treat it as a trip | partial — plausibility checks do not prove detection of every short; see `I-011` |
| R-7 | Survive an engine installation and 50 m cable runs | **not proven — needs measurement** |
| R-8 | Setpoint is operator-settable and survives a power cycle — never hard-coded | EEPROM implementation exists; integration validation and I-036/I-037 status in `STATE.md` |
| R-9 | Communicate over RS-485 (Modbus RTU planned) | deferred for REV A0 by decision `0010`; protocol not written |

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

Accepted, and the reasoning is now on record correctly in
`docs/decisions/0009-operating-environment-corrected.md`: the eight sensors sit
on one engine block, so channel-to-channel differences are small, and there is
no VFD injecting common-mode current into the frame. `0003` reached the same
answer from a wrong premise and is superseded; `0008` over-corrected from
another wrong premise.

Still to be confirmed before the unit is trusted:

- Measure the potential between the sensor sheaths and the panel ground with the
  engine running and while cranking (`I-004`).
- Ungrounded probes would remove the cranking-current path between cylinders for
  free. Not required, worth asking the supplier for (`I-026`).
