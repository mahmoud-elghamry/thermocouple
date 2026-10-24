# Brief - Lane F2: operator UI module (24-ch), standalone

You are an implementer (Codex Sol). Other Sol lanes work in parallel on other files (protection fix; Modbus).
Claude reviews, integrates into the main loop and commits. Do not run git commands that write.

## Read first

`firmware/spec/00`, `01` (loop, budgets, mailbox, copy-edit-validate-commit), `04` 4-5 (states, ACK - the UI never
decides protection), `05` (settings fields, OFF encoding, type change rules, PIN), `06-ui.md` (all - this is your
spec), `10` 1-2. Public headers: `include/app/app.h` (getters + `app_commit_settings` mailbox), `include/drivers/
keys.h`, `lcd.h`, `include/services/settings.h`, `scan.h`, `fault.h`, `events.h`, `include/common/*`.

## Write ONLY

`include/app/ui.h`, `src/app/ui*.c` (screens pure where possible: state + snapshot in -> 80-char frame out),
`test/ui/` (host tests + a fake for the `app_*` getters/mailbox, keys and lcd), `test/build_ui.ps1` (copy the
compiler setup of `test/build_core.ps1`; link only what you need). **Do not edit** `main.c`, `app.c`, `build.ps1`,
`sources/*.txt`, any other existing file, or anything under `test/acceptance/`. If you need something from another
module, say so in the report; do not change it.

## Build

`ui_init()`, `ui_task(budget)`: run screens, setup menu, PIN entry, commissioning flow of `06`; edits go to a
working copy, validated with `set_validate`, committed only through `app_commit_settings` (never touch EEPROM).
Read-only use of protection/scan/fault state. Budget: <= 1 ms per `ui_task` call on the AVR (`10` 2) - no
division in hot paths, at most a few LCD characters per call (lcd_task already paces); RAM <= ~600 B.

## Tests (first)

Every screen and menu path of `06`, key gestures (short/long SET, chord, ACK is not the UI's), PIN lock/unlock and
lockout, type change clears setpoints and requires re-entry, OFF channel, invalid entry refused with message,
commit busy/fail shown, the UI never blocks a pass. Also compile `src/app/ui*.c` for the AVR with
`-Wall -Wextra -Werror` (same flags as `build.ps1`).

## Report (under 400 words)

Files, test command + counts, AVR compile result and the module's RAM, what Claude must add to `main.c`/`app.c`
to integrate (exact calls), spec gaps (file + section).
