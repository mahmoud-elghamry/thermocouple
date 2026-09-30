# Goal and requirements

**Owner: the user.** An agent may propose a change here but must not rewrite it
alone. Changes go through `docs/decisions/`.

**Keep under 120 lines.**

---

## The goal

A system that reads **24 K-type thermocouples** and stops the relevant machine
when a channel exceeds its setpoint. Owner clarified the count on 2026-09-29
(`decisions/0024`); one machine versus independent groups is awaiting confirmation.
The existing eight-channel board is a candidate module, not the whole system.

It is going onto real equipment. It is not a demonstration.

## Where it runs

Earlier eight-channel installation basis, corrected 2026-09-07. The 2026-09-29
24-channel clarification supersedes the system count; do not extrapolate the
old one-engine/one-probe-per-cylinder mapping to all 24 channels.

| | |
|---|---|
| The machine | Earlier basis: one eight-cylinder engine, no VFD. Machine count and shutdown grouping for 24 sensors: **owner will confirm** |
| The sensors | Earlier basis: cylinder bodies, not exhaust gas. Exact mapping of all 24: **unconfirmed** |
| The unit | Owner currently expects boards in the same panel or nearby. More distant placement is an option, not selected. Earlier sensor cable basis: roughly 50 m |
| Vibration and heat | Existing basis is a separate panel; moving acquisition onto/near the engine requires a fresh environmental assessment |
| The 24 V supply | Engine battery per accepted decision `0016`; surge qualification remains open (I-028/I-077) |

For the existing eight-channel same-engine basis, the shared isolated island
floats with the probe group and the barrier separates it from the controller.
That rationale must be rechecked if channel assignment spans different machines.

## What it must do

| # | Requirement | Status |
|---|---|---|
| R-1 | Read 24 K-type thermocouples | **system incomplete**; current PCB/firmware provide eight channels |
| R-2 | Open the appropriate dry contact when any associated channel exceeds its setpoint | Eight-channel implementation exists; system output count/group mapping pending; I-073/I-081 open |
| R-3 | Energised to run — power loss, reset or fault must stop the machine | Eight-channel implementation; single-fault limitations in I-081, system shutdown architecture pending |
| R-4 | Show the readings and the state locally | Current eight-channel UI: 16x2 LCD, 5 buttons; 24-channel/master UI not implemented |
| R-5 | Latch a trip until it is acknowledged | Host-tested implementation with unsafe save-recovery ACK gap I-073 |
| R-6 | Detect a broken or shorted sensor and treat it as a trip | partial — plausibility checks do not prove detection of every short; see `I-011` |
| R-7 | Survive an engine installation and 50 m cable runs | **not proven — needs measurement** |
| R-8 | Setpoint is operator-settable and survives a power cycle — never hard-coded | EEPROM implementation exists; integration validation and I-036/I-037 status in `STATE.md` |
| R-9 | Coordinate boards if a modular architecture is selected; RS-485/Modbus RTU is a candidate | Protocol/master not written; previous standalone deferral does not complete the 24-channel system (`0024`, I-086) |

## What it must not do

- Allow the machine to run when the unit itself has failed.
- Report a temperature it is not confident in.
- Depend on the isolation barrier for mains-level separation. It is not
  qualified for that.

## Response time

The trip must happen within **1 s** of the setpoint being crossed. The existing
eight-channel timing budget is in `I-013`; physical timing is unmeasured.
The 24-channel system needs its own end-to-end budget, including communication
and stale-data handling wherever they participate in shutdown.

## Explicitly out of scope for now

- Certification to IEC 61010 / IEC 61508.
- 4-20 mA or 0-10 V analogue output.
- Any IoT or cloud path. RS-485 to a local master only.

## The open architectural question

The existing board's eight thermocouples share one isolated island. That isolates
the group from the controller but **not the channels from each other**.
The system choice between one 24-channel board and multiple modules is still open.

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
