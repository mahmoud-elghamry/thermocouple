# Brief - Lane F1e: new timing limits, finish the CPU work

Continuation of your F1 session. Claude stopped your F1d run on purpose: the owner raised the limits on
2026-10-23 (like Murphy, requirement 2 s) so you no longer need to squeeze the loop to 8 ms. New numbers (see
`git diff 660d0cb -- firmware/spec`): RUN window `T_WIN` **1200 ms** (was 900), scan freshness/deadline **1200 ms**
(was 1000), worst loop **20 ms = 160000 cycles incl. your reserve** (was 8 ms / 64000), ADC RDY window **36-69 ms**
(was 36-57; timeout = 1.15 x 42.331 + 20).

1. Put these numbers in **one** header (e.g. `include/app/timing.h`) and use it everywhere: `protection.c`
   WINDOW_MS, `outputs.c` and `relays.c` range checks, `timer.c` deadline limit (must accept 1200; the service
   relay test keeps its own 1000 ms), `app.c` window watch, `ad7124.c` 36/57, `acquisition_budget.h`, the profiler
   gate (`profile_summary.py` 64000 -> 160000). No other behaviour change.
2. Keep the CPU reductions you already made (soft SPI, one CJ per pass, split commit, ISR); finish only what is
   half-done so the tree is consistent. Do not chase further cycles once the profiler is under 160000.
3. Your own tests (unit, integration, timer, review) follow the new numbers. Do **not** touch
   `test/acceptance/` or `build_acceptance.ps1`: another lane updates them in parallel from the spec.

Write rules: as F1c/F1d. Done means: outputs deleted, `build.ps1` and `test/build_core.ps1` exit 0, the profiler
under 160000 cycles. Also run `test/build_acceptance.ps1` once at the very end and report its result as is (it may
still be mid-update). Report under 400 words: files changed, the numbers per file, profiler worst pass, results
with counts, AVR flash/RAM.
