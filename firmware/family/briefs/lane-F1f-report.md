F1f is complete and verified. Newer hot/C01 evidence refuses ACK with R4, and scan completion rechecks trip conditions before opening the RUN window.

After deleting all three output directories, all required gates exited **0**:

- `build.ps1`: **2,773,070 integration checks** passed; supporting suites passed.
- `test/build_core.ps1`: **125,504 checks, 0 failures**.
- `test/build_acceptance.ps1`: **14,270 passed, 0 failed**.

Hot/C01 regressions pass on host and AVR simulator. The new core tests produce **40 failures against pre-fix code**.

Profiler: **2,430 passes**, worst **101,487 cycles / 12.686 ms**, below **160,000 cycles**, including reserve.

Flash: **56,702 bytes** including CRC. RAM with stack allowance: **11,938/12,288 bytes**.

State updated; documentation check: **0 findings**. Acceptance sources untouched. No commits made.

[Full report](firmware/family/briefs/lane-F1f-report.md)