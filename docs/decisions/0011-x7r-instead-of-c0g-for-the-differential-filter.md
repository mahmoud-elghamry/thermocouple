---
status: accepted
date: 2026-09-08
deciders: Zain
---

# X7R instead of C0G for the thermocouple differential filter

## Context

Each of the eight channels has a 100 nF capacitor across `T+`/`T-` — `C1`,
`C6`, `C11`, `C16`, `C21`, `C26`, `C31`, `C36`. With the two 100 Ω series
resistors it forms the differential low-pass in front of the MAX31856, cutting
off around 8 kHz. Its partners `C2`/`C3` (10 nF to `GND_SENS`) form the
common-mode pair at around 159 kHz. The 10:1 capacitance ratio between them is
what keeps component tolerance from converting common-mode noise into
differential noise, which is the thing that destroys a microvolt measurement.

The schematic specified `100n C0G 50V` in an 0805 footprint.

**That part does not exist.** A parametric search of LCSC returns **zero**
100 nF C0G/NP0 parts in 0805 from any manufacturer, in stock or out. The
dielectric's permittivity is too low to reach 100 nF in that case size; the
smallest package that carries it is 1206, where 16 parts are available.

So the board could not be ordered as drawn. This was found on 2026-09-07 while
building `passives_catalog.json` for `I-007`, and is `I-035`.

## Decision

**Use X7R.** `CC0805KRX7R9BB104` — 100 nF, 50 V, ±10 %, JLCPCB basic part,
15.7 M in stock. The schematic `Value` now reads `100n X7R 50V` so the drawing,
the netlist and the BOM agree.

## Why X7R is acceptable *here*

C0G was the right instinct — X7R has a voltage coefficient, a temperature
coefficient and a piezoelectric response, and any of those modulating a
measurement filter would be bad. None of them applies to this position:

- **No DC bias.** The capacitor sits between `T+` and `T-`. A K-type
  thermocouple produces tens of microvolts, so the DC voltage across this part
  is essentially zero. X7R's capacitance loss is a function of applied DC bias;
  at zero bias it delivers its rated value.
- **Nothing to shake it.** X7R is microphonic, but `docs/decisions/0009`
  established that the unit lives in its own panel roughly 50 m from the
  engine. The board is not on the machine. There is no vibration to convert
  into charge.
- **The cutoff does not need to be precise.** The signal of interest is DC.
  A ±10 % part moves an 8 kHz corner to somewhere between 7.2 and 8.8 kHz,
  against a signal bandwidth of essentially zero. Nothing depends on where
  exactly that corner sits.
- **The ratio survives.** `C2`/`C3` stay C0G (`GRM2195C1H103JA01D`, in stock).
  The 10:1 differential-to-common-mode ratio, which is the part that actually
  protects CMRR, is unchanged.

## What was rejected

**Drop to 10 nF C0G**, which does exist in 0805. Rejected: it moves the
differential corner from ~8 kHz to ~80 kHz, giving up an order of magnitude of
filtering against whatever 50 m of cable picks up. That is a real measurement
regression to buy a dielectric whose advantages do not apply here.

**Move to a 1206 footprint** and keep C0G. Rejected: a footprint change means
regenerating the board, which breaks the REV A0 freeze
(`docs/decisions/0010`) and stops the order until a new route, DRC run and
Gerber set exist. The gain is a dielectric property this position cannot use.

**Order 1206 parts onto the 0805 pads.** Not considered seriously — a 1206 body
on 0805 pads is an assembly defect, not a substitution.

## Consequences

The PCB is untouched. The footprint is identical, and
`kicad-cli pcb drc --schematic-parity` reports **0 parity issues** after the
change, because KiCad's parity check compares footprints and nets, not value
text. `netlist_fingerprint.py` confirms 167 components / 154 nets / 555 pins,
unchanged.

`netlist-baseline-reva0.json` was deliberately revised to accept the nine value
changes, with the reason recorded inside the file. Eight are this decision; the
ninth is `C48`, an unrelated generator-versus-schematic drift found by the same
run and tracked as `I-044`.

If a REV A1 respin happens for other reasons, revisiting this is optional, not
required. There is no measurement this substitution is known to degrade.
