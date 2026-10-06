# Reference

Background documents. **These are not sources of truth any more.**

The live documents are `AGENTS.md` at the repository root and the five files in
`docs/`. If something here disagrees with `docs/STATE.md`, `docs/ISSUES.md` or
`docs/decisions/`, those win.

| File | What it is | Still useful for |
|---|---|---|
| `INDUSTRIAL_8CH_PLAN_AR.md` | the original requirements and architecture study | the reasoning behind the isolation architecture, the No-Go conditions, the standards list. **Its §22 prototype geometry (250 x 140, 30 mm channel pitch) was never justified - see `0028`, I-090** |
| `SOFTWARE_ARCHITECTURE_AR.md` | the MCAL/HAL/APP layering | firmware work |
| `CONNECTIONS.md` | pin map used by the Proteus simulation | the simulation only — not the 8-channel board |

`analysis/` holds a kicad-happy run against the single-channel board from
2026-09-01. It is kept on disk but not tracked: it is machine output, and the
findings it supported are now issues in `docs/ISSUES.md`.

Moved to `_old/docs-reference/` on 2026-10-06: `DESIGN_REVIEW_AR.md` (single-channel
review, findings already in ISSUES), `LESSONS_LEARNED_AR.md`, `PROJECT_GUIDE_AR.md`.
