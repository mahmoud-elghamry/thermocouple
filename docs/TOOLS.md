# Tools and commands

Only commands that have actually been run in this repository. If one stops
working, fix it here rather than working around it in a session.

---

## Installed

| Tool | Where | Used for |
|---|---|---|
| KiCad 10.0.6 (same as the cloud; updated 2026-09-26) | `C:\Program Files\KiCad\10.0` | everything hardware |
| KiCad Python (`pcbnew`) | `…\10.0\bin\python.exe` | the board generator and router scripts |
| `kicad-cli` | `…\10.0\bin\kicad-cli.exe` | ERC, DRC, netlist, BOM, Gerbers, 3D render |
| `kicad-tool` | `%USERPROFILE%\.local\bin` | schematic edits, schematic↔board sync. Install: `uv tool install git+https://github.com/mash/kicad-skills.git` - **never** `pip install kiutils`, that pulls upstream and breaks it |
| Freerouting 2.4.1 | `%LOCALAPPDATA%\kicad-tools\freerouting.jar` | autorouting via Specctra DSN/SES |
| Temurin JRE 25 | `%LOCALAPPDATA%\kicad-tools\jre25\*\bin\java.exe` | runs Freerouting |
| avr-gcc | see `firmware/build.ps1` | firmware |
| Konnect | `C:\Users\Public\AI-Tools\konnect\konnect.exe` (what `~/.claude.json` registers; `sch_layout/kon.py` needs it on PATH or in `KONNECT`) | the KiCad MCP - 226 tools; IPC when KiCad is open, S-expressions when it is closed |

Freerouting and the JRE are **not** in the repository. Override the paths with
`FREEROUTING_JAR` and `FREEROUTING_JAVA` if they move.

## Hardware — source-preserving validation

```powershell
pwsh -File hardware\8ch\run_all.ps1
```

This is now the default: copy the four KiCad source files into a fresh
`production/validation-*` directory, run ERC and the A0 netlist contract, then
refill and DRC the copy. The source hashes must remain unchanged. Errors,
unconnected pads and parity failures stop the run; warnings are reported.
KiCad ERC exit 5 can mean warnings, so its report is parsed before accepting it.

```powershell
pwsh -File hardware\8ch\test_gates.ps1  # injected native/report failures
```

## Hardware — regeneration

The explicit `run_all.ps1 -Regenerate` path checks every native exit and report,
and refuses while KiCad editors are open. **Authorized since the owner lifted
the REV A0 freeze on 2026-09-15** (`docs/decisions/0014`). It re-routes the
whole board, so everything after it has to be re-verified. The individual
commands, from `hardware/8ch/`:

```powershell
$py  = 'C:\Program Files\KiCad\10.0\bin\python.exe'
$cli = 'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe'
$env:KICAD_CLI = $cli
$env:KICAD10_FOOTPRINT_DIR = 'C:\Program Files\KiCad\10.0\share\kicad\footprints'

python sch_layoutuild.py --in-place       # schematic: base 05d6abd + sch_layout/ (own ERC + netlist gate)
& $cli sch erc --output erc-report.rpt --severity-error --severity-warning thermocouple_8ch.kicad_sch
& $cli sch export netlist --output thermocouple_8ch.net thermocouple_8ch.kicad_sch
python apply_rules.py                        # net classes + .kicad_dru into the project
& $env:KICAD_TOOL pcb sync thermocouple_8ch.kicad_pcb thermocouple_8ch.kicad_sch
& $py generate_board.py                      # placement, planes, keepouts, PE ring, silkscreen
& $py route.py --passes 25 --threads 1       # DSN -> Freerouting -> SES -> stitching -> pours
& $cli pcb drc --output drc-report.rpt --severity-error --severity-warning --schematic-parity thermocouple_8ch.kicad_pcb
& $py close_gaps.py                          # joins whatever DRC still reports as open
& $py check_board.py                         # structural checks DRC cannot make
```

**Since the schematic is hierarchical (I-062), the order is different**, learned
on the REV A2 run (2026-09-28):

1. Schematic changes go into `sch_layout/` (a new part or a pin change in
   `reva2.py`-style code called from `fixes.py`, its position in `extra.py`,
   its block in `rootlayout.py`). Then run `build.py --in-place`.
   (`populate_schematic.py` was the flat-sheet tool; it is in `_old/` since
   2026-10-06.)
2. A deliberate connectivity change needs a new baseline. Write it only
   after `build.py`'s fingerprint lists exactly the differences you intended.
3. `kicad-tool pcb sync` needs `KICAD10_FOOTPRINT_DIR` set. Without it, every
   footprint comes back "unresolved" and new parts are not added.
4. `build.py` changes the sheet files, so `board_provenance.py --check`
   reports DRIFT. That is not hand work; run `--record`.
5. **Freerouting once stopped by itself after 2 s** ("Fanout stage
   interrupted", 151 unconnected), and `route.py` still exited 0. Re-running
   `generate_board.py` + `route.py` worked. Always read the unconnected count;
   DRC is the gate that catches it.

### After any generator run that ADDED parts

```powershell
python hardware\8ch\check_mpn_consistency.py          # --fix rewrites mismatches
```

`kicad-tool` creates a new symbol by cloning an existing one of the same type,
and the clone brings the donor's `MPN`/`Manufacturer`/`LCSC` with it. On
2026-09-16 that gave six new capacitors a **100 nF** part number and six new
resistors a **10 k** one. ERC passed, the netlist fingerprint passed - neither
looks at MPN. Run this whenever `build.py` adds symbols.
`I-054`.

## Firmware

```powershell
pwsh -File firmware\build.ps1     # -Wall -Wextra -Werror, plus host unit tests
```

## Visual check

```powershell
& $cli pcb render --output output\board_3d_top.png --width 1600 --height 1000 --side top --quality high thermocouple_8ch.kicad_pcb
```

## Gerbers — only when DRC is clean

Do not run this while `docs/ISSUES.md` still lists `I-001`.

A release goes to its own folder per revision under `production/`, not next to
the sources. The current one is `production/8ch-reva2/` (2026-09-28, with
`RELEASE.txt`, the upload zip and `validation-report/`). Superseded packages move to
`production/_OLD_DO_NOT_ORDER/` (REV A0, REV A1 - none was fabricated); stale
`validation-*` runs are deleted. `production/` is gitignored.

**Name the layers.** Without `--layers`, KiCad 10 plots every layer - Fab,
Courtyard, User.1-4 - and a fab may read them as copper or silk.

```powershell
$out = '..\..\production\8ch-reva2'
New-Item -ItemType Directory -Path $out | Out-Null     # fails if it exists: new revision, new folder
& $cli pcb export gerbers --check-zones --layers 'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts' --output "$out\" thermocouple_8ch.kicad_pcb
& $cli pcb export drill   --output "$out\" --format excellon --excellon-units mm --generate-map --map-format gerberx2 thermocouple_8ch.kicad_pcb
& $cli pcb export ipcd356 --output "$out\thermocouple_8ch.d356" thermocouple_8ch.kicad_pcb
& $cli pcb export pos     --output "$out\cpl.csv" --format csv --units mm --side both thermocouple_8ch.kicad_pcb
& $cli sch export bom     --output "$out/bom.csv" --fields 'Reference,Value,Footprint,MPN,Manufacturer,LCSC,${QUANTITY}' --group-by 'Value,MPN,LCSC' thermocouple_8ch.kicad_sch
```

The technician's kit (every through-hole part plus what is not on the board;
`0027`): `<KiCad python> hardware\8ch\kit_list.py <release>	echnician_kit.csv 3`.

Copy `docs/STATE.md`'s check numbers into the release folder as well. A
fabrication package without the report it passed is not a package.

## Schematic layout (`I-002`, `I-062`) - `hardware/8ch/sch_layout/`

**The schematic is six files, all A4, since 2026-09-26** (`0019`, `0021`):
`thermocouple_8ch.kicad_sch` (the root, an index of sheet blocks),
`power.kicad_sch`, `mcu.kicad_sch`, `isolation.kicad_sch`,
`relay_rs485.kicad_sch`, and `channel.kicad_sch` (used by TC1-TC8). Nets
that stay inside one sheet carry its path: `/TCn/FILT_P`, `/POWER/+24V_RAW`,
`/RELAY_RS485/GND_RS485`. A new one needs an `apply_rules.py` pattern
`/SHEET/NAME`, or it lands in Default and the isolation rule fires; board
scripts compare through `board/units.bare()`, which drops a functional-sheet
path. Print it: `kicad-cli sch export pdf --pages 1,2,3,4,5,6` gives the root,
the four functions and TC1 (TC2-TC8 are the same drawing). Compare netlists across a rename with
`netlist_fingerprint.py OLD NEW --allow-renames [map.json]` (nets matched by
pins), and carry a rename to the board with
`<KiCad python> sch_layout/rename_board_nets.py BOARD map.json` **before**
`kicad-tool pcb sync` - sync alone renames pads and leaves tracks behind.

```sh
python hardware/8ch/sch_layout/build.py              # scratch copy, prints the gate
python hardware/8ch/sch_layout/build.py --in-place   # rewrite the schematic
```

Measured 2026-09-24 in the cloud: about a minute; netlist IDENTICAL, ERC 0/0,
output equal to the committed sheet apart from UUIDs. With the `hier.py` step,
2026-09-26 on the workstation: 3 min, IDENTICAL, ERC 0/0 (put KiCad's `bin`
and the Konnect folder on PATH first). Every write goes through
Konnect over stdio (`kon.py`). Needs `konnect` and `kicad-cli` on PATH and
`KICAD10_SYMBOL_DIR` set (the cloud hook does all three; on the workstation set
it to `C:\Program Files\KiCad\10.0\share\kicad\symbols`).

| File | Holds |
|---|---|
| `build.py` | entry point and the gate |
| `fixes.py` | netlist corrections carried by the drawing (`I-058`, `I-057`) |
| `channel.py`, `chmap.py` | the channel template and which parts are which channel |
| `extra.py` | placement of every other block, in 1.27 mm grid units |
| `relayout.py` | move/rotate a part and carry its pin labels and NC flags |
| `route.py` | wires: never through another net's pin, wire, pin lead or a body |
| `labels.py` | one label per wired group, placed where its text is clear |
| `hier.py` | flat wired sheet -> A4 root + `channel.kicad_sch` x 8 + the functional sheets (`0019`, `0021`) |
| `rootlayout.py` | which functional block each root item belongs to |
| `funcsheets.py` | moves each block onto its A4 sheet (POWER, MCU, ISOLATION, RELAY_RS485; `0021`) |
| `sexpr.py` | minimal KiCad S-expression reader/writer (no kiutils) |
| `rename_board_nets.py` | renames board nets in place from a rename map |

**It starts from a label-only base** (`05d6abd`) and refuses one with wires.
Change a part's position in `extra.py`/`channel.py`, re-run, look at the
render (`kicad-cli sch export svg`), repeat. A netlist difference means the
layout moved connectivity - fix the script, never the baseline.

## Which mode am I in, and may I write?

Two ways to change the hardware, and a guard that tells them apart -
`AGENTS.md` rules 8 and 9, `docs/decisions/0012`.

```powershell
python hardware\8ch\board_provenance.py --status   # report, never fails
python hardware\8ch\board_provenance.py --check    # exit 1 if writing would lose work
python hardware\8ch\board_provenance.py --record   # after a generator run
```

`--check` fails for two reasons, and the message says which:

- **KiCad holds the project open** (`~*.lck` next to the board). Ask the user
  to close it. **Do not close KiCad yourself** - it may hold unsaved work,
  which is exactly how the board was lost on 2026-09-07.
- **The files have drifted** from the last generator run, so hand edits exist
  and regenerating would destroy them. Either fold them back into `board/`, or
  abandon them deliberately and `--record` again.

## One KiCad MCP, and what else there is

`Konnect` is the only KiCad MCP wired up. The Seeed server was
retired 2026-09-14 - `docs/decisions/0013`. Which layer does what:

| Layer | Tool | When |
|---|---|---|
| Live editing and queries | **Konnect** | KiCad open **or** closed |
| Offline deep analysis | `kicad` skill analysers | feeds `emc`; produces `net_lengths`, `ground_domains`, `layer_transitions` |
| File read/write CLI | `kicad-tool` skill | scripted edits, the generative pipeline |
| **This board's own rules** | `check_board.py`, `netlist_fingerprint.py`, `board_provenance.py`, `check_mpn_consistency.py`, `validate.ps1`, `test_gates.ps1` | **nothing generic can replace these** |

The last row is the point. Island membership, the isolation barrier, the
cold-junction distance, the 167/154/555 netlist contract, whether a generator
run would destroy hand edits - these are this project's rules. No MCP knows
them and none ever will.

## The KiCad IPC API - measured on this machine, 2026-09-13

KiCad's official API is protobuf over an NNG socket. Measured by reading the
installed binaries, not the docs:

| | Finding | Where |
|---|---|---|
| Server present | `kiapi.dll`, `nng.dll` | `KiCad/10.0/bin/` |
| **Server enabled** | **`"enable_server": false`** | `%APPDATA%/kicad/10.0/kicad_common.json` |
| Client library | `kipy` **not installed** | `pip install kicad-python` |
| Version | 10.0.3 | `kicad-cli version` |
| Schematic handler | **`API_HANDLER_SCH` present** | `_eeschema.dll` |
| Board handler | `API_HANDLER_PCB` present | `_pcbnew.dll` |
| Document types | `DOCTYPE_SCHEMATIC`, `DOCTYPE_PCB`, `DOCTYPE_SYMBOL`, `DOCTYPE_FOOTPRINT` | `kiapi.dll` |
| Schematic objects | 22 `KOT_SCH_*` including **`SYMBOL`, `PIN`, `LINE`, `JUNCTION`, `LABEL`, `NO_CONNECT`** | `kiapi.dll` |
| Edit commands | `GetItems`, `CreateItems`, `UpdateItems`, `DeleteItems`, `ParseAndCreateItemsFromString`, `HitTest`, `GetBoundingBox` | `kiapi.common.commands` |
| Transactions | **`BeginCommit` / `EndCommit`** - edits land in KiCad's undo stack | `kiapi.common.commands` |
| Plot / export | **zero commands** | grep found none |
| Run DRC / ERC | **none** - only `InjectDrcError`, for reporting *into* KiCad | `kiapi.board.commands` |

So the shape of it: **IPC can edit, and cannot verify.** `kicad-cli` and our
scripts stay the verification path either way.

**Correction to an earlier claim in this file.** It used to say the IPC API
"needs KiCad open, making the two-writer hazard permanent". That is backwards.
Editing *through* KiCad's API means KiCad is the only process writing the file,
and the edit joins its undo stack - which is **safer** than writing the file
under an open editor, which is precisely the 2026-09-07 failure. The real
Windows hazard is different and specific: a client that cannot find the socket
may **fall back to editing the file directly** while KiCad has it open. On
Windows, NNG `ipc://` is a named pipe under `\.\pipe\`, not a file, so
socket auto-detection fails on a default install. Set `KICAD_API_SOCKET`
explicitly before letting any IPC client write, and confirm it is live with a
read call first.

The "cannot plot or export before KiCad 11" half of that claim was correct and
is confirmed by the table above.

## Reading a datasheet

`pdftotext` ships with Git for Windows - no separate poppler install needed.

```powershell
& "C:\Program Files\Git\mingw64in\pdftotext.exe" -f 12 -l 14 docs
eference\datasheets\ATmega32A.pdf -
```

It is on the Bash tool's PATH as plain `pdftotext`, and on PowerShell's only by
full path. `-f`/`-l` bound the page range; a 400-page datasheet dumped whole is
unreadable. Version here is 4.00 (Xpdf build), verified 2026-09-13.

## EMC and SPICE

The `emc` skill consumes the `kicad` skill's analyser JSON, so run those first:

```powershell
python $env:USERPROFILE\.claude\skills\kicad\scriptsnalyze_schematic.py thermocouple_8ch.kicad_sch --analysis-dir ..\..\docs
eferencenalysispython $env:USERPROFILE\.claude\skills\kicad\scriptsnalyze_pcb.py thermocouple_8ch.kicad_pcb --full --analysis-dir ..\..\docs
eferencenalysispython $env:USERPROFILE\.claude\skills\emc\scriptsnalyze_emc.py --analysis-dir docs
eferencenalysis\ --text
```

Set `PYTHONIOENCODING=utf-8` first or the text report dies on an arrow
character under cp1252. `docs/reference/analysis/` is gitignored.

First run: 2026-09-13, 122 findings, triaged into `I-045` - most of the volume
is one heuristic firing per net. **The `spice` skill cannot run here:** it
needs ngspice, LTspice or Xyce on PATH and none of the three is installed.
KiCad's built-in ngspice is a library inside the GUI, not a CLI, so it does not
satisfy the skill.

## Cloud sessions (Claude Code on the web)

`.claude/hooks/session-start.sh`, registered as a `SessionStart` hook in
`.claude/settings.json`. It runs only when `CLAUDE_CODE_REMOTE=true`; on this
workstation it exits at once. It installs avr-gcc, KiCad 10 `kicad-cli` (KiCad
PPA), `pwsh`, `uv` + `kicad-tool`, and Konnect 0.11.1 (prebuilt Linux release -
keep the version equal to `konnect.exe --version` here), then registers Konnect
at **local** scope in the container. `.mcp.json` stays empty. No
`KICAD_API_SOCKET` is needed there: no KiCad GUI, so Konnect edits files directly.
First session takes a few minutes; its last lines list any tool that is
**MISSING**, with a log path. Tested 2026-09-24 in WSL Ubuntu without root:
pwsh, uv, kicad-tool and Konnect installed; the apt steps need root, which the
cloud container has.

**Measured in the real cloud container, 2026-09-24** - WSL did not show this:
the proxy returns **403 for `ppa.launchpadcontent.net` and `astral.sh`**, and
`add-apt-repository` fails (no `apt_pkg`). Worse, `apt-get install kicad` then
succeeds from Ubuntu's own archive with **KiCad 7.0.11**, which cannot open
these files, and the summary said *all tools present*. The hook now accepts
only a `kicad-cli` reporting `10.x`, and falls back to KiCad's image
`ghcr.io/kicad/kicad:10.0` (10.0.6; `docker.io` answers 429) behind a
`kicad-cli` wrapper in `~/.local/bin`, plus the stock library tables in
`~/.config/kicad/10.0`. `uv` falls back to PyPI. GitHub release downloads
(pwsh, Konnect) work. Result: every tool present, Konnect connected, second
run 16 s. The same image carries KiCad's `pcbnew` Python and `ngspice`, so
`-Regenerate` is closer than the table below says - Freerouting and a JRE are
what is still missing.

| Workstation | Cloud equivalent |
|---|---|
| `pwsh -File firmware\build.ps1` | `make -C firmware all test` (build.ps1 needs MSVC) |
| `pwsh -File hardware\8ch\run_all.ps1` | `pwsh -File hardware/8ch/validate.ps1` |
| `run_all.ps1 -Regenerate` | by hand, measured 2026-09-24: Temurin JRE 25 (`github.com/adoptium/temurin25-binaries`) and `freerouting-2.4.1.jar` (`github.com/freerouting/freerouting` releases) into `~/.local/opt`; KiCad's footprints copied out of the image; then `apply_rules.py`, `kicad-tool pcb sync`, and `generate_board.py` / `route.py` / `close_gaps.py` run with the image's `python3` (`docker run --user root` with `/tmp`, `/home`, `~/.local` mounted, `FREEROUTING_JAR`, `FREEROUTING_JAVA`, `JAVA_TOOL_OPTIONS=` cleared). Routing takes ~12 min. |

**Cloud work lives only in the container until it is pushed.** Commit and push
to a `claude/*` branch before the session ends; `git push` is in `ask`, not
`deny`, so the owner approves each push.

## Konnect - editing through a running KiCad

`docs/decisions/0013`. A single binary at `D:	ools\konnect\konnect.exe`,
registered at **user scope** - `~/.claude.json` for Claude Code,
`~/.codex/config.toml` for Codex - so both find it in every project. The
project's `.mcp.json` declares **no** servers: naming it in both places is a
collision, and on 2026-09-14 it produced `CONNECTION_CLOSED` against a server
that was provably healthy (starts in 0.01 s, survives idle, answers
`initialize`). 226 tools in 21 toolsets, loaded on demand:
`list_toolboxes`, then `load_toolset` for `sch_wiring`, `sch_analysis`,
`sch_batch`, `sch_export`, `sch_components`. `unload_toolset` keeps context
small.

**Three preconditions, in order. Check them; do not assume them.**

1. KiCad's API server is on - `kicad_common.json` -> `api.enable_server: true`.
2. **The editor you need is open**, not just the project manager. The handlers
   live in `_eeschema.dll` and `_pcbnew.dll`; with only `kicad.exe` running you
   get `AS_UNHANDLED` on every request.
3. `KICAD_API_SOCKET` is set. It lives in the user-scope registration and is
   **not optional on Windows**: NNG makes an `ipc://` endpoint a named pipe,
   not a file, so auto-detection fails and a client can decide KiCad is not
   running and start editing the file underneath it. `.mcp.json` carries the
   same warning for anyone setting the project up elsewhere.

Confirm with `open_project`, which reports `ipc_available` and
`kicad_ui_running`, **before** any write.

Useful, verified on this schematic 2026-09-13:

```
get_pin_connections {schematic, reference, pin_number}   net + absolute x/y
export_netlist_summary {schematic}                       every pin, one call
list_schematic_wires {schematic}                          -> count: 0  (I-002)
connect_pins / batch_connect_pins                        wire by ref+pin
run_erc, generate_netlist, export_schematic_svg          the checks
set_visual_baseline / compare_visual_baseline            visual regression
```

The argument is `schematic`, not `path` - the error message names the field it
wanted, so read it rather than guessing.

**Opening KiCad creates `~*.lck` and `board_provenance.py --check` will refuse
while it is there. That is correct.** Do not close KiCad to get past it
(`AGENTS.md` rule 8).

**Konnect is not installed into `~/.claude`.** `konnect init` would add 6
skills, 2 agents and 4 hooks to the global config; only the MCP server is wired
up here. The hooks guard the IPC-versus-file-fallback case and are worth
revisiting.

## 24-channel board (`hardware/24ch/`) - pipeline and the order of work

Lessons from 2026-10-08, when routing took a whole day it should not have.
Read `hardware/24ch/README.md` for the commands; this is the *order* and why.

**Two phases. Know which one you are in.**

1. **Generative, until placement is frozen.** `gen/build.py` (schematic),
   `kicad-tool pcb sync`, `gen/place.py`, `gen/rules.py --route-prep`,
   `gen/fanout.py`. Each run rebuilds from the generator and wipes every hand
   edit. Any move of a part invalidates all tracks, so routing restarts from
   `output/fanned.kicad_pcb`. Do placement experiments here, not after routing.
2. **Incremental, once a routing result is kept.** Never run `place.py` again.
   Freerouting reads the tracks already on the board and routes only what is
   missing, so a second run *continues* (`route24.py --board <kept copy>`);
   lock the good tracks first so it does not rip them up. The last few
   connections in congested spots are finished by direct edits:
   **Konnect (`pcb_routing`, `pcb_export`) through a running KiCad first**,
   or a person in KiCad with the interactive router (push-and-shove) - an
   engineer closes 50-80 short connections in a few hours. Computer-use on the
   KiCad window is the last resort, after Konnect was tried.

**Before any long Freerouting run (each pass is 2-8 minutes):**

**Interactive finishing and locks (2026-10-09):** the handed-off board had
3,336 locked tracks/vias and 558 unlocked. KiCad's Shove router cannot move
locked surrounding copper. Locking a kept route is useful when protecting it
from an autorouter, but is not a permanent finishing setting: before a local
Shove operation, select and unlock the necessary neighbouring tracks/vias,
leave footprints and unrelated copper protected, then save and re-run DRC.
Do not interpret a blocked escape as proof that the board needs re-placement.

- Run `gen/padcheck.py`. Freerouting sees the DSN clearance (net class + the
  `--pad` margin). If that is larger than the gap between two pads *of the same
  part*, every such pad is "already a violation" and Freerouting never connects
  it. On 2026-10-08 the AD7124 LFCSP (0.25 mm between pads) against 0.20 +
  0.06 mm, and the relays (1.4 mm) against a 2.0 mm Contact class, left ~85
  connections that no number of passes could route. Fix: class clearance below
  the tightest in-part gap (Island/Default 0.15 mm, Contact 1.0 mm); the big
  clearances *to other classes* (3 mm island, 2 mm contacts) belong in
  `.kicad_dru` pair rules, and `route24.py --contact-rule` passes the contact
  one to the router as a `class_class` rule.
- Watch the unrouted count per pass in `output/freerouting*.log`. If it stops
  falling for ~5 passes, stop and find the cause; more passes, more threads or
  a longer run will not fix a rule or placement problem.
- Result of the 2026-10-09 variants (same board, 30 passes, KiCad DRC after import):
  router margin 25 um -> 395-488 clearance errors (Freerouting rounds below 0.15 mm);
  40 um plus the contact/chassis pair rules -> 10 errors, 25 unconnected. Those are
  now `route24.py` defaults. The router's own "unrouted" count (69) includes plane
  nets; only KiCad DRC's unconnected count matters.
- Prefer 2-3 variants in parallel (`--board output/var_x.kicad_pcb --tag x`,
  each with its own `var_x.kicad_pro` copy) over one long run.
- Long router runs cost no model usage. If you must stop (usage limit, owner
  away), **start the long run in the background first**, then stop.

**Finishing the last connections (2026-10-09), in this order:**
1. `gen/finish.py drc` then `finish.py stubs` (pad-to-via stubs the router dropped).
2. `route24.py --tag x --passes 2` on a **locked** board (`finish.py lock`): a short
   fill. Longer locked or unlocked runs did not help - Freerouting counted ~209
   "unrouted" against KiCad's 13 and gained one per 5-10 min pass.
3. `gen/maze.py` - a grid maze router (0.05 mm) with the real clearances (0.21 to
   pads/vias/power, 0.16 signal-to-signal, 2 mm contacts, 1.5 mm chassis), domain and
   barrier masks, via-to-plane endings for plane nets. `--skip NET` leaves a net for
   hand routing (it would have drawn a 40 mm decoupling loop).
4. `maze.py --ripup` -> `finish.py rip` -> `maze.py`: rips the few signal tracks in the
   way; the rip-up's target nets route first, else the ripped nets retake the corridor.
* Codex in the desktop app, asked to use KiCad's interactive router, wrote a script per
  connection on board copies instead: 4 of 7 correct, but >50 % of the owner's weekly
  limit. Prefer `maze.py`; give an agent the GUI only with a hard budget.

* **Driving the KiCad GUI (2026-10-09).** The computer-use MCP returned an all-dark screenshot on this
  machine every time, while a GDI capture worked: `gen/kicad_ui.ps1` (cap / crop / click / keys, DPI-aware,
  Windows scaling 125 % -> clicks are in the 1536x864 screenshot frame). Calibrate board mm to screen from
  the status bar `X Y`. Only with the owner away from the keyboard: keys go to the foreground window, and
  in pcbnew plain letters are hotkeys (a stray Ctrl+A selected 5683 items). The interactive router (X, Shove)
  could not leave a pad boxed in by another net's track - fix the blocker first.
* **One writer, also for scratch copies.** After a session restart an orphaned background loop kept writing
  `output/work.kicad_pcb` while a new one started - both runs were wasted. `tasklist | grep python` first.
* **When a general tool fails twice on one connection, stop and route it by hand coordinates**
  (`finish.py add NET LAYER W x1,y1 x2,y2 ... [via]`) after reading the blockers (`near.py`-style listing of
  tracks in a box). Rip-up loops around a dense LFCSP cascaded instead of converging.

**Looking at the board yourself:** `kicad-cli pcb export pdf` (or `sch export
pdf`) and render pages with PyMuPDF (`pip install pymupdf` into
`C:\Users\malgh\AppData\Local\Programs\Python\Python310`); `kicad-tool ...
render-region` needs `rsvg-convert`, which is not installed. Konnect's
`pcb_export` also writes SVG/PNG. Ask the owner for photos only of what is not
in the files (the LCD module bought locally, the enclosure, the panel).

**Schematic pages are A4 or A3 only** (owner, 2026-10-08): `build.py`
splits sheets and refuses anything bigger.

**Finishing the 24-ch board (2026-10-09)** - `gen/finish.py nori` pushes tracks off pads to the NORI
0.2 mm (re-run until DRC is clean; tracks pinned at both ends by hand), `finish.py dangling` deletes
router stubs, each checked by a DRC run on a copy (pcbnew cannot load a second board after a Remove:
board edits run in a child process). `maze.py` with `THERMO24_MAZE_IN2=1` may use In2.Cu. A work copy in
`output/` needs its own `.kicad_pro`/`.kicad_dru` next to it, or DRC uses default 0.2 mm classes.
`gen/silk.py` places labels by obstacle search (pads, Fab body outlines, other text; KiCad text boxes
include line spacing - use the glyph box); board min text height 0.8 mm. `gen/fab.py` runs DRC with
`--refill-zones --save-board` so the Gerbers carry the pours DRC checked (scripts save boards unfilled).
Render check: `kicad-cli pcb render --side top`.

## Things that will bite you

- **A gate that reads a file can pass on the wrong file.** Two did on
  2026-09-26: `close_gaps.py` read a `drc-report.rpt` from 2026-09-07 and said
  "no missing connections" on a board with one (it now runs its own DRC with
  `--refill-zones` and refuses an older report), and `check_mpn_consistency.py`
  read only the root after `I-062` - 56 symbols checked instead of 128, still
  "all match" (it now follows every `Sheetfile`). When a check's count drops,
  suspect the check.
- **`populate_schematic.py` (now in `_old/`) refused the hierarchical root**
  (`I-062`); `sch_layout/build.py` replaced it.

- **`PCB_VIA::GetWidth()` needs a layer argument** in KiCad 10. The no-argument
  form trips a wxWidgets assert that opens a modal dialog and hangs a headless
  run. `generate_board.py` disables wx asserts for this reason.
- **KiCad's SWIG bindings degrade after any `board.Remove()`** — every container
  accessor then returns bare pointers, for the rest of the process. Clearing is
  done in a child process (`generate_board.py --clear-only`).
- **Freerouting's multi-threaded optimiser is broken** by its own warning and
  generates clearance violations. Always `--threads 1` for a run you keep
  (on 2026-10-08 a single-thread 24-ch pass took 8 min against 2.5 min on 4
  threads; 4-thread runs are for comparing variants, and their result must pass
  KiCad DRC before it is kept).
- **Killing `route24.py` does not stop Freerouting.** The Java process keeps
  running (`taskkill /F /IM java.exe`), and Freerouting writes its `.ses` only
  at the end - a cancelled run leaves nothing to import.
- **Codex 0.162 alpha cannot run any command with the elevated Windows sandbox**
  (`helper_unknown_error: setup refresh had errors`; it then reviews blind). Run
  `codex exec -c 'windows.sandbox="unelevated"' -s read-only -o report.md - < brief.txt`.
- **`kicad-tool` on Windows needs `KICAD_CLI`** (its default is the macOS path;
  the error is a bare `[WinError 2]`) and `KICAD10_FOOTPRINT_DIR` for `pcb sync`.
- **Freerouting rounds clearances down** (0.2454 mm against a 0.25 mm rule), so
  `route.py` pads the values it writes into the DSN.
- **KiCad exports every copper layer as `(type signal)`.** `route.py` rewrites
  In1/In2 to `(type power)` so signals stay on the outer layers.
- **`kicad-tool` regenerates UUIDs on every write**, so a label UUID from an
  earlier query is stale after the first delete. Re-query each round.
- **Heredocs in this environment mangle backslashes.** Write patch scripts to a
  file instead of piping them inline.
