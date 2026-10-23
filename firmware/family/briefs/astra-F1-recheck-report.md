**All five original findings are fixed, but I found one new S1 regression. No additional S2 found.** Reviewed clean HEAD `233f0f1`, production AVR disassembly, and existing reports; reproduced the regression in the existing AVR simulator image. No files edited.

**New S1 — ACK can re-arm RUN while a newer channel result is still over-trip.**

Locations: [protection.c:190](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/protection.c:190), [app.c:232](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/app.c:232), [protection.c:257](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/protection.c:257).

Trigger:

1. Validated scan N is cool; RUN is energised.
2. Early in N+1, a TRIP-mode channel becomes hot. Immediate evaluation correctly trips RUN.
3. After relay release, a fresh ACK arrives before N+1 completes. ACK checks N’s cached `completed_clear`, ignoring the newer hot result, and enters RUN.
4. N+1 completes validated. `results_evaluated` suppresses channel re-evaluation, so nothing reasserts the trip. [protection.c:290](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/protection.c:290) opens the RUN window.

**Reproduced with AVR instructions and simulated MCAL:** CH1 changed from 25.0°C to 143.7°C, trip setting 100.0°C. Observed `TRIPPED/PWM=0`, then accepted ACK, then validated hot scan 6 with `RUN/PWM=1`, remaining deadline **1199 ms**.

**Spec:** `04 §3.3`, `§5 rule 5`, and `§6.1`: channels must be clear before ACK; window renewal requires no trip action.

**Minimal fix:** newer per-channel evidence must veto ACK despite a cool completed-scan cache. Also preserve/recheck current trip conditions before granting a window when completion re-evaluation is skipped. Add this exact interleaving as a regression test.

The five original findings:

| Finding | Verdict and AVR evidence |
|---|---|
| **1. S1: expiry overwritten without ACK** | **Fixed.** [timer.c:23](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/mcal/timer.c:23) atomically checks sticky expiry and subtracts elapsed handoff time; the ISR sets expiry at line 43. [relays.c:14](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/drivers/relays.c:14) refuses restart; [app.c:254](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/app.c:254) observes expiry around hardware application. Production disassembly confirms interrupt exclusion. |
| **2. S1: SET press fails to abort service RUN test** | **Fixed.** [service.c:222](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/service.c:222) stops relays on debounced press edges before UART-busy or gesture handling. [keys.c:46](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/drivers/keys.c:46) produces those edges from ISR-maintained key state. No release is required. |
| **3. S2: deterministic AVR CPU lockout** | **Fixed for the reviewed paths and revised budget.** [fault.c:62](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/services/fault.c:62) searches bytes; [protection.c:32](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/protection.c:32) prepares validation once per pass. [main.c:164](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/main.c:164) uses 20 ms. Existing [profiler report](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/build/profile/summary.txt) records 12.752 ms including MCAL bounds/reserve; this is simulator evidence, not a silicon measurement. |
| **4. S2: ACK timestamped twice** | **Fixed.** [keys.c:63](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/drivers/keys.c:63) queues authoritative press/event timestamps; [ack_input.c:13](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/ack_input.c:13) derives duration from them. Both are production AVR paths. |
| **5. S2: ACK silences an active alarm using old cool evidence** | **Fixed for alarm clearance.** [protection.c:79](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/protection.c:79) records latest result/reset eligibility; [protection.c:136](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/protection.c:136) prioritises that evidence. The analogous **trip-ACK** defect above remains. |

**Split settings commit — passes the reviewed power-cut/reset sequencing.** Preparation emits no EEPROM operations ([settings_store.c:213](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/services/settings_store.c:213)). The inactive slot is invalidated, body/CRC written, magic completed last, then every byte compared before RAM publication ([settings_store.c:215](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/services/settings_store.c:215), [ee_owner.c:97](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/app/ee_owner.c:97)). Boot checks magic, CRC and semantics in [settings.c:100](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/services/settings.c:100). Protection changes inhibit RUN from transaction start; ACK rejects `writing` at `protection.c:205`. Epoch-wrap clearing precedes settings commit: a cut may intentionally leave **old settings plus cleared calibration**, requiring relearning, as `05 §6` permits; no mixed settings record or half-prepared RUN grant found.

**CJ scheduling/soft SPI — passes source and instruction review.** [scan.c:177](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/services/scan.c:177) advances one register frame per pass; ADC ready timestamps remain checked while DATA waits. [tmp126.c:56](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/drivers/tmp126.c:56) requires all five checks before accepting temperature. [spi.c:13](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/mcal/spi.c:13) meets [TMP126 §7.6](https://www.ti.com/lit/ds/symlink/tmp126.pdf) digital timing; production SBI/CBI instructions preserve PB3. `tmp126.c:23` and `iso_spi.c:22` release `SIO_WR_N` after command hold, before read clocks; writes retain drive through data/CRC, matching `02 §2.4`.

**Timing constants — consistent:** RUN/freshness 1200 ms, loop 20 ms, RDY 36–69 ms; service remains separately 1000 ms. Existing timer/preparation executables reran: **16/284 checks passed**; documentation check: **0 findings**.