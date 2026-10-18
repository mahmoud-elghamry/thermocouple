# Shared family circuit library - state

**Last updated:** 2026-10-14 (Claude). Plan: `docs/decisions/0039`. **Hard limit: 60 lines.**

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

## After the 24-ch REV A4 merge (2026-10-19)

* `gen/test_family.py::test_24_model_identical_to_original` and `tools/test_profiles.py::test_profile24_source_constants`
  fail: the family config/profile "24" still describes REV A3, the 24-ch generator is now REV A4 (`0041` gated
  SIO driver U411, `0042` door LCD). Bring config 24 / profile 24 up to REV A4 (or re-point the tests) before the
  family tools are used on the 24-ch again. I-129 and I-130 still apply to REV A4 (checked after the merge).
