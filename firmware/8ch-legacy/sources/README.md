# Source lists

One file per link unit, one source path per line, relative to `firmware/src/`.

Both build systems read these files instead of carrying their own copy of the
list. Before this, `Makefile` and `build.ps1` each held a hand-maintained set
of sources that had already started to drift, and a file added to one but not
the other builds green on the developer's machine and fails in CI, or worse,
links a different program than the one that was tested (`I-022`).

Blank lines and `#` comments are ignored.

| File | Links into |
|---|---|
| `base.txt` | every target: GPIO, SPI, board pin map, LCD |
| `app_8ch.txt` | the eight-channel protection application, minus its converter |
| `bank_max31856.txt` | the real board's converter bank (`U2`..`U9`) |
| `bank_max6675.txt` | the Proteus simulation's converter bank |
| `app_legacy.txt` | the superseded single-channel board's application |
| `sensor_max31856.txt` | single-channel MAX31856 backend for the legacy app |
| `sensor_max6675.txt` | single-channel MAX6675 backend for the legacy app |
| `host_test.txt` | the pure modules the host tests link natively |
| `host_test_app.txt` | `main_8ch.c`'s application modules, linked natively against HAL doubles alongside `main_8ch.c` itself (pulled in by `#include`, not listed here - see the list's own comment) (I-042) |
| `host_test_driver.txt` | the MAX31856 bank driver, linked natively against a register model (I-042) |
