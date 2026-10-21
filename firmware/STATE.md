# Firmware - state

**Hard limit: 60 lines.** Index of all products: `docs/STATE.md`. Read `docs/ISSUES.md` in full too.
**Last updated:** 2026-10-14.

## Where it stands

* `firmware/` holds the **REV A2 8-channel** firmware (ATmega, MAX31856 front end): 4 builds and
  3 host test suites pass (2026-10-09 snapshot `production/validation-20261009-043553-906505`).
  Build: `pwsh -File firmware\build.ps1`; cloud: `make -C firmware all test`.
* **Family firmware (`0043`):** specification `firmware/spec/` rev 5, reviewed by Astra three times (reports in
  `production/review-20261015-a4/ASTRA-5..7`, local). Code goes to `firmware/family/` (the 8-ch code stays
  untouched). Status 2026-10-21 night (owner closed the session; safe stop):
  F0 + F1 done and committed up to `e2e0b28` (clean build by Claude: integration 2693646, core 125440, acceptance
  14182/14182, all pass); Astra F1 review findings fixed except **S3: AVR loop 41.75 ms worst vs 8 ms**
  (`test/integration/profile_avr.ps1`, avr-gdb simulator). Lane **F1d** (brief `briefs/lane-F1d-cpu.md`) was
  stopped mid-work; its partial edits are the WIP commit after `660d0cb` - **untested, gates not run**.
  To continue: `sh firmware/family/briefs/run_lane.sh F1d resume` (same Sol session, thread in `lane-F1d.thread`),
  then delete outputs, run the three gates + the profiler, review, commit. After F1d: short Astra re-check of
  the F1c/F1d fixes, then F2 (UI) and F3 (Modbus) in parallel (separate files). Runner: one lock per file group.
* **24-ch F0 code exists but is untested on hardware** (I-100); F0 is enough for bring-up (programming,
  service-mode readings, relay tests); F1 (protection that can grant RUN) is not done.
* Direction (`0037` D2): **one firmware for the board family** (8 / 24 / 36 ch = 1 / 3 / 5 banks of
  AD7124-8), board chosen at build time. The 8-ch REV A2 firmware becomes reference.

## What the 24-ch firmware must do (pointers, not a design)

* Scan 3 banks concurrently, trip within 1 s (~0.62 s scan, I-119); per-channel setpoints in EEPROM,
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
