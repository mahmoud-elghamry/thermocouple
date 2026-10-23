# Brief - Lane F8: REF retry after a transient G08; firmware identity in the image

Continuation of your session after F7 (verified by Claude, uncommitted). Astra's F7 re-check
(`briefs/astra-F7-recheck-report.md`): no S1, two S2. Timing limits stay unchanged.

1. **S2 REF lockout (Astra 1).** F7 regression: when REFOK reads high at the start of the periodic test,
   `ref_begin()` raises G08, clears `ref_test_ok` **and sets `last_ref`**, so after REFOK returns low no scan can
   validate for ~10 min (AVR: all banks validated, board scan invalid, next test 595 s away). Before F7 the test was
   retried on the next scan. Fix: a failed precheck is not a completed test - keep the attempt pending and retry at
   the next slot-10 opportunity (one attempt per scan), with the full pulse/recovery checks of `02` 10; only a
   completed test (pass or G09) restarts the 10-min interval. G08 still trips and needs ACK as `04` says. Add host
   and AVR regressions: REFOK high at test entry, restored 5 s later -> first scan after a successful test validates
   and ACK recovers; REFOK held high -> never validates.
2. **S2 image identity (Astra 2).** The validator accepted a 64-byte fixture with a matching sidecar as a
   production image, and an old production HEX with its old sidecar also passes. Make identity part of the
   firmware itself: a small constant record linked at a fixed flash address (magic, board 24, MCU, firmware
   version, git commit short hash, dirty flag), written by `build.ps1` from `git rev-parse` at build time.
   `image_metadata.py` must find and check that record inside the HEX payload (and the CRC must cover it).
   `program.ps1` prints the identity and refuses unless the embedded commit equals the current `git rev-parse HEAD`
   of this repo (a dirty build is allowed but printed as `DIRTY` in the PASS line), or the user passes
   `-Release <path>` naming an approved release HEX + sidecar. Mock tests: 64-byte fixture, old image, other-board
   image, missing record, release path. If `08` service mode has a version/identity line, report the same record
   there; if not, say so (do not change the spec).

Write rules as F5. Never `test/acceptance/`, `test/build_acceptance.ps1`. Iterate with host suites and
`profile_avr.ps1 -CompileOnly`; full `build.ps1` once at the end. Done means: outputs deleted; `build.ps1`,
`test/build_core.ps1`, `test/build_acceptance.ps1`, `test/integration/soak.ps1` exit 0; `program.ps1 -DryRun`
runs. Report under 400 words with counts, AVR worst pass, worst jitter gaps, flash/RAM.
