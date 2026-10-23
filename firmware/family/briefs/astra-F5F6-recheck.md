# Astra - re-check of F5 and F6 (read-only)

Your full review (`astra-full-review-report.md`) found no S1, two S2 and two S3. Lane F5 fixed them
(`lane-F5-report.md`), lane F6 then trimmed the firmware to the 24-ch board only (owner 2026-10-23,
`firmware/spec/00-overview.md` Targets, `docs/decisions/0043` 9), added a cppcheck gate, `program.ps1`, a 60-day
simulated soak and fixed two things the soak found (`lane-F6-report.md`). Both are uncommitted in the working tree
on top of commit `22e5a80`; `git diff` shows them. Claude re-ran every gate on a clean build: all PASS, AVR worst
pass 19.857/20 ms incl. reserve, measured scans 859/882/1120 ms at 5/10/20 ms cadence (limit 1200), stack
528/1536 B, RAM 11322/14336 B, 60-day soak 265363192 checks PASS.

Same question as always: **where can this firmware close or keep RUN closed when the spec says it must be open,
or lock the machine out when it must recover.** Check in particular:

1. Each of your four findings is really fixed, not just its test (G01/G10 split and the UI's blank/PIN path;
   scan scheduling in `scan.c` - results are now processed after the next slot is started, with the fault cause
   and bank validity captured before; ACK refusal channel; C10/C11 cause order).
2. The new code: `scan.c` (batched POLL_SLOT, CJ frames per pass, REF self-test chained into BEGIN_SCAN with
   `goto`), `gpio.c` (switch-based SBI/CBI), `stack_monitor.c` (paint in `.init5`), `app_uptime_s()` and the event
   timestamps across the 32-bit ms wrap, the 24-only validation in `settings.c` and `settings_store.c`,
   `modbus_map.c` bounds, `iso_spi.c` select.
3. The REF self-test every 10 min at a 20 ms loop cadence: does a scan that contains it still validate inside
   1200 ms in the worst case, and is that case actually measured?
4. `program.ps1`: fuse values against `02` 6, read-back, EESAVE before the chip erase, anything that can leave a
   board programmed with the wrong image or fuses while printing PASS.

Spec: `firmware/spec/` (all). Code: `firmware/family/src`, `include`, `program.ps1`; tests only to check a claim.
Report (under 1000 words): severity S1/S2/S3, file:line, input sequence, spec clause, minimal fix. Reproduce
S1/S2 on the AVR simulator image if you can. Say plainly if there is no S1. Do not edit files.
