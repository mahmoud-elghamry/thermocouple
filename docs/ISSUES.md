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

## P0 — blocks ordering the 24-ch board (REV A3)

| # | Sev | Issue | Close when |
|---|---|---|---|
| I-108 | medium | **LCD and panel mechanics.** Done 2026-10-11 (`0034` D2): J503 panel-button header (JST XH B6B-XH-A, C144397) on the board in parallel with SW501-SW505, tact switch C7470135 (9.5 mm, 75,020 pcs; 10 mm C7470136 has 1,000). **Still needed before ordering:** the locally bought LCD's drawing to confirm the standoff holes H6-H9 and J502's position; then the panel cut-out. | LCD drawing checked against H6-H9/J502; front-panel cut-out drawing |
| I-103 | high | **All parts from one source** (owner, `0031` D6): NORI buys every part (turnkey). Stock read 2026-10-11 (`hardware/24ch/output/stock-20261011.csv` + `-notes.md`, jlcsearch API, spot-checked on lcsc.com): 87 of 93 BOM lines OK for 50 boards, 0 out of stock, 5 without a code (tact switches, I-108). One conflict: C17917 (R401 150R 1206) API 6 vs lcsc.com 152,600 - confirm on the JLCPCB page at order time. The API's numbers drift from lcsc.com (e.g. C2837519 44k vs 7.9k), so re-read stock on the order day. Named alternates per line still to add. | Order-day stock read on the JLCPCB/LCSC page; an alternate named for each single-maker part |
| I-106 | high | **NORI order spec** (`0033` D2). **Owner 2026-10-11: where they assemble (China or Egypt) and how (stencil, X-ray) is their business; we give the spec, they meet it.** So these are order instructions, not questions: 4 layers FR4 1.6 mm 1 oz, ENIG (0.5 mm LFCSP needs a flat finish), all vias tented, use our paste layer as is (window-pane paste on the AD7124/LM5164 exposed pads; U601's 3 EP vias tented), top-side assembly, flux washed off. Coating: I-105. Turnkey, customs theirs (owner 2026-10-09). | `gen/fab.py` writes these notes into the release; NORI quote accepts them |
| I-078 | medium | **Order package pending.** NORI (`0033` D2): 4-layer bare 170 x 145 quoted EGP 8,710 for 5 / 11,500 for 10 (site calculator 2026-10-09, assembly extra). Parts $104.9/board at LCSC qty-1 (`gen/cost.py`), 52 extended codes, ~$156 setup per order. `gen/fab.py` now refuses until DRC 0/0/0 **and** `pincaps.py` pass, and puts ORDER-NOTES, MANIFEST and ACCESSORIES.csv (`hardware/24ch/accessories.csv`, I-116) in the release. Needs: I-111 closed, the release, NORI's quote covering or excluding each accessory line, delivered total. | Release from a board that passes every gate; NORI quote reviewed with the owner |

## P1 — before a unit protects a machine

| # | Sev | Issue | Close when |
|---|---|---|---|
| I-118 | high | **Heartbeat must prove the scan, not just a timer** (Astra R-03): RUN_PERMIT PWM from OC0A can keep the charge pump alive while the main loop hangs. Toggle the heartbeat only when a fresh scan of all channels completes; watchdog not fed from an independent ISR. | Fault injection: hung loop with timers running opens the contact within the set time |
| I-119 | high | **24-ch firmware port list** (Astra R-04/R-05/R-11/R-12): scan needs >= 14 slots (~0.62 s, burnout ~5 s, common-mode ~10 s); ADT7310 0x0000 is 0 degC, not a dead bus (use ID/status/freshness); negative EMF is normal when the tip is colder than CJ; `program.ps1`/fuses are ATmega32 only; integration test mocks readback/WDT/EEPROM; `'1'+index` breaks at CH10; samples need timestamps; fault byte is full; EEPROM A/B records; watchdog <= 0.5 s against the 1 s budget (from I-097). | Each item in target24 with a test or bench measurement |
| I-104 | high | **24-ch firmware requirements from the front-end reviews** (`0032` rev 3-4): burnout lower window + per-channel baseline; ADT7310 ID/config/status checks (0x0000 is 0 degC - I-119), two-sensor cross-check per bank; reference ratio calibrated at production; PGA gain-ratio test; AVDD/6 every scan; mid-power mode; CRC on every read; reversed-polarity fault; open TC trips by default (`0034` D1); >= 14-slot schedule (I-119); RUN_PERMIT PWM into the charge pump toggled only by completed scans (I-118); JTAG off, WDTON, BOD; REFOK active-low. | Implemented and each one shown by fault injection at the bench |
| I-100 | high | **Independent channel limits are required but not implemented** (owner, 2026-10-07, `0029`). The 24-ch firmware is not written; the 8-ch firmware has one scalar setpoint. Needed: 24 operator-adjustable persistent limits, channel selection on the 20x4 LCD, per-channel trip/reset/hysteresis, per-channel "alarm only" and "not fitted" (`0034` D1), CRC/readback, EEPROM A/B records, config lock. Never invent commissioning temperatures. | Behaviour tested on the host and the bench; all build gates pass |
| I-085 | high | **24-channel installation drawing pending** (`0031`): trip (RUN PERMIT C-NO, from I-113) and alarm contacts, J601 3 = CHASSIS bar, J401 FEED and SENSE as two wires joined only at the engine, J503 panel buttons, probe-to-channel map, ground compatibility. An unused input reads open and trips (`0034` D1), so a partly fitted board needs a saved per-channel "not fitted" setting (I-100). | Panel drawing shows every terminal, the contacts' rated load and battery power; all 24 sensors mapped |
| I-102 | medium | **Panel fuse** (off-board, `CALCULATIONS` 7.4): `0020` stands conditionally (1 A time-delay, >= 80 V DC, >= 10 kA, pre-arc I²t >= 1 A²s): steady margin 2.65x at 9 V, inrush screening 0.509 A²s at 32 V = 1.96x. Goes into the accessory BOM (I-116). | Exact fuse and holder picked against DC rating, fault current and derating; startup I²t measured |
| I-091 | medium | **Operator interface** (`0031` D4): 20x4 LCD bought locally, five buttons + panel header (`0034` D2). Ask the operations engineer whether opening the door to read and ACK is acceptable. | Operations engineer answered; LCD part recorded |
| I-093 | medium | **Terminals and shield:** shield bonded at panel entry (`0031` D8); 48 pluggable 3.81 mm TC terminals (Kangnex) on the board. Exact extension cable and gauge still to specify. | Cable specified on the installation drawing (I-085) |
| I-094 | medium | **RS-485/Modbus** (`0031` D7): ADM2587E + SM712 on the board. Remote setpoint writes need CRC, read-back and a local enable; comms loss never grants RUN (protocol: I-086). | Protocol written and tested |
| I-086 | low | No Modbus firmware yet. The master is the plant PLC/SCADA (`0031` D7); the RS-485 hardware is on the board (I-094). Never in the trip path; comms loss never grants RUN. | Register map written and tested |

## P2 — measure at the bench when boards arrive

| # | Sev | Issue | Close when |
|---|---|---|---|
| I-114 | medium | **CJ sensors 25-35 mm from the terminal pads** (Astra R-08). The I-111 repair freed no room near the terminals (2026-10-11), so this is measured, not moved. | Gradient test with LCD, relays and RS-485 loaded: compensated error inside the budget |
| I-105 | high | **Board leakage is a measurement error source** (`0032` rev 3, H1): 3.2 k per leg turns ~10 Mohm node leakage into ~4 degC. **Layout guard done 2026-10-11** (`gen/vbias_pour.py`): V_BIAS pours over each bank's input network on F/B.Cu, island pour cut out there; input-node pads with GND_ISO within 0.5 mm 197 -> 6 (the 6 are ADC pins beside AVSS/EP). Washing + coating: `gen/fab.py` ORDER-NOTES carries the procedure (NORI if offered, else us). R_leak > ~120 Mohm per node. | Coated boards pass a humidity/leakage test at the bench |
| I-101 | high | **Probe junction type cannot be controlled** (custom, maybe mixed). Direction (`0031`): 3x AD7124-8, one probe at a time, 20 M TC- bias + buffered mid-rail engine-reference wire. Circuit in `0032` rev 2 after three Codex reviews: 2.2 k / BAV199 / 1 k protection, 150 ohm AVDD preload as clamp sink, REF3030 cross-check at gain 1, sensed engine-reference wire, 2 ADT7310 per bank, 13-slot scan 0.57 s. Out of scope: DC miswire survival (I-080). Still open (owner 2026-10-09: not before ordering - at the first engine test): engine ground volts at cranking; cable capacitance; hot leakage. | Schematic reviewed; bench test with grounded, insulated, mixed probes, a cut wire and a lost reference wire |
| I-120 | medium | **Bench and field test matrix** (Astra section 12): every channel and its location, <= 1 s contact response, open sensor, mixed grounds and cut FEED/SENSE, CJ gradient, partial power, firmware hang, ACK/startup, EEPROM power cut, Modbus flood, 50 m cable, humidity, installer trial, per-unit production test. | Each row run and logged on the first boards |
| I-098 | medium | **STUCK and step checks may nuisance-trip** (audit 12). A reading that stays inside 0.1 °C for 120 scans (~55 s) trips and needs ACK; a steady or stopped engine body can do that. `MAX_STEP` 50 °C/scan is from the cylinder-body basis, which GOAL says not to extend to all 24. Not inherited, but never validated. | Logged on a running and a stopped engine; window widened if needed |
| I-076 | high | **Buck layout measured, not claimed.** 24-ch U601: after the I-111 repair, measure rails, SW ringing and sensor noise. (8-ch U14 layout history: `0026`, `CALCULATIONS` 5.2.) | Rails, ringing on SW and sensor noise measured on an assembled 24-ch board |
| I-003 | high | The isolated module (24-ch: U401 B0505S-1WR2) is unregulated; its light-load output may approach 6 V. Mitigated by the LP2985 (`0002`) and the preload (`0032` rev 2), never measured. | Module output measured at real load |
| I-004 | high | The isolation barrier was never tested electrically. The 3 mm in `.kicad_dru` is functional, not a standard. | Insulation test across the barrier |
| I-013 | high | The 1 s trip requirement has never been measured. 24-ch budget: I-119 (~0.62 s scan). | Input stepped past the setpoint, contact timed on a scope |
| I-028 | medium | Battery input (24-ch: F601 PTC, D601, D602 SMBJ60A, U601 LM5164; panel fuse I-102). Open: (b) SMBJ60A clamps at ~96.8 V at its peak current, 3.2 V under the LM5164's 100 V; ISO 7637-2 fast pulses not worked through; (c) EMC of the switcher, ties to I-076. History: `git show 7107a94:docs/ISSUES.md`. | Fast-transient analysis or test; EMC and noise measured on hardware |
| I-096 | medium | **5 V budget** (`CALCULATIONS` 7, 7.7): with rev 3-4 parts and R502 = 22 ohm the 5 V worst is ~0.45 A, 9 V battery 0.35 A, 23 % margin on F601 at 70 degC; island preload fitted (`0032` rev 2). Open: the LCD's real backlight current and the operating envelope. | LCD measured; operating envelope (max ambient, min battery) agreed |

## P3 — later, or accepted limits

| # | Sev | Issue | Close when |
|---|---|---|---|
| I-081 | medium | A welded contact or a shorted driver keeps RUN permitted. 24-ch: both trip-relay NO poles in series (`0032` rev 3), so one welded pole is covered; a shorted Q701 or a weld on both poles is not. Read-back is the coil low side, not the contact. **Review weight:** accepted, documented limit (owner, 2026-10-01). A redundant shutdown path is a machine-safety decision. | The owner records the machine's other protection, or asks for a second path |
| I-080 | low | 24 V wired by mistake onto a TC terminal: 24-ch input is 2.2 k + BAV199 + 1 k into the island rails; not re-derived for the shunt clamp (8-ch figure: `CALCULATIONS` 5.3). **Review weight:** agreed low. We do not design for this miswire. | Only if the owner requires miswire tolerance |
| I-026 | low | **Superseded by I-101** (2026-10-08). Probe model does not exist (made to order); junction type to be measured on receipt with clip leads on the tip metal, not fingers. Electrical sheath isolation is not thermal isolation. | I-101 closed and probes classified on receipt |
| I-046 | medium | Konnect is AGPL-3.0; exposure today is zero (nothing distributed, no Konnect code in the repo). | Settled before shipping anything built around Konnect |
| I-054 | low | kicad-tool clones inherit the donor's MPN; `check_mpn_consistency.py` in `validate.ps1` catches it. | kicad-tool fixed upstream |
| I-056 | medium | Doc-system review (2026-09-17). The file-size and row-length parts are handled by `0025`. Still open: a dated evidence log, a decisions index, requirement-to-evidence traceability. | Those three exist, or are explicitly declined |
| I-084 | low | CI has no 24-ch job (schematic ERC/netlist, DRC, `pincaps.py`), and the 8-ch job runs fewer checks than `validate.ps1`. Ties to I-115. | CI runs the 24-ch gates, or the difference is documented |
| I-109 | low | **Cost options for the next revision** (`0033` D3): ADT7310 x6 is $32.4 of $104.9/board; TMP117 (C699536, ~$1.03, I2C, needs a bus change) saves ~$26/board. 52 extended LCSC codes cost a per-order setup fee at JLC-style assemblers (basic-part check by Haiku 5.5 and Sonnet 5.5, 2026-10-09: only 2N7002 -> C8545 and 2.2n -> C28260 C0G qualify, ~$6); non-critical pull-ups, LED resistors and bypass caps could move to basic parts (keep C0G, 20 M, BAV199). Codex 2026-10-09 (`production/review-20261008/codex-alternatives-review.md`): 3 CJ sensors + 2 ISO7761 (~$19, needs terminal-gradient data), RS-485 optional (~$9) or CA-IS2092W (~$5). Market (`market-scan.md`): Murphy TDXM 24-ch $2,200-3,600, PLC routes $1,900-3,300. Open designs (`open-designs-scan.md`): none replaces ours; ADI CN-0376 uses 3 k per input path (ours 3.2 k). | Decided at REV B |

## REV A2 (8-ch reference board) only

The 8-ch board is never ordered (`0031`); these stay open only for it: I-079, I-058, I-072, I-087, I-059, I-064, I-083.

| # | Sev | Issue | Close when |
|---|---|---|---|
| I-079 | medium | **`production/8ch-reva2/RELEASE.txt` said the K1 coil is ~2.9 kOhm.** The G5LE-1 DC24 coil is **1.44 kOhm ±10 %** at 23 °C (16.7 mA; `datasheets/G5LE-relay.pdf`). The 2.9 came from an old I-058 text, copied without checking. The package is marked on hold. | The re-exported package's RELEASE text uses 1.44 kOhm |
| I-058 | high | K1 coil pins were fixed in the schematic and PCB (2026-09-24/26). Before power-up: pins 2-5 read **1.44 kOhm ±10 %**, 1-4 read 0 Ohm and 1-3 open. | Measured on an assembled board |
| I-072 | low | Stale overview text: `hardware/8ch/README.md` (TSR 1-2450), firmware comments on feedback. **Audit 2026-10-06 (24) adds:** VFD comments `config.py:80`, `check_board.py:174`; "C_diff 100n C0G" (X7R since `0011`) `config.py:73`; "AP2112K" for U13 `placement.py:78`; "0.5 A PTC" `apply_rules.py:59`; "G5LE-1" `placement.py:150`; value text "10u 10V" on C45/C46/C55 (MPNs are 25 V/16 V). | Reconciled |
| I-087 | low | The Proteus project simulates a MAX6675, not the fitted MAX31856, so it proves nothing about the real sensor path (review 2026-09-29). | Updated, or labelled as legacy |
| I-059 | low | Field-text overlaps in dense schematic spots; readable, not tidy. | KiCad GUI touch-up |
| I-064 | low | The board overlaps the PCB-editor page frame. Cosmetic; fabrication is unaffected. | Offset applied at a regeneration |
| I-083 | low | `build.py` needs git history (base `05d6abd`); a source ZIP cannot regenerate the schematic. Not wrong, just coupled. | The release notes name the base commit, or the base is kept as a file |

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
