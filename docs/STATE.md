# Current state

**Read second, after `AGENTS.md`. Update before finishing. Hard limit: 60 lines.**

**Last updated:** 2026-09-13

## Last session

Every gate run end to end, to settle whether `I-036`..`I-042` were reported or
actually fixed. They were, and are closed against a passing run rather than a
reading of the diff. Doing so exposed three defects in the gates themselves
(`I-043`), the worst being `validate.ps1` reporting *"Sources unchanged"*
without having hashed anything. The PCB was not touched; REV A0 stays frozen
(`docs/decisions/0010`).

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

`run_all.ps1 -Regenerate` was NOT run: it rewrites the frozen board. No Gerber
release, SPICE, thermal or physical measurement; Proteus not executed.

## Next actions

1. **`I-002`** - redraw the schematic; tooling is ready (`0013`), one sheet.
2. **`I-044`** - regenerate-then-compare; `board_provenance.py` covers half.
3. Owner decisions: **`I-028`** 24 V source, **`I-025`** layer sourcing.
4. Bench once a board exists: `I-004`, `I-003`, `I-013`; REV A1 layout `I-045`.

## Tooling 2026-09-13, and one correction

**One KiCad MCP now: Konnect** (`0013`). It talks IPC to a running KiCad 10, so
edits go through KiCad and land in its undo stack, and it reads and writes
S-expressions itself when KiCad is closed - which is why the Seeed server was
retired on 2026-09-14 with nothing left of its own. Wired for Codex too.
**`I-002`'s tooling blocker is gone**: pin coordinates and nets come from one
call, verified on this schematic. `KICAD_API_SOCKET` must stay set or a client
edits files under an open KiCad (#529, reproduced here). The scripts in
`hardware/8ch/` are **not** replaced - they hold this board's own rules. Licence
open `I-046`; first `emc` run `I-045`; `spice` blocked, no simulator.

## Preserve for I-002 and hardware work

A hierarchical redraw was attempted and reverted: symbols lacked KiCad instance
data, so the netlist exported **zero components** while the seven sheets looked
correct. The agent ran out of quota mid-run and left half-written files, which a
`git add -A` swept into a commit. Verify every step with
`netlist_fingerprint.py`; never alter the baseline to make it pass.
`prune_dangling_labels()` assumes labels sit on pins - account for wired ones.
