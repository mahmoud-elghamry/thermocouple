# production/ - what is here and which folder to use

Everything here is generated and local (only this README is tracked). Product STATE files name the
current release; this page is the map.

| Folder | What it is |
|---|---|
| `24ch-reva4-*` | **24-ch REV A4 - the board being ordered.** Made in the 24-ch worktree (`.claude/worktrees/24ch-rev-a4`); fix I-133 before sending |
| `8ch-revb0-*` | new 8-ch REV B0, 4 layers - release candidate |
| `8ch-revb0-2l-*` | new 8-ch REV B0-2L, 2 layers, local fab - release candidate |
| `40ch-reva0-*` | 40-ch REV A0 - release candidate (owner: probably never built, `0043` 9) |
| `reference/` | the old 8-ch REV A2 (MAX31856) release and the board-size map - reference only |
| `reviews/` | review reports (Astra, Codex, Claude), one folder per review |
| `validation/` | validation runs (`hardware/8ch/validate.ps1`, firmware validation copies) |
| `bench/` | firmware bench reports (`firmware/family/read_report.ps1`), created when used |
| `_OLD_DO_NOT_ORDER/` | every superseded release (incl. 24-ch REV A3 `4b1601` and its NORI zips) - **never order from it** |

Rules:

* One current release per board at the top level; the release tools (`hardware/family/tools/fab.py`,
  `hardware/24ch/gen/fab.py`) write there. When a new one is made, move the previous one to
  `_OLD_DO_NOT_ORDER/` and update the product's STATE.md.
* Inside a release: `MANIFEST.txt` hashes every file; `WHICH-FILE-WHERE.txt` says what goes to whom;
  `ORDER-NOTES.txt` is the text for the supplier; `CPL-JLC.csv` is for JLC only (check every listed part in
  JLC's placement preview), `CPL.csv` for other assemblers.
* When a revision is actually ordered, copy its upload zip into the repo as `.gitignore` explains.
