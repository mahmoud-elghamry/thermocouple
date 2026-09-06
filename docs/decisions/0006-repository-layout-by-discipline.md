---
status: accepted
date: 2026-09-07
deciders: Zain, Claude
---

# Lay the repository out by discipline, and separate sources from output

## Context

The root had grown into a mix of live work, dead work and scratch files:
`pcb/` held both the superseded single-channel board and the active
`pcb/8ch/`; `BOM.csv` at the root was the single-channel BOM and duplicated the
8-channel one; `project_code_bundle.txt` was a code dump for pasting into a
chat; `tmp/` held a stray netlist; `semulation/` was a spelling mistake; and
`pcb/.history/` contained a nested `.git` from an editor extension — flagged as
`P-07` in the design review months earlier and never removed.

There was also no defined home for fabrication output, so Gerbers landed
wherever a script put them.

## Decision

Lay the top level out by **discipline and lifecycle**, which is the convention
for hardware/firmware monorepos:

```
hardware/8ch/             active board
hardware/single-channel/  superseded board, kept for reference
firmware/                 AVR C plus host tests
simulation/               Proteus project
production/               fabrication output, generated, gitignored
docs/                     goal, state, issues, decisions, tools, reference
```

Sources are tracked; anything a script regenerates is not.

## Why not organise by feature, or by Diátaxis

**Feature-based versus layer-based** is a web-application argument — whether to
group code by feature (`users/`, `orders/`) or by layer (`controllers/`,
`models/`). It has no meaning in a repository whose contents are a PCB, some
firmware and a simulation. The axis that matters here is discipline.

**Diátaxis** is the right framework for product documentation, and its central
rule was adopted: every document serves exactly one need, and a document that
serves two gets split. Its four-folder structure (tutorials / how-to /
reference / explanation) was not, because six documents in four folders is
filing, not organisation.

## Consequences

- The dead board is now named as dead. `hardware/single-channel/` cannot be
  mistaken for the active work the way `pcb/` could.
- `production/` is gitignored, so fabrication output can never be confused with
  a source file again.
- The scripts needed no changes: they resolve paths from `__file__`. Only prose
  references had to be updated.
- `semulation/` could not be renamed on the day — Proteus held the folder open.
  Left as `I-010`.
