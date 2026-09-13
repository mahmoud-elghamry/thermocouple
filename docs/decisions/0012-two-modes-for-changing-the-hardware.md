---
status: accepted
date: 2026-09-13
deciders: Zain
amends: 0010
---

# Two modes for changing the hardware, with a guard between them

## Context

Until now the hardware had exactly one way to change: run the pipeline.
`populate_schematic.py` rewrites the schematic, `generate_board.py` clears every
track, via, zone and drawing and re-places from `board/`, and `route.py` runs
Freerouting over the result. `AGENTS.md` rule 9 said, correctly, that nothing
drawn by hand survives.

That was the right architecture for getting from nothing to a placed, routed,
DRC-clean board. It is the wrong one now, and the reason is `docs/decisions/0010`:
REV A0 is frozen, and what the board needs from here are surgical changes -
nudge one silkscreen label, drop one dangling via, add two resistors for the
run-permit read-back.

Regenerating for a change that size is not conservative, it is reckless:

    move one silkscreen label
      -> generate_board.py clears the whole board
      -> Freerouting routes from scratch, differently every run
      -> a board nobody has verified, in place of one that passed
         0 DRC errors, 0 unconnected, 0 parity

Meanwhile a KiCad MCP is now installed (`.mcp.json`), which makes direct editing
practical for an agent rather than only for a human in the GUI.

## Decision

**Both modes are legitimate. Pick by the size of the change.**

| | Generative | Incremental |
|---|---|---|
| How | `populate_schematic.py`, `generate_board.py`, `route.py` | KiCad, or the KiCad MCP's seven write tools |
| Right for | new parts, a changed stack-up, re-placement, anything touching many nets | one label, one via, a value, a small local edit |
| Cost | full re-route, full re-verification, new Gerbers | none beyond the edit and its checks |
| Reproducible | yes - rerun and get the same board | no - the edit lives only in the file |

**What is forbidden is not either mode. It is running the generator on top of
hand edits without knowing they are there**, which destroys work silently and
which nothing in the project could previously detect: `netlist_fingerprint.py`
compares the *schematic's* connectivity and never looks at the PCB, and
`validate.ps1` hashes files only within a single run.

So a guard was added: `hardware/8ch/board_provenance.py`.

- `--record` stores the SHA-256 of `thermocouple_8ch.kicad_pcb` and
  `.kicad_sch` as the generator left them. Run it after every generator run.
- `--check` compares. It exits non-zero when the files have drifted, which
  means hand edits exist and a generator run would lose them. It also refuses
  while KiCad holds a `~*.lck`, because a second writer is exactly how the
  board was lost on 2026-09-07.
- `--status` reports without failing.

Tested on 2026-09-13: drift detected on a one-byte change, lock file detected,
and a clean tree reports `regenerating is safe`.

## The rule for crossing between modes

Going generative → incremental is free. Going the other way is not:

> Once the board has been hand-edited, the generator may not be run until the
> edit is either **folded back into `board/` and the part tables**, or
> **deliberately abandoned** - and `--record` re-run to say so in writing.

`--check` enforces the first half. The second half is a human decision and
should leave a line in `docs/STATE.md` saying what was given up.

## On closing KiCad

The guard **refuses** while KiCad has the project open. It does not close
KiCad, and no agent should: the window may hold unsaved work, which is the
2026-09-07 failure exactly. Opening KiCad is harmless; closing it is the user's
call.

## Consequences

**`board/`, `generate_board.py` and `route.py` stay.** They are not dead. They
are how the board is rebuilt when a change is big enough to deserve it, and
they remain the record of how REV A0 came to exist. This decision does not
retire the generative pipeline; it stops it being the only option.

**`check_board.py` still applies in both modes.** Its six structural checks -
island membership, isolation barrier, decoupling proximity, cold-junction
distance, filter symmetry, routing completeness - read the board as it is on
disk and do not care who wrote it.

**A hand-edited board cannot be reproduced from source.** That is the real
price. It is acceptable for a frozen revision whose Gerbers already exist; it
would not be acceptable while the design was still moving.

**The MCP's seven write tools are now permitted** - in incremental mode, on a
board whose provenance has been recorded, with `netlist_fingerprint.py` run
afterwards if the edit could have touched connectivity.

## Rejected

**Stay purely generative.** Rejected: it makes a one-label fix cost a full
re-route and re-verification, which in practice means the fix never happens -
`I-006` and `I-024` have been open since the board was first routed for exactly
this reason.

**Go purely incremental and delete the pipeline.** Rejected: the measurements
still ahead (`I-003`, `I-004`, `I-013`) may force a change big enough to want a
clean regeneration, and `I-028` could still replace the whole input stage.
Throwing away a working generator before those are settled would be premature.

**Let an agent close KiCad automatically.** Rejected on the evidence: the
2026-09-07 loss was unsaved work in an open window. An agent cannot tell
whether a window holds unsaved work, and losing a user's edits to save a prompt
is a bad trade.
