# Brief - Lane A: hardware path, phase F0, 24-ch board

You are the implementer (Codex Sol). Another implementer works in parallel on Lane B (pure core). Claude
reviews your diff, runs the gates and commits. Do not run git commands that write (no add/commit/checkout).

## Read first

`firmware/spec/00-overview.md`, `01-architecture.md`, `02-hardware-interface.md`, `03-acquisition.md`,
`04-protection.md` (sections 4, 6 for what outputs must do), `06-ui.md` sections 1-2, `08-service-mode.md`,
`09-tests.md`, `10-phases.md`. Hardware source of truth: `hardware/24ch/gen/c_mcu.py`, `c_iso.py`, `c_bank.py`,
`c_out.py`. Existing 8-ch firmware for style and the build scheme: `firmware/build.ps1`, `firmware/Makefile`,
`firmware/sources/`, `firmware/src/`, `firmware/tests/`. Datasheet texts:
`C:\Users\malgh\AppData\Local\Temp\claude\D--tasks-thermo\7f207358-9e1f-4e51-94b7-67c3674c8411\scratchpad\ds\`.

## Write ONLY under `firmware/family/` and only these parts

* `include/board/`, `src/board/board_cfg_24.c` (24-ch only; keep the structure ready for 8/40 later)
* `include/mcal/`, `src/mcal/` (gpio, spi, uart, timer, wdt, eeprom, flash_crc) + host fakes in `test/fakes/`
* `include/drivers/`, `src/drivers/` (iso_spi, ad7124, tmp126, lcd, keys, relays, rs485)
* `include/services/scan.h`, `src/services/scan.c`
* `include/app/service.h`, `src/app/service.c` (service mode passive steps P01-P16 and active A01-A07 of `08`)
* `src/app/main.c` for F0: boot order of `02` 8, the cooperative loop of `01` 2, flow check + watchdog of `01` 2.3,
  service mode entry; protection is a stub that keeps RUN open (state `START_LATCHED`) until Lane B lands.
* `test/fakes/fake_ad7124.c`, `fake_tmp126.c` (register-level, fault injection per `01` 3), `test/unit/` for every
  module you write, `build.ps1` and `sources/*.txt` for `firmware/family` (target ATmega1284P with the avr-gcc
  path used by `firmware/build.ps1`; host build with the same compiler setup as the existing host tests).
* Use the shared headers `include/common/types.h`, `meas.h`, `fault_codes.h` as they are (owned by Claude; if
  you need a change, say so in the report instead of editing them).
* Do NOT write `tc_math`, `channel_eval`, `protection`, `settings`, `events`, `fault` (Lane B owns them). Where you
  need them, call the interface in `10-phases.md` 1 and provide a minimal host stub under `test/stubs/` only.

## Rules

* Tests first from the spec, then code. Every check and limit in `03` sections 4, 5, 10 has a unit test against the
  fake ADC/TMP126, including fault injection (wrong ID, CRC error once/repeated, ERROR bits, POR flag, stalled RDY,
  torn MCLK read, signature mismatch).
* No dynamic memory, no floats in measurement paths, bounded loops, `-Wall -Wextra -Werror` (`01` 8). Modules
  <= ~400 lines.
* Anything the spec leaves OPEN: use the provisional value written in the spec, mark it `/* OPEN-xx */`, and list
  it in your report. Never invent setpoints.
* Run the host tests and the AVR build yourself; both must pass.

## Report (your final message)

Files written; test results (counts, pass/fail, the exact command); AVR build size (flash/RAM); every OPEN item you
used; anything in the spec you found wrong or ambiguous (file + section). Under 600 words.
