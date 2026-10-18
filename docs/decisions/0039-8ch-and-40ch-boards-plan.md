# 0039 - The new 8-ch and 40-ch boards: architecture and work plan

* Status: **accepted** (owner, 2026-10-14, rev 2 after review by Codex gpt-6-astra high). The owner then delegated
  the checkpoints marked OK below to Claude while away: Claude decides on its own recommendation, records each
  pick in this file under "Picks made under delegation", and the owner may reverse any of them.
* Builds on: `0031`-`0033` (24-ch architecture, size, routing), `0034`-`0036` (review repairs, cost-down),
  `0037` (family, one firmware), `0038` (K or J per channel)
* Owner input 2026-10-14: 8-ch derived from the 24-ch, 4 layers first (a 2-layer version for a fab in Egypt is
  studied after), keep trip + alarm relays, RS-485, five buttons + panel header, LCD header on standoffs (or a
  cable to the door); folder `hardware/8ch-new/`. The big board: 5 banks **all 40 TC channels fitted** (was
  "36 ch" in `0037`) plus **4 PT100 points**, because one input cannot serve both sensor types.

## Facts that shape the plan (24-ch sources)

* ATmega1284P: all 32 I/O pins used on the 24-ch (`hardware/24ch/gen/c_mcu.py:6-16`), 9 of them chip selects.
  The 40-ch needs 5 ADC + 10 TMP126 + 1 RTD ADC = 16 selects.
* CA-IS3761HW = 5 forward / 1 reverse, default output high (`c_iso.py:13-23`); the 24-ch uses 3.
* Reference designators: banks 1xx-3xx, isolation 4xx, MCU 5xx, power 6xx, outputs 7xx.
* Generator and tools are 24-ch specific: `bank(1..3)`/"ABC", `rules.py:19-25` geometry, `place.py` floor plan,
  `pincaps.py:27` (three ADCs), `maze.py:34` (170 x 145), `fanout.py:117` (REFIN1- grounded).
* `hardware/24ch/thermo24.xml` is **stale** (2026-10-11, still ADT7310/ISO7761/R415, Astra). The baseline is the
  release netlist `production/24ch-reva3-20261014-072946-4b1601/netlist.xml` + its `BOM.csv`.

## Decisions proposed

**D1 - Folders.** `hardware/family/gen/` = a narrow shared circuit library (blocks + board configs).
`hardware/8ch-new/` and `hardware/40ch/` = the boards, each with its own placement script, rules geometry,
README (with a pin-map table for the firmware chat) and STATE. `hardware/24ch/` is not touched; `hardware/8ch/`
(REV A2) stays reference. Placement and routing stay per board; routing tools get board size/geometry as
parameters, not a general framework.

**D2 - Shared circuit library, proven against the release.** Config "24" must reproduce the 4b1601 release:
same components, values, MPNs, footprints, DNP flags and complete pin connectivity (independent compare of the
exported netlist and BOM against the release files, hashes recorded) - not only `build.py`'s self-check against
its own model (`build.py:198`). Implementer: Sol in a git worktree, scope = `hardware/family/gen/` only;
Claude reviews the diff and re-runs the compare.

**D3 - Chip selects.** 8-ch: direct (CS_ADC1, CS_CJ1, CS_CJ2), 2x CA-IS3761HW. 40-ch: **one 74HC154 (4-to-16,
HC runs at 3.3 V) on the island**, A0-A3 + active-low EN through 2x CA-IS3761HW (forward SCLK, DIN, A0-A3, EN,
REFTEST = 8 of 10; reverse DOUT, REFOK); 5 MCU pins instead of 16. Firmware sequence with worst-case waits:
EN high -> wait (isolator propagation + decoder disable + old device releases DOUT) -> set address -> wait ->
EN low -> wait CS setup -> clock; >= 1 us between CS edges kept (I-119). Not claimed as a hardware guarantee:
island-side EN pull-up defined, start-up/brown-out/loss of either isolator supply tested; every transfer checks
the target's identity (device-specific register signature + CRC) so a stuck address line is caught;
address-fault injection at the bench. Rejected: one isolator channel per CS (19 forward, 4 isolators, MCU still
7 pins short); a bigger MCU (second firmware port); MCU-side expander (same isolator count).

**D4 - 40-ch: 5 identical banks, all 40 channels fitted** (owner). No population mask needed; both TMP126 of
every bank beside their headers.

**D5 - PT100: one RTD bank = one more AD7124-8**, 3-wire per ADI CN-0383, shared low-side Rref on REFIN1,
matched IOUT0/IOUT1 with current swapping, separate excitation and sense protection branches at the connector.
Owner asked for 4 points; 4 x 4 AIN uses every pin, so this ADC cannot keep the REF3030 check of `0032`.
**Resolved at step 4 with numbers, before layout:** (a) 4 points + another way to check Rref drift and gain, or
(b) 3 points + a fixed precision check resistor in the fourth slot. Owner decides. Also at step 4: excitation
current and Rref against compliance (AVDD - 0.37 V; 2 x 250 uA through 5.11k + 3.2k protection = 3.355 V
fails), reference-detect and PGA range, self-heating, lead mismatch (0.1 ohm ~ 0.26 degC), fault coverage (each
lead open, pair short, sheath fault, Rref/return fault). RTDs must be insulated from sheath/frame. PT100 only
(PT1000 not offered unless the fixed hardware passes its whole range).

**D6 - Designed in from the start:** caps beside their pins (`pincaps` 0 before routing, I-111); TMP126 close to
its header with stitched isothermal copper (I-114; placement is not thermal validation - the gradient test stays);
V_BIAS guard pours (I-105); fiducials, RUN PERMIT C-NO label, panel-button header (I-112, I-113, `0034` D2);
terminals at the board edge (`0036` D7); router clearances below in-part pad gaps (`padcheck`).

**D7 - Feasibility before any schematic freeze** (step 4): island supply (DC-DC minimum load and start-up, LDO
dissipation, preload/clamp), 5 V and battery current, panel fuse; shared DOUT bus (6 ADCs + 10 TMP126 ~260-300 pF:
TMP126 writes ~25 kHz with 22k, not 40 kHz; 150 uA through R443 vs the ADC's 100 uA test condition - consider a
separate TMP126 data line); engine-reference broken-FEED detection with 40 bias paths (~1.05 V vs 1.32 V
threshold with 36, `c_iso.py:82,110-120`); scan latency with 6 concurrent ADCs, RTD swaps and diagnostics <= 1 s;
firmware flash/RAM/EEPROM for 40 + 4 channels (masks wider than 32 bits). Board sizes from to-scale floor plans
(`0031` D10): estimates 8-ch ~110-120 x 100 mm, 40-ch ~220 x 170 mm (+52 % area) - **preliminary quote before
the 40-ch layout is committed**.

## Work plan (each step ends with its gate report; **OK** = owner checkpoint)

| # | Step | Who | Gate / output |
|---|---|---|---|
| 0 | Plan OK | owner | **OK** |
| 1 | Shared circuit library + config "24" | Sol (worktree), Claude reviews | release compare: 0 differences; ERC 0/0 |
| 2 | 8-ch config + schematic (1 bank, direct CS) | Claude | ERC 0/0, compare vs model, cost |
| 3 | 8-ch feasibility (supply, fuse, size) + floor plan to scale | Sol (calcs) + Claude | `CALCULATIONS` sec. 9; **OK** on floor plan |
| 4 | 40-ch feasibility (all of D7) + RTD and decoder circuits; Astra review | Sol (calcs), Claude, Astra | written review; **OK** on RTD (a)/(b), size, quote |
| 5 | 8-ch board: new, sync, place, rules, padcheck, pincaps, fanout, route, maze/finish | Claude (only writer) | DRC 0/0/0, unconnected 0, pincaps 0 |
| 6 | 8-ch release (fab, assembly spec, quote) | Claude | release folder + MANIFEST; **OK** |
| 7 | 40-ch schematic | Claude | ERC 0/0, compare, cost |
| 8 | 40-ch floor plan | Claude | **OK** |
| 9 | 40-ch board + release | Claude | DRC 0/0/0, fab set; **OK** |
| P | Any time: datasheets/LCSC for new parts (74HC154, Rref 0.1 % low-drift, 3-position terminals) | Sol (read-only) | table with codes, stock, price |
| L | After step 6: 2-layer 8-ch study for a local fab | - | own decision |

Kept: one writer per board file; generative until placement is frozen, incremental after (`0012`); Sol never
writes a `.kicad_pcb` or the schematic; every Sol diff reviewed and gates re-run by Claude; nothing is committed
without the owner and only the owner merges. Boards are qualified at the bench (I-120) before machine use.

## Picks made under delegation (Claude, 2026-10-14; the owner may reverse any of them)

* **P1 - Board name 40 ch** (`hardware/40ch/`); "36 ch" swept from the entry documents.
* **P2 - Gated TMP126 command driver on both new boards (I-124).** Through R443 (22k) the SIO edge is
  ~1-2.5 us against TMP126's 100 ns maximum (datasheet 7.6, read 2026-10-14; Sol's `CALCULATIONS` 9.5/10.5),
  and R443 loads AD7124 DOUT ~150 uA. New circuit: 74LVC1G125 (U411) drives DIN onto SIO through 220R only
  while SIO_WR_N is low (spare isolator channel + MCU PC1; default-high isolator and pull-ups keep it off);
  100k defines DOUT when idle; R443 removed. The 24-ch REV A3 keeps R443 (no free MCU pin) - I-124.
* **P3 - 40-ch references:** banks D and E use 8xx and 9xx (4xx-7xx are isolation, MCU, power, outputs),
  the RTD bank 10xx; the decoder is U410 with R444/C420, the SIO driver U411/R445-R447/C421.
* **P4 - PT100 bank values** (`CALCULATIONS` 10.11, Astra review 2026-10-14): IOUT 2 x 250 uA swapped every
  reading, R_ref 2.49k 0.1 % (V_ref 1.245 V, above the 0.7-1 V reference-detect band), 330R headroom
  (0.165 V), gain 16 (311 ohm full scale), worst IOUT pin 2.27 V vs 2.93 V compliance; excitation and return
  limiters 1k 2512 1 W (a lead miswired to 24 V puts ~0.4 W in it), sense 2.2k 1206 + BAV199 + 1k; sense
  filter 1n caps to RTD_RET (pad leakage sees < 0.1 V); one 1k return limiter per probe into RTD_RET.
* **P5 - D5 choice (b): three PT100 points + an on-board 150R 0.1 % check resistor** in slot 4, wired
  through the same protection/filter network and read every scan (`c_rtd.py`). First pick was (a), four
  points with indirect diagnostics; Astra and Sol both rejected it: the internal-reference / ratiometric
  comparison measures I_exc x R_ref, so an R_ref drift hides inside the IOUT tolerance, and +2 % R_ref reads
  8.25 degC low at 150 degC (Astra). The owner asked for four; a fourth point needs a second RTD ADC (one more
  AD7124-8 + network + a 17th chip select; not designed) or the owner accepting (a) with that residual. Kept from (a): current-swap agreement, reference detect, gain-ratio test, idle
  test with both currents off (a sheath/frame fault on any probe makes the others read low).
* **P6 - 8-ch size: floor plan v2 130 x 137 mm with the LCD on the board** (as agreed: standoffs, header
  for a door cable as well). The owner asked about 100 x 100 (2026-10-14): not possible with the LCD on the
  board - the 98 x 60 mm module may cover only parts < ~7 mm, and terminals, buttons, the B0505 and the bulk
  capacitor must stay outside it. With the LCD on the door (cable only) the same parts place at 115 x 100 mm
  (scratch study: 0 overlaps; routed to 64 DRC violations / 15 unconnected, the same as v1) - the owner
  chooses. v1 (130 x 125) routed with 16 connections left that all had to cross the LCD header J502, a THT
  pin row between the top terminals and the relays/buck; v2 moves the LCD 13 mm down so every power and
  contact path stays above that row.
* **P7 - 40-ch size: floor plan v1 250 x 145 mm** = the 24-ch floor plan + a 52 mm right island column
  (bank E = bank D turned 180 degrees, RTD bank on the top edge) + a third bank on the bottom edge; the CS
  decoder sits in the gap between banks A and B. Cost estimate `CALCULATIONS` 10.12.
* **P8 - AD7124 SYNC tied to +3V3_ISO on the new boards** (no 10k pull-up R191/R291/R391/R891/R991/R1091;
  `boards.py sync_tied`). The firmware never drives SYNC (one ADC per bank, no synchronised starts); on the
  routed 8-ch the SYNC via blocked the only escape of AVDD pin 26 (the 24-ch had the same fight). Pin 27
  joins pin 26 with a 0.5 mm stub and the AVDD via sits where the 24-ch has it. The 24-ch keeps its R191.
* **P9 - 8-ch H4 is a plain NPTH**; CHASSIS = J601 pin 1 + plated H5 + C610/R607 in the top-left corner.
  A CHASSIS track to H4 crossed both relays' contacts (1.5 mm / 2 mm rules).
* **P10 - Layout method** (lesson of the night): parts that the finished 24-ch already places well are placed
  from its final coordinates (`hardware/40ch/gen/pos24.json`; 8-ch: MCU, buck and isolator neighbourhoods as
  relative tables), and `pincaps` is 0 before the router runs - the first 8-ch route had 13 caps too far.

## Notes for the firmware chat (the owner briefs it; not ISSUES rows)

* 8-ch: CS_ADC1 PB4, CS_CJ1 PB2, CS_CJ2 PC0, SIO_WR_N PC1; PB0, PB1, PC3-PC5 unused. 40-ch: CSA0-3 =
  PB0, PB1, PB2, PC0; CS_EN = PB4 (drive high before making it an output); SIO_WR_N = PC1; PC3-PC5 unused.
  Decoder Y0-Y4 = bank ADCs A-E, Y5 = RTD ADC, Y6-Y15 = TMP126 1-10.
* TMP126 frames are bit-banged (SPI off). Read: SIO_WR_N low for the 16 command clocks, keep the last bit
  >= 20 ns after rising edge 16, SIO_WR_N high, wait ~1 us (isolator + buffer), then falling edge 16 and the
  read. Write: keep driving through the payload and CRC. U411 stays off during every ADC transaction; idle
  DOUT is undefined (never read it). Decoder: EN high, wait (>= 1 us: isolator + HC at 3.3 V + DOUT release),
  address, wait, EN low, wait; identical devices are told apart by a unique value written to each at start-up
  and read back every scan (address-alias check), RUN inhibited until a fresh fully validated scan; brown-out
  of either isolator side re-initialises everything. RTD: wait for the reference RC (2.3 ms to 0.01 %) and
  restart the filter after every current change; never use a conversion that spans a change.

## Consequences

* `0037` "36 ch = 5 banks (40 inputs, 36 used)" becomes 40 fitted + 4 PT100 when this is accepted: sweep GOAL,
  AGENTS, STATE, `docs/superseded.txt`.
* New ISSUES rows tagged [8ch] / [40ch] as steps open; index lines in `docs/STATE.md`.
* The firmware chat gets, per board: pin map, CS scheme (direct / decoded + sequence), bank count, RTD bank.
