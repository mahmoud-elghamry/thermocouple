# Brief - Lane C: independent acceptance tests for the protection core

You are an independent tester (Codex Sol). Two other implementers wrote the code; your job is to find where it
disagrees with the specification. Claude reviews your work and commits. Do not run git commands that write.

## Independence rule

Derive every expected result from the **specification only**: `firmware/spec/00-overview.md`, `01-architecture.md`,
`03-acquisition.md` section 7, `04-protection.md` (all), `05-settings-events.md` (all), `09-tests.md`,
`docs/GOAL.md`. You may read the **public headers** under `firmware/family/include/` to know how to call the code.
**Do not open anything under `firmware/family/src/` or the existing tests under `firmware/family/test/unit/` and
`test/scenarios/`** - an expected value copied from the implementation proves nothing.

## Write ONLY

* `firmware/family/test/acceptance/` (test files, fixtures, a runner) and
* `firmware/family/test/build_acceptance.ps1` - copy the compiler setup of `firmware/family/test/build_core.ps1`
  (you may read that script) and link against the same production sources it lists.

## What to test

1. Every row of the channel truth table and the master fault table of `04` (action per mode: TRIP vs ALARM_ONLY,
   OFF channels ignored, unknown enum values -> most restrictive).
2. The state machine of `04`: CONFIG_LOCK / START_LATCHED / RUN / TRIPPED / SERVICE, every allowed and forbidden
   transition, ACK rules R1-R6 including held key, stale ACK, ACK during a save, ACK with a fault still present.
3. The RUN window: opened only by a validated scan in RUN; expiry = G05 trip; a late scan after expiry must not
   re-close the contact without ACK; ACK ordering of `04` 6.1. Over-temperature opens RUN at once (no waiting).
4. Read-back of `04` 6.2 with the sense polarity (sense reads LOW when the coil is energised).
5. Settings `05`: A/B selection after a power cut at every write step, CRC and semantic validation, OFF canonical
   encoding, type change clears setpoints and bumps the epoch, epoch wrap 63 -> 0 invalidates the baseline,
   calibration completeness (tag must equal current type + epoch).
6. Thermocouple conversion `03` 7 against the NIST reference points listed there (bound + 0.05 C rounding).
7. End-to-end timing in simulated time: an over-temperature crossing must open RUN within 2 s (requirement, GOAL)
   assuming the scan timing of `03` (normal ~690 ms, worst ~870 ms); report the computed worst case.

Each test names the spec clause it checks (file + section + row). Bounded loops, no dynamic memory, warnings as
errors, same as the production build.

## Report (your final message, under 600 words)

The exact command and counts. **Every failing test is a finding:** give the spec clause, the input, the expected
value from the spec, the value the code returned. Say for each whether you believe the code or the spec is wrong.
Also list spec clauses you found untestable through the public headers.
