# Current state - index

**Read second, after AGENTS.md; then the product's own STATE.md; then all of ISSUES.md (P0 first).
Hard limit: 60 lines, and so is every product STATE.md.**
**Last updated:** 2026-10-14 (two lines of work, `0037` D5).

## The products (`0037`: one board family on the 24-ch architecture, one firmware)

| Product | Folder | State file | Headline |
|---|---|---|---|
| 24-ch board REV A3 | `hardware/24ch/` | `hardware/24ch/STATE.md` | cost-down variant `0036`; RS-485 fitted again (owner 2026-10-14), release `4b1601`; NORI quote pending |
| Firmware | `firmware/` | `firmware/STATE.md` | 8-ch REV A2 firmware passes; **24-ch firmware not written (I-100)** |
| 8-ch board | `hardware/8ch/` (REV A2), `hardware/8ch-new/` (REV B0), `hardware/8ch-2l/` (REV B0-2L) | `hardware/8ch-new/STATE.md`, `hardware/8ch-2l/STATE.md` | REV A2 (MAX31856) is reference; REV B0 (4 layers, 130 x 137) DRC 0/0/0, release candidate in `production/` (`0039`); REV B0-2L (2 layers, local fab, 150 x 154) DRC 0/0/0, release candidate in `production/` (`0040`) |
| 40-ch board | `hardware/40ch/` | `hardware/40ch/STATE.md` | 40 TC + 3 PT100 (`0039`); schematic ERC 0/0, layout v2 250 x 145 placed, DRC 0/0/0 with parity, release candidate in `production/` (2026-10-17) |
| Simulation | `simulation/` | `firmware/STATE.md` | done in branch `firmware`: a Proteus demo needs the firmware first |
| Report for management | - (no branch) | - | last, after NORI quote + simulation: report with board callouts, features, quotes; slides |

## Repository and branches (`0037` D3)

* `main` is the official line; `cheaper-parts` merged by the owner 2026-10-14 (1904891). The 24-ch
  board with the original parts is tag `24ch-premium`.
* **Two lines of work (`0037` D5):** hardware (24-ch order, then 8-ch, then 40-ch, in that order) on
  `main`, one chat in `D:\tasks\thermo`; firmware + simulation in branch `firmware`, one chat in
  `D:\tasks\thermo-branches\firmware`, merged by the owner per tested stage. Report last, no branch.
  A new branch only when a second chat must change the same area at once. Agents never merge.
* A chat writes its product's STATE.md; it edits this index only when a headline above changes.

## Cross-product

* ISSUES rows: new rows start with the product in brackets ([24ch], [8ch], [40ch], [fw], [all]);
  untagged rows are 24-ch (`0037` D4).
* Gates: `python docs/check_docs.py` (all STATE files, size and references); per product as in
  `docs/TOOLS.md`. Never claim a gate without its report.
* Never edit `hardware/single-channel/` or anything in `_old/`.
