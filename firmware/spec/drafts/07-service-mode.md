# Family firmware specification - 07 service mode (DRAFT, research input)

Status: draft. `0043` rev 2 section 7 ("Service mode") wins on any disagreement; `00-overview.md` conventions apply.
The service mode is the board's bench test: **the code tested on the bench is the code that ships** (0043 section 1).
Fuse expectations, pin sense polarity, scan limits and plausibility windows are owned by 01/02/03 and are referred to,
not invented. Screen mock-ups are 20x4 (notation in 05, section 0).

## 1. Entry and guarantees

* **Entry:** hold SET while powering up (05 section 8: the splash is shown 1.5 s; SET alone held from 0.5 s to 1.5 s
  after reset selects service mode; ACK+SET is PIN recovery instead; any other key pattern is no gesture).
* **RUN never closes in service mode.** On entry the service flag is set; the protection latch stays in START (latched),
  `ack_possible` is forced false, ACK is not armed and the charge-pump PWM (PB3) stays off. The only times RUN is driven are
  the explicit active steps A01/A02 (section 4), each after a keypad confirmation. ALARM is driven only in A03/A04.
* The service flag lives in RAM and is cleared only by a reset. Exit = reset (section 7).
* All acquisition code is the normal code; service mode reads its results, it does not use a separate driver.
* Modbus is off; the UART is the report port at 9600 8N1 (section 5).
* A watchdog reset, brown-out or power cut during service mode restarts the board normally (START: ACK REQUIRED).
* Settings and events are never modified by service mode, except the one scratch area of A05.

## 2. Flow

1. Entry splash, then `SERVICE MODE`:
```
|SERVICE MODE        |
|RUN STAYS OPEN      |
|PASSIVE TESTS START |
|                    |
```
2. **Passive part** (automatic, no keys except the key test at the end): steps P01-P72, section 3. One complete scan is
   captured after the board scan has been running validated for at least 2 scans (or 10 s timeout: the ADC steps then
   report FAIL `NO_VALID_SCAN`); steps P10-P32 all use that one captured scan.
3. **Key test** (P70-P72, needs a person).
4. `ACTIVE TESTS?` screen: SET starts, ESC skips all active steps (their lines are not produced; the summary says `SKIPPED A01-A05`).
5. **Active part**, steps A01-A05, each with its own warning and confirmation (section 4).
6. **Summary and report** (section 6), then send, browse or exit.

Progress screen during the passive part (row 4 = counts so far):
```
|SERVICE  PASSIVE    |
|P13 ADC_B_AVDD      |
|RUNNING...          |
|OK 41  FAIL 0       |
```

## 3. Passive steps, in order

**Report line format (exact):** `<step id> <item> <value> OK` or `<step id> <item> <value> FAIL <reason>`.

* Fields separated by exactly one space; `<step id>` = `P` or `A` and two digits; `<item>` and `<value>` contain no
  spaces (upper case, digits, `_ . + - : / =` and units written as `mV`, `uV`, `C`, `MS`); `<reason>` is the rest of the
  line, upper case with underscores, <= 24 characters, present **only** on FAIL.
* Value `-` when nothing could be read. Line length <= 60 characters, terminated by CR LF, ASCII only.
* Lines starting with `#` are comment lines: header `#SERVICE-REPORT 1 BOARD=<8CH|24CH|40CH> FW=<version>-<build>` first,
  trailer `#END PASS=<n> FAIL=<n>` last. Step lines are never split.
* Within a step, items are in ascending bank (A..E) or channel order. Steps are in ascending id.

Reason vocabulary: `NO_RESPONSE`, `BAD_CRC`, `BAD_ID`, `REG_MISMATCH`, `ERR_REGISTER_SET`, `OUT_OF_WINDOW`, `DISAGREE`,
`OPEN_SENSOR`, `NO_VALID_SCAN`, `TIMEOUT`, `STUCK`, `SENSE_MISMATCH`, `VERIFY_FAILED`, `NOT_RECORDED`, `EXPECTED=<hex>`,
`EEPROM_CRC`, `BOARD_MISMATCH`, `LIMIT_EXCEEDED`.

| Step | Item (value format) | OK when | Source of limits |
|---|---|---|---|
| P01 | `BOARD` (`8CH`/`24CH`/`40CH`) | build board = settings/EEPROM board identity if a record exists (blank record is OK) | 04 |
| P02 | `FIRMWARE` (`<ver>-<build>`) | always OK (identification) | - |
| P03-P05 | `FUSE_LOW`, `FUSE_HIGH`, `FUSE_EXT` (`0xNN`, read with LPM+BLBSET, no SPM) | equals the expected value in 01 (WDTON programmed, BOD, JTAG off, EESAVE programmed, clock 8 MHz crystal); FAIL reason `EXPECTED=0xNN` | 01 |
| P06 | `WDT_ACTIVE` (`YES`/`NO`) | WDE reads set and cannot be cleared | 01 |
| P07 | `RESET_CAUSE` (`POWER_ON`/`EXTERNAL`/`BROWNOUT`/`WATCHDOG`) | always OK (identification) | - |
| P08 | `SETTINGS_A`, `SETTINGS_B` (`SEQ=<n>`, `BLANK`, `INVALID`) | `SEQ`/`BLANK` OK, `INVALID` FAIL `EEPROM_CRC` | 04 |
| P09 | `CALIBRATION` (`BANK_A-C_PRESENT`, `NONE`) | present and CRC good; else FAIL `NOT_RECORDED` | 04 (OPEN-3) |
| P10 | `ADC_<b>_ID` (`0x14` for AD7124-8 or the revision 02 specifies) | ID/revision as 02 | 02 |
| P11 | `ADC_<b>_REGS` (`MATCH`/`DIFF`) | configuration registers read back as written | 02 |
| P12 | `ADC_<b>_ERR` (`0xNNNNNN`) | error register clear | 02 |
| P13 | `ADC_<b>_AVDD` (`4987mV` from the AVDD/6 slot) | inside the 02 window | 02 |
| P14 | `ADC_<b>_REF` (REF3030 ratio, 4 decimals) | inside the 02 window (provisional +-1.6 %, 0043 section 4.2) | 02 |
| P15 | `ADC_<b>_CRC` (`good/total` over 200 reads of the ID register) | good = total | 02 |
| P20 | `TMP126_<b>1`, `TMP126_<b>2` (`+23.4C`; ID 0x2126 and CRC are checked inside) | valid, ID correct, plausible range | 02 |
| P21 | `CJ_<b>_AGREE` (difference in C) | within the agreement window of 03/I-114 | 03 |
| P30 | `CH<nn>_EMF` (`+0.012mV`; PT100 on the 40-ch: `CH41_RES` in `109.73R`) | conversion valid and within the service plausibility window of 02 | 02 |
| P31 | `CH<nn>_TEMP` (`+24.1C`, K type unless settings say J) | valid; with shorted inputs or probes at room temperature within the window of 02 around the cold junction | 02 |
| P32 | `CH<nn>_BURN` (`OK`/`OPEN`) | burnout result not open; FAIL `OPEN_SENSOR` | 02 |
| P40 | `SCAN_MS` (milliseconds of the last complete scan) | below the complete-scan deadline of 03 | 03 |
| P50 | `REFOK` (`PRESENT`/`ABSENT`) | PA2 active-low = reference present | 0032 |
| P51 | `REFTEST` (`PASS`/`FAIL`) | self-test sequence of 0032 rev 4 passes | 0032 |
| P60 | `RUN_SENSE` (`OPEN`/`CLOSED`) | `OPEN` (RUN is off in service mode) | 01 |
| P61 | `ALARM_SENSE` (`ALARM`/`CLEAR`) | `ALARM` (the outputs module holds the alarm state; polarity per 03) | 01/03 |
| P70 | `KEY_IDLE` (`ALL_RELEASED` or `<KEY>_DOWN`) | no key down at the start; else FAIL `STUCK` | - |
| P71 | `KEY_UP`, `KEY_DOWN`, `KEY_SET`, `KEY_ACK` (`PRESSED`/`-`) | seen pressed within 20 s of its prompt; else FAIL `TIMEOUT` | - |
| P72 | 24-ch: `KEY_ESC_CHORD`; 8-ch/40-ch: `KEY_ESC` (`PRESSED`/`-`) | seen within 20 s (24-ch: UP and DOWN together, the ESC button) | - |
| P80 | 40-ch only: `DECODER_SIG` (`MATCH`/`DIFF`) | each ADC/TMP126 unique signature reads back (0043 section 4.4) | 02 |
| P81 | 40-ch only: `RTD_CHECK_R` (ohm), `RTD_REF` (`OK`/`BAD`) | check resistor 150 ohm 0.1 % and reference within windows | 02 |

Banks `<b>`: A for 8-ch; A-C for 24-ch; A-E for 40-ch. Channels `<nn>`: 01-08, 01-24, 01-40 (+41-43 on 40-ch).
Inputs of a bench test are shorted (or at room temperature probes); an open input legitimately fails P30-P32.

Key test prompts (row 3 = key name, row 4 = seconds left); each key in the order UP, DOWN, SET, ACK, ESC:
```
|SERVICE  KEY TEST   |
|PRESS KEY:          |
|UP                  |
|TIME LEFT 18 S      |
```
For ESC on the 24-ch row 3 reads `UP+DOWN (ESC)`.

## 4. Active steps

Each active step follows the same two-screen pattern; nothing is driven before the technician **holds SET for 2 s**.
ESC skips the step (no report line). Warning screen, RUN and ALARM steps:
```
|ACTIVE TEST A01     |
|DISCONNECT RUN AND  |
|ALARM CONTACTS FIRST|
|HOLD SET 2S=GO ESC  |
```
The firmware cannot verify the disconnection; the warning and the hold are the only guards. Steps:

| Step | Action | Report items | OK when |
|---|---|---|---|
| A01 | enable RUN drive (charge pump PWM on) for up to 1 s, measure the time until the read-back says closed | `RUN_ON` (`140MS`) | closes within the limit of 01 and the sense agrees |
| A02 | stop the drive and measure the time until the read-back says open | `RUN_OFF` (`35MS`) | opens within the limit and the sense agrees |
| A03 | drive ALARM to the non-alarm state, measure the read-back | `ALARM_ON` (`12MS`) | read-back follows (polarity per 03) |
| A04 | drive ALARM back to the alarm state, measure the read-back | `ALARM_OFF` (`11MS`) | read-back follows |
| A05 | EEPROM scratch test (below) | `EEPROM_SCRATCH` (`4PATTERNS`) | all patterns read back; FAIL `VERIFY_FAILED` |

(A01+A02 and A03+A04 each run as one confirmation; the warning screen is shown per pair. The names `RUN_ON`/`ALARM_ON`
mean "driven to the energised state".) Failure reasons: `SENSE_MISMATCH`, `TIMEOUT`, `LIMIT_EXCEEDED`. After each pair the
outputs are returned to RUN off / ALARM active before anything else happens.

**A05 EEPROM test** touches **only the scratch area** reserved by 04 (a fixed block that no settings copy, calibration
record or event ring uses; a compile-time check refuses a build where the scratch block overlaps another region). It reads
the block, writes the patterns `0x00`, `0xFF`, `0xAA`, `0x55`, each time reading back and comparing, writes address-dependent
data once, then **restores the original contents**. The service code has no API that can address outside the block. The
screen shows (no contact warning, but the same 2 s hold):
```
|ACTIVE TEST A05     |
|EEPROM SCRATCH AREA |
|ONLY. SETTINGS SAFE |
|HOLD SET 2S=GO ESC  |
```
If power is cut during A05 the scratch block holds garbage; nothing depends on its contents.

Running screen of an active step: `ACTIVE TEST A01` / `RUN CONTACT DRIVEN` / `DO NOT TOUCH`.

## 5. Report transmission

* Interface: RS-485 UART, **9600 baud, 8 data bits, no parity, 1 stop bit** (8N1), ASCII, lines end CR LF, regardless of
  the Modbus settings. DE (PD7) asserted only while sending, released at transmit-complete (06 section 2.2).
* Lines are sent **as they are produced** (streaming, so a PC logger sees progress) and the whole report can be **re-sent**
  from the summary screen. The results are kept in a small RAM table (id, item index, value, status, reason code: ~8
  bytes per line, about 1 KB for the 24-ch, about 1.7 KB for the 40-ch); lines are formatted from the table on demand,
  so no 5 KB text buffer is needed.
* The PC end is a USB-RS485 adapter. A missing listener does not stop the test; the LCD carries the result.
* Sending never blocks the main loop; the next test step does not wait for the UART.

## 6. LCD during and after the test

Summary:
```
|SERVICE  DONE       |
|PASS 124 FAIL 1     |
|FIRST FAIL P32      |
|SET=SEND UP/DN=LIST |
```
UP/DOWN browse every report line, one per screen (`STEP n/N`, id and item, value, `OK` or `FAIL reason`):
```
|STEP 102/125        |
|P32 CH17_BURN       |
|OPEN                |
|FAIL OPEN_SENSOR    |
```
SET short = send the whole report again; ESC = exit menu (section 7). A zero-fail run shows `ALL OK` on row 3 of the summary.

## 7. Exit

* From the summary: ESC (24-ch: UP+DOWN) shows `EXIT SERVICE?` with `HOLD SET 2S=RESTART` / `ESC=STAY`; a 2 s hold performs
  a deliberate watchdog reset (the watchdog fuse makes it unstoppable) and the board starts normally: `START: ACK REQUIRED`.
* Power cycle exits at any time.
* No key is needed to leave a running step; a step that times out reports FAIL and continues.

## 8. Example complete report, 24-ch, blank board, inputs shorted, one open probe on channel 17

All values are illustrative (fuse bytes are an example for 8 MHz crystal, BOD 4.3 V, JTAG off, WDTON, EESAVE; the real
expected values come from 01). 125 step lines, pass 124, fail 1:

```
#SERVICE-REPORT 1 BOARD=24CH FW=1.0.0-0042
P01 BOARD 24CH OK
P02 FIRMWARE 1.0.0-0042 OK
P03 FUSE_LOW 0xE7 OK
P04 FUSE_HIGH 0xC1 OK
P05 FUSE_EXT 0xFC OK
P06 WDT_ACTIVE YES OK
P07 RESET_CAUSE POWER_ON OK
P08 SETTINGS_A BLANK OK
P08 SETTINGS_B BLANK OK
P09 CALIBRATION BANK_A-C_PRESENT OK
P10 ADC_A_ID 0x14 OK
P10 ADC_B_ID 0x14 OK
P10 ADC_C_ID 0x14 OK
P11 ADC_A_REGS MATCH OK
P11 ADC_B_REGS MATCH OK
P11 ADC_C_REGS MATCH OK
P12 ADC_A_ERR 0x000000 OK
P12 ADC_B_ERR 0x000000 OK
P12 ADC_C_ERR 0x000000 OK
P13 ADC_A_AVDD 4987mV OK
P13 ADC_B_AVDD 4987mV OK
P13 ADC_C_AVDD 4987mV OK
P14 ADC_A_REF 0.9996 OK
P14 ADC_B_REF 1.0004 OK
P14 ADC_C_REF 1.0011 OK
P15 ADC_A_CRC 200/200 OK
P15 ADC_B_CRC 200/200 OK
P15 ADC_C_CRC 200/200 OK
P20 TMP126_A1 +23.4C OK
P20 TMP126_A2 +23.6C OK
P20 TMP126_B1 +23.5C OK
P20 TMP126_B2 +23.5C OK
P20 TMP126_C1 +23.2C OK
P20 TMP126_C2 +23.4C OK
P21 CJ_A_AGREE 0.2C OK
P21 CJ_B_AGREE 0.0C OK
P21 CJ_C_AGREE 0.2C OK
P30 CH01_EMF +0.019mV OK
P30 CH02_EMF +0.026mV OK
P30 CH03_EMF +0.033mV OK
P30 CH04_EMF +0.040mV OK
P30 CH05_EMF +0.047mV OK
P30 CH06_EMF +0.014mV OK
P30 CH07_EMF +0.021mV OK
P30 CH08_EMF +0.028mV OK
P30 CH09_EMF +0.035mV OK
P30 CH10_EMF +0.042mV OK
P30 CH11_EMF +0.049mV OK
P30 CH12_EMF +0.016mV OK
P30 CH13_EMF +0.023mV OK
P30 CH14_EMF +0.030mV OK
P30 CH15_EMF +0.037mV OK
P30 CH16_EMF +0.044mV OK
P30 CH17_EMF +0.051mV OK
P30 CH18_EMF +0.018mV OK
P30 CH19_EMF +0.025mV OK
P30 CH20_EMF +0.032mV OK
P30 CH21_EMF +0.039mV OK
P30 CH22_EMF +0.046mV OK
P30 CH23_EMF +0.013mV OK
P30 CH24_EMF +0.020mV OK
P31 CH01_TEMP +23.9C OK
P31 CH02_TEMP +24.0C OK
P31 CH03_TEMP +24.2C OK
P31 CH04_TEMP +24.4C OK
P31 CH05_TEMP +24.6C OK
P31 CH06_TEMP +23.8C OK
P31 CH07_TEMP +23.9C OK
P31 CH08_TEMP +24.1C OK
P31 CH09_TEMP +24.3C OK
P31 CH10_TEMP +24.4C OK
P31 CH11_TEMP +24.6C OK
P31 CH12_TEMP +23.8C OK
P31 CH13_TEMP +24.0C OK
P31 CH14_TEMP +24.1C OK
P31 CH15_TEMP +24.3C OK
P31 CH16_TEMP +24.5C OK
P31 CH17_TEMP +24.7C OK
P31 CH18_TEMP +23.8C OK
P31 CH19_TEMP +24.0C OK
P31 CH20_TEMP +24.2C OK
P31 CH21_TEMP +24.4C OK
P31 CH22_TEMP +24.5C OK
P31 CH23_TEMP +23.7C OK
P31 CH24_TEMP +23.9C OK
P32 CH01_BURN OK OK
P32 CH02_BURN OK OK
P32 CH03_BURN OK OK
P32 CH04_BURN OK OK
P32 CH05_BURN OK OK
P32 CH06_BURN OK OK
P32 CH07_BURN OK OK
P32 CH08_BURN OK OK
P32 CH09_BURN OK OK
P32 CH10_BURN OK OK
P32 CH11_BURN OK OK
P32 CH12_BURN OK OK
P32 CH13_BURN OK OK
P32 CH14_BURN OK OK
P32 CH15_BURN OK OK
P32 CH16_BURN OK OK
P32 CH17_BURN OPEN FAIL OPEN_SENSOR
P32 CH18_BURN OK OK
P32 CH19_BURN OK OK
P32 CH20_BURN OK OK
P32 CH21_BURN OK OK
P32 CH22_BURN OK OK
P32 CH23_BURN OK OK
P32 CH24_BURN OK OK
P40 SCAN_MS 702 OK
P50 REFOK PRESENT OK
P51 REFTEST PASS OK
P60 RUN_SENSE OPEN OK
P61 ALARM_SENSE ALARM OK
P70 KEY_IDLE ALL_RELEASED OK
P71 KEY_UP PRESSED OK
P71 KEY_DOWN PRESSED OK
P71 KEY_SET PRESSED OK
P71 KEY_ACK PRESSED OK
P72 KEY_ESC_CHORD PRESSED OK
A01 RUN_ON 140MS OK
A02 RUN_OFF 35MS OK
A03 ALARM_ON 12MS OK
A04 ALARM_OFF 11MS OK
A05 EEPROM_SCRATCH 4PATTERNS OK
#END PASS=124 FAIL=1
```

## 9. Differences per board

| Board | Banks | Channels | P80/P81 | ESC key step |
|---|---|---|---|---|
| 8-ch | A | 01-08 | no | `KEY_ESC` (pin PD5) |
| 24-ch | A-C | 01-24 | no | `KEY_ESC_CHORD` |
| 40-ch | A-E | 01-40, 41-43 PT100 | yes | `KEY_ESC` (pin PD5) |

Line counts: 8-ch about 60, 24-ch 125 (the example), 40-ch about 200. At 9600 baud (960 bytes per second) the 24-ch
report of about 4 KB takes about 4-5 s to send.

## 10. Tests

* Host: result table formatting for every line (grammar check by regular expression
  `^[PA][0-9]{2} [^ ]+ [^ ]+ (OK|FAIL [A-Z0-9_=]{1,24})$`), counts in the trailer, entry decision from key patterns (SET only,
  ACK+SET, mixed), RUN never driven before A01 confirmation, scratch-area bound, exit path.
* Bench: report on the PC through the USB-RS485 adapter on all first boards; wrong fuse byte -> P03-P05 FAIL; open
  channel -> P32 FAIL; key held at power-up -> P70 FAIL; scope on RUN during the whole service run: closes only in A01.

## 11. OPEN items

* OPEN-1: expected fuse values, limits for A01-A04 timings, scan limit, windows: from 01/02/03 (this file only names them).
* OPEN-2: whether the REFTEST pulse, which acts on the REF_SENSE filter, may run with the engine reference connected; 0032 rev 4
  decides.
* OPEN-3: where the production calibration record is written (not defined in 0043): P09 only reports it. A calibration step
  could be added to the active part later; it is not specified here.
* OPEN-4: scratch-area address and size are 04's (a 32-64 byte block at the end of the EEPROM is suggested).
* OPEN-5: the 2 s hold for active steps and the 20 s key timeout are drafts.
