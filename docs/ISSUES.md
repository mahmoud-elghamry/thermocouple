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
| I-078 | medium | **The order package is not uploadable yet.** **Done:** every line coded (`0027`): 5 exact-MPN codes; K1 is now G5LE-14 DC24, C53 is now the Rubycon YXF; U12 is XP IA0505S from DigiKey, hand-fit. The owner decided: factory fits SMD, the technician fits all THT (unless the factory THT price difference is small), 3 boards. **Left:** the fab choice; add the DIP-40 socket, LCD and cable, shunts and the `0020` fuse to a technician kit list; export BOM/CPL in the fab's format (SMD only); review the fab's matching page and preview with the owner. | Fab chosen; fab-format files exported; screenshots reviewed with the owner |
| I-079 | medium | **`production/8ch-reva2/RELEASE.txt` said the K1 coil is ~2.9 kOhm.** The G5LE-1 DC24 coil is **1.44 kOhm ±10 %** at 23 °C (16.7 mA; `datasheets/G5LE-relay.pdf`). The 2.9 came from an old I-058 text, copied without checking. The package is marked on hold. | The re-exported package's RELEASE text uses 1.44 kOhm |

## P1 — before a unit protects a machine

| # | Sev | Issue | Close when |
|---|---|---|---|
| I-085 | high | **The system is 24 thermocouples; the board has 8** (owner, 2026-09-29). **Direction agreed 2026-10-01** (`0024`): three identical, autonomous 8-channel modules, each tripping its own relay. The owner still has to answer one question: one machine (all three contacts in series) or separate groups (one contact per machine). Either answer is panel wiring only, so this no longer blocks ordering the module. | The owner has answered the grouping question; the panel wiring drawing shows it |
| I-074 | medium | **A healthy boot latches a CH1 FAULT that needs an ACK,** while the display says SAFE (the output is correctly off). This is the driver's first-sweep "settling" meeting the app. Repro: `repro_boot.c`. Latching on boot may be desirable; showing SAFE is not. | Startup policy chosen (latch-and-show, or wait for the first valid sweep); display and output agree; regression added |

## P2 — measure at the bench when boards arrive

| # | Sev | Issue | Close when |
|---|---|---|---|
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
| I-025 | low | The two-layer backup `hardware/8ch-2layer/` is parked and now a revision behind A2. | Deleted or regenerated if 4-layer turns out unobtainable |
| I-026 | low | Ungrounded (insulated) junction probes would remove the cranking-current path between cylinders at no cost. | Specified at probe purchase |
| I-046 | medium | Konnect is AGPL-3.0; exposure today is zero (nothing distributed, no Konnect code in the repo). | Settled before shipping anything built around Konnect |
| I-054 | low | kicad-tool clones inherit the donor's MPN; `check_mpn_consistency.py` in `validate.ps1` catches it. | kicad-tool fixed upstream |
| I-056 | medium | Doc-system review (2026-09-17). The file-size and row-length parts are handled by `0025`. Still open: a dated evidence log, a decisions index, requirement-to-evidence traceability. | Those three exist, or are explicitly declined |
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
