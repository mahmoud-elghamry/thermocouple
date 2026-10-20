# 0043 - Family firmware plan (8/24/40-ch): features, safety logic, menus, phases

* Status: **proposed, rev 2** (plan only, no code). Rev 1 2026-10-20; rev 2 the same day after Astra review 4
  (`production/review-20261015-a4/ASTRA-4-firmware-plan-report.md`, local): 11 blockers and 10 "should" folded
  in. Owner decisions in section 8 still open.
* Builds on: `0029` (per-channel setpoints, manual ACK), `0030` D8 (config lock), `0031` (architecture; Modbus never
  in the trip path; D5 alarm relay), `0032` (ADC diagnostics, engine reference, charge pump), `0034` (open sensor
  trips, alarm only, buttons), `0036`, `0037` (one firmware), `0038` (K or J per channel), `0039` (8/40-ch,
  decoder, PT100), `0041` (TMP126 SIO_WR_N, UP+DOWN = ESC), `0042` (LCD and buttons on the door); ISSUES I-100,
  I-104, I-118, I-119, I-098, I-086, I-094, I-013, I-114, I-120
* Reference products: Murphy TDXM-DC (per-channel setpoints, TC type per channel incl. "ignore", last-trip
  history, Modbus RTU), Dynalco SC-2124M (4x20 LCD, channel names, password setup, open-TC detection).

## 1. Goal and scope

One firmware image per board type (build-time `BOARD=8|24|40`), ATmega1284P at 8 MHz: what an engine technician
expects from a TDXM-class scanner, under the safety rules already fixed in this repo. The bench test of the first
boards is **a service mode of this firmware**, so the code tested on the bench is the code that ships.

Out of scope for v1: Modbus writes, analog outputs, RTC, Fahrenheit, non-English LCD text, deviation alarms and
operator offsets (section 8), more than one PIN level.

## 2. Channels and settings

### 2.1 Per channel (saved; see 5 for storage rules)

| Setting | Values | Blank-board default | Notes |
|---|---|---|---|
| Fitted / type | OFF, K, J; PT100 on the 40-ch RTD inputs | none -> config lock (`0030` D8) | type change: RUN inhibited, setpoints re-confirmed, old samples discarded, ACK (`0038` D2) |
| Mode | TRIP / ALARM ONLY | TRIP | truth table in 3.2 |
| Name | 6 chars, shown with the fixed channel number (`01 CYL1A`) | blank | |
| Alarm SP | 0..probe limit, 1 C | none -> config lock | |
| Trip SP | alarm SP < trip SP <= probe limit | none -> config lock | |
| Reset band | 2..50 C | 5 C | used for trip reset and alarm clear |
| Probe limit | per channel, entered at commissioning | type's table max | bounds both SPs (`0038`) |

No temperature is ever invented (I-100). No trip delay: every validated result is compared at once (GOAL 1 s,
I-013).

### 2.2 Global

Modbus address and baud (9600/19200); one setup PIN; production calibration record (REF ratio per bank, `0032`).

## 3. Protection logic

### 3.1 Validated scan (what may refresh RUN)

A scan of a bank is **validated** only if, for that scan: every ADC read had a good SPI CRC; the ADC ID/revision,
configuration registers and error register read back as written; the MCLK/conversion counter advanced; each
channel result carries a fresh sequence tag from this scan; the diagnostic slots of 4.2 passed; both TMP126 of the
bank were read with good CRC (or the degraded rule of 3.4 applies). A failed read is retried at most twice in the
same scan; then the bank is FAULT. The **whole board scan** is validated when every bank is. Over-temperature
evaluation uses hardware-valid results only and is never suppressed by advisory checks (I-098).

### 3.2 Channel truth table

| Condition | TRIP channel | ALARM ONLY channel | OFF channel |
|---|---|---|---|
| value >= trip SP | trip + alarm | alarm | ignored |
| alarm SP <= value < trip SP | alarm | alarm | ignored |
| sensor fault (open TC, out of range, burnout fail) | trip + alarm | alarm | ignored |
| needed for ACK | valid and <= trip SP - band | valid or not: does not block ACK | no |

Global instrument faults (3.3) trip regardless of channel modes.

### 3.3 Global faults -> trip + alarm

ADC missing / wrong ID / configuration readback mismatch / repeated CRC; REF cross-check or AVDD out of window;
engine reference lost (REFOK, PA2, active-low) or REFTEST self-test failed (4.3); both CJ of a bank invalid or
disagreeing (3.4); 40-ch decoder signature mismatch (4.4); RTD bank failure on the 40-ch (4.5); complete-scan
deadline missed; settings invalid; RUN or ALARM read-back mismatch.

### 3.4 Cold junction

Both TMP126 of a bank read every scan (ID 0x2126, CRC, re-read once on CRC fail, value <= 2 scans old). The two
must agree within a window set from the bench gradient test (I-114). One valid and one invalid: the bank keeps
running on the valid one, status DEGRADED CJ on the LCD and ALARM; the error of this fallback is measured on the
bench before it is accepted (until then the stricter rule is: trip). Both valid but disagreeing: trip.

### 3.5 Latch, ACK and startup

* Any trip opens RUN within one scan and latches. Power-up, reset, brown-out and watchdog reset all start latched:
  `START: ACK REQUIRED` (`0029`). No automatic restart.
* ACK is accepted only: from a fresh press (the key must be seen released after boot, after the trip and after
  any service/recovery gesture); with the latest validated scan younger than one scan; every TRIP-mode fitted
  channel valid and <= trip SP - band; no global fault; settings valid. Otherwise the LCD says why.
* While latched, evaluation continues: new trips, alarms and faults are still detected, displayed and logged; the
  first-out stays at the top.
* **Alarm relay** (`0031` D5, ALARM_DRIVE PC6, read-back PC7): polarity as on the board (energised = no alarm,
  so a dead board alarms - to confirm against the schematic in F0). Latches until ACK after the condition has
  cleared by the reset band; an active warning stays on the LCD after ACK. Read-back mismatch -> global fault.

### 3.6 RUN output and watchdog

PB3 charge-pump PWM >= 1 kHz runs only while (a) the protection latch permits RUN and (b) a deadline window,
refreshed by each validated board scan, has not expired (I-118). Watchdog <= 0.5 s, enabled first thing at
start-up (WDTON set, so it cannot be disabled - no long delays before the main loop), fed only when acquisition
has advanced, never from an ISR (I-119); a separate complete-scan deadline catches a loop that advances but never
completes. Fuses: WDTON, BOD, JTAG off (+ MCUCR.JTD), EESAVE (I-104).

### 3.7 Settings while running (owner decision 8.1, proposed)

All protection settings (type, mode, setpoints, band, probe limit) only with RUN inhibited and a new ACK after
saving; names may be edited live. This is a new, simpler policy than `0038` D2 (which covers type changes only).
"RUN inhibited" means the contact is open; it does not prove the engine has stopped.

## 4. Measurement

### 4.1 Banks

8-ch = 1 bank, 24-ch = 3 (direct CS), 40-ch = 5 + RTD ADC (74HC154). AD7124: SPI mode 3 <= 2 MHz, CRC on, REF_EN = 1,
no REFIN2, mid power, 25 SPS, one CS low at a time, >= 1 us between CS edges, no continuous read. Banks in
parallel. TMP126 bit-banged with the SIO_WR_N timing of `0041`; SIO_WR_N never low while an AD7124 CS is low.

### 4.2 Slot schedule per bank (15 slots, CALCULATIONS 9.7, ~0.70 s cycle)

8 TC channels; REF3030 cross-check at gain 1 (calibrated ratio, window +-1.6 % provisional); zero (shorted input);
non-zero / PGA gain-ratio check; AVDD/6; rotating common-mode check (one channel per scan); rotating burnout (one
channel per scan, upper and lower window plus a per-channel baseline learned at commissioning; burnout readings
never used as temperature); one spare slot for the gain-ratio second reading. Open-TC coverage is therefore about
every 8 scans (~6 s), not 1 s; a sensor that fails open between checks still reads implausibly (rail) and trips.
K/J in voltage domain with NIST tables, CJ converted with the same type; CJ per channel interpolated between the
bank's two sensors by pin position (I-114).

### 4.3 Engine reference

REFOK (PA2, active-low) checked every scan; REFTEST (PA3) self-test at start-up and every N minutes, with the
sequence of `0032` rev 4. Cut FEED, cut SENSE and a failed self-test each inhibit RUN (bench test in I-120).

### 4.4 40-ch decoder

Sequence: CS_EN high, >= 1 us, set address, >= 1 us, CS_EN low, >= 1 us, clock (`0039` D3). At start-up each ADC
and TMP126 gets a unique value written to a spare register; every scan that value is read back, so an aliased
address is caught even between identical parts. Island power loss (either isolator side) -> full re-init and RUN
inhibited until a fresh, fully validated scan.

### 4.5 40-ch PT100 bank

3 x 3-wire PT100 + one 150R 0.1 % check resistor (slot 4) on the RTD ADC; IOUT 2 x 250 uA swapped every reading;
Rref 2.49k, gain 16; ~2.3 ms reference settling and filter restart after every current change, no conversion
spanning a change; reference and gain checks; a currents-off reading detects sheath faults (`0039` P4/P5,
CALCULATIONS 10.11). Check-resistor or reference failure invalidates the whole RTD bank (global fault).

### 4.6 Advisory checks

Rate and stuck checks (I-098) are display-only advisories until bench thresholds exist; they never mark a sample
invalid and never suppress the over-temperature comparison.

## 5. Settings and event storage

A/B records with version, board type, channel count, explicit serialisation (no C structs), CRC16, and semantic
checks (type, mode, ranges, alarm < trip <= probe limit, board identity). Save = write the older copy, read back,
then switch; a failed save keeps the old copy active, latches a fault until a retry succeeds and ACK. Blank or
invalid -> config lock, RUN never granted, ACK cannot clear it. EEPROM budget allocated in CALCULATIONS (to add:
names, probe limits, calibration, event ring) and channel masks as byte arrays (40-ch > 32 channels).
Events: transitions only (trip with channel, cause, value, threshold; alarm; fault; ACK; power-up; setting change),
32 entries, stamped with uptime and a power-cycle counter; trip history kept after ACK.

## 6. Screens and keys (20x4)

* Home: line 1 status (`RUN OK`, `ALARM 2`, `TRIP 03 CYL3B`, `START: ACK REQUIRED`, `LOCKED: SETUP`,
  `DEGRADED CJ`, `SERVICE`); lines 2-4 six channels per page with markers (`!` alarm, `#` trip, `?` fault,
  `-` off, `a` alarm-only). UP/DOWN pages; optional automatic page rotation with hold.
* Channel detail: number + name, type, mode, value, SPs, min/max since ACK, CJ.
* Events list; first-out with cause, value and threshold at the top until ACK.
* Setup (hold SET 3 s + PIN): Channels / Comms / Service / PIN / Exit. Edits on a copy, confirm screen old -> new,
  save and read back. A new trip always takes over the screen, even inside a menu.
* Keys: UP, DOWN, SET (short = enter/confirm, long = setup), ESC (24-ch: UP+DOWN chord, `0041` D3; 8/40-ch: ESC
  pin and the chord), ACK. Chord wins over single keys; release-before-press rule of 3.5. HAL to be adapted for
  20x4 addressing and ESC (the 8-ch HAL is 16x2 with NEXT).
* One setup PIN; recovery: hold ACK+SET at power-up -> RUN inhibited, PIN reset to the default, settings kept,
  event logged.

## 7. Service mode, structure and phases

**Service mode** (hold SET at power-up, separate from setup): RUN never closes on entry. Passive part, automatic:
board type, fuse readback, each ADC ID/registers/AVDD/REF ratio, each TMP126, each channel raw uV + temperature +
burnout, scan time, keys (press each), REFOK/REFTEST. Active part, each step confirmed on the keypad and only with
the contacts disconnected (shown on the LCD): RUN and ALARM drive + read-back; EEPROM test on a scratch area that
never touches commissioned settings. Plain-text report on RS-485 (9600 8N1, Modbus off in this mode) and on the
LCD, each line `OK` or `FAIL <reason>`; Claude reads it on the PC through the USB-RS485 adapter.

Reuse from `firmware/` (8-ch REV A2): MCAL/HAL/APP layering, source lists, host-mock tests, protection
latch/ACK concepts, CRC settings pattern. Replace: board map, MAX31856 driver, scalar setpoint, static RUN level,
2 s watchdog and the start-up that disables it, ATmega32 fuses/programming, 16x2 LCD, button set.

Modules: `board_cfg`, `iso_spi`, `ad7124`, `tmp126`, `rtd` (40-ch), `scan`, `tc_math`, `channel_eval`,
`protection`, `outputs`, `settings`, `events`, `ui`, `modbus`, `service`.

| Phase | Content | Gate |
|---|---|---|
| F0 | ATmega1284P programming + fuses + early watchdog; board_cfg, iso_spi, ad7124, tmp126, scan with all diagnostic slots, tc_math; minimal outputs (RUN off/latched, read-back), calibration storage, 20x4 diagnostic display; service mode | host tests; cold start and watchdog-reset start on the bench; service report all OK on the first boards |
| F1 | channel_eval, protection (3.1-3.6), settings A/B, events | table-driven host tests of every rule in 3; fault injection: stalled acquisition with timers running, held keys, power cut during save, partial island power, aliasing (40-ch); bench: trip <= 1 s, ACK rules; Astra review before engine use |
| F2 | ui screens, setup menus, PIN | bench walk-through by the owner's technician |
| F3 | Modbus read-only map (fn 3/4; signed 0.1 C, validity/age, type, mode, faults, actual RUN, first-out; all writes rejected), flood/malformed-frame test | Modbus poll test; I-120 matrix |

Implementer: Sol per phase with host tests; Claude reviews and runs the gates; Astra reviews F1.

## 8. Owner decisions (Astra's recommendation in brackets)

1. Protection settings only with the contact open and a new ACK; names live [yes].
2. Alarm relay latches until ACK after the condition clears [yes].
3. Deviation-from-average alarm: not in v1, add if the technicians ask [defer].
4. Per-channel offset: none in v1; production calibration only [omit].
5. 6-char names next to the channel number [yes].
6. Modbus read-only in v1 [yes].

Rejected: trip delay (breaks the 1 s rule); startup bypass timer (only for low setpoints); two PIN levels and
challenge-response recovery (I-100 needs a lock, not roles); "hottest" screen (channels have different limits);
separate test firmware (service mode instead).
