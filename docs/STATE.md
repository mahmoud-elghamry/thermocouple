# Current state - index

**Read second, after AGENTS.md; then the product's own STATE.md; then all of ISSUES.md (P0 first).
Hard limit: 60 lines, and so is every product STATE.md.**
**Last updated:** 2026-10-14 (board family and per-product state, `0037`).

## The products (`0037`: one board family on the 24-ch architecture, one firmware)

| Product | Folder | State file | Headline |
|---|---|---|---|
| 24-ch board REV A3 | `hardware/24ch/` | `hardware/24ch/STATE.md` | cost-down variant `0036`; RS-485 fitted again (owner 2026-10-14) - new release in branch `24ch-order`; NORI quote pending |
| Firmware | `firmware/` | `firmware/STATE.md` | 8-ch REV A2 firmware passes; **24-ch firmware not written (I-100)** |
| 8-ch board | `hardware/8ch/` | `hardware/8ch/STATE.md` | REV A2 (MAX31856) is reference; new 8-ch from the 24-ch design not started |
| 36-ch board | `hardware/36ch/` (not created) | - | owner request 2026-10-14; 5 banks, needs its own review first (`0037` D1) |
| Simulation | `simulation/` | `firmware/STATE.md` | done in branch `firmware`: a Proteus demo needs the firmware first |
| Report for management | - (no branch) | - | not started: board drawing with callouts, features, quotes |

## Repository and branches (`0037` D3)

* `main` is the official line; `cheaper-parts` merged by the owner 2026-10-14 (1904891). The 24-ch
  board with the original parts is tag `24ch-premium`.
* Branches from `main`: `24ch-order`, `firmware` (+ simulation), `8ch`, `36ch`; the report needs none.
  Each chat works in its own branch/worktree; the owner merges. Agents never merge.
* A chat writes its product's STATE.md; it edits this index only when a headline above changes.

## Cross-product

* ISSUES rows: new rows start with the product in brackets ([24ch], [8ch], [36ch], [fw], [all]);
  untagged rows are 24-ch (`0037` D4).
* Gates: `python docs/check_docs.py` (all STATE files, size and references); per product as in
  `docs/TOOLS.md`. Never claim a gate without its report.
* Never edit `hardware/single-channel/` or anything in `_old/`.
