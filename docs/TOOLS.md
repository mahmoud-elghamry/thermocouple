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
