# Thermo — 8-channel thermocouple protection unit

Read this file first. It is the entry point for every agent and every new
session. Follow the AGENTS.md open standard, so Codex, Cursor, Copilot and
others read it directly; `CLAUDE.md` imports it for Claude Code.

**Keep this file under 150 lines.** If it grows past that, something belongs in
`docs/` instead.

---

## What this project is

A protection unit that reads eight K-type thermocouples and opens a dry contact
when any of them exceeds a setpoint. **It is being built to go on a real
machine.** Treat every decision as safety-relevant.

The output is energised-to-run: loss of power, reset, or a fault means the
contact opens and the machine cannot start.

## Where to look

| File | What it holds | Who owns it |
|---|---|---|
| `docs/GOAL.md` | the goal and the requirements | the user |
| `docs/STATE.md` | what is done, what is next — **read this second** | whoever worked last |
| `docs/ISSUES.md` | open problems, numbered `I-001` | anyone |
| `docs/decisions/` | one file per decision, MADR format | whoever decided |
| `docs/TOOLS.md` | the commands that actually work here | anyone |
| `docs/reference/` | long background documents | reference only |

Do not add a new file to `docs/` for your own notes. Findings go into
`docs/ISSUES.md`, decisions into `docs/decisions/`, progress into
`docs/STATE.md`. A review that lives in its own file gets read once and then
rots — that has already happened here once.

## Repository layout

```
hardware/8ch/             the 8-channel board - the active hardware work
hardware/single-channel/  superseded board, kept for reference - DO NOT MODIFY
firmware/                 AVR C for the ATmega32A, with host unit tests
simulation/               Proteus simulation project
production/               fabrication output - generated, never committed
docs/                     see the table above
```

Sources are tracked; anything a script regenerates is not. Gerbers, drill and
placement files, renders and netlists belong in `production/` or are ignored.

## Rules

1. **Never claim something is ready without the report to back it.** "DRC is
   clean" means a `drc-report.rpt` with zero manufacturing errors, quoted with
   its numbers. The same for ERC, builds and tests.
2. **Do not touch `hardware/single-channel/`.** It is the superseded board, kept
   only for reference.
3. **Do not commit or push** unless the user asks. Leave work in the tree for
   review.
4. **Firmware is in scope.** Several open issues are firmware faults with
   safety consequences; a PCB-only reading of a task is too narrow.
5. **Update `docs/STATE.md` before you finish.** The next session starts there.
6. **Record decisions.** If you chose between real alternatives — a part, an
   architecture, a tolerance — add a file to `docs/decisions/`. Include what you
   rejected and why.
7. **No pointless complexity.** If a part or a feature can be removed and the
   unit still meets its goal, propose removing it.
8. **One session on the hardware at a time.** `generate_board.py` rewrites the
   whole board and `thermocouple_8ch.kicad_pcb` is a single file, so a second
   agent - or an open KiCad window - silently overwrites the first. On
   2026-09-07 the board was rewritten at 01:23 while a KiCad window held
   unsaved edits from 00:59. Close KiCad before running anything that writes
   the board. Working in `firmware/` or `docs/` at the same time is fine;
   `hardware/` is not.
9. **Nothing routed by hand survives.** `generate_board.py` clears every track,
   via, zone and drawing. A fix drawn in KiCad is gone on the next run, so
   fixes belong in `hardware/8ch/board/` or `route.py`.
10. **Keep source files small enough to edit safely.** A thousand-line generator
   edited by pattern-matching is how a fix landed in the wrong function twice on
   2026-09-06 and cost two full rebuild cycles.

## Build and check

Full details in `docs/TOOLS.md`. The short version:

```powershell
pwsh -File hardware\8ch\run_all.ps1      # schematic -> ERC -> rules -> board -> route -> DRC
```

```powershell
pwsh -File firmware\build.ps1       # firmware build + host tests
```

Both must be run before claiming anything about the current state.

## Hard constraints — do not design around these

- **MAX31856 is not a galvanic isolator.** It is a good thermocouple front end,
  but T+/T- are not separated from AGND/DGND.
- **The sensor island isolates the group, not the channels.** All eight
  thermocouples share one isolated ground. This is accepted (see
  `docs/decisions/`), not solved.
- **Cables may run 50 m near a motor/VFD.** Layout symmetry and plane pairs
  improve the odds; only measurement settles it.
- **The isolation rules in `.kicad_dru` are functional, not certified.** No
  creepage/clearance analysis against IEC 61010 has been done.
- **The dry contact is marked LOW-VOLTAGE LOAD ONLY** and the clearances match
  that, not a mains rating.
