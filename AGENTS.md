# Thermo — thermocouple protection boards: one family of 8, 24 and 40 channels

Read this file first. It is the entry point for every agent and every new
session. Follow the AGENTS.md open standard, so Codex, Cursor, Copilot and
others read it directly; `CLAUDE.md` imports it for Claude Code.

**Keep this file under 150 lines.** If it grows past that, something belongs in
`docs/` instead.

---

## What this project is

A protection system for **K- and J-type thermocouples** (per channel, `0038`) on engines. **`0037` (2026-10-14): one board
family on the 24-ch architecture** - banks of one AD7124-8 each: 8 ch = 1 bank, 24 ch = 3, 40 ch = 5 + a PT100 bank (`0039`) -
and **one firmware** for all of them. **`hardware/24ch/` (REV A4 `0041` on the cost-down `0036`) is the
board being ordered**; `0031` holds its architecture (grounded, insulated or mixed probes).
`hardware/8ch/` (REV A2, MAX31856) is reference; the new 8-ch (`hardware/8ch-new/`) and 40-ch (`hardware/40ch/`) derive from it via `hardware/family/` (`0039`).
Any channel trips the common run-permit contact.
Earlier eight-channel basis: cylinder-body probes, roughly 50 m cables, no VFD.
Per-channel setpoints and manual ACK (`0029`): family firmware, 24-ch only so far (`0043`). Supply: engine battery, nominal 24 V (`0016`). HMI selection/mounting is delegated to the design team (`0029`).
**It is being built to go on a real machine.** Treat decisions as safety-relevant.

The output is energised-to-run: loss of power, reset, or a fault means the
contact opens and the machine cannot start.

## Where to look

| File | What it holds | Who owns it |
|---|---|---|
| `docs/GOAL.md` | the goal and the requirements | the user |
| `docs/STATE.md` | index of the products — **read this second**, then the product's own `STATE.md` (`hardware/<board>/`, `firmware/`) | whoever worked last |
| `docs/ISSUES.md` | open problems by priority P0-P3, short rows (`0025`) — **read all of it third** | anyone |
| `docs/ISSUES-closed.md` | archive of closed issues | anyone |
| `docs/decisions/` | one file per decision, MADR format | whoever decided |
| `docs/TOOLS.md` | the commands that actually work here | anyone |
| `docs/reference/CALCULATIONS.md` | every computed value: inputs, formula, verdict | anyone - **add to it, never re-derive silently** |
| `docs/reference/` | long background documents | reference only |

Do not add a new file to `docs/` for your own notes. Findings go into
`docs/ISSUES.md` (new rows tagged [24ch]/[8ch]/[40ch]/[fw]/[all]), decisions into `docs/decisions/`,
progress into the product's `STATE.md`. A review that lives in its own file gets read once and then
rots — that has already happened here once.

## Repository layout

```
hardware/24ch/            the 24-channel board REV A4 - being ordered (README, STATE.md there)
hardware/8ch/             the 8-channel board REV A2 - reference; the new 8-ch derives from 24ch
hardware/8ch-new/, 40ch/  new 8-ch REV B0 (8ch-2l: 2 layers, 0040) and 40-ch (40 TC + 3 PT100); family/ = shared lib (0039)
hardware/single-channel/  superseded board, kept for reference - DO NOT MODIFY
firmware/                 family/ = the one firmware (24-ch first), spec/ = its spec, 8ch-legacy/ = old 8-ch REV A2
simulation/               Proteus simulation project
production/               fabrication output - generated, never committed
_old/                     superseded files, reference only - never build or order from it
docs/                     see the table above
```

Products are folders, not branches (`0037` D3, D5): hardware work is on `main` (one chat); firmware and
simulation in a branch (`firmware`; the family firmware was written in `24ch-rev-a4`), brought to `main` per rule 3; a new branch only for parallel work. Sources are tracked; anything a script regenerates is not. Gerbers, drill and
placement files, renders and netlists belong in `production/` or are ignored.

## Rules

1. **Never claim something is ready without the report to back it.** "DRC is
   clean" means a `drc-report.rpt` with zero manufacturing errors, quoted with
   its numbers. The same for ERC, builds and tests.
2. **Do not touch `hardware/single-channel/`.** It is the superseded board, kept
   only for reference.
3. **Do not commit or push** unless the user asks. Leave work in the tree for
   review. **No `git merge` without the owner's word.** With that word a branch may be copied into `main`
   instead (`git merge-tree` result, conflicts by hand, ordinary commit; owner 2026-10-24).
4. **Firmware is in scope.** Several open issues are firmware faults with
   safety consequences; a PCB-only reading of a task is too narrow.
5. **Update your product's `STATE.md` before you finish** (and the index `docs/STATE.md` only when a
   headline changes), and run `python docs/check_docs.py` (exit 0).
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
   change reverted), update the product's `STATE.md`, and stop. Never stop halfway
   through a write to the board or schematic.

## Build and check

Full details in `docs/TOOLS.md`. **24-ch board: read its "24-channel board" section before
touching placement or routing** - generative until placement is frozen, incremental after;
check `padcheck.py` before any long router run. The short version:

```powershell
pwsh -File hardware\8ch\run_all.ps1      # validate a snapshot; source hardware stays unchanged
pwsh -File firmware\family\build.ps1   # 24-ch family firmware: build, host tests, AVR profiler; then
pwsh -File firmware\family\test\build_core.ps1; pwsh -File firmware\family\test\build_acceptance.ps1
```

Both must be run before claiming anything about the current state. In a cloud
(Linux) session use `make -C firmware/8ch-legacy all test` (legacy 8-ch only) and
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
