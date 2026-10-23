# Brief - Lane C3: independent acceptance test - newer evidence vetoes ACK

You are the independent tester who owns `firmware/family/test/acceptance/` (same independence rule as before: spec
and public headers only, never `src/` or other test folders; no git writes).

Add tests from `04-protection.md` 3.3, 5 (rule 5) and 6.1 for this interleaving: completed scan N cool, RUN
granted; then, before scan N+1 completes, an immediate per-channel result shows a TRIP-mode channel over its trip
setpoint (and, separately, a channel fault such as OPEN) -> protection trips; an ACK before N+1 completes must be
refused (R4) and RUN must stay open; when N+1 completes containing that hot result, the window must not open.
Also the cool case: the newer result back below trip minus band -> ACK accepted after the next validated scan.

The production code is being fixed in parallel; failures now are expected - report them, do not chase them. Run
`firmware/family/test/build_acceptance.ps1` once at the end. Report under 250 words: tests added (clause), result
with counts, each failure expected vs actual.
