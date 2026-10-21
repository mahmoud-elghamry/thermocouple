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
The sampled full-pass estimate reserves 25% + 2048 cycles for interrupts and is
not an exhaustive WCET proof. It exceeds the 64000-cycle (8 ms) budget.
The final sampled maximum is 334015 cycles / 41.752 ms, with epoch-wrap commit
and CJ read in the same pass: 159463 production CPU cycles + 106110 MCAL bound,
then the interrupt reserve. Pure epoch-wrap commit alone is 109606 cycles /
13.7007 ms. The calibration measures Timer2 ISR execution at 716 cycles.

S3 remains blocked by protected sources: `set_commit_with_cal()` alone measures
76044 cycles (9.5055 ms), and `src/mcal/spi.c` software SPI measures 3234 cycles
per byte (97020 cycles / 12.1275 ms for a normal 30-byte CJ read). Both violate
`01` section 2 before other loop work. Neither protected file was changed.
Allowed CPU reductions include byte searches, one validation per pass, an
incremental event-ring recovery/cached cursor, bounded service EEPROM CRC work,
incremental mutable ADC verification, and removal of LCD modulo division.

Production file inventory (relative to `firmware/family`):

- `src/app/{main,app,protection,ack_input,ee_owner,service}.c`;
  `include/app/{protection,outputs_hw,acquisition_budget}.h`.
- `src/drivers/{keys,relays,ad7124,lcd}.c`, `include/drivers/keys.h`;
  `src/mcal/timer.c`, `include/mcal/timer.h`;
  `src/services/{fault,scan}.c`, `include/services/fault.h`.
- Small permitted integration exceptions: relay handoff checks expiry atomically;
  service adds press abort and chunks EEPROM CRC; ADC/scan split the final mutable
  verification without weakening its checks, retaining ID/transport classification;
  LCD cursor increment avoids repeated AVR division.

Support changes: `build.ps1`, `sources/hardware_host.txt`,
`test/unit/{test_peripherals,test_protection}.c`,
`test/integration/{README.md,model.c,model.h,test_app.c,test_review.c,test_timer.c,
avr_profile.c,avr_mcal_wrap.c,avr_mcal_cycles.c,profile_avr.ps1,profile_summary.py}`,
and `test/stubs/{settings_counted.c,avr/io.h,avr/interrupt.h,util/atomic.h}`.
No acceptance, common-header, settings/event/TC-core source was edited.
