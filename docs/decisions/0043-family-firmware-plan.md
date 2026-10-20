# 0043 - Family firmware plan (8/24/40-ch): features, safety logic, menus, phases

* Status: **proposed** (plan only, no code; owner 2026-10-20: "plan first, Astra reviews, then pick the implementer")
* Date: 2026-10-20
* Builds on: `0029` (per-channel setpoints, manual ACK), `0031` (architecture, Modbus never in the trip path),
  `0032` (ADC diagnostics, charge pump), `0034` (open sensor trips, alarm only, buttons), `0036`, `0037` (one
  firmware), `0038` (K or J per channel), `0039` (8/40-ch, decoder, PT100), `0041` (TMP126 SIO_WR_N, UP+DOWN = ESC),
  `0042` (LCD and buttons on the door); ISSUES I-100, I-104, I-118, I-119, I-098, I-086, I-094, I-013, I-120
* Reference products: Murphy TDXM-DC (per-channel SP1-SP3, TC type per channel incl. "ignore", offset, group
  deviation from average, last-trip history, Modbus RTU fn 3/6), Dynalco SC-2124M (4x20 LCD, channel names,
  password setup, open-TC detection, alarm/shutdown classes). Sources in the review folder; the official TDXM-DC
  manual (00-02-0511) could not be fetched, so TDXM details are from an older manual.

## 1. Goal and scope

One firmware image per board type (build-time `BOARD=8|24|40`), ATmega1284P at 8 MHz, that does what an engine
technician expects from a TDXM-class scanner, plus the safety rules this project already fixed. The first boards'
bench test is **a service mode of this firmware**, not a separate program, so the code tested on the bench is the
code that ships.

Out of scope for v1: remote writes over Modbus, analog outputs, real-time clock, Fahrenheit, languages other than
English on the LCD (HD44780 has no Arabic glyphs).

## 2. What the technician sees (operator features)

### 2.1 Per-channel settings (saved, CRC-checked, A/B copies)

| Setting | Values | Default (blank board) | Who may change |
|---|---|---|---|
| Fitted / type | OFF (not fitted), K, J (PT100 on the 40-ch RTD inputs) | none - board is config-locked until set (`0030` D8) | Engineer |
| Mode | TRIP (alarm + shutdown) / ALARM ONLY | TRIP | Engineer |
| Name | 6 chars, e.g. `CYL1A`, `EXH-L` | `CH01`.. | Technician |
| Alarm setpoint (high warning) | 0..probe max, 1 C steps | none - must be entered | Technician |
| Trip setpoint (high shutdown) | > alarm SP, <= probe max | none - must be entered | Technician |
| Reset band (hysteresis) | 2..50 C | 5 C | Technician |
| Trip delay | 0..5 s (in whole scans) | 1 scan | Engineer |
| Offset | -5..+5 C | 0 | Engineer (shown on the channel screen when not 0) |
| Deviation group | none / A / B | none | Engineer |

No temperature is ever invented: a fitted channel without both setpoints keeps the config lock (I-100).

### 2.2 Global settings

Deviation alarm per group (alarm only, never trip in v1): a channel more than `dev` C from its group's average of
valid channels, enabled only above a group average of `dev_min` C (so a cold engine does not alarm). Modbus address
and baud (9600/19200). Technician and engineer PINs. Display contrast is hardware (pot), not firmware.

### 2.3 Screens (20x4)

* **Home** (default, returns here after 60 s without a key): line 1 status
  `RUN OK` / `ALARM 2` / `TRIP CYL3B` (first-out) / `LOCKED: SETUP`; lines 2-4 six channels per page
  `01 512K 02 498K` with a marker per channel (`!` alarm, `#` trip, `?` fault, `-` not fitted). UP/DOWN pages.
* **Hottest**: the 3 highest valid channels with names.
* **Channel detail** (SET on home, then pick): name, type, mode, value, alarm/trip SP, min/max since reset, CJ.
* **Events**: last 32 events (trip, alarm, fault, ACK, power-up, setting change) with an uptime stamp and the
  power-cycle count (no RTC). First-out trip stays at the top until ACK.
* **Menu** (hold SET 3 s): Setpoints / Channel setup / Groups / Comms / Service / PINs / Exit.

### 2.4 Keys

UP, DOWN scroll and change values; SET enters / confirms; ESC back (24-ch: UP+DOWN together, `0041` D3; 8/40-ch:
read the ESC pin if fitted and also accept UP+DOWN, so all boards behave the same); ACK acknowledges.
Edits are made in a copy and need a confirm screen showing old -> new before they are saved and read back.

### 2.5 Access levels

* Operator, no PIN: view, ACK.
* Technician PIN: names, alarm/trip setpoints, reset band.
* Engineer PIN: type/fitted, mode, delay, offset, groups, comms, service mode, PIN change.
* PIN recovery: hold ACK+SET at power-up -> shows a code; the engineer gets the reset from the documented
  procedure. Factory default PINs are printed in the installation drawing (I-085) and must be changed at
  commissioning.

## 3. Protection logic (the part that must be right)

Per channel, each validated scan gives one of: OK, ALARM, TRIP, FAULT (open TC, out of range, ADC/CJ diagnostic
failure for its bank).

* **Trip**: value >= trip SP for `delay` consecutive validated scans, or FAULT on a TRIP-mode channel.
  Any trip -> RUN contact opens within one scan (<= 1 s budget, I-013) and stays open (latched).
* **Alarm**: value >= alarm SP, deviation alarm, FAULT on an ALARM-ONLY channel, or any trip. Alarm relay as in
  `0031` D5; alarm latches until ACK.
* **ACK** clears a latched trip only when every fitted channel is valid and at or below (trip SP - reset band),
  no global fault is active and the settings are valid. ACK with a condition still present is refused, and the
  LCD says why.
* **Global faults -> trip** (all channels): ADC missing / wrong ID / CRC errors repeated / REF cross-check fail /
  AVDD out of window; both CJ sensors of a bank failed; scan deadline missed; settings invalid; RUN read-back
  mismatch. One CJ of a bank failed -> use the other for that bank and raise ALARM (not trip).
* **Power-up / reset / brown-out / watchdog**: RUN off, latched; ACK needed (`0029`). No automatic restart.
* **RUN output**: PB3 charge-pump PWM >= 1 kHz is (re)enabled only for a window that each completed, validated
  scan refreshes; if the window expires the PWM stops and the contact drops (I-118). Watchdog <= 0.5 s, fed only
  from scan progress, never from an ISR (I-119). WDTON, BOD, JTAG off, EESAVE (I-104).
* **Settings changes while running**: proposed (owner decides, see 7): alarm SP, names and LOWERING a trip SP may
  be edited while running; RAISING a trip SP, type, mode, fitted, delay and offset need RUN inhibited (engine
  stopped) and an ACK afterwards (`0038` D2 requires RUN inhibited for type changes).
* **Modbus never grants RUN, clears a trip or writes settings in v1** (`0031` D7, I-086, I-094).

## 4. Measurement (fixed by earlier decisions, restated for the implementer)

* Banks of one AD7124-8 + two TMP126; 8-ch = 1 bank, 24-ch = 3 (direct CS), 40-ch = 5 + RTD ADC (74HC154).
* AD7124: SPI mode 3 <= 2 MHz, CRC on every read, REF_EN = 1, no REFIN2, mid power, 25 SPS. Banks run in parallel.
  Scan schedule per bank: 8 TC + burnout(rotating) + REF + zero + non-zero + common-mode(rotating); slot count
  (13-15) to be fixed by the implementer from CALCULATIONS 9.7 and recorded; target cycle <= 0.75 s.
* TMP126 bit-banged with SIO_WR_N timing of `0041`; ID 0x2126; CRC on; re-read on CRC fail; 0x0000 = 0 C.
  CJ per channel interpolated between the bank's two sensors by pin position (I-114).
* K/J conversion in voltage domain with NIST tables (5 C steps, ~2.5 KB), CJ converted with the same type.
* Open-TC: burnout current rotating one channel per scan; burnout readings never used as temperature.
* Plausibility (I-098): rate/stuck checks raise ALARM only until bench-validated thresholds exist.

## 5. Service mode (= the bench test of the first boards)

Entered by holding SET at power-up; RUN stays inhibited for the whole session. Prints a plain-text report on
RS-485 (9600 8N1, same pins as Modbus, Modbus off in this mode) and shows it on the LCD:
board type, fuse/bootloader check, each ADC ID/revision/error reg/AVDD/REF ratio, each TMP126 ID and value,
each channel raw uV + temperature + burnout result, button states (press each key), relay drive and read-back
test (RUN and ALARM toggled once with readback), EEPROM A/B write-read test, scan time measured. Every line ends
`OK` or `FAIL <reason>`. Claude reads this report directly on the PC through the USB-RS485 adapter.

## 6. Software structure and phases

Reuse from `firmware/` (8-ch REV A2): layering MCAL/HAL/APP, source lists, host-mock tests, protection latch/ACK
and CRC-settings concepts, LCD and button HAL. Replace: board map, MAX31856 driver, scalar setpoint, static RUN
level, 2 s watchdog, ATmega32 fuses/programming.

Modules: `board_cfg` (per-board pins, CS strategy direct/decoder), `iso_spi` (CS, timing, SIO_WR_N),
`ad7124`, `tmp126`, `scan` (schedule, deadline), `tc_math` (K/J/PT100), `channel_eval`, `protection`,
`outputs` (charge pump window, alarm relay, read-back), `settings` (A/B, explicit serialisation, versioned),
`events` (EEPROM ring), `ui` (screens, menus, PIN), `modbus` (read-only map), `service`.

| Phase | Content | Gate |
|---|---|---|
| F0 | board_cfg, iso_spi, ad7124, tmp126, scan, tc_math, service mode | host tests; runs on the first boards; service report all OK |
| F1 | channel_eval, protection, outputs, settings, events | host tests of every rule in section 3 (table-driven), fault injection; bench: trip <= 1 s, ACK rules, power-cut, watchdog |
| F2 | ui screens, menus, PINs | bench walk-through by the owner's technician |
| F3 | modbus read-only map, deviation alarm | Modbus poll test; I-120 matrix |

Each phase: code + host tests by the implementer (Sol), review and gates by Claude, Astra review of F1
(protection) before it runs on an engine.

## 7. Decisions the owner should confirm

1. Settings while the engine runs: proposed split in section 3 (safe-direction edits live, the rest with RUN
   inhibited) vs `0038`'s stricter "RUN inhibited for any settings change".
2. Alarm relay latches until ACK (proposed) vs follows the condition.
3. Deviation alarm in v1 as alarm only (proposed) vs not at all vs allowed to trip.
4. Offset per channel +-5 C (TDXM has it; proposed engineer-only and shown) vs none.
5. Names on the LCD (6 chars) - yes proposed.
6. Modbus read-only in v1 - proposed.

Rejected: startup bypass timer (only needed for low setpoints; v1 has high setpoints only); Fahrenheit; RTC
(events use uptime + power-cycle count); separate test firmware (service mode instead).
