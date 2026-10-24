# Brief - Lane C2: update the independent acceptance tests to the new timing (spec only)

You are the independent tester (Codex Sol) who owns `firmware/family/test/acceptance/`. Same independence rule as
your first brief (`lane-C-acceptance.md`): derive expectations from the spec only; never open
`firmware/family/src/` or the other test folders. Do not run git commands that write.

The owner raised the timing limits on 2026-10-23 (limits like Murphy, requirement 2 s): RUN window `T_WIN`
900 -> **1200 ms**, scan freshness/deadline 1000 -> **1200 ms**, loop worst 8 -> **20 ms**, ADC RDY window
36-57 -> **36-69 ms**. Read `git diff 660d0cb -- firmware/spec` for the exact changes, then `04-protection.md` 2,
5, 6.1, 6.3, `03-acquisition.md` 3, 10, 11, `09-tests.md` S05/S26.

Update every test whose expected value or input timing derives from those numbers (window length, expiry instant,
freshness age, the end-to-end crossing budget). Keep every other assertion unchanged. Each changed test still
names its spec clause. Write ONLY `firmware/family/test/acceptance/` and `test/build_acceptance.ps1`.

The production code is being changed in parallel to the same numbers, so failures right now are expected: report
them, do not chase them. Run `powershell -NoProfile -ExecutionPolicy Bypass -File
firmware/family/test/build_acceptance.ps1` once at the end. Report (under 300 words): which tests changed and
why (clause), the run result with counts, and each failure with expected vs actual.
