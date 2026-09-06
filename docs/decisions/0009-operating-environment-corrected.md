---
status: accepted
date: 2026-09-07
deciders: Zain, Claude
amends: 0003, 0008
---

# The operating environment, corrected

## Context

Two facts in the project record were wrong. Both came from agents assuming
rather than asking, and both were corrected by the user on 2026-09-07.

| Recorded | Actual |
|---|---|
| Eight sensors on the same cylinder | Same engine, **eight different cylinders** |
| A motor/VFD panel | **An engine.** There is no VFD anywhere |
| — | The unit lives in **its own panel**, 50 m of cable away from the engine |
| — | The sensors read **cylinder body** temperature, not exhaust gas |

`docs/GOAL.md` R-7 still says *"Survive a motor/VFD panel and 50 m cable runs"*.
That file is owned by the user, so it is flagged here rather than edited.

## What this settles

**Vibration and ambient temperature are not design constraints.** The board is
in a dedicated panel, not on the engine. The DIP-40 socket, the relay, the
radial electrolytic and the DC-DC modules are all fine where they are. This
removes what would otherwise have been the most serious mechanical problem on
the board - a socketed microcontroller on an engine walks out of its socket.

**The shared isolated island suits this application well.** All eight sheaths
bond to one engine block, so channel-to-channel differences are small. The
island floats up to engine-block potential as a whole and the isolation barrier
carries the difference between the engine and the panel - which is exactly the
job it was designed for. `0003` reached the right answer for the wrong reason;
`0008` over-corrected on a premise that was also wrong.

**Ungrounded probes drop from blocker to insurance.** Worth specifying if the
supplier has them, because they remove the cranking-current path for free, but
they no longer gate the design. `I-026` is downgraded accordingly.

**The setpoint is a stored, operator-settable value.** The user is explicit that
it must not be hard-coded and must survive a power cycle so the engineer can set
it on site. That is `I-012`, and it is a stated requirement rather than a
nice-to-have.

## What is still open

**Where the 24 V comes from is undecided, and it changes the input protection.**

- *A 24 V supply in the panel, off the mains.* The present protection - 0.5 A
  PTC, SS34 series diode, SMBJ33A clamp, TSR 1-2450 - is adequate. No change.
- *The engine's own battery and alternator.* It is not. Load dump on a 24 V
  system reaches 60-120 V; the SMBJ33A clamps near 53 V and the TSR 1-2450 is
  rated to 36 V input, so the regulator sits below the clamp and would be
  destroyed. That case needs a wide-input regulator - the Recom R-78HB series
  runs 9-72 V and KiCad already carries the footprint - plus a clamp chosen
  under its ceiling. Tracked as `I-028`.

The barrier still has to be measured (`I-004`), and no EMC or real-sensor
testing has been done. Neither is changed by any of the above.
