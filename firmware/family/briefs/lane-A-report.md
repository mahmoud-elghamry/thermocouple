Lane A is implemented. F0 keeps RUN in `START_LATCHED` outside confirmed service tests.

Files written under `firmware/family/`:

- Board header and `board_cfg_24.c`.
- MCAL headers/sources: GPIO, SPI, UART, timer, watchdog, EEPROM, flash CRC.
- Driver headers/sources: `iso_spi`, `ad7124`, `tmp126`, LCD, keys, relays, RS-485.
- `scan.h/c`, `service.h/c`, and F0 `main.c`.
- Register-level ADC/TMP126 and MCAL fakes; five unit-test files.
- `build.ps1` and `sources/hardware_{host,avr}.txt`.

Validation command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File firmware/family/build.ps1
```

**715 checks passed, 0 failed:** hardware 234, scan 103, peripherals 69, service 287, main 22. Host build uses MSVC `/W4 /WX` and AddressSanitizer; AVR uses `-Wall -Wextra -Werror`.

AVR size: **37,434 bytes flash plus 2-byte CRC; 6,974 bytes static RAM**, or **7,998 bytes including the 1 KB stack allowance**. CRC insertion/readback and memory-budget gates pass. [Validation log](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/build/validation.log). `python docs/check_docs.py` also passed with zero findings.

OPEN assumptions used: **A1; H3, H4, H5, H7; Q1–Q7 and Q9–Q14**, plus the unnumbered provisional diagnostic/burnout windows in `03 §4`. These cover register/filter assumptions, timing, ID whitelist, calibration, ERROR handling, MCLK checks, TMP126 configuration writes, CJ agreement and interpolation.

Spec issues for review:

- `02 §8` versus `03 §4`: recovery scope differs; implementation reinitializes the whole island.
- `02 §4.3` excludes additional ISR work, while `06 §2` requires key sampling there; implementation follows `06`.
- `02 §8 S0`: emitted initialization takes 26 cycles, exceeding the stated `<20` bound.
- `05 §6` reverses the ratio wording relative to `03 §4`; implementation uses slot 8’s internal/external ratio.
- `08 §4 A07`: confirmed channels configured OFF cannot receive the K/J-only calibration tag required by `05 §6`; saving fails without changing calibration.

No shared-header changes or git writes. STATE updates remain with Claude under the lane boundary. Bench tests were not run; `cppcheck` was unavailable.