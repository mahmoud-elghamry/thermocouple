**No S1 found. Two S2 findings and one S3 remain. No files were edited.**

1. **S2 — Healthy acquisition can still expire RUN under permitted loop jitter.**

   **Location:** [scan.c:268](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/services/scan.c:268), final verification at line 301, and REF scheduling at line 252.

   **Sequence:** Healthy, commissioned board; ADC readiness set to the profiler’s worst-case 49 ms; ACK into RUN. Apply loop intervals targeting 20/8/20/20 ms, increasing each interval when necessary to accommodate its measured execution cost. Make the periodic REF test due.

   **AVR reproduction:** Using the existing simulator image and profiler accounting—including MCAL bounds and reserve—all intervals remained **≤20 ms**. The gap between validated scans reached **1230 ms** across the REF test. RUN stopped and latched **G05**, although the eventual scan validated and reported only **1170 ms**. A later ordinary gap reached **1210 ms**, with reported scan duration **1190 ms**.

   Polling alignment and the separate CJ/final-verification passes consume the remaining margin. Starting `duration_ms` after REF testing also hides time that matters to the RUN window.

   **Spec:** `01` §2; `03` §10.2; `04` §6.1.

   **Minimal fix:** Reduce mandatory acquisition overhead enough to bound the **complete-to-complete interval**, including REF testing and variable polling alignment, below 1200 ms. Add a measured-cost jitter regression asserting uninterrupted healthy RUN; retain the existing safety deadline.

   This is a demonstrated scheduler counterexample under allowed cadence, **not evidence that current UI/Modbus traffic produces that exact cadence on hardware**.

2. **S2 — Programming verification does not establish that the selected image is production firmware.**

   **Location:** [program.ps1:39](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/program.ps1:39), programming and PASS at lines 60–63.

   **Sequence:** Select an existing simulator/test ELF, such as `build/profile/profile.elf`, through `-Image`. The script checks existence and extension only. If avrdude successfully writes and verifies those bytes, the script prints `PROGRAM PASS`.

   `-p m1284p` checks the connected MCU; it does not establish the firmware’s board identity, production provenance, or valid boot CRC. Successful byte-for-byte verification can therefore accompany programming the wrong application.

   **Spec:** `00` Targets; `02` §§7–8; `01` §6.

   **Minimal fix:** Validate production-image identity and the patched image CRC before changing fuses or flash, using build-generated metadata tied to the selected artifact. Reject simulator, legacy and unpatched images.

   **Evidence:** Static control-flow finding. No hardware programming was attempted; the dry-run attempt was blocked by the environment’s PowerShell language-mode restriction.

3. **S3 — Valid masked efuse readback is rejected.**

   **Location:** [program.ps1:55](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/program.ps1:55).

   **Sequence:** An avrdude version returns `0x04` for extended fuses, masking unused bits. The script requires exactly `0xFC`, reports failure and stops before flashing, despite the required BOD configuration being correct.

   **Spec:** `02` §7 explicitly permits this readback representation.

   **Minimal fix:** Compare `(efuse & 0x07) == 0x04`; retain exact comparisons for low and high fuses.

The other three original findings are fixed in their application paths: G01 clears independently of G10 and setup preserves the saved PIN/configuration; ACK refusal retains its channel; C10/C11 now update cause ordering. The scheduler finding is only partially resolved. Capturing the completed slot, driver fault and bank validity before starting the next conversion correctly preserves the old result’s fault evidence.

At **fixed 20 ms cadence**, my simulator check passed the periodic REF cycle: **1120 ms acquisition, 1180 ms between completions**. That is not a worst-case bound. The checked-in AVR cadence test measures three scans at each fixed cadence without triggering periodic REF; the soak exercises REF at nominal 20 ms but does not cover the jitter counterexample above.

I found no additional defect in the reviewed timestamp-wrap logic, 24-only settings/store validation, Modbus bounds, or SPI selection. Production disassembly confirms 32 SBI/CBI GPIO cases and stack painting after early initialization and data/BSS initialization. Fuse values F7/C1/FC match §6, and EESAVE is written and checked before the flash operation’s chip erase.