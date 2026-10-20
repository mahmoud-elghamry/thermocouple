# 10 - Phases, module interfaces, budgets, who does what

## 1. Module interfaces (headers the implementer creates first)

Signatures are the contract between modules; names follow `00`. `res_t` = `enum { OK, BUSY, ERR_TIMEOUT,
ERR_CRC, ERR_ID, ERR_READBACK, ERR_RANGE }`.

| Module | Main functions | Pure? |
|---|---|---|
| `board_cfg` | `const board_t *board(void)` (banks, CS method, pins, channel table, keys, RTD) | data |
| `iso_spi` | `iso_select(dev)`, `iso_deselect()`, `iso_xfer(buf, n)`, `iso_sio_write_enable(bool)` | no |
| `ad7124` | `ad_init(bank)`, `ad_verify(bank)`, `ad_start_slot(bank, slot)`, `ad_poll(bank, *code) -> res_t` | no |
| `tmp126` | `cj_read(sensor, *temp_mC) -> res_t` | no |
| `rtd` (40-ch) | `rtd_step(*result) -> res_t` | no |
| `scan` | `scan_task()`, `const scan_out_t *scan_last()` (meas[], bank status, `scan_validated`, `scan_no`) | no |
| `tc_math` | `tc_emf_to_dC(type, emf_nV, cj_dC, *out) -> res_t`, `pt100_ohm_to_dC(...)` | **yes** |
| `channel_eval` | `chan_cond(const result_t*, const chan_cfg_t*) -> cond_t`, `chan_action(cond, mode) -> act_t` | **yes** |
| `protection` | `prot_step(const prot_in_t*, prot_state_t*, prot_out_t*)`, `prot_on_result(ch, ...)` | **yes** |
| `outputs` | `out_task(const prot_out_t*)`, `out_readback() -> rb_t` | no |
| `settings` | `set_validate(const settings_t*) -> res_t`, `set_pack/unpack`, `set_active()`, `set_commit(const settings_t*)` | validator/pack pure |
| `events` | `ev_log(type, code, unit, ch, value, thr)`, `ev_get(i, *e)` | no |
| `fault` | `fault_raise(code, unit)`, `fault_clear(code, unit)`, `fault_active(code)` | no |
| `ui` | `ui_task(budget_us)`; mailbox `ui_cmd_t` | screens pure |
| `modbus` | `mb_task(budget_us)`; `mb_build(const snapshot_t*, req, *resp)` | builder pure |
| `service` | `svc_task()` | no |
| MCAL | `gpio_*`, `spi_xfer`, `uart_*`, `tick_ms()`, `wdt_feed()`, `ee_read/ee_write_byte/ee_ready`, `flash_crc()` | no |

## 2. Budgets

| Item | Budget | Basis |
|---|---|---|
| Loop period | <= 5 ms typical, <= 8 ms worst | `01` 2 |
| `ui_task` | <= 1 ms | 8 LCD chars x ~50 us + formatting |
| `modbus_task` | <= 1 ms per call, one frame | `07` 2 |
| Scan cycle | ~690 ms normal, <= 870 ms worst, deadline 1000 ms (G05) | `03` 3.1, 10.2 |
| Crossing -> contact open | ~0.75 s normal, ~0.9 s worst estimate (requirement 2 s, target ~1 s; measured T05) | `04` 6.3 |
| Flash | <= 64 KB of 128 KB (tables ~3 KB) | CALCULATIONS 9.8/10.8 |
| RAM | <= 12 KB of 16 KB incl. 1.5 KB stack (F1: commit frame measured 1046 B + 384 B margin; F0 measured 8.0 KB: two scan copies, settings A/B images, fault registry; raised from 8 KB 2026-10-20) | `05` 7.3 + buffers |
| EEPROM | per `05` 1 | |

## 3. Phases

| Phase | Deliverable | Gate to pass before the next phase |
|---|---|---|
| **F0** bring-up (needed when the first boards arrive), **24-ch only** | build system for ATmega1284P; `board_cfg` for the 24-ch (8/40-ch tables later, same structure); minimal settings load + validate (read-only, no editing) and the fault registry; MCAL; early watchdog + flow check; fuses + programming script; `iso_spi`, `ad7124`, `tmp126`, `scan` with **all** diagnostic slots, `tc_math`; `outputs` minimal (RUN off, ALARM de-energised, read-back); calibration storage; 20x4 `lcd` + `keys`; `service` mode complete | unit + driver tests pass on the PC; on the first boards: programming + fuse read-back, cold start, watchdog-reset start, service report all OK for fitted items (`09` T01-T04, T09, T10) |
| **F1** protection | `channel_eval`, `protection`, `outputs` full (window, read-back table), `settings` A/B with commit, `events`, `fault` | all unit tests and scenarios S01-S28 pass; **Astra review of F1 code**; bench T05-T08, T13 |
| **F2** operator UI | `ui` screens and setup menus, PIN, commissioning flow | screen tests; owner's technician commissions a board from blank with only the LCD and keys |
| **F3** Modbus | `modbus` read-only map | map tests; bench T12; I-120 matrix before the first engine |

F0 is the only phase the first bench session needs. F1 must be complete and reviewed before any engine runs on
this board.

**Scope now: the 24-ch board.** 8-ch and 40-ch (incl. decoder and PT100, `03` 8-9) stay specified but are
implemented and tested only when those boards are revived; `board_cfg` keeps the extension points.

## 4. Who does what

* **Implementer: Sol (gpt-6.1-sol)** per phase, in a branch/worktree off `firmware`, given: this spec, the phase
  table, and the rule "write the tests from the spec first, then the code". Sol may run `build.ps1` and the host
  tests. It does not program boards.
* **Claude:** reviews every diff against the spec, runs the gates, programs the boards and reads the service
  reports on the bench, keeps `firmware/STATE.md` and this spec consistent.
* **Astra:** reviews the spec (now) and the F1 code before engine use.
* **Owner:** bench handling (power, probes, heat/ice, cables), decisions flagged as OPEN.

## 5. Open items carried by the spec

Listed in the files where they arise and collected here when the spec is reviewed; none blocks F0 except the
values marked OPEN in `02`/`03` (fuse bytes, register values, windows), which are fixed before F0 starts.
