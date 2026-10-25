# Current state - index

**Read second, after AGENTS.md; then the product's own STATE.md; then all of ISSUES.md (P0 first).
Hard limit: 60 lines, and so is every product STATE.md.**
**Last updated:** 2026-10-24 (branch `24ch-rev-a4` merged into main `7a31f0c`; coordination sweep; all family boards re-released).

## The products (`0037`: one board family on the 24-ch architecture, one firmware)

| Product | Folder | State file | Headline |
|---|---|---|---|
| 24-ch board REV A4 | `hardware/24ch/` | `hardware/24ch/STATE.md` | gated TMP126 SIO driver (`0041`), door LCD/buttons (`0042`); release `production/24ch-reva4-20261025-040133-02daef`; install guide `hardware/24ch/install-guide/` |
| 8-ch board | `hardware/8ch/` (REV A2), `hardware/8ch-new/` (REV B0), `hardware/8ch-2l/` (REV B0-2L) | `hardware/8ch-new/STATE.md`, `hardware/8ch-2l/STATE.md` | REV A2 (MAX31856) is reference; REV B0 (4 layers, 130 x 137) DRC 0/0/0, release candidate in `production/` (`0039`); REV B0-2L (2 layers, local fab, 150 x 154) DRC 0/0/0, release candidate in `production/` (`0040`) |
| 40-ch board | `hardware/40ch/` | `hardware/40ch/STATE.md` | 40 TC + 3 PT100 (`0039`); DRC 0/0/0 with parity, Astra: send for quotation; release candidate `production/40ch-reva0-20261024-141240-35825e` |
| Firmware | `firmware/` | `firmware/STATE.md` | family firmware `firmware/family/` F0-F8, **24-ch only** (`0043` 9); host + AVR-simulator tests pass, bench pending; 8-ch REV A2 in `firmware/8ch-legacy/` |
| Simulation | `simulation/` | `firmware/STATE.md` | legacy 8-ch MAX6675 demo only (I-136); an A4 demo needs the family firmware on Proteus |
| Report for management | - (no branch) | - | last, after NORI quote + simulation: report with board callouts, features, quotes; slides |

## Repository and branches (`0037` D3)

* `main` is the official line and the source of authority; the 24-ch board with the original parts is tag
  `24ch-premium`. Old branches and worktrees (family-lib, family-tools, firmware, cheaper-parts) removed 2026-10-24.
* **Two lines of work (owner 2026-10-24):** the 24-ch board and its firmware in branch `24ch-rev-a4`
  (worktree `.claude/worktrees/24ch-rev-a4`, one chat) until the first boards are built and work; everything else
  (8ch-new, 8ch-2l, 40ch, family, docs) on `main` (`D:\tasks\thermo`, one chat). The branch is merged into
  `main` on the owner's word (rule 3; last merge 2026-10-24 `7a31f0c`). Report last, no branch.
  A new branch only when a second chat must change the same area at once. No `git merge` without the owner's word (rule 3).
* A chat writes its product's STATE.md; it edits this index only when a headline above changes.

## Cross-product

* ISSUES rows: new rows start with the product in brackets ([24ch], [8ch], [40ch], [fw], [all]);
  untagged rows are 24-ch (`0037` D4).
* Gates: `python docs/check_docs.py` (all STATE files, size and references); per product as in
  `docs/TOOLS.md`. Never claim a gate without its report.
* Never edit `hardware/single-channel/` or anything in `_old/`.
