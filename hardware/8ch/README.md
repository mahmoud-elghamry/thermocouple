# 8-channel thermocouple protection board — engineering prototype

**Status: not released for fabrication.** See “Where this actually stands”
below before drawing any conclusion from a clean check report.

This directory is a self-contained KiCad 10 project. It does not share files
with, and must not be confused with, the single-channel board in `hardware/single-channel/`.

---

## What the board is

| | |
|---|---|
| Size / stack-up | 250 × 140 mm, 4 layers |
| Measurement | 8 × MAX31856, one per K-type input, on a shared isolated island |
| Controller | ATmega32A-PU in a DIP-40 socket, internal RC oscillator, 5 V |
| Local HMI | 16×2 HD44780 in 4-bit mode, five buttons, contrast pot |
| Output | Energised-to-run SPDT dry contact (G5LE-1 24 V) via a 2N7000 low-side switch |
| Comms | Isolated half-duplex RS-485 (ADM2587E) with jumper-selected termination and bias |
| Supply | 24 VDC in → PTC + series Schottky + TVS → TSR 1-2450 → 5 V |
| Sensor supply | IA0505S isolated DC-DC → LP2985-3.3 → +3V3_SENS |

### Layer stack-up

```
F.Cu    signal + ground pour
In1.Cu  ground planes   GND_SENS | GND_CTRL | GND_RS485
In2.Cu  supply planes   +3V3_SENS | +5V_CTRL | +5V_RS485
B.Cu    signal + ground pour + chassis/PE ring
```

No signal is routed on In1 or In2. Every outer-layer track therefore has an
uninterrupted return directly beneath it, and the In1/In2 pair provides the
interplane capacitance that does most of the high-frequency decoupling for the
microvolt front end.

### Three copper islands

```
      x=6           x=145  x=151.5                  x=208 x=214     x=244
   +-----------------+ gap +-------------------------+ gap +---------+
   |  SENSOR ISLAND  |     |  CONTROL ISLAND         |     |         |  y=6
   |  8 × MAX31856   |     |  ATmega32A, LCD,        |     |(control)|
   |  GND_SENS       |     |  relay, 24 V input      |     |         |  y=97
   |  +3V3_SENS      |     |                   ------+-----+---------+
   |                 |     |                   | gap band            |  y=99
   |                 |     |                   |   RS-485 ISLAND     |
   +-----------------+     +-------------------+   GND_RS485         |  y=134
```

Signals cross a barrier only through U10/U11 (ISO7760 / ISO7761) and U15
(ADM2587E). The gap bands are emitted as KiCad rule areas, so the autorouter
cannot bridge them and a reviewer can see the intent on the board.

A fourth net, `CHASSIS_SHIELD`, is the cable-shield / protective-earth
reference. It is a B.Cu loop 3 mm inside the board edge, bonded to the four
plated M3 mounting holes, to J1.3, J4.4 and the eight thermocouple shield
screws — deliberately isolated from all three signal grounds so a shield
current cannot become a measurement ground loop.

---

## Files

| File | Role |
|---|---|
| `thermocouple_8ch.kicad_sch` | schematic — the structural source of truth |
| `thermocouple_8ch.kicad_pcb` | board |
| `thermocouple_8ch.kicad_pro` | project, **including the net classes** |
| `thermocouple_8ch.kicad_dru` | custom clearance rules (isolation, relay, chassis) |
| `populate_schematic.py` | builds the schematic through kicad-tool |
| `apply_rules.py` | writes net classes and `.kicad_dru` into the project |
| `board/` | the generator, split by responsibility - see `board/__init__.py` |
| `generate_board.py` | command-line entry point for `board/` |
| `route.py` | DSN → Freerouting → SES, then pours, stitching and finishing |
| `close_gaps.py` | joins anything DRC still reports as unconnected |
| `check_board.py` | structural checks DRC cannot make (islands, barriers, decoupling, cold junction, filter symmetry) |
| `run_all.ps1` | snapshot validation by default; explicit regeneration after owner authorization |
| `validate.ps1` / `check_commands.ps1` | fresh copy, source hashes, checked native exits and report gates |
| `test_gates.ps1` | fault injection for native-command and report failures |

Design rules live in the **project**, not in the scripts. Anyone opening
`thermocouple_8ch.kicad_pro` in KiCad sees the same track widths, via sizes and
clearances the generator used.

---

## Validating and rebuilding

```powershell
pwsh -File hardware\8ch\run_all.ps1
```

The default validates a fresh snapshot under `production/` without changing the
source hardware, including zone refill on the copy before DRC. Errors stop the
pipeline; warnings remain visible. Full regeneration requires `-Regenerate` and
is not authorized during the owner's REV A0 freeze. The commands below are the
historical regeneration sequence, for a later authorized revision:

```bash
python populate_schematic.py --labels-only
kicad-cli sch erc --output erc-report.rpt --severity-error --severity-warning thermocouple_8ch.kicad_sch
kicad-cli sch export netlist --output thermocouple_8ch.net thermocouple_8ch.kicad_sch
python apply_rules.py
kicad-tool pcb sync thermocouple_8ch.kicad_pcb thermocouple_8ch.kicad_sch
"C:\Program Files\KiCad\10.0\bin\python.exe" generate_board.py
"C:\Program Files\KiCad\10.0\bin\python.exe" route.py --passes 40 --threads 1
"C:\Program Files\KiCad\10.0\bin\python.exe" check_board.py
kicad-cli pcb drc --output drc-report.rpt --severity-error --severity-warning --schematic-parity thermocouple_8ch.kicad_pcb
```

`generate_board.py` and `route.py` need KiCad 10's bundled Python (`pcbnew`).
Re-running regeneration discards the existing routing. Snapshot validation
checks the current saved board without relying on regeneration reproducibility.

### External tools

Routing needs **Freerouting 2.4.x** and a **Java 25** runtime. Neither is in
this repository. Defaults are `%LOCALAPPDATA%\kicad-tools\freerouting.jar` and
`%LOCALAPPDATA%\kicad-tools\jre25\*\bin\java.exe`; override with
`FREEROUTING_JAR` and `FREEROUTING_JAVA`. Freerouting 2.4.1 is compiled to
class-file version 69, so a Java 21 runtime will not load it.

---

## Check results

Read `erc-report.rpt` and `drc-report.rpt`; these numbers come from them.

| Check | Before | Now |
|---|---|---|
| clearance | 304 | **0** |
| shorting items | 19 | **0** |
| tracks crossing | 22 | **0** |
| dangling vias | 7 | 1 (warning) |
| hole clearance / hole-to-hole | 6 / 5 | **0 / 0** |
| zones intersecting | 2 | **0** |
| starved thermals | 2 | **0** |
| solder-mask bridges | 2 | **0** |
| footprint/symbol field mismatch | 146 | **0** |
| silkscreen overlap / over pad | 10 / 3 | 6 / 2 (warnings) |
| **unconnected items** | 46 | **0** |
| **schematic ↔ PCB parity** | — | **0** |
| ERC errors | 7 | **0** |
| ERC warnings | 189 | 171 (all `endpoint_off_grid`) |

**Zero errors.** The nine remaining violations are warnings: six silkscreen
overlaps, two pieces of silkscreen over a pad, and one dangling via.

`check_board.py` passes all six structural checks that DRC cannot make - island
membership, isolation barrier, decoupling proximity, cold-junction distance,
input-filter symmetry and routing completeness. Zero courtyard overlaps, zero
parts off the board edge, all 167 footprints carry a courtyard.

### Fabrication output

Generated into `production/8ch/` (not committed - regenerate it):

```bash
kicad-cli pcb export gerbers --output ../../production/8ch/     --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts     --subtract-soldermask thermocouple_8ch.kicad_pcb
kicad-cli pcb export drill --output ../../production/8ch/ --format excellon     --drill-origin absolute --excellon-units mm --generate-map --map-format gerberx2 thermocouple_8ch.kicad_pcb
kicad-cli pcb export pos --output ../../production/8ch/thermocouple_8ch-pos.csv     --format csv --units mm --side both thermocouple_8ch.kicad_pcb
kicad-cli pcb export ipcd356 --output ../../production/8ch/thermocouple_8ch.d356 thermocouple_8ch.kicad_pcb
```

Eleven Gerber layers, Excellon drill plus map, the `.gbrjob`, a placement CSV
and an IPC-D-356 netlist for the fab's electrical test.

**Do not hand-edit the board.** `generate_board.py` clears every track, via,
zone and drawing, so anything drawn by hand in KiCad is erased on the next run.
Fixes belong in `board/` or in `route.py`.

---

## Where this actually stands

Nothing here makes this board safe to put on a machine. The following remain
open and none of them can be closed by DRC, ERC, or a 3D render:

- **The shared sensor island is a conditional proof of concept.** It isolates
  the group of eight channels from the controller. It does **not** isolate the
  channels from each other. It is only valid if the eight thermocouple sheaths
  are measured to be at the same potential, on the same equipotential bond.
  That measurement has not been made.
- **MAX31856 is not a galvanic isolator.** It is a better thermocouple
  front end than MAX6675 — filtering, fault detection, input protection — but
  T+/T− are not separated from AGND/DGND. Its presence does not solve a
  grounded tip or a 50 m cable.
- **The isolation rules are functional, not certified.** `.kicad_dru` enforces
  3 mm between islands. That number comes from the tightest part on the board
  (the IA0505S module's own pin pitch), not from a creepage/clearance analysis
  against IEC 61010 at a stated working voltage and pollution degree.
- **The PE ring's spacing is set by connector geometry.** Screw terminals put
  the shield pin 5.00 mm from the adjacent signal pin, which leaves 2.4 mm of
  copper gap. The chassis clearance rule is 1.5 mm for that reason. It is not
  a mains-rated separation.
- **The dry contact is marked LOW-VOLTAGE LOAD ONLY** and its clearances are
  chosen to match that, not a mains rating.
- **No noise, EMC or real-sensor testing has been done.** Cables run about 50 m
  from engine cylinder bodies to a separate panel, with no VFD in the installation.
  Layout symmetry and a plane pair improve the odds;
  they do not substitute for measurement.
- **The unregulated isolated DC-DC needs review.** IA0505S is an unregulated
  ±5 V module. At the ~12 % load this island draws, its output can sit well
  above 5 V. The AP2112K was replaced by LP2985-3.3 with a higher input rating
  (decision 0002), but the converter's real output still needs measurement.
- **DRDY and FAULT are not brought to the MCU.** Both isolators are fully
  allocated (ISO7760: 6/6 forward; ISO7761: 5 forward + 1 reverse for MISO), so
  crossing sixteen more signals needs a second isolator plus fault-OR logic.
  The firmware reads the MAX31856 fault register (0x0F) on every sample. This
  is a deliberate trade-off — see the plan document — not an oversight.
- **The schematic is electrically correct but not a readable drawing.** It is
  generated as symbols plus net labels with no wires, on one sheet. It produces
  a correct netlist and it passes ERC, but no engineer can review or sign it in
  that form. Redrawing it as wired hierarchical sheets is outstanding work.
- **The passive catalog exists, but the filter specification still conflicts.**
  `passives_catalog.json` records MPNs and sourcing snapshots. The eight 100 nF
  differential capacitors still say C0G in the schematic while the catalog
  selects X7R (`I-035`). Resolve that discrepancy before ordering; stock and
  price snapshots are not a live availability guarantee.
