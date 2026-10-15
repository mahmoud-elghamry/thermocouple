# 0041 - 24-ch REV A4: gated TMP126 SIO driver, PD5 taken from the ESC button

* Status: accepted (owner, 2026-10-15: fix it now, before the order, rather than test A3 at the bench;
  take the ESC pin; keep five buttons with the diode trick so the family looks the same)
* Date: 2026-10-15
* Branch: `24ch-rev-a4` (worktree `.claude/worktrees/24ch-rev-a4`); the issue row (I-124) and the new
  boards' circuit (`0039` P2, `hardware/family`) are on `main`, not in this branch yet
* Supersedes: `0036` D1 on the TMP126 write path (R443 22k DIN-DOUT); `CALCULATIONS` 8.3
* Builds on: `0036` (TMP126, CA-IS3761HW), `0029` (button arrangement is a design-team choice)

## Context

On REV A3 every TMP126 command bit reaches SIO through R443 22k. With ~62-85 pF on DOUT_ISO the SIO
edge is ~1.2-1.6 us (30-70 %); TMP126 datasheet SNIS209C 7.6 gives tRISE/tFALL 100 ns maximum.
R443 also loads AD7124 DOUT ~150 uA against the 100 uA VOH test point. TI's own typical application
(9.2, 10k isolation resistor) cannot meet 100 ns either, so A3 may well work at the planned 62.5 kHz,
but the owner did not want to order boards that might be scrapped and could not easily run the
proposed bench test (scope + 10^6 reads hot and cold). The new 8/40-ch boards already use a gated
driver; the 24-ch had no free MCU pin.

## Decisions

**D1 - Circuit: the same as the new boards.** U411 74LVC1G125 (SOT-23-5, TI, C23654) drives DIN_ISO
onto SIO through R446 220R only while SIO_WR_N_ISO is low; R445 10k keeps OE high while the isolator
powers up (the CA-IS3761 output also defaults high); R447 100k biases DOUT when everything is
deselected; C421 100n. **R443 removed**; R446 reuses its footprint. SIO edge ~20 ns, DOUT load
~33 uA (`CALCULATIONS` 8.5). BOM +1 line (C23654), 96 lines.

**D2 - Enable pin: PD5 (was BTN_ESC) -> SIO_WR_N -> U405 spare channel C (pin 4 in, pin 13 out),
R439 10k pull-up (MCU reset).** Rejected:
* order A3 as is, relying on firmware CRC/retry - the owner would rather not risk a scrapped batch;
* LCD_RS shared while LCD_E is low (Astra's path) - a standing firmware rule, contention if broken;
* REFTEST shared - pulses would discharge the REF_SENSE filter (1k into 100n) and fake a broken wire;
* RS485_DE, RUN_SENSE, ALARM_SENSE - needed (RS-485 fitted again, relay read-back is safety);
* a 74HC138-style CS decoder to free pins - re-wires nine chip selects across the isolators;
* a 4-wire CJ sensor (ADT7310, MAX31723) - six footprints beside the terminals where there is no room
  (I-114), dearer;
* R443 down to 10k - edge only halves, DOUT load doubles.

**D3 - ESC button kept through two diodes.** D501/D502 1N4148W (C83528, already on the BOM): ESC
(SW504, J503 pin 4) pulls BTN_UP and BTN_DOWN low together; the firmware reads UP+DOWN as ESC on every
board of the family. Same five buttons and the same panel header as the 8/40-ch boards. Rejected: four
buttons (ESC = cancel by timeout / UP+DOWN) - simpler, but the 24-ch would look different from the
family; a BAT54C dual diode - one more BOM line for no gain.

**D4 - Layout, incremental (`0012`).** `delta.py` with `R443>R446`; U411, C421, R445 in the only free
island area (between banks A and B, ~81.5/114 mm, U411 straddles the DIN trunk with pin 2 on it);
R447 beside R446; R439 beside U405; D501/D502 beside J503. The old BTN_ESC route from PD5 is re-netted
to SIO_WR_N (38 segments), its leg to SW504 removed. A DIN branch that fed only R443 pad 1 removed.
`maze.py` with In2 allowed: SIO_WR_N_ISO uses 4.5 mm of In2 (+3V3_ISO plane); In1 (GND_ISO) uncut.
TC traces untouched. New island nets added to class Island in `thermo24.kicad_pro`.

## Firmware requirements (for the family firmware, I-100)

* TMP126 frame bit-banged. **Read:** SIO_WR_N low for the 16 command bits, high after the 16th rising SCLK
  edge and before the falling edge after which the TMP126 drives SIO. **Write:** SIO_WR_N stays low through
  the command, the data and the optional CRC (the host drives all of it; R447 would otherwise pull the bus
  high). Never low while any AD7124 CS is low. (Astra review 2026-10-15, TMP126 8.5.2.)
* Read every TMP126 with CRC enabled; a failed CRC -> re-read; trip only on repeated failure.
* Buttons: UP and DOWN low together = ESC (all boards).
* RUN_PERMIT charge pump: PWM >= 1 kHz (100 Hz does not hold the 2N7002 on), toggled only by completed scans
  (I-118); AD7124 SPI <= 2 MHz through the isolators; REF_EN = 1, no REFIN2 (AIN14/15 are TC inputs).
  (Reviews 2026-10-15, `CALCULATIONS` 8.5.)

## Review 2026-10-15 (4 Claude reviewers + Astra twice, `production/review-20261015-a4/`)

No pinout, net, package, missing-part or value error that blocks the order. Fixed: mirrored terminal labels,
stale REV/DNP text, missing ASSEMBLY-SPEC.pdf, J601 pin wording in I-085. Left as accepted, optional (owner's
no-over-engineering rule): ADM2587E pins 2/1 and 19/20 have 10 nF where ADI pairs 10 nF + 100 nF (rails have
100 nF elsewhere; RS-485 is not in the trip path); REF3030 C413 100 nF (TI text says 0.1 or > 0.47 uF; it is
only the cross-check reference); crystal load 22 pF vs CL 20 pF (oscillates, small frequency offset).

## Consequences

* A3 release `4b1601` and its quotes are superseded for ordering; REV A4 release
  `production/24ch-reva4-20261015-195548-b4c4e2`: DRC (errors, refilled, schematic parity) 0/0/0.
* Needs a new JLCPCB/NORI quote. On merge: sweep the I-124 row, README, STATE index.
