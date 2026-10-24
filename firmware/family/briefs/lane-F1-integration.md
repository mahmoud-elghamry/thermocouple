# Brief - Lane F1: integrate protection into the 24-ch firmware

You are the implementer (Codex Sol), the **only** writer in `firmware/family/` for this run. Lanes A (hardware path,
F0) and B (pure core: protection, settings, events, fault, channel_eval, outputs decision) are done and green; an
independent acceptance suite guards the core. Your job is phase F1 of `firmware/spec/10-phases.md` 3: the real
firmware that can grant RUN. Claude reviews, re-runs the gates and commits. Do not run git commands that write.

## Read first

`firmware/spec/00`, `01` (all - loop, flow check, data ownership, mailbox, copy-edit-validate-commit), `02` 4.2
and 8 (Timer2 deadline, boot order), `04` (all), `05` (all), `08` 1-2 (service entry/exit), `09`, `10`; then the
current code: `src/app/main.c` (F0: protection is a stub that keeps RUN off), `include/app/*.h`,
`include/services/*.h`, `src/drivers/relays.c`, `briefs/lane-A-report.md`, `lane-B-report.md`, `lane-B2-report.md`.

## What to build

1. **Main loop with protection** (`01` 2, `04`): replace the F0 stub. Each pass: scan -> immediate per-channel
   results (`scan_take_results` -> `prot_on_result`) and immediate faults (`prot_on_fault`) -> `prot_step` ->
   `outputs_step` -> `outputs_hw_apply` (Timer2 deadline armed from `window_remaining_ms`, never reloaded to 900 ms
   by the shell) -> read-back faults G06/G07 back into protection. Keys give the ACK command with held/age/
   released per `04` ACK rules. Flow check covers every task; any missed checkpoint lets the watchdog reset.
2. **Boot to START_LATCHED** with the loaded settings + calibration (already in F0 boot); CONFIG_LOCK on invalid
   settings/calibration; SERVICE entry/exit per `08` (leaving service always goes to START_LATCHED).
3. **EEPROM ownership** (`01` data ownership): one owner serialises settings commits, calibration commits and event
   writes through the `set_store_step` / `ee_*` protocol; nothing blocks the loop. Event persistence: one entry per
   transition (`prot_out_t.event_mask`), POWER_UP after the first validated scan, power-cycle count (`05` 7).
4. **Settings commit path** usable by service mode and later by the UI (F2): a mailbox command carrying a
   validated candidate; protection gets `commit_begin/commit_done/protection_change` exactly as `prot_in_t`
   documents; type-epoch wrap goes through `set_commit_with_cal`.
5. **Integration tests** in `test/integration/` (new): the whole firmware on the host with the register-level
   fakes and simulated time. At least: S01-S06, S09-S12, S14 of `09` end to end (fake ADC -> scan -> protection
   -> pin); an over-temperature crossing opens RUN (PWM stopped) within **1000 ms** simulated in the normal case
   and report the measured worst case (requirement 2 s); ACK refusal and acceptance through the keys; a stalled
   ADC stops the pump within the window and latches G05; power cut during a commit (old or new, never a mix).
   Add the suite to `build.ps1` so one command runs everything.

## Write ONLY

`src/app/main.c`, new files under `src/app/` and `include/app/` for the glue (e.g. `app.c`, `ee_owner.c`,
`ack_input.c`), `sources/*.txt`, `build.ps1`, `test/integration/`, `test/stubs/` (remove stubs that the real
modules now replace). Small changes in `src/services/scan.c`, `src/app/service.c`, `src/drivers/*.c` are allowed
**only** if integration cannot work without them; list each with its reason in the report.

**Do not edit:** `src/app/protection.c`, `channel_eval.c`, `outputs.c`, `src/services/settings*.c`, `fault.c`,
`events.c`, `tc_*.c`, their headers, `include/common/*`, anything under `test/acceptance/`, `test/unit/`,
`test/scenarios/`, `test/build_*.ps1`. If one of them is wrong or missing something, stop that item and report it
with the spec clause - Claude decides.

## Rules

Tests first, then code. No dynamic memory, no floats, bounded loops, `-Wall -Wextra -Werror`, modules <= ~400
lines. Loop worst case <= 8 ms (`10` 2): measure it in the host model and report. Never invent setpoints.

## Done means (delete `build/`, `test/unit/output_core/`, `test/acceptance/output/` first; all exit 0)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File firmware/family/build.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File firmware/family/test/build_core.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File firmware/family/test/build_acceptance.ps1
```

## Report (final message, under 600 words)

Files written/changed (with the reason for any change outside your list), the three results with counts copied
from the output, AVR flash/RAM, loop worst case, crossing-to-open times, spec gaps or contradictions (file +
section).
