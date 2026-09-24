# 0016 — LM5164 for a battery supply, replacing the TSR 1-2450

* Status: accepted
* Date: 2026-09-16
* Deciders: owner (source is a battery; cost ceiling), agent (part selection)
* Relates to: `I-028`, `docs/decisions/0009`, `docs/reference/CALCULATIONS.md` §1

## Context

`I-028` had been open since 2026-09-08 with two questions attached to it, and
the input stage could not be finished until both were answered:

1. Panel 24 V unit, or the engine battery?
2. If the battery, is the alternator load-dump suppressed?

On 2026-09-16 the owner answered (1): **the engine battery.** On (2) the owner
said plainly that confirmation is not obtainable, and set a cost constraint —
a small price difference is acceptable, a large one is not.

That settles the requirement even without an answer to (2). A 24 V system with
a *suppressed* alternator is specified for a **58 V load dump lasting roughly
350 ms** (ISO 16750-2 Test B). The fitted `TSR 1-2450` is rated 6.5–36 V. It
does not survive, and no amount of clamping fixes that, because a TVS rated for
a 10/1000 µs pulse is being asked to absorb an event 350 000 times longer.

An earlier draft of `I-028` had costed the obvious replacement, `R-78HB5.0-0.5L`
at **$18.32**, and that number is what kept the issue shut for a week. It was
also the wrong part in three ways beyond price.

## Decision

Replace the module with **`LM5164DDAR`** (`C477928`, $1.36) — a 6–100 V, 1 A
synchronous constant-on-time buck — and raise every part between `J1` and the
5 V rail to match.

| | TSR 1-2450 (fitted) | R-78HB (earlier plan) | **LM5164 (chosen)** |
|---|---|---|---|
| Input range | 6.5–36 V | 9–72 V | **6–100 V** |
| Margin over a 58 V load dump | none, it dies | 14 V | **42 V** |
| Cranking floor | 6.5 V | 9 V — *worse* | **6.0 V — better** |
| Output current | 1 A | 0.5 A — *halved* | **1 A** |
| LCSC price, qty 1 | $6.78 | $18.32 | **$1.36** |

Externals add about **$0.40**: 33 µH inductor (`C167888`-class, $0.05), two
100 V 1210 input ceramics ($0.26), bootstrap/ripple/divider parts (~$0.03).

**The fix is roughly $5 per unit cheaper than what it replaces.** The cost
constraint did not have to be traded against anything.

Three further input parts also fail at 58 V and were not previously flagged:

| Ref | Was | Why it fails | Now |
|---|---|---|---|
| `D1` | `SS34` | 40 V Schottky | `SS310`, 100 V (`C15874`) |
| `D2` | `SMBJ33A` | conducts at 58 V and burns | `SMBJ60A`, 60 V standoff, 96.8 V clamp (`C49066953`) |
| `C53` | 47 µF **50 V** | 50 V part on a 58 V rail | 22 µF **100 V**, `CP_Radial_D8.0mm` |
| `C54` | 2.2 µF **50 V** | same | 4.7 µF **100 V** 1210 |

`C53` shrinks from 47 µF to 22 µF deliberately. It was described as a
ride-through reservoir and is not one — 47 µF from 24 V to 6.5 V is 12.5 mJ,
which at 2.2 W is **5.7 ms**. Its real job is bulk and parallel damping for the
50 m feed, and 22 µF does that in a package that exists at 100 V.

All component values are derived in `docs/reference/CALCULATIONS.md` §1 from TI
datasheet SNVSAU4D, not chosen by eye.

## Alternatives rejected

* **`R-78HB5.0-0.5L`**, the plan of record until today. Rejected on four counts:
  $18.32 against $1.36; the current capability halves to 0.5 A against an
  estimated 0.405 A load, i.e. 81 % utilisation; the minimum input rises to
  9 V, making **cranking worse than the board is today**; and 72 V leaves less
  headroom than 100 V.
* **Keep the TSR and add a series surge clamp** (`LTC4364`, `C580878`, or a
  discrete P-FET clamp). Genuinely attractive at first: this unit draws only
  ~94 mA at 24 V, so a series element never passes more than 100 mA and the
  clamp's dissipation during a load dump is about 2 W for 350 ms — well inside
  a DPAK. It was rejected because the `LTC4364` costs **$11.25**, more than the
  regulator it would be protecting, and the discrete version needs a charge
  pump or a P-channel topology plus a safe-operating-area check against a real
  SOA curve — engineering risk and part count, to preserve a module that the
  wide-input IC beats on price anyway.
* **A big load-dump-rated TVS** (`SM8S33A`, `C312613`, 6.6 kW). Rejected
  because the TVS has to absorb the *alternator*, which can deliver tens of
  amps, while a series or wide-input solution only has to handle the *load*,
  which is 100 mA. Different league of energy for no benefit.
* **`MP9486A`** (`C404013`, 4.5–100 V, 1 A) — a valid second source at $2.95,
  and worth remembering if the LM5164 goes short. The LM5164 won on price and
  on TI's documentation, which is what made §1 of `CALCULATIONS.md` possible.

## Consequences

* **`I-028` is no longer blocking.** Question (2) is not answered, but see the
  limit below.
* **The honest limit.** 100 V covers the *suppressed* load dump with 42 V of
  margin. A genuinely **unsuppressed** alternator reaches far higher and
  nothing near this price survives it. Internal suppression has been standard
  on alternators for decades and 58 V is what the vehicle-electronics industry
  designs to, so this is standard practice rather than a gamble — but it is
  stated here rather than hidden behind "100 V covers everything".
* **`F1` is now a safety item, not a convenience.** A 1206 PTC interrupts about
  40 A; a 24 V battery pushes thousands of amps into a short. A PTC is not an
  adequate sole protective device on a battery feed. An **external inline fuse
  with real breaking capacity belongs in the panel** — which is normal practice
  for battery-fed equipment. Tracked in `I-028`.
* **This buys an EMC problem.** A shielded module has become a 303 kHz
  switching regulator on a board that measures 41 µV per °C. Run the `emc`
  skill on the result and keep the switch node out of the sensor island. The
  board has not been generated yet, so the layout constraint can still be
  honoured for free.
* **`D2` clamps at 96.8 V against a 100 V absolute maximum — 3.2 V of margin.**
  That is thin, and the ISO 7637-2 fast transients, which exist on a battery
  and not on a panel supply, have not been worked through at all. Recorded in
  `CALCULATIONS.md` §3 as open.
* The netlist baseline changes: 13 new components and 5 new nets. A new
  `netlist-baseline-reva1.json` is the gate from here.
