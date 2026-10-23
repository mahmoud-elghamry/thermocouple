# Lane C: independent protection-core acceptance

Run from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File firmware/family/test/build_acceptance.ps1
```

`-Gcc` selects the build_core.ps1 GCC/sanitizer/gcov setup when host GCC is available.
Default is its MSVC setup, /W4 /WX plus AddressSanitizer, followed by strict AVR
production compilation (-std=c11 -Os -Wall -Wextra -Werror). The runner returns
nonzero for any failed assertion. `output/test-results.txt` preserves every failure's
clause, input, expected value and returned value. Generated artifacts are ignored.

Only public headers and the permitted specification were used to derive tests.
No production implementation, existing unit test or scenario was opened. The build
links exactly build_core.ps1's eleven production sources. The hardware output seam
is a no-op fake; no production source or existing test is modified. All test loops
are bounded, arrays have fixed bounds, and tests allocate no dynamic memory.

## Timing revision and observed result (2026-10-23, Lane C2)

Expectations follow `git diff 660d0cb -- firmware/spec` and the current clauses:

* `test_accept_protection.c`: 04 5 R2 accepts age1199 ms and rejects age1200 ms.
* `test_accept_outputs.c`: 04 6.1 and 09 S05/S26 use a1200 ms RUN window,
  check1199/1200 ms boundaries, place the late scan at1250 ms, and shift ACK
  grace, recovery, unauthorized-refresh and uint32-wrap inputs accordingly.
  Output-only fixtures also carry the specified1200 ms window; all04 6.2
  feedback assertions are unchanged.
* 03 3.1/10.2 and04 6.3: worst simulated scan1050 ms, conservative crossing
  budget1093 ms; normal690 ms and the2000 ms requirement remain unchanged.

The command above was run **once**: exit1, **14,182 checks / 14,153 passed /
29 failed**. MSVC /W4 /WX compilation and strict AVR production compilation
passed; no AddressSanitizer diagnostic was emitted. The build script was unchanged.
The complete assertion report is `output/test-results.txt`; failures grouped below
retain every input and expected/actual combination (NONE=0, G04=4, G06=6, G07=7):

| Clause / input | Count | Expected | Actual |
|---|---:|---|---|
| 04 5 R2: scan age1199 ms | 1 | ACK_NONE=0 | ACK_R2_SCAN=2 |
| 04 6.1: window length after new scan | 1 | 1200 ms | 900 ms |
| 04 6.1: window age1199 ms, ordinary clock and uint32 wrap | 2 | run_permission=1 | 0 |
| 04 6.2: RUN all four command/sense combinations at t=0,59,60,160 ms; matching pairs (0,1),(1,0) also at t=161 ms | 18 | NONE=0 | G04=4 |
| 04 6.2: RUN mismatching pairs (0,0),(1,1) at t=161 ms | 2 | G06=6 | G04=4 |
| 04 6.2: ALARM mismatching pairs (0,0),(1,1) at t=161 ms | 2 | G07=7 | NONE=0 |
| 04 6.2: recovering RUN mismatch, new duration exactly100 ms | 1 | NONE=0 | G04=4 |
| 04 6.2: recovering RUN mismatch, new duration101 ms | 1 | G06=6 | G04=4 |
| 04 1/6.3: crossing at102 ms, next result1050 ms later | 1 | PWM-off at1152 ms | at1001 ms (899 ms after crossing) |

These are observations against production being changed in parallel; no production
source or other test folder was opened, no implementation fix was attempted, and
the acceptance command was not rerun. This core link list has no ADC RDY-window,
scan-duration detector or actual loop-period test; 03 3/10/11's69 ms RDY upper bound,
1200 ms scan deadline and01 2's20 ms loop bound are not directly exercised here.
`python docs/check_docs.py`: exit0, zero findings. Only acceptance files were edited.

## Historical observed result (2026-10-20, before the timing revision)

14,182 assertions: **14,170 pass, 12 fail**. MSVC warnings-as-errors compilation,
AddressSanitizer execution (no sanitizer diagnostic), and all eleven strict AVR
compile gates complete. Exit 1 is intentional because acceptance is not clean.
`python docs/check_docs.py`: 0 findings. Host GCC/gcov was unavailable on PATH;
branch coverage was not measured, and no branch-completeness claim is made.

Each failing assertion is a finding; grouped here only to avoid repeating inputs:

| Clause | Input | Expected from spec | Returned | Judgment |
|---|---|---|---|---|
| 04 3.1 row1, 3.2 OFF column, 9 TC/AC rows | In RUN, CH1 canonically OFF, CH2 fitted/normal; separately raise C01, C02, C03, C06, C07, C08, C09 on CH1 | `alarm_active=0` for each | `1` for each (7 failures); RUN remains permitted | Code wrong: OFF is ignored entirely (09 S19) |
| 04 6.1 ACK ordering, 8 scan-before-mailbox | START_LATCHED, fresh 50 ms ACK and validated completion in same call | `window_remaining_ms=0` | `900` | Code wrong: opening must await NEXT scan |
| Same | Same | `window_refresh=0` | `1` | Code wrong |
| Same | Same passed to outputs_step | `pwm_enable=0` | `1` | Code wrong |
| 04 2 current settings, 5 R2, 6.1 positive scan proof | RUN window opened at101 ms, settings seq10, complete scan tagged9 at500 ms | `window_refresh=0` | `1` | Code wrong: wrong-generation evidence cannot renew permission |
| Same | No new scan; inspect at1001 ms, original deadline | `run_permission=0` | `1` | Code wrong: old-settings scan extended deadline |

The old-sequence test intentionally contradicts the caller's scan_validated boolean
with its settings_seq: a defensive safety boundary must reject this inconsistent
proof. ACK correctly rejects it (the separate R2 test passes); RUN refresh does not.

## Coverage and oracles

| Test file | Specification anchors |
|---|---|
| tables.c | 04 3.1 all conditions and threshold edges; 3.2 all modes/OFF; 3.3 hysteresis; 9 every fault/action row in both modes, C10/C11 via conditions; 01 5 unknown enums; 09 S21 bank independence |
| test_accept_protection.c | 04 4 all five states versus no event, ACK, invalid settings/calibration, protection/name commit and immediate trip/fault; boot SERVICE precedence; corrupt state/complements; 4.1 first-out; 5 R1-R6 and refusal boundaries; 7.2 alarm latch |
| test_accept_outputs.c | 04 1 immediate trip; 6.1 ACK ordering, validated-only refresh, flow, exact1200 ms expiry (09 S05/S26), late scan with/without intervening calls, no auto recovery, uint32 time wrap; 6.2 all four active-low rows for both relays, 60 ms settle, >100 ms continuous mismatch; 6.3 timing |
| test_accept_settings.c | 05 2 explicit independently packed layout/CRC; 3 each field invalid with repaired CRC, OFF canonical, board/PT100 constraints; 4 all A/B rows and sequence wrap; 5 protection change classification, clear setpoints, every epoch increment incl63->0; 6 tag/type/epoch, staged completeness and CRC; 09 S27 K->OFF->K baseline binding |
| storage.c | 05 4-6 and 09 S07: reboot after EVERY operation, both inactive slots, settings and calibration, pre-existing valid older copy, sequence wrap, no mixed record, newest valid selection, retry/failure faults G02/G13 |
| math_events.c | 03 7 all six listed NIST points, forward/inverse/CJ, 0.03+0.05 C bound, negative differential EMF, C08 floor/C02 range; 05 7 event packing/CRC, ring and sequence wrap, bad entries skipped |

Power cuts: settings806 operations per direction (403 writes), calibration500 per
direction (250 writes). Every operation is checked, including immediately before
the first write and after final verification. Real EEPROM delays are not modeled.

Timing injects the spec's K100 C EMF (4.096 mV, CJ0 C) immediately after the prior
channel slot, schedules the next result after690 or1050 ms (03 3.1/10.2), then runs real tc_math,
channel/protection and output decisions at1 ms simulated steps. Expected core PWM-off is at
690/1050 ms (the current worst-case run fails as recorded above). Adding the two5 ms processing allowances,30 ms pump decay and3 ms relay
release gives **733 ms normal, 1093 ms worst**, below GOAL's2000 ms requirement (04 6.3).
The scanner, electrical filter and mechanical contact are assumptions, not measured
or linked here; this is a core end-to-end simulation conditional on those timings.

## Untestable or deliberately not claimed

* **05 5 epoch-wrap coupled invalidation:** set_change_type takes only chan_cfg_t;
  set_commit takes no calibration pointer; cal_commit is a separate transaction.
  No public combined type/settings/calibration transaction can be driven to verify
  that63->0 also writes the historical baseline as not learned, or to cut power
  between those two commits. The epoch arithmetic and tag rejection ARE tested;
  the wrap collision prevention itself remains unverified. A caller must invalidate
  calibration first or otherwise ensure an ancient matching tag can never run.
* **05 1, 7.2-7.3:** no power-cycle counter/header manager or full application's
  event-persistence orchestrator in the core API. Deferred POWER_UP after first scan,
  transition-only persistent writes and wear behavior are not observable here.
* **04 4 boot gestures/reset flags, 9 G03 halt/G15 fuse permanence/G14 re-init;
  01 2.3 watchdog/checkpoints:** core can receive faults and settings validity but
  cannot drive the actual boot/loop orchestration. Fault actions and safe state
  decisions are tested, not detector coverage or physical reset/halt behavior.
* **04 6.1 Timer2 ISR/atomicity, 6.2 electrical/coil behavior, 6.3 actual contact
  timing; 04 4 SERVICE bench exception:** outside the mandated core link list.
  Low-level hardware/service headers exist; testing those sources would require
  widening the link list. The mock does not prove timer ISR or relay operation.
* **04 3.1 advisories / 09 2 advisory tests:** public measurement flags expose no
  ADVISORY_RATE/STUCK bits (C04/C05 are reserved in v1); reserved fault actions are
  tested as no action, rather than inventing flag bit values.
* **09 1/2 numerical branch coverage and every50 C NIST sweep:** no host gcov tool
  was available, and permitted03 7 supplies six numerical points, not a full NIST
  oracle. No implementation/generated-table values were reused as expectations.

STATE/ISSUES were intentionally not edited: Lane C's explicit write scope permits
only this directory and build_acceptance.ps1. Findings are left here for Claude's
review and project-record updates. No git-writing command was run.
