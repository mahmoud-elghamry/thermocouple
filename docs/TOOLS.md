# Tools and commands

Only commands that have actually been run in this repository. If one stops
working, fix it here rather than working around it in a session.

---

## Installed

| Tool | Where | Used for |
|---|---|---|
| KiCad 10.0.3 | `C:\Program Files\KiCad\10.0` | everything hardware |
| KiCad Python (`pcbnew`) | `…\10.0\bin\python.exe` | the board generator and router scripts |
| `kicad-cli` | `…\10.0\bin\kicad-cli.exe` | ERC, DRC, netlist, BOM, Gerbers, 3D render |
| `kicad-tool` | `%LOCALAPPDATA%\Temp\thermo-kicad-tool-venv\Scripts` | schematic edits, schematic↔board sync |
| Freerouting 2.4.1 | `%LOCALAPPDATA%\kicad-tools\freerouting.jar` | autorouting via Specctra DSN/SES |
| Temurin JRE 25 | `%LOCALAPPDATA%\kicad-tools\jre25\*\bin\java.exe` | runs Freerouting |
| avr-gcc | see `firmware/build.ps1` | firmware |
| KiCad MCP | `D:\tools\kicad-mcp-server` | 47 tools for reading, analysing and validating the board without hand-rolled parsers |

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

## Hardware — regeneration (frozen on REV A0)

The explicit `run_all.ps1 -Regenerate` path checks every native exit and report,
and refuses while KiCad editors are open. It is **not authorized during the
owner's REV A0 freeze**. The source-preserving default was tested this session;
regeneration was deliberately not run. The historical individual commands below
remain useful after an approved revision change, from `hardware/8ch/`:

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

A release goes to `production/8ch/`, not next to the sources. That folder is
gitignored, so nothing there can be mistaken for a source file.

```powershell
$out = '..\..\production\8ch'
New-Item -ItemType Directory -Force -Path $out | Out-Null
& $cli pcb export gerbers --output "$out\" thermocouple_8ch.kicad_pcb
& $cli pcb export drill   --output "$out\" --format excellon --excellon-units mm --generate-map thermocouple_8ch.kicad_pcb
& $cli pcb export pos     --output "$out\cpl.csv" --format csv --units mm --side both thermocouple_8ch.kicad_pcb
& $cli sch export bom     --output "$outom.csv" --fields 'Reference,Value,Footprint,Description,Datasheet,QUANTITY' --group-by 'Value,Footprint,Description' thermocouple_8ch.kicad_sch
```

Copy `docs/STATE.md`'s check numbers into the release folder as well. A
fabrication package without the report it passed is not a package.

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

## KiCad MCP

Configured in `.mcp.json` (Claude Code) and `~/.codex/config.toml` (Codex), so
any agent on this project picks it up. Runs under KiCad's own Python, so
`pcbnew` imports and the numbers are real rather than text-parsed.

**Use the analysis tools freely.** `get_pcb_statistics`, `list_pcb_footprints`,
`analyze_pcb_nets`, `trace_netlist_connection`, `find_tracks_by_net`,
`list_schematic_components`, `run_erc`, `run_drc`, `get_*_violations`,
`export_*`. They read; nothing they do can be lost.

Hand-written regex parsers over `.kicad_pcb` and `.net` got connectivity wrong
twice on 2026-09-07 - once nearly reporting `RUN_PERMIT` as unconnected when it
is connected through `R30`. `trace_netlist_connection` is the tool for that
question.

**The seven write tools** - `add_wire`, `add_label`, `add_global_label`,
`add_hierarchical_label`, `add_component_from_library`, `setup_pcb_layout`,
`create_kicad_project` - edit files directly, which counts as a hand edit. They
are permitted in incremental mode only, after `board_provenance.py --check`
passes, and `netlist_fingerprint.py` afterwards if the edit could have touched
connectivity.

Verified 2026-09-13 against the real board: 250.10 x 140.10 mm, 4 layers,
174 footprints, 1044 track segments, 125 vias, 15 zones, 155 nets - matching
the figures measured by hand.

**A second KiCad MCP was evaluated and rejected.** The IPC-API servers
(`Finerestaurant/kicad-mcp-python` and similar) use KiCad's official API, which
is architecturally nicer, but on KiCad 9 and 10 that API cannot plot or export -
support lands in KiCad 11. It could edit the board and then not run the checks
that prove the edit safe. It also needs KiCad open, making the two-writer
hazard permanent. Revisit at KiCad 11.

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
