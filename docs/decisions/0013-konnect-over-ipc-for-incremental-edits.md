---
status: accepted
date: 2026-09-13
deciders: Zain
amends: 0012
---

# Konnect over the KiCad IPC API for incremental edits

## Context

`docs/decisions/0012` established two modes for changing the hardware and then,
the same day, had to withdraw the tool it named for the incremental one: the
Seeed MCP's `add_wire` turned out to be a text append with no parser. That left
incremental mode with no agent-usable tool at all - only KiCad's GUI, driven by
a human.

`I-002` is the problem that makes this matter. The schematic has 171 symbols,
543 labels and **zero wires**. Fixing it means placing wires between specific
pins of specific symbols, and the blocker has always been the same: an agent
cannot wire what it cannot locate. The only source of absolute pin coordinates
was `kicad-tool sch query symbol --format json`, one symbol at a time, with the
resulting S-expressions written by hand - which is how the previous attempt
produced seven sheets that looked correct and a netlist with zero components.

## What was measured, not assumed

KiCad 10.0.3's own binaries were read on 2026-09-13:

- `kiapi.dll` and `nng.dll` ship with KiCad; the API server exists.
- `_eeschema.dll` contains `API_HANDLER_SCH`, so the **schematic** is served,
  not only the board. `DOCTYPE_SCHEMATIC` is in the enum and 22 `KOT_SCH_*`
  object types are defined, including `SYMBOL`, `PIN`, `LINE` and `JUNCTION`.
- `BeginCommit` / `EndCommit` exist: an edit made through the API lands in
  KiCad's own undo stack.
- **No plot or export command exists, and no run-DRC/ERC command** - only
  `InjectDrcError`, which reports *into* KiCad. Verification stays with
  `kicad-cli` and our scripts.
- The server was **disabled** (`api.enable_server: false`); it is now on, with
  a backup at `kicad_common.json.bak-20260913`.

## Decision

**Use `mixelpixx/Konnect` v0.11.1 as the incremental-mode tool.** It is a single
Rust binary that speaks the official IPC API to a running KiCad 10 and exposes
226 tools across 21 toolsets, loaded on demand.

Verified against this project's own schematic on 2026-09-13, read-only:

    get_pin_connections R1.1  ->  {"net":"TC1_RAW_P","pin_x":28.19,"pin_y":19.0}
    get_pin_connections U1.1  ->  {"net":"CS1_CTRL","pin_x":57.24,"pin_y":153.68}
    list_schematic_wires      ->  {"count":0}          <- I-002, confirmed
    export_netlist_summary    ->  171 components, every pin with net and x/y

`export_netlist_summary` returns what `I-002` needs in **one call**, and
`connect_pins` / `batch_connect_pins` wire by reference and pin number rather
than by coordinate. The toolsets that matter: `sch_wiring` (20),
`sch_components` (20), `sch_batch` (12), `sch_analysis` (15), `sch_export` (10 -
including `run_erc`, `generate_netlist` and an SVG/PNG **visual baseline**).

**The correction in 0012 stands** - the Seeed MCP's write tools were never
usable. This decision originally kept it for one job: reading files with KiCad
**closed**, which `validate.ps1` and CI need. That reason did not survive
testing.

### Retired 2026-09-14: Seeed-Studio/kicad-mcp-server

Konnect has a native S-expression engine, so it reads offline as well. Verified
with no KiCad process running:

    get_pin_connections R1.1  ->  {"net":"TC1_RAW_P","pin_x":28.19,"pin_y":19.0}
    list_schematic_wires      ->  {"count":0}
    find_orphan_items         ->  {"orphan_count":0}

That leaves the Seeed server with nothing of its own. Its writes were denied,
its online reads are Konnect's, and its offline reads are Konnect's too. The one
advantage claimed for it - importing `pcbnew` for measured rather than parsed
figures - was never actually needed: the EMC run that produced `I-045` took all
of its geometry from the `kicad` skill's own S-expression parser, including
`net_lengths`, `ground_domains`, `layer_transitions` and `decoupling_proximity`,
none of which the Seeed server produced at all.

Unwired from `.mcp.json` and its rules dropped from `.claude/settings.json`.
The files remain at `D:	ools\kicad-mcp-server` (1.3 MB) and nothing imports
them. `.claude/settings.json` now denies `taskkill` against KiCad instead,
which enforces `AGENTS.md` rule 8 mechanically rather than by good intentions.

## Why this is safer than what it replaces, not more dangerous

0012 worried that an IPC client "needs KiCad open, making the two-writer hazard
permanent". That was backwards and is retracted. Editing *through* KiCad means
KiCad is the only process writing the file, and `BeginCommit`/`EndCommit` put
the change where a human can Ctrl+Z it. Writing the file yourself under an open
editor is the 2026-09-07 failure.

**The real hazard is narrow, specific, and now handled.** Konnect issue #529:
on Windows, NNG makes an `ipc://` endpoint a *named pipe*, not a file, so a
client looking for `%TEMP%\kicad\api.sock` finds nothing, concludes KiCad is not
running, and **falls back to editing the file directly** - with KiCad holding it
open. Reproduced here exactly:

    pipe exists:  \.\pipe\C:\Users\malgh\AppData\Local\Temp\kicad\api.sock
    file exists:  False

`KICAD_API_SOCKET` is therefore set explicitly in `.mcp.json` and is **not
optional**. With it set, `open_project` reported `"ipc_available": true`.
Confirm IPC is live with a read call before any write; a write that silently
took the file path is exactly the failure this project has already had once.

## Rejected

**`Finerestaurant/kicad-mcp-python`.** Rejected in `docs/TOOLS.md` earlier for a
reason that was partly wrong. The correct reason: its own README says schematic
support is still being developed. PCB only, and `I-002` is a schematic problem.

**`mixelpixx/KiCAD-MCP-Server`** (2.2k stars, the popular one). It is the same
author's earlier, file-parsing generation; Konnect is the rewrite onto the
official API. Taking the older one for its star count would be choosing the
architecture we just rejected in the Seeed server.

**`Huaqiu-Electronics/kicad-mcp`.** Uses IPC and covers schematic and PCB, but
18 stars and 46 commits against Konnect's 634 and 893.

**Staying with `kicad-tool` and hand-written S-expressions.** Not rejected -
retained. It is the only path when KiCad is closed, and it is what the
generative pipeline uses. Konnect is added beside it, not over it.

## Open, and the owner's to settle

**Konnect is AGPL-3.0.** Free for individuals, students and open-source work;
the project states that businesses building on or around it must open-source
that work under the same licence, and sells commercial licences. Using it to
edit our own schematic is very probably outside that - a board is not a
derivative work of the editor, any more than a binary is of the compiler - but
this is a company product going onto a real machine, so the reading should be
confirmed rather than assumed. Tracked as `I-046`. Nothing has been distributed
and no Konnect code is in this repository; the exposure today is zero.
