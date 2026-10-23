F4 is integrated, but **Done is not met**: `build.ps1` exits **1** because the image exceeds the unchanged 64 KB flash cap. All functional and timing gates pass.

Changed loop/mailbox/key routing, UI hooks, UART/Timer1 and Modbus adapters, event-history and trip-latch views, epoch handling, source lists, build gates, fakes and tests. Full [47-file inventory](/D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/build/changed-files.txt). Service and TMP126 formatting changes preserve behavior.

After deleting every build/output directory:

- Full build: hardware **234**, scan **103**, peripherals **71**, service **287**, review **5726**, integration **2771982**, F4 integration **1374330**, timer **22**, store preparation **426**, UART **84** checks PASS.
- UI: **696 checks, 0 failures**; gestures: **586 checks, 0 failures**.
- Modbus: **1527729 checks PASS**.
- Core: exit **0**, **125506 checks, 0 failures**.
- Acceptance: exit **0**, **TOTAL checks=14270 passed=14270 failed=0**.

AVR flash is **72910 bytes including CRC**. RAM is **12237 bytes static**, **13773/14336** including reserved stack.

Profiler: **2609 passes**, worst **114062 cycles / 14.258 ms**, including reserve. Combined UI/Modbus flood/commit/CJ/slot/ACK: **106206 cycles**. UI and Modbus remain below 1 ms. After ten simulated minutes of garbage traffic, trip timing was **48/48 ms** baseline/flood; normal crossing worst was **713 ms**.

Remaining gaps:

- `10` §2: flash exceeds **65536 bytes**; the cap needs an owner decision.
- `07` §2: RX ISR measures **218 cycles / 27.25 µs**, exceeding the approximate 5 µs / <1% estimate. Actual driver costs replace F3’s flat 2000-cycle estimate in the integrated timing gate.

Acceptance/common files untouched. Documentation check: **0 findings**. No git writes.