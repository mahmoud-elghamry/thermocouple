# Firmware - state

**Hard limit: 60 lines.** Index of all products: `docs/STATE.md`. Read `docs/ISSUES.md` in full too.
**Last updated:** 2026-10-23.

## Where it stands

* `firmware/` holds the **REV A2 8-channel** firmware (ATmega, MAX31856 front end): 4 builds and
  3 host test suites pass (2026-10-09 snapshot `production/validation-20261009-043553-906505`).
  Moved to `firmware/8ch-legacy/` 2026-10-23 (owner); build `pwsh -File firmware\8ch-legacy\build.ps1`.
* **Family firmware (`0043`):** spec `firmware/spec/`, code `firmware/family/` by Codex Sol lanes (briefs, reports
  and runner `family/briefs/run_lane.sh`; roles `docs/TOOLS.md`). F0, F1 protection, F2 UI, F3 Modbus integrated (F4).
  **F5** fixed Astra's full review (G01 after first save, scan vs loop cadence, ACK refusal channel, C10/C11 cause
  order, stack high-water); verified by Claude on a clean build 2026-10-23: core 125509/0, acceptance 14270/14270,
  integration 2762469 + F4 1378251, UI 702/586, Modbus 1527729, AVR worst 19.74/20 ms, measured scans
  854/891/1120 ms at 5/10/20 ms cadence (limit 1200), stack 562/1536 B, flash 73430 B, RAM 13783/14336 B.
  **Uncommitted** (owner asleep; commits wait for him). `build.ps1` takes ~12 min (AVR profiler).
* **Scope 2026-10-23 (`0043` 9): 24-ch only.** **F6** removed 40-ch/PT100/decoder code (RAM 12247 -> 9786 B static,
  11322/14336 B with stack), added a cppcheck 2.22 gate (0 findings), `family/program.ps1` (USBasp, fuses F7/C1/FC
  written then read back, flash verify, `-DryRun`; default image the CRC-patched `build/thermo24_f1.hex`), the
  `.init` order gate and a 60-day soak (`test/integration/soak.ps1`, ~10 min) that found and fixed a RUN-window
  expiry at the 10-min REF self-test and event timestamps going backward at the ms wrap. **C4** made acceptance
  24-only. Claude re-ran all on a clean build: core 125511/0, acceptance 14361/14361, build.ps1 PASS (818 s), AVR
  worst 19.857/20 ms, stack 528/1536 B, soak PASS. **Astra F5/F6 re-check:** no S1; gap between validated scans
  reached 1230 ms under allowed loop jitter (I-124), programming image/efuse checks. **F7** (limits unchanged) overlaps
  the REF test with slots 10-12 and batches end-of-scan checks: AVR gaps 1035/954/863/906 ms under jitter, worst
  pass 19.586/20 ms, stack 539/1536 B, RAM 11328/14336 B, flash 73636 B; `program.ps1` checks image identity, SHA-256
  and boot CRC (41 mock checks). Astra F7 re-check: no S1; REF lockout after a transient G08 and image identity -> **F8**: REF retry stays pending,
  firmware identity record at 0x1FF80 (git HEAD, CRC-covered; `program.ps1` refuses stale/foreign images). Claude ran
  F8's gates (Codex hit its usage limit until 2026-10-29): all PASS, AVR worst 19.471 ms, jitter gaps <= 1047 ms,
  stack 579/1536 B, RAM 11335/14336 B, flash 74086 B, soak PASS. Independent Claude review of F8: no S1/S2. Open S3 (owner
  to choose): G09 retests only after 10 min (fail-safe, slower recovery); a DIRTY build programs without `-Release`;
  freshness uses repo-wide HEAD/status (any docs commit marks an image stale).
* **24-ch code is untested on hardware** (I-100): host and AVR-simulator evidence only.

## What the 24-ch firmware must do (pointers, not a design)

* Scan 3 banks concurrently, trip within 2 s like Murphy (GOAL; ~0.75 s normal, ~1.1 s worst); per-channel setpoints in EEPROM,
  latch + manual ACK (`0029`); open sensor trips by default, alarm-only is a saved per-channel
  setting (`0034` D1); relay held by a heartbeat from completed scans (I-118); internal watchdog
  (WDTON fuse, `fuses.md`).
* AD7124 diagnostics every scan (CRC, ID, error register) and burnout/open check one channel per scan
  (`0031` D2).
* TMP126 cold junction (`0036` D1): one CS low at a time, >= 1 us between CS edges, writes <= ~40 kHz
  (CALCULATIONS 8.3), CRC + device ID 0x2126 on every read; no AD7124 continuous-read mode.
* Open firmware issues: I-100, I-104, I-118, I-119, I-097; RS-485/Modbus hardware is fitted (owner
  2026-10-14), protocol later (I-086, I-094).
* The simulation demo (`simulation/`, Proteus) is done in this branch once the firmware runs: MCU, LCD,
  buttons, relays with simulated temperatures (Proteus has no AD7124/TMP126 model).
* To study: thermocouple type per channel (K / J), `0037` D2.

## Preserve

* **Images are not interchangeable**: the 8-ch image drives the run output HIGH only while safe to
  run; legacy single-channel images drive it HIGH on over-temperature. `program.ps1` warns.
