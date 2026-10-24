Added **88 assertions** for HOT and OPEN interleavings in `test_accept_protection.c`, citing `04 §3.3`, `§5 rule 5`, and `§6.1`. They cover newer evidence vetoing ACK, adverse scan completion keeping the window closed, and recovery after a validated cool scan. Existing assertions remain unchanged.

Ran once:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File firmware/family/test/build_acceptance.ps1
```

**Exit 1: 14,270 checks; 14,264 passed; 6 failed.** Strict AVR compilation passed.

All failures occurred on ACK before N+1 completed, with completed scan N still cool:

| Case | Field | Expected | Actual |
|---|---|---|---|
| HOT | ACK reason | R4 (4) | NONE (0) |
| HOT | State | TRIPPED (3) | RUN (2) |
| HOT | Run permission | 0 | 1 |
| OPEN | ACK reason | R4 (4) | NONE (0) |
| OPEN | State | TRIPPED (3) | RUN (2) |
| OPEN | Run permission | 0 | 1 |

The window and PWM remained off despite the erroneous ACK acceptance. Adverse completed-scan and cool-recovery checks passed, as did all 14,182 pre-existing checks.

[Full results](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/test/acceptance/output/test-results.txt). No production inspection, implementation changes, or git writes.