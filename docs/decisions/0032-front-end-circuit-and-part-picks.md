# 0032 — Front-end circuit and first part picks for the 24-channel board

* Status: **accepted, revision 4** (2026-10-08): revision 1 after Codex reviews, then
  revisions 2-4 at the end of this file, which override the text above them. The 24-ch
  schematic implements revision 4; every "check" not closed in `ISSUES.md` is still open.
* Relates to: `0031` (architecture), I-101, I-103, I-091, I-093, I-094, I-095,
  I-096; Codex review `production/review-20261008/codex-frontend-review.md`
* Sources: AD7124-8 Rev B (LCSC C97314 PDF), local datasheets, LCSC stock read
  2026-10-08 in the browser

## Per-channel input (x24)

```
TC+ ──┬────────── R_s 1k ──┬────────┬──── AIN(2k)
      │                    │BAV199  │ C_cm 1n C0G to AVSS
      │                    │        ├── C_d 10n C0G ──┐
TC- ──┼── R_b 20M to V_mid │        │                 │
      └────────── R_s 1k ──┴────────┴──── AIN(2k+1) ──┘
```

* **R_b = 20 Mohm from each TC- terminal to V_mid**, on the terminal side of R_s,
  so the bias current does not flow through R_s. 39 Mohm was dropped: LCSC
  stocks 99 pcs at 33 M and 54 pcs at 39 M, but 245,086 at 20 M (FRG0805F2005TS,
  C3013337, 1 %).
  * Grounded probes, 100 mV between cylinders: I = 0.1 / 20M = 5 nA; error
    = 5 nA x 50 ohm assumed TC- lead = 0.25 uV = 0.006 degC (41 uV/degC).
  * Floating probe: common-mode shift = (I+ + I-) x R_b = 2 x 3.3 nA (AD-B p.7
    typ, full power) x 20M = 0.13 V. Leakage budget for 1.5 V headroom:
    1.5 / 20M = 75 nA per channel (was 38 nA at 39M).
  * Common-mode recovery after burnout: 20M x 2 x 1 nF = 40 ms (was 0.78 s
    with 10 nF C_cm at 39M, Codex Q2).
* **R_s = 1 kohm per leg** (0805, 1 %): limits clamp current. ADC input
  current mismatch error <= 3.3 nA x 1k = 3.3 uV = 0.08 degC worst, typically
  far less. Check: AD-B input current max over temperature.
* **Clamp: BAV199 per leg** to AVDD and AVSS, after R_s (low leakage, pA-nA;
  Nexperia 5 nA max at 75 V, 25 degC). **Check:** REV A2's code C5184419
  (15,280 pcs) is an **HXY MOSFET** BAV199, not Nexperia; its leakage must be
  read from the HXY datasheet, or a Nexperia code found. HXY datasheet (LCSC
  PDF, read 2026-10-08): IR 5 nA max at 70 V, 25 degC; VF 0.9 V at 1 mA; no
  high-temperature leakage figure, so measure it at the bench or prefer Nexperia. A Schottky clamp was rejected: its
  reverse leakage at 85 degC is microamps, which breaks the 75 nA budget.
  Codex Q1c: BAV199 lets the node reach ~AVDD + 0.9 V at 1 mA against the
  AD7124's AVDD + 0.3 V. The AD7124 also rates **AINx input current 10 mA**
  absolute maximum (AD-B p.13, Table 4). **Check:** whether a second series
  resistor (1k) between the clamp node and the AIN pin is needed so the
  internal diode never carries more than its allowance; leaning yes, it costs
  48 resistors.
* **Filter:** C_d 10 nF C0G across the pair, C_cm 1 nF C0G each leg to AVSS
  (was 100 nF / 10 nF). Burnout charge time to gain-32 full scale:
  (10n + 1n/2) x 78 mV / 0.5 uA = 1.6 ms. RFI corner 1/(2 pi x 2k x 10.5n)
  = 7.6 kHz; 50/60 Hz rejection is the AD7124's digital filter.
* **Gain 32**: full scale +/-2.5 V / 32 = +/-78 mV covers K-type to ~1370 degC.
  High-gain CMR window at 3.3 V: 0.116 to 3.184 V (AD-F Table 3 note 8), i.e.
  about +/-1.5 V around V_mid.
* No TVS on the thermocouple inputs: any practical TVS leaks microamps.

## Common-mode reference

* **V_mid = AVDD/2** from a 2 x 100k divider with 100 nF to AVSS (Thevenin
  50 kohm; the 24 R_b in parallel are 0.83 Mohm).
* **Engine reference terminal:** V_mid -> 10 kohm -> one terminal, wired to the
  engine block with its own wire. The island then sits at engine - 1.65 V and
  grounded probes land at mid-rail. **Check:** surge/ESD on that wire, the
  transient through barrier capacitance, and what happens if the wire is
  missing (Codex Q1a, Q1d). No spare AIN pin is left to monitor it.

## Converters, reference, cold junction

* **3x AD7124-8BCPZ** (C97314, 3,576; C578388 RL7, 4,450), full power, internal
  clock, 25 SPS single-cycle, gain 32, buffers on.
* **External reference REF3025-class 2.5 V on REFIN1 of all three** (pins 12/13,
  dedicated, not AIN). Thermocouples convert on the internal reference; once
  per scan each ADC converts **its internal reference (mux code 10010) against
  REFIN1**. Two independent references disagreeing beyond tolerance = trip.
  Also per scan, in rotation: AVSS-AVSS zero, (AVDD-AVSS)/6, temperature
  sensor vs. cold-junction sensor. Part: **REF3025AIDBZR** (TI, 0.2 %, SOT-23;
  C11334, 24,271); ADR3425ARJZ (C60864, 2,613) if tighter drift is wanted.
* **Cold junction: 3x ADT7310TRZ** (ADI, +/-0.5 degC, SPI, SOIC-8;
  C578060 REEL7 967 pcs), one at each terminal bank, on the island.
* **Scan per ADC:** 8 TC + 1 burnout slot (one channel per scan, rotating) +
  1 diagnostic slot (rotating) = 10 x 43 ms = 0.43 s, 0.45 s at -5 % clock;
  the three ADCs run in parallel. A channel's burnout slot follows its normal
  reading, so the next normal reading is ~0.4 s (10 x the 40 ms recovery) later.

## Island power and isolation

* **Isolated DC-DC: B0505XT-1WR3 class, SMD** (YLPTEC C42389632, 10,101) or
  SIP-4 B0505S-1WR2 (YLPTEC C2992393, 9,044; EVISUN C7503641, 4,090; same
  pinout as REV A2's IA0505S, which LCSC does not list). Then LP2985-3.3
  (C129375, 3,424) -> AVDD and, through a ferrite, IOVDD.
* **Minimum load** (Codex, `CALCULATIONS` 7.1): a 1 W unregulated module needs
  ~20 mA (10 %), the island draws ~12 mA, so its output can rise toward 6 V.
  Proposed: a **270 ohm 1206 preload** on the module output (5.5 V / 270 =
  20 mA, 0.11 W; inside the 0.50 A envelope), unless a module specified at
  ~12 mA is found. Check against the chosen module's datasheet.
* **Digital isolators: 2x ISO7761DWR** (C2871529, 351) = 10 forward / 2 reverse.
  Forward: SCLK, DIN, 3 ADC CS, 3 CJ CS = 8. Reverse: shared DOUT = 1.
  ISO7760 dropped (73 pcs). ADT7310 (Rev A datasheet, timing table): DOUT
  data out on SCLK falling edge, valid on rising (SPI mode 3, as the AD7124);
  its t10 is quoted as the "true bus relinquish time", which implies DOUT
  releases after CS rises. **Check** that wording against the pin table.

## Control side (24 V)

| Block | Part | LCSC, stock 2026-10-08 |
|---|---|---|
| MCU | ATmega1284P-AU, TQFP-44 (pins as ATmega32A, 16 KB RAM) | C33575, 1,943 |
| Buck | LM5164DDAR + L1 SMDRH104R-330MT (kept from REV A2) | C477928, 12,579; C9936, 5,965 |
| Surge | SMBJ60A (D2) | C49066953, 5,350 |
| PTC F1 | 1812L075/60GR is **out of stock**. Requirement (`CALCULATIONS` 7.3): hold > 0.52 A at max ambient, >= 58 V. Candidates, both 60 V / 0.75 A hold, 2920: Bourns MF-SM075/60-2, Littelfuse 2920L075/60MR; hot hold derating to check | C210842, 10,495; C207083, 2,960 |
| Relays x2 | G6K-2F-Y-TR DC24 (trip, alarm) | C5278023, 13,908 |
| RS-485 | ADM2587EBRWZ (isolated), alt. CA-IS2092W | C12081, 6,979; C5121950, 1,074 |
| Buttons x5 | TS665CJ (kept) | C393938, 141,250 |
| TC terminals | Kangnex 3.81 mm 8-pos header + plug, 6 of each (2 per bank) | C14235, 20,855; C14234, 13,798 |
| Power/relay/RS-485 terminals | Kangnex 5.08 mm (kept) | C8270, C192769 |
| LCD | 20x4 HD44780, bought locally (`0031` D4); 16-pin header (kept) | C7501270 |

Everything else (passives, crystal, LEDs) is carried over from REV A2 and is
re-checked at BOM time.

## Rejected here

* Schottky input clamps (leakage), TVS on TC inputs (leakage), 39 Mohm bias
  (stock), ISO7760 (stock), ADC die sensor as cold junction (Codex Q4), one ADC
  for all 24 (`0031`).

## Revision 1 after Codex's reviews (2026-10-08)

Codex reviewed this file (`production/review-20261008/codex-0032-review.md`)
and floor plan v1 (`codex-floorplan-review.md`), both local. W1 accepts the
following; each overrides the text above where they differ.

1. **Protection, per leg:** TC terminal -> **R1 2.2 k pulse-rated** -> clamp
   node with **Nexperia BAV199,215** (C40919, LCSC marketplace; HXY C5184419 has
   no hot-leakage figure) to AVDD/AVSS -> **R2 1 k** -> AIN; C_d and C_cm on the
   ADC side; R_b stays on the terminal side. Typical input-current error
   1.5 nA x 3.2 k = 4.8 uV = 0.12 degC. **DC miswire survival (e.g. 24-30 V on a
   TC terminal) stays out of scope** (I-080, owner). Transient energy: ESD
   charge goes into the AVDD bulk capacitance (e.g. 150 pF x 8 kV = 1.2 uC into
   10 uF = 0.12 V); sustained injection must stay below the island's own load
   (~12 mA) or AVDD rises, so a relative shift of a few volts on a few channels
   (about 1 mA per leg) is tolerated, and an input outside the common-mode
   window is a fault, not a reading. No AVDD crowbar for now; to re-check at
   the bench (rule 7). ADG7421F fault-protection switches were rejected as cost
   and complexity for a fault we do not design for.
2. **Reference check:** **REF3030AIDBZR (3.0 V, C38423, 26,748)** on REFIN1,
   internal 2.5 V reference measured against it at **gain 1** (ratio 0.8333,
   not full scale). Provisional threshold +/-1.6 % (budget 1.43 %, Codex R5).
   100 nF on each REFIN and REFOUT; the three REFOUTs never joined.
3. **V_mid buffered:** 2 x 100 k + 100 nF divider -> **MCP6001** (C116490
   Microchip, 1,300; TLV9001 is marketplace-only) -> 47-100 ohm -> V_mid;
   engine-reference terminal through **2 x 4.99 k pulse-rated**.
   **No continuity sense wire:** a missing reference wire leaves the readings
   correct (the 20 M bias still centres the probes) and only reduces transient
   headroom, which the per-scan gain-1 common-mode check of every TC+ and TC-
   catches as a fault. Commissioning checks the wire. Re-open if the bench
   shows otherwise.
4. **Scan:** 8 TC + burnout + reference + zero + non-zero (internal 20 mV pair
   at gain 32) = **12 slots, 0.53 s** worst clock per bank, banks in parallel;
   supply and die-temperature checks in slower rotation; burnout per channel
   about every 4.2 s. Supply/6 at gain 1. Slot order and firmware details are
   recorded for later (owner: software later).
5. **Cold junction: two ADT7310 per bank** (6 in total) at the header seams,
   each covering 4 channels; thermal copper on the island.
   **Third ISO7761** so every chip select is direct (no decoder): forward
   SCLK, DIN, 3 ADC CS, 6 CJ CS = 11 of 15; reverse DOUT (with a 47-100 k
   island pull-up) + 2 spare. SPI mode 3, one CS at a time, 10 k CS pull-ups.
6. **Relays: G6K-2F-Y DC5 on the regulated 5 V rail** instead of DC24 on the
   battery. The 24 V coil's 150 % maximum (36 V) is exceeded by the 58 V
   load-dump basis, and a 5 V coil also holds through cranking dips. Cost:
   +2 x ~20 mA on 5 V (inside the 0.50 A envelope); stock is LCSC marketplace
   (C47190 TR, C326376). Driver and flyback re-checked in the schematic.
7. **Top terminals:** REV A2's C8270/C192769 are fixed 5.08 mm screw
   terminals, not plugs. Kept as fixed screw terminals for power, contacts and
   RS-485 (rarely unplugged); the floor-plan text that said "plugs" was wrong.
8. **Floor plan v2: 170 x 145 mm** (`production/review-20261008/floorplan-v2.png`):
   real REV A2 footprint sizes; 3 mm copper-free band on all layers; an
   isolated RS-485 pocket at its connector; isolated DC-DC at the top of the
   left barrier, ~26 mm from AD7124 #3; island mounting holes NPTH with
   insulating spacers, control holes plated chassis, 6 mm hardware keep-out;
   keypad column with 15 mm pitch and ACK apart; ISP, contrast and LEDs outside
   the LCD shadow. Taller button actuators are needed (LCD face ~24 mm above
   the board); 8-10 mm board standoffs to the plate; ~30 mm free beyond each
   wired edge in the panel. Size is final only after placement in KiCad.

## Revision 2 after Codex's short check of revision 1 (2026-10-08)

Codex (`production/review-20261008/codex-rev1-check.md`, local) passed items
2, 5, 7 and 8 and rejected 1, 3, 4 and 6. W1 agrees with all four and changes:

1. **AVDD sink, with a defined envelope.** The DC-DC preload moves from the
   module output to the 3.3 V rail: **150 ohm, 1206** (3.3 / 150 = 22 mA,
   73 mW). It satisfies the module's ~20 mA minimum load (island ~12 + 22 =
   34 mA) **and** is a guaranteed AVDD load: positive clamp injection up to
   22 mA in aggregate only reduces the LDO's output current; AVDD cannot rise.
   Example: one leg at AVDD + 5 V injects (5 - 0.9) / 2.2k = 1.9 mA, so about
   11 such legs at once. Beyond that AVDD rises and the AD7124 supply monitor
   and input OV flags must fault (diagnostic). LDO dissipation (5.5 - 3.3) x
   34 mA = 75 mW. Negative injection is drawn from AVSS and does not raise AVDD.
2. **Reference-wire continuity is sensed after all** (Codex R4 circuit): the
   ENGINE REF terminal has two positions, feed and sense, joined only at the
   engine. Sense -> protection -> 100 k to AVSS -> comparator (TLV7011 class,
   threshold ~0.6 V from an AVDD divider) -> spare reverse isolator channel.
   Connected: ~1.50 V; feed broken with all 24 grounded bias paths: ~0.18 V.
   A spare forward channel can pull sense low as a self-test. Cost: one
   comparator, a few resistors, one more terminal position. Comparator:
   **TLV7031DBVR** (TI, push-pull, SOT-23-5; C2869832, 93,680), since
   TLV7011 is marketplace-only.
3. **Schedule:** one rotating common-mode slot (gain 1, TC+ or TC- of one
   channel) is added: **13 slots, ~0.57 s** worst clock per bank; every input's
   common mode is checked about every 16 scans (~9 s). Firmware detail later.
4. **Relay supply, stated precisely:** the 5 V rail and therefore the relays
   hold while the battery stays above the LM5164 UVLO (6.05 V falling,
   `CALCULATIONS` 1.7); below that the 5 V rail collapses, the relay releases
   and the machine trips, which is the safe direction. Pickup (75 %) matters
   only at start. Release time with a diode flyback (ms) is negligible
   against the 1 s budget, but the driver may use a diode + zener flyback for
   faster release; decided in the schematic. LM5164 transient margin at the
   0.52 A envelope is 2x its 1 A rating (`CALCULATIONS` 7.3, 7.6).

## Revision 3 after an independent review (Claude Opus subagent, 2026-10-08)

Report kept in the session record (summary here). It found faults that both
W1 and Codex missed. Hardware changes, now in the 24-ch schematic
(`hardware/24ch/`):

1. **Leakage through 3.2 k (H1):** a node-to-rail leakage of ~10 Mohm gives
   ~4 degC on an insulated probe, either sign, invisible to every diagnostic.
   C_cm now returns to **V_BIAS** (not AVSS), so its pad leakage sees ~0 V.
   **Washing and conformal coating are mandatory** (was "to be decided" in
   `0031`); layout runs a V_BIAS guard around clamp node, R2 and AIN copper;
   requirement R_leak > ~120 Mohm per node, to be humidity-tested.
2. **Bias bus separated (M4):** V_MID -> 10 k -> **V_BIAS** (100 nF per bank +
   BAV199 clamp) feeds the 24 R_b and C_cm; the engine-reference feed stays
   on V_MID. R_b is a **1206** 20 M (FRG1206F2005TS, C3000606).
3. **AVDD clamp (M1):** TL431 + MMBT3906 shunt at ~3.5 V (22 ohm limit, ~150 mA)
   in addition to the 150 ohm preload. Rev 2's claim that the AD7124 flags a
   rising AVDD was wrong (its monitors only see LDO undervoltage); firmware
   measures (AVDD-AVSS)/6 every scan.
4. **Sense load 100 k -> 1 M (M5):** a short or leakage across R_b no longer
   pushes ~15 uA down a grounded TC- (would read ~37 degC low). Threshold now
   15k/10k = 1.32 V (connected ~1.63 V, broken <= 0.9 V).
5. **5 V crowbar (M6):** SMBJ5.0A on +5V, so a shorted buck FET blows F601
   instead of leaving the relays and MCU on 24 V.
6. **Trip relay poles in series:** both NO contacts of the G6K in series, so
   one welded contact cannot keep RUN (I-081 partly mitigated); NC from pole 1.
   Read-back of both relays is the coil low side through 10 k.

Firmware requirements recorded for later (owner: software later), I-104:
burnout lower window and per-channel commissioning baseline (H2: shorted C_d
or R2 otherwise reads as T_CJ forever); ADT7310 ID/config/status checks,
reject 0x0000/0xFFFF, cross-check the two sensors per bank (H3: a dead CJ bus
reads 0 degC = channels low by the panel temperature); reference ratio
calibrated at production and thresholded on drift (M2: +/-1.6 % = ~10 degC at
600 degC); PGA ratio test between gains; AVDD/6 every scan; AD7124 mid-power
mode (M7, input current /3); CRC required on every read (a reset disables
it); reversed-polarity fault on negative EMF; open TC default = trip.

Open, needs measurement: engine-to-panel **AC** and transient voltage (M3:
insulated channels follow the panel through cable-shield capacitance;
consider bonding shields to ENGINE REF instead of the panel bar). Nexperia
BAV199 is LCSC marketplace-only: find a stocked alternate or bench-test HXY
hot leakage. CALCULATIONS 7.1 to be re-run for 3x ISO7761 and 6x ADT7310.

## Revision 4 after a pin-level schematic review (Claude Opus subagent, 2026-10-08)

Every IC pinout was checked against its datasheet and footprint: no wrong pin
(AD7124-8, ADT7310, ATmega1284P, ISO7761 directions, ADM2587E, LM5164, TL431
DBZ pin 1 = K for TI parts only, REF3030, TLV7031, MCP6001, BAV199, B0505S on
the CRE1 footprint, G6K-2F-Y pins 1+/8- coil, 3/6 COM, 2/7 NC, 4/5 NO).
Changes made in `hardware/24ch/gen`:

1. **AVDD clamp fixed:** the 1 k between the TL431 cathode and the PNP base
   pushed the turn-on to ~3.8 V with ~10 mA of sink. Now the cathode drives the
   base directly, 470 ohm base-emitter (PNP on at ~1.3 mA TL431 current),
   22 ohm 2512 collector resistor (0.5 W at full clamp). TL431 must be TI
   (TL431BIDBZR): other vendors' SOT-23 pin order differs.
2. **Trip drive through a charge pump:** PB3 (OC0A) must run a square wave;
   100 nF coupling + BAT54S + 100 nF/100 k gate hold. A pin stuck high or low
   (hung firmware) drops the relay in ~10-30 ms. A shorted 2N7002 is detected
   by the read-back but not cleared: accepted with the series contacts (I-081).
3. **REFOK fail-safe:** comparator inputs swapped, LOW = wire connected, so the
   isolator's default-high on lost island power reads "broken"; 1 M hysteresis
   (~20 mV) and 100 nF on the 1 M sense node.
4. **RS-485 at reset:** 10 k pull-down on DE, 10 k pull-up on RxD; the 10 nF
   caps the ADM2587E datasheet asks for at pins 2/1 and 19/20 added; the
   isolated rail is renamed +3V3_RS485 (it is 3.3 V).
5. **Removed (rule 7):** island-side CS pull-ups R406-R414 (push-pull
   isolator outputs), R426, R439, the RS-485 test points (the screw terminal
   is the test point). The IOVDD ferrite mentioned in rev 0 is not used.
6. **CHASSIS ESD return:** 1 nF 2 kV + 1 M from CHASSIS to GND. The RS-485
   cable shield bonds at the panel bar, so J703 is A/B/GND only.
7. **Accepted, not fixed:** SMBJ5.0A on +5 V is only a partial crowbar (its
   6.4 V breakdown is above the MCU's 6 V absolute maximum; it may not survive
   until F601 trips). A shorted buck FET is a rare single fault; the relays
   drop if the TVS fails short, and the MCU is lost either way. Revisit with
   an SCR crowbar if the bench shows otherwise.

Firmware additions to I-104: RUN_PERMIT is a continuous PWM (OC0A), never a
static level; JTAG fuse off and MCUCR.JTD; WDTON and BOD fuses set; REFOK
active-low.
