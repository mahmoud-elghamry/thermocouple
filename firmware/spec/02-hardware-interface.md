# 02 - Hardware interface (adopted 2026-10-20 from the research draft; fault codes and cross-references aligned with `04`; OPEN items at the end)

Status: draft research input for `firmware/spec/02-hardware-interface.md` (2026-10-20). Facts carry their source;
anything not confirmed from a source is marked **OPEN** with what is needed. Conventions: `00-overview.md`.
Decided behaviour: `docs/decisions/0043` rev 2 (3.6, 4.1, 4.3, 4.4).

## 0. Sources used

| Tag | Source | Revision / where |
|---|---|---|
| M24 | `hardware/24ch/gen/c_mcu.py`, `c_iso.py`, `c_bank.py`, `c_out.py` | branch `24ch-rev-a4`, last c_mcu change `3a2480c` (2026-10-15) |
| FAM | `hardware/family/gen/boards.py`, `c_iso.py`, `c_rtd.py` | `main` `ba01457` (2026-10-19) |
| D39 | `docs/decisions/0039` (notes for the firmware chat, D3, P2-P8) | `main` |
| D41 | `docs/decisions/0041` (SIO_WR_N, ESC diodes) | this branch |
| C | `docs/reference/CALCULATIONS.md` 1.3, 8.5, 9.7, 10.7 | `main` |
| AVR | ATmega164A/PA/324A/PA/644A/PA/1284/P complete data sheet | Microchip DS40002070B (2020) |
| ISO | CA-IS3760/61/62/63 data sheet, 6.10 switching characteristics | Chipanalog 2019 (local text, Chinese headings stripped) |
| ADC | AD7124-8 data sheet **Rev B** (Chinese edition, local copy; page/table numbers of Rev B) | ADI D13048sc-0-7/15(B) |
| TMP | TMP126 data sheet | TI SNIS209C (June 2022), downloaded 2026-10-20 |
| HC | CD74HC154 data sheet (TI) - same 74HC family as the fitted Nexperia 74HC154PW | TI, downloaded 2026-10-20 |
| LVC | SN74LVC1G125 data sheet, switching characteristics | TI (local text) |
| 485 | ADM2582E/ADM2587E data sheet, Table 3 (ADM2587E, 500 kbps) | ADI (local text) |

**OPEN-A1:** the English AD7124-8 data sheet (current revision) could not be downloaded in this session
(analog.com timed out). Every AD7124 citation below is Rev B page/table; re-cite against the current English
revision before the spec is frozen (table numbers may have moved).

## 1. Pin tables

Notation: **Dir** O = output, I = input, I-PU = input with internal pull-up (PORTxn = 1, DDxn = 0).
**Reset state** = what the pin does while the MCU is in reset / before firmware touches it: every AVR I/O is
tri-stated during reset (AVR 14.2.6: "the pull-up will be disabled during reset"), so the level is set by the
board. **Init** = value firmware writes in step S2 of section 8 (PORT written before DDR so an output never
glitches to the wrong level).

### 1.1 24-ch REV A4 (source M24 `c_mcu.py:6-16`, FAM `B24`)

| Pin | Signal | Dir | Reset state (board) | Init | Notes |
|---|---|---|---|---|---|
| PA0 | LCD_RS | O | floating | 0 | HD44780 RS; LCD R/W tied to GND (J502 pin 5) -> write-only, no busy flag |
| PA1 | LCD_E | O | floating | 0 | |
| PA2 | REFOK | I | driven by U404 reverse ch. (push-pull) | input, no pull-up | **active low**: low = engine wire connected; high = broken **or island unpowered** (isolator default-high, `c_iso.py` U408 note) |
| PA3 | REFTEST | O | floating -> U405 input open | 0 | high = self-test (Q401 pulls REF_SENSE low). **OPEN-H1:** CA-IS3761 output state with its input *floating* (MCU in reset) is not in the local text; if it defaults high, REFOK reads "broken" during MCU reset - harmless (RUN is off) |
| PA4-PA7 | LCD_D4-D7 | O | floating | 0 | |
| PB0 | CS_ADC2 | O | high (R431 10k to +5V) | 1 | bank B AD7124, via U403 |
| PB1 | CS_ADC3 | O | high (R432) | 1 | bank C AD7124, via U403. CKOUT fuse must stay unprogrammed (section 6) |
| PB2 | CS_CJ1 | O | high (R433) | 1 | bank A TMP126 #1, via U404 |
| PB3 | RUN_PERMIT | O (OC0A) | floating; R702 100k holds the trip gate low -> relay off | 0, Timer0 off | charge-pump drive, section 4.2. A static level never holds the relay (`c_out.py` pump note) |
| PB4 | CS_ADC1 | O | high (R430) | 1 | bank A AD7124. **Also the SPI /SS pin**: must be an output before SPE/MSTR are set (AVR 18.3) |
| PB5 | MOSI | O | floating | 0 | SPI and TMP126 bit-bang data out; also ISP |
| PB6 | MISO | I | via R405 2k2 from U403 reverse ch. | input, no pull-up | ISP contention resistor R405 |
| PB7 | SCK | O | floating | **1** | SPI mode 3 idles high (section 3) |
| PC0 | CS_CJ2 | O | high (R434) | 1 | bank A TMP126 #2 |
| PC1 | CS_CJ3 | O | high (R435) | 1 | bank B TMP126 #1 |
| PC2 | RUN_SENSE | I | R703 10k from coil low side, 100 nF | input, no pull-up | low = trip relay coil energised. JTAG TCK pin: JTAGEN fuse off + MCUCR.JTD (section 6, 8) |
| PC3 | CS_CJ4 | O | high (R436) | 1 | bank B TMP126 #2; JTAG TMS |
| PC4 | CS_CJ5 | O | high (R437) | 1 | bank C TMP126 #1; JTAG TDO |
| PC5 | CS_CJ6 | O | high (R438) | 1 | bank C TMP126 #2 (via U405); JTAG TDI |
| PC6 | ALARM_DRIVE | O | floating; R712 100k gate pull-down -> alarm relay off | 0 | relay energised when high. Polarity meaning (energised = no alarm?) is `04`'s (0043 3.5, "to confirm in F0") |
| PC7 | ALARM_SENSE | I | R713 10k from coil low side | input, no pull-up | low = alarm coil energised |
| PD0 | UART_RX (RXD0) | I | R738 10k pull-up (ADM2587E RxD is high-Z while transmitting) | USART0 | |
| PD1 | UART_TX (TXD0) | O | floating | USART0 | |
| PD2 | BTN_UP | I-PU | floating | pull-up | active low. UP and DOWN low together = ESC (D41 D3, D501/D502) |
| PD3 | BTN_DOWN | I-PU | floating | pull-up | active low |
| PD4 | BTN_SET | I-PU | floating | pull-up | active low |
| PD5 | SIO_WR_N | O | high (R439 10k; island side R445 10k) | 1 | low = U411 drives DIN onto TMP126 SIO (D41 D1). **Never low while an AD7124 CS is low** |
| PD6 | BTN_ACK | I-PU | floating | pull-up | active low |
| PD7 | RS485_DE | O | low (R737 10k pull-down) = receive | 0 | DE and /RE tied (R733) |
| RESET | RESET_N | - | R501 10k, C508 10n | - | ISP J501 pin 5 |
| XTAL1/2 | 8 MHz crystal | - | Y501, 22 pF C0G | - | fuses section 6 |
| AREF | AREF | - | 100 nF | - | AVR ADC not used |

ESC on the 24-ch has no pin: ESC = BTN_UP and BTN_DOWN both low (C 8.5: pin reads ~0.6 V vs VIL max 1.5 V).

### 1.2 8-ch REV B0 (source FAM `B8`: MCU24 with PC1 = SIO_WR_N and unused CS removed; D39 notes)

Same as 1.1 except:

| Pin | Signal | Dir | Reset state | Init | Notes |
|---|---|---|---|---|---|
| PB0 | - (unused) | I-PU | floating | pull-up | AVR 14.2.6 recommends the internal pull-up on unconnected pins |
| PB1 | - (unused) | I-PU | floating | pull-up | |
| PB2 | CS_CJ1 | O | high (R433) | 1 | TMP126 #1 via U403 |
| PB4 | CS_ADC1 | O | high (R430) | 1 | /SS: output before SPI enable |
| PC0 | CS_CJ2 | O | high (R434) | 1 | TMP126 #2 via U403 |
| PC1 | SIO_WR_N | O | high (R439) | 1 | via U404 |
| PC3, PC4, PC5 | - (unused) | I-PU | floating | pull-up | JTAG pins: JTAG off still required |
| PD5 | BTN_ESC | I-PU | floating | pull-up | own ESC pin (no diodes, `esc_diodes=False`); UP+DOWN chord also = ESC (0043 6) |

Isolators: U403 forward SCK, MOSI, CS_ADC1, CS_CJ1, CS_CJ2; reverse DOUT -> MISO. U404 forward REFTEST,
SIO_WR_N; reverse REFOK.

### 1.3 40-ch REV A0 (source FAM `B40` / `MCU40`; D39 D3 and notes)

Same as 1.1 except:

| Pin | Signal | Dir | Reset state | Init | Notes |
|---|---|---|---|---|---|
| PB0 | CSA0 | O | floating (no pull-up) | 0 | 74HC154 A0 via U403. Address lines are don't-care while CS_EN is high |
| PB1 | CSA1 | O | floating | 0 | A1 via U403 |
| PB2 | CSA2 | O | floating | 0 | A2 via U403 |
| PC0 | CSA3 | O | floating | 0 | A3 via U404 - **a different port from A0-A2**, so an address change is never atomic: change it only while CS_EN is high |
| PB4 | CS_EN | O | high (R430 10k control side; R444 10k island side) | **1 first, then DDR** (D39: "drive high before making it an output") | 74HC154 E0 (E1 tied to GND_ISO). High = every Y output high = all devices deselected. Also /SS |
| PC1 | SIO_WR_N | O | high (R439) | 1 | via U404 |
| PC3, PC4, PC5 | - (unused) | I-PU | floating | pull-up | |
| PD5 | BTN_ESC | I-PU | floating | pull-up | |

Decoder outputs (FAM `c_iso.py decoder()`): Y0-Y4 = AD7124 of banks A-E, Y5 = RTD AD7124, Y6-Y15 = TMP126 1-10
where TMP126 j of bank b (b = 1..5, i = 0,1) is j = 2(b-1)+i+1, i.e. bank A = Y6/Y7, B = Y8/Y9, C = Y10/Y11,
D = Y12/Y13, E = Y14/Y15. Address = Yn number, A0 = LSB.

Isolators: U403 forward SCK, MOSI, CSA0, CSA1, CSA2; reverse DOUT -> MISO. U404 forward CSA3, CS_EN, REFTEST,
SIO_WR_N; reverse REFOK.

### 1.4 What is common (all boards)

* RUN_PERMIT PB3, RUN_SENSE PC2, ALARM_DRIVE PC6, ALARM_SENSE PC7, REFOK PA2, REFTEST PA3, LCD port A,
  UART PD0/PD1, RS485_DE PD7, buttons PD2/PD3/PD4/PD6 (+ PD5 ESC on 8/40), SPI PB5/PB6/PB7.
* Island devices share one SCLK, one DIN and one DOUT net (DOUT_ISO) through one reverse isolator channel
  (`c_iso.py`). R447 100k biases DOUT_ISO high when nothing drives it: **idle DOUT data is undefined, never read
  it** (`c_iso.py sio_driver()` R447 note).
* AD7124 SYNC: 24-ch R191/R291/R391 10k to +3V3_ISO; 8/40-ch tied to +3V3_ISO (D39 P8). Firmware never drives
  SYNC. AD7124 CLK pin not connected: internal clock only.
* TMP126 ALERT pins grounded (`c_bank.py`); ALERT is never used.

## 2. Chip-select strategy

### 2.1 Rules (all boards; 0043 4.1, D41, D39 D3)

1. At most one island device selected at a time. Firmware keeps a single bus-owner state in `iso_spi`.
2. >= 1 us between any two CS edges (CS high -> next CS low, and CS low -> first SCLK, last SCLK -> CS high).
3. SIO_WR_N low only inside a TMP126 frame, never while an AD7124 is selected.
4. No AD7124 continuous-read mode (CONT_READ = 0, `03` section 2.1); never hold an AD7124 CS low while waiting
   for a conversion - poll with short transactions.
5. Before any CS goes low: SCK is at its idle level for the transfer type (high for both AD7124 SPI mode 3 and
   the TMP126 bit-bang of section 2.4).

### 2.2 Direct CS (8-ch, 24-ch)

`select(dev)`: CS pin low, wait >= 1 us, transfer. `deselect()`: wait >= 1 us after the last SCLK edge, CS pin
high, wait >= 1 us before the next select.

Why 1 us is enough (worst cases from the data sheets):

| Path element | Max | Source |
|---|---|---|
| CA-IS3761 propagation tPLH/tPHL | 13 ns | ISO 6.10.1 / 6.10.2 (5 V and 3.3 V tables) |
| CA-IS3761 part-to-part skew tsk(pp) (CS on a different isolator than SCLK, e.g. CS_CJ on U404/U405) | 4.5 ns | ISO 6.10.2 |
| AD7124 CS high -> DOUT high-Z (t5) | 80 ns | ADC Rev B Table 3 (p.10) |
| TMP126 CS high -> SIO high-Z, tSIO(DIS) | 200 ns | TMP 7.6 |
| TMP126 CS low -> first rising SCLK, tLEAD | 100 ns min | TMP 7.6 |
| TMP126 CS high time between frames, tINTERFRAME | 100 ns min | TMP 7.6 |
| AD7124 CS low -> SCLK (t10) | 0 ns min | ADC Rev B Table 3 |

Largest requirement ~200 ns + 2 x 13 ns -> **1 us gives > 3x margin**. At 8 MHz, 1 us = 8 CPU cycles; implement
with a calibrated busy-wait (`_delay_us(1)` with F_CPU = 8000000) - not with the 1 ms tick.

### 2.3 Decoded CS (40-ch, 74HC154)

Sequence to select device n (Yn, n = 0..15) - D39 D3, 0043 4.4:

```
1. CS_EN = 1                      (already 1 when idle)
2. wait >= 1 us                   previous device released DOUT (t5 80 ns / tSIO(DIS) 200 ns) and
                                  every Y output high (HC enable-to-output <= 265 ns, below)
3. CSA0..CSA3 = n                 PB0..PB2 then PC0; non-atomic is fine because EN is high
4. wait >= 1 us                   address through U403/U404 (13 ns) and settled at the HC inputs
5. CS_EN = 0                      Yn goes low
6. wait >= 1 us                   E0 -> Yn propagation (<= 265 ns) + isolator 13 ns
7. clock the transfer
8. wait >= 1 us after the last SCLK edge
9. CS_EN = 1
10. wait >= 1 us before step 3 of the next select (rule 2)
```

Decoder timing bound: CD74HC154 (TI) propagation address->output and enable->output, CL = 50 pF, VCC = 2 V:
175 ns (25 C), 220 ns (-40..85 C), **265 ns (-55..125 C)** max; 35/44/53 ns at 4.5 V (HC data sheet,
switching specifications). VCC = 3.3 V lies between the two tabulated supplies, so 265 ns is a safe upper bound.
**OPEN-H2:** the fitted part is Nexperia 74HC154PW; confirm its 2.0 V column is not slower than the TI figure
(Nexperia site timed out from this session).

Address-line faults (stuck CSAx, swapped lines) are not prevented by this sequence; they are caught by the
per-device signature check in `03` section 9 (0043 4.4).

### 2.4 TMP126 frame (bit-banged, all boards)

Hardware SPI is disabled during the frame (SPCR.SPE = 0, so PB5/PB7 are plain port pins; their DDR bits stay
output). SCLK idles high. Timing values are the minimums the firmware must respect; the source column is the
binding constraint.

TMP126 bus rules (TMP 8.5.2): data clocked **in on the rising** SCLK edge, **out on the falling** edge; the
first 16 bits are the command word; on a read the TMP126 drives SIO after the command word; the host drives
SIO for the whole write. U411 74LVC1G125 drives DIN_ISO onto SIO through R446 220R only while SIO_WR_N is low
(D41 D1).

Read frame (command + 1 data word + CRC = 48 clocks):

```
R1  check: no AD7124 selected; SPE = 0; SCK (PB7) = 1
R2  select TMP126 (direct: CS_CJx = 0; 40-ch: section 2.3 steps 1-6 with n = 6 + j - 1)
R3  wait >= 1 us                                   tLEAD 100 ns (TMP 7.6) + isolator skew
R4  SIO_WR_N = 0 ; wait >= 1 us                    U411 enable: isolator 13 ns + ten <= 10.4 ns (LVC)
R5  for bit = 15 .. 0 of the command word:
        SCK = 0 ; MOSI = bit ; wait >= 1 us        tSU 10 ns (TMP 7.6)
        SCK = 1 ; wait >= 1 us                     TMP126 samples on this rising edge; tHOLD 20 ns
R6  after the 16th rising edge (SCK still high):
        wait >= 1 us                               hold of bit 0 (tHOLD 20 ns)
        SIO_WR_N = 1 ; wait >= 1 us                driver off before the TMP126 drives SIO:
                                                   isolator 13 ns + tdis <= 9.3 ns (LVC, worst column)
R7  for 32 bits (16 data, MSB first, then 16 CRC):
        SCK = 0 ; wait >= 2 us                     TMP126 drives on this falling edge, tVALID 35 ns;
                                                   + reverse isolator 13 ns + R405 2k2 x ~15 pF (~35 ns)
        sample MISO (PB6)
        SCK = 1 ; wait >= 1 us
R8  wait >= 1 us ; deselect (CS_CJx = 1 / 40-ch: CS_EN = 1) ; wait >= 1 us
```

Write frame: identical R1-R4, then 32 bits (command + data) or 48 bits (command + data + CRC) all driven by
the host as in R5; **SIO_WR_N stays low through command, data and CRC** (D41 firmware requirements; R447 would
otherwise pull the bus high), then SIO_WR_N = 1, R8.

Resulting rates: ~3-4 us per bit -> ~170 us per 48-bit frame; far below the TMP126 fCLK max 10 MHz (TMP 7.6).
TMP126 edge requirement tRISE/tFALL <= 100 ns (TMP 7.6) is met by the driver, not by the clock rate:
~19 ns at 85 pF, ~40 ns at 180 pF (C 8.5). Contention if firmware breaks rule 3: ~13 mA limited by R446 (C 8.5) -
a firmware fault, must never happen; host test for `iso_spi` checks the ordering.

## 3. SPI to the AD7124 (hardware SPI, all boards)

| Item | Value | Source |
|---|---|---|
| Mode | **3** (CPOL = 1, CPHA = 1): MCU sets up on the falling edge, samples on the rising edge | AVR Table 18-2; AD7124 shifts DOUT on SCLK falling and latches DIN on rising (ADC Rev B Table 3, timing diagrams p.11) |
| Bit order | MSB first (DORD = 0) | ADC Rev B serial interface |
| SCLK limit of the AD7124 | high and low pulse >= 100 ns each (t3, t4) -> <= 5 MHz | ADC Rev B Table 3 |
| SCLK chosen | **1 MHz default** (SPI2X = 1, SPR1:0 = 01 -> fosc/8) | AVR Table 18-5 |
| SCLK maximum allowed | **2 MHz** (SPI2X = 0, SPR1:0 = 00 -> fosc/4), only after a bench scope check of MISO at the MCU pin | budget below |
| SPCR (1 MHz) | `0x5D` = SPE(6) | MSTR(4) | CPOL(3) | CPHA(2) | SPR0(0) ; SPSR.SPI2X = 1 | AVR 18.5.1, 18.5.2 |
| SPCR (2 MHz) | `0x5C` ; SPSR.SPI2X = 0 | AVR 18.5.1 |

Read-path budget (DOUT must be valid at the MCU before the rising edge, i.e. within half a period after the
falling edge):

| Contribution | Max | Source |
|---|---|---|
| SCK falling -> island SCLK (U403 forward) | 13 ns | ISO 6.10 |
| AD7124 SCLK active edge -> DOUT valid (t2) | 80 ns | ADC Rev B Table 3 (specified at 25 pF) |
| Extra for the real DOUT_ISO bus load (62-85 pF 24-ch, ~180 pF Astra; ~300 pF 40-ch, C 8.5/10.5) | ~40 ns 24-ch, ~70 ns 40-ch (estimate, R_out ~200 ohm) | **OPEN-H3**: no AD7124 output-impedance figure; measure |
| U403 reverse channel | 13 ns | ISO 6.10 |
| R405 2k2 into MISO (~15 pF): to VIH 0.6 VCC = 0.92 tau | ~30 ns | R405 value M24 `c_iso.py` |
| MCU MISO setup before sampling edge | 10 ns | AVR Table 28-15 item 4 |
| **Total** | **~186 ns (24-ch), ~216 ns (40-ch)** | |

Half period: 250 ns at 2 MHz (margin ~35-65 ns), 500 ns at 1 MHz (margin > 280 ns), 125 ns at 4 MHz (fails).
Write path (MOSI and SCLK through the same isolator): AD7124 needs DIN setup 30 ns (t8) and hold 25 ns (t9)
(ADC Rev B Table 3); MOSI changes half a period before the rising edge; skew between two channels of one
isolator <= tsk(o) 2.5 ns (ISO 6.10). OK at both clocks.

Cost of 1 MHz instead of 2 MHz: a 5-byte transaction (command + 3 data + CRC) takes 40 us instead of 20 us;
per scan per bank ~60 transactions -> +1.2 ms. Negligible against C 9.7 (700 ms cycle).

## 4. Timers

### 4.1 Allocation

| Timer | Use | Interrupt | Notes |
|---|---|---|---|
| Timer0 | RUN_PERMIT charge-pump square wave on OC0A (PB3) **only** | none | 0043 3.6 / I-104: nothing else on this timer |
| Timer1 | free-running 1 MHz time base for short measured intervals (slot period, TMP126/ADC timeouts) | none | optional; CS waits use busy-wait |
| Timer2 | 1 ms tick (`ms_tick`) and the RUN deadline countdown | OCIE2A | never feeds the watchdog (I-119) |
| Watchdog | system reset, section 5 | none (WDTON) | |

### 4.2 Timer0 - charge pump (OC0A, PB3)

Requirement: square wave >= 1 kHz (0043 3.6; C 8.5: gate ~1.4-2.9 V at 100 Hz - not enough; 3.8-4.1 V at 1 kHz;
4.1-4.2 V at 2 kHz). Chosen **2.000 kHz**, 50 % duty, CTC toggle:

| Register | Value | Meaning | Source |
|---|---|---|---|
| OCR0A | `249` (0xF9) | f = fclk / (2 x N x (1 + OCR0A)) = 8 MHz / (2 x 8 x 250) = 2000 Hz | AVR 15.7.2 (CTC frequency) |
| TCCR0A | `0x42` | COM0A1:0 = 01 (toggle OC0A on compare match), WGM01:0 = 10 (CTC with WGM02 = 0) | AVR Table 15-2, Table 15-8 |
| TCCR0B | `0x02` | WGM02 = 0, CS02:0 = 010 (clk/8) | AVR Table 15-9 |
| TIMSK0 | `0x00` | no Timer0 interrupts | |
| DDRB3 | 1 | OC0A output needs the DDR bit set | AVR 15.6 |

Start pump: `TCNT0 = 0; OCR0A = 249; TCCR0A = 0x42; TCCR0B = 0x02`.
Stop pump (any trip, deadline expiry, fault): `TCCR0A = 0x00` (OC0A disconnected, pin returns to PORTB3),
`PORTB3 = 0`, `TCCR0B = 0x00`. The relay gate decays to 1 V in ~15-30 ms after the drive stops (C 8.5).
Check on the bench: 2 kHz gate voltage at minimum 5 V (C 8.5 "Measure the gate at the bench").

RUN deadline (0043 3.6, I-118): `run_deadline_ms` is reloaded **only** by the scan-completion path when a
validated board scan is published and protection permits RUN; the Timer2 ISR decrements it and calls the stop
sequence above when it reaches 0. Reload value **900 ms** (decided, `04` 6.1; re-checked against the measured scan time) (cycle ~700 ms, C 9.7; trip budget 1 s,
GOAL). The ISR can only remove RUN, never start the pump. **OPEN-H4:** reload value to be fixed in `04` with
the measured scan time.

### 4.3 Timer2 - 1 ms tick

| Register | Value | Meaning | Source |
|---|---|---|---|
| ASSR | `0x00` | synchronous clock (AS2 = 0) | AVR 17.9 |
| TCCR2A | `0x02` | WGM21:0 = 10, CTC; OC2A/OC2B disconnected | AVR 17.11 |
| TCCR2B | `0x04` | CS22:0 = 100 -> clkT2S/64 = 125 kHz | AVR Table 17-9 |
| OCR2A | `124` | 125 kHz / 125 = 1000 Hz | |
| TIMSK2 | `0x02` | OCIE2A | |

ISR work is bounded: `ms_tick++`, RUN deadline countdown, nothing else.

### 4.4 Timer1 - 1 us time base (optional)

TCCR1A = 0x00, TCCR1B = 0x02 (normal mode, clk/8 = 1 MHz), no interrupts; 16-bit wrap 65.536 ms, so only for
intervals < 60 ms (one ADC slot is ~42-45 ms).

## 5. Watchdog

| Item | Value | Source |
|---|---|---|
| Mode | System Reset only; WDTON fuse programmed locks WDE = 1, WDIE = 0 | AVR 11.3.2, Table 11-1 |
| Timeout | **WDP3:0 = 0100, 32K cycles, 0.25 s typical at 5 V** | AVR Table 11-2 |
| Why not 0.5 s (0101) | 0043 asks <= 0.5 s; the 128 kHz WDT oscillator is given only as typical with characterisation graphs (AVR Figures 30-381/382), no min/max. 0.25 s typical keeps the real timeout under 0.5 s even with a 50 % slow oscillator. | **OPEN-H5**: measure the WDT timeout on the first boards (service mode), confirm < 0.5 s hot and cold |
| Change sequence | write `WDCE | WDE` (0x18), then within 4 cycles `WDE | WDP2` (0x0C) with WDCE = 0, one operation each, interrupts off | AVR 11.3.2 steps 1-2, 11.4.2 |
| Default after reset with WDTON | WDP = 0000 -> 2K cycles, **16 ms typical** | AVR 11.4.2 initial value 0, Table 11-2 |
| Feeding | `wdr` only in the main loop, only when acquisition progress counter (slot results accepted, or init steps completed) advanced since the last feed; never from an ISR | 0043 3.6, I-119 |

Consequence of the 16 ms reset default: the watchdog must be set (or fed) before the C runtime clears 16 KB of
RAM. Section 8 S0 does it in `.init3`.

## 6. Fuses (ATmega1284P, 8 MHz crystal)

"0" = programmed (AVR 27.2). Values:

| Byte | Value | Bits |
|---|---|---|
| **lfuse** | **`0xF7`** | CKDIV8 1, CKOUT 1, SUT1 1, SUT0 1, CKSEL3..0 0111 |
| **hfuse** | **`0xC1`** | OCDEN 1, JTAGEN 1, SPIEN 0, WDTON 0, EESAVE 0, BOOTSZ1 0, BOOTSZ0 0, BOOTRST 1 |
| **efuse** | **`0xFC`** | bits 7-3 unused (1), BODLEVEL2..0 = 100 |
| lock | `0xFF` | prototypes; production lock is an owner decision (keep readable for field diagnosis, as `firmware/fuses.md` argues) |

Low fuse (AVR Table 27-5):

| Bit | Fuse | Value | Why |
|---|---|---|---|
| 7 | CKDIV8 | 1 | no /8: F_CPU = 8 MHz (factory default is programmed -> 1 MHz) |
| 6 | CKOUT | 1 | no clock on PB1 (PB1 = CS_ADC3 / CSA1) |
| 5:4 | SUT1:0 | 11 | with CKSEL0 = 1: "crystal oscillator, slowly rising power", 16K CK + 14 CK + 65 ms (AVR Table 9-6) |
| 3:0 | CKSEL3:0 | 0111 | **full-swing crystal oscillator** 0.4-20 MHz (CKSEL3..1 = 011, AVR Table 9-5), "useful ... in noisy environments" (AVR 9.4); C501/C502 22 pF inside the 12-22 pF range (AVR Table 9-6 guidance) |

Rejected: low-power crystal oscillator CKSEL 1111/1101 (AVR 9.3: "may be more susceptible to noise in noisy
environments"); internal RC (Modbus and timing accuracy).

High fuse (AVR Table 27-4):

| Bit | Fuse | Value | Why |
|---|---|---|---|
| 7 | OCDEN | 1 | on-chip debug off (AVR: never ship with OCDEN programmed) |
| 6 | JTAGEN | 1 | **JTAG off**: PC2-PC5 are RUN_SENSE and chip selects (factory default is programmed = JTAG on) |
| 5 | SPIEN | 0 | ISP enabled (cannot be changed over ISP anyway, AVR Table 27-4 note 1) |
| 4 | WDTON | 0 | **watchdog always on**, System Reset mode (AVR 11.3.2) |
| 3 | EESAVE | 0 | EEPROM kept through chip erase: re-flashing keeps settings and calibration |
| 2:1 | BOOTSZ1:0 | 00 | factory value; no boot loader, irrelevant while BOOTRST = 1 |
| 0 | BOOTRST | 1 | reset vector at 0x0000 |

Extended fuse (AVR Table 27-3, Table 28-13):

| BODLEVEL2:0 | VBOT min / typ / max | Use |
|---|---|---|
| 111 | disabled | - |
| 110 | 1.7 / 1.8 / 2.0 V | - |
| 101 | 2.5 / 2.7 / 2.9 V | - |
| **100** | **4.1 / 4.3 / 4.5 V** | **chosen** |

The MCU runs from the regulated +5 V (LM5164 output 4.9996 V, V_REF tolerance +-1.5 % -> >= 4.92 V, C 1.3); BOD
max 4.5 V stays below it, and 4.1 V min keeps the MCU in reset well above its 2.7 V / 10 MHz operating limit
and before the 5 V relays and LCD misbehave. BOD hysteresis 50 mV, minimum pulse 2 us (AVR Table 28-12).

Firmware self-check: at start-up read the three fuse bytes from software (AVR 26.8.9 "Reading the Fuse and Lock
Bits from Software", Z = 0x0000 low, 0x0003 high, 0x0002 extended) and compare with the masks
`lfuse == 0xF7`, `hfuse == 0xC1`, `efuse & 0x07 == 0x04`. Mismatch -> fault **G15** (`03` fault table), RUN
never granted. Cheap, and it catches a unit programmed without WDTON/BOD (0036 D5 relied on the production
test for exactly this).

## 7. Programming (USBasp, avrdude)

ATmega1284P signature: `0x1E 0x97 0x05` (AVR 27.3, Table 27-6; the non-P ATmega1284 is
0x1E9706). A factory chip runs at 1 MHz (internal RC with CKDIV8), so ISP SCK must be slow until the fuses are
set (ISP SCK < fCPU/4).

```
# 1. identify + read factory fuses (slow ISP clock)
avrdude -c usbasp -p m1284p -B 32 -U lfuse:r:-:h -U hfuse:r:-:h -U efuse:r:-:h -U lock:r:-:h

# 2. write fuses (board must have Y501 fitted - with CKSEL 0111 and no crystal the chip stops)
avrdude -c usbasp -p m1284p -B 32 -U lfuse:w:0xF7:m -U hfuse:w:0xC1:m -U efuse:w:0xFC:m

# 3. flash (8 MHz now; avrdude verifies after writing by default)
avrdude -c usbasp -p m1284p -B 4 -U flash:w:thermo<BOARD>.hex:i

# 4. read back and compare (the record of the unit)
avrdude -c usbasp -p m1284p -B 4 -U lfuse:r:-:h -U hfuse:r:-:h -U efuse:r:-:h -U lock:r:-:h
```

Expected read-back: lfuse `0xf7`, hfuse `0xc1`, efuse `0xfc` (some avrdude versions mask the unused efuse bits
and print `0x4`: compare `efuse & 0x07 == 0x04`), lock `0xff`. `program.ps1` must be rewritten for `-p m1284p`
and these values (I-119: today it is ATmega32 only). Programming order matters only for the clock: fuses before
relying on 8 MHz. Once WDTON is set an empty or wrong image resets every 16 ms; ISP still works (RESET held low).
**OPEN-H6:** `-B` values are USBasp bit-clock periods in us; confirm `-B 4` is reliable through J501 on the
board (2k2 R405 on MISO).

## 8. Start-up order (reset -> first validated scan)

All outputs safe throughout: RUN pump off (PB3 static low or floating), ALARM relay off, RS-485 receive,
every island device deselected, SIO_WR_N high. The protection latch starts latched (`START: ACK REQUIRED`,
0043 3.5) - this sequence never closes RUN by itself.

| Step | Action | Time bound |
|---|---|---|
| S0 (`.init3`, before .data/.bss init) | `cli`; `wdr`; copy MCUSR to a `.noinit` byte, MCUSR = 0; WDT timed sequence -> WDP = 0100 (0.25 s) (section 5); MCUCR.JTD = 1 written twice within 4 cycles (AVR 25.8.1); PORTB3 = 0, DDRB3 = 1 | < 20 cycles; must finish inside the 16 ms default timeout |
| S1 | C runtime: .data copy, .bss clear (16 KB) | ~ few ms at 8 MHz, < 0.25 s |
| S2 | GPIO per section 1 (PORT then DDR): CS / CS_EN / SIO_WR_N high, RUN low, ALARM low, DE low, REFTEST low, SCK high, LCD low, button and unused pull-ups | us |
| S3 | read fuses from software, check (section 6); fail -> G15, continue in fault | us |
| S4 | Timer2 tick (4.3), Timer1 (4.4), `sei` | |
| S5 | SPI init: PB4 already output (rule from AVR 18.3), SPCR/SPSR per section 3 | |
| S6 | USART0 init, DE low (section 9) | |
| S7 | LCD init (HD44780: wait >= 40 ms after VCC; module data sheet - `06`); feed WDT between init steps | |
| S8 | read settings and calibration (`05`); invalid -> config lock | EEPROM read only |
| S9 | island bring-up: per AD7124 reset + ID (`03` 2.2) - retry every 10 ms until all respond or 500 ms elapsed (island DC-DC + LDO start, C 9.2 "UNVERIFIED") | <= 500 ms; feed WDT per attempt as init progress |
| S10 | AD7124 configuration, CRC on, readback (`03` 2.2-2.4) | |
| S11 | AD7124 internal calibrations (`03` 2.5) | ~ 2 x 45 ms per setup calibrated, all banks in parallel |
| S12 | TMP126 configuration and signature writes (`03` 6.2); wait >= 7.5 ms (tCONV max, TMP 7.5) | |
| S13 | device signatures written and read back (`03` 9) | |
| S14 | REFTEST self-test (section 10) | ~ 20 ms |
| S15 | first board scan (`03` 7): all slots, CJ, signatures, REFOK | ~ 0.7 s |
| S16 | publish first validated board scan to `protection`; RUN stays open until ACK rules of `04` pass | |

Any failure in S9-S15 raises its fault code (`03` section 11) and the loop keeps scanning; recovery is
automatic when a later scan validates (RUN still needs ACK).

MCUSR flags (AVR 25.8.2: JTRF, WDRF, BORF, EXTRF, PORF) are passed to `events` as the start-up cause.

## 9. UART / RS-485 (USART0)

| Item | Value | Source |
|---|---|---|
| Pins | RXD0 PD0, TXD0 PD1, DE PD7 (DE and /RE tied, R733) | M24 `c_out.py` |
| Baud | UBRR0 = 51 (9600, error 0.2 %) or 25 (19200, 0.2 %), U2X0 = 0 | AVR Table 19-9 (8.0000 MHz column); UBRR = fosc/(16 baud) - 1 |
| Frame | UCSR0C = 0x06 (8N1, service report) or 0x26 (8E1); Modbus framing is `07`'s | AVR 19.11 |
| DE on | PD7 = 1, then wait >= 2.5 us before the first start bit (ADM2587E driver enable time tZH/tZL max 2.5 us) | 485 Table 3 |
| DE off | after the last byte: wait for TXC0 (stop bit shifted out, AVR 19.7), then PD7 = 0 (disable 200 ns max) | AVR 19.7, 485 Table 3 |
| Echo | none: receiver disabled while DE is high (/RE tied); RxD high-Z then, R738 holds PD0 high | `c_out.py` R738 note |
| Reset / ISP | R737 pulls DE low: the bus is released while the MCU is in reset | `c_out.py` |

RS-485 is never in the trip path (0031 D7).

## 10. Engine reference (REFOK / REFTEST) - interface part

* REFOK (PA2) sampled once per board scan outside a self-test window; high -> **G08** (0043 4.3). Debounce:
  none in firmware - the hardware has 100 nF on the 1 M sense node (`c_iso.py` C419, R422) and 1 M hysteresis
  (R442, ~20 mV).
* REFTEST self-test (0043 4.3; 0032 rev 4 item 3): at start-up (S14) and every **N = 10 min (decided 2026-10-20,
  OPEN-H7, `04`)**:
  1. REFOK must read low (connected) before the test, else G08 (no self-test on a broken wire).
  2. REFTEST = 1; wait **>= 5 ms** (R425 1k into C419 100 nF: tau 0.1 ms; comparator and isolators ns).
  3. REFOK must read **high**; else **G09** (comparator, isolator or REFOK path stuck low).
  4. REFTEST = 0; wait **>= 20 ms** (recharge through R421 10k + feed 2 x 4.99k into 100 nF: tau ~2 ms).
  5. REFOK must read **low** again; else G08.
  During steps 2-5 the scan does not evaluate REFOK. **OPEN-H7:** both waits from RC estimates; confirm on the
  bench (I-120 cut FEED / cut SENSE).

## 11. Power loss and island loss

| Event | What the hardware does | What firmware does |
|---|---|---|
| +5 V sags below VBOT (4.1-4.5 V) | BOD reset (AVR Table 28-13): pins tri-state -> pump stops -> trip relay drops in ~15-30 ms (C 8.5); alarm relay drops | restart at S0; MCUSR.BORF logged; starts latched |
| Watchdog timeout | reset as above | MCUSR.WDRF logged; starts latched (0043 3.5) |
| Island supply lost (DC-DC or LDO) | every reverse isolator output defaults **high** (0036 D3, CA-IS3761 "H" variant): MISO reads all 1s, REFOK reads high | REFOK high -> G08; every AD7124/TMP126 transaction fails CRC/ID -> bank faults on all banks in the same scan -> **G14 island power lost**; RUN deadline expires; scanning continues |
| Island supply returns | AD7124s power up with reset registers: **CRC disabled**, POR_FLAG = 1 (ADC Rev B STATUS) | first STATUS read showing POR_FLAG = 1 on any ADC, or recovery from G14 -> **full re-init of every island device** (S9-S14), then RUN inhibited until a fresh fully validated board scan (0043 4.4) and the ACK rules of `04` |
| One isolator's island side lost (cannot happen alone on 24-ch: all share +3V3_ISO) | its forward outputs to the island are undefined | treated as island loss by the same checks |
| +5 V lost entirely | MCU off, all relays drop | power-up path |

**OPEN-H8:** CA-IS3761 default-output behaviour when the *output* side is powered but the *input* side is not,
and the time to default (tDO 8/12 in 6.10, unit not legible in the local text) - read the English data sheet.

## 12. OPEN items (this file)

| ID | What | Needed |
|---|---|---|
| A1 | all AD7124 citations are Rev B (Chinese edition) page/table numbers | re-cite against the current English AD7124-8 data sheet |
| H1 | CA-IS3761 output level with its input floating (MCU in reset) | English CA-IS3761 data sheet / bench |
| H2 | Nexperia 74HC154 timing at 2 V (TI CD74HC154 used as bound) | Nexperia 74HC_HCT154 data sheet |
| H3 | AD7124 DOUT edge on the real bus capacitance (read-path budget) | scope MISO at 2 MHz on the first boards; until then 1 MHz |
| H4 | RUN deadline 900 ms decided (`04` 6.1); re-check against the measured scan time (P15) | first boards |
| H5 | real WDT timeout (0.25 s typ chosen so it stays < 0.5 s) | measure hot and cold in service mode |
| H6 | USBasp `-B` value through J501 / R405 | first programming session |
| H7 | REFTEST waits (5 ms / 20 ms); interval N = 10 min decided | bench, I-120 cut FEED/SENSE |
| H8 | CA-IS3761 default-output timing (tDO) and input-side-unpowered behaviour | English data sheet |
