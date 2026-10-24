**No S1 found. Two S2 findings remain. No files were edited.**

1. **S2 — A transient G08 at self-test entry blocks recovery for ten minutes.**

   **Location:** [scan.c:213](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/src/services/scan.c:213), with validation gated at line 110 and retry scheduling at line 239.

   **Sequence:** Healthy commissioned board in RUN; periodic REF test becomes due. REFOK reads high immediately before `ref_begin()`. The function raises G08, clears `diag.ref_test_ok`, updates `last_ref`, and skips the test. Restore REFOK low. Subsequent healthy scans cannot validate because `ref_test_ok` remains false; another test cannot start until 600000 ms elapses.

   **AVR reproduction:** At 13380 ms, G08 stopped RUN. At 18380 ms, with REFOK restored, all three banks were `BANK_VALIDATED`, but board validation remained false, RUN remained off, and the next test was **595000 ms away**. G08 was the first cause. ACK cannot recover without a validated scan.

   **Spec:** `02` §10 distinguishes a failed precheck—“no self-test on a broken wire”—from G09; `03` §11 permits G08 clearance on restored REFOK in a validated scan; `02` §8 requires automatic acquisition recovery followed by ACK.

   **Minimal fix:** Track an unsuccessful/pending REF attempt separately from the successful-test interval. Retry at the next safe slot-10 opportunity after REFOK recovers, preserving the required pulse/recovery checks and ACK latch.

2. **S2 — Image consistency is checked, but production identity and freshness are still not established.**

   **Location:** [image_metadata.py:59](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/image_metadata.py:59), verification at line 67; [program.ps1:40](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/program.ps1:40), programming/PASS at lines 63–66.

   **Sequence:** Select the existing `build/program_test/fixture.hex`. Its payload is merely bytes 0–63, with a matching CRC and sidecar asserting board 24. The real validator accepted it:

   `Production image PASS: board 24, 64 bytes, CRC16 FD2F, SHA-256 verified`

   If avrdude successfully writes and verifies those bytes, the script reaches `PROGRAM PASS`. No metadata tampering is needed for this example. Likewise, an old production HEX **together with its matching sidecar** passes: neither file is compared against an expected release or current source/build identity.

   **Spec:** `00` Targets; `02` §§7–8 require the target application and its startup protections; `01` §6 requires protection against bad programming. This leaves the earlier wrong-image finding only partially closed.

   **Minimal fix:** Check the selected image against an independently selected production-build manifest containing the expected image hash and source/build identity. Require either the current build or an explicitly selected approved release.

   **Evidence boundary:** Validator execution plus static programming-path tracing; no hardware programming attempted.

The scheduler changes otherwise held up. I found no omitted per-scan check or stale-data acceptance in the reviewed paths: CJ completion gates DATA consumption; immutable verification resets each scan; all 19 mutable checks follow final P5; captured slot/error evidence survives starting the next conversion. Injected G09, slot-10 ADC conversion error, and CRC failure during the REF window all produced **invalid scans with RUN off**.

Additional measured-cost AVR cadence runs, with ADC readiness at 49 ms and REF exercised, produced:

| Cadence, ms | Maximum completion gap |
|---|---:|
| 20/20/8/20 | 1036 ms |
| 20/20/9 | 793 ms |
| 17/11/20 | 921 ms |
| 20/7/1/20 | 928 ms |
| 19/9/20/1 | 875 ms |
| 20/20/20/1/7 | 915 ms |
| Adaptive polling near 48 ms, then 20 ms | 1067 ms |

All 28 completions validated and healthy RUN remained uninterrupted. No interval exceeded 20 ms after measured-cost adjustment. This supports the timing fix; it is not an exhaustive cadence proof.

The efuse mask finding is closed. The earlier G01/configuration, ACK-refusal-channel, and C10/C11 ordering fixes remain present in their application paths.