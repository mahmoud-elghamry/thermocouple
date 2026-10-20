# 09 - Verification: tests, fakes, fault injection, bench, traceability

Every rule in `03`-`08` has a test that would fail if the rule were broken. Host tests run on every build
(`firmware/build.ps1`, CI); bench tests run on the first boards; field tests at the first engine (I-120).

## 1. Test levels

| Level | Where | Tool | Covers |
|---|---|---|---|
| Unit | PC | host gcc + test runner (existing `firmware/test` style) | pure modules: `tc_math`, `channel_eval`, `protection`, settings validator/serialiser, CRCs, Modbus map, key decoder, screen formatter |
| Driver | PC | fake devices (`01` 3) | `ad7124`, `tmp126`, `rtd`, `iso_spi`, `scan` against register-level fakes with injected faults |
| Scenario | PC | whole application linked with fakes, simulated time | end-to-end behaviour over minutes of simulated time (section 3) |
| Bench | first boards | service mode + scripted steps, USB-RS485 log read by Claude | hardware/firmware together (section 4) |
| Field | first engine | I-120 matrix | installation, 50 m cables, real temperatures |

Coverage target for the pure safety modules (`protection`, `channel_eval`, `settings` validator): every row of
every table in `04` and `05` exercised; branch coverage reported (gcov) and every uncovered branch justified.

## 2. Unit tests (minimum list)

| Module | Tests |
|---|---|
| `tc_math` | NIST reference points for K and J every 50 C across the range, both directions (EMF->T and T->EMF for CJ), error <= the table-interpolation bound of `03`; negative EMF (tip colder than CJ); out-of-range -> RANGE flag; PT100 points 0/100/400 C (40-ch, deferred) |
| `channel_eval` | every row of `04` 3.1/3.2 for each mode; boundaries: value == alarm SP, == trip SP, == trip SP - band, one LSB either side; advisory flags never change the condition |
| `protection` | every transition of `04` section 4; every ACK rule of section 5 (one test per refusal reason); first-out kept while further causes arrive; state/complement corruption -> TRIPPED; unknown enum -> most restrictive |
| `outputs` | window open/expiry, PWM never started without a fresh validated scan, read-back table `04` 6.2 with the 60 ms settle and 100 ms filter |
| `settings` | serialise/deserialise round trip; every validation rule of `05` 3 (one failing record per rule); boot selection table `05` 4 incl. modular sequence wrap |
| `events` | ring wrap, newest selection with sequence wrap, bad CRC entry skipped |
| `keys` | debounce, chord within/outside 150 ms, cancelled single press, long press, auto-repeat timing, release-before-press after boot and after trip, stuck key |
| `ui_screens` | each screen of `06` rendered to the exact 20x4 text for 8/24/40 boards; status-line priority |
| `modbus` | each register of `07` from a known snapshot; exceptions 01/02; CRC; frame end timing |

## 3. Scenario and fault-injection tests (host, simulated time)

| ID | Scenario | Pass |
|---|---|---|
| S01 | cold start, valid settings, all channels normal | START_LATCHED; ACK -> RUN; PWM on only after the first validated scan |
| S02 | ramp one channel through alarm and trip SP | alarm at alarm SP, RUN off within one slot cycle of the crossing sample; first-out correct |
| S03 | trip, then cool below trip SP but above trip SP - band; press ACK | refused R4; cool below; ACK accepted |
| S04 | ACK held during power-up | never accepted until released and pressed again (R1) |
| S05 | acquisition stalls (fake ADC stops answering) with timers running | RUN window expires <= 900 ms; B05; watchdog reset if the flow check stops |
| S06 | main loop hangs in one task | watchdog reset within 0.5 s; boot into START_LATCHED with G11 |
| S07 | power cut at every byte of a settings save (loop over all positions) | after "reboot" the old or the new record is used, never neither, never a mix |
| S08 | corrupt each settings field in EEPROM | CONFIG_LOCK, ACK refused |
| S09 | SPI CRC error once / repeatedly | once: retry, no fault; repeated: B02 trip |
| S10 | wrong ADC ID, register read-back mismatch, error register bit | B01/B03/B04 trip |
| S11 | one CJ invalid; both invalid; disagreeing | B12 (trip in v1); B10; B11 |
| S12 | REFOK lost; REFTEST fails | G08/G09 trip |
| S13 | 40-ch decoder alias (fake answers at the wrong address) | B13 trip |
| S14 | RUN read-back stays high when commanded on; stays low when commanded off | G06 trip/alarm per `04` 6.2 |
| S15 | Modbus flood of random bytes at 19200 during S02 | identical trip timing to S02 |
| S16 | protection setting committed while RUN | RUN opens before the EEPROM write starts; ACK needed after |
| S17 | names-only commit while RUN | RUN stays closed |
| S18 | ALARM ONLY channel over its trip SP, then a TRIP channel normal | alarm only; ACK of other trips not blocked by it |
| S19 | channel OFF with an open input | ignored entirely |
| S20 | (advisories not in v1) a real fast rise of 100 C/s | trip at the trip SP, nothing suppresses it |
| S21 | same fault code on two banks; one clears | the other bank's fault stays active |
| S22 | ADC_CONV_ERR on one conversion, ERROR read clears it | that conversion never used; fault until a new good conversion |
| S23 | settings committed mid-scan | the straddling scan does not count for ACK (R2) |
| S24 | island power lost then restored | G14, full re-init, RUN only after ACK and a validated scan |
| S25 | G05 deadline fault clears at the next scan | trip latch stays until ACK (no silent recovery to RUN) |
| S26 | RUN window expires at 900 ms, a validated scan arrives at 950 ms | TRIPPED at 900 ms; contact stays open until ACK |
| S27 | channel K -> OFF -> K, reset in between | baseline not accepted (epoch changed); LOCKED: CALIBRATE until re-learned |
| S28 | blank board learns in service, then a channel is configured as J | that channel LOCKED: CALIBRATE until re-learned |

## 4. Bench tests on the first boards (service mode + scripted, results in the board's log)

| ID | Test | Pass | Issue |
|---|---|---|---|
| T01 | power-on values (`POWER-ON-TEST.pdf`), lab supply with 0.3 A limit | in range | - |
| T02 | programming + fuse read-back | P02 OK | I-104 |
| T03 | service passive report | all fitted items OK | - |
| T04 | ice water and boiling water on two channels vs reference thermometer | within +-2 C (provisional bench acceptance; the K-table error itself is < 0.2 C, `03` 7) | I-101 |
| T05 | trip timing: heat a probe (or inject an EMF) across the trip SP, scope on the contact | <= 2 s required, ~1 s expected; measured value recorded | I-013 |
| T06 | open a probe wire | C01 within ~6 s (burnout) or at once (rail) | 0034 |
| T07 | cut FEED, cut SENSE | G08 trip | 0032 |
| T08 | pull the 24 V while running; brown-out | contact opens; restart needs ACK | 0029 |
| T09 | hold ACK at power-up; hold SET at power-up | no ACK; service mode | `06` |
| T10 | relay steps A02-A04 incl. static-level PB3 does not hold RUN | OK | I-118 |
| T11 | CJ gradient with LCD, relays and RS-485 loaded | compensated error within budget | I-114 |
| T12 | Modbus poll of every register; flood during T05 | correct values; T05 unchanged | I-086 |
| T13 | power cut during a settings save (relay-timed) | old or new settings, never neither | `05` |

## 5. Traceability (requirement -> where specified -> test)

| Requirement | Spec | Tests |
|---|---|---|
| Any channel trips the common contact, <= 2 s (GOAL, 0029; target ~1 s) | `04` 3, 6.3 | S02, T05 |
| Energised to run; reset/power loss opens (0030 D5) | `04` 4, 6 | S01, S06, T08 |
| Charge pump, refreshed only by completed scans (I-118) | `01` 2.4, `04` 6.1 | S05, T10 |
| Watchdog <= 0.5 s, flow-checked (I-119) | `01` 2.3 | S06 |
| Per-channel setpoints, never invented (I-100) | `05` 2-4 | S08, settings unit tests |
| Manual ACK, no auto restart (0029) | `04` 5 | S03, S04, T09 |
| Open sensor trips by default; alarm only per channel (0034 D1) | `04` 3.2 | S18, T06 |
| K/J per channel (0038) | `05` 2.2, `03` | tc_math tests, T04 |
| ADC diagnostics every scan (0032, I-104) | `03` | S09-S12 |
| Engine reference monitored (0032) | `03`, `04` G08/G09 | S12, T07 |
| Modbus never in the trip path (0031 D7) | `07` | S15, T12 |
| Settings A/B, CRC, semantic checks (0030 D8, 0038 D2) | `05` | S07, S08, T13 |
| Protection settings only with contact open + ACK (owner 2026-10-20) | `04` 4, `06` 4.1 | S16, S17 |
| 40-ch aliasing and PT100 (0039) | `03` | S13, rtd driver tests |
