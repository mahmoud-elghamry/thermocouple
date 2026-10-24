# 04 - Settings, calibration and events: EEPROM map, A/B records, validation, save, events

**DRAFT - research input, not the final spec** (owner, 2026-10-20). Follows `00-overview.md`. Decided behaviour:
`docs/decisions/0043-family-firmware-plan.md` rev 2 sections 2, 5 and 8; `0029`, `0030` D8, `0038` D2, `0032`
(calibration). Fault codes and global states are those of `03-protection.md` (draft). Modules: `settings`,
`events`, MCAL `eeprom`.

---

## 1. Facts this file rests on

| # | Fact | Evidence |
|---|---|---|
| E1 | ATmega1284P: 4 KiB EEPROM | `CALCULATIONS` 9.8 (Microchip datasheet Atmel-42719) |
| E2 | EEPROM endurance 100 000 write/erase cycles per cell; one byte write from the CPU ~3.3 ms (erase + write) | ATmega1284P datasheet Atmel-42719, features page and EEPROM section. **Not re-opened in this session: check the exact figures before the final spec** |
| E3 | A brown-out during an EEPROM write can corrupt the cell being written; BOD is the datasheet's mitigation. BOD fuse is required here | 0043 3.6 (fuses: BOD), I-104 |
| E4 | The 8-ch firmware stores one native C struct at EEPROM address 0, single copy, CRC-16 poly 0x1021 init 0xFFFF MSB-first over magic + setpoint, read-back with `memcmp` after `eeprom_update_block` | `firmware/src/app/settings.c:7-33`, `firmware/src/hal/settings_store.c:10-37` |
| E5 | `CALCULATIONS` 9.8/10.8 proposed per-channel A/B records of 24 B: 40-ch total 3456 B, 640 B free; "EEPROM is the tightest resource"; "A/B records do not require a full configuration-image duplicate"; channel masks must be byte arrays (> 32 channels) | `CALCULATIONS` 9.8, 10.8 (main) |
| E6 | 40-ch board = 40 TC + 3 PT100 (+ one 150R check resistor, not a channel) = 43 channels | 0043 4.5, `00-overview.md` (channels 41..43); `CALCULATIONS` 10.8 counted 44 (four PT100), superseded by `0039` P5 |
| E7 | Wrong TC type is the hazard: type change only under the settings lock, RUN inhibited, confirm screen, setpoint re-confirmed, old samples discarded, ACK; corrupt or unknown type inhibits RUN, never falls back to K | `0038` D2 |
| E8 | Old single limit is never copied to channels; invalid configuration prevents RUN | `0030` D8; I-100 |

Kept from the 8-ch code: the CRC polynomial and init (E4), read-back after write, "a correct CRC over an
out-of-range value is still not a setpoint" (`settings.c:56-62`). Replaced: native struct storage, single copy,
address 0, blocking `eeprom_update_block`.

---

## 2. EEPROM map (4096 B, one map for all three boards)

Slots are sized for the largest board (43 channels); smaller boards use the same addresses and leave the tail of
each slot unused.

| Address (hex) | Size | Content | Written when |
|---|---|---|---|
| 0x000-0x00F | 16 | reserved, never written (stays 0xFF). A stray write to address 0 by a pointer bug lands on nothing | never |
| 0x010-0x01F | 16 | layout header (2.1) | first save on a blank or foreign EEPROM |
| 0x020-0x31F | 768 | settings copy A (section 3) | saves (A/B alternating) |
| 0x320-0x61F | 768 | settings copy B | saves |
| 0x620-0x71F | 256 | calibration copy A (section 5) | production (service mode), baseline learning |
| 0x720-0x81F | 256 | calibration copy B | same |
| 0x820-0xA9F | 640 | event ring, 32 x 20 B (section 8) | each logged event |
| 0xAA0-0xADF | 64 | power-cycle counter, 8 slots x 8 B (8.4) | each boot |
| 0xAE0-0xAFF | 32 | service-mode EEPROM test scratch (07 active step); never read by anything else | service mode only |
| 0xB00-0xFFF | 1280 | free, reserved (e.g. a future Modbus-write enable record, 0043 8.6) | never in v1 |

Used 2816 B (incl. the 16 B reserved at 0), free 1280 B (31 %). Budget comparison in section 10.

### 2.1 Layout header (0x010)

| Offset | Type | Field | Value |
|---|---|---|---|
| +0 | u8[2] | magic | 0x54 0x48 (`TH`) |
| +2 | u8 | layout version | 1 (this map) |
| +3 | u8 | board type | 8, 24 or 40 |
| +4 | u8 | channel count | 8, 24 or 43 |
| +5 | u8[9] | reserved | 0x00 |
| +14 | u16 | CRC16 over +0..+13 | section 2.3 |

If the header is blank, invalid, or its layout version / board type / channel count differ from the build
(`BOARD`), **every record is ignored** -> `CONFIG_LOCK` (G01) and no calibration (G04). There is no migration from
another layout or board type (E8). The first successful save writes the header (section 6 step 2).

### 2.2 Serialisation

* Explicit byte-by-byte serialisation; never a C struct image (E4 replaced, 0043 5).
* Multi-byte integers **little-endian** (low byte at the lower address), including CRCs.
* Signed values two's complement. Temperatures in settings are whole degrees C (`u16`); runtime converts to 0.1 C.
* Text: ASCII, fixed length, space-padded (0x20), no terminator.
* Reserved bytes are written 0x00 and **must read 0x00** (validated); a later format that uses them bumps the
  format version.

### 2.3 Checksums

* **CRC16**: CRC-16/CCITT-FALSE: poly 0x1021, init 0xFFFF, MSB-first, no reflection, no final XOR (same as the 8-ch
  `settings.c:10-31`). Check value over ASCII `123456789` = **0x29B1** (host test vector). Not avr-libc
  `_crc_ccitt_update`, which is the reflected variant.
* **CRC8** (event entries): CRC-8/SMBUS: poly 0x07, init 0x00, no reflection, no final XOR. Check value over
  `123456789` = **0xF4**.

---

## 3. Settings record (copy A at 0x020, copy B at 0x320)

### 3.1 Header (24 B)

| Offset | Type | Field | Valid values |
|---|---|---|---|
| 0x00 | u8[2] | magic / commit marker | 0x53 0x54 (`ST`) = committed; anything else = not valid. Written **last** in a save |
| 0x02 | u8 | format version | 1 |
| 0x03 | u8 | board type | equals build `BOARD` (8, 24, 40) |
| 0x04 | u8 | channel count N | equals board: 8, 24, 43 |
| 0x05 | u8 | reserved | 0 |
| 0x06 | u32 | sequence | 1..0xFFFFFFFE; new = active + 1 |
| 0x0A | u16 | firmware version that wrote it (major << 8 \| minor) | any (informational, not validated) |
| 0x0C | u8 | Modbus address | 1..247 |
| 0x0D | u8 | Modbus baud code | 0 = 9600, 1 = 19200 (0043 2.2) |
| 0x0E | u16 | setup PIN | 0..9999 (length/format **OPEN**, 05) |
| 0x10 | u8[8] | reserved | all 0 |

### 3.2 Channel block (16 B per channel, channel `c` = 1..N at 0x18 + 16 (c-1))

| Offset | Type | Field | Valid values |
|---|---|---|---|
| +0 | u8 | type | 0 OFF, 1 K, 2 J on TC channels; 0 OFF, 3 PT100 on 40-ch channels 41..43 only |
| +1 | u8 | mode | 0 TRIP, 1 ALARM ONLY (0 when OFF) |
| +2 | u8[6] | name | allowed characters per 05 (**OPEN**: proposed `A-Z 0-9 space - / .`); blank = 6 spaces |
| +8 | u16 | alarm SP, whole C | fitted: 0 <= alarm SP < trip SP; OFF: 0 |
| +10 | u16 | trip SP, whole C | fitted: alarm SP < trip SP <= probe limit; OFF: 0 |
| +12 | u8 | reset band, whole C | fitted: 2..50; OFF: 0 |
| +13 | u16 | probe limit, whole C | fitted: 1..table max of the type (K 1372, J 1200, PT100 850); OFF: 0 |
| +15 | u8 | reserved | 0 |

CRC16 at `0x18 + 16 N`, covering bytes 0x00 .. `0x18 + 16 N - 1` **including the committed magic**. Record length
`26 + 16 N`: 8-ch 154 B, 24-ch 410 B, 40-ch 714 B (slot 768 B; 54 B unused at 43 channels).

An OFF channel keeps its name; its numeric fields are normalised to 0 so that turning it back on needs setpoints
entered again (E7, "never invent").

### 3.3 Semantic validation (the same function at boot, after every save read-back, and on the RAM copy before save)

1. Magic = `ST`; format version = 1; board type and channel count equal the build; reserved bytes 0.
2. CRC16 matches.
3. Sequence not 0 and not 0xFFFFFFFF.
4. Modbus address 1..247; baud code 0 or 1; PIN 0..9999.
5. Per channel: type allowed for that channel number; mode 0 or 1; every name byte in the allowed set.
6. Per OFF channel: mode, alarm SP, trip SP, band, probe limit all 0.
7. Per fitted channel: `1 <= probe limit <= table max(type)`; `alarm SP < trip SP <= probe limit`; `band` in 2..50.
8. At least one fitted channel (**OPEN**, owner: require at least one fitted **TRIP** channel? a board protecting
   nothing would otherwise grant RUN on global checks only).

Any failure = record invalid. Nothing is repaired or defaulted (0038 D2: never fall back silently).

---

## 4. Boot: record selection and the RAM copy

### 4.1 Selection rule

| Copy A | Copy B | Result |
|---|---|---|
| valid | valid, A.seq > B.seq | A active |
| valid | valid, B.seq > A.seq | B active |
| valid | valid, equal seq, identical bytes | A active |
| valid | valid, equal seq, different bytes | **none** -> `CONFIG_LOCK`, G01 (cannot happen without a bug) |
| valid | invalid | A active (B is the next save target) |
| invalid | valid | B active |
| invalid | invalid | none -> `CONFIG_LOCK`, G01 |
| any | any, header (2.1) invalid or foreign | none -> `CONFIG_LOCK`, G01 |

"Valid" = all of 3.3. No wrap handling: 2^32 saves cannot happen within the endurance of the cells.

### 4.2 Calibration selection

The same rule on the calibration copies (section 5). None valid -> G04 (trip, latched, 03 section 9).

### 4.3 What config lock means (0030 D8, 0043 5)

`CONFIG_LOCK`: RUN never granted; ACK refused (`NO ACK: SETUP LOCK`); setup reachable (05) so a full, valid record
can be built and saved; the only exit is a successful save (03 T14) followed by an ACK.

### 4.4 RAM copy

The active record's raw bytes (up to 714 B) are kept in RAM as the authoritative image; fields are read from it
through accessors. Once per validated board scan its CRC16 is recomputed (may be spread over main-loop passes,
<= 10 ms per pass) and compared with the stored CRC; mismatch -> **G03** (trip, power cycle). Edits are made on a
separate edit copy, never on the active image.

---

## 5. Calibration record (copy A at 0x620, copy B at 0x720)

| Offset | Type | Field | Valid values |
|---|---|---|---|
| 0x00 | u8[2] | magic / commit marker | 0x43 0x41 (`CA`), written last |
| 0x02 | u8 | format version | 1 |
| 0x03 | u8 | board type | build `BOARD` |
| 0x04 | u8 | bank count | 1, 3, 6 (40-ch: 5 TC + RTD bank) |
| 0x05 | u8 | channel count N | 8, 24, 43 |
| 0x06 | u32 | sequence | as 3.1 |
| 0x0A | u16 | firmware version | informational |
| 0x0C | u8[4] | reserved | 0 |
| 0x10 | u32[6] | REF ratio per bank, in ppm (internal 2.5 V measured against REF3030 at gain 1; nominal 833 333, `0032` rev 3 item 2) | banks 0..bank count-1: inside the plausibility window from 02 (**OPEN**); unused banks and the RTD bank: 0 (**OPEN**: whether the RTD bank gets a stored check value, 02) |
| 0x28 | s32[N] | burnout baseline per channel, units from 02 (proposed nV, `emf_nV`) | 0x7FFFFFFF = not learned; PT100 and OFF channels: 0x7FFFFFFF |
| 0x28 + 4N | u16 | CRC16 over 0x00 .. 0x27 + 4N | |

Lengths: 8-ch 74 B, 24-ch 138 B, 40-ch 214 B (slot 256 B).

Writers: REF ratios only in service mode (production, 0043 7). Baselines: learned at commissioning (0043 4.2) under
`SETUP_INHIBIT` (03 section 5), per channel or all fitted channels; the trigger screen is 05/07's (**OPEN**). A fitted
TC channel whose baseline is `0x7FFFFFFF` raises **C06 NO BASELINE** (action by channel mode). Changing a channel's
type does not erase its baseline (the probe and cable are the same); **OPEN**: should a type change force relearning?

Both writers save the whole calibration record with the A/B procedure of section 6 (one routine for both record
kinds).

---

## 6. Save procedure (settings and calibration alike)

### 6.1 Steps

1. **Build and check** the new image in RAM from the edit copy: sequence = active.seq + 1 (1 if none active),
   firmware version, header fields; run 3.3 on it. Fail -> refuse; nothing is written; the UI shows the first
   failed rule (05).
2. **Layout header**: if 2.1 is not exactly the expected header, write it and read it back. (Only on a blank or
   foreign EEPROM; nothing else there is valid then.)
3. **Target** = the copy that is not active (the older one, or the invalid one).
4. Write target magic = 0x00 0x00 (explicit invalidate), read back.
5. Write bytes 0x02 .. end of body, skipping bytes that already hold the new value (update-if-different).
6. Write the 2 CRC bytes.
7. Write the magic (commit marker) last.
8. **Read back** the whole target record from EEPROM and run the boot validation (3.3) on the read bytes; compare
   byte-for-byte with the RAM image.
9. Pass: switch the active pointer to the target; replace the RAM image (4.4); tell `protection` (apply, 03 T11/T12/
   T14); log `SETTING_CHANGE` (or `CAL_CHANGE`).
10. Fail: write the target magic to 0x00 0x00 once more (best effort); the active copy and the RAM image are
    unchanged; raise **G02** (03 section 9); the UI offers retry (whole procedure from step 1) or cancel. G02 clears
    only after a successful save and ACK (0043 5).

### 6.2 Non-blocking writes

* One byte per EEPROM-ready poll, from the main loop; interrupts are disabled only for the EEMPE/EEPE sequence
  (4 cycles). No call blocks for a whole record: the watchdog (fed only on acquisition progress) and the 10 ms
  main-loop pass limit (03 6.3) must keep running.
* Worst case (every byte differs) 40-ch: 714 B x 3.3 ms = **2.36 s**; typical (a few fields + sequence + CRC +
  magic, target two saves old) **< 50 B, < 0.2 s**.
* Settings saves and event writes share the EEPROM: one writer queue, the save first, events after (events are
  buffered, 8.3).

### 6.3 Power-cut safety

| Power lost during | At the next boot | Result |
|---|---|---|
| steps 1-3 (nothing written) | active copy valid, target older valid or invalid | old settings |
| step 4 (invalidate) | target magic may be torn: not `ST` -> invalid | old settings |
| steps 5-6 | target magic 0x0000 -> invalid | old settings; the edit is lost (operator sees old values) |
| step 7 (commit) | magic torn -> invalid; or complete -> target valid with full CRC | old settings, or the new ones if the commit completed |
| after 7, before 8 | target fully written, CRC and 3.3 checked at boot | new settings (boot does the read-back check) |
| step 10 | target invalid | old settings |

Every boot lands in `START_LATCHED` or `CONFIG_LOCK`, so a power cut during a save never grants RUN by itself.
The active copy is never written during a save; only a brown-out corrupting a cell other than the one being written
could hit it (not a known AVR mechanism with BOD set, E3), and the CRC would then reject it -> the other copy, or
`CONFIG_LOCK`.

---

## 7. What a change needs (owner decision 8.1, 0043 3.7)

| Setting | RUN must be open (`SETUP_INHIBIT`) | New ACK after save | Other |
|---|---|---|---|
| type | yes | yes | setpoints re-entered (0038 D2); old samples discarded (`CH_INIT`) |
| mode | yes | yes | |
| alarm SP, trip SP | yes | yes | |
| reset band | yes | yes | |
| probe limit | yes | yes | both SPs re-checked against it (3.3 rule 7) |
| burnout baseline learning | yes | yes | calibration record |
| REF ratio calibration | service mode only | power cycle + ACK | calibration record |
| name | no (live) | no | |
| Modbus address / baud | no (live) | no | applied after the save is read back |
| PIN | no (live) | no | |
| PIN reset by the ACK+SET power-up gesture (0043 6) | at power-up (RUN open anyway) | yes (`START_LATCHED`, cause RECOVERY) | settings otherwise kept; logged |

Modbus never writes any of these in v1 (decision 8.6).

---

## 8. Events

### 8.1 Entry (20 B; slot `k` = 0..31 at 0x820 + 20k)

| Offset | Type | Field |
|---|---|---|
| +0 | u16 | event sequence 1..0xFFFE (0 and 0xFFFF = empty/blank) |
| +2 | u8 | event type (8.2) |
| +3 | u8 | code: bits 7-6 class (0 none, 1 G, 2 B, 3 C), bits 5-0 number `nn` (so `G08` = 0x48, `C01` = 0xC1) |
| +4 | u8 | channel 1..43, 0 = none |
| +5 | u8 | detail (per type, 8.2) |
| +6 | s16 | value, 0.1 C (0x8000 = none) |
| +8 | s16 | threshold, 0.1 C (0x8000 = none) |
| +10 | u32 | `uptime_s` since this boot |
| +14 | u32 | `power_cycles` (8.4) |
| +18 | u8 | global state (03 3.1 codes) after the event |
| +19 | u8 | CRC8 over +0..+18 |

Ring head: at boot every slot is read; valid = CRC8 good and sequence not 0/0xFFFF. The newest is the valid slot `k`
whose successor slot is not valid with sequence + 1 (modulo the 1..0xFFFE range). The next event goes to slot
`(k + 1) mod 32` with sequence + 1. No valid slot: slot 0, sequence 1. A torn entry (power cut) fails its CRC and is
simply skipped. Trip history survives ACK (0043 5); the ring overwrites the oldest.

### 8.2 Types and when each is logged (transitions only)

| Type | Name | Logged when | channel | code | detail | value / threshold |
|---|---|---|---|---|---|---|
| 0x01 | POWER_UP | once per boot, after settings load | 0 | 0 | reset cause bits from MCUSR (PORF 1, EXTRF 2, BORF 4, WDRF 8) | - |
| 0x02 | TRIP | a channel's `trip_latched` goes 0 -> 1, or a G/B fault with action trip latches | ch / 0 | 0 = over-temperature, else Gnn/Bnn/Cnn | bit 0 = first-out, bits 3-1 = bank for Bnn | value; threshold = trip SP or 0x8000 |
| 0x03 | ALARM | a channel's `alarm_latched` goes 0 -> 1 (without a trip in the same step) | ch | 0 or Cnn | 1 above alarm SP, 2 above trip SP (ALARM ONLY), 3 fault | value; threshold = the SP crossed |
| 0x04 | FAULT | a G/B fault with action alarm latches, or an advisory first appears (once per code per boot) | ch / 0 | Gnn/Bnn/Cnn | bank | - |
| 0x05 | ACK | an accepted ACK changed something | 0 | 0 | 1 = RUN granted, 0 = alarm latches only | - |
| 0x06 | SETUP_ENTER | entry to `SETUP_INHIBIT` (RUN opened for setup) | 0 | 0 | state left | - |
| 0x07 | SETTING_CHANGE | a settings save completed (read back) | the single changed channel, 0 if several or global | 0 | bitmask: 1 protection, 2 name, 4 Modbus, 8 PIN | old / new trip SP x10 when one channel's trip SP changed, else 0x8000 |
| 0x08 | CAL_CHANGE | a calibration save completed | channel if one baseline, 0 otherwise | 0 | 1 REF ratios, 2 baselines | - |
| 0x09 | SAVE_FAIL | save procedure step 10 | 0 | G02 | 0 settings, 1 calibration | - |
| 0x0A | RECOVERY | ACK+SET power-up gesture executed (PIN reset) | 0 | 0 | 0 | - |
| 0x0B | SERVICE_ENTER | service mode entered | 0 | 0 | 0 | - |
| 0x0C | EVENTS_LOST | after the queue overflowed, when it drains | 0 | 0 | lost count (saturates at 255) | - |

Not logged: ACK refusals, condition clears (the ACK records the clearing), repeated sets of a latch already set,
display-only states. This bounds the write rate by latches, which need a human ACK to re-arm (except POWER_UP).

### 8.3 Queue

RAM FIFO of 8 entries, written by the EEPROM writer one byte per pass after any save in progress. An entry takes
20 x 3.3 ms = 66 ms. Overflow drops the new entry and counts it; one `EVENTS_LOST` is logged when the queue drains. A
read-back mismatch of a written entry -> G22 (advisory). The event queue never delays protection.

### 8.4 Power-cycle counter (0xAA0, 8 slots x 8 B)

Slot = `u32 count`, `u32 ~count`. Value = highest count among valid slots (count and complement agree). At boot:
`power_cycles = value + 1`, written to the slot after the one holding the highest value (round-robin), then the
POWER_UP event is logged. No valid slot on a non-blank area -> restart from the highest torn-free value or 1, G23
advisory. Blank area -> 1, no advisory.

---

## 9. Defaults and blank board

A blank EEPROM (all 0xFF): no header, no settings, no calibration -> `CONFIG_LOCK` (G01) and G04. Nothing is
written at boot except the power-cycle counter and the POWER_UP event.

Values the setup edit copy starts from (0043 2.1; nothing safety-relevant invented):

| Field | Starts as | Note |
|---|---|---|
| type | **unset** (must be chosen: OFF, K, J, PT100 where allowed) | 0043: "none -> config lock" |
| mode | TRIP | 0043 2.1; 0034 D1 |
| name | 6 spaces | |
| alarm SP, trip SP | **unset** (must be entered) | never invented (I-100) |
| reset band | 5 C | 0043 2.1 |
| probe limit | table max of the chosen type (K 1372, J 1200, PT100 850) | 0043 2.1; the commissioning engineer lowers it to the probe's rating (0038 D2) |
| Modbus address / baud | **OPEN** (06); proposed 1 / 9600 (not safety-relevant) | |
| PIN | default from 05 (**OPEN**) | the recovery gesture resets to the same default |
| REF ratios | none: production calibration in service mode | G04 until done |
| burnout baselines | not learned (`0x7FFFFFFF`) | C06 per fitted TC channel until learned |

A save is accepted only when the whole record passes 3.3, so a partly configured board cannot leave `CONFIG_LOCK`.

---

## 10. Budget and wear

### 10.1 EEPROM budget (40-ch, 43 channels)

| Area | Needed at 43 ch | Allocated |
|---|---|---|
| reserved + layout header | 32 | 32 |
| settings A/B | 2 x 714 = 1428 | 1536 |
| calibration A/B | 2 x 214 = 428 | 512 |
| event ring | 640 | 640 |
| power-cycle counter | 64 | 64 |
| service scratch | 32 | 32 |
| **Total** | **2624** | **2816** |
| **Free of 4096** | 1472 | **1280** |

Against `CALCULATIONS` 10.8 (3456 B used, 640 B free with 44 per-channel A/B 24 B records): a whole-image A/B
record with 16 B per channel needs less, and adds names, probe limits and the power counter. **Verdict: fits,
1280 B (31 %) free.** To be added to `CALCULATIONS` 10.8 by whoever owns it (not edited here).

Alternative considered and rejected: per-channel A/B records (`CALCULATIONS` 9.8). They save fewer bytes per edit
but make a multi-channel change non-atomic and need a per-record sequence; at 43 channels the whole image fits.

### 10.2 Wear (100 000 cycles per cell, E2)

| Area | Assumed rate | Writes per cell per year | Years to 100 000 |
|---|---|---|---|
| settings record body | 1 save/day (commissioning ~100 saves in year 1) | ~183 (each copy gets every other save) | > 500 |
| settings magic bytes | 2 writes per save (invalidate + commit), 1 save/day | ~365 | ~270 |
| calibration | a few per year | < 10 | n/a |
| event ring | 30 events/day (10 power-ups + 20 others) | 30 x 365 / 32 = ~342 | ~290 |
| power counter | 10 boots/day | 3650 / 8 = ~456 | ~220 |

Failure case, a reset loop (e.g. a brown-out or watchdog loop at 1 boot/s): the power counter slots reach 100 000
after about 100 000 x 8 / 86 400 = **9.3 days**, the event ring after 100 000 x 32 / 86 400 = **37 days**. RUN is open
for the whole loop (every boot is latched) and the settings cells are not written, so the consequence is a worn
counter/log (G23/G22 advisories), not a protection loss. **OPEN** (owner): accept, or delay the boot writes until the
first validated scan.

---

## 11. OPEN in this file

1. ATmega1284P EEPROM endurance and write time to be re-read from the datasheet (E2).
2. PIN format and default (05); name character set (05); Modbus defaults (06).
3. Require at least one fitted TRIP channel for a valid record (3.3 rule 8)?
4. REF-ratio plausibility window and burnout baseline units (02); RTD bank stored check value.
5. Baseline learning trigger screen (05/07); whether a type change forces relearning.
6. Reset-loop wear of the counter and ring (10.2).
7. `CALCULATIONS` 10.8 to be updated with this map (2816 B allocated, 1280 B free).
