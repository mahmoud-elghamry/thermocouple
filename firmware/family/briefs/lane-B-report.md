Implemented Lane B. **4,084 checks pass**, with AddressSanitizer and strict AVR compilation.

Files written under `firmware/family/`:

- `include/services/`: `tc_math.h`, `tc_tables.h`, `settings.h`, `events.h`, `fault.h`.
- `include/app/`: `channel_eval.h`, `protection.h`, `outputs.h`, `outputs_hw.h`.
- `src/services/`: corresponding implementations, plus `settings_cal.c`, `settings_store.c`, `settings_bytes.h`.
- `src/app/`: `channel_eval.c`, `protection.c`, `outputs.c`, `outputs_shell.c`.
- `test/unit/`: module tests, runner, fixtures, NIST generator/reference vectors, and generated-output ignore rules.
- `test/scenarios/test_scenarios.c`; `test/build_core.ps1`.

Exact verification command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File firmware/family/test/build_core.ps1
```

Results:

- **4,084 checks, zero failures**; MSVC `/W4 /WX` with AddressSanitizer.
- All production modules compile with AVR `-Wall -Wextra -Werror`.
- S01–S28 pass as **core boundary simulations**. ADC retries, physical watchdog timing, and actual Modbus flooding remain integration checks.
- Settings and calibration saves tested at every EEPROM byte boundary.
- `python docs/check_docs.py`: **0 findings**.
- [Test report](/D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/test/unit/output_core/test-results.txt).

**gcov branch coverage remains unverified:** native GCC was unavailable and WSL access was denied. The build script includes a `-Gcc` coverage mode.

Spec findings for Claude:

- `05-settings-events.md` §§2.2, 6: the six-bit epoch wraps after 64 type changes, permitting an ancient matching baseline to become valid again.
- `03-acquisition.md` §7: the stated interpolation bound excludes rounding to the public 0.1 °C output.
- `04-protection.md` §§5–6: ACK-to-window ordering is unspecified. This implementation waits for a new validated scan before enabling PWM and trips after 900 ms without one.
- `05-settings-events.md` §6: PT100 calibration/tag completeness is unspecified; fitted PT100 channels conservatively fail completeness.
- `04-protection.md` §§2–3.1: advisory flags are absent from the shared measurement header.

Requested shared-header changes:

- Widen `result_t.flags` and define separate advisory flags; consider a distinct C09 flag.
- Clarify C03 registry units as zero-based **channels**, carrying raw pin identity separately in events. Lane B currently requires that normalization.

Shared headers and project state files remain for Claude’s review/update under the lane ownership rules.