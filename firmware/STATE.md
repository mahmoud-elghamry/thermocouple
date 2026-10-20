# Firmware - state

**Hard limit: 60 lines.** Index of all products: `docs/STATE.md`. Read `docs/ISSUES.md` in full too.
**Last updated:** 2026-10-14.

## Where it stands

* `firmware/` holds the **REV A2 8-channel** firmware (ATmega, MAX31856 front end): 4 builds and
  3 host test suites pass (2026-10-09 snapshot `production/validation-20261009-043553-906505`).
  Build: `pwsh -File firmware\build.ps1`; cloud: `make -C firmware all test`.
* **Family firmware (`0043`):** specification `firmware/spec/` rev 5, reviewed by Astra three times (reports in
  `production/review-20261015-a4/ASTRA-5..7`, local). Code goes to `firmware/family/` (the 8-ch code stays
  untouched). F0 = 24-ch only, implemented by Codex Sol in two parallel lanes (hardware path / pure core),
  briefs in `firmware/family/briefs/`; Claude reviews, runs the host tests and commits on branch `24ch-rev-a4`.
  Any session can continue from the briefs + this line + `docs/TOOLS.md` "Codex roles".
* **The 24-ch firmware is not written** (I-100). It is the main blocker: without it the 24-ch board
  cannot be tested beyond its supply rails (ASSEMBLY-SPEC power-on test).
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
