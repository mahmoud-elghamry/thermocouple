# Open issues

**How this file works** (`decisions/0025`, 2026-10-01):

* It is an **index sorted by priority**, and it stays short so every agent
  reads all of it. One table row per issue.
* A row is at most about 600 characters and holds four things: what is wrong,
  why it matters, where the evidence is, and when the issue can be closed.
  Long arithmetic goes to `reference/CALCULATIONS.md`, a choice between
  alternatives goes to `decisions/`, and raw logs go to `production/review-*/`.
  The row points there.
* No narrative sections. A review's findings become rows here. Its coverage
  notes become rows too, or one bullet under "Not verified by anyone" below.
* Numbers are never reused. Closing an issue means moving its row to
  `ISSUES-closed.md` with the date and what fixed it.
* **Review weight.** A finding an agent judged overstated keeps its row, but
  says so, together with the agreed weight and the reason. Nothing is silently
  dropped.

Severity: **blocker** stops fabrication · **high** is a real failure mode ·
**medium** costs time or quality · **low** is tidiness.

**Priority:**

* **P0** blocks the board order.
* **P1** must be done before a unit protects a machine.
* **P2** is measured at the bench when boards arrive.
* **P3** is later, or an accepted limit.

---

## P0 — blocks ordering the module (REV A3 after the shrink, `0028`)

| # | Sev | Issue | Close when |
|---|---|---|---|
| I-101 | blocker | **Probe junction type cannot be controlled** (custom, maybe mixed). Direction (`0031`): 3x AD7124-8, one probe at a time, 20 M TC- bias + buffered mid-rail engine-reference wire. Circuit in `0032` rev 2 after three Codex reviews: 2.2 k / BAV199 / 1 k protection, 150 ohm AVDD preload as clamp sink, REF3030 cross-check at gain 1, sensed engine-reference wire, 2 ADT7310 per bank, 13-slot scan 0.57 s. Out of scope: DC miswire survival (I-080). Still open: owner measurement of engine ground volts at cranking; cable capacitance; hot leakage. | Schematic reviewed; bench test with grounded, insulated, mixed probes, a cut wire and a lost reference wire |
| I-103 | high | **All parts from one source** (owner, 2026-10-08, `0031` D6): the board goes to NORI, who likely order from abroad; no part may need a separate search or shipment. LCSC stock 2026-10-08: AD7124-8 C97314 3,576 / C578388 4,450; ATmega32A-AU C5659 43,402; ATmega644PA-AU C38349 311; ATmega1284P-AU C33575 1,943; G6K-2F-Y-TR DC24 C5278023 13,908; Kangnex 3.81 header C7245 67,450 / plug C7244 55,080. **Gaps found:** REV A2's IA0505S (U12) has no LCSC code (B0505S-1WR3 only via LCSC marketplace, MOQ/lead time); terminal CJ sensor not chosen (TMP126 marketplace-only). Confirm which catalogue NORI uses (LCSC/JLCPCB assumed) and that they assemble the 5 x 5 mm LFCSP AD7124-8. | NORI confirmed catalogue and assembly limits; every BOM line has dated stock there and a named alternate |
| I-104 | high | **Firmware requirements from the front-end reviews** (`0032` rev 3): burnout lower window + per-channel baseline; ADT7310 ID/config/status checks and 0x0000/0xFFFF rejection, two-sensor cross-check per bank; reference ratio calibrated at production; PGA gain-ratio test; AVDD/6 every scan; mid-power mode; CRC on every read; reversed-polarity fault; open TC default trip; 13-slot schedule; RUN_PERMIT as continuous PWM into the charge pump (rev 4); JTAG off, WDTON, BOD; REFOK active-low. Without these a shorted C_d, a dead CJ bus or reference drift can read LOW unflagged. | Implemented in firmware and each one shown by fault injection at the bench |
| I-105 | high | **Board leakage is now a measurement error source** (`0032` rev 3, H1): 3.2 k series per leg turns ~10 Mohm node leakage into ~4 degC. Washing + conformal coating mandatory; V_BIAS guard in layout; R_leak > ~120 Mohm per node. | Coating in the fab order; guard in the layout; humidity test at the bench |
| I-106 | high | **Questions for NORI before ordering** (`0033` D2): (1) assembled in China and imported, or assembled by them in Egypt? (2) LFCSP-32 AD7124: their stencil for the exposed pad (window-pane paste) and via treatment (EP has 4 vias, tent or plug); they have AOI only, no X-ray. (3)+(4) **answered by the owner 2026-10-09: turnkey - NORI buys every part and solders it (or imports the board assembled); customs are their concern**; (5) cleaning + conformal coating (I-105) offered? | Answers recorded here and in `0033` |
| I-107 | blocker | **24-ch routing: 2 connections left** (2026-10-09). `thermo24.kicad_pcb`: KiCad DRC 0 violations, 2 unconnected - TC21_NA (pad 15 of U301 boxed in by TC21_PA; re-route the pair) and CS_CJ5_ISO (long island run). Geometry and plan: `production/review-20261008/codex-route-brief.md`. Then `rules.py` full (NORI 0.2 mm rule not yet on the board), silkscreen, DRC 0, `fab.py`. Tools: `gen/finish.py`, `gen/maze.py` (TOOLS "24-channel board"). | `drc-report.rpt` 0/0/0 |
| I-108 | medium | **Buttons and LCD mechanics.** LCD face ~24 mm above the board; tallest 6x6 THT tact on LCSC found 9.5 mm. Options: guided actuator extension, panel-mounted buttons on a cable, or a taller switch. Needs the locally bought LCD's drawing (bezel height, standoff length) and the panel face. Silkscreen for installers (channel numbers, K+/K-, battery polarity, contact function, shield) goes with it. | LCD model and drawing in hand; button part with LCSC code; front-panel cut-out drawing |
| I-110 | medium | **AD7124 exposed-pad vias sit under the paste.** `fanout.py` put 4 vias at (+-0.8, +-0.8) mm in the EP; the LFCSP footprint's 4 paste windows are 1.45 mm squares at (+-0.9, +-0.9) with 0.35 mm gaps on the axes, so solder wicks into the holes (NORI has no X-ray). Move them onto the gap cross ((0,0), (0,+-1.25), (+-1.25,0)) and tent them on B.Cu; check LM5164 (U601) EP vias the same way. | Vias moved, DRC 0, paste layer checked in Gerber |
| I-102 | medium | **Panel fuse for one board** (`CALCULATIONS` 7.4): `0020` stands conditionally (1 A time-delay, >= 80 V DC, >= 10 kA, pre-arc I²t >= 1 A²s): steady margin 2.65x at 9 V, inrush screening 0.509 A²s at 32 V = 1.96x. | Exact fuse and holder picked against DC rating, prospective fault current and derating; startup I²t measured |
| I-078 | medium | **Order package pending.** Fab/assembler: NORI (`0033` D2): 4-layer bare 170 x 145 quoted EGP 8,710 for 5 / 11,500 for 10 (site calculator 2026-10-09, assembly extra). Parts $104.9/board at LCSC qty-1 prices, 52 extended LCSC codes, ~$156 setup per order (`hardware/24ch/gen/cost.py`, `output/cost.csv`; 62 was BOM lines). Still needed: DRC-clean board, `gen/fab.py` (Gerber+drill zip, BOM, CPL, PDF), NORI's assembly quote, delivered total. | Files exported from a DRC-clean board; NORI quote with assembly reviewed with the owner |
| I-090 | high | **Board size decided: 170 x 145 mm, 4 layers, barrier bands unchanged** (`0033` D1). Moving the barrier under the LCD puts the LCD standoffs/hardware in the band; 180 x 150 costs +23 % at 10 boards (NORI quote 2026-10-09) and needs full re-placement. Placement done, 0 overlaps. | Routing finished on this placement and every gate re-run |
| I-091 | high | **Operator interface set (`0031` D4):** 20x4 LCD on standoffs on the board, five buttons beside it (UP, DOWN, SET, ESC, larger ACK); door untouched. **LCSC 2026-10-08: no 20x4 character LCD really in stock** (HS204A C5329590: 3 pcs; the rest 0/pre-order); 128x64 ST7920 3.2" HS12864-15C C2939934: 60 pcs. **Owner: buy the 20x4 locally** (plug-in, not factory-assembled; `0031` D4). Backlight current into I-096. Ask the operations engineer whether opening the door to read and ACK is acceptable. | Parts with stock chosen; mounting in the floor plan; operations engineer answered |
| I-092 | high | **Contacts 30 VDC / 1 A max, signal loads only** (owner, `0030` D5). Two relays (trip, alarm; `0031` D5): **G6K-2F-Y DC5 on the regulated 5 V rail** (`0032` rev 1): the DC24 coil maximum (36 V) is below the 58 V load-dump basis, and 5 V holds through cranking dips. Stock is LCSC marketplace (C47190/C326376). | Coil current, driver, flyback and read-back drawn and checked in the schematic |
| I-093 | medium | **Terminals and shield:** shield bonded at panel entry (`0031` D8), so 2 terminals per TC, 48 in total, pluggable 3.81 mm, possibly tiered; cold-junction sensors at each terminal zone. Exact cable/gauge still to specify. | Terminal part from the single source in the floor plan; cable specified |
| I-094 | medium | **RS-485/Modbus to PLC/SCADA fitted and isolated** (owner, `0031` D7): ADM2587E C12081 (stock 6,979, 2026-10-08), alternate CA-IS2092W. Never in the trip path; remote setpoint writes need CRC, read-back and a local enable. | Transceiver, TVS, termination/bias in the schematic; protocol written with comms loss never granting RUN |
| I-095 | medium | **MCU and shrink part choices:** ATmega32A class is enough for 24 channels (`0031` D3); prefer pin-compatible ATmega644PA/1284P if stocked at the single source. Verify pin mapping against the complete datasheet (local ATmega32A.pdf looks truncated). | MCU chosen with dated stock; pins checked |
| I-096 | medium | **5 V budget re-derived for the 24-ch board** (Codex, `CALCULATIONS` 7, 2026-10-08): 270 mA typ / 440 mA screening worst, 0.50 A design envelope; LM5164 and L1 ample. **Open:** the 1 W island DC-DC is below its 20 mA minimum load (island ~12 mA) -> preload or a module rated for the load (`0032`); With rev 3-4 parts and R502 = 22 ohm the 5 V worst is ~0.45 A, 9 V battery 0.35 A, 23 % margin on F1 at 70 degC (`CALCULATIONS` 7.7); a brighter backlight eats that margin. | Island supply loading fixed; LCD measured; operating envelope (max ambient, min battery) agreed |
| I-079 | medium | **`production/8ch-reva2/RELEASE.txt` said the K1 coil is ~2.9 kOhm.** The G5LE-1 DC24 coil is **1.44 kOhm ±10 %** at 23 °C (16.7 mA; `datasheets/G5LE-relay.pdf`). The 2.9 came from an old I-058 text, copied without checking. The package is marked on hold. | The re-exported package's RELEASE text uses 1.44 kOhm |

## P1 — before a unit protects a machine

| # | Sev | Issue | Close when |
|---|---|---|---|
| I-085 | high | **24-channel installation drawing pending.** Now one 24-channel board with a trip and an alarm contact (`0031`); per-channel limits selected (`0029`, I-100). Physical probe mapping/ground compatibility and panel diagram remain unverified. Firmware requires all 8 inputs per module; an unused open input trips. Optional master is outside the trip path. | Panel drawing shows series contacts, rated load and battery power; all 24 required sensors mapped |
| I-100 | high | **Independent channel limits are required but not implemented** (owner, 2026-10-07, `0029`). Firmware currently uses one scalar setpoint per module. Add 8 operator-adjustable persistent limits, channel-selection UI, per-channel trip/reset/hysteresis, CRC/readback and safe old-EEPROM migration/config lock. Never invent commissioning temperatures. | Firmware plan reviewed; independent hot/fault/ACK/save/migration behavior tested; all build gates pass |
| I-097 | medium | **Firmware timing inherited from the single-channel/MAX6675 code** (audit 9, 10, 23). `SCAN_TICKS` 8 x 50 ms comes from the MAX6675's 220 ms conversion; the MAX31856 gives a reading every ~100 ms, so ~350 ms of the 1 s budget is avoidable. Watchdog is `WDTO_2S` (`main_8ch.c:134`, from `ec0cdd7`) against a 1 s requirement: a hang with PB3 high keeps RUN ~2 s. The budget is quoted as 628, 625 and 623 ms. Setpoint upper limit 1200 °C has no basis. | Scan every 2 ticks (`STUCK_SCANS` rescaled); `WDTO_500MS`; one budget in `CALCULATIONS`; setpoint cap from the sensor mapping; tests pass |

## P2 — measure at the bench when boards arrive

| # | Sev | Issue | Close when |
|---|---|---|---|
| I-098 | medium | **STUCK and step checks may nuisance-trip** (audit 12). A reading that stays inside 0.1 °C for 120 scans (~55 s) trips and needs ACK; a steady or stopped engine body can do that. `MAX_STEP` 50 °C/scan is from the cylinder-body basis, which GOAL says not to extend to all 24. Not inherited, but never validated. | Logged on a running and a stopped engine; window widened if needed |
| I-076 | high | **Layout done 2026-10-01 (`0026`), measurement open.** The U14 stage is now placed and copper-drawn by `board/powerstage.py` and protected from the router. C63 to VIN is 3.5 mm (was 19.5), C54 is 7.0 mm (was 12.1), SW is one straight 1.0 mm track pin 8 to L1 (was 9.4 mm with 0.2 mm sections), and BST is 3.0 mm. `CALCULATIONS` 5.2. | Rails, ringing on SW and sensor noise measured on an assembled board |
| I-058 | high | K1 coil pins were fixed in the schematic and PCB (2026-09-24/26). Before power-up: pins 2-5 read **1.44 kOhm ±10 %**, 1-4 read 0 Ohm and 1-3 open. | Measured on an assembled board |
| I-003 | high | The IA0505S is unregulated; its light-load output may approach 6 V. Mitigated by the LP2985 (`0002`), but never measured. | Module output measured at real load |
| I-004 | high | The isolation barrier was never tested electrically. The 3 mm in `.kicad_dru` is functional, not a standard. | Insulation test across the barrier |
| I-013 | high | The trip budget is 623 ms calculated against a 1 s requirement (`app_config.h`), and has never been measured. | Input stepped past the setpoint, contact timed on a scope |
| I-028 | medium | Battery input: the stage and the panel fuse are done (`0016`, `0020`). Still open: (b) D2's 96.8 V clamp leaves 3.2 V under the LM5164's 100 V, and ISO 7637-2 fast pulses have not been worked through; (c) physical EMC of the 303 kHz switcher, which ties to I-076. Full history: `git show 7107a94:docs/ISSUES.md`. | Fast-transient analysis or test; EMC and noise measured on hardware |

## P3 — later, or accepted limits

| # | Sev | Issue | Close when |
|---|---|---|---|
| I-081 | medium | A welded K1 contact or a shorted Q1 keeps RUN permitted. R53/R54 read the drain, not the contact. This is true of **every** single-relay design. **Review weight:** the 2026-09-29 review rated it high; agreed 2026-10-01 as an accepted, documented limit (owner). A redundant shutdown path is a machine-safety decision, not a board fix. | The owner records the machine's other protection, or asks for a second path |
| I-077 | low | At a 58 V load dump, K1's coil sees 2.4x nominal and R32 sees 0.67 W against 0.25 W (`CALCULATIONS` 5.1). **Review weight:** rated high; agreed low on 2026-10-01. The dump lasts ~350 ms, a coil's thermal time constant is seconds, and resistors take short overloads. Cheap to harden during I-076 if wanted. | Accepted as is, or R32 split or up-rated |
| I-080 | low | 24 V wired by mistake onto a TC terminal would overload the 100 R input resistors and the shared 3.3 V rail (`CALCULATIONS` 5.3). **Review weight:** rated medium; agreed low. We do not design for this miswire. | Only if the owner requires miswire tolerance |
| I-086 | low | There is no RS-485/Modbus firmware and no master. **Review weight:** rated high, but with autonomous modules (I-085) no master is in the trip path. A master for display and configuration later is mainly firmware: RS-485 (ADM2587E) is already on the board. It also needs a device to act as master (a PC, HMI, PLC or one module) and the bus wiring. | A master is requested; its data contract is written with comms loss never granting RUN |
| I-026 | low | **Superseded by I-101** (2026-10-08). Probe model does not exist (made to order); junction type to be measured on receipt with clip leads on the tip metal, not fingers. Electrical sheath isolation is not thermal isolation. | I-101 closed and probes classified on receipt |
| I-046 | medium | Konnect is AGPL-3.0; exposure today is zero (nothing distributed, no Konnect code in the repo). | Settled before shipping anything built around Konnect |
| I-054 | low | kicad-tool clones inherit the donor's MPN; `check_mpn_consistency.py` in `validate.ps1` catches it. | kicad-tool fixed upstream |
| I-056 | medium | Doc-system review (2026-09-17). The file-size and row-length parts are handled by `0025`. Still open: a dated evidence log, a decisions index, requirement-to-evidence traceability. | Those three exist, or are explicitly declined |
| I-084 | low | CI runs fewer checks than local `validate.ps1` (no DRC, parity or MPN check). | CI runs the same subset, or the difference is documented |
| I-083 | low | `build.py` needs git history (base `05d6abd`); a source ZIP cannot regenerate the schematic. Not wrong, just coupled. | The release notes name the base commit, or the base is kept as a file |
| I-109 | low | **Cost options for the next revision** (`0033` D3): ADT7310 x6 is $32.4 of $104.9/board; TMP117 (C699536, ~$1.03, I2C, needs a bus change) saves ~$26/board. 52 extended LCSC codes cost a per-order setup fee at JLC-style assemblers (basic-part check by Haiku 5.5 and Sonnet 5.5, 2026-10-09: only 2N7002 -> C8545 and 2.2n -> C28260 C0G qualify, ~$6); non-critical pull-ups, LED resistors and bypass caps could move to basic parts (keep C0G, 20 M, BAV199). Codex 2026-10-09 (`production/review-20261008/codex-alternatives-review.md`): 3 CJ sensors + 2 ISO7761 (~$19, needs terminal-gradient data), RS-485 optional (~$9) or CA-IS2092W (~$5). Market (`market-scan.md`): Murphy TDXM 24-ch $2,200-3,600, PLC routes $1,900-3,300. Open designs (`open-designs-scan.md`): none replaces ours; ADI CN-0376 uses 3 k per input path (ours 3.2 k). | Decided at REV B |
| I-099 | low | **Rule-7 and precision leftovers from the single-channel board** (audit 15, 17, 19, 22, 25): R1-R16 100R **0.1 %** while the ±5 % C_cm caps dominate the mismatch; 19 SPI damping resistors with no calculation (re-check after the shrink shortens traces); R29 220R backlight set before an LCD is chosen; D5/D6 SMAJ6.0CA sit inside RS-485's −7/+12 V range (SM712 is the usual part); two legacy single-channel firmware images and the MAX6675 sim bank (why the I-082 guard was needed). | Each kept with a reason or removed |
| I-072 | low | Stale overview text: `hardware/8ch/README.md` (TSR 1-2450), firmware comments on feedback. **Audit 2026-10-06 (24) adds:** VFD comments `config.py:80`, `check_board.py:174`; "C_diff 100n C0G" (X7R since `0011`) `config.py:73`; "AP2112K" for U13 `placement.py:78`; "0.5 A PTC" `apply_rules.py:59`; "G5LE-1" `placement.py:150`; value text "10u 10V" on C45/C46/C55 (MPNs are 25 V/16 V). | Reconciled |
| I-087 | low | The Proteus project simulates a MAX6675, not the fitted MAX31856, so it proves nothing about the real sensor path (review 2026-09-29). | Updated, or labelled as legacy |
| I-059 | low | Field-text overlaps in dense schematic spots; readable, not tidy. | KiCad GUI touch-up |
| I-064 | low | The board overlaps the PCB-editor page frame. Cosmetic; fabrication is unaffected. | Offset applied at a regeneration |

## Not verified by anyone yet

This list is from the 2026-09-29 review coverage. The full table is in
`production/review-20260929/ISSUES-as-reviewed-20260929.md`, which is
local-only.

* Worst-case tolerances of every component; cold-junction gradients; 50 m cable accuracy and noise.
* Partial power-up and backfeed across the isolators; live SPI/ISP edges.
* Contact load and inrush against the relay rating; real contact timing.
* The exact LCD module, cable orientation and terminal mechanical drawings; the fab's rotation preview.
* RS-485 bus details (termination, bias, cable, EMC).
* Stock and lifecycle across all sources (58 parts "unknown").
