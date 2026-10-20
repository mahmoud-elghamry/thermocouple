# F1 integration

Run `powershell -NoProfile -ExecutionPolicy Bypass -File firmware/family/build.ps1`.
The host source list replaces the obsolete F0 `test_main.c` (which asserted that
ACK could never grant RUN) with `test_app.c`. The other hardware, scan, peripheral
and service unit tests still run unchanged, before integration enables its model.

The real boot, drivers, scanner, protection, output filter and EEPROM protocol
are linked. `model.c` reuses Lane A's unchanged register-level fakes and extends
the MCAL seam with 3.4 ms byte programming, Timer2 during bus work, a 250 ms
watchdog, EEPROM errors and cuts that discard the unfinished byte.

Coverage includes S01-S06, S09-S12 and S14: real key gestures, delayed permission
after ACK, hysteresis, 28 crossing phases, stalled acquisition, every missing
flow checkpoint, watchdog restart, SPI retries, ADC/CJ/reference faults and both
feedback inputs. Additional cases cover names/protection saves, failed-save retry,
epoch wrap, all 24 channels fitted, ALARM ONLY, C03 channel attribution, service
mailbox commits and REF/burnout calibration with OFF inputs.

The settings cut sweep covers all 403 emitted byte writes, the initial boundary,
and durable magic before RAM publication. Every case boots and checks both
changed protection fields together; both the old and the new record must occur.
Independent core/acceptance suites retain their broader storage fault sweeps.

Timing reports measure simulated **PWM stop**, not a physical contact. The loop
model accounts for SPI bytes, software SPI, explicit delays and EEPROM reads;
it excludes C instruction execution. Its microsecond maximum is a host-model
result, not AVR CPU WCET. Actual loop WCET and pump/contact decay require bench
measurement (`08` P16 / `09` T05). All setpoints in this suite are explicit test
fixtures; production boot creates none.

The AVR build also checks the commit stack frame plus a 384-byte caller/interrupt
margin. F0's 1 KiB allowance is insufficient: the existing pure settings commit
alone takes 1046 bytes at `-Os`. The shell reserves 1536 bytes, shared between its
canary and build budget through `app/stack_budget.h`, within the 12 KiB total.
`10` §2's 1 KiB stack estimate needs the reviewer's documentation update.

Spec conflict retained for reviewer: `08` §1 automatically services blank/invalid
boards, while `04` §4 / `05` §4 call for CONFIG_LOCK. F1 follows F0/`08` for those
boards; valid settings with incomplete calibration enter CONFIG_LOCK. Service
exit is reset only; a valid, complete board restarts START_LATCHED.
