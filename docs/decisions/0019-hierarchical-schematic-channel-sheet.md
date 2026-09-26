# 0019 — A3 root plus one channel sheet used eight times

* Status: accepted
* Date: 2026-09-26
* Deciders: owner (asked for A4 sheets, a channel drawn once), agent (the split)
* Relates to: `I-062`, `I-002`, `docs/decisions/0012`

## Context

The schematic was one flat A2 sheet with all 201 parts. It was correct but
hard to print or read. The owner asked for sheets per function on A4, with
the thermocouple channel drawn once and used eight times.

Net names are not cosmetic here. `apply_rules.py` assigns net classes by name
pattern, and those classes drive the isolation rules in `.kicad_dru`. The
board generator finds the RS-485 planes by name, and `check_board.py` sorts
nets into islands by name. A hierarchical sheet prefixes every net that stays
inside it with the sheet path.

Measured on the netlist: only **seven** nets leave a channel (its CS, plus
SCK, MOSI, MISO, +3V3_SENS, GND_SENS and CHASSIS_SHIELD). The other blocks,
however, have 65 sheet-local nets, and many of them are named in the rules
and in the generator: `+5V_RS485`, `GND_RS485`, `RELAY_*`, `RS485_*`,
`+24V_*`, `+5V_ISO`.

## Options

* **(a) Every function on its own A4 sheet.** This renames about 65 nets
  across the isolation rules, the plane generator and the checks.
* **(b) The channels only, as one reused sheet; the rest stays on the root,
  packed onto A3.** This renames 40 nets, all inside channels, all following
  one pattern: `/TCn_FILT_P` becomes `/TCn/FILT_P`.
* **(c) Keep the old names** by bringing every internal net out to a root
  label. This needs more than a hundred extra labels on the root, which is
  more clutter than the flat sheet had.

## Decision

**(b).** It delivers what the owner wanted most: one channel drawing, reused.
It confines the renames to a single pattern, which three places can match.
The isolation-relevant names of the control, RS-485 and relay blocks are not
touched at all. The root is A3, not A4: the MCU, isolators, power supply,
RS-485 and relay together do not fit A4 at a readable size.

How it is done and proved:

* `sch_layout/hier.py` derives the two files from the flat wired sheet, as
  the last step of `build.py`. It refuses if any channel's symbols are not
  placed exactly like channel 1's.
* `netlist_fingerprint.py --allow-renames` matches nets by their pin sets:
  all 645 pins stayed on the same nets, no component was added or removed.
  Exactly two deliberate differences: the 40 renames, and JTC1–8's value
  `TCn_K_TYPE` becomes `K_TYPE`, because KiCad 10 keeps one value per symbol,
  not per sheet instance. The baseline was regenerated from that proven
  netlist, with the reason written into it.
* `apply_rules.py` patterns now read `/TC?/FILT_?`, `/TC?/RAW_?` and
  `/TC?/MISO_CH`. **Without that change the channel nets fall to Default,
  and DRC reported 499 isolation violations on a test copy.**
* `sch_layout/rename_board_nets.py` renames the board's nets in place, so
  pads, tracks and zones move together; `kicad-tool pcb sync` alone moved
  only the pads. Copper is unchanged.

## Consequences

* Result on the workstation, KiCad 10.0.6: ERC 0/0; netlist IDENTICAL to the
  revised baseline; DRC 0 errors, 0 warnings, 0 unconnected, 0 parity;
  `check_board.py` all 6 ok; all 40 channel nets in `SensorSignal`.
  `build.py` from `05d6abd` reproduces the result (IDENTICAL, ERC 0/0).
* A new channel-level net needs a pattern in `apply_rules.py` of the form
  `/TC?/NAME`.
* `validate.ps1` and `board_provenance.py` now carry `channel.kicad_sch`.
* The flat wired sheet exists only as an intermediate in `build.py`'s scratch
  folder. `populate_schematic.py` still writes flat, label-only output as
  before; `build.py` carries it to the hierarchy.
