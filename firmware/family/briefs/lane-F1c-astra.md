# Brief - Lane F1c: fix the Astra review findings of F1

Continuation of your F1 session. Astra (read-only reviewer) reviewed F1; Claude checked the findings against the
code and accepts all of them. Full text: `firmware/family/briefs/astra-F1-review-report.md` - read it first.

Fix, each with a test that fails before the fix where a host test can show it:

1. **S1 Timer2 expiry is not sticky.** Latch expiry in the ISR (`timer.c`); the shell must never restart the PWM
   after an expiry, protection must see it as G05 (TRIPPED, ACK needed) even if a validated scan arrives in the
   same pass. Re-check at the hardware handoff. `04` 6.1, `02` 4.2.
2. **S1 SET does not abort an active relay test until release.** During any active relay test (A01-A05 that drive a
   relay), any newly debounced *press* of any key stops it at once, independent of the release-based gesture
   events. `08` 1, `04` 4.
3. **S2 CPU budget on the AVR.** `first_fault` does ~2592 `fault_at` calls per pass (~11.7 ms of call overhead
   alone at 8 MHz) and scan completion runs whole-record `set_validate` per channel. Search the fault bitmaps by
   byte (skip zero bytes); validate settings and rebuild the fitted mask once per pass, not per result. Then give
   a **worst-case cycle estimate for one full loop pass on the AVR** from the `-Os` disassembly / code structure
   (method + number), against the 8 ms budget of `01` 2. If an AVR simulator is available on this machine (simavr,
   or Proteus under `C:/Program Files (x86)/Labcenter Electronics/`), measure instead and say how.
4. **S2 ACK press timestamped twice.** Carry the key driver's press/event timestamps through to `ack_input`; one
   authoritative held duration and event age. `04` 5 rule 2.
5. **S2 ACK clears a live alarm with older scan evidence.** Alarm clearance must use the newest per-channel result
   (immediate slot evidence), never an older completed scan. `04` 3.3, 7.2.
6. **Queued:** remove `service_entry|=!set_valid` in `main.c`; invalid settings/calibration boot to CONFIG_LOCK,
   service only by SET at power-up (`08` 1 as changed today).

## Write

For this run you may also edit `src/app/protection.c`, `include/app/protection.h`, `src/services/fault.c`,
`include/services/fault.h`, `src/mcal/timer.c`, `include/mcal/timer.h`, `src/drivers/keys.c`,
`include/drivers/keys.h`, plus everything your F1 brief allowed. Unit tests for those modules under `test/unit/` may
be extended (never weakened). **Never** touch `test/acceptance/`, `test/build_acceptance.ps1`, `include/common/*`.

## Done means

Delete `build/`, `test/unit/output_core/`, `test/acceptance/output/`; then `build.ps1`, `test/build_core.ps1`,
`test/build_acceptance.ps1` all exit 0. Report under 500 words: per finding what changed and which test proves it,
the cycle estimate (method + number), the three results with counts copied from the output, AVR flash/RAM.
