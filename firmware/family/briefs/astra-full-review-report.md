**No S1 found.** I found one confirmed S2, one conditional S2 timing finding, and two S3 diagnostic defects. Files remain unchanged.

1. **S2 — First commissioning save leaves the board using the blank-board PIN and editor.**

   **Location:** [protection.c:247](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/protection.c:247), [ui.c:119](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/ui.c:119), [ui.c:84](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/ui.c:84), [ui_edit.c:4](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/ui_edit.c:4).

   **Sequence:** Boot with invalid settings and calibration. Commit valid settings containing fitted channels and a new PIN; calibration remains missing. Re-enter setup before restarting.

   G01 clears only when **both** settings and calibration are valid. The UI interprets lingering G01 as “blank,” accepts `0000` instead of the saved PIN, and initializes the editing copy with all channels OFF. The display continues directing the technician to SETUP instead of CALIBRATE. Another save can overwrite the commissioned channel configuration.

   **AVR reproduction:** Submitted the first settings through the real application commit mailbox, with PIN `1234` and 24 K channels. After completion: active PIN `1234`, G01=1, G10=1. Entering `0000` through UI key events reached `UI_NEW_PIN`; `blank=1`, editing CH1=OFF while active CH1=K. This reproduces the commit/UI integration, rather than the complete initial editing gesture sequence.

   **Spec:** `05` §5; `06` §§5.1–5.2 and §6 steps 2–4.

   **Minimal fix:** Clear G01 independently when settings become valid; retain G10 for missing calibration. Determine blank commissioning from settings validity, preserving the saved PIN and channel configuration when only calibration is missing.

2. **S2, conditional — The scan scheduler can exceed freshness limits at a loop cadence comfortably below 20 ms.**

   **Location:** [scan.c:250](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/services/scan.c:250), [scan.c:269](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/services/scan.c:269), [scan.c:94](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/services/scan.c:94). The timing coverage gap is at [avr_profile.c:50](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/test/integration/avr_profile.c:50).

   **Sequence:** Start healthy, ACK into RUN, then sustain a 6 ms main-loop cadence. CJ work, serialized bank DATA processing, and 19 end-of-scan verification passes accumulate elapsed time beyond the scan budget.

   **AVR reproduction:** Advancing the fixture clock 6 ms per real `f0_task()` invocation produced a **1254 ms scan**, G05, `scan_validated=0`, and RUN→TRIPPED. At 5 ms, the scan took 1115 ms and remained valid; at 7 ms, 1365 ms and G05. Sustained invalid scans also prevent ACK recovery.

   **Qualification:** This establishes a scheduler counterexample, **not that actual UI/Modbus traffic sustains that cadence**. The existing profiler advances simulated time by a fixed 1 ms per pass, separately from measured instruction cycles. Its 14.26 ms maximum-pass result therefore does not establish the elapsed whole-scan deadline. The architecture’s typical target is ≤5 ms; actual loaded cadence remains unresolved.

   **Spec:** `01` §2; `03` §10.2; `04` §5 rule 3 and §6.1.

   **Minimal fix:** First couple acquisition timing validation to actual execution time under maximum UI/Modbus load. If that reproduces the overrun, reduce mandatory scheduler passes through bounded batching of CJ/data/register-check work. Preserve the owner’s 1200 ms limits.

3. **S3 — ACK refusal loses its channel number and displays CH 00.**

   **Location:** [ui.c:27](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/ui.c:27), [ui_screens.c:249](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/ui_screens.c:249), [protection.c:229](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/protection.c:229).

   **Sequence:** Trip CH1 hot; request ACK while it remains hot. The UI retains R4 for three seconds but reads its channel from the per-pass protection output, which is cleared on the following pass.

   **AVR reproduction:** After refused ACK and 30 passes, the requested LCD row was exactly `R4 CH 00 HOT/FAULT`. Protection correctly remained TRIPPED, but the recovery diagnostic identified a nonexistent channel.

   **Spec:** `06` §3.4; `04` §5, R4.

   **Minimal fix:** Latch the refusal channel alongside the reason for the message’s lifetime.

4. **S3 — Temperature alarms do not update the “newest cause” view.**

   **Location:** [app_view.c:48](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/app_view.c:48).

   **Sequence:** Raise CH2 above its alarm threshold, then CH1. `app_view_cause()` filters through `fault_action()`, which returns `ACT_NONE` for the temperature cause codes C10/C11. Consequently, neither the stored cause nor newest-first ordering updates.

   **AVR reproduction:** With alarm=80°C and trip=100°C, raising CH2 then CH1 to 85°C set both alarm latches, but the view retained C02 and identified CH2 as newest. The underlying protection actions still worked.

   **Spec:** `06` §3, status priority 6: alarm count and newest cause.

   **Minimal fix:** Handle C10/C11 using the channel’s evaluated action before applying the registry-fault filter.

The remaining review found no additional unsafe RUN grant through UI commits, Modbus requests/broadcasts, service/RTU ownership, or ISR-shared state. Timer1 is free-running; the deadline ISR is Timer2.

For stack depth, UI, EEPROM commit, and Modbus execute sequentially. Production disassembly does not contain the old 1046-byte synchronous commit frame, and I found no overflow path. However, the 1536-byte stack allowance is **not a measured integrated high-water mark**.

Reproductions used the existing AVR simulator image and fake peripherals. I did not rebuild, modify files, or establish physical bench timing.