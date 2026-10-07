# Goal and requirements

**Owner: the user.** An agent may propose a change here but must not rewrite it
alone. Changes go through `docs/decisions/`.

**Keep under 120 lines.**

---

## The goal

A system that reads **24 K-type thermocouples** using **three autonomous
eight-channel modules**. Their run-permit contacts are in series: any channel
trip opens the common shutdown circuit (owner confirmed 2026-10-07,
`decisions/0024`). The existing board implements one module, not the whole system.

It is going onto real equipment. It is not a demonstration.

## Where it runs

Earlier eight-channel installation basis, corrected 2026-09-07. The 2026-09-29
24-channel clarification supersedes the system count; do not extrapolate the
old one-engine/one-probe-per-cylinder mapping to all 24 channels.

| | |
|---|---|
| The machine | Earlier basis: one eight-cylinder engine, no VFD. Common series shutdown for all 24 confirmed; physical sensor/engine mapping remains unconfirmed |
| The sensors | K-type; probably grounded-junction (owner, 2026-10-07), not verified. Earlier basis: cylinder bodies; exact model and 24-channel mapping unconfirmed |
| The unit | Same panel or nearby; K-type shielded twisted extension cable, roughly 50 m basis accepted (`0029`); exact cable/termination to be specified |
| Vibration and heat | Existing basis is a separate panel; moving acquisition onto/near the engine requires a fresh environmental assessment |
| The 24 V supply | Engine battery per accepted decision `0016`; surge qualification remains open (I-028/I-077) |

For the existing eight-channel same-engine basis, the shared isolated island
floats with the probe group and the barrier separates it from the controller.
That rationale must be rechecked if channel assignment spans different machines.

## What it must do

| # | Requirement | Status |
|---|---|---|
| R-1 | Read 24 K-type thermocouples | Three 8-channel modules selected; complete physical system not built or tested |
| R-2 | Open the common potential-free dry-contact circuit when any channel exceeds its own setpoint | Dry contact exists; per-channel limits pending I-100; contact/load ratings unresolved I-092; A2 low-voltage only; I-081 accepted limit |
| R-3 | Energised to run — power loss, reset or fault must stop the machine | Local implementation; series shutdown selected; single-fault limitations in I-081 |
| R-4 | Show readings, channel limits and state locally | LCD off-board; display type/mounting/buttons delegated to design team (`0029`); current 16x2/5-button UI needs per-channel editing |
| R-5 | Latch startup/reset/trip until manual ACK with valid, cool channels | Owner reconfirmed 2026-10-07 (`0029`, I-089 closed); per-channel reset checks pending I-100; I-073 fixed |
| R-6 | Detect a broken or shorted sensor and treat it as a trip | partial — plausibility checks do not prove detection of every short; see `I-011` |
| R-7 | Survive an engine installation and 50 m cable runs | **not proven — needs measurement** |
| R-8 | Each channel has its own operator-settable persistent setpoint; values chosen at commissioning | Accepted 2026-10-07 (`0029`); current firmware stores one shared limit per module; per-channel UI/EEPROM/protection not implemented (I-100) |
| R-9 | Optional later communication between modules or with a master; RS-485/Modbus RTU is a candidate | Protocol/master not written; autonomous trips and series contacts do not depend on communication (`0024`, I-086) |

## What it must not do

- Allow the machine to run when the unit itself has failed.
- Report a temperature it is not confident in.
- Depend on the isolation barrier for mains-level separation. It is not
  qualified for that.
- Treat potential-free contacts as unlimited ratings; REV A2 permits low-voltage loads only.

## Response time

The trip must happen within **1 s** of the setpoint being crossed. The existing
eight-channel timing budget is in `I-013`; physical timing is unmeasured.
The three-module installation needs contact/load timing verified; communication
is not in the selected shutdown path. Watchdog timing still needs work (I-097).

## Explicitly out of scope for now

- Certification to IEC 61010 / IEC 61508.
- 4-20 mA or 0-10 V analogue output.
- Any IoT or cloud path. RS-485 to a local master only.

## Isolation and installation questions

The existing board's eight thermocouples share one isolated island. That isolates
the group from the controller but **not the channels from each other**.
Three independent modules are selected; that does not validate probe grounding.

Accepted, and the reasoning is now on record correctly in
`docs/decisions/0009-operating-environment-corrected.md`: the eight sensors sit
on one engine block, so channel-to-channel differences are small, and there is
no VFD injecting common-mode current into the frame. `0003` reached the same
answer from a wrong premise and is superseded; `0008` over-corrected from
another wrong premise.

Still to be confirmed before the unit is trusted:

- Measure the potential between the sensor sheaths and the panel ground with the
  engine running and while cranking (`I-004`).
- Verify the probable grounded junction against its actual model/continuity;
  ungrounded probes can also measure temperature (`0029`, I-026).
