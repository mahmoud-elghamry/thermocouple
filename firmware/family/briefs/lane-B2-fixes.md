# Brief - Lane B2: fix the core against the independent acceptance findings

You are the implementer (Codex Sol) of the pure core (Lane B). An independent tester (Lane C) wrote acceptance
tests from the spec only; 12 assertions fail. Claude reproduced them and clarified the spec. Do not run git
commands that write.

## Read first

`firmware/spec/04-protection.md` section 6.1 (the paragraph starting "ACK ordering" - updated today: same-pass
ACK + scan, settings-sequence rule, OFF channels), `05-settings-events.md` section 5 (epoch wrap 63 -> 0),
`firmware/family/briefs/lane-C-report.md`, the failing lines in
`firmware/family/test/acceptance/test_accept_protection.c` / `test_accept_outputs.c`.

## Fix (write ONLY these files, plus their unit tests under `test/unit/` and `test/scenarios/`)

`src/app/protection.c`, `include/app/protection.h`, `src/services/fault.c`, `include/services/fault.h`,
`src/services/settings*.c`, `include/services/settings.h`.

1. **OFF channels:** C01-C09 latched on a channel whose type is OFF must not make `alarm_active` true (nor trip,
   nor refuse ACK). `fault_alarm_latched` has no settings; give protection a way to ask only global/bank latches
   and evaluate C latches per fitted channel.
2. **ACK + scan in the same `prot_step`:** that scan must not open the window; PWM waits for a later pass.
3. **Settings sequence:** protection keeps the sequence it accepted (set at ACK into RUN). Window refresh needs
   `settings->sequence` == that sequence and the scan tagged with it; after a names-only `commit_done` in RUN the
   accepted sequence moves to the new one and the replaced one is still accepted until the first new-sequence
   scan. A sequence change without `commit_done` refreshes nothing.
4. **Epoch wrap:** the commit path that takes a channel's type epoch from 63 to 0 must also store that channel's
   burnout baseline as 'not learned' in the calibration record (A/B, power-cut safe in the existing step
   machine). Expose it through the public header so it can be tested end to end.

Do not edit anything under `test/acceptance/` or `build_acceptance.ps1`: those are the independent oracle.

## Done means

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File firmware/family/test/build_core.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File firmware/family/test/build_acceptance.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File firmware/family/build.ps1
```

all three exit 0. If an acceptance assertion still fails and you believe the test (not the code) is wrong, leave it
failing and argue it in the report with the spec clause.

## Report (final message, under 400 words)

What changed per item, the three results with counts, anything still failing and why.

## Resume note (2026-10-21)

A first B2 run was interrupted mid-work: its edits are in the working tree (`git diff` shows them - protection,
fault, settings_store, their headers and unit tests). Continue from them; do not start over.
