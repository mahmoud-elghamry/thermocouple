# 0035 - I-111 layout repair: which part gets the spot next to the pin

* Status: accepted (engineer's call; owner delegated the layout repair in `0034` D3 and asked on
  2026-10-11 to work the P0 list through without stopping)
* Date: 2026-10-11
* Builds on: `0034` D3 (local repair, no regeneration); gate `hardware/24ch/gen/pincaps.py`

## Context

Moving every decoupling cap beside its pin is local, but the space beside a pin is often
already taken by another part or by routed copper. Each such conflict needed a choice.
Tools written for this: `gen/move.py` (move named parts, drop only their tracks),
`gen/capnear.py` (search a spot within N mm of a pin, score collisions, optional rip of
the signal tracks in the way, plane via beside a pad), `gen/buck24.py` (the LM5164 stage,
recorded as a script like the 8-ch `powerstage.py`).

## Decisions

**D1 - Every AD7124 bypass pin is equal: supplies, regulators and REFOUT.** The thermocouples
convert on the internal reference (`0032` "Converters, reference"), so REFOUT's 100 nF is part
of the measurement, not an unused pin; an early attempt that moved C191 away to make room
for AVDD was reverted. The gate covers AVDD (26), IOVDD (2), REGCAPA (24), REGCAPD (1) and
REFOUT (22) on all three ADCs.
* The ISO7761 island-side cap C408 swapped places with R402 (33 ohm SCLK damping): the cap
  must sit right of pin 16, the resistor can sit under pin 15 with no crossing.

**D2 - Analog input traces are never ripped to make room.** Thermocouple pairs (TC*) keep
their symmetric routes; only digital nets (SCLK, DIN, DOUT, CS, LCD, REFTEST, buttons) are
lifted and re-routed by `maze.py`. A spot that needs a TC track moved is not used.

**D3 - No via inside an SMD pad** (solder wicks down the hole). `maze.py` and `capnear.py`
now refuse it; two found (C408, C505) were removed. The exposed-pad thermal vias of the
AD7124/LM5164 are the only vias in pads, as before (`I-110`).

**D4 - Crystal moved to the XTAL pins (I-121).** Y501 sat ~25 mm away on the other side of
U501, traces under the chip on B.Cu. Moved left of U501 with C501/C502 between it and pins
7/8, traces on F.Cu only: XTAL1 ~8 mm, XTAL2 ~13 mm (C503, the pin-5 VCC cap, keeps the
straight path). Rejected: a 3225 crystal (smaller, would fit closer) - a part change for the
next revision, not needed to pass.

**D5 - The FB check counts the divider resistor.** The LM5164 FB network is R602/R603 at
FB; `pincaps.py` measured only capacitors. Limit unchanged (5 mm).

**D6 - AD7124: the rule follows how each pin is connected (owner, 2026-10-11: "the easiest
solution, even if we change decisions").** The 3 mm rule could not be met around the three
AD7124s without re-routing the SPI bus through the thermocouple area (tried twice, reverted).
* AVDD and IOVDD sit on the +3V3_ISO plane (In2) over the GND_ISO plane (In1): the current path
  is pin - via - plane - via - cap, so what counts is a via beside the pin and beside the cap.
  Gate: own via within 1.5 mm of the pin and of a cap no farther than 12 mm. Result: all six pass.
* REGCAPA, REGCAPD and REFOUT are single traces (no plane), and REFOUT is the reference the
  thermocouples convert against: a long trace picks up the SPI clock and may upset the internal
  regulators. Gate: 5 mm (was 3). Result 2.3-4.3 mm after moving C391-C393 (U301 above/right of
  the ADC) and swapping C193/C197, C293/C297 in the cap rows (REGCAPD 9 -> 3.3 mm).
* Rejected: 3 mm everywhere (re-routes the SPI bus around each ADC by hand, hours, risk to the
  TC traces); no limit (REGCAP/REFOUT at 9-12 mm is a real noise/stability risk).
* Bench check: reference and regulator noise is part of I-120.

## Consequences

* `pincaps.py` checks all five AD7124 bypass pins on each ADC (D6) and is a release gate in `fab.py`.
* A generic rip-up around the AD7124 failed (DOUT_ISO re-routed to 168 mm, three nets
  unroutable) and was reverted from `output/bak/thermo24-20261011-before-adc.kicad_pcb`;
  the ADC neighbourhoods are re-laid by hand coordinates instead.
