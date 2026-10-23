Implemented F5; changes remain uncommitted. Protected files are unchanged.

Changed protection/app/UI code and headers, `app_view.c`, `scan.c`, new stack-monitor files, service reporting, `gpio.c`, source lists, and regression/profiler harnesses.

- G01 clears independently of missing calibration; setup uses settings validity and preserves the saved PIN/configuration.
- ACK refusal retains its channel; C10/C11 update newest-cause ordering.
- Scanning batches bounded work and starts the next conversion before temperature calculations.
- Stack painting preserves `.noinit`, reports beside P16, and has an ISR-overlay gate.
- Atomic GPIO operations and faster one-microsecond delays bring the combined workload under budget.

After deleting generated directories, all three commands exited **0**:

| Command | Results copied from output |
|---|---|
| `build.ps1` | Hardware **234**, scan **103**, peripherals **71**, service **288**, review **12174**, integration **2762469**, F4 integration **1378251**, timer **22**, preparation **426**, UART **84** checks PASS; UI **702**, gestures **586**, zero failures; Modbus **1527729** checks PASS |
| `test/build_core.ps1` | **125509 checks, 0 failures** |
| `test/build_acceptance.ps1` | **14270 passed, 0 failed** |

AVR simulator: **18210 measured passes**, worst **157917 cycles / 19.740 ms**, including **25% + 2048 cycles reserve**. Combined-load and hot/C01 evidence flags are **63**, with zero functional errors.

Validated scan maxima at **5/10/20 ms cadence**:

- Host: **785/840/1120 ms**, 10/10 validated each.
- Measured-clock AVR: **854/891/1120 ms**, 3/3 validated each.
- Host with **4 ms CPU charged per channel**: **1120 ms** at 20 ms cadence.

Stack high-water: **533 B**; measured ISR overlay **29 B**; conservative gate **562/1536 B**.

AVR flash: **73432 B including CRC**. Static RAM: **12247 B**; with stack allowance: **13783/14336 B**.

Profiler runs separately via `profile_avr.ps1`, invoked by the build; runtime **684.9 s**. Documentation and whitespace checks pass.