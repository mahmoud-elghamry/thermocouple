# Astra re-check - fixes to the F1 review (read-only)

Your F1 review (`firmware/family/briefs/astra-F1-review-report.md`) found 2 S1 + 3 S2. Since then (commits after
`0a441fc` on this branch): F1c fixed them, F1d/F1e cut CPU time, and the owner raised the timing limits on
2026-10-23 (RUN window and scan freshness 1200 ms, loop worst 20 ms; requirement 2 s like Murphy; spec diff:
`git diff 660d0cb d74a2e9 -- firmware/spec`). All host suites and an avr-gdb cycle profiler pass (worst pass
12.75 ms).

Check, read-only, under `firmware/family/`:
1. Each of your five findings: is it really fixed on the AVR, not only in the host model? Quote file:line.
2. The new code paths: sticky Timer2 expiry (`src/mcal/timer.c`, `src/drivers/relays.c`), split settings commit
   (`src/services/settings_store.c`, `settings.c`, `src/app/ee_owner.c`) - power cut or reset at any step must
   leave old or new, never a mix, and never let RUN close on half-prepared settings; one-CJ-per-pass schedule and
   soft SPI (`src/mcal/spi.c`, `src/drivers/tmp126.c`) against the TMP126 timing and `02` 2 SIO_WR_N order;
   `include/app/timing.h` used consistently.
3. Anything new of severity S1/S2 (same scale as before).

Report under 900 words: per item fixed / not fixed with evidence, new findings with file:line, trigger sequence,
spec clause, minimal fix. Say plainly if no S1. Do not edit files.
