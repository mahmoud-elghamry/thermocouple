# Family firmware specification - 00 overview and shared conventions

Source of truth for *what* is decided: `docs/decisions/0043-family-firmware-plan.md` (rev 2, owner-approved
section 8 table on 2026-10-20). These spec files say *exactly how*, so an implementer can write the code and the
tests without inventing behaviour. If a spec file and 0043 disagree, 0043 wins and the spec file is a bug.

All files are written by one author (Claude) so names, codes and patterns agree; `drafts/` holds research input
(register values, timings, mock-ups with datasheet citations) and is not normative.

| File | Content |
|---|---|
| `00-overview.md` | this file: scope, conventions, identifiers shared by all files |
| `01-architecture.md` | execution model, layers, data ownership, patterns, defensive techniques, coding rules, layout |
| `02-hardware-interface.md` | per-board pin maps, CS strategies, SPI/UART/timers, fuses, start-up order, programming |
| `03-acquisition.md` | AD7124 setup, slot schedule, diagnostics, TMP126, CJ, TC math, 40-ch decoder and PT100, scan validation |
| `04-protection.md` | channel and global state machines, truth tables, latch/ACK, RUN and ALARM outputs, master fault table |
| `05-settings-events.md` | EEPROM map byte by byte, A/B records, validation, save/recovery, calibration, events |
| `06-ui.md` | 20x4 screens (exact text), keys and chords, menu tree, edit/confirm flows, PIN, commissioning |
| `07-modbus.md` | read-only register map, framing, timing, reserved write area |
| `08-service-mode.md` | service mode entry, passive and active steps, report line format |
| `09-tests.md` | host unit tests, fakes, fault injection, scenarios, bench matrix, requirement traceability |
| `10-phases.md` | module APIs, task breakdown per phase F0-F3, gates, timing and memory budgets |

## Targets

* MCU ATmega1284P, 8 MHz crystal, 128 KB flash, 16 KB RAM, 4 KB EEPROM. avr-gcc, C11, no dynamic memory, no
  floating point in the protection path (integer fixed point).
* Planned: one source tree, `BOARD=8|24|40` at build time selects `board_cfg`, one binary per board type.
  **Not built yet:** the build always uses `board_cfg_24.c`; an 8-ch port also needs settings, UI bounds and
  image identity parameterised (Sol audit 2026-10-24); `FAMILY_CHANNELS` / `FAMILY_FAST_IO_HEADER` are only fast-I/O hooks.
* **Implemented scope: the 24-ch board only (owner 2026-10-23: the 40-ch board is probably never built).** The
  firmware carries no 40-ch, PT100 (`rtd`) or 74HC154 decoder code; arrays are sized `MAX_CHANNELS` 24,
  `MAX_BANKS` 3. The 40-ch sections of these files (`02` 1.3 and 2.3, `03` 8, PT100 rows of `05`) stay as the
  design record and are not normative for the code. The 8-ch board stays a `board_cfg` extension point. The
  EEPROM map of `05` keeps its addresses, so a later board does not change the record layout. J stays supported.
* Host tests (gcc on the PC) for every module that has logic; hardware access only through MCAL/HAL so it can be
  mocked.

## Shared conventions (every file uses these)

* **Channels** numbered 1..N on the LCD and in Modbus (N = 8, 24, 40; PT100 inputs on the 40-ch are channels
  41..43). In code `ch` is 0-based. Bank letters A..E; bank `b` holds channels `8b+1 .. 8b+8`.
* **Temperature** `int16_t` in 0.1 C (`temp_dC`), range -2000..+14000. **EMF** `int32_t` in nV (`emf_nV`).
  Raw ADC codes `uint32_t` 24-bit.
* **Time**: `scan_no` (`uint32_t`, increments once per completed board scan), `ms_tick` (`uint32_t`, 1 ms timer
  for timeouts only). Events stamp `uptime_s` + `power_cycles`.
* **Validity**: every channel result carries `{value, scan_no, flags}`; a result is *fresh* when
  `scan_no == current scan`.
* **Fault codes**: `Gnn` global (trip everything), `Bnn` bank (applies to the 8 channels of one bank), `Cnn`
  channel. Each spec file that detects a fault defines its code in its own table; `04-protection.md` holds the
  complete list and the action for each. Codes are shown on the LCD and in Modbus, so they never change meaning.
* **Modules** (names fixed): `board_cfg`, `iso_spi`, `ad7124`, `tmp126`, `rtd`, `scan`, `tc_math`,
  `channel_eval`, `protection`, `outputs`, `settings`, `events`, `ui`, `modbus`, `service`, plus MCAL `gpio`,
  `spi`, `uart`, `timer`, `wdt`, `eeprom`.
* **Words**: *trip* = RUN contact opened by protection; *alarm* = ALARM relay + LCD warning; *latched* = needs ACK;
  *config lock* = settings blank/invalid, RUN never granted; *validated scan* = defined in `03` and used by `04`.

## Owner rules that apply everywhere

Energised-to-run: anything unknown opens RUN. Never invent a setpoint. Modbus never grants RUN, ACKs or clears a
trip. No over-engineering: a feature that is not needed for the goal is left out (AGENTS rule 7).
