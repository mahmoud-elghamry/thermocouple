Implemented standalone F3 within the allowed files; no commits or integration edits.

Files: [modbus.h](/D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/include/app/modbus.h), `src/app/modbus.c`, `src/app/modbus_map.c`, `test/build_modbus.ps1`, and `test/modbus/`. Full handoff: [README](/D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/test/modbus/README.md).

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File firmware/family/test/build_modbus.ps1
```

Results:

- **1,527,729 host checks passed**, with MSVC warnings-as-errors and ASan.
- Both modules pass AVR `-Os -Wall -Wextra -Werror`.
- **553 B static RAM**, including the 256 B shared buffer; driver storage and stack additional.
- **49,734 simulated steps**: worst 0.697 ms; **0.947 ms** including the reserved driver/ISR allowance. Integrated drivers must verify that allowance.
- Documentation check: zero findings.

The six required interfaces are declared in `modbus.h`: `mb_io_configure`, `mb_io_now_us`, `mb_io_rx`, `mb_io_tx_start`, `mb_io_tx_busy`, and `mb_io_status`. They require 8N2 configuration, extended Timer1 timestamps, preserved UART/overflow errors, binary UDRE TX with DE held through final TXC, and read-only metadata/feedback/trip-latch inputs.

Integration after application/scan initialization:

```c
mb_init();  /* once */
```

Every loop, after protection/output and before EEPROM:

```c
if (boot == LOOP && flash_valid && mode != SERVICE)
    mb_task(1000);
```

Replace unconditional `rs485_task()` with a SERVICE-only call. Add both modules and adapters to target sources.

Spec gaps recorded in the handoff:

- `07 §3/4.2`: invalid quantities and absent channels—implemented exceptions 03 and 02 respectively.
- `07 §4.1`: alarm counting, age saturation, and missing feedback/metadata/persistent trip-latch getters.
- `01 §4 / 07 §2`: multi-call snapshot assembly—partial replies are discarded when source evidence changes.
- `02 §4.4 / 07 §1–2`: timestamp resolution and RX-ring metadata storage differ.