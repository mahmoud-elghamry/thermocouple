# Brief - Lane F3: Modbus RTU read-only module (24-ch), standalone

You are an implementer (Codex Sol). Other Sol lanes work in parallel on other files (protection fix; UI). Claude
reviews, integrates into the main loop and commits. Do not run git commands that write.

## Read first

`firmware/spec/00`, `01` (loop, budgets, data ownership), `07-modbus.md` (all - this is your spec), `04` 9 (fault
codes), `05` 7 (events), `10` 1-2. Public headers: `include/app/app.h` (read-only getters), `include/services/
scan.h`, `fault.h`, `events.h`, `settings.h`, `include/mcal/uart.h`, `include/drivers/rs485.h`,
`include/common/*`.

## Write ONLY

`include/app/modbus.h`, `src/app/modbus*.c` (frame builder pure: snapshot + request -> response bytes),
`test/modbus/` (host tests, fakes for uart/rs485/app getters), `test/build_modbus.ps1` (copy the compiler setup of
`test/build_core.ps1`). **Do not edit** `main.c`, `app.c`, `build.ps1`, `sources/*.txt`, `uart.c`, `rs485.c` or any
other existing file, nor `test/acceptance/`. If the UART/RS-485 driver lacks something you need (binary TX, frame
timing), write the module against a small interface you define in `modbus.h` and list exactly what the driver must
provide in the report.

## Build

`mb_init()`, `mb_task(budget)`: fn 03/04 read-only maps of `07`, 1.5/3.5-character rules with the Timer1/RX
timestamps of `07`, CRC16, exception codes, address/baud from settings, no reply to broadcast. Never writes
settings or touches protection. Budget <= 1 ms per call on the AVR; RAM: the 256 B TX buffer of `07` plus small
state.

## Tests (first)

Every register of the maps (values from a fake snapshot), every exception, CRC good/bad, wrong address, broadcast,
inter-character gap at the 1.5/3.5 boundaries for 9600 and 19200, garbage flood (no crash, bounded time), max
response length. Also compile `src/app/modbus*.c` for the AVR with `-Wall -Wextra -Werror`.

## Report (under 400 words)

Files, test command + counts, AVR compile result and RAM, the driver interface needed, the exact integration
calls for `main.c`, spec gaps (file + section).
