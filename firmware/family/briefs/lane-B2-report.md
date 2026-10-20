All four fixes are complete:

1. **OFF channels:** C01–C09 active faults and latches are ignored for alarm, trip, and ACK; global/bank latches remain effective.
2. **ACK ordering:** ACK into RUN leaves the window closed. A validated scan processed in a later pass must open it.
3. **Settings sequences:** refresh requires the accepted sequence. Names-only commits allow the immediately replaced sequence until new-sequence evidence arrives; unannounced changes cannot extend the window.
4. **Epoch wrap:** public `set_commit_with_cal` persists and verifies baseline/tag invalidation before publishing epoch-zero settings. Plain `set_commit` rejects wraps. Retry guards prevent stale calibration-slot reuse.

All required commands exited **0**:

| Command | Result |
|---|---|
| `test/build_core.ps1` | **125,429 checks, 0 failures**, S01–S28 pass; strict AVR compilation passes |
| `test/build_acceptance.ps1` | **14,182 assertions, 0 failures**; strict AVR compilation passes |
| `build.ps1` | **715 checks pass**; AVR build and CRC verification pass |

Power-cut and failure-injection tests cover both slot directions, simultaneous wraps, changes to/from OFF, sequence rollover, and retries.

No remaining failures. Acceptance sources and runner were untouched. `docs/check_docs.py` also passed with zero findings.