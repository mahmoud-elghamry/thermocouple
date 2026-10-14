# 0036 - Cheaper-parts variant of the 24-ch board (branch `cheaper-parts`)

* Status: accepted (owner, 2026-10-12: "start, and add your recommendations"; RS-485 and alarm
  relay choices and the TMP126 proposal are the owner's own; external watchdog removed by the owner)
* Date: 2026-10-12
* Builds on: `0031`, `0032` (part picks), `0035` (I-111 repair); I-109 (cost options)
* Evidence: `production/review-20261012-cheaper/` (local): `frontend-alternatives.md`,
  `digital-power-alternatives.md`, `pcb-and-similar-boards.md`, `review-tmp126-watchdog.md`

## Context

Parts were ~$105/board (`gen/cost.py`, LCSC 10-piece prices). The owner asked for a cheaper
version without losing protection. Three research passes (front end, digital/power, PCB/assembly)
and one independent circuit review were run before any change. Rule: AD7124 front end, input
protection, isolation and the trip path stay as they are.

## Decisions

**D1 - Cold-junction sensor: TMP126DCKR (TI, LCSC C5219998) replaces ADT7310 x6.**
Owner's proposal. ~$2.24 against $5.40 (10 pcs), ~$19/board; +/-0.25 degC (ADT7310 +/-0.5);
SC-70-6. It has one bidirectional SIO pin instead of DIN/DOUT: every SIO sits on DOUT_ISO, and
one **R443 22k** joins DIN_ISO to DOUT_ISO (TI datasheet 9.2 uses 10k; 22k halves the AD7124
DOUT load to ~0.15 mA, near its 0.1 mA VOH spec - review item a). R415 (100k DOUT pull-up) is
removed: R443 now defines DOUT with all devices deselected. ALERT unused, tied to GND_ISO.
* Rejected: TMP117 (I2C, 4 addresses, a second bus), TMP127 (+/-0.8 degC, no CRC), NTC/Pt1000
  (all 16 AD7124 inputs are used, would need another ADC), 3 sensors instead of 6 (~$10 once the
  sensors are cheap, loses the second point per bank; needs the I-114 gradient data).
* Placement: the input networks fill the strip from the ADCs to the terminals; the only gap
  (~3 x 2 mm, at the J101/J102 seam) would need the TC traces re-routed (`0035` D2). The sensors
  stay in their banks, moved <= 8 mm to the nearest clear spot beside their 100 nF
  (`capnear.py`). I-114 stays a bench measurement.

**D2 - RS-485 block: footprints stay, parts not fitted (DNP).** Not in the requirements; the
owner wants the place kept so a site can have it soldered later. 16 parts DNP (U703, D731,
C731-C736, R733-R736, JP731-JP733, J703), ~$8.6/board. R737 (DE pull-down) and R738 (RxD
pull-up) stay fitted so the MCU pins are defined. `fab.py` drops DNP parts from BOM and CPL and
lists them in `DNP.txt`; `cost.py` skips them.

**D3 - Drop-in substitutions (same footprint, same pinout):**
* ISO7761DWR x3 -> **CA-IS3761HW** (Chipanalog, C528656): 5 forward / 1 reverse, default output
  high, SOIC-16W (checked on the LCSC listing 2026-10-12), ~$3.9/board.
* 3296W trimmer -> BOCHEN 3296W-1-103 (C118954), 10k; ~$0.8.
* 22u 25 V X7R 1210 -> SAMWHA CS3225X7R226K250NRL (C2918511); ~$0.4.

**D4 - Alarm relay stays fitted** (owner: ~$2 is not worth it). It may be left off later.

**D5 - External window watchdog: tried and removed (owner, 2026-10-12).** A TPS3430 resetting the
MCU was added and reviewed. Removed because it adds a new way to stop a running engine (a
scan that runs long misses the window, 0.12-0.71 s with the parts at hand) and protects only
against a missing WDTON fuse, which the production test checks. The hang hazard is closed by
the I-118 firmware fix plus the internal watchdog; a real hang still opens the contact.

**D6 - Not taken now:** ATmega644PA (-$2.5, 4 KB RAM, 101 in stock, firmware unknown);
ADS1248 x6 instead of AD7124 (-$5, full re-route); Chinese 24-bit ADCs (no burnout source or
CRC confirmed); 2-layer PCB (`0028`, uV island). Fab choice (NORI ~$220 vs JLCPCB ~$55 bare for
10, `pcb-and-similar-boards.md`) is the owner's, outside this decision.

**D7 - Screw terminals J601, J701, J702, J703 turned 180 deg: wire entry at the board edge** (owner
spotted it in the 3D view, 2026-10-12). They faced into the board with the relays ~2 mm in front: no
wire could go in. Turned about the middle pin, pin numbers swapped in the schematic (pin 3 <-> 1), so
each position keeps its net, its silkscreen label and its copper. J703's back then touched the RS-485
row: C733/C734/C736/R734/R735/D731 moved 0.5 mm with their track ends; BIAS_B rerouted around pin 1.
The part fits either way round, so ORDER-NOTES names the direction.

**D8 - Supplier files are a request for a quotation, not conditions** (owner, 2026-10-12). LCSC codes
are reference part numbers; equivalents welcome; preferences stated as preferences; a word asked before
replacing the few accuracy parts. BOM/CPL renamed `BOM.csv`/`CPL.csv`; the supplier's ACCESSORIES.csv
carries only what they could supply, without internal notes. Design sources (KiCad files, schematic
PDF) are not sent unless asked. NORI asked for the assembly specification in one file (2026-10-14):
`ASSEMBLY-SPEC.pdf` (`gen/assembly_spec.py`) adds the power-on test - 24 V, current-limited, expected
voltages at the 11 test points, GND-GNDI open - and what we ask back with the boards.

## Consequences

* Parts ~$105 -> ~$72/board at 10-piece prices, ~$65 at the real order quantity (CALCULATIONS 8.1).
* Firmware (I-119): TMP126 writes at <= ~40 kHz (22k into the bus capacitance, CALCULATIONS 8.3);
  one CS low at a time, >= 1 us between CS edges, no AD7124 continuous read; DOUT echoes MOSI
  when nothing is selected, so a dead sensor can read 0x0000 = 0 degC: use the TMP126 CRC and
  device ID (0x2126) on every read.
* Board: `gen/delta.py` carries a schematic change onto the routed board (replace, add,
  remove, re-net, DNP) without regenerating.
