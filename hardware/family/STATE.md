# Shared family circuit library - state

**Last updated:** 2026-10-19 (Codex). Plan: `docs/decisions/0039`. **Hard limit: 60 lines.**

## What is here

* `gen/` - circuit generator shared by the family (written by Codex Sol in worktree `family-lib`,
  reviewed and extended by Claude): `boards.py` holds the configs 24 / 8 / 40; blocks `c_bank`, `c_iso`
  (isolators, SIO driver, decoder), `c_mcu`, `c_out`, `c_power`, `c_rtd` (PT100 bank, 40-ch only).
* `python gen/build.py 24|8|40 [--out DIR]` -> schematic, ERC, netlist self-check, BOM (default `out/<board>/`).
* `gen/compare_release.py` - independent compare of an exported netlist + BOM with a release folder.
* `gen/gate.ps1` - every gate in one run (Windows PowerShell: `powershell -ExecutionPolicy Bypass -File`).
* `tools/` - the 24-ch board tools parameterised by `tools/profiles.py` (`--board 24|8|40`, `--pcb <copy>`), Sol,
  worktree `family-tools`. `tools/regress.ps1` (run by Claude 2026-10-14): **33 passed, 0 failed**, 24-ch files
  byte-identical; silk/fiducials child-process bugs fixed in the family copies only (I-127).

## Verified (KiCad 10, run by Claude 2026-10-14)

* `gate.ps1`: FAMILY GATES: PASS. Config 24 vs release `24ch-reva3-20261014-072946-4b1601`:
  463/463 components, 266/266 net names, 95/95 BOM lines, **0 differences**; ERC 0 errors 0 warnings;
  fault injection 3/3 detected (changed value, swapped pin, removed part); `hardware/24ch/` byte-identical.
* Config 8: ERC 0/0, netlist 0 mismatches, 92 BOM lines, 243 fitted parts (SYNC tied, H4 plain).
* Config 40: ERC 0/0, netlist 0 mismatches, 108 BOM lines, 707 fitted parts (3 PT100 + check resistor, SYNC tied).
* `python -B gen/test_family.py`: 7 tests OK.

## Open

* Cost: `gen/cost.py` has no offline price cache; parts cost not yet computed for 8 / 40.
* Generated output (`out/`) is ignored; the boards' own folders take a copy when their layout starts.

## REV A4 family regression sync (2026-10-19, plain Python only)

* Config 24 matches the read-only 24-ch REV A4 model exactly, including every part field/description (`0041`):
  gated U411, PD5 -> U405 channel C, R439 pull-up, D501/D502 ESC diodes. New `sio_a4` / `esc_diodes` options
  are enabled only for B24; B8/B40 explicitly disable both. Revision/title now A4.
* Profile 24: U411 supply-pin check matches the source; driver ref, revision, release prefix and silk updated.
  Updated A3-specific subset/count expectations and the HTML golden check's revision only; donor comparison retained.
* Gates: `python -m unittest test_family`: **8 tests OK** (24: 470 components, 96 BOM lines, 449 fitted);
  `python -m unittest test_profiles test_docs_new`: **13 tests OK**. Python 3.11.15 used because `py -3`
  reports no installed Python. No KiCad/kicad-cli/pcbnew execution; no ERC/DRC or release-generation claim.
* Before/after dumps: `out/a4-proof/{before,after}/`, reproducible via `out/a4-proof/snapshot.py`;
  models B8/B40, full sheets (including RTD), root parts and profiles 8/8l/40 are **byte-identical (9/9)**.
  Identity hashes/report: `out/a4-proof/identity.txt`. Board folders and docs unchanged. No commit.
* I-129 and I-130 still apply to REV A4; this sync implements the existing decision, not a board revision.
