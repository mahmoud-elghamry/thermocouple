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
The gate reserves 25% + 2048 cycles for interrupts. Its passes cover boot,
held ACK, healthy scans, a 24-channel fault burst, names/protection saves,
service, epoch wrap, LCD, UI editing, and combined commit + CJ + DATA + ACK +
Modbus garbage. All six combined evidence bits and newest-hot/C01 safety
checks must pass. Measured CPU/stack maxima and counts are in
`build/profile/summary.txt`; the full run takes about 12-15 minutes here.
This is a measured path set with conservative MCAL bounds, not an exhaustive
WCET proof for every possible input.

Timing limits remain in `include/app/timing.h`: RUN and scan deadline 1200 ms,
loop 20 ms / 160000 cycles, observed ADC RDY 36..69 ms, service relay 1000 ms.
`profile_avr.ps1 -CompileOnly` builds the simulator and calibrates MCAL quickly;
`build.ps1` always runs the complete measured-clock gate.

F7 removes serial acquisition overhead. ADC slot 0 starts before CJ work;
two checked sensors per wait pass complete the current-scan CJ records by
first DATA. Static readbacks remain in conversion waits. All 19 mutable
readbacks run in three bounded batches (7/7/5), starting after the final P5, as required by 03 sections 3.2/5.
The periodic REF pulse overlaps only slots 10-12: internal 20 mV and AVDD
nodes (03 section 3), while REFTEST pulls REF_SENSE low (02 section 10).
The >=5 ms high and >=20 ms low waits remain; external slot 13 cannot start
until recovery completes. Every required register/CJ check remains.

P15 `duration_ms` now measures publication-to-publication, including REF;
the first scan after initialization/recovery reports acquisition time because
there is no previous completion in that acquisition epoch. Tests assert exact
equality to completion timestamps. Host and soak exercise 24 scans for each
20/8/20/20, 20/1/20/1, 19/20/3 and fixed-seed random 1..20 ms pattern with REF
due. The AVR profiler repeats eight scans/pattern, lengthening each target to
its measured pass cost. All passes must stay <=20 ms, completions <=1100 ms,
and healthy RUN must remain uninterrupted. Already elapsed modeled clock time
is subtracted from padding, so simulated time is charged once.

The F1f C01 regression uses a test-only publication barrier to retain the
original ACK-before-completion interleaving after the seven verification
passes were reduced to three. Its refusal/first-out/PWM assertions are unchanged.
Cooling fixtures wait for any TC/burnout step mismatch to clear at the owning
channel's scheduled recheck (03 section 4.1), rather than relying on scan phase.

`build.ps1` writes `thermo24_f1.hex.json`: production format, board/MCU,
byte count, CRC16 and HEX SHA-256. `program.ps1`, including DryRun, validates
that metadata, the entire Intel HEX record structure/extent, and the stored
boot CRC at 0x1FFFE before any avrdude operation. It requires Python 3 (standard
library only). Programmer mocks reject profiler, legacy, unpatched, tampered,
missing-metadata, wrong-CRC and bad-record images without invoking avrdude.
Low/high fuses compare exactly; efuse uses `(value & 7) == 4` (02 section 7).

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

F8 retains a pending REF attempt when the precheck or low recovery sees G08.
Only a completed test with restored REFOK (pass or G09) updates the ten-minute
interval. Slot 10 makes at most one retry per scan. Host and AVR cases hold
REFOK high for five seconds, then require the first completion after a full
successful pulse/recovery to validate; RUN stays latched off until a fresh key
ACK. A separate held-high case must never validate. The AVR gate requires all
five sticky evidence bits and a recovery time below three seconds.

Production identity is now embedded at `APP_IDENTITY_ADDRESS` (0x1FF80),
64 bytes: eight-byte magic, board, MCU signature, three version bytes, dirty
flag, twelve-digit commit plus NUL, and reserved zero bytes. The header
`include/app/image_identity.h` owns the map. Build obtains HEAD and dirty state
using read-only git commands and checks the linked record address/size.
CRC16 covers two ordered programmed spans: code/data, followed by the identity;
unprogrammed flash holes remain excluded. Its stored word stays at 0x1FFFE.
The real boot-CRC host test changes each identity byte and checks failure,
while retaining the 128-byte step bound. Service P01 reads that same record.

Sidecars use `thermo-production-v2`, and their identity must equal the record
inside the HEX. The validator also rejects payloads smaller than the MCU's
140-byte vector table. Default programming requires embedded commit == this
repository's current HEAD; DIRTY is allowed and printed in the final PASS line.
`program.ps1 -Release <path>`, optionally with `-DryRun`, is the owner's explicit
approval of that particular release HEX plus its adjacent sidecar. It bypasses
only the HEAD comparison. Identity, board/MCU, CRC and hash checks still apply;
if `-Image` is also supplied it must resolve to the same file. Release paths,
like Image paths, are relative to the family directory unless absolute.
