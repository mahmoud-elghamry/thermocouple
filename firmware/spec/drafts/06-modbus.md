# Family firmware specification - 06 Modbus RTU, read-only (DRAFT, research input)

Status: draft. `0043` rev 2 (sections 7 phase F3 and 8.6) wins on any disagreement; `00-overview.md` conventions apply.
**[V]** = checked against a source named in the line; **[D]** = design choice of this draft.
Fault codes `Gnn/Bnn/Cnn` are the codes of `03-protection.md`; this file only transports them.

## 1. Principles

* Modbus is **read-only in v1** (0043 section 8.6, owner 2026-10-20). Every write function code is answered with an
  exception. Writes may come in a later version; the address space is reserved for them now (section 8).
* **Never in the trip path** (`0031` D7, 0043 section 1): no Modbus request, flood, CRC error, bus fault or missing master
  can change RUN, ALARM, a latch, a setpoint or a scan. Comms loss does not alarm and never grants RUN. RUN, ACK and
  trip reset are never writable over Modbus, now or in any later version.
* Reads come from a **snapshot** taken at the end of each completed board scan, so one response is internally consistent
  (all values from the same `scan_no`; the scan number is in the global block).
* Service mode (07) switches Modbus off (the UART is then the 9600 8N1 report port).

## 2. Physical layer and framing

* `[V]` 24-ch RS-485 pins (`hardware/24ch/gen/c_mcu.py`): PD0 = UART_RX, PD1 = UART_TX, PD7 = RS485_DE (ADM2587E isolated
  transceiver, SM712 protection). 8-ch and 40-ch use the same pins (`main:hardware/family/gen/boards.py`).
* RTU framing: 1 start bit, 8 data bits, parity per setting, stop bits per setting, CRC-16 (polynomial 0xA001, initial
  0xFFFF, low byte sent first). Frame = address (1 byte), function (1), data, CRC (2).

### 2.1 Settings

| Setting | Values | Default | Notes |
|---|---|---|---|
| Address | 1..247 | 1 | 0 (broadcast) is never answered |
| Baud | 9600, 19200 | 9600 | 0043 section 2.2 |
| Parity | NONE, EVEN, ODD | NONE | NONE = 8N2 (two stop bits, as the Modbus serial spec requires without parity; a master using 8N1 still works because the receiver checks the first stop bit only); EVEN = 8E1; ODD = 8O1 |

Settings are edited in Setup > COMMS (05) and take effect at the end of the save, between frames. If the saved comms
settings are invalid, the defaults above are used (Modbus never blocks start-up and never depends on a valid protection
configuration).

### 2.2 Timing

Character time = 11 bits (start + 8 + parity-or-second-stop + stop).

| Item | 9600 | 19200 | Rule |
|---|---|---|---|
| Character | 1146 us | 573 us | |
| t1.5 | 1719 us | 859 us | **not checked** (the AVR USART receiver cannot time it without a dedicated capture; the CRC protects the frame) |
| t3.5 frame gap | 4010 us | 2005 us | A frame ends when no character has arrived for t3.5. Timer resolution <= 100 us (a dedicated hardware timer, assigned in 01; the 1 ms tick alone is not accepted) |
| Reply guard | >= 2 ms after the end of the request, and not before t3.5 | | gives masters and USB-RS485 adapters time to turn round [D] |
| Reply deadline | reply starts within 50 ms of the end of the request (target < 10 ms) | | [D] |
| DE turnaround | assert DE (PD7) -> wait >= 20 us -> first byte | | confirm against ADM2587E driver-enable time (OPEN-1) |
| After last byte | release DE when the USART transmit-complete flag is set (not the data-register-empty flag), then flush any echoed bytes | | the receiver is disabled with DE on the board; discard the RX FIFO on release |

If a new character arrives while a reply is waiting for its guard time, the pending reply is cancelled (the master
has already started a new request).

### 2.3 Receive state machine

* RX interrupt: store the byte in a 32-byte frame buffer, restart the t3.5 timer, set `rx_active`. Budget **<= 60 cycles
  including entry and exit** (7.5 us at 8 MHz). A byte beyond 32 is counted and dropped, and the frame is marked
  *overflow*.
* Framing error, parity error or data overrun on any byte: mark the frame *bad* (it is discarded at t3.5, no reply).
* Frame end (t3.5 expired): hand the frame to the main loop (one frame at a time; a second frame arriving before the first
  is handled replaces it and is counted as `overflow`).
* Main loop `modbus_poll()` handles at most **one frame per call**, never waits, and has a CPU budget of **<= 300 us per
  call** (CRC by 256-entry flash table: ~25 cycles per byte; reply build from the snapshot: <= 250 bytes copied).

### 2.4 Frame acceptance

A frame is processed only if: length >= 4 and <= 32, no overflow and no UART error, CRC correct, address = own address.
Everything else is dropped **silently** (no reply): wrong CRC, wrong address, broadcast (address 0), too short, bad parity.
Frames for other slaves cost only the receive interrupt (section 10).

## 3. Functions and exceptions

| Function | Behaviour |
|---|---|
| 03 Read Holding Registers | supported; the whole read map of section 5 (and its reserved ranges as in section 8) |
| 04 Read Input Registers | supported; **identical data and addresses as 03** (many masters read only one kind) |
| every other function (05, 06, 15, 16, 22, 23, 08, 43, ...) | exception 01 ILLEGAL FUNCTION (this includes every write) |

Request format for 03/04 is exactly 8 bytes: quantity 1..125 registers; addresses are 0-based protocol addresses.

| Exception | When |
|---|---|
| 01 ILLEGAL FUNCTION | function code other than 03 or 04 (including all writes and the reserved write registers) |
| 02 ILLEGAL DATA ADDRESS | any register of the requested range (start .. start+qty-1) is not mapped for this board (for example channel 9 on an 8-ch board, anything in the reserved write range 0x1000..0x1FFF in v1, anything above 0x1FFF) |
| 03 ILLEGAL DATA VALUE | quantity 0 or > 125, or request length wrong for the function |
| 04 SLAVE DEVICE FAILURE | no consistent snapshot available (internal error); never because of a protection state |
| 06 SLAVE BUSY | not used |

A request is treated atomically: if any register of the range fails, the whole request gets exception 02.

## 4. Data conventions

* Registers are 16 bits, big-endian on the wire. 32-bit values are two registers, **high word first** (address n = high).
* Temperatures, setpoints, band: `int16`, signed, **0.1 C** units (so a 600 C trip setpoint reads 6000).
* "Not available": `0x8000` (-32768) for signed values, `0xFFFF` for unsigned values and enumerations; never a made-up number.
* Channel numbers are 1-based (1..8, 1..24, 1..40 and PT100 41..43 on the 40-ch).
* Codes: a fault/cause is one word: high byte = class (`0x01` channel Cnn, `0x02` bank Bnn, `0x03` global Gnn), low byte = nn.
  `0x0000` = none. Bank faults add the bank index in the bank status word (section 5.2), not in the code.

## 5. Register map (identical start addresses on all boards; unfitted items read `n/a`)

### 5.1 Global block 0x0000 - 0x003F (always fully mapped)

| Addr | Name | Type | Content |
|---|---|---|---|
| 0x0000 | PROTO_REV | u16 | map revision, **1** |
| 0x0001 | BOARD_TYPE | u16 | 8, 24 or 40 |
| 0x0002 | CHANNEL_COUNT | u16 | 8, 24 or 43 (40 TC + 3 PT100) |
| 0x0003 | FW_VERSION | u16 | major in the high byte, minor in the low byte (`0x0100` = 1.0) |
| 0x0004 | FW_BUILD | u16 | build number |
| 0x0005 | STATUS | bits | b0 RUN_ACTUAL (read-back says closed), b1 ALARM_ACTUAL (alarm output active per read-back), b2 LATCHED, b3 CONFIG_LOCK, b4 SETUP_INHIBIT, b5 DEGRADED_CJ, b6 ANY_FAULT, b7 REF_OK (engine reference), b8 LOCAL_WRITE_ENABLE (always 0 in v1), b9..b15 0 |
| 0x0006 | LATCH_STATE | u16 | 0 RUN_PERMITTED, 1 TRIP_LATCHED, 2 START_LATCHED, 3 SETUP_INHIBIT, 4 CONFIG_LOCK (03 names map onto these) |
| 0x0007 | ALARM_COUNT | u16 | channels in alarm now |
| 0x0008 | TRIP_COUNT | u16 | channels with a latched trip |
| 0x0009 | FIRST_OUT_CH | u16 | 0 none; 1..43 channel; 0xFFFE = global or bank fault (no channel) |
| 0x000A | FIRST_OUT_CAUSE | u16 | code of section 4 (the cause the first-out reports in 03; over-temperature is the code 03 assigns to it) |
| 0x000B | FIRST_OUT_VALUE | s16 | 0.1 C at the trip, 0x8000 if none |
| 0x000C | FIRST_OUT_THRESH | s16 | 0.1 C, trip setpoint at the trip, 0x8000 if none |
| 0x000D-0x000E | FIRST_OUT_UPTIME | u32 | `uptime_s` at the trip (0 if none) |
| 0x000F | FIRST_OUT_PC | u16 | `power_cycles` (low 16 bits) at the trip |
| 0x0010 | FAULT_COUNT | u16 | number of active fault codes (may exceed 8) |
| 0x0011-0x0018 | FAULT[0..7] | u16 | active fault codes, oldest first; unused = 0 |
| 0x0019-0x001A | SCAN_NO | u32 | `scan_no` of this snapshot |
| 0x001B-0x001C | UPTIME_S | u32 | seconds since power-up |
| 0x001D-0x001E | POWER_CYCLES | u32 | `power_cycles` |
| 0x001F | SCAN_MS | u16 | duration of the last complete scan, ms, saturating |
| 0x0020-0x0024 | BANK_STATUS[A..E] | bits | b0..b7 bank fault nn (0 = none), b8 DEGRADED_CJ, b9 SCAN_VALID; banks that do not exist read 0xFFFF |
| 0x0025 | RTD_STATUS | bits | 40-ch only (same bit layout as a bank, fault nn in b0..b7); else 0xFFFF |
| 0x0026-0x002F | reserved | u16 | read as 0 |
| 0x0030 | DIAG_REQUESTS | u16 | valid requests answered since power-up (wraps) |
| 0x0031 | DIAG_CRC_ERR | u16 | frames dropped for CRC (wraps) |
| 0x0032 | DIAG_UART_ERR | u16 | framing, parity, overrun, overflow (wraps) |
| 0x0033 | DIAG_EXCEPTIONS | u16 | exception replies sent (wraps) |
| 0x0034 | DIAG_WRITE_REJECT | u16 | write function codes rejected (wraps) |
| 0x0035-0x003F | reserved | u16 | read as 0 |

Diagnostic counters are RAM only (reset at power-up) and never raise a fault or an alarm.

### 5.2 Channel blocks: 16 registers per channel, base = 0x0100 + 16 x (channel - 1)

Channels beyond the board's count are not mapped (exception 02): 8-ch ends at 0x017F, 24-ch at 0x027F, 40-ch at 0x03AF
(channel 43).

| Offset | Name | Type | Content |
|---|---|---|---|
| +0 | TEMP | s16 | 0.1 C; `0x8000` when the channel has no valid value (unset, off, fault, not yet measured) |
| +1 | FLAGS | bits | b0 VALID (hardware-valid result from the latest validated scan), b1 FAULT (sensor fault active), b2 ALARM (value >= alarm SP, or alarm-only fault), b3 TRIPPED (channel latched a trip), b4 CONFIGURED, b5 DEGRADED_CJ (its bank), b6 FIRST_OUT, b7 ALARM_ONLY, b8..b15 0 |
| +2 | AGE_SCANS | u16 | current `scan_no` minus the scan of this value, saturating at 0xFFFF; 0 = from this snapshot |
| +3 | FAULT_CODE | u16 | channel fault code (class 0x01, nn) or 0; a bank or global fault shows in the global block |
| +4 | TYPE | u16 | 0 UNSET, 1 OFF, 2 K, 3 J, 4 PT100 |
| +5 | MODE | u16 | 0 TRIP, 1 ALARM ONLY, 0xFFFF unset |
| +6 | STATE | u16 | 0 OFF, 1 NORMAL, 2 ALARM, 3 TRIP (latched), 4 FAULT, 5 UNCONFIGURED, 6 WAIT (no result yet) |
| +7 | ALARM_SP | s16 | 0.1 C; 0x8000 unset |
| +8 | TRIP_SP | s16 | 0.1 C; 0x8000 unset |
| +9..+15 | reserved | u16 | read as 0 |

Chosen for a PLC: one request of 5 or 6 channels x 16 = 80-96 registers reads a whole screen's worth; 24 channels need four
requests (<= 125 registers each). A master that needs all channels from one scan reads the global block first and
compares SCAN_NO with the AGE_SCANS of each channel.

## 6. Block map summary per board

| Block | 8-ch | 24-ch | 40-ch |
|---|---|---|---|
| 0x0000-0x003F global | yes | yes | yes |
| 0x0100-0x017F channels 1-8 | yes | yes | yes |
| 0x0180-0x027F channels 9-24 | no | yes | yes |
| 0x0280-0x03AF channels 25-43 | no | no | yes (25-40 TC, 41-43 PT100) |
| 0x1000-0x1FFF reserved write area | exception 02 | exception 02 | exception 02 |

## 7. Examples (24-ch, address 1)

Read STATUS .. FAULT[7] (20 registers from 0x0005):
`01 03 00 05 00 14 CRC` -> `01 03 28 <40 data bytes> CRC`. Read channel 3 temperature and flags:
`01 04 01 20 00 02 CRC` (0x0100 + 16 x 2 = 0x0120). A write: `01 06 01 20 00 00 CRC` -> `01 86 01 CRC` (exception 01).
A read of channel 25: `01 03 02 80 00 01 CRC` -> `01 83 02 CRC` (exception 02).

## 8. Reserved holding-register block (future setpoint writes)

Addresses `0x1000 - 0x1FFF` are reserved for **future writable holding registers**. In v1 nothing is mapped there: reads
return exception 02, writes exception 01. The planned layout (informative, may still change) leaves room for it:

| Planned range | Planned use |
|---|---|
| 0x1000 - 0x100F | write control: local-enable status mirror, staging area command, check word, result code |
| 0x1100 + 8 x (channel - 1) | per channel staging registers: ALARM_SP, TRIP_SP (0.1 C), band, probe limit |

Conditions for enabling writes later (0043 section 8.6, I-094; any v2 must meet all of them):

1. A **local enable on the keypad** (a setup menu item with a timeout); without it every write is refused.
2. **CRC**: the frame CRC, plus a separate check word over the staged block.
3. **Read-back**: the value is written through the same settings save path as the keypad (A/B write, read back,
   switch) and the master sees success only after the read-back matched.
4. **The same semantic checks as the keypad** (alarm SP < trip SP <= probe limit, ranges, type present).
5. **RUN inhibited**: writing is accepted only while RUN is open by the SETUP latch reason; after the write a new local
   ACK is needed.
6. **RUN, ACK and trip reset stay local-only forever** (`0031` D7): no register may ever perform them.

## 9. Behaviour by condition

| Condition | Behaviour |
|---|---|
| Before the first complete scan | replies are valid; channel TEMP `0x8000`, FLAGS.VALID 0, STATE 6 (WAIT) or 5/0 from settings |
| Config lock / blank settings | block 0 replies; channels STATE 5 UNCONFIGURED |
| Latched trip or fault | STATUS.LATCHED, LATCH_STATE, FIRST_OUT_* set; values stay live because evaluation continues while latched |
| Setup edit in progress | the map shows the **saved** settings, never the half-edited copy |
| Service mode | Modbus off, no replies |
| Master absent for any time | nothing happens |

## 10. Flood and malformed-frame requirement (protection timing is never starved)

Requirements the implementation and the F3 tests (08) must meet:

* CPU: the RX interrupt costs <= 60 cycles per byte. At 19200 baud (1920 bytes per second maximum) that is 115 200 cycles per
  second = **1.4 % of the CPU**. Reply path <= 300 us per frame, at most one frame per main-loop pass: a continuous
  stream of valid requests at 19200 baud (about 100 per second) costs <= 3 %.
* No interrupt-disabled section longer than 10 us in the Modbus code. The main loop never waits on the UART, the timer or
  DE; transmit is interrupt-driven (<= 40 cycles per byte), end-of-frame is a timer interrupt.
* Garbage with no gaps (a babbling master or noise) fills the 32-byte buffer, is dropped and counted; the buffer is
  re-armed at the next t3.5 silence. A stream without t3.5 silence yields no processing at all.
* Frames addressed to other slaves (typical on a shared bus) cost only the RX interrupt and one CRC-free address compare
  at frame end: **the CRC is computed only for frames addressed to this slave** [D].
* Malformed requests (length, quantity, function) never write anything and always end in an exception or silence; none
  changes any state except the diagnostic counters.
* Pass criteria (F3 gate, I-120 "Modbus flood"): with the bus saturated for 10 minutes at 19200 baud by (a) valid reads of the
  whole map, (b) random bytes, (c) valid frames with bad CRC, (d) frames for another address, (e) write requests: the board scan
  period stays within +-2 % of the quiet value, the RUN deadline is never missed, no watchdog reset occurs, ALARM/RUN outputs
  and the LCD behave identically, and the response to a normal request stays under 50 ms.
* A host test drives the framing code with a model clock for every row of section 2.4 and 3 (CRC, address, exceptions,
  quantity 0/126, address ranges per board, write rejects, exception 02 across a block end).

## 11. OPEN items

* OPEN-1: confirm ADM2587E DE enable time (20 us is a draft value), the dedicated timer for t3.5 (01 owns the timer map), and
  the RE/DE wiring so that echo is not received.
* OPEN-2: confirm with 03 the numeric mapping of LATCH_STATE and the cause code for over-temperature; the fault list is
  03's, not repeated here.
* OPEN-3: parity default NONE (8N2) is a guess at what the plant PLC expects; the owner or the integrator decides.
* OPEN-4: whether a PLC integrator wants min/max since ACK, band and probe limit in the channel block (reserved offsets 9..15
  are free; adding them later does not move any address).
