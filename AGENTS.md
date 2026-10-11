# Thermo — 24-channel protection system; current board has 8 channels

Read this file first. It is the entry point for every agent and every new
session. Follow the AGENTS.md open standard, so Codex, Cursor, Copilot and
others read it directly; `CLAUDE.md` imports it for Claude Code.

**Keep this file under 150 lines.** If it grows past that, something belongs in
`docs/` instead.

---

## What this project is

A protection system for **24 K-type thermocouples** (owner clarified 2026-09-29).
**`hardware/24ch/` (REV A3) is the active board** (routed, fab set 2026-10-09, repairs open: I-111..I-116);
`hardware/8ch/` (REV A2) is the earlier eight-channel board, kept as reference.
**`0031` (2026-10-08): ONE 24-channel board, 3x AD7124-8 front end (grounded,
insulated or mixed probes), all parts from one source. Read `0031` first: it
holds the agents' work split and supersedes most of `0030` and `0024`.**
Any of the 24 channels trips the common run-permit contact.
Earlier eight-channel basis: cylinder-body probes, roughly 50 m cables, no VFD.
Per-channel persistent setpoints and manual ACK are required (`0029`); the 24-ch firmware is not written yet (I-100).
Supply: engine battery, nominal 24 V (`0016`). HMI selection/mounting is delegated to the design team (`0029`).
**It is being built to go on a real machine.** Treat decisions as safety-relevant.

The output is energised-to-run: loss of power, reset, or a fault means the
contact opens and the machine cannot start.

## Where to look

| File | What it holds | Who owns it |
|---|---|---|
| `docs/GOAL.md` | the goal and the requirements | the user |
| `docs/STATE.md` | what is done, what is next — **read this second** | whoever worked last |
| `docs/ISSUES.md` | open problems by priority P0-P3, short rows (`0025`) — **read all of it third** | anyone |
| `docs/ISSUES-closed.md` | archive of closed issues | anyone |
| `docs/decisions/` | one file per decision, MADR format | whoever decided |
| `docs/TOOLS.md` | the commands that actually work here | anyone |
| `docs/reference/CALCULATIONS.md` | every computed value: inputs, formula, verdict | anyone - **add to it, never re-derive silently** |
| `docs/reference/` | long background documents | reference only |

Do not add a new file to `docs/` for your own notes. Findings go into
`docs/ISSUES.md`, decisions into `docs/decisions/`, progress into
`docs/STATE.md`. A review that lives in its own file gets read once and then
rots — that has already happened here once.

## Repository layout

```
hardware/24ch/            the 24-channel board - THE ACTIVE HARDWARE WORK (README there)
hardware/8ch/             the 8-channel board REV A2 - reference
hardware/single-channel/  superseded board, kept for reference - DO NOT MODIFY
firmware/                 AVR C, host unit tests; 8-ch images only so far (24-ch board: ATmega1284P)
simulation/               Proteus simulation project
production/               fabrication output - generated, never committed
_old/                     superseded files, reference only - never build or order from it
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
   review. **Never merge, even if subsequently requested** (owner, cloud session).
4. **Firmware is in scope.** Several open issues are firmware faults with
   safety consequences; a PCB-only reading of a task is too narrow.
5. **Update `docs/STATE.md` before you finish**, and run `python docs/check_docs.py` (exit 0).
6. **Record decisions.** If you chose between real alternatives — a part, an
   architecture, a tolerance — add a file to `docs/decisions/`. Include what you
   rejected and why. **A decision that replaces an earlier one sweeps GOAL, README,
   ISSUES rows and STATE in the same change** and adds the old wording to
   `docs/superseded.txt` (I-117: skipped sweeps left GOAL describing three modules).
7. **No pointless complexity.** If a part or a feature can be removed and the
   unit still meets its goal, propose removing it.
8. **One writer on the hardware at a time.** `thermocouple_8ch.kicad_pcb` is a
   single file, so a second agent - or an open KiCad window - silently
   overwrites the first. On 2026-09-07 the board was rewritten at 01:23 while a
   KiCad window held unsaved edits from 00:59. Run
   `python hardware/8ch/board_provenance.py --check` before writing the board;
   it refuses while KiCad holds a `~*.lck`. **Do not close KiCad to get past
   it** - it may be holding unsaved work. Every 24-ch tool that saves the board goes
   through `gen/guard.py`: it refuses while KiCad holds a `~*.lck` or another tool holds `output/.writer.json`. Working in `firmware/`
   or `docs/` at the same time is fine.
9. **Two ways to change the hardware. Know which one you are in.**
   *Generative* - run the pipeline; it rebuilds everything from `board/` and the
   part tables, and destroys whatever hand edits exist at that moment.
   *Incremental* - edit the board or schematic directly, in KiCad or with our
   scripts; this is the right mode for a surgical change on a frozen board,
   because regenerating re-routes the whole PCB and hands you a different board
   to re-verify. Neither is wrong. Running the generator **on top of** hand
   edits is, and it fails silently. `board_provenance.py --check` is what tells
   them apart - it exits non-zero when a generator run would lose work; after
   any generator run, `--record`. Which mode suits which job:
   `docs/decisions/0012`. The incremental tool is KiCad itself or **Konnect**
   (`0013`), the only KiCad MCP here: with KiCad open it edits *through* KiCad,
   so KiCad stays the only writer; with KiCad closed it reads and writes the
   files itself.
10. **Keep source files small enough to edit safely.** A thousand-line generator
   edited by pattern-matching is how a fix landed in the wrong function twice on
   2026-09-06 and cost two full rebuild cycles.
11. **Stop at a safe point when your usage runs low and the owner is away.**
   The usage limit is background, not the plan: work normally. If your tool
   warns that the session or weekly limit is close and nobody is answering,
   finish the step in hand, leave the tree consistent (gates re-run or the
   change reverted), update `docs/STATE.md`, and stop. Never stop halfway
   through a write to the board or schematic.

## Build and check

Full details in `docs/TOOLS.md`. **24-ch board: read its "24-channel board" section before
touching placement or routing** - generative until placement is frozen, incremental after;
check `padcheck.py` before any long router run. The short version:

```powershell
pwsh -File hardware\8ch\run_all.ps1      # validate a snapshot; source hardware stays unchanged
```

```powershell
pwsh -File firmware\build.ps1       # firmware build + host tests
```

Both must be run before claiming anything about the current state. In a cloud
(Linux) session use `make -C firmware all test` and
`pwsh -File hardware/8ch/validate.ps1`; see `docs/TOOLS.md`, "Cloud sessions".
`run_all.ps1 -Regenerate` rewrites and re-routes the whole board. The owner
lifted the REV A0 freeze on 2026-09-15 (`docs/decisions/0014`), so it is
authorized - run `board_provenance.py --check` first.

## Hard constraints — do not design around these

- **Neither MAX31856 nor AD7124-8 is a galvanic isolator.** T+/T- are not
  separated from the converter's ground.
- **The board isolates the group, not the channels.** All 24 thermocouples
  share one isolated island; accepted because all 24 are on one engine (owner,
  2026-10-08, `0031`). A probe on another machine needs a fresh review.
- **Cables run roughly 50 m from the engine to a separate panel; no VFD.**
  Layout symmetry and plane pairs help; only measurement settles performance.
- **The isolation rules in `.kicad_dru` are functional, not certified.** No
  creepage/clearance analysis against IEC 61010 has been done.
- **The dry contact is marked LOW-VOLTAGE LOAD ONLY** and the clearances match
  that, not a mains rating.
