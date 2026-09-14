# Current state

**Read second, after `AGENTS.md`. Update before finishing. Hard limit: 60 lines.**

**Last updated:** 2026-09-15

## Last session

**REV A0 unfrozen; the REV A1 set is in the schematic and firmware** (`0014`).
All but `I-028`; `I-025` stays four-layer. 21 parts: `Y1`+`C60`/`C61` crystal
(`I-032`), `R53`/`R54` read-back (`I-016`), `D7`-`D22` BAV199 protection
(`I-045`). One number to know: a 3.3 V TVS there injects up to **9.8 degC of
error** through 2 uA leakage; BAV199 leaks 3 pA.

**The board has NOT been regenerated.** That is next, and it re-routes all.

`I-002` moved a long way: A4 -> A2 (**`U1` hung 14.8 mm off the page**), control
section +284 mm clear of the channels, **ERC 192 warnings -> 0/0**, overlaps
122 -> 57, netlist IDENTICAL. Still 0 wires - that part remains.

## Measured, not claimed

| Check | Result |
|---|---|
| `firmware/build.ps1` | **exit 0**; 4 images, 3 suites `all checks passed` |
| Real 8ch image | 5592 B flash (17.1 %), was 5556 B - the read-back is now live |
| Netlist | 167 -> **188** components, 154 -> **155** nets, 555 -> **613** pins |
| Fingerprint vs REV A0 | 48 differences, **every one intended**, no net lost a pin |
| Fingerprint vs REV A1 | **IDENTICAL** - `netlist-baseline-reva1.json` is the gate now |
| ERC | **0 errors**, 192 `endpoint_off_grid` and nothing else (all `I-002`) |
| DRC | **not run** - the board is untouched and now lags the schematic |

The board is **behind** the schematic by 21 components. No Gerber release,
SPICE, thermal or physical measurement; Proteus not executed.

## Next actions

1. **`I-002` wires** - the last part. Move symbols BEFORE wiring (`I-047`), in
   exact 1.27 mm multiples (`I-050`); gate on `netlist-baseline-reva1.json`.
2. **Regenerate the board** - `run_all.ps1 -Regenerate`, now authorized.
3. Owner decision **`I-028`**; bench once a board exists: `I-004`, `I-003`, `I-013`.

## Tooling, and two traps it set

`Konnect` is the only KiCad MCP (`0013`), registered at user scope only - naming
it in `.mcp.json` too was a collision that broke it. **`kicad-tool` was in
`%TEMP%` and a reboot deleted it** (`I-048`); now `~/.local/bin`, and it needs
`KICAD_CLI` set or fails with a bare `[WinError 2]`. **`Assert-ErcReport` only
counted errors** (`I-049`), so two names on the run-permit sense net passed the
gate; it now fails on any untolerated warning class.

## Preserve for I-002 and hardware work

A hierarchical redraw was attempted and reverted: symbols lacked KiCad instance
data, so the netlist exported **zero components** while the seven sheets looked
correct. Verify every step with `netlist_fingerprint.py`; never alter the
baseline to make it pass. `prune_dangling_labels()` would have deleted the new
wiring on the next `run_all.ps1` (guarded, `I-047`), and it does not remove a
stale label that has come to rest **on** another pin - `I-049`, `I-050`.
