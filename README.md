# Thermo — 8-channel thermocouple protection unit

> Working on this repository with an AI agent? Start at **`AGENTS.md`**,
> then `docs/STATE.md`.

A protection unit that reads eight K-type thermocouples — one per cylinder of an
engine — and opens a dry contact when any of them exceeds an operator-set
temperature. It is being built to go on real equipment.

The output is **energised to run**: loss of power, a reset, a sensor fault or a
missing setpoint all open the contact, so the engine cannot start.

## Where things are

| | |
|---|---|
| **The active board** | `hardware/8ch/` — 4-layer, placed, routed, DRC-clean, Gerbers in `production/8ch/` |
| **The firmware for it** | `firmware/`, target `thermo_8ch_max31856` |
| **Programming a unit** | `firmware/fuses.md`, then `firmware/program.ps1` |
| **What is done and what is next** | `docs/STATE.md` |
| **Open problems** | `docs/ISSUES.md` |
| **Why things are the way they are** | `docs/decisions/` |
| **Commands that actually work here** | `docs/TOOLS.md` |

`hardware/single-channel/` is a **superseded** board kept only as the record of
what was fabricated earlier. Do not work from it and do not modify it.

## Build

```powershell
pwsh -File firmware\build.ps1
```

Builds four images with warnings as errors and runs the host tests:

| Image | For |
|---|---|
| `thermo_8ch_max31856` | **the real board** |
| `thermo_8ch_max6675_sim` | Proteus simulation — Proteus has no MAX31856 model |
| `legacy_1ch_max31856` | the superseded single-channel board |
| `legacy_1ch_max6675` | the same, Proteus |

```powershell
pwsh -File hardware\8ch\run_all.ps1
```

Regenerates and re-checks the board end to end. **Read `docs/STATE.md` first** —
the board is frozen at REV A0 and this rewrites it.

> **The images are not interchangeable.** The eight-channel image drives PB3
> HIGH only while it is *safe to run*. The legacy single-channel images drive
> the same pin HIGH on *over-temperature*. Flashing the wrong one inverts the
> safety function with no visible symptom. `program.ps1` warns you.

## State

This is an **engineering prototype**, not a finished product. It has never been
built or electrically tested. Specifically:

- The isolation barrier has never been measured (`I-004`), and the rules in
  `.kicad_dru` are functional, not qualified against any standard.
- The trip time is calculated at 623 ms against a 1 s requirement, but has not
  been measured on hardware (`I-013`).
- The schematic produces a correct netlist and passes ERC, but it is not a
  drawing anyone can review or sign (`I-002`).
- Modbus RTU is deferred: there is no crystal, and the internal RC oscillator
  is not accurate enough for a reliable UART (`docs/decisions/0010`).
- The relay contact is marked **low-voltage loads only** and the clearances
  match that, not a mains rating.

`docs/ISSUES.md` is the full list. Nothing here is claimed as done without a
report to back it.
