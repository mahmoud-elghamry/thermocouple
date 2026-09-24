# 0015 — One 5.0 mm terminal-block family for all eleven field connectors

* Status: accepted
* Date: 2026-09-15
* Deciders: owner (pitch ruling), agent (part selection)
* Supersedes: the `1935161` entries written with `I-051`

## Context

Ten connectors (`JTC1`–`JTC8`, `J1`, `J3`) carried MPN **1935161** against the
footprint `TerminalBlock_Phoenix_MKDS-1,5-3_1x03_P5.00mm_Horizontal`; `J4` used
the 4-position variant and had no MPN at all. `I-053` raised this as a *pitch*
question — 5.00 mm footprint against a part believed to be 5,08 mm.

The owner ruled that 0.08 mm per position is irrelevant, that everything would
still fit and work, and that re-footprinting ten connectors was not worth the
time. That ruling is correct and is honoured here: **no footprint was changed.**

Checking the order code before acting on the ruling showed the premise was
wrong, and wrong in a way the ruling does not cover. Phoenix **1935161 is
`PT 1,5/ 2-5,0-H` — two positions, 5.0 mm pitch.** Not an MKDS. The footprint's
pitch was right all along; the *position count* was not. Ordering it would have
delivered eleven connectors with one terminal too few, on every thermocouple
input and on the 24 V and relay terminals. The MKDS 1,5/3-5,08 that `I-053`
assumed is order code 1715734.

## Decision

All eleven field connectors take the KANGNEX **WJ128V-5.0** family:

| Ref | Part | LCSC | Positions |
|---|---|---|---|
| `JTC1`–`JTC8`, `J1`, `J3` | `WJ128V-5.0-3P` | `C8270` | 3 |
| `J4` | `WJ128V-5.0-04P-14-00A` | `C192769` | 4 |

`populate_schematic.py` was corrected as well, so a from-scratch rebuild cannot
reintroduce the old number.

## Alternatives rejected

* **Keep Phoenix, fix only the order code** (MKDS 1,5/3-5,08 = 1715734, and its
  4-way sibling). Correct electrically, but 5,08 mm — which would have forced
  the footprint change the owner just declined — and a specialty import for a
  board sourced from LCSC/JLCPCB in Egypt.
* **Cixi Kefa `KF128-5.0-3P` (`C474951`)** — equally valid, 5.0 mm, 3 positions,
  in stock. Rejected only because Kefa's 4-position 5.0 mm sibling is not
  listed at LCSC, so `J4` would have come from a second family. One family for
  all eleven is worth more than the price difference.

## Consequences

* Pitch now matches the footprint exactly: 5.0 mm on both sides, on all eleven.
* The footprint's silkscreen is the Phoenix MKDS body outline, so the KANGNEX
  housing may sit slightly outside it. Pads and pitch are what solder; this is a
  courtyard/silkscreen item to eyeball at layout, not a fit problem.
* Every orderable part on the board now has an MPN and an LCSC code. The only
  BOM rows without one are the nine test points, which are plated holes.
* Verified after the change: ERC **0 violations**, netlist fingerprint
  **188 / 155 / 613 IDENTICAL** to `netlist-baseline-reva1.json`.
