# Reference

Background documents. **These are not sources of truth any more.**

The live documents are `AGENTS.md` at the repository root and the five files in
`docs/`. If something here disagrees with `docs/STATE.md`, `docs/ISSUES.md` or
`docs/decisions/`, those win.

| File | What it is | Still useful for |
|---|---|---|
| `INDUSTRIAL_8CH_PLAN_AR.md` | the original requirements and architecture study | the reasoning behind the isolation architecture, the No-Go conditions, the standards list |
| `DESIGN_REVIEW_AR.md` | an independent review of the single-channel board at commit `c8ae6f5` | its findings are now tracked in `docs/ISSUES.md`; do not work from this file directly |
| `SOFTWARE_ARCHITECTURE_AR.md` | the MCAL/HAL/APP layering | firmware work |
| `CONNECTIONS.md` | pin map used by the Proteus simulation | the simulation only — not the 8-channel board |
| `LESSONS_LEARNED_AR.md` | notes from earlier iterations | context |
| `PROJECT_GUIDE_AR.md` | early project guide | context |

`analysis/` holds a kicad-happy run against the single-channel board from
2026-09-01. It is kept on disk but not tracked: it is machine output, and the
findings it supported are now issues in `docs/ISSUES.md`.
