# 0038 - Thermocouple type K or J, chosen per channel, firmware only

* Status: accepted (owner, 2026-10-14)
* Date: 2026-10-14
* Builds on: `0037` D2 (one firmware for the family; K/J per channel "to study"), `0032` (front end, gain 32)

## Context

The owner asked whether the boards can read type J as well as type K. Commercial engine scanners do:
Murphy TDXM (24 ch, J or K), Altronic DPYH-4300 (J or K, set from the front keypad), Axiomatic
AX185001 (20 ch, per channel J/K/B/E/N/R/S/T), Advantech ADAM-4018+ (per channel, "+" model only).
Reviewed read-only 2026-10-14 by Codex gpt-6.1-sol, then gpt-6-astra (high), who agreed with the hardware
conclusion and tightened D2.

## Decision

**D1 - Every board of the family (8 / 24 / 40 ch, `0039`) reads K or J, chosen per channel in the saved
settings. No hardware change**, including the 24-ch REV A3 already being ordered.
* Thermocouples are measured against the AD7124 internal 2.5 V reference (REF3030 on REFIN1 is the
  independent diagnostic check, `0032`), so gain 32 gives +/-78.1 mV; J spans -8.095 mV (-210 degC) to 69.553 mV (1200 degC), so it fits.
  Protection, bias, isolation and the TMP126 cold junction are type-independent.
* The board measures E(tip) - E(CJ); the firmware converts with the **same type's** table for the
  cold junction and the tip. Errors quoted in degC in `0032` used K's 41 uV/degC; J (~52-55 uV/degC)
  turns the same microvolts into fewer degrees.

**D2 - A wrong type setting is the hazard, and the settings are guarded against it.**
K probe set as J reads low: K 500 degC = 20.644 mV reads ~378 degC (CJ 0 degC) - a missed trip.
J probe set as K reads high (J 400 degC = 21.848 mV reads ~528 degC) - a nuisance trip.
A cold engine gives no clue (tip = CJ, EMF ~0). So: the type is changed only under the settings lock,
with RUN inhibited and a confirm screen, saved together with its setpoint in the existing A/B records
(checked for type, channel, range and record version, not only CRC); old samples are discarded; the type letter shows beside every reading; a corrupt or unknown setting
inhibits RUN, never falls back to K silently; a changed type needs its setpoint reconfirmed and ACK;
Modbus may read the type, not write it; commissioning heats each probe well above the cold junction with a known source,
checks polarity, shows the trip contact opening, and records channel, type and extension cable.
Setpoints are bounded by the installed probe's rating, not the table end (J tables reach 1200 degC,
typical J service ~750-760 degC, WIKA).
* Per bank instead of per channel was considered (Astra): fewer settings, but one mistake then hits 8
  channels and wiring is constrained - not safer. Kept per channel.

**D3 - Extension cable matches the probe type:** KX for K, JX for J (IEC 60584-3 colours: K green,
J black). Goes on the installation drawing (I-085, I-093).

## Rejected

* Jumper/DIP per channel or per bank: can be mis-set too, needs MCU pins or shift registers and room;
  per bank forces 8 channels to one type.
* Detecting the type from loop resistance: 50 m extension cable of unknown gauge gives no unique signature.
* Two firmware images (K and J): the wrong one gets programmed; mixed installations impossible.
* More types (T, E, N, R, S, B): each one adds commissioning and fault-validation work for no
  current need (AGENTS rule 7). Electrically they fit; revisit on request.

## Consequences

* GOAL, AGENTS and `hardware/24ch/README.md` say K or J.
* The firmware chat (branch `firmware`) takes D1-D2 into the 24-ch firmware; the owner briefs it.
  Codex's review notes for it: 5 degC table steps (K max ~0.48 degC interpolation error over
  -270..1372, J ~0.04; both < 0.02 above 0 degC; UNVERIFIED until checked on the real quantized tables),
  ~2.5 KB flash, burnout response checked against normal EMF and cable resistance, open-sensor/burnout windows per type,
  negative EMF is normal (the "reversed polarity" wording in `0032` rev 4 is wrong, I-119 is right).
