**Found two S1 defects and three S2 defects.** This was a read-only source and existing AVR-disassembly review. The deterministic AVR lockout in finding 3 can mask the normal-RUN defects until fixed.

1. **S1 — Timer2 expiry can be overwritten without ACK.**  
   **Locations:** [timer.c:27](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/mcal/timer.c:27), [protection.c:224](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/protection.c:224), [relays.c:17](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/drivers/relays.c:17).  
   **Trigger:** While RUN is active, a validated completion enters protection just before the old window expires. `in.now_ms` records that earlier time. Timer2 then expires during decision/output processing and stops PWM. Protection still uses the frozen timestamp, grants a new 900 ms window, and `outputs_hw_apply()` restarts PWM because the remaining time increased. The ISR leaves no sticky expiry indication; the new software timestamp also prevents subsequent G05 detection. A short interruption may not even release the physical relay.  
   **Spec:** `04 §6.1`: expiry itself must latch TRIPPED/G05; later scans cannot reclose without ACK. `02 §4.2`: ISR-owned deadline.  
   **Minimal fix:** Latch expiry in the ISR. Atomically check that latch when granting/reloading a window; propagate G05 and require ACK before allowing another start. Recheck elapsed time at the hardware handoff.

2. **S1 — Pressing SET does not abort an active RUN relay test.**  
   **Location:** [service.c:253](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/service.c:253).  
   **Trigger:** Enter SERVICE using SET, confirm A03, then press and hold SET again while RUN is energised. Abort checks only `keys_get()` events. The key driver emits SET **on release**, so RUN remains energised until release or the one-second deadline, despite the abort key being pressed.  
   **Spec:** `08 §1` and `04 §4`: the service RUN exception stops on any key.  
   **Minimal fix:** During active relay tests, stop immediately on any newly debounced held key, independently of UI gesture/release events.

3. **S2 — Healthy AVR execution deterministically raises G04 and prevents recovery.**  
   **Locations:** [protection.c:87](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/protection.c:87), [protection.c:52](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/protection.c:52), [main.c:164](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/main.c:164).  
   **Trigger:** Boot with valid settings/calibration and no active faults. Every protection pass searches 27 trip-action codes across 96 units: **2,592 `fault_at()` calls**. In the existing `-Os` ELF, their call/return and register-save overhead alone is **93,312 cycles = 11.664 ms at 8 MHz**, excluding actual lookup work. Therefore the `>8 ms` guard raises G04. Nothing clears that active G04; ACK refuses it. Reset repeats the same failure. Instruction costs were checked against the [Microchip instruction manual](https://ww1.microchip.com/downloads/en/DeviceDoc/AVR-InstructionSet-Manual-DS40002198.pdf).

   Independently, scan completion calls whole-record `set_validate()` once per channel. With 24 fitted K channels, selected compulsory instructions alone exceed **9.36 ms**, even after fixing the fault search. The host model accounts for I/O time, not these CPU costs.  
   **Spec:** `01 §2`: worst loop ≤8 ms; `04 §5`: healthy, clear protection must permit ACK.  
   **Minimal fix:** Search fault bitmaps by byte and inspect units only in nonzero bytes. Validate settings and rebuild the fitted mask once per pass, not per result. Verify complete AVR execution paths against the budget.

4. **S2 — A qualifying ACK can be consumed and rejected because its press is timestamped twice.**  
   **Location:** [ack_input.c:10](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/ack_input.c:10).  
   **Trigger:** `keys_task()` records the debounced press at 100 ms; a Timer2 tick occurs before `ack_input_step()`, which records it at 101 ms. At 150 ms the driver emits its valid 50 ms ACK, but the adapter calculates 49 ms. Protection rejects R1 after the event has been consumed. Holding longer cannot help because the driver has marked ACK delivered; another release/press is required.  
   **Spec:** `04 §5`, rule 2: a fresh press held ≥50 ms qualifies.  
   **Minimal fix:** Carry the driver’s press/event timestamps through the queue; use one authoritative duration and event age.

5. **S2 — ACK can silence a currently active alarm using older cool evidence.**  
   **Locations:** [app.c:177](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/app.c:177), [protection.c:108](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/protection.c:108).  
   **Trigger:** In RUN, completed scan N is cool. Early in scan N+1, an ALARM ONLY channel crosses its alarm threshold; immediate evaluation sets its alarm latch. Before N+1 completes, a fresh ACK uses `scan_last()`—scan N—and clears that latch. Subsequent passes also consult N, so ALARM can indicate healthy until N+1 completes although the latest channel result remains hot.  
   **Spec:** `04 §§3.3, 7.2`: active causes remain alarmed; ACK clears only causes proven clear.  
   **Minimal fix:** Track the latest per-channel condition/reset eligibility and use it for alarm clearance. Older completed-scan data must not override newer slot evidence.

The queued removal of `service_entry |= !set_valid` is confirmed necessary under `08 §1`. No files were edited.