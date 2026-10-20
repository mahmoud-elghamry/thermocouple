# 08 - Service mode (bench test of the first boards, commissioning calibration)

Decided behaviour: `0043` section 7 and Astra review 4 finding 11. Service mode is part of the shipped firmware,
so the code tested on the bench is the code that runs on the engine. Normative for `service`.

## 1. Entry, exit, safety

* Entry: SET held at power-up (`06` 2). State `SERVICE` (`04`): **RUN never closes** in this mode - the PWM is not
  started at all; the ALARM relay stays de-energised (= alarm) except in the one confirmed relay step.
* Exit: only by reset/power cycle; the next start is `START_LATCHED` (ACK needed).
* Modbus is off; the RS-485 port prints the report as plain text, 9600 8N1, CR LF line ends.
* The LCD shows the current step on line 1 (`SERVICE MODE  P03`) and the last report line on lines 2-4.

## 2. Report line format

```
<step> <item> <value> OK|FAIL <reason>
```

`step` = `Pnn` passive or `Ann` active; `item` <= 16 chars, no spaces; `value` in the unit stated by the step;
one line per item. The last line is `END <n_ok> OK <n_fail> FAIL`.

## 3. Passive steps (automatic, in order, nothing switched)

| Step | Item(s) | Value | OK when |
|---|---|---|---|
| P01 | `BOARD` | build board type, firmware version, build hash | matches settings header (or blank board) |
| P02 | `FUSES` | lfuse/hfuse/efuse bytes (read via SPM `boot_lock_fuse_bits_get`) | equal the values in `02` |
| P03 | `RESET` | reset cause flags | always OK (information) |
| P04 | `FLASH_CRC` | CRC | matches the stored image CRC |
| P05 | `EEPROM_A`, `EEPROM_B`, `CAL` | valid/invalid, sequence | information (blank board = invalid, OK) |
| P06 | `ADC<b>_ID` per bank | ID register | per `03` |
| P07 | `ADC<b>_REGS` | read-back of the configuration | all match |
| P08 | `ADC<b>_AVDD` | mV | in the `03` window |
| P09 | `ADC<b>_REF` | ratio ppm | in window (before calibration: wide window of `03`) |
| P10 | `ADC<b>_ZERO`, `_GAIN` | uV / ratio | in window |
| P11 | `CJ<n>` per TMP126 | ID, C | ID 0x2126, CRC ok, 0..70 C on the bench |
| P12 | `CH<nn>` per channel | uV, C, type | fresh valid result, or `OPEN` with reason if nothing connected (FAIL only for fitted channels) |
| P13 | `CH<nn>_BURN` per channel | burnout reading | in window / open detected as expected |
| P14 | `ENGREF` | REFOK level, REFTEST result | REFOK active with FEED-SENSE connected; self-test passes |
| P15 | `SCAN` | ms per board scan | <= 750 ms |
| P16 | `LOOP` | worst loop ms | <= 20 ms |

## 4. Interactive and active steps

Each active step first shows on the LCD and prints:

```
A01 DISCONNECT RUN AND ALARM CONTACTS - SET=GO ESC=SKIP
```

and waits for SET (ESC skips and prints `SKIP`). The step never starts on a key that was already held.

| Step | What happens | OK when |
|---|---|---|
| A01 | keys: "PRESS UP" ... "PRESS ACK", "PRESS UP+DOWN" (ESC chord) one by one, 10 s each | each key seen pressed and released |
| A02 | ALARM relay: energise 1 s, release | ALARM_SENSE follows both ways (`04` 6.2) |
| A03 | RUN relay: start the PWM for 1 s, stop | RUN_SENSE low while on, high within 100 ms after stop; drop-out time printed in ms |
| A04 | RUN with PWM stopped but pin held high 1 s (static level) | relay must NOT stay energised after the pump decays (proves the charge pump) |
| A05 | EEPROM test on the scratch area 0x0F00-0x0FFF only: write pattern, read back, restore 0xFF | pattern matches; settings/calibration untouched (their CRC re-checked) |
| A06 | `CAL REF` (if selected): measure each bank's REF ratio, store the calibration record (`05` 6) | record valid after read-back |
| A07 | `LEARN BURNOUT` (if selected, every fitted probe connected): store baselines | every fitted channel inside the absolute window |

## 5. Example (24-ch, bench, one probe on channel 1, others open)

```
P01 BOARD 24 v1.0.0 a3f9c1 OK
P02 FUSES F7-C1-FC OK
P03 RESET POWERON OK
P04 FLASH_CRC 7A21 OK
P05 EEPROM_A INVALID OK
P06 ADC_A_ID 14 OK
P06 ADC_B_ID 14 OK
P06 ADC_C_ID 14 OK
...
P11 CJ1 2126 24.8C OK
...
P12 CH01 1012uV 25.1C K OK
P12 CH02 OPEN - FAIL OPEN
...
P15 SCAN 702ms OK
END 61 OK 23 FAIL
```

(Fuse bytes per `02` 6; the ADC ID value is OPEN-Q5 in `03` until confirmed on the first boards.) Claude reads this
on the PC through the USB-RS485 adapter and answers with the next action.
