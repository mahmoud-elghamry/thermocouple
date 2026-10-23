F2 is standalone; only the permitted UI/header/test paths changed. No commits,
source-list edits, main/app changes, or STATE updates were made.

Run from the repository root:

```powershell
powershell -File firmware/family/test/build_ui.ps1
powershell -File firmware/family/test/ui/profile_ui.ps1
python docs/check_docs.py
```

Generated evidence stays in ignored `test/ui/output/`. The timing harness links
real settings/fault logic, UI, and a mailbox fake with the alias-safe integration
below; it does not time the unmodified app shell or target LCD transport.
Verified: 695 UI checks + 586 real-driver gesture checks, zero failures; strict
AVR compilation passes. Static UI RAM is 556 B; largest individual UI stack
frame is 35 B. Maximum of 2,678 simulator samples: 6,186 cycles, 0.77325 ms
at 8 MHz. `check_docs.py`: zero findings.

Claude's integration:

1. Include `app/ui.h`; compile `src/app/ui.c`, `ui_edit.c`, `ui_format.c`,
   `ui_screens.c`. After `app_init` has bound its state, execute `ui_init();
   ui_bind_candidate(&mailbox);` **inside app.c**, where its existing mailbox is
   visible. No extra settings-sized RAM buffer is needed. UI preparation has
   exclusive access until submission; accepted input remains frozen until completion.
2. In `app_commit_settings`, retain validation/busy checks and replace its copy
   with `if(candidate != &mailbox) mailbox=*candidate;`. This also avoids overlapping
   struct-copy assumptions and keeps the measured submission budget.
3. Call `ui_task(1000)` once per normal pass after `app_step`, before the existing
   `lcd_task()`. Service remains exclusive. Forward non-ACK events from the ACK
   dispatcher using `ui_key(e.key)`; retain/retry a false return. Do not drain the
   queue again in UI. Report every ACK outcome with `ui_ack_result(reason)`.
4. Call `ui_store_result(RES_OK)` only after durable settings publication;
   report final failure with `ui_store_result(RES_ERR_READBACK)` after retries.
   Preserve transaction identity: calibration/event completions are not UI saves.
5. Capture ACK+SET at the existing 300-ms boot check. After UI initialization,
   call `ui_pin_recovery()`. Consume `ui_take_pin_reset()` in app, reset PIN
   through the owner, log PIN_RESET, retain startup latch, and report completion.
6. Feed `ui_detail_stats(min,max,cj)` for `ui_channel()` (reset extrema on accepted
   ACK); `ui_alarm_snapshot(count,code,channel,unit)` with newest cause; and satisfy
   `ui_event_request(&age)` through nonblocking owner reads followed by
   `ui_event_result(age,count,result,&event)`.

Gaps requiring integration review:

* `06` 3.2/3.3/3.4/5.3 lack public extrema/history, completion, ACK-generation,
  and recovery seams; the hooks above supply them.
* `05` 5 versus `settings_store.c` PREP_EPOCH: repeated confirmed type edits in
  one session advance epoch repeatedly; the existing owner accepts only one
  net type change. Resolve epoch/wrap semantics before integration.
* `06` 3 says status on every non-menu screen but detail/events examples replace
  that header; examples are followed. Large event PC values use the footer for
  uptime so neither field is truncated. HOLD SET on confirmation returns to editing.
