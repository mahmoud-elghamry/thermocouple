# Brief - Lane F5: fix the Astra full-review findings

Continuation of your F1 session. Astra's full review of the integrated firmware (`f9b5a4f` + runner commits) found
**no S1**, two S2 and two S3; Claude accepts all four. Read `firmware/family/briefs/astra-full-review-report.md`.

1. **S2 commissioning:** clear G01 as soon as settings are valid (G10 stays for missing calibration); the UI's
   "blank board" decision uses settings validity, never G01 - so after the first save the saved PIN and channel
   configuration are used and the display says CALIBRATE. `05` 5, `06` 5-6.
2. **S2 scan time vs loop cadence:** the scan must meet `03` 10.2 (worst ~1050 ms, deadline 1200 ms) with the loop
   at its 20 ms worst, not only at 1 ms. Reduce the number of loop passes a scan needs (bounded batching of CJ,
   DATA and end-of-scan verification work per pass, still inside the per-pass cycle budget). Make the profiler
   advance simulated time by the **measured cycles of each pass** (not a fixed 1 ms) and add a gate: full scans at
   sustained 5, 10 and 20 ms cadence stay < 1200 ms and validated. Keep the owner's 1200 ms limits.
3. **S3:** latch the ACK refusal channel with its reason for the message lifetime (`06` 3.4).
4. **S3:** C10/C11 alarms update the newest-cause view (`06` 3, priority 6).
5. **Stack:** measure the integrated stack high-water mark (paint at boot, scan in the profiler over the combined
   UI + commit + Modbus + ISR passes; also expose it in service mode next to P16) and gate it below the 1536 B
   allowance.

Write rules as F4 (any file in `firmware/family/` except `test/acceptance/`, `test/build_acceptance.ps1`,
`include/common/*`; never weaken an assertion). Done means: every output/build directory deleted, then
`build.ps1`, `test/build_core.ps1`, `test/build_acceptance.ps1` exit 0. Report under 400 words with counts, the
scan times at 5/10/20 ms cadence, stack high-water, flash/RAM.
