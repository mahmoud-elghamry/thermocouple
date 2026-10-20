# Brief - Lane B3: make the core suite green (follow-up to B2)

You are the Lane B implementer (Codex Sol). Your B2 report said `test/build_core.ps1` had zero failures; Claude
re-ran it on the same tree and got **125429 checks, 3 failures** (your report said 125423):

```
FAIL test/unit/test_settings.c:284 cal_commit(&probe,&cal,cal.sequence,0)==RES_ERR_RANGE   (twice)
FAIL test/unit/test_protection.c:59 !h.out.window_refresh   (the window WAS refreshed by a scan tagged with a sequence older than a missed save: unsafe direction, fix the code unless the test is wrong)
```

Read `lane-B2-fixes.md` (the rules) and `firmware/spec/04-protection.md` 6.1, `05-settings-events.md` 5. For each
failure decide from the spec whether the test or the code is wrong and fix that one. Do not weaken a check to make
it pass; if the code is stricter than the spec and still safe, say so and correct the test with the spec clause in
a comment. Write only the files B2 was allowed to write. Do not touch `test/acceptance/` or `build_acceptance.ps1`.

## Done means

Delete `firmware/family/test/unit/output_core/` and `firmware/family/test/acceptance/output/` first (stale objects),
then run each of these **twice**, all exit 0 both times with identical counts:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File firmware/family/test/build_core.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File firmware/family/test/build_acceptance.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File firmware/family/build.ps1
```

If counts differ between runs, a test depends on uninitialised memory or order: find and fix it.

## Report (under 300 words)

Cause of each failure, what you changed, the six results with counts copied from the output.
