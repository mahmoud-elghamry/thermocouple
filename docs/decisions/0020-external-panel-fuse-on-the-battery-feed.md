# 0020 — An external 1 A time-delay DC fuse at the battery end of the supply lead

* Status: accepted
* Date: 2026-09-26
* Deciders: owner
* Relates to: `I-028` (a), `0016`

## Context

The unit is fed from the engine's 24 V battery (`0016`). The only over-current
device on the board is `F1`, a 1206 PTC (0.5 A hold). A PTC limits a moderate
overload, but it interrupts only about 40 A, and a battery pushes thousands of
amps into a short. A short in the supply lead, or in the board's input
before `F1`, would be fed with nothing to break it. The lead would then burn
instead of opening.

The board load is small: 94 mA at 24 V, and 0.38 A at the 6 V cranking floor
(`CALCULATIONS.md` 1.8, 1.9).

## Options

* **(a) An external fuse in the + lead, at the battery end, sized for the
  wire and the unit.** The board is unchanged.
* **(b) A bigger fuse on the board.** It would protect the board but not the
  lead from the battery to the panel, which is where the dangerous fault is.
  A cartridge fuse with real breaking capacity doesn't fit the input cluster
  either.
* **(c) Rely on `F1`.** Rejected: its breaking capacity is two orders of
  magnitude short of what a battery can deliver.

## Decision

**(a).** Panel wiring specification:

| | Requirement | Why |
|---|---|---|
| Position | + lead, **as close to the battery as practical** | A fuse protects the wire downstream of it; the lead between battery and fuse stays unprotected, so keep it short |
| Rating | **1 A, time-delay** (slow-blow) | 2.6x the worst load (0.38 A at cranking); rides the hot-plug inrush into `C53`/`C54` |
| Voltage | **DC-rated, 80 V DC or more** | Must still break during a 58 V suppressed load dump (`CALCULATIONS.md` 1.1). An AC rating alone doesn't count, and automotive blade fuses (32 V DC) are not enough |
| Breaking capacity | **10 kA or more at DC** | The battery's prospective short current is thousands of amps |
| Type | 10x38 mm DC cartridge in a DIN-rail fuse holder | Common in panels, rated for DC, and the holder isolates the unit for service |
| Not acceptable | 5x20 mm glass fuses | Breaking capacity is tens of amps |

Wire from the fuse to the panel: 1 mm² or more. A 1 A fuse protects any
common panel wire; the size is set by mechanical strength and volt drop, not
current.

## Consequences

* `F1` stays. It handles overloads on the board; the external fuse handles
  shorts in the wiring. Either one opening is safe, because the output is
  energised-to-run and loss of supply opens the contact.
* The exact part is chosen at purchase. Its datasheet must show a DC rating of
  80 V or more, 10 kA or more breaking capacity, and pre-arc I²t of 1 A²s or
  more (`CALCULATIONS.md` 1.9). No specific part number has been verified yet.
* The installation drawing and wiring notes for the panel must show this fuse.
