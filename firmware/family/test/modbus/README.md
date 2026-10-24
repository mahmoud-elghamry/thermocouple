Lane F3 standalone handoff (2026-10-23)

Files: `include/app/modbus.h`, `src/app/modbus.c`, `src/app/modbus_map.c`,
`test/build_modbus.ps1`, and `test/modbus/{test_modbus.c,avr_profile.c,profile.py,.gitignore,README.md}`.
No integration files, source lists, drivers, acceptance tests, or STATE files changed.

Run from repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File firmware/family/test/build_modbus.ps1
```

Host: **1,527,729 checks**, MSVC `/W4 /WX` + ASan. Includes both functions, every
mapped register on 24-channel snapshots (00 Targets / 0043 section 9), every function rejection, exceptions,
CRC, malformed/address/broadcast/overflow cases, gap boundaries, timestamp wrap,
133-byte maximum, TX-buffer ownership, source-change cancellation, age saturation,
and 687.5 seconds of logical 19200-baud 8N2 garbage plus recovery.

AVR: both modules compile with `-Os -Wall -Wextra -Werror`, ATmega1284P.
Static RAM **553 B**, including shared RX/TX **256 B**; driver ring and stack extra.
Compiler reports `mb_task` frame **73 B** (nested calls additional).
Simulator: **49,734 steps**, worst **5,576 cycles / 0.697 ms**;
adding **2,000 cycles** for real adapter/ISR overhead gives **0.947 ms**.
That overhead contract still needs verification with the integrated drivers.
Reports: `output/test-results.txt`, `avr-size.txt`, `timing.txt`, `cycles.log`, `*.su`.
`python docs/check_docs.py`: exit 0, zero findings.

Implement all six `mb_io_*` seams in `modbus.h`: 8N2 baud configuration/flushing,
extended atomic Timer1 clock, timestamped/error-preserving 64-entry RX queue,
binary borrowed-buffer UDRE transmission with DE held through TXC, busy indication,
and read-only status (build versions, actual feedback, full uptime, cycles, persistent
trip bitmap). No current driver supplies these contracts. Preserve overflow evidence,
reject TX if new RX is pending, suppress echo, and meet the 2,000-cycle allowance.

Integration in `main.c` after application/scan initialization:

```c
#include "app/modbus.h"
mb_init();
/* Every normal-mode loop, after protection/output, before EEPROM owner: */
if (boot == LOOP && flash_valid && mode != SERVICE) mb_task(1000);
/* Replace the unconditional rs485_task() with: */
if (mode == SERVICE) rs485_task();
```

Add both modules and the adapters to target sources during integration.

Spec gaps: `07` sections 3/4.2 omit quantity exceptions and absent-channel behavior:
implemented exception 03 for 0/>64, exception 02 beyond fitted-board channel count.
`07` 4.1 does not define active-alarm counting or scan-age overflow: active channel
conditions plus G/B instances (excluding informational resets), saturating scan age.
`01` 4 / `07` 2 do not define multi-call snapshot assembly: generation/evidence
changes discard partial replies. `02` 4.4 versus `07` 1 disagree about timestamp
resolution; adapter supplies extended 50us timestamps. `07` 2's 64-byte ring omits
timestamp storage. `07` 4.1 requires metadata/feedback/persistent channel-trip
evidence absent from current getters; adapter must supply it without inferring
trip latches from `trip_seen`, which clears on recovery.
