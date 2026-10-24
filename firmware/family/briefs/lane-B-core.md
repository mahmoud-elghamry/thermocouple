# Brief - Lane B: pure core (F0 parts + F1 logic), host-tested

You are the implementer (Codex Sol). Another implementer works in parallel on Lane A (hardware path). Claude
reviews your diff, runs the gates and commits. Do not run git commands that write.

## Read first

`firmware/spec/00-overview.md`, `01-architecture.md`, `03-acquisition.md` sections 7, 10, 11, `04-protection.md`
(all), `05-settings-events.md` (all), `09-tests.md`, `10-phases.md`; decisions `docs/decisions/0043*`, `0034*`,
`0029*`; existing 8-ch code for reuse ideas: `firmware/src/app/protection.c`, `settings.c`,
`firmware/src/hal/settings_store.c`, `firmware/tests/`.

## Write ONLY under `firmware/family/` and only these parts

* `include/services/` + `src/services/`: `tc_math` + `tc_tables` (NIST ITS-90 K and J, voltage domain, integer
  only, table step and error bound per `03` 7), `settings` (pack/unpack, CRC16, validator, A/B selection,
  calibration record incl. staged parts and type-epoch tags, commit procedure as a state machine over an EEPROM
  interface), `events` (ring, CRC8), `fault` (registry by (code, unit), `01` 4).
* `include/app/` + `src/app/`: `channel_eval`, `protection` (states, ACK rules, first-out, immediate trip on
  result and on fault, RUN window logic incl. expiry = trip), `outputs` logic split so the decision part is pure
  (window, read-back table of `04` 6.2) and the pin part is a thin call into an `outputs_hw.h` interface that
  Lane A implements.
* `test/unit/` for every module; `test/scenarios/` with S01-S28 of `09` 3 that need only your modules plus fakes
  of `scan_out_t` input (write the scenario harness with simulated time; S05/S06/S09-S14 that need the fake ADC
  may be written against `scan_out_t` sequences instead).
* Shared headers `include/common/types.h`, `meas.h`, `fault_codes.h` are owned by Claude: use them as they are;
  request changes in your report.
* Host build: your own `test/build_core.ps1` (same compiler setup as the existing host tests) so you do not touch
  Lane A's `build.ps1`.

## Rules

* Tests first from the spec (every row of every table in `04` and `05` gets a test), then code. Pure functions:
  no globals, no I/O (`01` 3 "functional core").
* No dynamic memory, no floats, bounded loops, `-Wall -Wextra -Werror`. Modules <= ~400 lines.
* Unknown/out-of-range enum values -> most restrictive behaviour (`01` 5). Never invent setpoints.

## Report (your final message)

Files written; test results with the exact command; anything in the spec you found wrong, ambiguous or missing
(file + section); requested changes to the shared headers. Under 600 words.
