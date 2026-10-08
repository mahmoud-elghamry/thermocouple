# 0030 — REV A3: three stacked modules, per-channel probe bias, signal contact, work split

* Status: accepted (owner, 2026-10-08); engineering items marked "verify" still open
* Date: 2026-10-08
* Deciders: owner; plan reviewed by Codex gpt-6.1-sol (read-only,
  `production/review-20261008/codex-plan-review.md`, local)
* Relates to: `0024`, `0028`, `0029`, `0009`, `0008`, `0020`; I-026, I-085, I-091,
  I-092, I-094, I-096, I-097, I-100

## Facts from the owner, 2026-10-08

* All 24 probes are on **one engine** today. Each 8-channel module must also
  work **alone on its own engine**: a module is a self-contained product.
* The probes are made to order; **no model number exists**. Junction type is
  **unknown and may be mixed**. The owner's hand-held multimeter readings were
  ~47 ohm wire-to-sheath on one probe (not repeatable, later OL), and >= 1 Mohm
  on another. They were taken with fingers on the probe tips and possibly on
  the over-braid, so **they do not classify the probes**.
* The dry contact only carries a **signal**. It never switches 220 V, and the
  current is low.
* Space matters: no three large boards side by side.

## Decisions

**D1. Three identical 8-channel modules, stacked on spacers.** They are
joined by a short header or ribbon carrying RS-485 and the supply. Rejected:
one 24-channel board. It would be a new design, one failure would take out
24 channels, and every probe would share one isolated island.

**D2. Each module trips on its own; the three COM-NO contacts are in series.**
The link between modules is never in the trip path. No message can grant
RUN, clear a trip or bypass protection; loss of comms never grants RUN.
I-081 (welded contact or shorted driver) stays an accepted limit.

**D3. Non-isolated RS-485 between stacked modules** (transceiver + TVS, DE low
at reset, defined termination/bias). This is valid **only inside one panel on
one battery**. A module used alone on another engine does not get a
non-isolated link to another engine. Closes the direction of I-094. The
current saving from removing the ADM2587E must be re-derived (I-096); it is
not assumed.

**D4a. Display, buttons and ACK: on identical main boards, no extra PCB (owner, 2026-10-08).** The panel door is not modified.
* **All three boards are the same PCB and the same assembly.** Each carries
  the setup buttons, the ACK button, a keyed LCD header, the stack header,
  its ACK fan-out diode and a role/address jumper. On the lower boards the
  buttons are simply unused.
* **The 20x4 LCD module is fitted only on the master** (the top board), on
  four standoffs above it. The board reserves the standoff holes and an LCD
  keep-out with no tall parts under it. The buttons sit outside the LCD
  outline so they stay reachable. A module used alone fits its own LCD.
* **ACK fan-out:** the master's ACK button pulls one ACK line in the stack
  header low. Each board meets that line through **its own diode** (cathode
  to the line, anode to its ACK input, pull-up to its own 5 V). An unpowered
  board then neither sources nor sinks current, and ACK never travels over
  RS-485. This needs bench qualification.
* **Floor-plan constraints this creates:**
  * A 20x4 module is roughly 98 x 60 mm. On a 100 x 100 mm board it covers
    most of the top face, so the terminals must stay outside its outline.
  * In a stack, the screws of the lower boards' terminals are under the
    board above. **Pluggable terminal blocks** (the plug is wired off-board,
    then pushed in from the side) or side-screw terminals are therefore
    likely needed.
  * The floor plan decides whether 100 x 100 holds. If it does not, a
    16x2 LCD or a slightly larger board are the fallbacks, both shown to the
    owner.
* Dropped idea: a separate small HMI board (owner did not want a second PCB).
* To ask the operations engineer: is opening the door to read the display and
  press ACK acceptable? Nothing is asked of him to change.

**D1a. A single 24-channel board stays rejected (owner, 2026-10-08).** The
terminals set its size: 24 x ~15 mm three-screw blocks is ~360 mm of edge
(~240 mm with the shield bonded at panel entry). Even split over two edges,
that is a board of roughly 120-180 mm by ~130 mm, near today's 250 x 140 mm
area, against ~100 x 100 mm of panel footprint for the stack. It is a rough
estimate, not a placement study. It would also be a new design: one MCU and
isolator set for 24 converters, and 24 BIAS outputs on one island.
**Kept as a later option (owner):** once the three-module system works, a
24-channel board may be designed as a second product variant. It is not on
the REV A3 path.

**D4. One display + keypad, on the top module (master role).** It shows all
24 channels, and setpoints and options for every module are set there. Every
module keeps its own setpoints in its own EEPROM. A write carries **module
address, channel, value and a transaction id**, and is CRC-checked and read
back. The display marks stale or missing data. **The role and address come
from a jumper/DIP on identical hardware running one firmware image**, not
from a different firmware per position: a wrong image must not be able to
change a module's protection (I-082). A module used alone uses its own
LCD/buttons.

**ACK** is one push-button on the master, fanned out by diodes (D4a), never sent over RS-485. The three ACK inputs are never joined directly, because that would backfeed into an unpowered module. The firmware keeps release-before-press and requires fresh local readings before ACK. (Superseded idea: a panel button with three separate NO contacts, dropped with the door change.)

**D5. Signal relay with gold-clad contacts** replaces the G5LE-14 DC24.
Marked rating: **30 VDC / 1 A maximum, signal loads only**. The minimum
load, the inductive-load limits, the coil supply, pickup/dropout, the driver,
the flyback and the R53/R54 read-back are verified from the chosen part's
datasheet before placement.

**D6. Probe bias: a per-channel option, plus one reference point per
module.** Today BIAS (pin 2) is hard-tied to T- (pin 3) in all eight
channels.
* Per channel, **one 0805 footprint between BIAS and T-**, **fitted with 0 ohm
  by default**. That is the datasheet's floating-probe circuit and today's
  behaviour.
* **Per module, one reference terminal** from the sensor island to the engine
  block (its own wire). Grounded channels have their 0 ohm removed and take
  their common mode through the engine from this one point. That way a broken
  probe cable cannot leave the other channels floating. **The reference
  circuit is a proposal and needs bench qualification.**
* Why: with grounded probes, the engine joins all eight T- lines, so all
  eight BIAS outputs (0.735 V and 2 kohm, typical only) fight. An outlier
  10 mV high drives about 4 uA and gives **about 10 degC of error, possibly
  reading LOW**. Arithmetic: `CALCULATIONS.md` 6.
* What a wrong fit does (first-order, unverified):

  | Probe | 0 ohm fitted | 0 ohm removed |
  |---|---|---|
  | floating | correct (datasheet circuit) | input floats: wrong reading or a fault; must be shown to trip, not read plausibly |
  | grounded | works, but BIAS fight: degrees of error, either sign | correct, if the module reference is connected |

  No configuration damages anything: the currents are microamps.
* The **simplest supported configuration** is verified insulated probes with
  the 0 ohm fitted. Grounded or mixed probes are a **bench-qualified
  installation variant**. If that qualification fails, per-channel isolation
  or a grounded-input front end is reconsidered before ordering.
* **Changing the converter alone does not fix this.** Any front end that
  drives its own bias onto each probe on a shared island has the same
  problem.
* Rejected: one universal resistor value (e.g. 100 kohm) for both probe
  types. Its effect on open-circuit detection and on the 0.5-1.4 V
  common-mode range is unverified (MAX31856 p.14).

**D7. 100 x 100 mm, 4 layers, is the target.** It must be proven by a
to-scale floor plan before any board write (`0028`). The floor plan must show
terminal access with the boards stacked (72 TC terminal positions across
three modules), clearances over the tallest part, and no buck or relay of one
board under another board's TC terminals or converters.

**D8. Per-channel persistent setpoints (I-100) and timing (I-097).**
* EEPROM records are versioned, written atomically, and recovered safely. An
  invalid configuration prevents RUN. The old single limit is **not**
  silently copied to eight channels.
* Scan timing is gated by elapsed time and readiness (first conversion up to
  185 ms), not by "skip one scan".
* Sensor-fault latency is specified separately: auto open-detection runs
  about every 1.6 s.
* The watchdog is fed only when protection makes progress (`WDTO_500MS` is
  about 0.52 s typical).

## Also required before REV A3 is frozen

* **Panel fuse for three modules** (`0020` sized it for one). Three modules
  charging together give roughly 9 x the single-module I²t, about 1.25 A²s
  against the >= 1 A²s requirement. Re-size the fuse, or fuse each module.
  `CALCULATIONS.md` 1.9 and 6.
* Power budget re-derived for an ordinary module and for the master (I-096);
  F1 and L1 re-checked against the LM5164 current limit.
* Fixed module address and role inputs; duplicate-address detection; SRAM
  audit on the master (ATmega32A, 2 KB).
* The local `ATmega32A.pdf` appears truncated. Obtain a complete copy before
  any pin review or package change.

## Work split (AGENTS.md rules 3, 8, 9)

| Worker | Does | Never touches |
|---|---|---|
| **W1, Claude Code on the workstation** | The only writer of `hardware/8ch/` (schematic, board, generator): floor plan first, shown to the owner, then REV A3 | — |
| **W2, Codex on the workstation** | Calculations and project documents (power, fuse, `CALCULATIONS.md`, decisions); core firmware (per-channel limits, EEPROM, timing, ACK) | hardware sources |
| **W3, Claude Code cloud session** | RS-485 protocol, supervisor and master display, in **new** firmware files and tests, on a `claude/*` branch, delivered by PR | existing files, hardware |

W1 reviews every W2 diff and every W3 PR before a commit. **Only the owner
merges a PR.** Each task's acceptance gates are in `docs/TOOLS.md`.
