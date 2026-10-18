# Family board tools

Copies of the ordered board's `hardware/24ch/gen/` tools. No circuit generators,
`place.py` or `rules.py` are included. Donor source files remain untouched.

Every entry accepts `--board 24|8|40` (default: `THERMO_BOARD`, otherwise 24)
and `--pcb <path>`. Common options are removed before the existing positional
parser runs. Selection and copy path survive child processes. `THERMO24_BOARD`,
`THERMO24_MAZE_IN2`, `THERMO24_WRITER_CLAIM`, and the FAB_PCB/FAB_SCH/FAB_OUT
overrides still work; use the corresponding THERMO8/THERMO40 prefix on those
profiles. `route24.py --board` now selects a profile; its old copy-path argument
is `--pcb`. `pincaps.py [board]` and `guard.py [board]` remain compatible.

`--pcb` selects adjacent `.kicad_pro`, `.kicad_dru`, `.xml`, `accessories.csv`
and `output/`; copy the sidecars and schematic set with the PCB. The family
guard refuses a write to the ordered `hardware/24ch/thermo24.kicad_pcb`, even
with `--force`. Fabrication reads that source and writes only a release snapshot.

`profiles.py` is the only profile module. It holds project/folder, width/height,
outline/mounting coordinates and types, ADC refs/banks/reference bases/channel counts, RTD
ref, plane/contact/chassis/high-clearance/protected nets, class and router
pair rules, pin-cap checks and buck/bootstrap identity, fiducial targets,
silk geometry/functions/revision, bias/island zone naming, board-only prefixes,
release prefix, assembly instructions/test points/orientation and output stems.
8 uses the confirmed 130 x 125 mm floor plan, mounting coordinates/types and REV B0.
40 uses bank bases 100/200/300/800/900, RTD U1001, decoder U410 and SIO U411;
its size remains **None**, not the approximate planning dimensions. All
unconfirmed per-board fields are None with a `set by floor plan` comment;
`require()` stops rather than generating guessed geometry or assembly guidance.

`fanout`, `maze`, and `capnear` import only `domain` and `BANDS` from the
selected board's own `gen/rules.py`, without executing its main writer. An
absent floor plan is an explicit failure. The helper modules split the copied
algorithms into files below 300 lines; they share their entry module's context.

## Regression hand-off

The implementer **must not run KiCad** in the sandbox. Claude runs:

```powershell
pwsh -NoProfile -File D:\tasks\thermo-branches\family-tools\hardware\family\tools\regress.ps1
```

The launcher pins KiCad 10 CLI/Python and the installed Python310/PyMuPDF renderer paths, disables bytecode and
Windows crash dialogs for child processes, and invokes a plain Python harness.
Use `-Python <system-python-with-PyMuPDF>` to override the default Python310;
`view.py` retains the donor's absolute Python310 renderer path.
Success means **exit 0** and `REGRESS: N passed, 0 failed`. A missing dependency,
tool crash, comparison difference or changed donor file fails
the gate; the other independent groups continue. A matching ordinary nonzero exit,
exact stdout and byte-identical resulting PCB reports `PASS (same failure as original)`.
Timeouts and crashes cannot pass this exception. No Java/Freerouting or full
maze routing runs are performed.

All artifacts go under `hardware/family/tools-test/regress-<time>/`: exact
donor scripts copied there (including rules solely as an unmodified fixture),
source board/project/rules/schematics/lib, stdout/stderr, command/exit JSON,
raw hashes, release files and summary.json. Both read-only invocations use
the same board copy; writing invocations get fresh identical A/B copies.
The gate hashes the entire donor folder before and after, including file sets.

Command pairs are printed as `CMD ...` and retained in `.command.json`:

| Tool | Pair / comparison |
|---|---|
| padcheck, pincaps, guard | donor copy vs family `--board 24 --pcb A`, exact stdout/exit |
| capnear | both `U403 1 C407 --step 0.5 --show 5`, same copy, exact stdout/exit |
| delta | both `--dry`, same exported XML; also write on A/B |
| cost | both `[5]` with identical offline price fixture injected by worker; stdout/CSV |
| maze, route24, fanout | import constants; route CLI pair-rule branches exercised with exporter/Java/import stubbed |
| silk, fiducials, vbias_pour, fanout | original A vs selected family B; PCB SHA or canonical geometry |
| move | both `C407 68.2 90.0 90`; PCB comparison |
| pcb_new | both `--force` on scratch A/B; PCB comparison |
| finish | drc, lock, unlock, unlock-box, strip, dedupe, stubs, nori, dangling, rip, add |
| fab | FAB_* on A/B into separate scratch roots; every output compared |
| assembly_spec | matching releases and scratch PCBs; PDF text/render comparison |
| view | both `0 0 40 30 <scratch>/view.png`; PNG SHA |

Cost fixtures test calculations, not live stock/prices. `nori` receives an
empty fresh violation fixture and `rip` an empty UUID list, so those checks
prove no-op preservation; `stubs`, `dangling`, `dedupe` run actual DRC.
Raw SHA256 is always retained. PCB normalisation drops UUID fields and sorts
unordered object collections, keeping coordinates, nets, clearances, polygon
vertex order and all other fields. Gerber/drill/XML normalisation removes only
creation times and scratch paths. ZIP members are compared independently.
PDFs (including ZIP members) compare normalised text plus rendered pixels with printed release/path
lines masked; those lines' invariant text is still checked. Manifests' time,
paths and file hashes vary; all referenced output files are compared separately.
Gerber/drill date-comment normalisation retains KiCad version and every drawing/drill command;
CRLF is normalised before ZIP member comparisons. The manifest's source-board path is metadata.

## Corrections after the 2026-10-14 external run

Evidence: `tools-test/regress-20261014-105012-053905/summary.json` (28 passed, 5 failed).
Donor silk's stripping child claims the parent's lock; donor fiducials enumerates
footprints after Remove invalidates SWIG objects. Both exited 1 with identical
stdout and unchanged PCB hashes. The family copies now strip in a child under
a live parent claim, checked by parent PID, tool, board and KiCad locks, and reload
before enumeration. The gate still invokes the unmodified donor first; when the
documented donor failure becomes family success, it runs a **repaired reference**:
only the two deletion/child-launch corrections are applied to donor functions in
memory, with the same parent-claim validation. It requires matching output and
PCB geometry against that reference. This is labelled as a family bug fix, not
as identical behaviour to the donor's failing CLI. No donor file is edited.

`finish dangling` had original exit 0 (18 removals, 12 retained) but family timeout
at 600 seconds during candidate DRCs, before any final save. Its algorithm AST is
unchanged. Both dangling invocations now get a 3600-second budget; comparisons
remain strict. Timeout logs retain partial stdout and elapsed time, and stop the
harness-owned process tree rather than leaving DRC children running.

Fab's snapshots/BOM/CPL already matched. Only Gerber/drill comment times, source
path metadata, and missing PyMuPDF comparison dependencies caused failures.
With the corrected comparator and installed Python310, all **45 existing fab
output files** compare successfully. Assembly generation failed in the donor
before entering its code (`ModuleNotFoundError: No module named 'fitz'`); the
launcher now uses the verified renderer interpreter. The newly repaired KiCad
steps and assembly generation still require Claude's external rerun.

## Floor-plan work left outside this package

**rules.py per board:** PCB/project/DRU paths; island/control/RS485 domain
polygons and barrier bands; domain priority and U401 pin-domain exception;
plane-to-layer nets, zone names/priorities; class names/net assignments and
track/clearance/via/drill limits; project manufacturing minima; pair rules;
B0505 courtyard exception; K701/K702 contact/unused-pad exceptions (including
the literal unconnected net); chassis bridge C610/R607 exemptions; U601 EP9
thermal-via coordinates, paste-window locations/net; keepout layers/geometry.
These must agree with the profile's nets/classes and clearances. No imported
24-ch geometry is used as a fallback for another board.

**place.py per board:** project/board/netlist paths and envelope checks;
connector pitch/orientations; channel-column topology/reference numbering;
horizontal/vertical bank count, anchor positions, ADC decoupling regions and
CJ refs/positions; island support packing and isolator barrier crossings;
RS485 pocket, relay/power/MCU placement; LCD footprint/headers/keypad/LEDs;
mounting/standoff types and positions; packing gaps, regions and failure staging
position. The existing placement describes older component choices and is
not an approved floor plan for 8/40 or for rebuilding the ordered board.

Ignore paths for Claude to add: `hardware/family/tools-test/` and
`hardware/family/tools/__pycache__/`. No .gitignore was written here.
