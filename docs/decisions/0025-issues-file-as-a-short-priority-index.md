# 0025 — ISSUES.md is a short priority index; closed issues live in their own file

* Status: accepted
* Date: 2026-10-01
* Deciders: owner, with the agent's recommendation
* Relates to: `I-056`, `0001`

## Context

The "one line per issue" rule existed so the file would not grow unreadable.
It did not hold. By 2026-09-30 `ISSUES.md` was **72 KB**:

* 94 rows, one of them 7.7 KB (`I-028`);
* four narrative sections from the 2026-09-29 review;
* open and closed issues mixed, and no order of importance.

An agent reads a file that size partly or not at all, which is the failure the
rule was meant to prevent. The owner asked which is right: long rows that
explain everything, or short rows.

An agent does not need the explanation in the row. It needs enough to know
what is wrong and how much it matters, plus where to look. It follows the
pointer when it works on the issue. Long text in the index costs every reader,
every session, for the benefit of the one who works on that row.

## Decision

* `ISSUES.md` holds **open issues only**, grouped by priority:
  * **P0** blocks the order;
  * **P1** before a unit protects a machine;
  * **P2** measured at the bench;
  * **P3** later or accepted.
* Each row is at most about 600 characters: what, why, evidence pointer, close-when.
* Detail goes where it belongs: arithmetic to `CALCULATIONS.md`, choices to
  `decisions/`, logs to `production/review-*/`.
* Closed issues move to **`ISSUES-closed.md`**. It is an archive, read only when
  an old number comes up.
* A finding judged overstated **keeps its row**, marked "Review weight: rated X,
  agreed Y" with the reason. Disagreement is visible, never silent.
* No narrative sections. What a review could not verify becomes one bullet
  under "Not verified by anyone yet".

Result on 2026-10-01: 72 KB → about 11 KB. The pre-restructure text is in git
history (`7107a94`) and, for the uncommitted 2026-09-29 review, in
`production/review-20260929/ISSUES-as-reviewed-20260929.md`.

## Rejected

* **Keep long rows "so every agent understands"**: this is what produced 72 KB.
  The explanation is still one pointer away.
* **One file per issue**: `0001` rejected a scatter of small files, because a
  list you cannot see at once is not an index.
* **Delete closed issues**: their "what fixed it" is how a regression gets
  recognised.

## Consequences

* A new agent reads `AGENTS.md`, `STATE.md` and then all of `ISSUES.md`, which
  is now possible in one read.
* Anyone adding a row keeps it short. A row that needs more has a missing
  calculation or decision file.
