# Brief - Lane F7: bound the gap between validated scans; programming-script checks

Continuation of your F1 session, after F6 (verified by Claude, uncommitted). Astra's re-check
(`briefs/astra-F5F6-recheck-report.md`) found no S1, two S2 and one S3. **Do not change any timing limit**:
`include/app/timing.h` (RUN window and scan deadline 1200 ms, loop 20 ms) and the spec stay as they are - raising
a limit is the owner's decision, not ours.

1. **S2 scheduler (Astra 1).** With healthy sensors, ADC RDY at the 49 ms worst case and loop intervals of
   20/8/20/20 ms (each <= 20 ms, lengthened to its measured AVR cost), the gap between two validated scan
   completions reached 1230 ms across the 10-min REF self-test (RUN latched off, G05) and 1210 ms on an ordinary
   scan. Cause: polling alignment per slot plus the separate CJ, final-verification (`END_SCAN`, 19 indices) and
   REF passes, all serial. Reduce the mandatory serial overhead so the **complete-to-complete interval** stays
   **<= 1100 ms** in the worst case, including a scan that contains the REF self-test, for any loop-interval
   sequence with every interval <= 20 ms. Candidates (your choice, keep it simple and spec-conformant): run the
   END_SCAN mutable-register checks during the wait passes of the last slot's conversion instead of after it;
   overlap CJ reads and the REF pulse with ADC conversions where `02` 10 and `03` allow it (check that REFTEST
   does not disturb a conversion - cite the clause); avoid idle passes between slots. Keep every check the spec
   requires each scan.
2. **Measure what matters.** `duration_ms` (service P15) and the gates must report the complete-to-complete
   interval including REF time, not only acquisition from scan start. Add an AVR profiler regression with jittered
   cadences (at least 20/8/20/20, 20/1/20/1, 19/20/3, random <= 20 ms with a fixed seed) and the REF self-test due,
   asserting uninterrupted healthy RUN and the <= 1100 ms bound; add the same to the soak (REF due under jitter).
   Report worst gap per pattern.
3. **S2 programming (Astra 2).** `program.ps1` must refuse an image that is not the production 24-ch image before
   touching fuses or flash: have `build.ps1` write metadata next to the image (board 24, CRC16, byte count, SHA-256
   of the hex), and have `program.ps1` check that the selected file matches it and that the stored CRC at
   0x1FFFE matches the image. Reject profiler, legacy and unpatched images (add mock tests for each).
4. **S3 efuse (Astra 3).** Accept efuse read-back when `(value & 0x07) == 0x04` (`02` 7); keep exact lfuse/hfuse.

Write rules as F5. Never `test/acceptance/`, `test/build_acceptance.ps1`. Iterate with host suites and
`profile_avr.ps1 -CompileOnly`; run the full `build.ps1` once at the end. Done means: outputs deleted;
`build.ps1`, `test/build_core.ps1`, `test/build_acceptance.ps1`, `test/integration/soak.ps1` exit 0;
`program.ps1 -DryRun` runs. Report under 500 words: what changed in the scheduler, worst gap per cadence pattern
(before/after), AVR worst pass, RAM/flash, soak result.
