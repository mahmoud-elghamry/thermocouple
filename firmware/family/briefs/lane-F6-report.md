F6 complete in the working tree; no git writes. [Full report](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/briefs/lane-F6-report.md).

After deleting generated outputs, all three gates exited **0**:

- **Build:** hardware 234, scan 103, peripherals 71, service 288, review 12174, integration 2762739, F4 1378803, timer 22, preparation 420, UART 84, UI 702, gestures 586, Modbus 1576689 checks passed.
- **Core:** 125511 checks, 0 failures.
- **Acceptance:** 14361 passed, 0 failed.

Cppcheck **2.22.0: 0 findings**. Programming-script tests: **18 passed**; `program.ps1 -DryRun` exited **0**. No hardware was programmed.

Flash including CRC: **73432 → 73296 B**. Static RAM: **12247 → 9786 B**, saving **2461 B**. RAM including stack allowance: **13783 → 11322 B**.

AVR worst pass: **158856 cycles / 19.857 ms**, including reserve—under 20 ms, slightly above F5’s 19.740 ms after the timestamp and bounds fixes. Stack plus ISR overlay: **528/1536 B**.

The separate **60-day soak passed 265363192 checks across 259195038 passes** in **607.76 seconds**: 1218 power cuts, 21715 saves, one millisecond wrap and 16 event-sequence wraps.

The soak also found and fixed periodic reference-test window expiry and timestamps jumping backward at millisecond wrap. The u24 seconds field wraps at **194 days**; separate persisted fixtures cover that boundary.