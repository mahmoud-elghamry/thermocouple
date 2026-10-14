# Current state - index

**Read second, after AGENTS.md; then the product's own STATE.md; then all of ISSUES.md (P0 first).
Hard limit: 60 lines, and so is every product STATE.md.**
**Last updated:** 2026-10-14 (two lines of work, `0037` D5).

## The products (`0037`: one board family on the 24-ch architecture, one firmware)

| Product | Folder | State file | Headline |
|---|---|---|---|
| 24-ch board REV A3 | `hardware/24ch/` | `hardware/24ch/STATE.md` | cost-down variant `0036`; RS-485 fitted again (owner 2026-10-14), release `4b1601`; NORI quote pending |
| Firmware | `firmware/` | `firmware/STATE.md` | 8-ch REV A2 firmware passes; **24-ch firmware not written (I-100)** |
| 8-ch board | `hardware/8ch/` | `hardware/8ch/STATE.md` | REV A2 (MAX31856) is reference; new 8-ch from the 24-ch design not started |
| 36-ch board | `hardware/36ch/` (not created) | - | owner request 2026-10-14; 5 banks, needs its own review first (`0037` D1) |
| Simulation | `simulation/` | `firmware/STATE.md` | done in branch `firmware`: a Proteus demo needs the firmware first |
| Report for management | - (no branch) | - | last, after NORI quote + simulation: report with board callouts, features, quotes; slides |

## Repository and branches (`0037` D3)

* `main` is the official line; `cheaper-parts` merged by the owner 2026-10-14 (1904891). The 24-ch
  board with the original parts is tag `24ch-premium`.
* **Two lines of work (`0037` D5):** hardware (24-ch order, then 8-ch, then 36-ch, in that order) on
  `main`, one chat in `D:\tasks\thermo`; firmware + simulation in branch `firmware`, one chat in
  `D:\tasks\thermo-branches\firmware`, merged by the owner per tested stage. Report last, no branch.
  A new branch only when a second chat must change the same area at once. Agents never merge.
* A chat writes its product's STATE.md; it edits this index only when a headline above changes.

## Cross-product

* ISSUES rows: new rows start with the product in brackets ([24ch], [8ch], [36ch], [fw], [all]);
  untagged rows are 24-ch (`0037` D4).
* Gates: `python docs/check_docs.py` (all STATE files, size and references); per product as in
  `docs/TOOLS.md`. Never claim a gate without its report.
* Never edit `hardware/single-channel/` or anything in `_old/`.
