# Open issues

One line per issue, numbered and never renumbered. Close an issue by moving it
to the Closed section with the date and what actually fixed it — do not delete
it.

A review or an audit does **not** get its own file. Its findings become issues
here, or they will be read once and forgotten.

Severity: **blocker** stops fabrication or release · **high** is a real failure
mode · **medium** costs time or quality · **low** is tidiness.

---

## Hardware

| # | Sev | Issue |
|---|---|---|
| I-026 | low | Ungrounded (insulated) junction probes would remove the cranking-current path between cylinders for free. Downgraded from blocker on 2026-09-07: the eight sensors sit on one engine block, so channel-to-channel differences are small, and the board is in its own panel 50 m away. Worth specifying if the supplier stocks them. `docs/decisions/0009`. |
| I-027 | medium | Only applies if `I-026` goes ahead. With an ungrounded probe the input pair floats and `C2`/`C3` couple to `GND_SENS` for AC only. Confirm from the MAX31856 datasheet whether internal biasing defines the common mode; if not, one ~1 MOhm resistor per channel from `TC_FILT_N` to `GND_SENS`, which changes the schematic. |
| I-028 | high | The 24 V source is undecided and it changes the input protection. From a panel supply off the mains, the present PTC + SS34 + SMBJ33A + TSR 1-2450 is adequate. From the engine battery and alternator it is not: load dump reaches 60-120 V on a 24 V system, the SMBJ33A clamps near 53 V and the TSR 1-2450 is rated to 36 V, so the regulator would be destroyed. That case needs a wide-input regulator (Recom R-78HB, 9-72 V, footprint already in KiCad) and a clamp under its ceiling. `docs/decisions/0009`. |
| I-025 | high | Four-layer fabrication is hard to source in Egypt. The board is 4-layer because In1 carries three ground planes and In2 three supply planes. A 2-layer version is feasible - the analogue-critical copper is only the ~18x24 mm front end of each channel, and a local unbroken ground pour under those eight blocks preserves most of it - but it needs a larger board, the supply rails as wide top tracks, and bottom-layer jumpers everywhere except under the front ends. Measured today: 766 segments / 2761 mm on F.Cu, 278 / 3593 mm on B.Cu, 125 vias. Decide between a 2-layer redesign and ordering 4-layer from JLCPCB/PCBWay. |
| I-002 | blocker | The schematic is not a drawing: 171 symbols, 543 labels, **0 wires**, one A4 sheet. It produces a correct netlist and passes ERC, but nobody can review or sign it. Source of all 171 `endpoint_off_grid` warnings. |
| I-003 | high | `IA0505S` is unregulated; at ~12 % load its output can approach 6 V. Mitigated by moving to a 16 V LDO (`0002`), but the module's real output has never been measured on hardware. |
| I-004 | high | The isolation barrier has never been verified electrically. `.kicad_dru` enforces 3 mm, chosen from the tightest part on the board, not from a standard. |
| I-005 | medium | DRDY and FAULT on all eight MAX31856 are unconnected. Both isolators are fully allocated. Fault detection relies on the SPI status register (0x0F). Accepted — `docs/decisions/0004`. |
| I-024 | low | One dangling via on `+3V3_SENS` at (67.80, 25.92): a pre-placed channel supply via whose stub did not survive the Specctra round trip. It reaches the plane but nothing else, so it is a drill hit that does no work. `drop_dangling_vias` does not catch it - KiCad's connectivity reports it as connected while DRC reports it as one-layer. Warning, not an error. |
| I-006 | medium | Eight silkscreen warnings remain (6 overlap, 2 over pads) plus one starved thermal. |
| I-007 | medium | Passives carry value, tolerance, dielectric and voltage but no MPN or distributor part number. Cannot go to an assembly house as is. |
| I-008 | low | The Murata NCS1S control-pin logic is unknown — the datasheet server returned HTTP 500 three times. Only matters if the wide-creepage regulated module is ever adopted. |
| I-010 | low | `semulation/` is still misspelled and its project file is `thermocouble [Autosaved]f.pdsprj`. The rename was attempted on 2026-09-07 but Proteus (PID 26536) held the folder open. Close Proteus and rerun. |

## Firmware

These are failure modes for a protection device, not polish.

| # | Sev | Issue |
|---|---|---|
| I-011 | high | No detection of a stuck or frozen reading. A shorted junction or a frozen ADC reads plausibly and forever, so the unit looks safe while it is blind. Needs a rate-of-change limit and a no-change timeout. |
| I-012 | high | The setpoint lives in RAM only. Any reset returns it to 200 °C. If the site set 120 °C, the unit silently permits a much higher temperature after a power cycle. Needs EEPROM with CRC and a fail-safe default. |
| I-013 | high | Trip response time is neither specified as a number nor measured. `docs/GOAL.md` states ≤ 1 s; nothing confirms it. |
| I-014 | high | `mcal_spi_transfer` returns on timeout without reading `SPDR`. On the ATmega32 `SPIF` clears by reading `SPSR` then `SPDR`, so one timeout can slip the byte stream permanently. The 8-channel driver has no re-init path. |
| I-015 | high | No fuse map for production. `BOD` matters most: at 3.3 V the right level is 2.7 V. Without it a slow supply sag can run arbitrary code and raise `RUN_PERMIT`. |
| I-016 | medium | `RUN_PERMIT` is a static level with no read-back. A pin stuck high, a shorted trace or a welded relay permits running forever and the firmware never knows. |
| I-017 | medium | MISO has no internal pull-up. With all CS high the shared line floats — the likely cause of the Proteus `Logic contention` warning. One line in `mcal_spi_master_init`. |
| I-018 | medium | MAX6675 driver uses SPI mode 1, which matches the Proteus model, not the real silicon (mode 0). |
| I-019 | medium | `max_decode_temperature_x10()` — sign-extend, shift, divide — has no host test. A shift error here returns a plausible wrong number, which no simulation would catch. |
| I-030 | blocker | **The 8-channel board has no firmware.** `main_8ch.c` — the only app with 8 channels, latching, setpoint and energised-to-run — links `temperature_max6675_bank.c`. The board carries eight MAX31856 (`U2`..`U9`). The only MAX31856 driver is single-channel (`BOARD_SENSOR_CS`, one pin) and links into the legacy `main.c`, which has no latch, no setpoint and no 8-channel scan. `README.md` says the two parts are "intentionally not mixed", but that was written when the deliverable was the single-channel board. Needs a `temperature_max31856_bank.c` taking a channel index, plus per-channel `init` and status-register reads — the mitigation `docs/decisions/0004` already assumes exists. |
| I-031 | high | The two apps drive `PB3` with **opposite polarity** and both `.hex` images are tracked in git. `main.c` sets the pin HIGH on over-temperature (alarm); `main_8ch.c` sets it HIGH while safe (run permit). Flashing `thermocouple_meter_max31856.hex` onto the 8-channel board inverts the safety function silently: the machine runs when hot and stops when cold. `hal_alarm_output_set()` carries the alarm-era name in both. Rename to the permit semantics and stop tracking any image that is not the board's. |
| I-032 | high | **No crystal, and the clock fuse is unspecified.** `U1.12/13` (XTAL1/XTAL2) are deliberately unconnected (`populate_schematic.py:474`) and there is no oscillator in the BOM, so the ATmega32A runs on its internal RC. Two consequences nothing in the repo covers: (a) the factory `CKSEL` default is internal **1 MHz**, but the firmware builds at `F_CPU=8000000UL`, so every `_delay_ms` runs 8x long — the 500 ms scan becomes 4 s and `R-3`'s 1 s trip is missed by four times, silently, on a correctly built image; (b) the internal RC is spec'd to a few percent over voltage and temperature, which is outside what an 8-bit UART frame tolerates, so `R-9` (Modbus RTU) is **not** "hardware ready" as `docs/GOAL.md` claims — and the board is already routed with no crystal footprint. Extends `I-015`, which names only `BOD`. No decision record exists for crystal versus internal RC. |

## Process

| # | Sev | Issue |
|---|---|---|
| I-021 | medium | No CI gate on the hardware. A change to the generator can break the board while the firmware CI stays green. |
| I-022 | low | Firmware has two parallel build systems (`Makefile`, `build.ps1`) with hand-maintained source lists that will drift. |
| I-023 | low | No version identity in the firmware. The board silkscreen now carries `THERMO-8CH REV A0 2026-09`; the firmware carries nothing. |
| I-033 | medium | Root `README.md` is stale and contradicts `AGENTS.md`. It calls the project a "100 C alarm output" meter, names `hardware/single-channel/` as the "Final physical design", and points at that board's `BOM.csv`. `AGENTS.md` says single-channel is superseded and must not be touched. It is the first file anyone opens. |
| I-034 | low | `erc-report.rpt` is dated 2026-09-06T08:57, `drc-report.rpt` 2026-09-07T01:40, so `run_all.ps1` has not been run end to end since the board changed. The ERC numbers quoted in `docs/STATE.md` under "2026-09-07" are a day old. Both reports are gitignored, so a fresh clone cannot audit the "Measured, not claimed" table at all. |

## Closed

| # | Closed | What fixed it |
|---|---|---|
| I-020 | 2026-09-07 | Split `generate_board.py` (1211 lines) into a `board/` package of ten modules, 18-258 lines each, by responsibility: config, units, geometry, boardio, placement, silkscreen, zones, copper, stitching, connections. `generate_board.py` is now a 65-line entry point and the stable import surface for `route.py`, `check_board.py` and `close_gaps.py`. Verified identical output: same 166 reference designators, same 16 supply vias, same structural checks, zero courtyard overlaps. |
| I-029 | 2026-09-07 | `docs/GOAL.md` corrected by the user's instruction: R-7 no longer says VFD, R-8 states the setpoint must never be hard-coded, and a new "Where it runs" section records the engine, the cylinder-body sensors, the dedicated panel and the 50 m cable so no agent has to guess again. |
| I-001 | 2026-09-07 | Not nine routing problems but three causes: `add_plane_stitching` filtered on `+3V3_SENS` so five of the six plane nets were never stitched; `finish()` poured the outer grounds *after* stitching so their isolated pieces did not exist yet; and `C56`/`C57`/`R33` sat in a 1 mm strip. Fixed by stitching every plane net, pouring before stitching, adding `stitch_pour_islands`, a 0.6 mm via fallback and a 1 mm placement move. `docs/decisions/0007`. DRC: 0 errors, 0 unconnected. Gerbers in `production/8ch/`. |
| I-009 | 2026-09-07 | `hardware/8ch/README.md` rewritten with the LP2985-3.3 and the measured numbers. |
| I-000 | 2026-09-06 | `Q1` had gate and source swapped — the gate sat on GND and the drive signal on the source, so the MOSFET could never turn on, the relay could never energise and `RUN_PERMIT` could never assert. The machine could not have started. Fixed in `populate_schematic.py`. |
