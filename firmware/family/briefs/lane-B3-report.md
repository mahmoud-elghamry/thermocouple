All six runs passed with identical output between runs.

The three reported failures indicate code faults:

- **Calibration, twice — `05` §5:** a stale slot could overwrite the verified baseline invalidation after epoch wrap. Both commit APIs must reject it.
- **Protection — `04` §6.1:** evidence older than a missed save must not refresh the RUN window.

The corrective guards were **already present on arrival**; the initial clean core run passed **125429 checks**. B3 preserved every assertion and added six checks proving rejected commits leave transaction state unchanged and rejected scans leave the deadline unchanged. Comments cite the spec and explain the safe, stricter refusal of all old tags after a sequence gap.

Both stale-output directories were deleted before testing.

| Command | Run | Output counts | Exit |
|---|---:|---|---:|
| `test/build_core.ps1` | 1 | 125435 checks, 0 failures | 0 |
| `test/build_core.ps1` | 2 | 125435 checks, 0 failures | 0 |
| `test/build_acceptance.ps1` | 1 | checks=14182 passed=14182 failed=0 | 0 |
| `test/build_acceptance.ps1` | 2 | checks=14182 passed=14182 failed=0 | 0 |
| `build.ps1` | 1 | hardware 234; scan 103; peripherals 69; service 287; main 22 — PASS | 0 |
| `build.ps1` | 2 | hardware 234; scan 103; peripherals 69; service 287; main 22 — PASS | 0 |

Strict AVR gates and image CRC verification passed. B3 changed only the two permitted unit-test files. Acceptance sources and runner hashes are unchanged. `check_docs.py`: zero findings; `git diff --check`: passed.