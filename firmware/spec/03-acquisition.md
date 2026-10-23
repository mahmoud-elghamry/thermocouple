# 03 - Acquisition (adopted 2026-10-20 from the research draft; fault codes and cross-references aligned with `04`; OPEN items at the end)

Status: draft research input for `firmware/spec/03-acquisition.md` (2026-10-20). Register values are derived
from the cited data-sheet fields; anything not confirmed from a source is **OPEN**. Conventions:
`00-overview.md` (channels 1..N, bank b holds 8b+1..8b+8 with b = 0..4 = A..E, `temp_dC`, `emf_nV`, Bnn/Cnn/Gnn).
Decided behaviour: `docs/decisions/0043` rev 2, sections 3.1, 3.4, 4.1-4.5. Source tags as in `02` section 0
(ADC = AD7124-8 **Rev B**, page/table numbers of Rev B - see OPEN-A1 in `02`).

Numbers marked *provisional* are thresholds that 0043 says come from the bench; they are starting values for
the first boards, not requirements derived from data-sheet typicals (owner rule).

## 1. Banks and devices

| Board | TC banks (AD7124-8) | TMP126 | Other | CS |
|---|---|---|---|---|
| 8-ch | 1 (A) | 2 | - | direct |
| 24-ch | 3 (A-C) | 6 | - | direct |
| 40-ch | 5 (A-E) | 10 | RTD AD7124-8 (3 x PT100 + 150R check), channels 41-43 | 74HC154 |

TC bank pin use (M24 `c_bank.py`): channel k (k = 0..7 inside the bank) on AIN(2k) = TC+ side (TCn_PA) and
AIN(2k+1) = TC- side (TCn_NA); REFIN1(+) = VREF_EXT (REF3030, 3.0 V), REFIN1(-) = GND_ISO; REFIN2 unused (all
AIN used, D41); TMP126 #0 at header J(100b+1) (channels 1-4 of the bank), #1 at J(100b+2) (channels 5-8).

## 2. AD7124 register configuration (TC banks)

Frame format (ADC Rev B COMMS register, Table 64, p.77): command byte `WEN(7)=0 | R/W(6) | RS[5:0]`, i.e.
write = `0x00 | addr`, read = `0x40 | addr`, then MSB-first data. **CRC** (ADC Rev B p.67-68): CRC-8,
polynomial x^8 + x^2 + x + 1 (0x07), initial value 0, computed over the command byte and the data; appended by
the host on writes and by the ADC on reads. Data-sheet example: data 0x654321 -> 0x86 (reproduced). CRC is
enabled by ERROR_EN.SPI_CRC_ERR_EN and is **off after every reset/POR** (0032 rev 3).

Test vectors (computed with the algorithm above, for host tests): write ERROR_EN 0x47FAFE: bytes
`07 47 FA FE` CRC `0x90`; write ADC_CONTROL 0x0748: `01 07 48` CRC `0xFF`; write ADC_CONTROL 0x0744: CRC `0xDB`;
write CONFIG_0 0x0875: `19 08 75` CRC `0x7C`; read ID returning 0x12: `45 12` CRC `0x64`; 0x14: CRC `0x76`.

### 2.1 Register images

| Reg | Addr | Size | Value | Fields (ADC Rev B) |
|---|---|---|---|---|
| ADC_CONTROL | 0x01 | 16 | **0x0748** standby / **0x0744** single conversion / 0x0754 internal zero-scale cal / 0x0758 internal full-scale cal | DOUT_RDY_DEL 0; CONT_READ **0**; DATA_STATUS **1** (status byte appended to DATA); CS_EN **1** (DOUT keeps the last bit until CS high; required for SPI_READ/WRITE/SCLK_CNT checks); REF_EN **1** (internal 2.5 V on, 0043 4.1); POWER_MODE **01** mid; Mode 0010 standby / 0001 single / 0101 / 0110; CLK_SEL **00** internal 614.4 kHz, not output (Table 66 p.78, Table 67 p.79) |
| IO_CONTROL_1 | 0x03 | 24 | **0x000000** | no IOUT, PDSW off, GPIO off (AIN2-AIN5 stay analog) (Table 68 p.80-82) |
| IO_CONTROL_2 | 0x04 | 16 | **0x0000** | no internal VBIAS: the board biases inputs to V_BIAS (Table 69 p.82) |
| ERROR_EN | 0x07 | 24 | **0x47FAFE** | MCLK_CNT_EN, ADC_CAL/CONV/SAT_ERR_EN, AINP/AINM OV/UV_EN, REF_DET_ERR_EN, DLDO/ALDO_PSM_ERR_EN, SPI_IGNORE/SCLK_CNT/READ/WRITE/CRC_ERR_EN, MM_CRC_ERR_EN; trip-test and LDO_CAP_CHK bits 0 (Table 71 p.84). Reset value 0x000040 |
| CHANNEL_0..14 | 0x09-0x17 | 16 | section 3 | Enable(15), Setup(14:12), AINP(9:5), AINM(4:0) (Table 73 p.86-87). Stored **disabled**; enabled one at a time (section 4) |
| CHANNEL_15 | 0x18 | 16 | 0x0001 | reset value, disabled; read back only |
| CONFIG_0 | 0x19 | 16 | **0x0875** | TC: Bipolar 1, Burnout 00, REF_BUFP/M 0, AIN_BUFP/M 1, REF_SEL 10 internal, PGA 101 = 32 (+-78.125 mV) (Table 74 p.88) |
| CONFIG_1 | 0x1A | 16 | **0x0A75** | TC + burnout: as CONFIG_0 with Burnout **01 = 0.5 uA** (0032: 1.6 ms to charge 10.5 nF to full scale at 0.5 uA) |
| CONFIG_2 | 0x1B | 16 | **0x0840** | REF check: Bipolar, REF_SEL 00 = REFIN1 (REF3030), REF buffers off, AIN_BUFP 1, AIN_BUFM 0 (AINM = AVSS), PGA 1 |
| CONFIG_3 | 0x1C | 16 | **0x0810** | Bipolar, internal ref, AIN buffers off, PGA 1 (AVDD/6) |
| CONFIG_4 | 0x1D | 16 | **0x0818** | Bipolar, REF_SEL 11 = AVDD, buffers off, PGA 1 (common-mode check, ratiometric to AVDD) |
| CONFIG_5 | 0x1E | 16 | **0x0810** | Bipolar, internal ref, **AIN buffers off**, PGA 1 (20 mV at gain 1, gain-ratio partner of CONFIG_0). ADI does not allow buffered gain-1 internal signals (AD7124 Rev F, Signal Chain Check, p.68); the AINM undervoltage flag that the internal 20 mV signal raises is ignored in **both** slots that measure it (10 and 11), independent of gain; all other checks stay |
| CONFIG_6, 7 | 0x1F, 0x20 | 16 | 0x0860 | reset value, unused, read back |
| FILTER_0..5 | 0x21-0x26 | 24 | **0xE60180** | Filter 111 = post filter, REJ60 0, POST_FILTER **011 = 25 SPS** (62 dB at 50/60 Hz +-1 Hz), SINGLE_CYCLE 0, FS left at reset 0x180 (Table 75 p.89, Table 62 p.64). **OPEN-Q1:** confirm FS is ignored when Filter = 111 |
| FILTER_6, 7 | 0x27, 0x28 | 24 | 0x060180 | reset, unused |
| OFFSET_0..5 | 0x29-0x2E | 24 | from calibration (2.5) | reset 0x800000 (p.90) |
| OFFSET_7 | 0x30 | 24 | device signature (section 9) | setup 7 is never selected |
| GAIN_0..5 | 0x31-0x36 | 24 | factory (gain 1) or calibrated (gain 32) | reset 0x5XXXXX = factory gain-1 calibration (p.90) |
| ID | 0x05 | 8 | check, section 2.3 | Rev B reset value **0x12** (p.83) |
| MCLK_COUNT | 0x08 | 8 | read only | Table 72 p.85 |
| ERROR | 0x06 | 24 | read only, section 5 | Table 70 p.83 |

Settling time used everywhere: post filter 25 SPS, **tSETTLE = 42.331 ms in mid power** (41.831 full, 42.995
low) (ADC Rev B Table 61 p.61); with a -5 % internal clock 44.559 ms (C 9.7). **OPEN-Q2:** cite the internal
clock tolerance (+-5 % assumed by C 9.7) from the English data sheet.

### 2.2 Bring-up of one ADC (after island power is present)

```
A1  reset: CS low, 64 SCLK with DIN = 1 (8 bytes 0xFF), CS high          (ADC Rev B p.48)
A2  wait >= 2 ms                                                          OPEN-Q3: Rev B p.48 shows "2 ms"
                                                                          next to reset/POR; confirm wording
A3  read STATUS (0x40), no CRC yet: POR_FLAG (bit 4) must be 1           (Table 65 p.77)
A4  read ID (0x45), no CRC: check section 2.3
A5  write ERROR_EN = 0x47FAFE (sent without CRC: CRC is not on yet)
A6  from here every transaction carries CRC; read ERROR_EN back -> 0x47FAFE
A7  write ADC_CONTROL = 0x0748, IO_CONTROL_1/2, CONFIG_0..5, FILTER_0..5, CHANNEL_0..14 (disabled images),
    OFFSET_7 signature
A8  read back every register written in A7 (and CHANNEL_15, CONFIG_6/7, FILTER_6/7, GAIN_0..5) and compare;
    capture GAIN_0..5 as read (factory values) for later comparison
A9  read ERROR: expected 0x000000 (bits that are set by the reset itself - OPEN-Q4 - cleared by this read)
A10 calibrate (2.5), then capture OFFSET_0..5 and GAIN_0..5 as the per-ADC expected images
```

A failure in A3-A10 is retried twice (whole sequence from A1); then the bank is faulted (B01/B02/B03).

### 2.3 ID check

ID = 0x12 in Rev B (p.83). The register is device ID in bits 7:4 and silicon revision in bits 3:0 (assumption
from the 0x12 value and AD7124 driver practice). Rule: `ID[7:4] == 0x1` (AD7124-8) **and** `ID[3:0]` in a
build-time whitelist {0x2, 0x4, 0x6, 0x7} (Rev B 0x12; Rev F documents 0x17 for current silicon). The revision
read on the first boards is recorded; an ID outside the list -> B01. **OPEN-Q5** closes when the first boards'
ID is logged.

### 2.4 Status byte (DATA_STATUS = 1)

DATA reads return 24 data bits + STATUS + CRC (5 bytes after the command). STATUS (Table 65 p.77): RDY(7) 0 =
new data, ERROR_FLAG(6), POR_FLAG(4), CH_ACTIVE(3:0). Every result is accepted only if: CRC good,
POR_FLAG = 0, CH_ACTIVE = the slot that was started (section 4). ERROR_FLAG = 1 -> read ERROR (section 5).

### 2.5 Calibration (start-up)

* Gain-32 setups: CONFIG_0 (TC). Sequence per ADC, all banks in parallel: enable only CHANNEL_0 (setup 0);
  write OFFSET_0 = 0x800000; ADC_CONTROL = 0x0758 (internal full-scale), wait RDY (STATUS poll, timeout
  200 ms); ADC_CONTROL = 0x0754 (internal zero-scale), wait RDY (200 ms); ADC_CONTROL = 0x0748; read OFFSET_0,
  GAIN_0; copy both to OFFSET_1/GAIN_1 (same PGA, CONFIG_1 differs only by burnout); disable CHANNEL_0.
  Data formula with these registers: ADC Rev B p.51.
* Gain-1 setups (2, 3, 4, 5): factory GAIN, OFFSET left 0x800000 - their checks have wide windows.
* ERROR.ADC_CAL_ERR after either step -> B04. Sanity: |OFFSET_0 - 0x800000| <= 0x010000 and GAIN_0 within
  +-2 % of the factory GAIN_0 captured in A8 (*provisional*), else B04.
* **OPEN-Q6:** confirm in the English data sheet ("Calibration" section): (a) full-scale before zero-scale and
  OFFSET reset to 0x800000 first; (b) internal full-scale calibration allowed at gain 32 in mid power; (c)
  calibration duration (timeout); (d) that the uncalibrated gain error at gain 32 justifies it (Rev B p.51 shows
  "-0.3 %" before and "+-0.0025 %" after - typicals).
* No periodic recalibration in v1: drift is caught by the REF, zero, non-zero and gain-ratio slots.

## 3. Slot schedule (15 slots per TC bank)

0043 4.2, C 9.7. CHANNEL_s holds slot s. Rotation indices per board scan number n: burnout channel
`kb = n mod 8`, common-mode input `i = n mod 16`, zero pin fixed (AIN1).

| Slot | Purpose | Setup | AINP | AINM | CHANNEL_s (disabled image; enable = OR 0x8000) |
|---|---|---|---|---|---|
| 0-7 | TC channel k = s | 0 | AIN(2k) | AIN(2k+1) | k0 0x0001, k1 0x0043, k2 0x0085, k3 0x00C7, k4 0x0109, k5 0x014B, k6 0x018D, k7 0x01CF |
| 8 | REF cross-check: internal 2.5 V against REF3030 | 2 | 10010 internal ref | 10001 AVSS | 0x2251 |
| 9 | zero: AIN1 against itself (same pin both inputs), TC gain path | 0 | AIN1 | AIN1 | 0x0021 |
| 10 | non-zero: internal 20 mV at gain 32 | 0 | 11100 V_20MV_P | 11101 V_20MV_M | 0x039D |
| 11 | gain-ratio partner: same 20 mV at gain 1 | 5 | 11100 | 11101 | 0x539D |
| 12 | AVDD/6 | 3 | 10100 (AVDD-AVSS)/6+ | 10101 (AVDD-AVSS)/6- | 0x3295 |
| 13 | common mode, rotating input i (AIN i vs AVSS, ratio to AVDD) | 4 | AIN(i) | 10001 AVSS | 0x4011 OR (i << 5): i0 0x4011 ... i15 0x41F1 |
| 14 | burnout, rotating channel kb | 1 | AIN(2kb) | AIN(2kb+1) | 0x1000 OR TC image of kb: 0x1001 ... 0x11CF |

Mux codes from ADC Rev B Table 73 (p.86-87). **OPEN-Q7:** confirm in the English data sheet that (a) AINP =
AINM = the same pin is a valid zero, (b) which AIN-buffer settings are allowed for the internal sources (internal
reference, V_20MV, (AVDD-AVSS)/6) - CONFIG_2/3/5 assume buffers may be on for the reference and 20 mV nodes and
off for AVDD/6; (c) that AINM = AVSS requires AIN_BUFM = 0.

Slot 9 consequence: the zero reading uses channel 1's TC- pin; if that pin is out of the common-mode window, the
OV/UV flags fire in slot 9 and the zero check fails for the bank. Accepted (a wiring fault that big is a real
fault); alternative internal short to evaluate on the bench.

### 3.1 Running one slot (single-conversion, one channel enabled)

```
P1  write CHANNEL_s = image | 0x8000
P2  write ADC_CONTROL = 0x0744   (single conversion: one settled conversion, then standby)
P3  poll STATUS once per main loop (loop <= 5 ms typical, <= 20 ms worst, `01` 2) until RDY = 0. The conversion
    start time is stamped at P2; timeout = 1.15 x 42.331 ms + 20 ms (worst loop) = 69 ms after P2 -> B05.
    The observed RDY time (first poll that sees RDY = 0, measured from P2) must lie in 36-69 ms (section 4).
P4  read DATA (24 bits + STATUS + CRC); checks of 2.4; CRC failure -> re-read DATA (data stays until the next
    conversion), at most 2 re-reads, then B02
P5  write CHANNEL_s = image (disabled)
```

The three banks (five on the 40-ch, plus the RTD ADC) run P1-P5 interleaved: P2 is issued to every bank within
~1 ms, so all banks convert in parallel and finish each slot within ~1 ms of each other. One scan:
15 x (44.559 + ~1.5 ms overhead) = **~690 ms normal** at -5 % clock (C 9.7's ~700 ms screen); worst with
slow polling 15 x ~70 ms = ~1050 ms (10.2); 1.2 s budget
(GOAL, I-013) with 30 ms pump/relay release (C 8.5).

The sequencer alternative (all 15 channels enabled, one start per scan) saves ~20 ms per scan but depends on
how single-conversion mode steps through several enabled channels and on rewriting rotating channels between
scans. **OPEN-Q8:** adopt only after the English data sheet confirms that behaviour; the per-slot method above is
the baseline.

### 3.2 Work between slots and scans

During each ~42 ms conversion window the MCU (CS of that ADC high except for short transactions) may read back
only the **static** registers of the image list (CONFIG_x, FILTER_x, ERROR_EN, IO_CONTROL_x, OFFSET/GAIN,
OFFSET_7 signature), two or three round-robin, all once per scan. The **mutable** ones (ADC_CONTROL, CHANNEL
enables) are read only at the post-P5 point of section 5, never during a conversion (ADI: ADC_CONTROL changes
at end of conversion, AD7124 Rev F p.50). Then it reads the TMP126 frames
(section 6), evaluates finished TC results (immediately, C 9.7: "Temperature samples must not wait for the next
complete-scan processing pass"), services UI/Modbus in bounded steps. Between scans: rotate CHANNEL_13/14 images
(write + read back), read ERROR, ID, MCLK_COUNT, OFFSET_7 signature.

## 4. Per-slot validation and limits

All voltages from a bipolar code: `delta = code - 0x800000`, `V = delta x Vref / (G x 2^23)` (ADC Rev B p.51
bipolar coding). TC slots: Vref = 2.5 V, G = 32 -> 1 LSB = 9.3132 nV (exact: `emf_nV = (delta x 9765625) >> 20`,
int64, round by adding 2^19 before the shift).

| Slot | Check | Limit | Fault |
|---|---|---|---|
| all | CRC on every transaction | 2 retries | B02 |
| all | STATUS.POR_FLAG = 0 | - | B15 -> full re-init of that bank |
| all | STATUS.CH_ACTIVE = s; RDY first seen between 0.85 x 42.331 ms (36 ms) and 1.15 x 42.331 ms + 20 ms (69 ms) after P2 - the upper bound includes one worst-case loop of polling delay | window *provisional* (C 9.7 -5 % clock) | B05 |
| all | ERROR_FLAG -> ERROR register classified (section 5) | - | B04 or channel code |
| 0-7 | code inside +-FS: `|delta| < 0.98 x 2^23` and no ADC_SAT_ERR / ADC_CONV_ERR | - | C02 (out of range) |
| 0-7 | no AINP/AINM OV/UV flag | flags are AVDD + 40 mV / AVSS - 40 mV comparators (ADC Rev B p.65, Fig. 119) | C07 |
| 8 | REF ratio `r = delta / 2^23` (nominal 2.5/3.0 = 0.83333, code 0xEAAAAB) | `|r / r_cal_b - 1| <= 1.6 %` *provisional* (0043 4.2, 0032 rev 1: budget 1.43 %); r_cal_b = production calibration per bank | B06 |
| 9 | zero `|V| <= 50 uV` | *provisional*, ~1.2 C on K | B08 |
| 10 | non-zero `15 mV <= V <= 25 mV` | *provisional*: the 20 mV source has no min/max in Rev B; this only proves a live gain-32 path | B09 |
| 11 | gain ratio `|V10 / V11 - 1| <= 0.5 %` (V10 at G = 32, V11 at G = 1) | *provisional* | B09 |
| 12 | AVDD = 6 V: `3.15 V <= AVDD <= 3.45 V` | LP2985 standard grade +-3.5 % (1-150 mA, legacy chip) = 3.18-3.42 V; TL431 clamp starts ~3.46 V min (2.4825 x (1 + 3.98/10.1)); AD7124 AVDD 2.9-3.6 V (Rev B Table 1 notes) | B07 |
| 13 | common mode `m = delta / 2^23` (= V/AVDD) | `0.05 <= m <= 0.95`: inside the gain-32 buffered window 0.116-3.184 V at 3.3 V (0032, data sheet Table 3 note 8) | C03 for the channel owning AIN(i) |
| 14 | burnout of channel kb, see 4.1 | | C01 / C06 / G10 |

REF calibration at production (service mode, 0043 2.2): per bank, mean of 16 slot-8 readings at room
temperature, accepted if `|r_cal / 0.83333 - 1| <= 1.0 %` (*provisional*: REF3030 +-0.2 % and 75 ppm/C max,
REF3030 data sheet features; AD7124 internal reference accuracy - OPEN-Q9 cite), stored with the settings
(`05`). No valid r_cal -> B06 on that bank (and `05` decides whether that is config lock).

### 4.1 Burnout (slot 14)

`d = V(slot 14, kb) - V(slot kb)` from the same scan (both gain 32). Expected for a closed loop:
`0.5 uA x (2 x (2.2k + 1k) + R_loop) = 3.2 mV + 0.5 uA x R_loop` (0032 network). Burnout current accuracy is not
specified min/max in Rev B, so the limits are relative to a **per-channel baseline** `b_k` learned at
commissioning (service mode: mean of 8 burnout deltas; accepted if 1.5 mV <= b_k <= 10 mV, *provisional*;
stored, `05`).

| Condition | Meaning | Fault |
|---|---|---|
| ADC_SAT_ERR, or `V(slot 14) >= 0.9 x FS` (70.3 mV), or `d > 2 x b_k` | open thermocouple / high-resistance loop (upper window) | C01 |
| `d < 0.5 x b_k` | shorted filter capacitor, shorted R2 or short at the input (0032 rev 3 H2: "otherwise reads as T_CJ forever") | C06 |
| no baseline stored | lower window cannot be checked | G10 (`04`/`05` decide the action; **OPEN-Q10**) |

Windows are *provisional* (0043 4.2: upper and lower window plus baseline). Burnout readings are never used as
temperature. Coverage: each channel every 8 scans (~5.6 s, C 9.7); between checks an open input drifts to the
rail and reads out of range (C02) or implausibly (0043 4.2).

## 5. ERROR register classification (ADC Rev B Table 70 p.83)

Read ERROR (0x46) when a STATUS shows ERROR_FLAG = 1, and once per scan unconditionally. **The first observed
ERROR value is kept against the conversion it belongs to** (reading ERROR clears ADC_CONV_ERR and other latched
bits, so a re-read is not evidence). A conversion with a conversion/saturation/OV-UV bit is never used as a
temperature: the fault below applies, and only a **new** conversion of that slot in a later scan can clear it.
SPI_* communication bits: the transaction is retried (at most twice per scan, 0043 3.1); repeated -> B04.

| Bits | During slot 0-7 | During slot 13 / 14 | During slots 8-12 | Any time |
|---|---|---|---|---|
| ADC_SAT_ERR (16), ADC_CONV_ERR (17) | C02 for that channel | 14: C01 (open); 13: C03 | B04 | - |
| AINP_OV (15), AINP_UV (14), AINM_OV (13), AINM_UV (12) | C07 for that channel | 13: C03; 14: ignored for OV/UV of the burnout pair (current drives the inputs) | B04 (slot 9: see 3) | - |
| REF_DET_ERR (11) | - | - | slot 8: B06 | B04 |
| LDO_CAP_ERR (19), ADC_CAL_ERR (18), DLDO_PSM (9), ALDO_PSM (7), SPI_IGNORE (6), SPI_SCLK_CNT (5), SPI_READ (4), SPI_WRITE (3), SPI_CRC (2), MM_CRC (1) | B04 | B04 | B04 | B04 |

**OPEN-Q4:** which ERROR bits clear on read and which follow the live condition (English data sheet "Diagnostics").

**Register read-back timing and expected states:** the image compare of 10.1 item 3 is done once per scan,
after P5 of the last slot, when the ADC has finished its single conversion and is back in standby: expected
ADC_CONTROL = image with MODE = standby (the value the device reports after a single conversion), every
CHANNEL_x enable bit = 0 (images otherwise unchanged), CONFIG/FILTER/ERROR_EN/IO_CONTROL/OFFSET_7 = image,
OFFSET/GAIN = the values captured after calibration.

MCLK_COUNT (0x08) is asynchronous to SPI, so one read can be torn: read it repeatedly until two consecutive
reads agree (at most 4 reads, else B05) - the agreed value is the sample. Sampled at P2 and at P4 of one slot
per scan; it must have changed (0043 3.1 "MCLK/conversion
counter advanced"), else B05. A frequency check from MCLK_COUNT needs its exact increment rate (Rev B Table 72
reads "/131" - **OPEN-Q11**); until then the slot-period window of section 4 is the clock check.

## 6. TMP126 driver (cold junction)

Bus timing and the SIO_WR_N sequence: `02` section 2.4. Frame and register facts (TMP SNIS209C):

* Command word (8.5.2.1, Fig. 8-10): bit 15 don't care, bit 14 CRC enable, bits 13:10 CRC data-block length in
  words (0 or > 1010b disables CRC), bit 9 auto-increment, bit 8 R/W (1 = read), bits 7:0 sub-address.
* CRC (8.5.2.5.1, Table 8-2): 16-bit, poly x^16 + x^12 + x^5 + 1 (0x1021), seed 0xFFFF, no reflection, XOR 0,
  over the command word and the data block; example 0xABCD -> 0xD46A (reproduced).
* Registers (Table 8-3): 00h Temp_Result, 02h Alert_Status (R/RC), 03h Configuration (reset 0006h), 05h
  TLow_Limit, 0Ch Device_ID (reset **2126h**: Rev[15:12] = 2, ID[11:0] = 126h, Table 8-17).
* Temp_Result: 14-bit two's complement in bits 15:2, LSB 0.03125 C, bits 1:0 always 00 (8.5.1, Table 8-1):
  `T_mC = ((int32)(int16)raw x 125) >> 4` (0x0C80 -> 25 000 m C).
* Data_Ready_Flag (Alert_Status bit 0): 1 = unread conversion; cleared by reading Alert_Status **or**
  Temp_Result (Table 8-7, 8.4.1). CRC_Flag (bit 7): last CRC-enabled write failed.
* "Repeated temperature reads are not supported" (8.5.2.4): one Temp_Result word per frame.
* Accuracy +-0.3 C at -20..85 C, +-0.4 C at -40..125 C; tCONV 4.5 / 6 / 7.5 ms; tRESET 0.5 ms; tINITIATION
  0.5 ms (7.5, 7.6).

### 6.1 Frames used

| Frame | Command | Data | CRC test vector (computed) |
|---|---|---|---|
| read Alert_Status | 0x4502 | status | - |
| read Temp_Result | 0x4500 | temperature | data 0x0C80 -> CRC 0x82FC |
| read Configuration | 0x4503 | expect 0x0004 | 0x0004 -> 0x4FCD |
| read TLow_Limit (signature) | 0x4505 | expect signature | - |
| read Device_ID | 0x450C | expect 0x2126 | 0x2126 -> 0x520B |
| write Configuration (no CRC) | 0x0003 | 0x0004 | - (see OPEN-Q12) |
| write TLow_Limit with CRC | 0x4405 | signature | 0xC000 -> 0xDD09 |

### 6.2 Configuration at start-up

Configuration = **0x0004**: Reset 0, AVG 0, Int_Comp 0, One_Shot 0, Mode 0 (continuous), Conv_Period 100 =
**250 ms** (Table 8-8) - at least two conversions per ~0.7 s scan, so Data_Ready is set every scan; conversion
period >= 31.25 ms keeps the specified accuracy (8.3.5). Written **without CRC** because 8.3.3 still says "Writing
to the configuration register with a CRC enabled transaction is currently not supported", while the revision
history of SNIS209C says that restriction was removed - **OPEN-Q12** (bench: try a CRC write, read back).
Verified by a CRC read of 03h. Then TLow_Limit signature (section 9) written with CRC and read back. Wait
>= 7.5 ms before the first scan read.

### 6.3 Per scan, per sensor

```
T1 read Alert_Status   -> CRC ok; CRC_Flag = 0; Data_Ready -> age = 0 if 1, else age += 1
T2 read Temp_Result    -> CRC ok; value
T3 read Device_ID      -> CRC ok; == 0x2126
T4 read Configuration  -> CRC ok; == 0x0004
T5 read TLow_Limit     -> CRC ok; == signature
```

T1 must come before T2 (T2 clears Data_Ready). A CRC failure on any frame -> that frame re-read **once**
(0043 3.4); second failure -> sensor invalid this scan. Total ~5 x 0.17 ms per sensor.

Sensor **valid** this scan if: all five frames CRC-good (after <= 1 re-read), ID 0x2126, Configuration 0x0004,
signature matches, `age <= 2` scans (0043 3.4: "value <= 2 scans old"), and -40.0 C <= T <= +125.0 C (the
specified accuracy range, 7.5). CRC protects against the A3-era echo and a dead bus (0x0000 = 0 C, I-119).

### 6.4 Two-sensor rule per bank (0043 3.4)

| Sensor 0 | Sensor 1 | Result | Code |
|---|---|---|---|
| valid | valid, `|T0 - T1| <= W_cj` | CJ OK, interpolate (6.5) | - |
| valid | valid, `|T0 - T1| > W_cj` | bank fault, trip | B11 |
| one valid | one invalid | **until the bench measures the fallback error: trip** (0043 3.4 "stricter rule"); afterwards (build/config flag `CJ_DEGRADED_ALLOWED`): bank runs on the valid sensor for all 8 channels, `DEGRADED CJ` + ALARM | B12 |
| invalid | invalid | bank fault, trip | B10 |

`W_cj` = **3.0 C provisional** (two sensors of +-0.3 C plus the header-to-header gradient). **OPEN-Q13:** set
from the I-114 gradient test with LCD, relays and RS-485 loaded.

### 6.5 CJ per channel by pin position (I-114)

`T_cj(k) = T0 + w_k x (T1 - T0)`, w_k in Q8 (w x 256), clamped to [0, 1] (no extrapolation beyond the sensors,
which would amplify sensor error). Default weights assume each sensor sits at the centre of its 4-channel
header and a uniform 7.62 mm channel pitch (3.81 mm terminal pitch, two pins per channel; `c_bank.py` HDR_FP):
x_k = 7.62 k mm, sensor 0 at the centre of channels 1-2 (k = 1.5), sensor 1 at the centre of 5-6 (k = 5.5)
(0-based k):

| k (ch in bank) | 0 (1) | 1 (2) | 2 (3) | 3 (4) | 4 (5) | 5 (6) | 6 (7) | 7 (8) |
|---|---|---|---|---|---|---|---|---|
| w_k (unclamped (k-1.5)/4) | -0.375 | -0.125 | 0.125 | 0.375 | 0.625 | 0.875 | 1.125 | 1.375 |
| w_k used (Q8) | 0 | 0 | 32 | 96 | 160 | 224 | 256 | 256 |

**OPEN-Q14:** replace the default with weights from the real sensor and terminal coordinates of each board
(`0036` D1: sensors moved <= 8 mm from their headers) and confirm with the I-114 gradient test; the header gap
between J1 and J2 is not included in the uniform-pitch assumption. Weights are a `board_cfg` table.

## 7. Thermocouple conversion (`tc_math`)

* Method (0043 4.2, voltage domain): `E_cj = E_type(T_cj)`; `E = emf_nV + E_cj`; `T = E_type^-1(E)`. The CJ is
  converted with the channel's own type (K or J).
* Tables: NIST ITS-90 reference functions (NIST Monograph 175 / SRD 60 coefficients; K above 0 C includes the
  exponential term). Generated offline by a script, stored in flash as `int32` nV at every **10 C**:
  K -200 .. +1370 C plus the end point 1372 C (159 entries), J -210 .. +1200 C (142 entries), ~1.2 KB.
  Coefficients checked here against NIST table values: K 100 C = 4.096 mV, 1000 C = 41.276 mV, 1372 C =
  54.886 mV; J 100 C = 5.269 mV, 760 C = 42.919 mV, 1200 C = 69.553 mV.
* Forward (T -> E, for the CJ) and inverse (E -> T) by linear interpolation in the same table; inverse uses
  binary search for `E[i] <= E < E[i+1]` and
  `T_dC = 100 i_C + (100 x (E - E[i]) + (E[i+1]-E[i])/2) / (E[i+1] - E[i])` (fits int32: one 10 C step is
  <= 0.65 mV = 650 000 nV, x 100 < 2^31). No floating point.
* Interpolation error of a 10 C table, computed here against the full NIST functions (0.05 C sweep): K <= 0.14 C
  (worst near -195 C), J <= 0.17 C (near -205 C); **<= 0.03 C for T >= -50 C** for both. A 20 C table would give
  0.52 / 0.61 C - rejected. These bounds are before rounding to the 0.1 C output (which adds <= 0.05 C). This is
  conversion arithmetic only, not system accuracy.
* ADC resolution 9.3 nV = 0.0002 C at 41 uV/C - negligible. Gain 32 full scale 78.125 mV covers K to 1372 C
  (54.886 mV) and J to 1200 C (69.553 mV) plus CJ and burnout offset.
* Out of range: `E < E[0]` or `E > E[last]` -> C02 (no temperature). Saturation/near full scale -> C02 (section 4).
* Plausibility floor: `T < -50.0 C` -> C08 *provisional* (engine panel cannot be colder; a reversed thermocouple
  reads negative). Negative EMF itself is normal (tip colder than CJ, I-119). Note: a reversed probe near CJ
  temperature reads plausibly and is not detectable - commissioning check.
* Output `temp_dC` int16 in -2000..+14000 (K max 13720).

## 8. PT100 bank (40-ch, `rtd`)

Hardware (FAM `c_rtd.py`, C 10.11, D39 P4/P5): probe p = 0..2 (channels 41-43), p = 3 = on-board 150R 0.1 %
check resistor; per p: AIN4p = IOUT to lead A, AIN4p+1 = IOUT to lead B, AIN4p+2 = sense A, AIN4p+3 = sense B;
REFIN1(+) = RTD_RET, REFIN1(-) = RTD_REFN across R_ref 2.49 k 0.1 %; 330R headroom below.

### 8.1 Registers (RTD ADC)

Same as 2.1 except:

| Reg | Value | Fields |
|---|---|---|
| CONFIG_0 | **0x09E4** | Bipolar, REF_BUFP 1, REF_BUFM 1 (REFIN1- = 0.165 V >= 0.1 V headroom, C 10.11), AIN_BUFP/M 1, REF_SEL 00 = REFIN1, PGA 100 = 16 |
| CONFIG_1 | **0x0810** | internal ref, buffers off, gain 1 (AVDD/6, sheath test) |
| CONFIG_2 | **0x0874** | internal ref, AIN buffers on, gain 16 (20 mV) |
| CONFIG_3 | **0x0810** | internal ref, AIN buffers off, gain 1 (20 mV partner; same rule as CONFIG_5) |
| CONFIG_4, 5 | 0x0860 | unused (reset) |
| IO_CONTROL_1 | per slot, below | IOUT1(13:11) = 011 = 250 uA, IOUT0(10:8) = 011 = 250 uA, IOUT1_CH(7:4), IOUT0_CH(3:0) (Table 68) |

IO_CONTROL_1 images (both currents 250 uA; normal = IOUT0 on lead A, IOUT1 on lead B; swapped = reverse):

| p | normal | swapped |
|---|---|---|
| 0 | 0x001B10 | 0x001B01 |
| 1 | 0x001B54 | 0x001B45 |
| 2 | 0x001B98 | 0x001B89 |
| 3 (check R) | 0x001BDC | 0x001BCD |
| currents off | 0x000000 | |

### 8.2 RTD slots (12; C 10.7 screen 574.7 ms < 668 ms TC cycle)

| Slot | Purpose | IO_CONTROL_1 | Setup | AINP / AINM | CHANNEL image |
|---|---|---|---|---|---|
| 0, 1 | PT100 p0 normal, swapped | 0x001B10 / 0x001B01 | 0 | AIN2 / AIN3 | 0x0043 |
| 2, 3 | p1 | 0x001B54 / 0x001B45 | 0 | AIN6 / AIN7 | 0x00C7 |
| 4, 5 | p2 | 0x001B98 / 0x001B89 | 0 | AIN10 / AIN11 | 0x014B |
| 6, 7 | check resistor | 0x001BDC / 0x001BCD | 0 | AIN14 / AIN15 | 0x01CF |
| 8 | sheath test, rotating sense input s in {2,3,6,7,10,11,14,15}, currents off | 0x000000 | 1 | AIN s / AVSS | 0x1011 OR (s << 5) |
| 9 | 20 mV at gain 16 | 0x000000 | 2 | V_20MV_P / M | 0x239D |
| 10 | 20 mV at gain 1 | 0x000000 | 3 | V_20MV_P / M | 0x339D |
| 11 | AVDD/6 | 0x000000 | 1 | (AVDD-AVSS)/6 +/- | 0x1295 |

Per slot: write IO_CONTROL_1 only while the ADC is in standby, **wait >= 2.3 ms** (R_ref x 100 nF = 249 us,
0.01 % after 2.29 ms, C 10.11), then P1-P5 of 3.1. A conversion never spans a current change (0043 4.5).

### 8.3 Conversion and checks

* Ratio: `V_sense / V_ref = R / (2 R_ref)` (both currents through R_ref), so
  `R_mohm = delta x 2 x 2 490 000 / (16 x 2^23)` (int64); full scale 311.25 ohm (C 10.11).
  `R = (R_normal + R_swapped) / 2` cancels IOUT mismatch to first order (C 10.11).
* T from R: IEC 60751 Callendar-Van Dusen (A = 3.9083e-3, B = -5.775e-7, C = -4.183e-12 below 0 C), table of R
  in mohm every 10 C from -50 to +400 C (46 entries), linear interpolation; error <= 0.005 C (computed here).
  R(100 C) = 138.506 ohm, R(200 C) = 175.856 ohm. Outside the table -> C09. **OPEN-Q15:** table top (400 C) vs the
  probes' class/limit.

| Check | Limit (*provisional*) | Fault |
|---|---|---|
| check resistor (mean of slots 6/7) | 150.000 ohm +-0.3 % (C 10.11 "window ~0.3 %") | B14 |
| sheath test (slot 8) | `|V| <= 0.10 V` (fault ~0.29 V, C 10.11) | B14 |
| 20 mV gain ratio (9/10) | `|V9 / V10 - 1| <= 0.5 %` | B14 |
| AVDD/6 (11) | as TC banks | B14 |
| REF_DET_ERR in slots 0-7 | none | B14 |
| ADC checks of 2.2-2.4, 5 | as TC banks | B14 |
| per probe: normal vs swapped | `|R_n - R_s| <= 1 % of R` *(OPEN-Q16: IOUT matching spec)* | C09 |
| per probe: R outside table, saturation, open lead | - | C09 |

Check-resistor or reference failure invalidates the whole RTD bank -> global fault (0043 4.5) -> B14.
**OPEN-Q17:** whether REF_DET_ERR flags conversions that use the internal reference while the RTD currents are
off (slots 8-11); if it does, mask it there.

## 9. Device signatures (0043 4.4; mandatory on all boards)

Written once at start-up (and after every re-init), read back **every scan**; any mismatch -> **B13** (aliased
address, stuck CSAx, swapped CS line). On 8/24-ch the same check costs two reads per device and catches crossed
chip selects, so the code path is identical on all boards.

| Device | Spare register | Value |
|---|---|---|
| AD7124 index d (0..4 = banks A..E, 5 = RTD) | OFFSET_7 (0x30, setup 7 never used) | `0xA50000 | (d << 8) | (0xFF - d)` (d0 0xA500FF, d1 0xA501FE, ... d5 0xA505FA) |
| TMP126 index j (0..9; bank b sensor i -> j = 2b + i) | TLow_Limit (05h; ALERT is grounded and unused) | `0xC000 + 0x0040 x j` (bits 1:0 stay 00; 0xC000 ... 0xC240) |

## 10. Scan validation

### 10.1 Validated bank scan (bank b, board scan n) - every item true

1. Every AD7124 transaction of bank b in scan n had a good CRC, after at most 2 retries each.
2. ID read in scan n passes 2.3; no STATUS with POR_FLAG = 1.
3. Every register of the image list (2.1, incl. OFFSET/GAIN captured after calibration and the OFFSET_7
   signature) read back in scan n equal to its image; rotating CHANNEL_13/14 equal to the images of scan n.
4. ERROR read in scan n: no bank-level bit (section 5) observed for any conversion of scan n (communication
   bits only after their retries).
5. All 15 slots completed in order, each result with CH_ACTIVE = slot, RDY inside its window, MCLK_COUNT advanced.
6. Slots 8-12 inside their limits (section 4).
7. CJ: both TMP126 valid and agreeing (6.4), or the degraded rule when `CJ_DEGRADED_ALLOWED` is set.
8. Every channel result is stamped with `scan_no = n` (fresh).

Channel faults (Cnn) do **not** invalidate the bank scan: they mark that channel's result invalid and go to
`channel_eval` (0043 3.2). Over-temperature evaluation uses hardware-valid TC results as soon as each slot
completes; advisory checks never suppress it (I-098).

A TC result is **hardware-valid** when: items 1-2 hold for its own transactions, CRC/CH_ACTIVE/POR checks pass, no
channel-level ERROR bit for its slot, the CJ of its bank is valid in scan n, and the previous scan of that bank
was validated (diagnostic slots 8-12 come after the TC slots in the same scan).

### 10.2 Validated board scan n - every item true

1. Every bank of the board validated for scan n (section 10.1).
2. 40-ch: RTD bank validated for scan n (section 8) and all 16 signatures (6 ADC + 10 TMP126) matched (section 9).
   8/24-ch: all signatures of its devices matched.
3. REFOK read low in scan n outside a REFTEST window; no REFTEST failure pending (`02` 10).
4. Scan n completed within **1200 ms** of its start (normal ~690 ms; worst 15 x ~70 ms = ~1050 ms) - else G05.
   (The RUN window of 1200 ms in `04` 6.1 still opens RUN sooner if scans stop arriving.)
5. No island-loss condition (G14) and no full re-init pending.
6. Fuse self-check passed at start-up (G15 not set).

Only a validated board scan reloads the RUN deadline (`02` 4.2). The watchdog is **not** tied to validated
scans: it is fed by the flow check of `01` 2.3, where acquisition progress means any slot state advance (a
STATUS poll answered, a conversion read, a slot completed, a boot/calibration/service step completed) within
the last 100 ms. Boot, calibration and service steps are written as bounded states so they also report progress.

## 11. Fault codes detected in acquisition

Bank codes carry the bank letter (e.g. `B06 C`); channel codes the channel number. Actions are `04`'s; per
0043 3.3 every B and G code here is an instrument fault: trip + alarm regardless of channel modes.

| Code | Name | Detected when | Clears when |
|---|---|---|---|
| G08 | Engine reference lost | REFOK high in a scan (outside self-test) | REFOK low in a validated scan (latch per `04`) |
| G09 | REFTEST self-test failed | REFOK not high during REFTEST (`02` 10) | next self-test passes |
| G05 | Scan deadline missed, or RUN window (1200 ms, `04` 6.1) expired in `RUN` | board scan not complete within 1200 ms, or window expiry | next validated board scan (the trip latch stays until ACK) |
| G14 | Island power lost | all banks fail CRC/ID in the same scan, or REFOK high together with bank faults on every bank | full re-init + validated board scan |
| B13 | Device signature mismatch | any signature read back wrong (section 9) | re-init + validated board scan |
| B14 | RTD bank fault (40-ch) | any RTD-bank check of section 8.3 except per-probe | validated RTD scan |
| G15 | Fuse mismatch | start-up fuse self-read (`02` 6) | never (reprogram) |
| B01 | ADC missing / wrong ID | bring-up A3/A4 or ID read fails 2.3 | re-init succeeds |
| B02 | Repeated SPI CRC | a transaction fails CRC 3 times in one scan | validated bank scan |
| B03 | Register readback mismatch | any image compare fails (10.1 item 3) | re-init + validated bank scan |
| B04 | ADC error flag | bank-level ERROR bit, ADC_CAL_ERR, calibration sanity | validated bank scan |
| B05 | Conversion sequence/timing | CH_ACTIVE wrong, RDY timeout or outside window, MCLK_COUNT stuck | validated bank scan |
| B06 | REF cross-check | slot 8 outside window, REF_DET_ERR in slot 8, no r_cal | validated bank scan |
| B07 | AVDD out of window | slot 12 | validated bank scan |
| B08 | Zero check | slot 9 | validated bank scan |
| B09 | Non-zero check | slot 10 | validated bank scan |
| B09 | Gain ratio | slots 10/11 | validated bank scan |
| B10 | Both CJ invalid | 6.4 | both valid and agreeing |
| B11 | CJ disagree | 6.4 | agree |
| B12 | One CJ invalid (degraded) | 6.4 (trip until the fallback is accepted; then alarm + `DEGRADED CJ`) | both valid |
| B15 | Unexpected ADC reset (POR_FLAG) | 2.4 | re-init + validated bank scan |
| C01 | Open / high-resistance TC | burnout upper window, saturation in slot 14 | next burnout check of that channel passes |
| C06 | Burnout lower window (shorted input) | 4.1 | next burnout check passes |
| C02 | Out of range | saturation, near full scale, EMF outside the table | next valid in-range result |
| C07 | Input over/under-voltage | AINP/AINM OV/UV in its TC slot | next result without the flag |
| C03 | Common mode out of window | slot 13 for either input of the channel | next CM check of that input passes |
| C08 | Implausibly cold | T < -50.0 C | next result >= -50 C |
| G10 | Burnout baseline missing | no commissioned b_k | baseline stored |
| C09 | PT100 fault (40-ch ch. 41-43) | R outside table, saturation, swap disagreement | next valid reading |

Merged into the master table of `04` section 9 on 2026-10-20 (Q18 closed).

## 12. OPEN items (this file)

| ID | What | Needed |
|---|---|---|
| Q1 | FS field with Filter = 111 (post filter) | English AD7124-8 data sheet, FILTER register |
| Q2 | internal clock tolerance (+-5 % assumed) | English data sheet spec table |
| Q3 | reset wait (2 ms) | English data sheet "Reset" |
| Q4 | ERROR bits clear-on-read vs live; bits set after reset | English data sheet "Diagnostics" |
| Q5 | ID values of shipping silicon | English data sheet + first boards |
| Q6 | calibration order, gain-32 internal FS cal in mid power, duration | English data sheet "Calibration" |
| Q7 | same-pin zero; buffer rules for internal sources and AVSS | English data sheet mux/buffer section; bench |
| Q8 | sequencer alternative | English data sheet single-conversion with several channels |
| Q9 | AD7124 internal reference accuracy/drift (for r_cal window) | English data sheet spec table |
| Q10 | action when burnout baseline is missing | `04` / `05` |
| Q11 | MCLK_COUNT increment rate | English data sheet Table (MCLK_COUNT) |
| Q12 | TMP126 configuration write with CRC | bench on first boards |
| Q13 | CJ agreement window W_cj | I-114 gradient test |
| Q14 | CJ interpolation weights from real coordinates | board placement data + I-114 |
| Q15 | PT100 table range | probe class from the owner |
| Q16 | PT100 swap-agreement limit (IOUT matching) | English data sheet + bench |
| Q17 | REF_DET_ERR with RTD currents off | English data sheet; bench |
| - | every *provisional* limit (sections 4, 4.1, 6.4, 8.3, 10.2) | bench data from the first boards (I-120) |
