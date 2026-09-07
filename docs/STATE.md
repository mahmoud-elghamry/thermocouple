# Current state

**Read second, after `AGENTS.md`. Update before finishing. Hard limit: 60 lines.**

**Last updated:** 2026-09-07

## Last session

Architecture and implementation review requested by the user. No product code,
schematic or PCB changed; REV A0 remains frozen (`docs/decisions/0010`).
Actual application/driver sources were exercised with host peripheral doubles.
New findings are `I-036` through `I-042` in `docs/ISSUES.md`.

The MAX31856 bank driver, EEPROM CRC/read-back and config lock ARE implemented.
However, failed saves leave edited limits active (`I-036`), first-time setup
hides the limit (`I-037`), and post-init MISO LOW passes as valid 0 C until the
stuck monitor trips on bad scan 121 in the reproduced 20 C case (`I-038`).
The existing tests pass but do not cover these integration paths (`I-042`).
Proteus still loads an obsolete HEX filename (`I-041`).

## Evidence from this session

Artifacts: `production/analysis-20260907/` (ignored, regenerate locally).

| Check | Result / basis |
|---|---|
| Firmware build | 4 images, `-Werror`; existing host suite: all checks passed |
| Real 8ch image | 5230 B flash, 376 B static RAM (excludes stack), 6 B EEPROM |
| Source lists | 8 lists / 19 C files accounted for; checked manually |
| New host reproductions | I-036/I-037 application loop; I-038 bank + monitor |
| Fresh netlist vs A0 | IDENTICAL: 167 components / 154 nets / 555 connected pins |
| Fresh ERC | 0 errors / 171 endpoint_off_grid warnings; wrapper exit 5 |
| Schematic wires | 0, queried through kicad-tool |
| Last saved DRC | 2026-09-07 01:40:45: 0 errors, 9 warnings, 0 unconnected/parity |

The DRC row is historical, not rerun this session. Full `run_all.ps1` was NOT
run because it regenerates the frozen board. No fresh manufacturing release,
EMC, SPICE, thermal, Gerber or physical/datasheet pin audit was performed.
No hardware measurement or Proteus execution was performed.

## Next actions

1. Fix I-036/I-037/I-038 with maintained application/driver regression tests.
2. Add explicit pipeline exit gates and wire in source-list checks (I-039/I-042).
3. Repair Proteus image binding (I-041); reconcile stale live docs (I-040).
4. Resolve I-035 capacitor specification/catalog mismatch before ordering.
5. Confirm 24 V source (I-028) and layer sourcing (I-025) with the owner.
6. Redraw schematic I-002 without connectivity changes; retain A0 contract.
7. Measure isolation, isolated supply and trip time (I-004/I-003/I-013).

## Preserve for I-002 and hardware work

Previous hierarchical redraw was reverted: missing KiCad instance data exported
zero components. Use kicad-tool, move symbols to the 1.27 mm grid, and verify
each step with `netlist_fingerprint.py`; never alter the baseline to pass.
`prune_dangling_labels()` assumes labels sit on pins; account for wired labels.
No board regeneration without revisiting the owner's A0 freeze. Only one
hardware writer, and close KiCad before a permitted board write. Hand routing
is erased by the generator; durable layout fixes belong in `board/` or `route.py`.
