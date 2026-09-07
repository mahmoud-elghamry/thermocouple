# Current state

**Read second, after `AGENTS.md`. Update before finishing. Hard limit: 60 lines.**

**Last updated:** 2026-09-07

## Last session

Ran every gate end to end for the first time, to settle whether the review
findings `I-036`..`I-042` were reported or actually fixed. They were fixed:
all five are now closed against a passing run, not against a reading of the
diff. No product code, schematic or PCB changed; REV A0 stays frozen
(`docs/decisions/0010`).

Exercising the gates exposed three defects in the gates themselves, all fixed
and recorded as `I-043`. The worst: `validate.ps1` printed *"Sources
unchanged"* **without hashing anything**, because PowerShell 5.1 will not bind
pipeline strings to `Get-FileHash`, so it compared two empty sets. A gate that
claims a check it never ran is worse than one that fails.

## Measured, not claimed

Every row below is from a command run this session.

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

1. **`I-035`** - the board cannot be ordered as specified: 100 nF C0G does not
   exist in 0805. Needs the owner's yes, then the `Value` text corrected.
2. **`I-002`** - redraw the schematic. Roughly 70 % of the remaining work.
3. **`I-041`** Proteus HEX binding, **`I-040`** stale `hardware/8ch/README.md`.
4. Close `I-005` (accepted in `0004`) and `I-008` (part never adopted).
5. Owner decisions: **`I-028`** 24 V source, **`I-025`** layer sourcing.
6. Bench, once a board exists: `I-004`, `I-003`, `I-013`.

## Preserve for I-002 and hardware work

A hierarchical redraw was attempted and reverted: the symbols lacked KiCad
instance data, so the exported netlist held **zero components** while the seven
sheets looked correct. The agent ran out of quota mid-run and left half-written
files, which a `git add -A` swept into a commit. Verify every step with
`netlist_fingerprint.py`; never alter the baseline to make it pass.
`prune_dangling_labels()` assumes labels sit on pins - account for wired ones.
One hardware writer at a time, close KiCad first, and no regeneration without
revisiting the A0 freeze. Hand routing is erased: fixes go in `board/`.
