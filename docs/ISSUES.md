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
| I-078 | medium | **The order package is not uploadable yet.** **Done:** every line coded (`0027`): 5 exact-MPN codes; K1 is now G5LE-14 DC24, C53 is now the Rubycon YXF; U12 is XP IA0505S from DigiKey, hand-fit. The owner decided: factory fits SMD, the technician fits all THT (unless the factory THT price difference is small), 3 boards. **Kit list done** (`kit_list.py` → `technician_kit.csv`: 13 through-hole purchase lines plus socket, LCD, cable, shunts and fuse, x3). **Left:** the fab choice; the LCD model and the `0020` fuse part; export BOM/CPL in the fab's format (SMD only); review the fab's matching page and preview with the owner. | Fab chosen; fab-format files exported; screenshots reviewed with the owner |
| I-090 | high | **The board is 250 x 140 mm and 81 % empty** (2026-10-06). Parts' courtyards are 67 of 350 cm² (19 %). The size was inherited from the first plan and never justified. An outside engineer flagged it. JLCPCB, 5 pcs, 4 layers: $46.60 now, $34.90 at 160 x 100, **$8.00 at 100 x 100**. Shrink before ordering, stay four layers: options and prices in `0028`. The owner has no enclosure constraint. | Owner picks option A or B (`0028`); board re-placed and re-routed; every gate re-run |
| I-091 | high | **Where do the LCD and buttons go? Never decided** (audit 2026-10-06, finding 2). J2 feeds a "panel-mounted" LCD on a cable, but SW1-SW5 are on the PCB edge. On the backplate the buttons cannot be reached with the door shut; on the door, 24 x 50 m cables land on the door. Three modules mean 3 LCDs and 15 buttons. It came from the single-channel/Proteus board. | Owner picks: board on backplate + LCD/keypad on the door on one keyed cable, or a door-mounted unit. Needed **before** the shrink floor plan |
| I-092 | high | **K1 is a 10 A power relay and nobody knows the load** (audit finding 8). J3's load rating is "pending". The G5LE is rated for reliable switching at 100 mA / 5 V, so a PLC or safety-relay input (a few mA) is below it. Also its 24 V coil runs from the battery (finding 1): it cannot pick up under 18 V while cranking. **Review weight: medium, not high** - once ON it holds down to ~2.4 V (release 10 % of rated), so only an ACK pressed during cranking is affected. A 5 V coil on the buck output would also remove I-077 and shrink Q1/R32. | Owner says what the contact drives (voltage, current, PLC input or contactor coil); relay and coil chosen against that |
| I-093 | medium | **Shield termination: one shield screw per channel** (audit finding 4). JTC1-8 are 3-way (T+, T-, shield to the chassis ring), so 24 channels = 72 screws. A pigtail landed on the PCB is weaker than a 360-degree bond or shield bar at the panel entry, and costs 5 mm of edge per channel. Whether the 50 m cable is shielded is not recorded. | Owner/installer says cable type and where shields end; if at the panel entry, 2-way terminals |
| I-094 | medium | **Isolated RS-485 is more than the current direction needs** (audit finding 5). ADM2587E (5 kV isoPower, 120 mA = 28 % of the 5 V budget, a known EMI source) has its own island and band, about 30 x 35 mm. Modules are autonomous in one panel (`0024`); no master firmware (I-086). `0024` says keep RS-485, not that it must be isolated or fitted. | Owner picks: keep as is, non-isolated transceiver + TVS, or keep the footprint and fit it as DNP |
| I-095 | medium | **Part choices to settle with the shrink** (audit findings 3, 7, 13, 16, 18, 20, 21): channel pitch 30 mm for a ~17.5 mm block, the real waste; U1 DIP-40 + socket (9.4 cm², from the single-channel board; ISP now works via R61) vs ATmega32A-AU TQFP-44, same firmware; SOIC-16W isolators set the 6-6.5 mm bands (SSOP-16 exists, check stock); J2 unkeyed 1x16 vs keyed 2x8; rule-7 removals: J6 (unused 2x10), C51 (no ADC), R17-R24 (non-F isolators already default high). | Each accepted or rejected in `0028`'s follow-up, before placement |
| I-096 | medium | **The 5 V load budget uses the IA0505S full-load current** (audit finding 6). `CALCULATIONS` 1.1 says ~265 mA; the island draws ~29 mA (5.4), so ~50-70 mA in. Real 5 V load ~0.22 A, not 0.425 A. That sized L1 (2.2 A) and drove F1 to 60 V/0.75 A instead of the 72 V/0.5 A part with more load-dump margin (`0022`). Estimate from `d2c4cd3`, never re-read. | 1.1 and 1.8 re-derived from datasheets; F1 and L1 re-checked before the shrink |
| I-079 | medium | **`production/8ch-reva2/RELEASE.txt` said the K1 coil is ~2.9 kOhm.** The G5LE-1 DC24 coil is **1.44 kOhm ±10 %** at 23 °C (16.7 mA; `datasheets/G5LE-relay.pdf`). The 2.9 came from an old I-058 text, copied without checking. The package is marked on hold. | The re-exported package's RELEASE text uses 1.44 kOhm |

## P1 — before a unit protects a machine

| # | Sev | Issue | Close when |
|---|---|---|---|
| I-085 | high | **The system is 24 thermocouples; the board has 8** (owner, 2026-09-29). **Direction agreed 2026-10-01** (`0024`): three identical, autonomous 8-channel modules, each tripping its own relay. The owner still has to answer one question: one machine (all three contacts in series) or separate groups (one contact per machine). Either answer is panel wiring only, so this no longer blocks ordering the module. **Audit 2026-10-06 (finding 11):** the firmware has one setpoint and treats all 8 channels as required, so a group that is not a multiple of 8 leaves channels open (trips forever) and one relay cannot serve two machines. | The owner has answered the grouping question; the panel wiring drawing shows it |
| I-089 | medium | **A watchdog or brown-out reset while running now stops the machine until someone presses ACK** (a consequence of I-074: every reset goes through the startup latch). This is fail-safe and it is what the owner chose, but a supply dip during cranking could stop an engine that was running. Owner to confirm it is acceptable. | The owner confirms, or asks for a different policy for a reset while running |
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
| I-026 | low | Ungrounded (insulated) junction probes would remove the cranking-current path between cylinders at no cost. | Specified at probe purchase |
| I-046 | medium | Konnect is AGPL-3.0; exposure today is zero (nothing distributed, no Konnect code in the repo). | Settled before shipping anything built around Konnect |
| I-054 | low | kicad-tool clones inherit the donor's MPN; `check_mpn_consistency.py` in `validate.ps1` catches it. | kicad-tool fixed upstream |
| I-056 | medium | Doc-system review (2026-09-17). The file-size and row-length parts are handled by `0025`. Still open: a dated evidence log, a decisions index, requirement-to-evidence traceability. | Those three exist, or are explicitly declined |
| I-084 | low | CI runs fewer checks than local `validate.ps1` (no DRC, parity or MPN check). | CI runs the same subset, or the difference is documented |
| I-083 | low | `build.py` needs git history (base `05d6abd`); a source ZIP cannot regenerate the schematic. Not wrong, just coupled. | The release notes name the base commit, or the base is kept as a file |
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
