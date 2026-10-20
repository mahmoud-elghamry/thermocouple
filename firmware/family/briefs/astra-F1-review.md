# Astra review - F1 protection code of the 24-ch family firmware (read-only)

You are the reviewer (read-only). The firmware decides whether a diesel engine may run: an energised-to-run relay
(RUN) is closed only while protection is satisfied; a fault, reset or hang must open it. The code was written by
Codex Sol in lanes, re-tested by Claude (all host suites pass: core 125435 checks, independent acceptance 14182,
integration 2.69 M checks on register-level fakes). Tests passing is not your question. Your question is: **where
can this code close or keep RUN closed when the spec says it must be open, or lock the machine out when the spec
says it must recover?** Second: real defects on an ATmega1284P (8 MHz, avr-gcc -Os) that host tests cannot see -
ISR/main-loop races, non-atomic 16/32-bit shared variables, stack depth, watchdog/flow-check holes, EEPROM timing.

## Spec (normative)

`firmware/spec/01-architecture.md`, `02-hardware-interface.md` (4.2 Timer2 deadline, 5 WDT, 8 boot), `03-acquisition.md`
sections 10-11, `04-protection.md` (all), `05-settings-events.md` (all), `08-service-mode.md` 1-2 and the relay tests,
`docs/GOAL.md` (trip within 2 s).

## Code to review (under `firmware/family/`)

`src/app/{protection,channel_eval,outputs,outputs_shell,app,ack_input,ee_owner,main,service}.c`,
`src/services/{fault,settings,settings_store,settings_cal,events,scan}.c`, `src/drivers/relays.c`,
`src/mcal/{timer,wdt,eeprom,gpio}.c`, their headers, `include/common/*`. Tests only to check a claim.

## Known and decided (do not re-report)

* `main.c` still enters SERVICE automatically on invalid settings (`service_entry|=!set_valid`); the spec was
  just changed (`08` 1: only SET at power-up, invalid -> CONFIG_LOCK). Confirm the fix is needed; it is queued.
* RAM budget 12 KB incl. 1.5 KB stack; F2 (UI) and F3 (Modbus) are not written yet.

## Report

Write your findings as your final message. For each: severity (**S1** RUN can be closed/kept closed wrongly, or
the trip can be later than 2 s; **S2** lockout or lost protection function without unsafe RUN; **S3** robustness /
spec mismatch; **S4** style), file:line, the concrete sequence of inputs that triggers it, the spec clause, and a
minimal fix. Say plainly if you found no S1. Under 1200 words. Do not edit files.
