# 0028 — Shrink the board before ordering; stay on four layers

* Status: **proposed — the owner chooses the target size** (see "Open")
* Date: 2026-10-06
* Deciders: owner (raised by an outside engineer; "no mechanical constraint")
* Relates to: `I-090`, `I-025`, `0014` (four layers), `0024` (3 modules), `I-078`

## Context

An experienced engineer told the owner the board is large with empty areas:
it could be much smaller, or two layers, and perhaps 100 x 100 mm "with
difficulty".

Measured on the REV A2 board (KiCad 10, courtyards, 2026-10-06):

* Outline **250 x 140 mm = 350 cm²**, four layers.
* 193 parts, all on the top side. Their courtyards total **67 cm², 19 % of the
  board**. The largest are U1 (DIP-40, 51.5 x 18.4 mm), K1, eleven terminal
  blocks (16 x 11 mm each), J2 (1 x 16 LCD header, 42 mm long), U12, U15.
* **No decision or calculation ever justified 250 x 140.** It came from the
  first 8-channel plan (`board/config.py`, there since `f60e6d3`, 2026-09-07)
  and was never questioned. `CALCULATIONS` 5.5 already notes it is "not an
  optimized minimum".
* The owner says there is **no enclosure or panel constraint** on the shape.

A to-scale map is in `production/board-size-map.svg` (local, not tracked).

### Prices (JLCPCB online calculator, 2026-10-06)

Bare PCB, 5 boards, 1.6 mm FR-4, green, HASL, calculator defaults. Shipping by
DHL is about $31-33 in every case. Not checked: PCBWay, and assembly (PCBA) and
stencil, which change much less with size.

| Size | 4 layers | 2 layers |
|---|---|---|
| 250 x 140 (now) | **$46.60** ($25 engineering fee + $21.60 board) | $20.90 |
| 160 x 100 | **$34.90** ($25 + $9.90) | $11.70 |
| 100 x 100 | **$8.00** (special offer, no engineering fee) | $4.00 |

So the money is small next to the parts (eight MAX31856 per board). The
step that matters is 100 x 100: four layers become **$8** because the $25
engineering fee disappears. 160 x 100 saves only ~$12 per order.
The bigger gain of any shrink is **panel space**: three modules (`0024`).

## Options

| | Target | What changes | Risk |
|---|---|---|---|
| **A** | **~160 x 100 mm** (−55 % area) | Placement and routing only. Schematic, netlist, BOM and firmware stay the same | Low: re-place, re-route, re-verify everything (DRC, power stage `0026`, vias I-075, drill file) |
| B | **100 x 100 mm** (−70 %) | Also: U1 DIP-40 → ATmega32A-AU (TQFP-44, SMD, same firmware); J2 1x16 → 2x8 header; probably parts on both sides; a denser analogue area | Medium-high: a schematic change, a new netlist baseline, a tighter isolation layout, and maybe two-sided assembly (costs more) |
| C | Two layers | Already tried in the old `8ch-2layer` (now `_old/`): hours of routing, 14 unfinished `+3V3_SENS` connections, and no ground plane under the microvolt inputs | Rejected: it saves $14-26 per order at the cost of the 50 m-cable noise immunity. Shrinking saves as much without that loss |

## Recommendation

**Shrink, and keep four layers.** The outside engineer was right about the
size and wrong about the layers.

The 2026-10-06 audit of inherited choices (I-091 to I-099) shows that the size
is not the only thing carried over unexamined. Several of those choices set the
board's edge length and area: where the HMI goes, the relay, the shield
screws, isolated RS-485, the DIP-40 and the channel pitch. So **the target size
is chosen after the owner answers I-091 to I-096, not before**:

* If the answers keep every part, go to A (~160 x 100), with a layout-only change.
* If the owner accepts the part changes in I-095 (TQFP MCU, 2x8 header, J6/C51/
  R17-R24 removed), and maybe I-093/I-094, then **B (100 x 100, $8) becomes
  realistic**. In that case it is one schematic change plus one layout pass,
  done once.

## Remaining design work

1. Complete I-091 (HMI delegated to design team in `0029`), I-092 (dry-contact
   ratings), I-093 (shield termination), I-094 (RS-485 form) and I-095 (verified parts).
   The owner conditionally accepts part changes (update below). I-096 is for
   the agent to do.
2. Then choose A or B. The agent proposes the floor plan and the owner approves
   it before any board write.

## Consequences

* `production/8ch-reva2/` stays **on hold**. The shrink is a new layout, so
  the board revision becomes **A3** (silkscreen, `BOARD_REV`, firmware
  `APP_TARGET_BOARD`).
* Every hardware gate is re-run and re-quoted after the shrink. The power-stage
  distances in `CALCULATIONS` 5.2 are re-measured, not assumed.
* I-025 (two-layer backup) is closed; the backup is in `_old/8ch-2layer/`.

## Update 2026-10-07 — sourcing candidate and conditional part changes

The owner permits changing the MCU and other components **provided the exact
replacements are available and suitable for normal use**. Exact choices,
ATmega32A-AU stock, proposed deletions and the floor plan still need review. Check
pin mapping, electrical/reset behavior, package, lifecycle and dated supplier
stock before committing to a replacement. The LCD will sit off the main PCB;
button mounting and cable distance remain design work (I-091, delegated in `0029`).

**NORI Solutions is the likely supplier, not a final order decision.** The
owner reports local two-layer fabrication and imported four-layer boards.
The supplied calculator screenshot at <https://norisolutions.com/pcb-fabrication>
shows **5 boards, 100 x 100 mm, 4 layers, FR-4 1.6 mm, green, EGP 2,530 total
(EGP 506 each), estimated 2–3 weeks**. No Gerbers are uploaded in the screenshot.
This is an indicative bare-board quote, not proof the current design fits that
size. Finish, stack-up, copper, manufacturing limits, assembly, tax and delivery
inclusions must be confirmed; direct page access in this cloud returned HTTP 403.

Compare like-for-like delivered totals: PCB + shipping + customs/taxes/clearance
+ payment costs, with assembly and components separately identified. The
historical JLCPCB 100 x 100 quote above totals about USD 39–41 with shipping,
before import costs. Re-quote the actual verified A3 size and specifications
with both suppliers before ordering; do not assume the promotional price lasts.
