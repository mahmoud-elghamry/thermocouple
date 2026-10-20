# 01 - Architecture and system design

How the firmware is built: execution model, layers, data ownership, the patterns used and why, and the rules
every module follows. The other spec files describe *behaviour*; this one describes the *structure* that
behaviour lives in. Decided behaviour: `docs/decisions/0043-family-firmware-plan.md` rev 2.

## 1. Design drivers

In order of weight (from the owner's priorities and the energised-to-run rule):

1. **Fail safe.** Any fault, hang, corruption or unknown value must end with the RUN contact open. The contact is
   held closed only by continuous, positive evidence that the system is healthy.
2. **Deterministic timing.** Threshold crossing to contact open <= 1 s on every board, under any UI or Modbus load.
3. **Testable on the PC.** Everything that decides something runs and is tested on the host without hardware.
4. **One firmware, three boards.** Board differences are data, not code paths scattered in `#ifdef`s.
5. **Simple.** 8-bit MCU, one developer at a time, AI implementers: no RTOS, no dynamic memory, no clever tricks.

## 2. Execution model: time-triggered cooperative loop

**Pattern: cooperative super-loop with non-blocking state-machine tasks.** No RTOS.

```
reset -> boot (2.1) -> loop forever:
    t0 = ms_tick
    acq_task()        // advances each bank's state machine; never waits on hardware
    if scan_complete: prot_task()     // pure decision step, once per board scan
    out_task()        // RUN window, ALARM, read-back sampling
    ui_task(budget 1 ms)
    modbus_task(budget 1 ms)
    store_task()      // at most one EEPROM page step per call
    flow_check_and_wdt()              // 2.3
```

* Every task is a state machine that does a bounded amount of work and returns. No `while (!ready)` loops on
  hardware; waits are states with a timeout measured in `ms_tick`.
* Target loop period <= 5 ms, **worst case <= 8 ms** - enforced by the per-task budgets (ui 1 ms, modbus 1 ms,
  store one EEPROM step) and measured in service step P16 (budget table in `10-phases.md`). The AD7124 conversion
  (~42 ms per slot at 25 SPS) is much longer than a loop, so polling its ready flag each loop costs nothing.
* **ISRs are minimal**: 1 ms timer (increments `ms_tick`, samples keys, counts down the RUN deadline and stops
  the pump at zero - it can only stop it, never start it), UART RX byte + 50 us timestamp (Timer1) into a ring,
  UART TX from a buffer, nothing else. No decision is ever made in an ISR. The charge-pump PWM is a hardware
  timer output with no ISR.
* Rejected: an RTOS (stacks per task in 16 KB RAM, priority bugs, nothing gained at this size); fully
  interrupt-driven acquisition (hard to test, races with the SPI sharing between banks).

### 2.1 Boot sequence (summary; exact order in `02-hardware-interface.md`)

Watchdog already running (WDTON) -> outputs to safe state (RUN PWM off, ALARM in alarm) -> clock/timers ->
flash CRC check -> load settings (A/B) -> island power-up and device init -> first validated scan -> state
`START_LATCHED` (or `CONFIG_LOCK`). Nothing in boot may take longer than the watchdog period without feeding it
through the flow check.

### 2.2 Concurrency rules

* Data shared with an ISR: only `ms_tick` (read with interrupts briefly disabled or a double-read), the key
  sample register, and single-producer/single-consumer ring buffers (UART). Nothing else.
* SPI is used by one task only (`acq_task`), so it needs no lock. The LCD port is used by `ui_task` only.

### 2.3 Program-flow monitoring and the watchdog

**Pattern: checkpoint signature.** Each task sets its bit in `flow_seen` when it completes a step. The watchdog
is fed only when (a) all expected bits for this loop are set and (b) `acq_task` has made progress within its
deadline (a conversion read, a state advance). Then `flow_seen` is cleared. A stuck task, a skipped task or an
acquisition that stopped advancing therefore stops the feeding and the watchdog resets the MCU (<= 0.5 s), which
boots into `START_LATCHED` with RUN open. Independently, the RUN window (2.4) expires if no validated scan arrives,
so even a loop that keeps feeding the watchdog but never completes a scan opens RUN.

### 2.4 RUN as a "dead-man" output

**Pattern: positive keep-alive.** The RUN contact is held by a charge pump driven by a 2 kHz hardware PWM (>= 1 kHz required; 2 kHz gives 4.1-4.2 V gate, CALCULATIONS 8.5)
(PB3). Protection does not "set RUN on"; it *refreshes a permission window* after each validated board scan in
which RUN is allowed. `out_task` stops the PWM when the window expires or permission is withdrawn. A static
output level can never hold the relay (hardware: AC-coupled charge pump, `0032` rev 4). Three independent
things must all be right for RUN to stay closed: the protection decision, a fresh validated scan, and a live
loop - and each one alone can open it.

## 3. Layers

```
APP        protection   channel_eval   ui   modbus   service        (decisions, presentation)
SERVICES   scan   tc_math   settings   events   fault registry      (data, no hardware)
DRIVERS    ad7124   tmp126   rtd   iso_spi   lcd   keys   relays   rs485   (devices)
MCAL       gpio   spi   uart   timer   wdt   eeprom   flash_crc          (registers)
BOARD      board_cfg (const tables per board)                         (data)
```

* **Dependencies point down only.** APP never touches a register; drivers never decide protection; services never
  call drivers except `scan` (which owns acquisition).
* **Pattern: functional core, imperative shell.** `protection`, `channel_eval`, `tc_math`, the settings
  validator and the Modbus map are **pure functions** over plain structs: same input, same output, no I/O, no
  globals. The shell (`acq_task`, `out_task`, `store_task`) does the I/O. This is what makes the safety logic
  testable with tables on the PC.
* **Pattern: link-time seams for mocks.** Each driver/MCAL module has one header; the target build links the real
  `.c`, the host build links a fake (`test/fakes/*.c`). No function-pointer vtables (zero cost, simpler for AVR).
* **Fake devices.** The host build has a register-level fake AD7124 and TMP126 (they answer reads/writes like the
  real parts, with injectable faults: wrong ID, bad CRC, stuck ready, aliasing), so the real drivers and the scan
  scheduler are tested unchanged.

## 4. Data ownership (single writer)

| Data | Owner (only writer) | Readers | Form |
|---|---|---|---|
| `board_cfg` | build | all | `const` in flash |
| active settings | `settings` | all | `const settings_t *` - changed only by a committed transaction (4.1) |
| `meas[ch]` results of the last scan | `scan` | channel_eval, ui, modbus, service | struct per channel `{temp_dC, emf_nV, scan_no, flags}` |
| fault registry | `fault` service; raised/cleared by detectors | protection, ui, modbus, events | one entry per (code, unit) - unit = bank, channel or input pin - so bank A and bank B can hold the same code independently; aggregated per code only for display/Modbus |
| protection state | `protection` | out_task, ui, modbus, events | struct; RUN permission stored twice (value + complement) |
| events ring | `events` | ui, modbus | EEPROM + RAM head copy |
| key events | `keys` driver | ui only | small queue |

* UI and Modbus read **snapshots** (copied once per loop by the reader) and never write protection data.
* A request from the UI (save settings, ACK) is a **command** placed in a one-slot mailbox and executed by its
  owner on its next step (**pattern: command mailbox**), so the owner validates it with fresh data.

### 4.1 Settings transactions

**Pattern: copy-edit-validate-commit.** The UI edits a working copy. Commit = validate (pure function, the whole
record, not the field) -> protection inhibits RUN if the change touches protection settings -> `store_task`
writes the inactive A/B copy, reads it back, flips the active pointer -> protection requires ACK. Until the flip,
the old settings remain in force. Details in `05-settings-events.md`.

## 5. State machines

All behaviour with memory is an explicit state machine: `enum` state, a transition function
`next = f(state, inputs)`, and a table in the spec. **Unknown or out-of-range state values are treated as the
most restrictive state** (global: `TRIPPED`; channel: `FAULT`). Machines:

* Global protection: `CONFIG_LOCK`, `START_LATCHED`, `RUN`, `TRIPPED`, `SERVICE` (`04-protection.md`;
  a protection-settings commit returns to `START_LATCHED`, so no separate inhibit state).
* Per channel: `OFF`, `OK`, `ALARM`, `TRIP`, `FAULT` (`04-protection.md`).
* Per bank acquisition: init, configure, verify, slot loop, recover (`03-acquisition.md`).
* UI: screen stack and edit session (`06-ui.md`).
* Store: idle, write page, verify, flip (`05-settings-events.md`).
* Modbus: idle, receiving, process, respond (`07-modbus.md`).

## 6. Defensive techniques (kept to the useful ones)

| Technique | Where | Why |
|---|---|---|
| Watchdog <= 0.5 s, WDTON fuse, fed only by flow check | 2.3 | hang -> reset -> RUN open |
| RUN keep-alive window + charge pump | 2.4 | stuck output cannot hold RUN |
| Read-back of RUN and ALARM drive | `04` | a dead driver/relay is detected |
| RUN permission stored as value + complement | protection | a RAM bit-flip cannot grant RUN |
| Flash CRC at boot | boot | a bad programming/corrupted image never runs |
| Stack canary checked every loop | boot + loop | stack overflow -> trip before corruption spreads |
| CRC on every SPI read, register read-back, device ID | drivers | wiring/isolator faults never look like temperatures |
| A/B settings + semantic validation | settings | power cut or corruption never yields wrong limits |
| Default branch of every `switch` -> most restrictive | all | unknown values fail safe |

Rejected as over-engineering for this board: full RAM march test at runtime, dual-MCU redundancy, redundant
computation of every temperature, encrypted settings.

## 7. Board variants

`board_cfg` is the only place that knows the board: number of banks, chip-select method (direct pins or the
74HC154 address), pin map, channel -> (bank, AIN pair, CJ pin-position weight) table, which keys exist, PT100
presence. It is `const` data selected by `BOARD`. Code outside `board_cfg` loops over the tables; it never asks
"which board am I". The only `#if BOARD` allowed outside `board_cfg` is in the build lists.

## 8. Coding rules

* C11, avr-gcc with `-Wall -Wextra -Werror -Os`; host build with the same warnings plus sanitizers.
* MISRA-C-inspired subset: no `malloc`, no recursion, no variable-length arrays, every loop bounded, fixed-width
  integer types, no floating point in the protection and measurement paths, explicit casts, one `return` path
  not required.
* Every public function documented in its header with units and ranges. Errors returned as `enum` codes; drivers
  report faults to the registry, they do not decide what to do.
* `cppcheck` clean. Each module <= ~400 lines (AGENTS rule 10).
* Versioning: firmware version (semver) + settings schema version + build hash, shown in service mode and Modbus.

## 9. Source layout

```
firmware/
  spec/                 this specification
  src/board/            board_cfg_8.c board_cfg_24.c board_cfg_40.c
  src/mcal/             gpio spi uart timer wdt eeprom flash_crc
  src/drivers/          iso_spi ad7124 tmp126 rtd lcd keys relays rs485
  src/services/         scan tc_math tc_tables settings events fault
  src/app/              protection channel_eval ui ui_screens modbus service main
  test/unit/            one test file per module (table-driven)
  test/fakes/           fake MCAL, fake AD7124/TMP126/LCD/EEPROM
  test/scenarios/       end-to-end host scenarios (trip timing, power cut during save, stalled acquisition)
  sources/*.txt         build lists per target (existing scheme, `check_lists.py`)
```

The existing 8-ch REV A2 code stays in place until the family firmware reaches F1; it is not modified.
