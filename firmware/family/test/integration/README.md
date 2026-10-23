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

F1b replays a simultaneous 24-channel C-fault fan-out at the registry seam while
all three register-fake ADCs report transport loss. Recovery uses real scans and
keys, with no reset: queue loss raises G13, never G04, and clears only on an
accepted ACK after the final queued EEPROM byte is durable. Tests also cover an
early accepted ACK, drain without ACK, preservation of another G13 save-failure
source, dropping the new entry, and giving the final free queue slot to first-out
TRIP before its companion FAULT. First-out code, channel, unit, value, threshold
and uptime are checked in EEPROM. The saturating per-boot loss count remains
available after ACK and is printed as `P17 EVENTS_LOST` in the service report.

The settings cut sweep covers all 403 emitted byte writes, the initial boundary,
and durable magic before RAM publication. Every case boots and checks both
changed protection fields together; both the old and the new record must occur.
The boundary counter includes only settings-slot writes, so background counter
and event writes cannot truncate the sweep when acquisition timing changes.
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

F1c follows the revised `08` section 1: invalid settings or calibration enter
CONFIG_LOCK; only SET at power-up enters SERVICE. Service exit is reset only;
a valid, complete board restarts START_LATCHED.

F1c adds `test_review.c` for ISR expiry at the hardware handoff, no scan-only
restart, accepted ACK recovery, authoritative 50 ms ACK timestamps and event
age, and held-key aborts for every physical key during A02/A03/A04. A separate
`test_timer.c` executable compiles the real Timer2 ISR against register stubs.
Core tests retain the newest hot/cool channel evidence across ACK and an older
completed scan. The 24-fitted-channel test counts one settings validation per
normal pass, including completion. Event-cursor recovery is compared with the
pure event implementation across sequence wrap and a torn newest entry.
The service abort matrix includes a names-only commit notification coinciding
with a SET press: gesture rearming must preserve the physical abort edge.

Run `powershell -File firmware/family/test/integration/profile_avr.ps1` for AVR
instruction measurements. It uses the installed PlatformIO AVR GDB simulator,
the Proteus AVR compiler at `-Os`, real application/services/drivers and the
same register models. The profiler excludes complete fake MCAL call frames and
adds bounded real MCAL costs. The actual software SPI is separately simulated
for all 256 transmitted byte values; the actual Timer2 ISR is calibrated too.
The simulator needs its ELF architecture corrected from avr:51 to avr:5 to use
the ATmega1284P's two-byte PC, and `.data` restored after startup because it does
not load that section's flash LMA. Neither workaround changes instruction bytes.
The profiler aliases EEPROM A/B fixture slots to fit SRAM; power-cut correctness
belongs to the independent full-EEPROM host suite, not this timing harness.
Raw cycles, per-pass estimates and calibration results are in `build/profile/`.
The gate reserves 25% + 2048 cycles for interrupts. It measures 1782 full
passes across boot, held ACK, healthy scans, a 24-channel fault burst, names and
protection saves, service, epoch wrap, a changed LCD frame, and a deliberately
combined preparation step + current CJ frame + ADC completion + real queued ACK.
The combined case requires all four evidence bits, and all target functional
checks must pass. This is a measured path set with conservative MCAL bounds,
not an exhaustive WCET proof for every possible input.

F1e timing values live only in `include/app/timing.h`: RUN window 1200 ms,
scan freshness/deadline 1200 ms, loop limit 20 ms (160000 cycles at 8 MHz),
ADC observed RDY 36..69 ms. The service relay exercise remains 1000 ms.
The profiler reads that same header for its cycle gate. `build.ps1` runs the
profiler automatically; `-HostOnly` runs just the native suites. The standalone
profiler command is `powershell -NoProfile -ExecutionPolicy Bypass -File
firmware/family/test/integration/profile_avr.ps1`. A run takes about one minute
on this machine, so it remains in the normal build gate.

Latest measured maximum: 102017 cycles / 12.752 ms including reserve, during
boot. The combined case measures 91317 cycles. Actual target calibration:
soft SPI 431 cycles/byte, Timer2 ISR <=216 cycles over 2049 samples, async commit
begin <=2640 cycles, preparation step <=1901 cycles over 190 samples. Both
legacy synchronous commit APIs retain their original complete-image contract;
the real EEPROM owner uses bounded preparation and immutable mailboxes.

CPU reductions retained from F1d include direct fixed-pin software SPI and key
sampling; one checked CJ frame per pass; one conversion completion per pass
while every pending bank's STATUS is still polled; retained first-RDY timing
before delayed held-DATA reads; bounded commit preparation; notification-only
changed-code hints; protection evidence caches; nibble CRC tables; bounded LCD
updates. Protection always reads authoritative fault bitmaps. The ADC/scan,
LCD and service changes are the permitted integration exceptions: they bound
loop work, preserve acquisition timing evidence, and report the shared limit.

The simulator instruments every RET of opaque MCAL wrappers. Explicit code
pointer casts avoid AVR GDB's data-space and 16-bit signed-offset ambiguity.
Each measured pass checks balanced exits and exact hardware/software SPI byte
counts. `run_gdb.py` keeps cycle evidence while discarding repeated section
inventories. Target SPI/key checks, prepared-image comparisons, and mixed-load
checks all require zero errors before the cycle-budget gate can pass.

No acceptance file, acceptance build script, or common header is changed by
this lane. Timing expectations in core fixtures and scenarios retain their
boundary meaning with values from the shared header. Native integration still
sweeps 405 settings power-cut boundaries and checks both old and new records.
