# Brief - Lane F1f: newer hot result must veto ACK (Astra re-check S1)

Continuation of your F1 session. Astra re-checked F1 at `233f0f1`: all five earlier findings are fixed, but it found
a new S1 and reproduced it on the AVR simulator. Read `firmware/family/briefs/astra-F1-recheck-report.md`.

Sequence: scan N cool, RUN on -> early in N+1 a TRIP-mode channel goes hot, immediate evaluation trips (correct)
-> a fresh ACK before N+1 completes is accepted because ACK uses N's cached `completed_clear` -> N+1 completes
validated, `results_evaluated` skips re-evaluation, the window opens: RUN closed with CH1 at 143.7 C, trip 100.0 C.

Fix (`04` 3.3, 5 rule 5, 6.1):
1. ACK uses the **newest** per-channel evidence for trip clearance too (you already did this for alarms in F1c):
   a newer over-trip or fault result on any fitted TRIP channel refuses ACK (R4), whatever the completed-scan
   cache says.
2. Before the window is granted or renewed, re-check current trip conditions even when completion re-evaluation
   is skipped; a scan whose results include an over-trip can never open the window.
3. Regression tests: this exact interleaving in the core unit tests and end to end in the integration suite (and,
   if your profiler harness allows, the AVR simulator case Astra used). Also the same with a channel fault (C01)
   instead of over-temperature.

Write rules as F1e. Never `test/acceptance/` (another lane adds an independent test in parallel). Done means:
outputs deleted; `build.ps1` (incl. profiler gate), `test/build_core.ps1`, `test/build_acceptance.ps1` exit 0.
Report under 300 words with counts.
