Implemented F1; left uncommitted for Claude’s review.

Files changed under `firmware/family/`:

- `src/app/{main,app,ack_input,ee_owner}.c`
- `include/app/{app,ack_input,ee_owner,stack_budget,service}.h`
- `sources/hardware_{avr,host}.txt`, `build.ps1`
- `test/integration/{test_app.c,model.c,model.h,README.md}`
- Permitted exception `scan.c`: ignore OFF-channel burnout baselines and normalize C03 to channel units.
- Permitted exception `service.c`: serialize calibration/scratch writes through the EEPROM owner, handle OFF calibration tags, and refresh committed settings validity.

All three gates exited **0** after deleting generated outputs:

| Gate | Output counts |
|---|---|
| `build.ps1` | hardware 234; scan 103; peripherals 69; service 287; integration **2607351 checks PASS** |
| `test/build_core.ps1` | **125435 checks, 0 failures**; S01–S28 PASS |
| `test/build_acceptance.ps1` | **checks=14182 passed=14182 failed=0** |

AVR: **51,876 bytes flash + 2-byte CRC**; **10,009 bytes static RAM**, **11,545 bytes including the 1,536-byte stack reservation**. The commit frame measures 1,046 bytes; its build gate includes 384 bytes of caller/interrupt margin.

Simulated timing:

- Crossing → PWM off: **677 ms worst**, 28 phases.
- Stalled ADC → PWM off: **47 ms**, with G05 subsequently latched.
- Hung-loop watchdog: **250 ms**.
- Loop: **2,839 µs worst in the I/O model**. AVR CPU WCET and physical contact timing remain unverified.

All **405 commit cut boundaries** passed, observing both complete old and complete new settings.

Reviewer follow-ups: `08 §1` automatically enters SERVICE on invalid settings, conflicting with CONFIG_LOCK in `04 §4` / `05 §4`. `10 §2`’s 1 KB stack estimate needs updating. STATE updates remain with Claude under the write boundary. `check_docs.py`: **0 findings**.