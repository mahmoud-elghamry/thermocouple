# Current state

**Read second, after `AGENTS.md`. Update before finishing. Hard limit: 60 lines.**

**Last updated:** 2026-09-24

## Last session

**The supply is an engine battery** (owner), so `I-028` is resolved in the
schematic: `TSR 1-2450` (36 V) -> **`LM5164` (6-100 V, 1 A)**, `D1` 40 -> 100 V,
`D2` 33 -> 60 V standoff, `C53`/`C54` -> 100 V. A suppressed load dump is 58 V
for ~350 ms. **~$5/unit CHEAPER than the module it replaces**, and a better
cranking floor. `0016`; every number is now in `reference/CALCULATIONS.md`.

**REV A1 and the BOM are done** (`0014`, `I-051`, `I-053`); the terminal blocks'
`1935161` was a two-way part on a three-way footprint. **Board NOT regenerated.**

## Measured, not claimed

| Check | Result |
|---|---|
| `firmware/build.ps1` | **exit 0**; 4 images, 3 suites `all checks passed` |
| Real 8ch image | 5592 B flash (17.1 %), was 5556 B - the read-back is now live |
| Netlist | **201** components, **162** nets, **645** pins (was 188/155/613) |
| Fingerprint | 28 differences, **every one inspected**; new nets checked pin by pin vs TI SNVSAU4D |
| ERC | **0 errors, 0 warnings** |
| DRC | **not run** - the board is untouched and now lags the schematic |
| BOM | 86 lines, **201 parts**; the only 9 without an MPN are the test points |
| `check_mpn_consistency.py` | **128 checked, all match** - it found 12 wrong first |

The board is **34 components behind** the schematic. No Gerber release, SPICE,
thermal, EMC or physical measurement; Proteus not executed.

## Next actions

1. **`I-002` wires** - still **0 wires**, the last schematic job (`I-047`,
   `I-050`). A wire along a signal row through a decoupling cap's ground pin
   shorts the net - that is how channel 1 put `TC1_FILT_P/N` on `GND_SENS`.
2. **Regenerate the board** - authorized; it lags by 34 components.
3. `I-028` tail: **`F1` is not adequate on a battery** (PTC breaks ~40 A, a
   battery pushes thousands) - external panel fuse. Then `emc`, bench `I-004`.
4. **Ask the owner** which `I-056` doc-system fixes to do; nothing started.

## Tooling, and the traps it sets

`Konnect` is the only KiCad MCP (`0013`). Cloud sessions: `session-start.sh`
installs it + toolchain (TOOLS.md, "Cloud"), verified in a real container;
there `validate.ps1` stops on `I-057`, netlist IDENTICAL, `make` passes. **`kicad-tool` clones a symbol to
make a new one, so the clone inherits its MPN** (`I-054`); run
`check_mpn_consistency.py` after any run that adds parts. The generator's
coordinates are **284 mm left of the sheet** (`I-055`).

## Preserve for I-002 and hardware work

A hierarchical redraw was attempted and reverted: symbols lacked KiCad instance
data, so the netlist exported **zero components**. Verify every step with
`netlist_fingerprint.py`; never alter the baseline to make it pass.
`prune_dangling_labels()` would have deleted the new wiring on the next
`run_all.ps1` (guarded, `I-047`), and it does not remove a stale label resting
**on** another pin - `I-049`, `I-050`.
