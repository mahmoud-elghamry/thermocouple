# 0021 — Every function on its own A4 sheet; the root becomes an A4 index

* Status: accepted; amends `0019` (which rejected this as option (a))
* Date: 2026-09-26
* Deciders: owner (asked again for A4 sheets by function), agent (the split)
* Relates to: `I-062`, `0019`

## Context

`0019` split out only the channels and left everything else on an A3 root.
It rejected one A4 sheet per function because about 65 nets inside those
blocks would gain a sheet path. Many of them are named in the net-class
patterns, which drive the isolation rules, in the plane generator, and in
`check_board.py`. The owner asked again for what was originally agreed: the
power supply, the MCU and the rest each on their own A4 page.

The risk `0019` avoided is real but checkable. A renamed net that misses its
pattern falls to `Default`, and the isolation rules then treat it as control
side. That happened once in testing (499 violations, `0019`). It can be
proven not to happen by comparing every net's class before and after.

## Decision

Four functional sheets, each A4 and used once. The root is an A4 page holding
their blocks and the eight channel blocks:

| Sheet | File | Contents |
|---|---|---|
| POWER | `power.kicad_sch` | J1, F1, D1/D2, LM5164 buck |
| MCU | `mcu.kicad_sch` | ATmega32A, crystal, reset, LCD, buttons, ISP |
| ISOLATION | `isolation.kicad_sch` | ISO7760/ISO7761, IA0505S, LP2985 |
| RELAY_RS485 | `relay_rs485.kicad_sch` | K1 drive and J3, ADM2587E and J4 |

A net shared between sheets goes through a sheet pin to a root label with its
old name, so it keeps that name. **56 nets that stay inside one sheet gain its
path**: for example `/+24V_RAW` becomes `/POWER/+24V_RAW` and `/RELAY_COM`
becomes `/RELAY_RS485/RELAY_COM`.

How it is made safe:

* `apply_rules.py` patterns name the new paths.
* `board/units.bare()` drops a functional-sheet path, so the generator,
  stitching, zones and `check_board.py` keep matching `GND_RS485` and the
  others by function. `find_net()` finds a net wherever its sheet is.
* `sch_layout/funcsheets.py`, called from `hier.py`, derives the sheets from
  the flat wired drawing, moving each block by whole grid steps.

## Proof, 2026-09-26, workstation, KiCad 10.0.6

* `netlist_fingerprint.py --allow-renames`: 645 pins on the same nets, 201
  components unchanged, 56 renames and nothing else. The baseline was
  regenerated from that netlist, with the reason written into it.
* **Netclass of every one of the 162 board nets compared before and after the
  rename: 0 changed.**
* `validate.ps1`: ERC 0/0, netlist IDENTICAL, MPN 128/128, DRC 0 errors, 0
  warnings, 0 unconnected, 0 parity. `check_board.py`: all 6 ok.
* The board's copper is unchanged. Nets were renamed in place
  (`rename_board_nets.py`), and `kicad-tool pcb sync` re-linked the
  footprints to their new sheets.

## Consequences

* A new net inside a functional sheet needs its pattern written as
  `/SHEET/NAME` in `apply_rules.py`. Without it, the net silently becomes
  `Default`.
* The PDF now has 13 pages: the root, the 4 functions, and TC1–TC8. The eight
  channel pages share one drawing and differ only in reference designators
  (U2 on TC1, U3 on TC2, and so on).
