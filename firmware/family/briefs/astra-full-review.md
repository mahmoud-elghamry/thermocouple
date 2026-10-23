# Astra - full review of the 24-ch firmware before bench (read-only)

You reviewed F1 twice (`astra-F1-review-report.md`, `astra-F1-recheck-report.md`); both rounds are fixed (F1c, F1f).
Since then the UI (F2) and Modbus (F3) were written as standalone modules and integrated into the main loop (F4,
commit `f9b5a4f`). All host suites, the independent acceptance suite and the avr-gdb cycle profiler pass (worst
pass 14.26 ms of the 20 ms budget; flash 72.9 KB of 96 KB; RAM 13.8 KB of 14 KB incl. stack). Owner timing limits
(2026-10-23, like Murphy): RUN window and scan freshness 1200 ms, trip within 2 s.

Question, as before: **where can this firmware close or keep RUN closed when the spec says it must be open, or
lock the machine out when it must recover** - now including everything the UI and Modbus can do: a UI save during
RUN, PIN/menu paths, commissioning from a blank board, Modbus traffic (valid, garbage, flood, broadcast) during a
trip, RS-485 shared between service text and Modbus, the new UART/Timer1 ISRs and their shared variables, the
F4 view hooks (extrema, event history, trip latch), stack depth with the deepest UI + commit + Modbus frames.

Spec: `firmware/spec/` (all; `06` UI, `07` Modbus are new to you). Code: everything under `firmware/family/src`
and `include`; `src/app/main.c`, `app.c`, `app_view.c`, `ui*.c`, `modbus*.c`, `mb_io.c`, `src/mcal/uart.c`,
`timer.c` first. Tests only to check a claim.

Report (under 1200 words): severity S1/S2/S3 as before, file:line, the input sequence, spec clause, minimal fix.
Reproduce S1/S2 on the AVR simulator image if you can (`test/integration/profile_avr.ps1` builds it). Say plainly if
there is no S1. Do not edit files.
