# F6/F7 accelerated soak

Run `powershell -File firmware/family/test/integration/soak.ps1` for 60 days.
The standalone gate takes about ten minutes; `build.ps1` runs its short rollover
case and a 15-minute smoke case, including the periodic reference self-test.
Use `-Days 1`, `-Minutes 60`, `-WrapTest`, or `-ClockTest` for focused iteration.
The script builds the real integrated firmware with the register-level fakes,
MSVC `/O2 /GL /W4 /WX`, and a fixed seed, `24F60001`.

F7 first exercises 24 scans for each jitter pattern (20/8/20/20, 20/1/20/1,
19/20/3, seeded random 1..20 ms) with ADC RDY at 49 ms and REF due. Every
completion must validate within 1100 ms of its predecessor, P15 must equal
that gap, and RUN must stay on. The remaining firmware passes use a nominal
20-ms cadence; UART arrivals and power-cut
injection also advance simulated time. No passes, scans,
protection decisions, UI tasks, Modbus tasks, or EEPROM owner steps are skipped.
Only identical settled timer/key ISR ticks are combined in the host model.
Eight individual samples follow each input change; timer expiry and watchdog
expiry retain their original order. A reference test compares individual and
combined ticks. The host clock is internally 64-bit; firmware time interfaces
retain their real 32-bit wrapping epochs.

All 24 channels are fitted. Explicit test-only limits are 80/100 C and a 200 C
probe rating. Seeded scenarios exercise temperature steps, island faults,
physical ACK holds, valid Modbus reads and garbage floods, actual UI edit/save
flows, event queue bursts, and power cuts inside settings and event writes.
Settings after a cut must equal the complete old or new record. Cuts are
randomized in the first and last three days, preserving a continuous middle
interval long enough to cross the natural 49.7-day millisecond wrap.
The short rollover case also starts a boot near wrap without rebasing live
firmware state. Hot evidence refuses ACK across wrap; a subsequent cool scan
and fresh ACK restore RUN. First-out timestamps must remain monotonic.

At least once per simulated minute the harness checks owner indices, queue
and transfer bounds, fault integrity, UART occupancy and the stack API bound.
After each scenario it also checks validated scan timing, event ring entries,
settings validity and safe outputs. Loop I/O time and watchdog health are
checked on every pass. Actual AVR CPU cycles and painted stack high-water are
measured separately by the mandatory AVR profiler; the host stack API is a stub.

The event u24 **seconds** field wraps at 194 days, not within 60 days (`05` 7).
Explicit fixtures cover `0xfffffe` through `0x1000001`, including persistence
through the real EEPROM owner, independently of the natural millisecond wrap.

The soak exposed two integration defects: a periodic reference test could
expire RUN at 20-ms cadence, and event/first-out timestamps divided the raw
millisecond tick, resetting at 49.7 days. Regression cases retain both triggers.
