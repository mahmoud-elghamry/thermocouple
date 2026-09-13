# Current state

**Read second, after `AGENTS.md`. Update before finishing. Hard limit: 60 lines.**

**Last updated:** 2026-09-07

## Last session

Ran every gate end to end for the first time, to settle whether the review
findings `I-036`..`I-042` were reported or actually fixed. They were fixed, and
are closed against a passing run rather than a reading of the diff. The PCB was
not touched; REV A0 stays frozen (`docs/decisions/0010`).

Exercising the gates exposed three defects in the gates themselves, fixed and
recorded as `I-043` - the worst being `validate.ps1` reporting *"Sources
unchanged"* without having hashed anything.

## Measured, not claimed

| Check | Result |
|---|---|
| `firmware/build.ps1` | **exit 0**; 4 images, `-Werror` |
| Host suites | `test_app_logic`, `test_app_integration`, `test_bank_driver` - all checks passed |
| Real 8ch image | 5556 B flash (17.0 %), 6 B EEPROM |
| `sources/check_lists.py` | 10 lists / 19 C files, all accounted for; wired into build, Makefile and CI |
| `hardware/8ch/test_gates.ps1` | **exit 0**; 8 injected failures all rejected |
| `hardware/8ch/validate.ps1` | **exit 0**; snapshot only, 4 source hashes recorded |
| Netlist vs REV A0 baseline | **IDENTICAL** - 167 components / 154 nets / 555 pins |
| ERC | **0 errors**, 171 `endpoint_off_grid` warnings (all from `I-002`) |
| DRC | **0 errors**, 9 warnings, 0 unconnected, 0 parity |

`run_all.ps1 -Regenerate` was NOT run: it rewrites the frozen board. No
Gerber release, EMC, SPICE, thermal or physical measurement was performed, and
Proteus was not executed.

## Next actions

1. **`I-002`** - redraw the schematic. Roughly 70 % of the remaining work.
2. **`I-044`** - a regenerate-then-compare step, so generator/schematic drift
   stops being invisible. `board_provenance.py` covers half of this now.
3. Owner decisions: **`I-028`** 24 V source, **`I-025`** layer sourcing.
4. Bench, once a board exists: `I-004`, `I-003`, `I-013`.

## Tooling added 2026-09-13

KiCad MCP (`Seeed-Studio/kicad-mcp-server`), wired into `.mcp.json` and
`~/.codex/config.toml`; its ~40 analysis tools replace the hand-written parsers
that got connectivity wrong twice. `board_provenance.py` refuses a generator
run that would destroy hand edits, or while KiCad holds the project open.
Rules 8 and 9 now cover both modes - `docs/decisions/0012`, `docs/TOOLS.md`.

## Preserve for I-002 and hardware work

A hierarchical redraw was attempted and reverted: the symbols lacked KiCad
instance data, so the netlist exported **zero components** while the seven
sheets looked correct. The agent ran out of quota mid-run and left half-written
files, which a `git add -A` swept into a commit. Verify every step with
`netlist_fingerprint.py`; never alter the baseline to make it pass.
`prune_dangling_labels()` assumes labels sit on pins - account for wired ones.
