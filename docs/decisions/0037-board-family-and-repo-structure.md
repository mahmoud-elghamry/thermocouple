# 0037 - One board family (8 / 24 / 36 channels), one firmware, products as folders

* Status: accepted (owner, 2026-10-14) for the direction; each product's details are decided in its own work
* Date: 2026-10-14
* Builds on: `0031` (one 24-ch board), `0036` (cost-down variant, merged into `main` by the owner, 1904891)

## Context

The 24-ch board (cost-down variant `0036`) is the one being quoted and ordered. The owner wants an
8-channel version as a company option and a new 36-channel board, a simulation others can run, and a
report for management. Work will run in several chats at once. Until now each product step used a
branch and `docs/STATE.md` held one product, so parallel work would collide in one 60-line file.

## Decisions

**D1 - One board family on the 24-ch architecture.** The 8-ch and 36-ch boards reuse the 24-ch circuit
blocks: banks of one AD7124-8 (8 differential channels) with TMP126 cold-junction sensors, input
protection, CA-IS3761 isolation, the LM5164 supply, trip and alarm relays, 20x4 LCD and buttons, isolated RS-485/Modbus
(fitted: owner 2026-10-14, reversing `0036` D2). A board differs by its number of banks: 8 ch = 1, 24 ch = 3,
36 ch = 5 (40 inputs, 36 used). The REV A2 8-ch board (MAX31856, `hardware/8ch/`) becomes reference
only; a new 8-ch board is derived from the 24-ch one.
* Not decided here: the 36-ch board's isolated supply, size and scan time (5 banks change all three) -
  reviewed in its own work before any layout.
* Rejected: keeping MAX31856 for 8 ch (two front ends, two firmware drivers, two test procedures).

**D2 - One firmware for the family.** Protection logic (per-channel setpoints, trip within 1 s,
latch and ACK, open-sensor handling, watchdog heartbeat) is written once; the board is chosen at
build time (number of banks). Thermocouple type per channel (K, J) is an option to study in the
firmware work: the AD7124 input range covers both, the difference is the conversion table.
The firmware chat decides the folder layout; until then `firmware/` holds the REV A2 8-ch images.
* Rejected: one firmware per board (the safety logic would be written and tested three times).

**D3 - Products are folders, branches are variants or short work.** `main` is the official line.
`hardware/<product>/` holds each board; a branch is used only for a variant of the same product or
for one chat's work, which the owner merges (agents never merge, AGENTS rule 3). The 24-ch board
with the original parts is kept as tag `24ch-premium` (commit c0dca80).

**D4 - State per product.** `docs/STATE.md` becomes a short index and the cross-product state.
Each product keeps its own `STATE.md` (`hardware/24ch/`, `hardware/8ch/`, `firmware/`, later
`hardware/36ch/`), each at most 60 lines and checked by `docs/check_docs.py`. `docs/ISSUES.md`
stays one file; a new row starts with its product in brackets ([24ch], [8ch], [36ch], [fw], [all]);
rows without a tag are 24-ch.

## Consequences

* A chat updates its product's `STATE.md`, adds the index line in `docs/STATE.md` only when the
  product's headline changes - so parallel chats rarely touch the same lines.
* `GOAL.md` names the family. RS-485 is fitted again (owner, 2026-10-14): the 24-ch release change
  (DNP flags, BOM/CPL, ASSEMBLY-SPEC) is done in branch `24ch-order`.
* Branches from `main` (2026-10-14): `24ch-order`, `firmware` (the simulation demo too, it needs the
  firmware), `8ch`, `36ch`. The management report needs no branch (it reads, it does not change sources).
