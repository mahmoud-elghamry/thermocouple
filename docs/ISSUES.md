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

## P0 — blocks ordering the REV A2 module

| # | Sev | Issue | Close when |
|---|---|---|---|
| I-075 | blocker | **U14 thermal vias are 0.4 mm drill in a 0.6 mm pad, which leaves a 0.10 mm ring.** `stitching.py` asks for 0.3 mm, but a later routing step replaces the via drill. Confirmed in the board and the drill file on 2026-09-30. The 2026-09-28 claim "smallest hole 0.3 mm" was right about hole size but missed this. `CALCULATIONS` 5.2. | The final PCB **and** the exported `.drl` show six 0.3 mm drills at U14; the step that overrides them is fixed so it cannot recur |
| I-076 | high | **The LM5164 power stage was autorouted.** VIN to C54 is 12.1 mm and VIN to C63 is 19.5 mm; TI section 7.4 wants the input caps at the pins. SW to L1 is 9.4 mm with 0.2 mm sections. Risks: ringing, and switching noise on a board that measures microvolts. `CALCULATIONS` 5.2; `production/review-20260929/regulator-copper.png`. | The U14 block is laid out by hand (fixed tracks before routing) to TI's guidance; DRC/parity clean; rails and noise measured on the bench (P2) |
| I-078 | medium | **The order package is not uploadable as it stands.** `bom.csv`/`cpl.csv` are in KiCad's format, not the fab's. 17 BOM lines have no LCSC code: MAX31856 x8, LP2985, ADM2587E, U1, IA0505S, K1, C53, RV1, and 9 test points, which need no part. The THT split (factory or local technician) is not decided. Missing from the BOM: the DIP-40 socket, LCD and cable, jumper shunts, and the `0020` fuse and holder. | Fab chosen; every line has a code or an explicit "hand-fit"; BOM/CPL exported in the fab's format; the fab's matching page and rotation preview reviewed line by line **with the owner** |
| I-079 | medium | **`production/8ch-reva2/RELEASE.txt` said the K1 coil is ~2.9 kOhm.** The G5LE-1 DC24 coil is **1.44 kOhm ±10 %** at 23 °C (16.7 mA; `datasheets/G5LE-relay.pdf`). The 2.9 came from an old I-058 text, copied without checking. The package is marked on hold. | The re-exported package's RELEASE text uses 1.44 kOhm |

## P1 — before a unit protects a machine

| # | Sev | Issue | Close when |
|---|---|---|---|
| I-085 | high | **The system is 24 thermocouples; the board has 8** (owner, 2026-09-29). **Direction agreed 2026-10-01** (`0024`): three identical, autonomous 8-channel modules, each tripping its own relay. The owner still has to answer one question: one machine (all three contacts in series) or separate groups (one contact per machine). Either answer is panel wiring only, so this no longer blocks ordering the module. | The owner has answered the grouping question; the panel wiring drawing shows it |
| I-073 | high | **Unsafe ACK after a save-failure recovery.** `protection.c:159` resets the trip without checking temperatures. With readings rising past the limit, 7 loop iterations permit RUN while it is hot. It was reproduced (`firmware/tests/reproductions/repro_save_ack.c`), and the code was read and confirmed 2026-09-30. The fix is small: fall through to the normal temperature check. | Fix + regression in the normal host test gate; `firmware/build.ps1` passes |
| I-074 | medium | **A healthy boot latches a CH1 FAULT that needs an ACK,** while the display says SAFE (the output is correctly off). This is the driver's first-sweep "settling" meeting the app. Repro: `repro_boot.c`. Latching on boot may be desirable; showing SAFE is not. | Startup policy chosen (latch-and-show, or wait for the first valid sweep); display and output agree; regression added |
| I-082 | medium | **`program.ps1` warns about a wrong image but flashes it anyway** (line 139 → 162). The legacy images have the opposite output logic. | It refuses an incompatible image; the technician package holds only the approved image, its hash and the fuses |
| I-070 | low | `version.h:16` still says REV A0; the board is A2. | Aligned when I-073 is fixed |

## P2 — measure at the bench when boards arrive

| # | Sev | Issue | Close when |
|---|---|---|---|
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
| I-025 | low | The two-layer backup `hardware/8ch-2layer/` is parked and now a revision behind A2. | Deleted or regenerated if 4-layer turns out unobtainable |
| I-026 | low | Ungrounded (insulated) junction probes would remove the cranking-current path between cylinders at no cost. | Specified at probe purchase |
| I-046 | medium | Konnect is AGPL-3.0; exposure today is zero (nothing distributed, no Konnect code in the repo). | Settled before shipping anything built around Konnect |
| I-054 | low | kicad-tool clones inherit the donor's MPN; `check_mpn_consistency.py` in `validate.ps1` catches it. | kicad-tool fixed upstream |
| I-056 | medium | Doc-system review (2026-09-17). The file-size and row-length parts are handled by `0025`. Still open: a dated evidence log, a decisions index, requirement-to-evidence traceability. | Those three exist, or are explicitly declined |
| I-071 | medium | `.github/workflows/hardware.yml:53` still checks against the A1 baseline. | CI uses `netlist-baseline-reva2.json` |
| I-084 | low | CI runs fewer checks than local `validate.ps1` (no DRC, parity or MPN check). | CI runs the same subset, or the difference is documented |
| I-083 | low | `build.py` needs git history (base `05d6abd`); a source ZIP cannot regenerate the schematic. Not wrong, just coupled. | The release notes name the base commit, or the base is kept as a file |
| I-072 | low | Stale overview text: `hardware/8ch/README.md` (TSR 1-2450), firmware comments on feedback. | Reconciled |
| I-087 | low | The Proteus project simulates a MAX6675, not the fitted MAX31856, so it proves nothing about the real sensor path (review 2026-09-29). | Updated, or labelled as legacy |
| I-055 | low | New parts added by `populate_schematic.py` land at the old +284 mm offset; this only matters before the layout pass. | Generator offset removed |
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
