# Brief - Lane F4: integrate UI (F2) and Modbus (F3) into the 24-ch firmware

You are the implementer (Codex Sol), continuing your F1 session, and the **only** writer in `firmware/family/` for
this run. F1 (protection) is done and green; F2 (`src/app/ui*.c`) and F3 (`src/app/modbus*.c`) were written as
standalone modules by other lanes and pass their own suites. Claude reviews and commits. No git writes.

## Read first

`firmware/family/test/ui/HANDOFF.md`, `firmware/family/test/modbus/README.md`, `briefs/lane-F2-report.md`,
`briefs/lane-F3-report.md`; spec `06`, `07`, `01` 2 (loop, budgets), `05` 5 (type epoch now set **once per commit
against the active record** - changed today), `10` 2 (RAM now <= 14 KB incl. 1.5 KB stack).

## Do

1. Main loop: call order per the two handoffs (`ui_task` after `app_step`; `mb_task` after protection/outputs and
   before EEPROM; non-ACK key events to `ui_key`; store results to `ui_store_result`; the mailbox binding).
   Service mode keeps the RS-485 port for its text report; Modbus only outside SERVICE.
2. The Modbus driver interface `mb_io_*` on the real UART/RS-485 (8N2, binary TX by UDRE, DE held until the final
   TXC, RX timestamps per `07`/`02` 4.4). Extend `uart.c`/`rs485.c` and their fakes as needed, keeping
   `rs485_line` for service.
3. Connect the hooks both handoffs list (recovery, event history, extrema, newest alarm, ACK result, feedback /
   metadata / trip-latch getters for Modbus).
4. Type epoch: make the UI and `settings_store` agree with `05` 5 as changed today (epoch from the active record at
   commit; repeated edits in one session are one change). Keep every power-cut guarantee.
5. `build.ps1`: run the UI and Modbus suites too (one command runs everything); RAM gate 14336 B incl. stack; the
   AVR profiler includes `ui_task` and `mb_task` in its passes (Modbus flood + UI menu + commit + CJ + slot + ACK in
   one pass as the combined case); gate stays 160000 cycles.
6. Integration tests end to end: commission a blank board through the keys (settings entered, saved, CONFIG_LOCK ->
   START_LATCHED -> ACK -> RUN), a Modbus read of live values and of the first-out after a trip, a garbage flood on
   RS-485 during a trip (trip timing unchanged), UI save during RUN (names-only keeps RUN; protection change goes
   to START_LATCHED).

## Rules

You may edit any file in `firmware/family/` **except** `test/acceptance/`, `test/build_acceptance.ps1`,
`include/common/*`; do not weaken any existing assertion (if one must change because the spec changed, cite the
clause). No dynamic memory, no floats, bounded loops, modules <= ~400 lines.

## Done means

Delete every `output`/`build` directory first; then `build.ps1` (incl. UI, Modbus, profiler), `test/build_core.ps1`,
`test/build_acceptance.ps1` all exit 0. Report under 500 words: files changed, counts copied from the output, AVR
flash/RAM, profiler worst pass, spec gaps.
