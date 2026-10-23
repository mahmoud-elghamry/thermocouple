# 07 - Modbus RTU (read-only in v1)

Decided behaviour: `0043` section 8 item 6 (read-only now; setpoint writes possible later under local enable,
CRC, read-back, the keypad's validation and RUN inhibited; RUN, ACK and trip reset local-only for good). Modbus
is never in the trip path (`0031` D7, I-086, I-094). Normative for `modbus`, drivers `rs485`, MCAL `uart`.

## 1. Physical and framing

* Isolated RS-485 (ADM2587E), UART0 PD0/PD1, driver enable DE on PD7 (`02`). Half duplex, slave only.
* 8 data bits, no parity, 2 stop bits (Modbus rule for no parity) - fixed; baud 9600 or 19200 from settings;
  address 1..247 from settings. Broadcast (address 0) is ignored (no writes exist).
* Inter-character gap > 1.5 characters inside a frame -> the frame is discarded (Modbus serial line 2.5.1.1).
  RX bytes are timestamped by Timer1 at 50 us resolution (`02` 4.4), so both limits are measurable at 19200.
  UART framing/overrun errors mark the frame bad (discarded).
* Frame end: silence >= 3.5 characters (9600: 4.0 ms; 19200: 1.75 ms per the Modbus spec's fixed 1.75 ms above
  19200 - use 2.0 ms at 19200). Measured with the 1 ms tick + the UART RX timestamp.
* Response: built into a 256 B TX buffer (largest response 5 + 2x64 = 133 B), sent by the UDRE interrupt one byte
  at a time; DE high before the first byte, low after the transmit-complete flag of the last byte. Turnaround delay before
  answering >= 3.5 characters after the request.

## 2. CPU budget (protection never starved)

* RX ISR: store byte + timestamp in a 64 B ring, nothing else (F4 measured 218 cycles = 27 us; at 19200 baud <= 6 % CPU). At 19200 baud that is <= 2,000 bytes/s ->
  < 1 % CPU even under a continuous flood.
* `modbus_task` processes at most one complete frame per loop, bounded to 1 ms; responses are built from the
  snapshot taken this loop (`01` 4). Frames with bad CRC, wrong length, wrong address or overflow are dropped
  silently; a flood of garbage only costs the ISR time above.

## 3. Functions

| Function | Use | Note |
|---|---|---|
| 03 Read Holding Registers | everything (same map as 04) | so SCADAs that only use 03 work |
| 04 Read Input Registers | everything | |
| 06, 16 and any other | - | exception 01 Illegal Function (writes rejected in v1) |

Max 64 registers per request; beyond the map or across a hole -> exception 02 Illegal Data Address.
Values not available yet (before the first scan) read as 0x8000 with the validity register telling why.

## 4. Register map (16-bit registers, 0-based addresses)

### 4.1 Global block 0..63

| Addr | Content | Unit / encoding |
|---|---|---|
| 0 | map version | 1 |
| 1 | board type | 8, 24, 40 |
| 2 | channel count | 8, 24, 43 |
| 3 | firmware version | major*256 + minor |
| 4 | firmware patch | |
| 5 | settings schema version | |
| 6 | protection state | 0 CONFIG_LOCK, 1 START_LATCHED, 2 RUN, 3 TRIPPED, 4 SERVICE |
| 7 | RUN coil-drive feedback (RUN_SENSE on the coil low side - infers coil drive, not contact continuity; a welded contact is an accepted limit, I-081) | 0 not driven, 1 driven |
| 8 | ALARM coil-drive feedback (same inference) | 0 not driven (= alarm), 1 driven |
| 9 | active alarm count | |
| 10 | first-out cause code | fault code index (table 9 of `04`), 0 none |
| 11 | first-out channel | 1..43 or 0 |
| 12 | first-out value | 0.1 C signed |
| 13 | first-out threshold | 0.1 C signed |
| 14-15 | scan number | u32, high word first |
| 16 | scan age | ms since the last validated board scan |
| 17 | power cycles | low 16 bits |
| 18-19 | uptime | s, u32, high word first |
| 20-27 | active fault bitmap | 128 bits, bit n = fault code index n |
| 28-35 | channels in trip (latched) | 128-bit bitmap, bit 0 = channel 1 |
| 36-43 | channels in alarm (active or latched) | bitmap |
| 44-51 | channels with fault | bitmap |
| 52 | last refused ACK reason | R1..R6 as 1..6, 0 none |
| 53-63 | reserved | 0 |

Fault code index: Gnn -> nn (1..20), B01..B15 -> 21..35, C01..C11 -> 41..51 (C10/C11 are first-out causes: over trip / over alarm SP) (stable, never reused). One bit per
code; which bank raised a B-code is in the event log and on the LCD.

### 4.2 Channel block, base 100 + 10*(ch-1), ch = 1..43

| Offset | Content | Encoding |
|---|---|---|
| 0 | temperature | 0.1 C signed; 0x8000 if not valid |
| 1 | state | 0 OFF, 1 NORMAL, 2 OVER_ALARM, 3 OVER_TRIP, 4 FAULT |
| 2 | flags | bit0 valid, bit1 open, bit2 range, bit3 CM fail, bit4 rate advisory, bit5 stuck advisory, bit6 trip latched, bit7 alarm latched |
| 3 | type | 0 OFF, 1 K, 2 J, 3 PT100 |
| 4 | mode | 0 TRIP, 1 ALARM ONLY |
| 5 | alarm SP | 0.1 C |
| 6 | trip SP | 0.1 C |
| 7 | reset band | 1 C |
| 8 | age | scans since this channel's last valid result (saturates at 65535) |
| 9 | reserved | 0 |

Channel block ends at 529. Names: 3 registers per channel at 600 + 3*(ch-1) (two ASCII chars per register,
first char in the high byte), 600..728.

### 4.3 Reserved write area (future, not implemented in v1)

Holding registers 1000..1999 are reserved for a later version: setpoint writes per channel (alarm SP, trip SP,
band), a write-enable handshake register, and a write status/result register. Conditions recorded in `0043`
8.6: local enable on the keypad (time-limited), CRC of the frame, the keypad's validator, RUN inhibited and a
local ACK, read-back of the stored value. v1 answers exception 02 for this range.

## 5. Tests

Poll every register on each board type; malformed frames (bad CRC, short, long, wrong address) produce no answer;
continuous 19200-baud garbage for 10 minutes changes neither trip timing (`04` 6.3) nor the loop period beyond
its budget; all write functions return exception 01.
