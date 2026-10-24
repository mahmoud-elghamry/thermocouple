# Goal and requirements

**Owner: the user.** An agent may propose a change here but must not rewrite it
alone. Changes go through `docs/decisions/`. Status column synced to `0031`-`0034`
2026-10-11 at the owner's request.

**Keep under 120 lines.**

---

## The goal

A system that reads **24 thermocouples, type K or J chosen per channel** (`0038`), on **one 24-channel board**
(owner, 2026-10-08, `decisions/0031`; replaces three modules, `0024`). Any channel
trip opens the potential-free shutdown contact. The owner added (2026-10-14, `0037`) an
8-channel option and a 40-channel board in the same family: same architecture, 1 or 5 banks; the 40-ch also
reads 3 three-wire PT100 points on a bank of their own, with a check resistor (`0039` P5).

It is going onto real equipment. It is not a demonstration.

## Where it runs

Earlier eight-channel installation basis, corrected 2026-09-07. The 2026-09-29
24-channel clarification supersedes the system count; do not extrapolate the
old one-engine/one-probe-per-cylinder mapping to all 24 channels.

| | |
|---|---|
| The machine | Earlier basis: one eight-cylinder engine, no VFD. Common series shutdown for all 24 confirmed; physical sensor/engine mapping remains unconfirmed |
| The sensors | K-type today, J also accepted per channel (`0038`); probably grounded-junction (owner, 2026-10-07), not verified. Earlier basis: cylinder bodies; exact model and 24-channel mapping unconfirmed |
| The unit | Same panel or nearby; shielded twisted extension cable of the probe's type (KX for K, JX for J, `0038` D3), roughly 50 m basis accepted (`0029`); exact cable/termination to be specified |
| Vibration and heat | Existing basis is a separate panel; moving acquisition onto/near the engine requires a fresh environmental assessment |
| The 24 V supply | Engine battery per accepted decision `0016`; surge qualification remains open (I-028/I-077) |

For the existing eight-channel same-engine basis, the shared isolated island
floats with the probe group and the barrier separates it from the controller.
That rationale must be rechecked if channel assignment spans different machines.

## What it must do

| # | Requirement | Status |
|---|---|---|
| R-1 | Read 24 thermocouples, type K or J per channel, grounded, insulated or mixed | J is firmware only (`0038`). One board REV A3, 3x AD7124-8 (`0031`, `0032`): schematic and routed board exist, layout repairs open (`docs/ISSUES.md` P0); not built or tested |
| R-2 | Open the common potential-free dry-contact circuit when any channel exceeds its own setpoint | Trip relay G6K-2F-Y, both NO poles in series (`0032` rev 3); signal loads only, 30 VDC / 1 A (I-092); per-channel limits are 24-ch firmware (I-100); I-081 accepted limit |
| R-3 | Energised to run — power loss, reset or fault must stop the machine | Relay held only by a heartbeat from completed scans (I-118); single-fault limits in I-081 |
| R-4 | Show readings, channel limits and state locally | 20x4 LCD on standoffs on the board, five buttons plus a header for panel buttons (`0031` D4, `0034` D2); per-channel editing is firmware (I-100) |
| R-5 | Latch startup/reset/trip until manual ACK with valid, cool channels | Owner reconfirmed 2026-10-07 (`0029`, I-089 closed); per-channel reset checks pending I-100; I-073 fixed |
| R-6 | Detect a broken sensor (each channel checked about every 4 s) | **Open sensor trips by default**; "alarm only" is a deliberate, saved per-channel setting the display shows (owner 2026-10-09, `0034` D1; replaces `0031` D5's open default). Wire-to-wire or wire-to-sheath shorts can read plausibly on any two-wire front end; see `I-011` |
| R-7 | Survive an engine installation and 50 m cable runs | **not proven — needs measurement** |
| R-8 | Each channel has its own operator-settable persistent setpoint; values chosen at commissioning | Accepted 2026-10-07 (`0029`); the 24-ch firmware is not written yet; the 8-ch firmware has one shared limit (I-100) |
| R-9 | Communication with a PLC/SCADA master | Isolated RS-485 / Modbus RTU fitted on the board (`0031` D7, I-094; owner 2026-10-14 keeps it fitted, reversing `0036` D2); protocol not written; never in the trip path (I-086) |

## What it must not do

- Allow the machine to run when the unit itself has failed.
- Report a temperature it is not confident in.
- Depend on the isolation barrier for mains-level separation. It is not
  qualified for that.
- Treat potential-free contacts as unlimited ratings; they carry low-voltage signal loads only (30 VDC / 1 A).

## Response time

The trip must happen within **2 s** of the setpoint being crossed (owner 2026-10-20: the same as the
market reference, Murphy TDXM-DC: "Scans all channels in 2 seconds", tripped set points "detected within two
seconds" - fwmurphy.com/product/tdxm, checked 2026-10-23; a sheathed probe itself takes seconds). No tighter
self-imposed target (owner 2026-10-23): the 24-ch firmware estimate is ~0.75 s normal, ~1.1 s worst (`firmware/spec/04` 6.3). The 24-ch
scan is ~0.62 s for 14 slots (I-119); contact timing is measured at the bench
(I-013, I-120). Communication is not in the shutdown path. Watchdog timing:
I-097, I-118.

## Explicitly out of scope for now

- Certification to IEC 61010 / IEC 61508.
- 4-20 mA or 0-10 V analogue output.
- Any IoT or cloud path. RS-485 to a local master only.

## Isolation and installation questions

All 24 thermocouples share one isolated island. That isolates the group from
the controller but **not the channels from each other**; accepted because all
24 are on one engine (owner, `0031`). A probe on another machine needs a fresh review.

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
