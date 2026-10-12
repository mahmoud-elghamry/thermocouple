# Current state

**Read second, after AGENTS.md; then read all of ISSUES.md (P0 first). Hard limit: 60 lines.**
**Last updated:** 2026-10-12 (workstation, branch `cheaper-parts`: cost-down variant `0036`).

## Branch `cheaper-parts` (2026-10-12, `0036`) - the cost-down variant of the 24-ch board

* TMP126 x6 (+ R443 22k DIN-DOUT, R415 gone), CA-IS3761HW x3, RS-485 block DNP (footprints kept,
  `DNP.txt`), BOCHEN trimmer, SAMWHA 22u; external watchdog tried and removed. Parts ~$72/board.
* Board edited incrementally (`gen/delta.py`, `capnear.py`, hand routes); TC traces cut by the first
  delta run were restored from `output/bak/thermo24-pre-0036.kicad_pcb` (analog nets now identical to it).
* Terminals J601/J701/J702/J703 turned to face the edge (`0036` D7); supplier files are an RFQ (D8).
  Gates and the release folder for NORI: next line (written after the release run).
* Next: I-123 stock check and NORI quote for this variant (older sets are in `_OLD_DO_NOT_ORDER`).

## Where we are

* REV A2 (8ch, reference) passes every gate (below), never ordered; next order is the 24-ch **REV A3**.

## 2026-10-08: ONE 24-channel board (`0031`) — read it before any work

* `0031` supersedes most of `0030`; still valid there: D2 comms never in trip path, D5, D8.
* Front end **3x AD7124-8** on one isolated island in parallel; 20 M TC- bias, mid-rail reference
  wire, CJ sensors at the terminals, open-TC check one channel per scan (~4 s each).
* 20x4 LCD (bought locally) + 5 buttons (+ panel header, `0034` D2); trip + alarm relay (30 VDC / 1 A signal);
  isolated RS-485/Modbus (ADM2587E); shield at panel entry; **all parts from one source** (NORI, I-103).
* `0032` = circuit + parts after Codex/Opus reviews (power `CALCULATIONS` 7, front end, floor plan).

**2026-10-09: 24-ch board, `hardware/24ch/` (README there), decisions `0032`-`0033`.**
Schematic 467 symbols, ERC 0/0, 12 pages A3/A4. Board 170 x 145 (`0033` D1). Fab NORI (I-106); parts ~$105 (`gen/cost.py`).
Board routed 2026-10-09 (history: git log). The 2026-10-09 fab set is **outdated**, moved to `production/_OLD_DO_NOT_ORDER/`
(board changed 2026-10-11) - never order from it; `gen/fab.py` makes a new one. Board: `hardware/24ch/thermo24.kicad_pcb`.

## Start here - next steps

**2026-10-11 (one session):** docs synced to `0031`-`0035`, `docs/check_docs.py` guards them (CI too);
ISSUES re-triaged (P0 = blocks the order only). NORI: our spec rides in ORDER-NOTES (I-106, I-105).
Board (`thermo24.kicad_pcb`, backups `output/bak/`): LM5164 stage re-laid (`gen/buck24.py`), ISO7761 +
MCU caps beside pins, crystal to the XTAL pins (I-121), J503 panel-button header (`0034` D2), fiducials,
installer silk (I-113), V_BIAS guard pours (`gen/vbias_pour.py`, I-105). Gates: DRC+parity+refill 0/0/0;
ERC 0/0 (468 symbols); `pincaps.py` 33/33 pass (exit 0).
New tools: `move.py`, `capnear.py` (spot search, rip, `via`), `finish.py dedupe`, `guard.py` on every writer.
**I-111 closed** (`0035` D6, owner: AD7124 supplies by plane vias, REGCAP/REFOUT <= 5 mm): `pincaps.py` 0 over.
**Next (only P0 left = I-078):** send `production/24ch-reva3-20261011-094327-940d10/` (git 7c7e25c, clean;
DRC 0/0/0, pincaps 0) to NORI for the turnkey quote incl. ACCESSORIES.csv. I-108 closed (owner: buy a 2004A that
fits H6-H9/J502), I-106/I-103 closed (ORDER-NOTES). Board warnings: 8 dangling stubs, 0 errors.
Then firmware P1 (I-118/119/104/100); bench P2 (I-120, I-101, I-105).

## Measured, not claimed (REV A2, before the shrink)

8-ch REV A2: ERC/DRC 0/0, netlist identical, firmware 4 builds / 3 suites PASS (2026-10-09 snapshot
`production/validation-20261009-043553-906505`; history in git). No physical qualification/SPICE.

## Preserve for hardware work
* Konnect is the only KiCad MCP (`0013`); run `board_provenance.py --check` before any board write, `--record` after.
* `route.py` re-drills vias to a 0.15 ring after the SES import (I-075). Check the exported drill file, not only DRC.
* `build.py` starts from `05d6abd` + `sch_layout/reva2.py`. kicad-tool clones inherit their MPN (I-054).
* `kicad-tool pcb sync` needs `KICAD10_FOOTPRINT_DIR`. Freerouting is deterministic for a given input.
* Never change a baseline to make a gate pass. Never edit `hardware/single-channel/` or anything in `_old/`.
