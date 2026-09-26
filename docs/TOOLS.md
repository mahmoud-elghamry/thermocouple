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
| Konnect | `D:	ools\konnect\konnect.exe` | the KiCad MCP - 226 tools; IPC when KiCad is open, S-expressions when it is closed |

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

python populate_schematic.py                 # add --labels-only to skip symbol work
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

### After any generator run that ADDED parts

```powershell
python hardware\8ch\check_mpn_consistency.py          # --fix rewrites mismatches
```

`kicad-tool` creates a new symbol by cloning an existing one of the same type,
and the clone brings the donor's `MPN`/`Manufacturer`/`LCSC` with it. On
2026-09-16 that gave six new capacitors a **100 nF** part number and six new
resistors a **10 k** one. ERC passed, the netlist fingerprint passed - neither
looks at MPN. Run this whenever `populate_schematic.py` reports new symbols.
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
the sources: `production/8ch/` is the REV A0 package that was fabricated -
**never overwrite it** - and `production/8ch-reva1/` is REV A1 (2026-09-26,
with `RELEASE.txt` and the upload zip). `production/` is gitignored.

**Name the layers.** Without `--layers`, KiCad 10 plots every layer - Fab,
Courtyard, User.1-4 - and a fab may read them as copper or silk.

```powershell
$out = '..\..\production\8ch-reva1'
New-Item -ItemType Directory -Path $out | Out-Null     # fails if it exists: new revision, new folder
& $cli pcb export gerbers --check-zones --layers 'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts' --output "$out\" thermocouple_8ch.kicad_pcb
& $cli pcb export drill   --output "$out\" --format excellon --excellon-units mm --generate-map --map-format gerberx2 thermocouple_8ch.kicad_pcb
& $cli pcb export ipcd356 --output "$out\thermocouple_8ch.d356" thermocouple_8ch.kicad_pcb
& $cli pcb export pos     --output "$out\cpl.csv" --format csv --units mm --side both thermocouple_8ch.kicad_pcb
& $cli sch export bom     --output "$out/bom.csv" --fields 'Reference,Value,Footprint,MPN,Manufacturer,LCSC,${QUANTITY}' --group-by 'Value,MPN,LCSC' thermocouple_8ch.kicad_sch
```

Copy `docs/STATE.md`'s check numbers into the release folder as well. A
fabrication package without the report it passed is not a package.

## Schematic layout (`I-002`) - `hardware/8ch/sch_layout/`

```sh
python hardware/8ch/sch_layout/build.py              # scratch copy, prints the gate
python hardware/8ch/sch_layout/build.py --in-place   # rewrite the schematic
```

Measured 2026-09-24 in the cloud: about a minute; netlist IDENTICAL, ERC 0/0,
output equal to the committed sheet apart from UUIDs. Every write goes through
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

## Things that will bite you

- **`PCB_VIA::GetWidth()` needs a layer argument** in KiCad 10. The no-argument
  form trips a wxWidgets assert that opens a modal dialog and hangs a headless
  run. `generate_board.py` disables wx asserts for this reason.
- **KiCad's SWIG bindings degrade after any `board.Remove()`** — every container
  accessor then returns bare pointers, for the rest of the process. Clearing is
  done in a child process (`generate_board.py --clear-only`).
- **Freerouting's multi-threaded optimiser is broken** by its own warning and
  generates clearance violations. Always `--threads 1`.
- **Freerouting rounds clearances down** (0.2454 mm against a 0.25 mm rule), so
  `route.py` pads the values it writes into the DSN.
- **KiCad exports every copper layer as `(type signal)`.** `route.py` rewrites
  In1/In2 to `(type power)` so signals stay on the outer layers.
- **`kicad-tool` regenerates UUIDs on every write**, so a label UUID from an
  earlier query is stale after the first delete. Re-query each round.
- **Heredocs in this environment mangle backslashes.** Write patch scripts to a
  file instead of piping them inline.
