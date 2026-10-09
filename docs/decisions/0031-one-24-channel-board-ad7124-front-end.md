# 0031 — One 24-channel board, AD7124-8 front end, single-source parts

* Status: accepted (owner, 2026-10-08). Engineering items marked "design" or
  "verify" are still open.
* Date: 2026-10-08
* Deciders: owner; front end reviewed adversarially by Codex gpt-6.1-sol
  (read-only, `production/review-20261008/codex-frontend-review.md`, local)
* Supersedes: `0030` D1, D1a, D3, D4, D4a, D6, D7 and its W3 work item.
  `0030` D2 (comms never in the trip path), D5 (signal relay) and D8 (per-channel
  setpoints, timing) still apply. Partly supersedes `0024` (three modules).
* Relates to: I-101, I-102, I-091, I-092, I-093, I-094, I-095, I-096, I-097,
  I-078, I-081, I-085, I-090, I-100; `0020`, `0028`, `0029`

## Why the plan changed the same day

`0030` kept 8x MAX31856 per module. The probes are made to order and their
junction type is unknown and may be mixed (I-101). With grounded probes the
engine joins every T- line, and the MAX31856 BIAS outputs then fight (ADI
guidance: T- of several MAX3185x must not be joined; `CALCULATIONS` 6.1).
Commercial instruments that accept both probe types connect **one probe at a
time to one converter** (Murphy TDXM, 24 channels; NI 9213, 16 channels with
high-value bias to COM; `reference/benchmarks/murphy-tdxm/`).

Once the front end is a multiplexed converter, two of the reasons `0030` gave
for rejecting one 24-channel board disappear: there are no 24 BIAS sources on
one island, and the channel design is new on either path.

## Decisions

**D1. One 24-channel board** (owner, 2026-10-08), replacing three stacked
modules. One MCU, one power stage, one trip relay, one display and keypad. No
inter-module RS-485, master role, stack header, ACK fan-out diodes or address
jumpers. A standalone 8-channel unit is the same PCB with one acquisition bank
fitted, its channel count fixed at the factory and locked; a missing required
channel trips.
* Accepted cost (Codex Q6): a welded trip contact or an undetected MCU fault
  now affects all 24 channels instead of 8 (I-081 scope grows). A second relay
  in series can be added later if the owner wants it.

**D2. Front end: 3x AD7124-8 on one isolated island, scanning concurrently.**
Each converts 8 differential channels through its internal mux (16 AIN pins,
all used). One AD7124 for 24 channels would take 24 x 41.8 ms = 1.0 s before
diagnostics, so it is rejected (Codex Q6b). Rejected: per-channel isolation
(8 converters + 8 isolated supplies per bank; Codex Q5), LTC2983 (167 ms per
channel), ADS124S08 (6 pairs, narrower input window at gain 32; Codex Q5).
Required changes from the review, to be designed before the schematic:
* **Common-mode reference:** each TC- biased through a high value (order of
  10-39 Mohm) **plus one protected reference wire** from the island to the
  engine at mid-rail, not AVSS. Every mix of probes must work, including all
  insulated, and losing the reference wire or the last grounded probe must not
  read plausibly. The leakage budget (~38 nA for 1.5 V at 39 Mohm) includes
  protection, board and connector leakage. Common-mode recovery after burnout
  (39 Mohm x 20 nF = 0.78 s) limits the filter capacitors.
* **Input protection redesigned:** the REV A2 BAV199 rail clamp allows ~4.2 V
  against the AD7124's AVDD + 0.3 V = 3.6 V absolute maximum.
* **Cold junction:** a sensor next to each terminal group, not the ADC die
  sensor (CN-0391 uses local RTDs). K-type NIST functions in firmware, done in
  voltage, not by adding temperatures.
* **Diagnostics every scan:** SPI CRC and register read-back, device ID and
  silicon revision, channel tag and fresh-data checks, error register, MCLK
  counter, zero and non-zero checks through the gain used, and a reference
  check against an **independent** quantity (a reference-derived ladder cannot
  see reference drift; a 2 % rise reads ~10 °C low).
* **Timing:** 25 SPS single-cycle settling is ~42-43 ms per switched channel
  (Rev B Table 61), so 8 TC + 2 checks is ~0.47 s per bank, the three banks in
  parallel. Burnout is tested on **one channel per scan in rotation**, so each
  channel is checked about every 4 s (owner: acceptable, 2026-10-08). Burnout
  readings are never used as temperatures. The firmware loop must service the
  ADCs faster than the 50 ms loop delay, and the watchdog follows I-097.
* **Known limit:** a wire-to-wire or wire-to-sheath short can read plausibly
  on any two-wire thermocouple front end, including per-channel isolation.
  R-6 is amended to say so.

**D3. Processor: ATmega32A class is enough** (Codex Q6c: 24 conversions per
scan ~30 ms estimated; present image 5918 B flash, 437 B static RAM). Prefer a
pin-compatible ATmega644PA or ATmega1284P (same code, 2-8x memory) **if** stock
and footprint check out at the single source (D6). Murphy's board uses a
44-pin Microchip 8-bit MCU for 24 channels (inferred from photo-2).

**D4. Operator interface on the board** (owner, 2026-10-08). The panel door
is not modified.
* **20x4 character LCD** (HD44780-compatible, 16-pin header) on standoffs above
  the board; no tall parts under it. **Bought locally in Egypt** (owner,
  2026-10-08): LCSC had no 20x4 in stock (HS204A C5329590: 3 pcs). It plugs into
  a header and is screwed on, so it is not part of the factory assembly. This is
  the one agreed exception to D6. Rejected: 128x64 ST7920 from LCSC (8 lines, but
  needs a framebuffer and more firmware).
* **Five buttons beside the LCD:** UP, DOWN, SET (enter/save), ESC, and a
  larger or differently coloured **ACK**.
* Still to ask the operations engineer: is opening the door to read the
  display and press ACK acceptable?

**D5. Outputs.** One **trip** relay (energised-to-run, `0030` D5) and one
**alarm** relay of the same signal type (owner, 2026-10-08), for warnings that
must not stop the engine: open thermocouple, approaching limit. Whether an
open thermocouple trips or only alarms is a firmware setting; its default is
still to be chosen (owner said alarm-only is acceptable). Both contacts:
30 VDC / 1 A maximum, signal loads only.

**D6. All parts from one source** (owner, 2026-10-08). The board will most
likely be made and assembled by NORI, who probably order from abroad. Every
part, including terminals, LCD and buttons, must come from **one catalogue**
with stock, so nothing needs a separate search or shipment. The owner recalls
that NORI buys parts, and has boards above two layers made, **in China**, so
**LCSC is the primary catalogue**. As a fallback each part should be stocked at **LCSC and at one
global distributor (DigiKey or Mouser)**: then the BOM works whichever route
NORI buys through. A part found only at one of them is flagged in the BOM. This rules out
special imports such as Phoenix FRONT-MC terminals and Newhaven displays
unless that catalogue stocks them.

**D7. RS-485 / Modbus RTU fitted** (owner, 2026-10-08) so the board can send
readings to a PLC/SCADA and take commands. **Isolated**, because the far end is
outside this board's ground: ADM2587E as in REV A2 (LCSC C12081, 6,979 pcs
2026-10-08; ~120 mA, into I-096); Chipanalog CA-IS2092W (C5121950) is a cheaper
alternate to evaluate. It is never in the trip path: no message can grant RUN,
clear a trip or bypass protection, and comms loss never grants RUN. Remote
setpoint writes, if allowed at all, need CRC, read-back and a local enable
(jumper or menu lock); to be specified with the protocol.

**D8. Cable shield bonded at panel entry** to a ground bar, not on the PCB.
Each thermocouple then needs two terminals (48 in total), pluggable 3.81 mm
blocks, possibly in tiers as on the Murphy board. Plus cold-junction sensors
at each terminal zone.

**D9. Mounting:** the board on standoffs on a metal plate in the panel, with
screws. Not DIN rail.

**D10. Board size is set by a to-scale floor plan**, not assumed. 100 x 100 mm
is not expected to hold 48 TC terminals, power and relay terminals, a 20x4
LCD (~98 x 60 mm) and five buttons. The first concept floor plan (2026-10-08,
placeholder blocks) came out at 170 x 130 mm; v1 with the `0032` parts is
170 x 120 mm, 4 layers. The floor plan is shown to the owner before any board write.

## Work split now

| Worker | Does |
|---|---|
| W1 Claude workstation | Floor plan, front-end design, schematic and board (only hardware writer) |
| W2 Codex | Calculations (fuse I-102, power I-096, front-end numbers), firmware core |
| W3 cloud | **On hold.** The RS-485 master/display task is cancelled |

## What could still go wrong (and how it is caught)

* A part goes out of stock between design and order: dated stock check at the
  single source before ordering, alternates named in the BOM.
* Assembly capability: AD7124-8 is a 5 x 5 mm LFCSP; confirm NORI assembles
  it, otherwise the order fails.
* Engine ground voltage during cranking is unknown: owner measurement
  requested (DC and AC, between distant probe locations and to battery
  negative).
* Grounded/insulated/mixed behaviour is proven only on the bench: build the
  first small batch, test all mixes and a cut wire, before machine use.
* Engine-room humidity, oil and vibration: **washing and conformal coating are
  mandatory** (`0032` rev 3, I-105); locking
  connectors to be decided.
