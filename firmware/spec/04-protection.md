# 04 - Protection: states, rules, outputs, master fault table

Decided behaviour: `0043` sections 3 and 8 (owner-approved table). Architecture: `01` sections 2.3, 2.4, 4, 5.
This file is normative for `channel_eval`, `protection`, `outputs` and the fault registry.

## 1. The one principle

**Opening needs no proof; closing needs full proof.**

* RUN opens as soon as *any* single valid result, fault or doubt says so - per channel, per slot, without waiting
  for the rest of the scan.
* RUN stays closed only while every condition of section 6.1 holds at the same time, re-proven by every validated
  board scan.

## 2. Inputs to protection (per board scan, plus immediate per-slot calls)

| Input | From | Notes |
|---|---|---|
| `meas[ch]` `{temp_dC, emf_nV, scan_no, flags}` | `scan` (`03`) | flags: `VALID`, `OPEN`, `RANGE`, `CM_FAIL`, `ADVISORY_RATE`, `ADVISORY_STUCK` |
| bank status per bank | `scan` | `VALIDATED` or the bank fault codes of `03` |
| `scan_validated` (whole board) | `scan` | all banks validated in this scan (`03` section 10.2), with the active settings sequence it was evaluated under |
| fault registry | drivers, scan, store, outputs | entries by (code, unit) (`01` 4) |
| active settings | `settings` | `const`, validated (`05`) |
| key commands | `ui` mailbox | `ACK`, `COMMIT_SETTINGS` |
| read-back pins | `outputs` | RUN_SENSE (PC2), ALARM_SENSE (PC7) |

## 3. Channel evaluation (`channel_eval`, pure)

Evaluated for every channel result the moment the slot result arrives (`eval_channel(ch, result, settings)`),
and again at the end of each board scan for markers.

### 3.1 Channel condition

| Order | Test | Condition |
|---|---|---|
| 1 | type == OFF | `OFF` |
| 2 | result not fresh, or `VALID` not set, or `OPEN`/`RANGE`/`CM_FAIL` set | `FAULT` (fault code from the flag: C01/C02/C03) |
| 3 | `temp_dC >= trip_SP` | `OVER_TRIP` |
| 4 | `temp_dC >= alarm_SP` | `OVER_ALARM` |
| 5 | otherwise | `NORMAL` |

Advisory flags (rate, stuck; I-098) never change the condition; they only add an LCD/Modbus advisory.

### 3.2 Action by mode (owner-approved truth table, `0043` 3.2)

| Condition | TRIP mode | ALARM ONLY mode | OFF |
|---|---|---|---|
| `OVER_TRIP` | **trip** + alarm | alarm | - |
| `OVER_ALARM` | alarm | alarm | - |
| `FAULT` | **trip** + alarm | alarm | - |
| `NORMAL` | - | - | - |

### 3.3 Reset (clear) conditions, used by ACK

* Trip cause of a TRIP-mode channel is clear when the channel is `NORMAL` or `OVER_ALARM` **and**
  `temp_dC <= trip_SP - band`.
* Alarm cause of any channel is clear when the channel is `NORMAL` **and** `temp_dC <= alarm_SP - band`, or the
  channel is now `OFF`.
* ALARM ONLY channels never block ACK of a trip (they cannot cause one).

## 4. Global protection state machine (`protection`)

States: `CONFIG_LOCK`, `START_LATCHED`, `RUN`, `TRIPPED`, `SERVICE`. RUN contact may be closed **only in `RUN`**, with one exception: the confirmed one-second bench relay test of
`08` A03/A04 in `SERVICE` (pump started by the service step itself, Timer2 deadline 1000 ms, stopped
unconditionally at the end of the step or on any key).
ALARM relay: section 7.

| From | Event / condition | To | Actions |
|---|---|---|---|
| (boot) | settings invalid or calibration invalid | `CONFIG_LOCK` | event `POWER_UP`, raise G01/G10 |
| (boot) | ACK+SET held at power-up | PIN recovery (`06` 5.3), then as below | event `PIN_RESET` |
| (boot) | SET held at power-up (`08`) - **takes precedence over settings validity**, so a blank board can be serviced | `SERVICE` | event `SERVICE_ENTRY` |
| (boot) | otherwise | `START_LATCHED` | cause `START` (power-up, WDT, BOD per reset flags), event |
| `CONFIG_LOCK` | valid settings committed (`05`) and calibration valid | `START_LATCHED` | cause `SETTINGS` |
| `START_LATCHED` | ACK accepted (section 5) | `RUN` | event `ACK` |
| `RUN` | any trip action (3.2), any trip fault (9) | `TRIPPED` | capture first-out (4.1), event `TRIP` |
| `TRIPPED` | ACK accepted | `RUN` | event `ACK`, clear first-out |
| `RUN`, `START_LATCHED`, `TRIPPED` | protection settings committed (`06` confirm screen) | `START_LATCHED` | cause `SETTINGS`, event `SETTINGS_CHANGED` |
| any except `SERVICE` | settings become invalid (read-back/CRC at runtime) | `CONFIG_LOCK` | raise G01 |
| `SERVICE` | (none) | - | left only by reset |
| any | state variable not one of the five, or its complement check fails | `TRIPPED` | raise G04 |

Notes:

* There is no separate "setup inhibit" state: committing a protection setting moves to `START_LATCHED` *before*
  the store writes (RUN opens first), and the new ACK is required after the write is verified.
* Names (not protection settings) commit without leaving the current state.
* Evaluation continues in every state: new trips/alarms/faults are detected, displayed and logged while latched.

### 4.1 First-out

On the transition into `TRIPPED` (or the first trip cause seen while in `START_LATCHED` after an ACK attempt
failed), record `{cause_code, ch or 0, temp_dC, threshold_dC, uptime_s}`. Later causes are logged as events but do
not replace the first-out. Cleared only by an accepted ACK. Survives a reset? **No** - after a reset the start
cause is `START`; the trip itself is already in the event log (`05`).

## 5. ACK acceptance

An `ACK` command from `ui` is accepted only if **all** hold; otherwise it is refused with the first failing reason
(shown on the LCD for 3 s, codes for `06`):

| # | Rule | Refusal code / LCD text |
|---|---|---|
| 1 | state is `START_LATCHED` or `TRIPPED` (in `RUN`, ACK only clears cleared alarms, 7.2) | - |
| 2 | the key press is fresh: ACK was seen released after boot, after the last trip and after any power-up gesture, held >= 50 ms (`06` 2); a queued ACK expires after 500 ms or on any trip or settings change | `R1 RELEASE ACK KEY` |
| 3 | the latest board scan is validated, completed less than 1500 ms ago, and was evaluated under the **current** settings sequence (a scan straddling a settings switch does not count) | `R2 WAIT FOR SCAN` |
| 4 | no trip-action global/bank fault is active (section 9) | `R3 FAULT Gnn/Bnn` |
| 5 | every TRIP-mode fitted channel is clear per 3.3 | `R4 CH nn HOT/FAULT` |
| 6 | settings valid and not being written | `R5 SETTINGS` |
| 7 | RUN and ALARM read-back consistent with "off" right now | `R6 RELAY CHECK` |

Accepted ACK in `START_LATCHED`/`TRIPPED`: go to `RUN`; also clear every alarm latch whose cause is clear (7.2).

## 6. RUN output contract (`outputs`)

### 6.1 Conditions to keep RUN closed (all at once)

1. state == `RUN` (stored as value + complement; both must agree);
2. a **RUN window** is open: it is (re)opened to `T_WIN = 1500 ms` only by a validated board scan processed in
   state `RUN` with no trip action; it is never extended by anything else;
3. no trip fault active;
4. flow check of `01` 2.3 passing (otherwise the watchdog resets the MCU anyway).

If any fails, `outputs` stops the PB3 PWM (timer output disconnected, pin driven low) in the same loop.
**Expiry of the RUN window while in `RUN` is itself a trip**: protection enters `TRIPPED` with cause G05 at that
moment, so a later validated scan can never re-close the contact without an ACK. The
window is a countdown owned by the Timer2 ISR (`02` 4.2): only the protection path reloads it (one atomic
write with interrupts disabled); the ISR stops the pump when it reaches zero.
Restarting the PWM requires condition 2 to be re-established by a *new* validated scan. **ACK ordering:** an
accepted ACK enters `RUN` with the window closed and its expiry timer started at the ACK; the PWM starts only when
the next validated scan opens the window, and if none arrives within `T_WIN` the expiry trip (G05) applies. "Next"
means a scan whose completion is processed in a later loop pass than the ACK: a scan completing in the same pass
as the ACK never opens the window. **Settings sequence:** the window is refreshed only by a scan tagged with the
active settings sequence; the single exception is a names-only commit made while in `RUN`, after which a scan
tagged with the sequence just replaced is also accepted, until the first scan with the new sequence. An active
sequence that changed without a commit seen by protection refreshes nothing (the window expires -> G05).
**OFF channels:** channel faults (C01-C09) on a channel set to OFF are ignored for alarm, trip and ACK alike.

`T_WIN` = 1500 ms > one normal scan cycle (~690 ms, `03`) and > the worst measured gap between validated scans (~1.07 s with loop jitter and the REF self-test) with margin for the bench (900 ms, then 1200 ms until the owner 2026-10-24 after Astra measured a 1230 ms gap between validated scans under loop jitter (I-132); owner: limits like Murphy); set from the scan time
measured on the first boards (service step P15) and recorded. A stalled scan opens RUN within `T_WIN` + pump decay
(< 1.55 s), so even a stall at the moment of a real over-temperature meets the 2 s requirement. Over-temperature
seen in a result does not wait for the window: it opens RUN immediately (section 1).

### 6.2 Read-back

RUN_SENSE (PC2) reads low when the coil is energised (10k from the coil low side, `hardware/24ch/gen/c_out.py`).
After any commanded change, wait `T_SETTLE = 60 ms` (pump rise/decay ~10-30 ms + RC), then compare every loop:

| Commanded | RUN_SENSE | Meaning | Action |
|---|---|---|---|
| on | low | ok | - |
| off | high | ok | - |
| on | high for > 100 ms | relay not pulling in (driver/pump/coil open) | G06, trip (RUN already ineffective), alarm |
| off | low for > 100 ms | coil still energised (shorted FET) - contact may stay closed | G06, alarm; accepted hardware limit (I-081), shown as `RUN STUCK ON` |

The same scheme for ALARM_SENSE (PC7) -> G07.

### 6.3 Timing budget, threshold crossing to contact open (24-ch, worst case)

| Step | Time |
|---|---|
| crossing happens just after the channel's slot started; next conversion of this channel | <= one gap between validated scans: ~690 ms normal, ~1.07 s worst measured (`03` 3.1, 10.2); G05 at 1500 ms |
| that conversion (single-cycle settled) | included above |
| read, CRC, conversion, `eval_channel` -> trip | < 5 ms |
| `outputs` stops PWM (same loop) | < 5 ms |
| charge-pump decay to relay drop-out | 15-30 ms (`CALCULATIONS` 8.5) |
| G6K release time | <= 3 ms (datasheet max) |
| **total** | **~0.75 s normal, ~1.1 s worst estimate** (a stall: `T_WIN` + decay < 1.55 s) incl. the filter allowance of `CALCULATIONS` 9.7 (requirement 2 s, GOAL; to be measured, I-013) |

Open-thermocouple detection is slower by design: burnout is checked on one channel per scan (each channel about
every 6 s, `03`). An open TC also drives the reading to a rail (`RANGE`), which trips at the next conversion.

## 7. ALARM output contract

### 7.1 Polarity (decided here)

**Energised = no alarm.** The ALARM relay is energised while no alarm is active and the system is healthy; it
drops on alarm, at reset, power loss or a dead board. The installer wires the alarm lamp/horn across COM-NC so a
dead board also signals. At reset the relay is off (100k gate pull-down, `c_out.py`), i.e. "alarm" until the first
validated scan in a non-alarm state. Rejected: energised = alarm (a dead board would look healthy).
Installation drawing (I-085) must state "ALARM: COM-NC closed = alarm".

### 7.2 Alarm latch

* Alarm is active when any channel has an alarm or trip action (3.2), any fault with alarm action (section 9) is
  active, the state is not `RUN`, or an alarm latch is set.
* An alarm latch is set per cause (channel or fault code) when it first becomes active.
* ACK (in any state, rule 2 of section 5 applies) clears the latches whose cause is clear (3.3); latches with an
  active cause stay, and their warning stays on the LCD.
* In `START_LATCHED`, `TRIPPED`, `CONFIG_LOCK` and `SERVICE` the alarm is always active.

## 8. Protection step (pseudo-code)

```
on slot result (ch):                         # immediate path, section 1
    c = eval_channel(ch, meas[ch], settings)
    if action(c, mode[ch]) has TRIP: enter_tripped(cause=ch)     # PWM stopped in the same loop
    if action has ALARM: set_alarm_latch(ch)

on fault raised (code, unit):                # immediate, any time
    if action has TRIP: enter_tripped(cause=code)   # latch set now; condition recovery never clears it
    if action has ALARM: set_alarm_latch(code, unit)
    (a fault whose condition later disappears is cleared in the registry; the trip latch stays until ACK)

on board scan complete:
    for each fitted ch: re-evaluate (markers, clear tests)
    (fault actions are NOT deferred to here: see 'on fault raised')
    if state == RUN and scan_validated and no trip action and no trip fault:
        run_window_open_until = now + T_WIN
    handle mailbox command (ACK / COMMIT) with fresh data      # section 5, 4
    update first-out, events (transitions only)
outputs (every loop):
    pwm_enable = state==RUN && now < run_window_open_until && !trip_fault && state_complement_ok
    alarm_energise = !alarm_active && state==RUN
    read-back checks (6.2)
```

## 9. Master fault table

Action: **T** = trip (RUN open, latched, alarm) for all channels; **TB** = trip, attributed to a bank;
**TC/AC** = per channel, trip or alarm depending on the channel's mode (3.2); **A** = alarm only, latched;
**I** = information/event only. "Clears" = when the condition is gone the fault deactivates; trips and alarm
latches still need ACK.

| Code | Name | Detected by (spec) | Action | LCD text (<= 20) |
|---|---|---|---|---|
| G01 | settings invalid / blank | settings (`05`) | T, `CONFIG_LOCK` | `LOCKED: SETUP` |
| G02 | save failed: protection settings or calibration | store (`05`) | T until a retry succeeds | `SAVE FAILED` |
| G13 | save failed: names, comms or PIN only; or event entries lost in a burst (`05` 7) | store (`05`) | A until a retry succeeds / the queue drained and ACK | `SAVE FAILED (INFO)` |
| G14 | island power lost (all banks fail together) | scan (`03`) | T; full re-init | `ISLAND POWER LOST` |
| G15 | fuse bytes differ from `02` | boot self-read (`02` 6) | T, never clears (reprogram) | `FUSE MISMATCH` |
| G03 | flash CRC at boot | boot (`02`) | halt with outputs safe | (LCD may be blank) |
| G04 | protection state/complement corrupt, stack canary | protection, loop (`01`) | T | `INTERNAL FAULT` |
| G05 | complete-scan deadline missed | scan (`03`) | T | `SCAN TIMEOUT` |
| G06 | RUN coil-drive feedback mismatch | outputs (6.2) | T + A | `RUN RELAY FAULT` |
| G07 | ALARM read-back mismatch | outputs (6.2) | T + A | `ALARM RELAY FAULT` |
| G08 | engine reference lost (REFOK high) | scan (`03`) | T | `ENGINE REF LOST` |
| G09 | engine reference self-test (REFTEST) failed | scan (`03`) | T | `ENGINE REF TEST` |
| G10 | calibration record invalid or a fitted channel has no burnout baseline | settings (`05`), scan (`03`) | T, `CONFIG_LOCK` | `LOCKED: CALIBRATE` |
| G11 | reset by watchdog | boot | I (start latched anyway) | `RESET: WATCHDOG` |
| G12 | reset by brown-out | boot | I | `RESET: LOW SUPPLY` |
| B01 | ADC no response / wrong ID | ad7124 (`03`) | TB | `BANK x ADC FAIL` |
| B02 | ADC SPI CRC repeated | ad7124 | TB | `BANK x COMMS` |
| B03 | ADC register read-back mismatch | ad7124 | TB | `BANK x CONFIG` |
| B04 | ADC error register set | ad7124 | TB | `BANK x ADC ERROR` |
| B05 | ADC conversion stalled | scan | TB | `BANK x STALLED` |
| B06 | reference cross-check out of window | scan | TB | `BANK x REF` |
| B07 | AVDD out of window | scan | TB | `BANK x AVDD` |
| B08 | zero check out of window | scan | TB | `BANK x ZERO` |
| B09 | non-zero or gain-ratio check out of window | scan | TB | `BANK x GAIN` |
| B10 | both CJ sensors invalid | tmp126 (`03`) | TB | `BANK x CJ FAIL` |
| B11 | CJ sensors disagree | scan | TB | `BANK x CJ DIFF` |
| B12 | one CJ sensor invalid | tmp126 | TB in v1 (A only after bench qualification, `0043` 3.4) | `BANK x CJ DEGRADED` |
| B13 | device signature mismatch (all boards; decoder aliasing on the 40-ch) | scan (`03` 9) | T | `ADDRESS FAULT` |
| B14 | 40-ch RTD bank failure | rtd (`03`) | T | `RTD BANK FAIL` |
| C01 | open thermocouple (burnout) | scan | TC/AC | `CH nn OPEN` |
| C02 | out of range for its type / probe limit | tc_math | TC/AC | `CH nn RANGE` |
| C03 | common-mode check failed | scan | TC/AC | `CH nn COMMON MODE` |
| C04 | rate advisory - reserved, not implemented in v1 (I-098 thresholds unvalidated) | - | - | - |
| C05 | stuck advisory - reserved, not implemented in v1 | - | - | - |
| C06 | burnout lower window (shorted input) | scan (`03` 4.1) | TC/AC | `CH nn SHORTED` |
| C07 | input over/under-voltage flag | ad7124 | TC/AC | `CH nn OVERVOLT` |
| C08 | implausibly cold (< -50 C) | tc_math | TC/AC | `CH nn TOO COLD` |
| C09 | PT100 fault (40-ch, 41-43) | rtd (`03` 8) | TC/AC | `CH nn RTD FAULT` |
| C10 | cause only (not a fault): over trip setpoint | channel_eval | (first-out/event cause) | `CH nn OVER TRIP` |
| C11 | cause only (not a fault): over alarm setpoint | channel_eval | (event cause) | `CH nn OVER ALARM` |
| B15 | unexpected ADC reset (POR flag) | ad7124 (`03` 2.4) | TB; re-init | `BANK x ADC RESET` |

Codes never change meaning once released; new faults get new numbers.
