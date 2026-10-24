Created the independent acceptance suite. No forbidden implementation/tests were opened, and no git-writing commands were run.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File firmware/family/test/build_acceptance.ps1
```

**14,182 assertions: 14,170 passed, 12 failed; exit 1.** Host warnings-as-errors/AddressSanitizer and all 11 strict AVR compilations completed. `python docs/check_docs.py`: exit 0, zero findings.

Every failing assertion is covered below:

| Spec clause | Input | Expected | Returned | Judgment |
|---|---|---|---|---|---|
| `04` §3.1 row 1, §3.2 OFF column, §9 | Separately raise C01/C02/C03/C06/C07/C08/C09 on an OFF channel while another fitted channel is normal | `alarm_active=0` each | `1` each — **7 failures** | Code wrong: OFF channels must be ignored |
| `04` §6.1 ACK ordering, §8 | Fresh ACK and validated scan completion in the same call | Window `0 ms`; refresh `false`; PWM `false` | `900 ms`; `true`; `true` — **3 failures** | Code wrong: PWM must await the **next** validated scan |
| `04` §2, §5 R2, §6.1 | Active settings sequence 10; completed scan tagged 9 arrives at 500 ms | No window refresh | Refresh `true` — **1 failure** | Code wrong: inconsistent settings-generation evidence should be rejected |
| Same | Inspect at original deadline, 1001 ms, without another scan | RUN permission `false` | `true` — **1 failure** | Code wrong: old-settings evidence extended the deadline |

Power-cut checks passed after every EEPROM operation in both slot directions: **806 operations per settings save and 500 per calibration save**, including sequence wrap. All six specified NIST reference points passed.

Computed timing: **733 ms normal, 913 ms worst case** (`870 + 5 + 5 + 30 + 3 ms`), below GOAL’s 2 s requirement. This assumes the specified scanner and mechanical delays; physical contact timing remains unmeasured.

Remaining gaps:

- `05` §5: no public combined transaction exposes **epoch 63→0 plus persisted baseline invalidation**. Epoch arithmetic and tag matching pass; coupled power-cut safety remains unverified.
- `05` §1/§7: power-cycle counting and application-controlled persistent event scheduling are outside the core API.
- `04` §4/§6: boot gestures, actual Timer2/WDT behavior, SERVICE relay tests and physical relay behavior require sources outside the mandated link list.
- `04` §3.1: advisory measurement bits are absent from public headers.
- Numerical branch coverage was unavailable with the installed MSVC path.

[Detailed coverage and findings](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/test/acceptance/README.md) · [Raw assertion results](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/test/acceptance/output/test-results.txt)