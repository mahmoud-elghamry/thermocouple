# 05 - Settings, calibration and events (EEPROM)

Decided behaviour: `0043` sections 2, 5, 8. Pattern: copy-edit-validate-commit (`01` 4.1). Normative for
`settings`, `events`, `store_task` and MCAL `eeprom`.

## 1. EEPROM map (ATmega1284P, 4096 bytes, little-endian)

| Address | Size | Content |
|---|---|---|
| 0x0000 | 16 | device header: magic `'T','F'`, layout version (1), board type, reserved |
| 0x0010 | 16 | power-cycle counter: `uint32` value, `uint32` complement, written twice (two slots, 8 B each) |
| 0x0040 | 768 | settings record **A** |
| 0x0340 | 768 | settings record **B** |
| 0x0640 | 256 | calibration record **A** |
| 0x0740 | 256 | calibration record **B** |
| 0x0840 | 512 | event ring: 32 entries x 16 B |
| 0x0A40 | 1216 | free (future: Modbus write log, more events) |
| 0x0F00 | 256 | service-mode scratch area (EEPROM test only; never holds settings) |

EESAVE fuse keeps all of it across re-programming (`02`).

## 2. Settings record (768 B slot)

### 2.1 Layout

| Offset | Type | Field | Valid range |
|---|---|---|---|
| 0 | u16 | magic `0x5354` ("ST") | exact |
| 2 | u8 | schema version | 1 |
| 3 | u8 | board type | 8, 24, 40 - must equal the build |
| 4 | u8 | channel count | 8, 24, 43 - must equal `board_cfg` |
| 5 | u8 | reserved | 0 |
| 6 | u32 | sequence number | incremented on every save |
| 10 | u8 | Modbus address | 1..247 |
| 11 | u8 | Modbus baud code | 0 = 9600, 1 = 19200 |
| 12 | u16 | setup PIN (4 BCD digits) | each nibble 0..9 |
| 14 | u8[2] | reserved | 0 |
| 16 | 16 x N | channel blocks (2.2) | |
| 16 + 16N | u16 | CRC16 over bytes 0 .. 16+16N-1 | |

N = channel count; 40-ch: 16 + 688 + 2 = 706 B < 768.

### 2.2 Channel block (16 B)

| Offset | Type | Field | Valid range |
|---|---|---|---|
| 0 | u8 | type | 0 OFF, 1 K, 2 J, 3 PT100 (PT100 only on 40-ch channels 41-43; TC types never there) |
| 1 | u8 | mode | 0 TRIP, 1 ALARM ONLY |
| 2 | char[6] | name | printable ASCII 0x20..0x7E, space-padded |
| 8 | i16 | alarm SP, 0.1 C | 0 <= alarm < trip |
| 10 | i16 | trip SP, 0.1 C | alarm < trip <= probe limit |
| 12 | u8 | reset band, 1 C | 2..50 |
| 13 | u8 | reserved | 0 |
| 14 | i16 | probe limit, 0.1 C | <= type table max (K 1372 C, J 1200 C, PT100 850 C) |

For type OFF the other fields are ignored but must still be in range (defaults 0) so the CRC and the validator
stay simple.

### 2.3 Serialisation and CRC

Explicit field-by-field packing (no C struct copy - padding and endianness must not matter, CALCULATIONS 9.8).
CRC16-CCITT, polynomial 0x1021, init 0xFFFF, no reflection, no final XOR (same as the 8-ch code).

## 3. Validation (pure `settings_validate`, whole record)

A record is **valid** only if all hold: magic, schema version, board type and channel count match the build;
CRC matches; every field in its range (2.1, 2.2); for every fitted channel (type != OFF): alarm < trip <= probe
limit <= type max, and trip SP is present (non-zero record written by commissioning, never a default); PT100 only
where `board_cfg` has an RTD input; at least one channel fitted. Any failure -> the record is invalid (never
"partly used").

## 4. Boot selection

| A | B | Use |
|---|---|---|
| valid | valid | the higher sequence number (modular compare) |
| valid | invalid | A |
| invalid | valid | B |
| invalid | invalid | none -> `CONFIG_LOCK` (G01); RUN never granted; ACK cannot clear it |

Blank EEPROM (all 0xFF) is simply "both invalid". Nothing is invented: a blank board shows `LOCKED: SETUP` and
waits for commissioning (`06`).

## 5. Save (commit) procedure (`store_task`, one step per loop)

1. Validator passes on the new record (in RAM). If the change touches any protection field (type, mode, alarm SP,
   trip SP, band, probe limit), protection first goes to `START_LATCHED` (RUN opens, `04` section 4).
2. Sequence = active sequence + 1; CRC computed.
3. Write it to the **inactive** slot, using the EEPROM's own byte write with the ready flag polled (one byte per
   loop step keeps the loop short; ~3.4 ms per byte, ~2.4 s for a 706 B record on the 40-ch - acceptable since
   RUN is already open).
4. Read the whole slot back and validate it (3).
5. On success: switch the active pointer to the new record; event `SETTINGS_CHANGED` (or `NAME_CHANGED`); if
   protection fields changed, protection stays `START_LATCHED` until ACK.
6. On failure: the old record stays active; raise G02 (trip until a retry succeeds); retry once automatically,
   then on the next commit attempt.

**Power cut at any step:** before step 5 the old copy is intact and has the higher valid sequence, or the new copy
fails CRC -> boot uses the old copy. After step 4 both are valid and the new one has the higher sequence -> boot
uses the new one. No step leaves zero valid copies unless both were already invalid.

Names only: the same procedure without the trip; the contact is not opened.

## 6. Calibration record (256 B slot, A/B like settings)

| Offset | Type | Field |
|---|---|---|
| 0 | u16 | magic `0x434C` ("CL") |
| 2 | u8 | version 1 |
| 3 | u8 | bank count |
| 4 | u32 | sequence |
| 8 | i32 x 6 | REF3030 / internal-reference ratio per bank, ppm deviation from nominal (`03` REF check) |
| 32 | i32 x 43 | burnout baseline per channel, nV (`03` burnout window) |
| 204 | u16 | CRC16 |

* Written in service mode (`08`): `CAL REF` (automatic, no instrument needed) and `LEARN BURNOUT` (with every
  fitted thermocouple connected and intact). Both are part of commissioning (`06`).
* Invalid or missing -> `CONFIG_LOCK` with G10 (`LOCKED: CALIBRATE`). Same A/B save and power-cut rules as 5.

## 7. Events

### 7.1 Entry (16 B)

| Offset | Type | Field |
|---|---|---|
| 0 | u16 | sequence (modular; the entry with the highest sequence is the newest) |
| 2 | u8 | event type (7.2) |
| 3 | u8 | code (fault code index, or 0) |
| 4 | u8 | channel 1..43 or 0 |
| 5 | u16 | power-cycle count (low 16 bits) |
| 7 | u24 | uptime, s (wraps after 194 days) |
| 10 | i16 | value, 0.1 C (or 0) |
| 12 | i16 | threshold, 0.1 C (or 0) |
| 14 | u8 | reserved |
| 15 | u8 | CRC8 (poly 0x07) over bytes 0..14 |

Ring of 32; the next write goes to the slot after the newest valid entry. An entry with a bad CRC is skipped
when reading (shown as `--`), never repaired.

### 7.2 Types (logged on transitions only, never every scan)

| Type | When |
|---|---|
| 1 POWER_UP | each boot (code: G11/G12 if reset by watchdog/brown-out) |
| 2 TRIP | entering `TRIPPED`, and each *new* trip cause while tripped (code, channel, value, threshold) |
| 3 ALARM | a new alarm cause appears |
| 4 FAULT | a fault code becomes active (once per activation) |
| 5 ACK | accepted ACK (code 0) |
| 6 SETTINGS_CHANGED | protection settings committed (channel 0 = several) |
| 7 NAME_CHANGED | names committed |
| 8 SERVICE_ENTRY | service mode entered |
| 9 CALIBRATION | calibration record written |
| 10 PIN_RESET | PIN recovery used |

### 7.3 Budget and wear

* Writes per year (estimate, generous): 10 boots/day -> 3,650 power-cycle writes (8 B, alternating slots);
  events ~20/day -> 7,300 entries, each cell rewritten every 32 entries -> ~230 writes/cell/year; settings a few
  per year. EEPROM endurance 100,000 cycles (datasheet) -> > 100 years for every area.
* RAM: active settings 706 B + working copy 706 B (40-ch) + calibration 206 B + event head 16 B ~ 1.7 KB of 16 KB.
