# 0034 - Response to the Astra review: open-sensor default, buttons, layout repair

* Status: accepted (owner 2026-10-09 for D1; engineer's call, owner delegated, for D2-D3)
* Date: 2026-10-09
* Builds on: `0031`, `0032`, `0033`
* Evidence: `docs/reference/review-20261009-astra.md` (Codex GPT-6-Astra, whole-project
  review at commit `5f8abc6`; its evidence files stay in `production/review-20261009-system/`)

## Context

The independent review found that the routed board passes ERC/DRC but places
decoupling and buck parts far from their pins (R-01, R-02 - measured again by
Claude: LM5164 input cap 12.8 mm, bootstrap cap 21 mm, isolator 100 n 19-29 mm),
that the project documents disagree on what an open thermocouple does (R-16),
and it left the button question (I-108) open. Its other findings became rows
I-111 to I-120 in `ISSUES.md`.

## Decisions

**D1 - An open (broken) thermocouple trips by default.** The run-permit opens,
the channel and the reason show on the LCD, ACK only after the input reads valid
again. A channel can be set to "alarm only" as a deliberate, saved, per-channel
setting that the display shows; it is never the default. This is firmware
(I-104); the hardware does not change. Rejected: alarm-only default (an engine
could run with a temperature nobody measures), several modes (complexity
without a requirement).

**D2 - Buttons: on-board tact switches plus a 6-pin header in parallel.** The
LCD face sits ~24 mm above the board and the tallest 6 x 6 tact on LCSC is
9.5 mm, so board buttons may not reach a panel. A 2.5 mm JST XH 6-pin header
(BTN_UP/DOWN/SET/ESC/ACK + GND, LCSC C144397) wired in parallel lets panel
buttons (industrial 12-16 mm, vibration/oil/glove friendly) go on the door with
a cable, while the board buttons still work on the bench. Cost a few cents, and
the choice is no longer tied to an LCD drawing we do not have. The tact switches
get an LCSC code (basic part if one fits the footprint). Rejected: buttons only on
the board (may not reach the panel), panel buttons only (bench testing needs a
harness), guided actuator extensions (mechanics not drawn).

**D3 - Layout repair is local.** Move each decoupling/bootstrap/input capacitor
next to its pin, strip and re-route only those nets (and anything they displace)
with `finish.py`/`maze.py`/hand routes; keep every other route. No `place.py`
or `route24.py` on the board. Also add three fiducials (R-09) and relabel the
trip contact as RUN PERMIT C-NO (R-15). Rejected: regenerating placement with
pin-proximity rules (re-routes the whole board and costs a day of re-verification).

## Consequences

* `place.py` keeps its `pack()` rows for the next fresh layout only after a
  "near pin" rule is added (I-111); until then the board is the source.
* Firmware list I-104/I-119 includes D1; the button header adds one schematic
  part (`c_mcu.py`) and a `pcb sync`.
