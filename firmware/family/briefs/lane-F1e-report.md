Implemented F1e. All three commands exited **0**.

[timing.h](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/include/app/timing.h) now supplies the shared limits:

- **1200 ms:** `protection.c` window/freshness, `outputs.c`, `relays.c`, `timer.c` range checks, `app.c` window watch, and `scan.c` deadline.
- **20 ms:** `main.c` loop guard and `service.c` report; the profiler derives **160000 cycles**.
- **36–69 ms:** `ad7124.c`, through `acquisition_budget.h`.
- **1000 ms:** the separate service relay exercise.

Updated unit/scenario/integration expectations and clock models. Finished the profiler’s combined-load checks and automatic `build.ps1` gate. Retained the CPU reductions and removed the unfinished LTO experiment. This lane did not edit acceptance files.

After deleting the three output directories:

- `build.ps1`: hardware **234**, scan **103**, peripherals **71**, service **287**, Astra review **5731**, integration **2750709**, Timer ISR **16**, Store preparation **284** checks PASS.
- `build_core.ps1`: **125440 checks, 0 failures**.
- Final acceptance run: **TOTAL checks=14182 passed=14182 failed=0**; strict AVR compilation PASS.

Profiler: **1782 measured passes**, worst **102017 cycles / 12.752 ms**, including MCAL bounds and **25% + 2048** reserve. Combined commit/CJ/slot/ACK pass: **91317 cycles**, all four conditions verified.

AVR flash: **56416 bytes**, including CRC storage. Static RAM: **10316 bytes**; with the **1536-byte** stack allowance: **11852/12288 bytes**.