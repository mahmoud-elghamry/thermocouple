# 03 - Protection: channel and global state machines, latch/ACK, RUN and ALARM outputs, fault list

**DRAFT - research input, not the final spec** (owner, 2026-10-20). Follows `00-overview.md` conventions. Source
of decided behaviour: `docs/decisions/0043-family-firmware-plan.md` rev 2, sections 2, 3 and 8 (section 8 table
owner-approved 2026-10-20). Where this draft goes further than 0043 it says so and marks the point **OPEN** or
**PROPOSED**. Evidence is quoted as `file:line` or `CALCULATIONS n.m` (branch `main`).

Modules: `channel_eval` (per-channel logic, section 2), `protection` (global logic, sections 3-5, 8), `outputs`
(sections 6-7). Acquisition faults are referred to "from 02" by category; this file assigns their codes and
actions (section 9, master table).

---

## 1. Facts this file rests on (with evidence)

| # | Fact | Evidence |
|---|---|---|
| F1 | RUN_PERMIT (24-ch PB3, OC0A) drives the trip relay through a charge pump: R701 100R -> C704 100n -> BAT54S D703 -> gate node TRIP_GATE with C705 100n and R702 100k to GND -> Q701 2N7002 -> coil K701 low side. A static level on PB3 (high or low) cannot hold the relay. | `hardware/24ch/gen/c_out.py:8-19, 35-43, 60-61`; `0032` rev 4 item 2 |
| F2 | Gate voltage with the pump running: 1.4-2.9 V at 100 Hz (not enough), 3.8-4.1 V at 1 kHz, 4.1-4.2 V at 2 kHz; gate decays to 1 V 15-30 ms after the drive stops. UNVERIFIED on the bench. | `CALCULATIONS` 8.5 (charge-pump paragraph, Astra review 2) |
| F3 | Trip relay NO path = both poles in series (pin 3 -> 4 -> 6 -> 5); NC from pole 1 only. One welded pole cannot keep RUN; a shorted Q701 or two welded poles can (accepted limit). | `c_out.py:23-30`; `0032` rev 4 item 6; ISSUE I-081 |
| F4 | RUN_SENSE (24-ch PC2) = TRIP_LOW (coil low side) through R703 10k, C703 100n to GND. **Coil energised -> Q701 on -> TRIP_LOW near 0 V -> RUN_SENSE reads 0. Coil off -> TRIP_LOW pulled to +5 V through the coil -> RUN_SENSE reads 1.** Sense filter tau = 10k x 100n = 1 ms. | `c_out.py:49-51` (desc "read-back: low when the coil is energised") |
| F5 | ALARM_DRIVE (24-ch PC6) -> R711 100R -> ALM_GATE, R712 100k to GND -> Q702 -> coil K702. **Drive high = coil energised. MCU in reset (pins high-Z) -> R712 holds the gate low -> coil off.** No charge pump on the alarm relay (static drive). | `c_out.py:40-43` (desc "relay off while the MCU is in reset") |
| F6 | ALARM_SENSE (24-ch PC7) = ALM_LOW through R713 10k / C713 100n: **0 = coil energised, 1 = coil off**, same as F4. | `c_out.py:49-51`, `62-63` |
| F7 | Alarm contact J702: pin 3 COM, pin 2 NO, pin 1 NC (pole 1 only). Both contacts rated 30 VDC / 1 A, signal loads only. | `c_out.py:32, 52-54`; `0031` D5 |
| F8 | Each relay has an LED from +5 V (1.5k) to the coil low side, "lit while the coil is energised"; the alarm LED is labelled **ALARM**, the trip LED **RUN**. | `c_out.py:46-48, 61, 63` |
| F9 | The family boards (8/40-ch) use the same output circuit; only the RS-485 fitting note differs. | `git show main:hardware/family/gen/c_out.py` diffed against `hardware/24ch/gen/c_out.py`: one line (RS-485 block title) |
| F10 | Scan timing: 24-ch/8-ch bank cycle 15 slots x 44.559 ms = 668.4 ms, cycle screen ~700 ms, trip response screen ~775 ms; 40-ch ~745 ms / ~820 ms. All UNVERIFIED in firmware. | `CALCULATIONS` 9.7, 10.7 |
| F11 | WDTO_500MS is about 0.52 s typical; feed only on protection progress. | `0030` D8; `CALCULATIONS` 10.7 ("A <=0.5 s watchdog cannot be fed only once per ~0.745 s scan") |
| F12 | The 8-ch firmware stops evaluating once latched (`if (state == NULL \|\| state->latched) return;`), so a second trip during a latch is never seen; 0043 3.5 now requires continued evaluation. | `firmware/src/app/protection.c:139-141` |
| F13 | The 8-ch firmware treats a drive (read-back) fault as not ACK-clearable ("hardware has to be repaired and the unit power-cycled"). Kept. | `protection.c:223-228` |
| F14 | The 8-ch firmware disables the watchdog at start and runs WDTO_2S fed every loop pass. Replaced (I-119, 0043 3.6). | `firmware/src/app/main_8ch.c:99-100, 134, 139` |
| F15 | The 8-ch HAL drives RUN as a static level and the alarm output high = alarm on. Both replaced (F1, section 7). | `firmware/src/hal/run_permit.c:23-27`; `firmware/src/hal/alarm_output.c:15-19` |
| F16 | The 8-ch refusal text uses `'1' + channel` (breaks at channel 10, I-119). New text uses two-digit channel numbers. | `protection.c:40` |

---

## 2. Per-channel logic (`channel_eval`)

### 2.1 Inputs per channel

From 02, for each result: `{ch, temp_dC, scan_no, hw_valid, fault_bits}`. `hw_valid` = the read had a good SPI CRC,
the ADC status showed no error for that conversion and the conversion belongs to this channel (sequence tag).
`fault_bits` = channel faults C01-C09 (section 9). A result is **provisional** until its bank's scan is validated
(0043 3.1) and **validated** after.

From settings (04): type (OFF/K/J/PT100), mode (TRIP / ALARM ONLY), alarm SP, trip SP, reset band, probe limit.
In this file SPs are used in 0.1 C: `TSP = trip_sp_C * 10`, `ASP = alarm_sp_C * 10`, `BAND = band_C * 10`.

### 2.2 Condition state (instantaneous, with hysteresis)

One condition state per fitted channel. OFF channels have no condition state (always `CH_OFF`).

| State | Meaning |
|---|---|
| `CH_OFF` | type = OFF: not evaluated, never blocks ACK, never alarms |
| `CH_INIT` | fitted, no hw-valid result since boot or since its settings were applied (type change discards old samples, `0038` D2) |
| `CH_NORMAL` | valid, below alarm (with hysteresis) |
| `CH_ALARM` | valid, alarm condition held (>= ASP, not yet <= ASP - BAND), trip condition not held |
| `CH_HIGH` | valid, trip condition held (>= TSP, not yet <= TSP - BAND) |
| `CH_FAULT` | any channel fault C01-C09 active, or the bank of this channel has an active Bnn fault |

Transition table (evaluated on every hw-valid result and on every fault-bit change; `v` = `temp_dC`):

| From | Condition | To |
|---|---|---|
| any fitted | fault bit set (C01-C09) or bank fault active | `CH_FAULT` |
| `CH_INIT` | hw-valid result, no fault | per the "entry" rule below |
| `CH_FAULT` | all fault bits clear **and** the clearing diagnostic passed again (for C01/C02: the next burnout check of this channel; for others: the next hw-valid result) **and** the bank has no fault | per the "entry" rule below |
| `CH_NORMAL` | `v >= TSP` | `CH_HIGH` |
| `CH_NORMAL` | `ASP <= v < TSP` | `CH_ALARM` |
| `CH_ALARM` | `v >= TSP` | `CH_HIGH` |
| `CH_ALARM` | `v <= ASP - BAND` | `CH_NORMAL` |
| `CH_HIGH` | `v <= TSP - BAND` and `v >= ASP` | `CH_ALARM` |
| `CH_HIGH` | `v <= TSP - BAND` and `v <= ASP - BAND` | `CH_NORMAL` |
| `CH_HIGH` | `v <= TSP - BAND` and `ASP - BAND < v < ASP` | `CH_ALARM` (alarm hysteresis still held) |
| any | type set to OFF by a settings apply | `CH_OFF` |
| `CH_OFF` / any | type changed to K/J/PT100 by a settings apply | `CH_INIT` |

Entry rule (from `CH_INIT` or `CH_FAULT`; conservative, the band is treated as "not yet cleared"):
`v > TSP - BAND` -> `CH_HIGH`; else `v > ASP - BAND` -> `CH_ALARM`; else `CH_NORMAL`.

Notes:
* A provisional result may move a channel **up** (towards `CH_ALARM`, `CH_HIGH`, `CH_FAULT`) at once; it may move
  a channel **down** (clearing) only once its scan is validated. Trip early, grant late (0043 3.1: "never
  suppressed").
* `CH_INIT` that lasts more than one validated board scan after the channel's bank produced a validated scan sets
  C09 STALE (section 9). In practice `CH_INIT` exists only after boot and after a settings apply, both with RUN
  already off.
* Advisory faults (C10 RATE, C11 STUCK) never change the condition state (0043 4.6, I-098).

### 2.3 What each condition does, by mode (0043 3.2)

| Condition state | TRIP channel | ALARM ONLY channel | OFF |
|---|---|---|---|
| `CH_HIGH` | set `trip_latched`, set `alarm_latched`, request global trip | set `alarm_latched` | - |
| `CH_ALARM` | set `alarm_latched` | set `alarm_latched` | - |
| `CH_FAULT` | set `trip_latched`, set `alarm_latched`, request global trip | set `alarm_latched` | - |
| `CH_INIT` | blocks ACK; no latch by itself | does not block ACK | - |
| `CH_NORMAL` | nothing | nothing | - |
| Blocks a RUN-granting ACK? | yes unless `CH_NORMAL`/`CH_ALARM` with `v <= TSP - BAND` from a validated scan | never | never |

### 2.4 Per-channel latch flags

| Flag | Set by | Cleared by |
|---|---|---|
| `trip_latched` | TRIP channel entering `CH_HIGH` or `CH_FAULT` (in any global state except BOOT, SERVICE) | an **accepted RUN-granting ACK** (section 4) only |
| `alarm_latched` | any fitted channel entering `CH_ALARM`, `CH_HIGH` or `CH_FAULT` | an ACK request (fresh press, section 4.1) **while** the channel is `CH_NORMAL` on a validated scan; an ACK while the condition is still active leaves it set (0043 3.5, decision 8.2: "latches until ACK after the condition clears") |
| `minmax` (display) | every validated value | accepted RUN-granting ACK (min/max since ACK, 0043 section 6) |

LCD markers (0043 section 6) derive from these: `#` trip_latched, `!` alarm_latched or `CH_ALARM`, `?` `CH_FAULT`,
`-` OFF, `a` ALARM ONLY. Exact precedence is 05's.

---

## 3. Global protection state machine (`protection`)

### 3.1 States and outputs

| Code | State | RUN output (pump) | ALARM relay | LCD line 1 (<= 20 chars) |
|---|---|---|---|---|
| 0 | `BOOT` | stopped, PB3 low | de-energised (= alarm, section 7) | `STARTING` |
| 1 | `CONFIG_LOCK` | stopped | de-energised (G01 is trip + alarm) | `LOCKED: SETUP` |
| 2 | `START_LATCHED` | stopped | per alarm latches (section 7.3) | `START: ACK REQUIRED` (cause POWER_UP / RECOVERY) or `SETUP DONE: ACK` (cause SETUP) |
| 3 | `RUN` | running while the deadline window is open (section 6) | per alarm latches | `RUN OK` / `ALARM n` |
| 4 | `TRIPPED` | stopped | de-energised (a trip always sets an alarm latch) | first-out, e.g. `TRIP 03 CYL3B`, `TRIP G08` |
| 5 | `SETUP_INHIBIT` | stopped | per alarm latches | `SETUP: RUN OPEN` |
| 6 | `SERVICE` | stopped except during the active RUN step of 07 | de-energised except during the active ALARM step of 07 | `SERVICE` |

`latch_cause` is kept with `START_LATCHED`: `POWER_UP`, `RECOVERY` (ACK+SET gesture), `SETUP` (return from
setup). State codes 0-6 are used in events (04) and Modbus (06) and never change meaning.

`return_to` is kept with `SETUP_INHIBIT`: the state to return to (`START_LATCHED` or `TRIPPED`).

### 3.2 Transitions (complete list)

| # | From | Event / condition | To | Actions in the same step |
|---|---|---|---|---|
| T1 | any | reset of any kind (power-on, brown-out, watchdog, external) | `BOOT` | hardware: pins high-Z, pump stops, R702/R712 turn both relays off |
| T2 | `BOOT` | SET held at power-up (07 entry rule) | `SERVICE` | log `SERVICE_ENTER` |
| T3 | `BOOT` | settings load (04 section 4): no valid record, layout/board mismatch, or semantic failure | `CONFIG_LOCK` | raise G01; log `POWER_UP`, `FAULT_SET G01` |
| T4 | `BOOT` | settings valid | `START_LATCHED` (cause `POWER_UP`, or `RECOVERY` if the ACK+SET gesture was held) | log `POWER_UP` (and `RECOVERY`); disarm ACK (4.1) |
| T5 | `START_LATCHED` | accepted RUN-granting ACK (4.2) | `RUN` | clear trip latches, first-out; open the RUN window; log `ACK` |
| T6 | `TRIPPED` | accepted RUN-granting ACK | `RUN` | as T5 |
| T7 | `RUN` | trip request (2.3) or a fault whose action is trip (section 9) | `TRIPPED` | **stop pump first**, then capture first-out (4.4), log `TRIP` / `FAULT_SET`, disarm ACK |
| T8 | `START_LATCHED` | trip request or trip-action fault | `TRIPPED` | capture first-out (the start latch is replaced by the real cause), log, disarm ACK |
| T9 | `RUN`, `START_LATCHED`, `TRIPPED` | operator confirms entry to a protection-setting edit (05) | `SETUP_INHIBIT` | stop pump; `return_to` = `TRIPPED` if from `TRIPPED`, else `START_LATCHED`; log `SETUP_ENTER` |
| T10 | `SETUP_INHIBIT` | trip request or trip-action fault | stays `SETUP_INHIBIT` | capture first-out if none held; `return_to` = `TRIPPED`; log; UI shows the trip (0043 section 6: a new trip takes over the screen) |
| T11 | `SETUP_INHIBIT` | edit session ends (saved OK, or cancelled) and `return_to` = `START_LATCHED` | `START_LATCHED` (cause `SETUP`) | apply new settings (type change -> `CH_INIT`); disarm ACK |
| T12 | `SETUP_INHIBIT` | edit session ends and `return_to` = `TRIPPED` | `TRIPPED` | apply settings; first-out kept; disarm ACK |
| T13 | `SETUP_INHIBIT` | save failed (04 section 6) | stays `SETUP_INHIBIT` until a retry succeeds or the operator cancels; on cancel -> T11/T12 with G02 latched | raise G02, log `SAVE_FAIL` |
| T14 | `CONFIG_LOCK` | a complete, semantically valid settings record is saved and read back (04) | `START_LATCHED` (cause `SETUP`) | clear G01 condition; G01 latch cleared by the ACK of T5 |
| T15 | `SERVICE` | none: service mode is left by a power cycle only (**PROPOSED**, 07 to confirm) | - | - |

There is no transition from any state to `RUN` except T5/T6. Modbus has no transition (0031 D7, `00` owner rules).
A watchdog, brown-out or power-on reset always lands in `BOOT` and then `START_LATCHED` or `CONFIG_LOCK`: no
automatic restart (`0029`, I-074, I-089).

### 3.3 Continued evaluation while latched (0043 3.5)

In `CONFIG_LOCK` (as far as settings allow), `START_LATCHED`, `TRIPPED` and `SETUP_INHIBIT`, acquisition,
`channel_eval`, fault detection, alarm latching, event logging and display all keep running exactly as in `RUN`.
A new trip while latched sets the channel's `trip_latched` and `#` marker and is logged; the first-out does not
change (4.4). This replaces the 8-ch behaviour that stopped evaluating once latched (F12).

`CONFIG_LOCK`: channels have no valid settings, so no channel conditions are evaluated; global and bank faults are
still detected, shown and logged; the display may show EMF only (05). `BOOT` and `SERVICE` do not run protection.

---

## 4. ACK

### 4.1 Fresh press rule

An **ACK request** is generated only by a debounced released -> pressed edge of the ACK key, alone (no other key
held; chord rules in 05), while `ack_armed` is set. The request clears `ack_armed`.

`ack_armed` is set when the ACK key has been seen continuously released (debounced) for **>= 100 ms**
(**PROPOSED**, 05 owns debounce). It is cleared (disarmed) by each of:

| Disarm event | Why |
|---|---|
| reset / `BOOT` | a key held through power-up (or jammed) cannot ACK (0043 3.5) |
| any trip latch set (T7, T8, T10, and any new `trip_latched` while latched) | a key held when a trip happens cannot ACK it |
| entry to and exit from `SETUP_INHIBIT` | |
| the RECOVERY gesture (ACK+SET at power-up) and its release | the gesture's ACK press is not an ACK |
| every ACK request (accepted or refused) | one press, one request |

### 4.2 RUN-granting ACK: acceptance conditions

Evaluated at the moment of the request, in `START_LATCHED` or `TRIPPED`, against the most recent **validated
board scan** (`last_vscan`). All must hold:

| # | Condition | Refusal text (line 1, <= 20 chars) |
|---|---|---|
| A1 | state is `START_LATCHED` or `TRIPPED` (in `RUN` see 4.3; in `CONFIG_LOCK` refuse) | `NO ACK: SETUP LOCK` (CONFIG_LOCK), `NO ACK: IN SETUP` (SETUP_INHIBIT) |
| A2 | no power-cycle-only fault latched (G03, G05, G06) | `NO ACK: POWER CYCLE` |
| A3 | no G02 pending (save failed and no successful retry since) | `NO ACK: SAVE FAULT` |
| A4 | the last completed board scan was validated, completed less than `W_RUN` ago (6.2), and completed **after** the latest of: boot, the latest trip-latch event, the exit from `SETUP_INHIBIT` | `NO ACK: WAIT SCAN` |
| A5 | no global or bank fault **condition** active (Gnn/Bnn with action trip, section 9) | `NO ACK: G08` / `NO ACK: B06 A` (first active code, lowest number first) |
| A6 | every fitted TRIP-mode channel has a validated result from `last_vscan` and `v <= TSP - BAND`, and is not `CH_FAULT` or `CH_INIT` | `NO ACK: 03 HOT` or `NO ACK: 03 FAULT` (lowest channel number first; two-digit channel, F16) |
| A7 | ALARM ONLY and OFF channels: not checked | - |

On acceptance (T5/T6), in this order: set state `RUN`; clear every `trip_latched`; clear the first-out (it stays in
the event log, 0043 section 5); clear `alarm_latched` of every channel in `CH_NORMAL`; clear global fault latches
whose condition is clear; reset min/max; set the RUN deadline (6.2) from `last_vscan`; log `ACK`.

On refusal: nothing changes except the refusal text, which stays on line 1 until the next ACK request or until the
blocking reason changes (re-evaluated every validated scan, as the 8-ch `ack_refusal_refresh` does, I-088). Refusals
are not logged (not a transition; avoids ring wear from key mashing).

### 4.3 ACK in `RUN`

An ACK request in `RUN` clears `alarm_latched` for every channel in `CH_NORMAL` and every global alarm latch whose
condition is clear (G/B faults with action alarm, e.g. B12 once accepted). It never changes RUN. Logged as `ACK`
(detail = alarm-only) when at least one latch was cleared.

### 4.4 First-out capture

* `first_out` = `{code, channel, bank, value_dC, threshold_dC, scan_no, uptime_s}` is captured on the transition
  into `TRIPPED` (T7, T8) and on the first trip in `SETUP_INHIBIT` (T10) when none is held. `START_LATCHED`'s
  cause is not a first-out.
* For an over-temperature trip `code` = 0 (temperature), `threshold_dC` = TSP. For a channel fault `code` = Cnn,
  `value_dC` = last valid value or none. For Gnn/Bnn, `channel` = 0, `bank` set for Bnn.
* Ties inside one evaluation pass (several causes in the same result or the same scan summary): Gnn before Bnn
  before Cnn/temperature; lower bank, then lower channel number first; within one channel a fault before
  over-temperature. Per-result evaluation (section 8) makes most ties impossible: the first result processed wins.
* The first-out is shown at the top until an accepted RUN-granting ACK; later trips are visible as `#` markers and in
  the event list.

---

## 5. Settings while running (0043 3.7, owner decision 8.1)

| Change | RUN | After saving |
|---|---|---|
| type, mode, alarm SP, trip SP, reset band, probe limit (any channel) | must be in `SETUP_INHIBIT` (RUN open) before the edit starts | `START_LATCHED`/`TRIPPED` -> new ACK (A4 forces a new validated scan) |
| burnout baseline learning (04, calibration record) | `SETUP_INHIBIT` | new ACK |
| production calibration (REF ratio) | `SERVICE` only | power cycle, then ACK |
| channel name, Modbus address/baud, PIN | live, no effect on RUN | - |

"RUN inhibited" means the contact is open; it does not prove the engine has stopped (0043 3.7).

---

## 6. RUN output contract (`outputs`)

### 6.1 Pump

* PB3 (OC0A on the 24-ch; pin per board in 01) runs a hardware-generated square wave, 50 % duty, **>= 2 kHz**
  (F2: 1 kHz gives 3.8-4.1 V gate, 2 kHz 4.1-4.2 V; the extra margin costs nothing). Suggested 4 kHz; the timer
  setting is 01's.
* Stopped = timer output disconnected from the pin (COM0A bits cleared) **and** the pin driven low as an output.
  The pin is written low before it is made an output at init (as the 8-ch `run_permit.c:8-11` already does).
* The pump is **started** only by `outputs_run_start()`, called only by `protection` on T5/T6. It is **stopped** by
  `outputs_run_stop()` (any exit from `RUN`), by the deadline check (6.2), by reset (pins high-Z), and by a read-back
  fault (6.3).

### 6.2 Deadline window (I-118)

* `run_deadline_ms` (u32) is written only by `protection`: at T5/T6 to `t(last_vscan) + W_RUN`, and after each
  validated board scan completed while in `RUN` to `t(completion) + W_RUN`. Written with interrupts disabled (u32
  on AVR is not atomic).
* The 1 ms timer ISR compares `ms_tick` with `run_deadline_ms` and calls the pump stop when the deadline has passed.
  The ISR may **stop** RUN; nothing in an ISR may start RUN or feed the watchdog (I-119). The main loop also checks
  the deadline before every protection step.
* An expired deadline raises **G07 SCAN DEADLINE** (trip, latched): T7.
* `W_RUN` = measured worst-case board-scan period + 100 ms, never more than 1000 ms. **Provisional 900 ms** for all
  boards (24-ch screen 700 ms, 40-ch 745 ms, F10). **OPEN**: set from the scan time reported by service mode on the
  first boards.

### 6.3 RUN read-back (RUN_SENSE, F4)

| Commanded | Expected RUN_SENSE after settling | Mismatch means |
|---|---|---|
| pump running | 0 (coil energised) | coil not energised: pump/gate/Q701 open, coil supply lost. Contact already open (safe side) |
| pump stopped | 1 (coil off) | Q701 shorted or gate held: **RUN cannot be opened by firmware** (I-081) |

* Settle time after any command change: **50 ms** (gate decay 15-30 ms, F2; relay operate/release; sense RC 1 ms).
* After settling, RUN_SENSE is sampled every main-loop pass (pass interval <= 10 ms, a constraint on every other
  module). A mismatch that persists on every sample for **20 ms** raises **G05** (trip + alarm, latched, cleared by
  power cycle only; F13). On G05 the pump is stopped (if it was running) and stays stopped.
* At boot, before any start: RUN_SENSE must read 1 for 50 ms after outputs init; otherwise G05 (a shorted Q701 is
  found before the first ACK).
* Limits (stated, not designed around): the sense is the coil low side, not the contact. A welded pair of poles is
  invisible (I-081). An open coil with Q701 on reads 0 ("energised") and is not detected (the contact is open
  anyway). An open coil with Q701 off pulls TRIP_LOW up only through the LED and 1.5k; the pin then sits about
  5 V - LED forward drop at microamps, close to VIH = 0.6 Vcc = 3.0 V: it may read either way. **OPEN**: bench check
  with the coil removed.

### 6.4 RUN contact timing budget

| Step | 24-ch / 8-ch | 40-ch | Source |
|---|---|---|---|
| Threshold crossed just after the channel's sample; next sample of that channel | 700 ms | 745 ms | F10 (cycle screen incl. SPI, CJ, 20/30 ms software allowance) |
| Crossing inside a conversion: one extra filter interval | 44.6 ms | 44.6 ms | F10 |
| Result read -> `channel_eval` -> `outputs_run_stop()` (per result, not at scan end) | < 1 ms (**UNVERIFIED**, inside the software allowance) | same | section 8 |
| Gate decay below Q701 threshold + relay release (incl. flyback diode) | 30 ms | 30 ms | F2, `CALCULATIONS` 9.7 |
| **Total, crossing -> contact open** | **~775 ms** | **~820 ms** | budget 1 s (GOAL, I-013) |

Other paths:

| Failure | Detected by | Contact open within |
|---|---|---|
| main loop hangs, timers still running | watchdog (no feed), reset -> pins high-Z | WDT period (~0.52 s, F11) + 30 ms |
| acquisition stops advancing, loop runs | watchdog (fed only on acquisition progress, 6.5) | ~0.52 s + 30 ms after the last progress |
| acquisition advances but no scan validates | deadline (6.2) | `W_RUN` (900 ms) + 30 ms after the last validated scan |
| over-temperature coinciding with the last case | deadline | up to one scan + `W_RUN` + 30 ms, ~1.6-1.7 s. **OPEN**: this double event exceeds 1 s; owner to accept or ask for a shorter `W_RUN` |
| open thermocouple | rail reading on the next sample (C03) or the burnout slot (C01) | one scan (~0.78 s) if it reads implausibly; otherwise up to ~8 scans (~6 s; 0043 4.2, `CALCULATIONS` 9.7) |

All UNVERIFIED until I-013 is measured on a scope (input stepped past the setpoint, contact timed).

### 6.5 Watchdog and scan-deadline interaction (0043 3.6, I-118, I-119)

* WDTON fuse set: watchdog always on, system-reset mode, **WDTO_500MS** (~0.52 s). It cannot be disabled; the start
  code must not call `wdt_disable()` (replaces F14).
* Fed (`wdt_reset`) only from the main loop, only when `scan` reports that acquisition advanced since the previous
  feed (a new CRC-good ADC/TMP126 result accepted or a slot completed). Slots are ~45 ms, so feeds come ~20 times a
  second while healthy. Never fed from an ISR, from the UI, Modbus or EEPROM code.
* Boot: each straight-line init step may feed once (no loop that feeds); no single init step longer than 250 ms;
  acquisition must be running before 0.5 s has passed without a feed.
* No blocking operation over 10 ms anywhere (EEPROM written one byte per pass, 04 section 6; LCD writes split).
* Three layers, three faults: no progress -> watchdog reset (logged at the next boot as reset cause, G20); progress
  without a validated scan -> `W_RUN` deadline, G07; a bank whose slot does not complete -> bank slot timeout from 02
  (B05). A watchdog reset lands in `START_LATCHED`, so a reset loop keeps RUN open.
* MCUSR is read and cleared at the very start of `main` and kept for the `POWER_UP` event (04).

---

## 7. ALARM output contract (`outputs`)

### 7.1 Polarity (0043 3.5, "to confirm against the schematic")

From F5/F6: the hardware de-energises the alarm relay whenever the MCU is in reset or unpowered. Therefore the
**fail-safe polarity of 0043 3.5 is implementable as specified: coil energised = no alarm; coil de-energised =
alarm**, so a dead, unpowered or resetting board shows alarm.

| Board condition | ALARM_DRIVE (PC6) | Coil | ALARM_SENSE (PC7) | J702 COM-NO | J702 COM-NC |
|---|---|---|---|---|---|
| healthy, no alarm latched | 1 | energised | 0 | closed | open |
| alarm active or latched | 0 | off | 1 | open | closed |
| unpowered / reset / BOOT | high-Z (R712 -> gate low) | off | 1 (if powered) | open | closed |

Installer: wire **COM-NC for an alarm lamp/horn input** (closes on alarm and on a dead board) or COM-NO as a
"healthy" input. To go on the installation drawing (I-085).

**Conflict found (OPEN, hardware)**: the LED on the alarm relay is labelled `ALARM` and is lit while the coil is
energised (F8), i.e. it would be lit when there is **no** alarm. Either relabel the silk (e.g. `ALM OK`) or accept
the confusion. The 8-ch firmware used the opposite polarity (`alarm_output.c:15-19`, high = alarm on); not carried
over.

Power: with this polarity the alarm coil is on almost all the time; `CALCULATIONS` 7.6 already counts both DC5
coils on (40 mA).

### 7.2 Read-back

Same rule as 6.3: expected ALARM_SENSE = 0 when commanded energised, 1 when commanded off; 50 ms settle; mismatch on
every sample for 20 ms -> **G06** (trip + alarm, latched, power cycle only). At boot the sense must read 1 (relay
off) before the first energise.

### 7.3 When the alarm relay is de-energised (= alarm)

`alarm_out_active` = any of:
* state is `BOOT`, `CONFIG_LOCK`, `TRIPPED` or `SERVICE` (except during the 07 alarm step);
* any channel `alarm_latched`;
* any global/bank fault latch with action trip or alarm (section 9), until cleared by ACK;
* any channel currently in `CH_ALARM`, `CH_HIGH` or `CH_FAULT` (ALARM ONLY or TRIP).

`START_LATCHED` with nothing latched and nothing active energises the relay (no alarm) once the first validated
board scan is done. **OPEN (owner)**: should every power-up also hold the alarm until ACK? This draft says no
(avoids a horn on every start; RUN is open anyway and visible on the RUN contact).

An active warning stays on the LCD after an ACK even when the relay latch was not cleared (0043 3.5).

---

## 8. One protection step (pseudo-code)

Two entry points. `on_result` runs for every new result from `scan` (trip early); `on_board_scan` runs once per
completed board scan (validate, clear, refresh RUN).

```
on_result(ch, r):                                  # r = {temp_dC, scan_no, hw_valid, fault_bits}
    if state in {BOOT, SERVICE, CONFIG_LOCK}: return
    if type[ch] == OFF: return
    cond_old = cond[ch]
    cond[ch] = channel_transition(cond[ch], r, provisional=true)   # may only move UP (2.2)
    if cond[ch] raises a trip request (2.3) and trip_latched[ch] == 0:
        if state == RUN: outputs_run_stop()        # FIRST, before any logging or display
        trip_latched[ch] = 1; alarm_latched[ch] = 1; ack_armed = 0
        enter_tripped_or_note(cause = C-code or temperature, ch, r.temp_dC, TSP)   # T7/T8/T10, first-out 4.4
        events_queue(TRIP, ...)
    elif cond[ch] in {CH_ALARM, CH_HIGH, CH_FAULT} and alarm_latched[ch] == 0:
        alarm_latched[ch] = 1
        events_queue(ALARM, ...)
    outputs_alarm_update()

on_board_scan(s):                                  # s = {validated, bank_status[], g_faults, b_faults, t_done}
    if state in {BOOT, SERVICE}: (BOOT: first scan only arms the alarm output) return
    for each new G/B fault in s with action trip (section 9):
        if state == RUN: outputs_run_stop()
        latch fault; ack_armed = 0; enter_tripped_or_note(code, ...); events_queue(FAULT_SET, ...)
    for each new fault with action alarm/advisory: latch or show per section 9
    if s.validated:
        last_vscan = s
        for each fitted ch: cond[ch] = channel_transition(cond[ch], validated result, provisional=false)  # may clear
        check_settings_ram_crc()                   # G03 (04 section 4.4)
        if state == RUN: set_run_deadline(s.t_done + W_RUN)          # 6.2, interrupts off
        refresh_ack_refusal_text()                 # 4.2
    else:
        # no refresh: the deadline runs out on its own -> G07 via the deadline check
    if state == RUN and now >= run_deadline: outputs_run_stop(); raise G07 (trip)
    outputs_readback_check()                       # 6.3 / 7.2, also called every main-loop pass
    outputs_alarm_update()

on_ack_request():                                  # from ui, fresh press only (4.1)
    clear alarm latches whose condition is clear   # 4.3, any state except BOOT/SERVICE
    if state in {START_LATCHED, TRIPPED}:
        reason = check A1..A6 against last_vscan
        if reason == none: accept (T5/T6, 4.2) else show reason
```

---

## 9. Master fault table

Code classes (`00`): `Gnn` global, `Bnn` bank, `Cnn` channel. Numbers never change meaning. Action words:
**trip** = RUN opens and latches (T7/T8) + alarm latch; **alarm** = alarm latch only; **advisory** = LCD only, no
relay, not latched. Channel faults take their action from the channel mode: TRIP channel -> trip, ALARM ONLY
channel -> alarm, OFF -> not evaluated. "ACK after X" means the condition must have cleared on a validated scan
and then an accepted ACK (4.2) clears the latch. Faults detected by acquisition are listed "from 02" by category;
02 defines the test and threshold, this table the code and the action. **OPEN**: 02 is being written in parallel;
its codes must be reconciled with this table (this table is the master).

### 9.1 Global (all boards unless noted)

| Code | Name | Detected by | Action | Latched | Cleared how | LCD text |
|---|---|---|---|---|---|---|
| G01 | settings invalid / blank / layout or board mismatch | `settings` at boot (04 section 4) | trip (CONFIG_LOCK) | yes | valid record saved (T14), then ACK | `G01 SETTINGS INVALID` |
| G02 | settings or calibration save failed | `settings` save read-back (04 section 6) | trip if the save was a protection or calibration save (RUN already open); **alarm** if it was a live save (name, Modbus, PIN). **PROPOSED** split; 0043 5 says only "latches a fault" | yes | successful retry, then ACK | `G02 SAVE FAILED` |
| G03 | settings RAM copy CRC mismatch | `protection` each validated scan (04 section 4.4) | trip | yes | power cycle (reload) | `G03 SETTINGS RAM` |
| G04 | calibration record invalid or missing (REF ratios) | `settings` at boot | trip | yes | valid calibration written in service mode, power cycle, ACK | `G04 CAL INVALID` |
| G05 | RUN read-back mismatch | `outputs` (6.3) | trip | yes | power cycle only | `G05 RUN RELAY FAIL` |
| G06 | ALARM read-back mismatch | `outputs` (7.2) | trip | yes | power cycle only | `G06 ALARM RELAY FAIL` |
| G07 | complete-scan deadline missed | `protection` / 1 ms ISR (6.2) | trip | yes | ACK after a validated scan | `G07 SCAN DEADLINE` |
| G08 | engine reference lost (REFOK high) | from 02 (REFOK, PA2 active-low, every scan) | trip | yes | ACK after REFOK low on a validated scan | `G08 ENGINE REF LOST` |
| G09 | REFTEST self-test failed | from 02 (start-up and every N min, `0032` rev 4) | trip | yes | ACK after a passing self-test (**OPEN**: does 02 re-run the test on demand?) | `G09 REFTEST FAIL` |
| G10 | decoder signature mismatch (aliased address) | from 02 (40-ch decoder) | trip | yes | ACK after re-init and a validated scan | `G10 DECODER ALIAS` |
| G11 | island power loss / re-init | from 02 (either isolator side; 40-ch explicitly, other boards if 02 detects it) | trip | yes | ACK after a fully validated scan | `G11 ISLAND POWER` |
| G12 | RTD bank failure (check resistor, reference, gain) | from 02 (40-ch PT100 bank) | trip (0043 4.5: global) | yes | ACK after a validated RTD bank | `G12 RTD BANK FAIL` |
| G20 | last reset was the watchdog | MCUSR at boot | advisory | no (shown until the first ACK) | ACK | `G20 WDT RESET` |
| G21 | last reset was brown-out | MCUSR at boot | advisory | no | ACK | `G21 BROWN-OUT RESET` |
| G22 | event log write failed (read-back) | `events` | advisory | no | next successful write | `G22 EVENT LOG FAIL` |
| G23 | power-cycle counter unreadable, restarted | `events` at boot | advisory | no | - | `G23 PWR COUNT RESET` |

### 9.2 Bank (bank letter A-E, `R` = 40-ch RTD bank)

Bank faults trip regardless of channel modes (0043 3.3: instrument faults trip regardless of mode), including a bank
whose channels are all OFF. Detected by acquisition after the retry rule of 0043 3.1 (at most two retries in the
same scan, then the bank is FAULT).

| Code | Name | Detected by (from 02) | Action | Latched | Cleared how | LCD text |
|---|---|---|---|---|---|---|
| B01 | ADC communication (CRC failed after retries) | ADC comms | trip | yes | ACK after the bank's next validated scan | `B01 A ADC COMMS` |
| B02 | ADC ID / revision wrong | ADC ID | trip | yes | same | `B02 A ADC ID` |
| B03 | ADC configuration read-back mismatch | ADC config | trip | yes | same | `B03 A ADC CONFIG` |
| B04 | ADC error register flag | ADC status | trip | yes | same | `B04 A ADC ERROR` |
| B05 | ADC not converting (conversion counter stuck, RDY or slot timeout) | ADC progress | trip | yes | same | `B05 A ADC STALLED` |
| B06 | REF3030 cross-check outside window | REF check | trip | yes | same | `B06 A REF CHECK` |
| B07 | AVDD/6 outside window | AVDD | trip | yes | same | `B07 A AVDD` |
| B08 | zero check (shorted input) outside window | zero slot | trip | yes | same | `B08 A ZERO CHECK` |
| B09 | gain-ratio check failed | gain slot | trip | yes | same | `B09 A GAIN CHECK` |
| B10 | both cold-junction sensors invalid | CJ | trip | yes | same | `B10 A CJ BOTH BAD` |
| B11 | both CJ valid but disagree beyond the window | CJ | trip | yes | same | `B11 A CJ DISAGREE` |
| B12 | one CJ invalid (degraded) | CJ | **trip** until the fallback error is measured on the bench, then **alarm** (0043 3.4; build-time constant) | yes | ACK after both CJ valid | `B12 A DEGRADED CJ` |
| B13 | result sequence tag not fresh (stale or aliased result) | scan validation | trip | yes | same as B01 | `B13 A STALE RESULT` |

### 9.3 Channel (two-digit channel number in the text)

| Code | Name | Detected by (from 02) | Action | Latched | Cleared how | LCD text |
|---|---|---|---|---|---|---|
| C01 | open thermocouple (burnout upper window) | burnout slot | by mode | yes | next passing burnout check of this channel, then ACK | `C01 03 OPEN TC` |
| C02 | burnout lower window / baseline deviation | burnout slot | by mode | yes | same | `C02 03 BURNOUT LOW` |
| C03 | over range (EMF/resistance above the type's table or ADC near full scale) | TC/RTD math | by mode | yes | valid in-range result on a validated scan, ACK | `C03 03 OVER RANGE` |
| C04 | under range | TC/RTD math | by mode | yes | same | `C04 03 UNDER RANGE` |
| C05 | input common mode outside window | rotating CM check | by mode | yes | next passing CM check of this channel, ACK | `C05 03 COMMON MODE` |
| C06 | burnout baseline not learned (fitted TC channel) | `settings` (calibration record, 04) | by mode | yes | baseline learned and saved, ACK | `C06 03 NO BASELINE` |
| C07 | RTD lead open or short | RTD checks (40-ch) | by mode | yes | valid result, ACK | `C07 41 RTD LEAD` |
| C08 | RTD sheath fault (currents-off reading) | RTD checks (40-ch) | by mode | yes | passing currents-off check, ACK | `C08 41 RTD SHEATH` |
| C09 | stale: no fresh result for this channel | `channel_eval` (2.2) | by mode | yes | fresh validated result, ACK | `C09 03 STALE` |
| C10 | rate of change implausible | advisory check (I-098) | advisory | no | condition clears | `C10 03 RATE?` |
| C11 | value stuck | advisory check (I-098) | advisory | no | condition clears | `C11 03 STUCK?` |

Over-temperature and alarm are conditions, not faults: `TRIP 03 CYL3B` / `ALARM 03` (05 owns the screen text).

---

## 10. OPEN in this file

1. `W_RUN` provisional 900 ms; set from the measured scan period (6.2).
2. Over-temperature coinciding with "scan never validates" can take ~1.6-1.7 s (6.4); owner to accept or ask.
3. Alarm relay LED labelled `ALARM` is lit in the healthy state with the fail-safe polarity (7.1); hardware chat.
4. Should every power-up hold the alarm relay until ACK (7.3)? Draft: no.
5. G02 action split (trip for protection saves, alarm for live saves) is a proposal beyond 0043 5.
6. G09 clearing: when is REFTEST re-run (02).
7. Codes from 02 to reconcile with section 9.
8. Open-coil read-back with Q701 off is marginal (6.3); bench check.
9. Service mode exit by power cycle only (T15); 07 to confirm.
10. ACK release time 100 ms and chord handling (4.1); 05 to confirm.
11. Whether a bank with every channel OFF still trips on its bank faults (draft: yes, per 0043 3.3 wording).
