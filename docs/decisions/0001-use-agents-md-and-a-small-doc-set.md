---
status: accepted
date: 2026-09-07
deciders: Zain, Claude
---

# Use AGENTS.md and a small, size-limited document set

## Context

Every agent that worked on this repository created its own file under `docs/`.
`INDUSTRIAL_8CH_PLAN_AR.md` grew to roughly 850 lines and started to contradict
itself. `DESIGN_REVIEW_AR.md` was written once and never updated, so its
findings were re-discovered by hand later. Nothing recorded the goal, the
decisions taken, the tools, or the current state in a form a new session could
pick up, so each new conversation started from zero.

`docs/` is not read automatically by any tool. `CLAUDE.md` is read by Claude
Code; `AGENTS.md` is read by Codex, Cursor, Copilot, Windsurf, Zed, Aider and
others. The project is worked on by more than one agent.

## Decision

`AGENTS.md` at the repository root is the single entry point. `CLAUDE.md`
contains only `@AGENTS.md` so Claude Code reads the same content.

Underneath it, five small files with stated line limits:

- `docs/GOAL.md` — the goal and requirements, owned by the user
- `docs/STATE.md` — current state and next action, ≤ 60 lines, rewritten each session
- `docs/ISSUES.md` — numbered open problems, `I-001` onward, never renumbered
- `docs/decisions/` — one MADR file per decision
- `docs/TOOLS.md` — the commands that actually work here

Long background documents move to `docs/reference/` and stop being sources of
truth. A review no longer gets its own file: its findings become issues.

## Why this shape

`AGENTS.md` is an open standard donated to the Linux Foundation's Agentic AI
Foundation in December 2025 and used by more than 60,000 repositories, so
choosing it costs nothing and buys cross-tool compatibility. MADR has been the
convention for decision records since 2017.

The line limits are the important part. Anthropic's own guidance on long-horizon
agent work treats context as working material that expires rather than a pile
that only grows — which is exactly how the plan document failed here.

## Alternatives rejected

- **`CLAUDE.md` as the source of truth.** Codex would not read it, and Codex
  works on this repository.
- **Keep one large plan document.** Already tried. It grew past the point where
  anyone could keep it true.
- **A `docs/` file per agent or per review.** This is the current failure mode.
