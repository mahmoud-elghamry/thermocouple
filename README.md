# Thermo — 24-channel thermocouple protection board

> Working on this repository with an AI agent? Start at **`AGENTS.md`**,
> then `docs/STATE.md`.

One board that reads **24 K-type thermocouples** on one engine (grounded,
insulated or mixed probes, roughly 50 m cables, no VFD) and opens a common
run-permit contact when any channel passes its own setpoint, the sensor fails
or the unit itself fails. It is being built to go on real equipment.

The output is **energised to run**: loss of power, a reset or a fault opens
the contact, so the engine cannot start.

## Where things are

| | |
|---|---|
| **The active board** | `hardware/24ch/` (REV A3, 3x AD7124-8) — see its README; repairs before ordering in `docs/ISSUES.md` P0 |
| **Earlier 8-channel board** | `hardware/8ch/` (REV A2) — reference only, never ordered |
| **Firmware** | `firmware/` — today only the 8-channel images; the 24-channel firmware is not written yet (I-100, I-104, I-118, I-119) |
| **What is done and what is next** | `docs/STATE.md` |
| **Open problems** | `docs/ISSUES.md` |
| **Why things are the way they are** | `docs/decisions/` (start with `0031`) |
| **Commands that actually work here** | `docs/TOOLS.md` |

`hardware/single-channel/` and `_old/` are **superseded** and kept only as a
record. Do not work from them and do not modify them.

## Build and check

```powershell
pwsh -File firmware\build.ps1                 # firmware images + host tests
cd hardware\24ch\gen; python build.py          # 24-ch schematic, ERC, netlist check
python docs\check_docs.py                     # entry documents agree with each other
```

> **The firmware images are not interchangeable.** The eight-channel image
> drives the run output HIGH only while it is *safe to run*; the legacy
> single-channel images drive the same pin HIGH on *over-temperature*.
> Flashing the wrong one inverts the safety function. `program.ps1` warns you.

## State

An **engineering prototype**: nothing has been built or electrically tested.
The isolation rules in `.kicad_dru` are functional, not qualified against any
standard; the contacts are rated for low-voltage signal loads only (30 VDC /
1 A). `docs/ISSUES.md` is the full list; nothing is claimed as done without a
report to back it.
