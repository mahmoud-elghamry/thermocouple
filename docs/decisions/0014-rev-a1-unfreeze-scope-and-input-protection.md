---
status: accepted
date: 2026-09-15
deciders: Zain
amends: 0010
---

# REV A1: unfreeze, scope, and the input protection part

## Context

`docs/decisions/0010` froze the board at REV A0 and collected three hardware
changes into a REV A1 set to be applied together. `run_all.ps1 -Regenerate` has
been unauthorized since, and `I-002` — the schematic redraw — was blocked behind
the question of whether to redraw first or change components first.

## Decision 1: REV A0 is unfrozen

The owner authorized the respin on 2026-09-14: *"اعمل كله ماعدا 028"*. That
permits a full regeneration, which re-routes the whole PCB and produces a board
that has to be verified from scratch. Nothing was fabricated under REV A0, so
nothing is stranded.

## Decision 2: scope

| In | Issue |
|---|---|
| `Y1` 8 MHz crystal + `C60`/`C61` 22 pF | `I-032` |
| `R53`/`R54` run-permit read-back divider | `I-016` |
| `D7`–`D22` thermocouple input protection | `I-045` |
| Silkscreen and the dangling via, riding along | `I-006`, `I-024` |

| Out | Why |
|---|---|
| `I-028` 24 V source | Owner deferred; it replaces the input stage, not two parts |
| `I-027` 1 MΩ bias resistors | Premise needs the MAX31856 datasheet, which we do not have — Analog Devices blocks automated download |
| `I-025` 2-layer | Owner: stay on four layers; two layers is a last resort if sourcing forces it |

## Decision 3: components first, then the redraw

The earlier plan in this session was to redraw first with the netlist frozen,
then add parts. That was wrong, and the owner said so: the generator places new
symbols at its own coordinates, so adding them after a hand layout means laying
out twice.

The safety argument that motivated redraw-first survives anyway. The fingerprint
gate's value is *"the redraw did not change connectivity"*, and that works
against **any** baseline established before the redraw. So:

    add parts -> regenerate -> re-baseline -> redraw against the new baseline

Layout happens once and the gate is still green during the risky step.

`populate_schematic.py` is additive (`if ref in existing: continue`), so this
also gives a clean division of labour for `I-002`: **the generator creates
symbols, with correct KiCad instance data; Konnect draws wires.** Symbols
created by hand without instance data are exactly what made the reverted
hierarchical redraw export zero components.

## Decision 4: BAV199 steering diodes, not a low-standoff TVS

A 3.3 V TVS across the input is the obvious protection part and it is the wrong
one. Measured from the datasheets on 2026-09-14 with `pdftotext`:

| | **BAV199** | PESD3V3L1BA |
|---|---|---|
| leakage typ | **0.003 nA** (3 pA) | 90 nA |
| leakage max | **5 nA** at V_R = 75 V | **2 µA** at V_RWM = 3.3 V |
| diode capacitance | **2 pF** | **101 pF** |
| price at LCSC | $0.0137 | $0.024–0.05 |

K-type gives 41 µV/°C. Leakage flows through the 100 Ω series resistor plus the
thermocouple's own resistance — roughly 200 Ω for 50 m — so the TVS worst case
is 2 µA × 200 Ω = 400 µV = **9.8 °C of error injected into the instrument whose
entire job is measuring temperature**, and leakage roughly doubles every 10 °C,
so a panel in an engine room makes it worse. BAV199's 5 nA is 0.024 °C.

The capacitance matters too: 101 pF of unmatched capacitance on a balanced pair
degrades the CMRR the whole front end exists to provide. 2 pF does not.

`Device:D_Dual_Series_AKC` is pin-exact for BAV199 in SOT-23 — pin 1 = A1,
pin 2 = K2, pin 3 = K1/A2 — so the part is wired pin 3 to the signal, pin 2 to
`+3V3_SENS`, pin 1 to `GND_SENS`, on `TC*_FILT_*` **after** the 100 Ω resistors
so those resistors limit the current into the diodes. 16 devices, $0.22 a unit.

**Open, to settle during board work:** the steering diodes dump surge current
into `+3V3_SENS`, and `LP2985` cannot sink. `C48` (4.7 µF) is probably enough,
but "probably" is not a number and the surge level has never been specified.

## Decision 5: `J6` pin 3 is disconnected

`PC2` was `SPARE_PC2` on the service/expansion header. It now carries
`RUN_PERMIT_SENSE`. Leaving it on the header would put a safety read-back one
jumper away from being forced high — on a protection device. The pin is now a
no-connect; five spare I/O remain on `J6`.

## What was measured

    populate_schematic.py   192 symbols (171 + 21)
    netlist                 167 -> 188 components, 154 -> 155 nets, 555 -> 613 pins
    fingerprint vs REV A0   48 differences, every one intended, no net lost a pin
    ERC                     0 errors, 192 endpoint_off_grid warnings and nothing else
    firmware build.ps1      exit 0; 3 suites pass; 5592 B flash (17.1%), was 5556 B

Arithmetic checks: 167 + 21 = 188. 555 + 16×3 + 2×2 + 2×2 + 1×2 = 613.
154 − `SPARE_PC2` − 2 unconnected-XTAL + `RUN_PERMIT_SENSE` + `XTAL1` + `XTAL2`
+ unconnected-`J6`-3 = 155.

The firmware half moved in the same change, as `0010` required:
`BOARD_HAS_RUN_PERMIT_SENSE` 0 → 1, low fuse `0x24` → `0x3F`. **A chip fused
`0x3F` on a board with no crystal waits forever for an oscillator and looks
bricked** — `fuses.md` now says so and `program.ps1` takes `-LowFuse 0x24`.

## Rejected

**Fold `I-028` in while the board is open.** Rejected by the owner, and the
engineering agrees: the battery case replaces the regulator, the bulk capacitors
and possibly adds an active clamp, and the two questions behind it (panel or
battery; suppressed alternator or not) are unanswered. Guessing produces a board
that has to be respun again.

**Add the `I-027` 1 MΩ resistors as cheap insurance.** Tempting at 8 × $0.01,
but `I-027` exists to ask a question — does the MAX31856 bias its own inputs? —
and the datasheet that answers it is the one document the project does not have.
Adding parts to settle a question nobody has answered is how the 101 pF TVS
would have got fitted.
