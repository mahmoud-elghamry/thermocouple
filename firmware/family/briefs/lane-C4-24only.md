# Brief - Lane C4: independent acceptance test - 24-ch only

You are the independent tester who owns `firmware/family/test/acceptance/` (same independence rule as before: spec
and public headers only, never `src/` or other test folders; no git writes).

Owner decision 2026-10-23 (`firmware/spec/00-overview.md` Targets, `docs/decisions/0043` section 9): the firmware
implements the 24-ch board only. `include/common/types.h` now has `MAX_CHANNELS` 24 and `MAX_BANKS` 3; the 40-ch,
PT100 and decoder code is being removed from `src/` in parallel (lane F6).

1. `test_accept_settings.c` around lines 171-186 builds a 40-ch record (`board_type=40`, `channel_count=43`,
   `b.ch[40]`, `CH_TYPE_PT100`). That indexes past the 24-entry arrays now. Replace it with the 24-ch-only checks
   that follow from `05` (record header bytes 3-4 "must equal the build", and the validity rule that follows) and
   `00` Targets: a record whose board type or channel count
   is not the 24-ch build's is rejected (never RES_OK) and the board stays in CONFIG_LOCK; a channel type outside
   OFF/K/J is rejected. Keep every other assertion unchanged. If a public header no longer declares a constant you
   used (for example `CH_TYPE_PT100`), test with the raw value the spec gives and say so.
2. Search the whole acceptance folder for anything else that assumes more than 24 channels or 3 banks (indexes,
   loops with literal 40/43/5/6, bank letters D/E) and fix it the same way.

The production code is being changed in parallel; failures now may be expected - report them, do not chase them.
Run `firmware/family/test/build_acceptance.ps1` once at the end. Report under 250 words: what you replaced (clause),
result with counts, each failure expected vs actual.
