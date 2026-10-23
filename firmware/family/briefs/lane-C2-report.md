Updated only acceptance files; all other assertions remain unchanged.

- `test_accept_protection.c`: ACK freshness boundaries now 1199/1200 ms (`04 §5 R2`).
- `test_accept_outputs.c`: 1200 ms window, expiry, ACK timeout, late scan at 1250 ms, recovery and wraparound (`04 §6.1`, `09 S05/S26`). Worst simulated scan is 1050 ms; crossing budget is **1093 ms**, against the unchanged 2 s requirement (`03 §3/10`, `04 §6.3`).
- README records changes and results. No direct RDY or loop-period tests exist in this suite.

Ran once:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File firmware/family/test/build_acceptance.ps1
```

**Exit 1: 14,182 checks, 14,153 passed, 29 failed.** Strict AVR compilation passed.

Every failure is represented below; command/sense pairs use the raw sense level.

| Clause / input | Count | Expected → actual |
|---|---:|---|
| `04 §5 R2`: scan age 1199 ms | 1 | ACK_NONE(0) → R2(2) |
| `04 §6.1`: refreshed window | 1 | 1200 → 900 ms |
| `04 §6.1`: age 1199 ms, normal/wrapped clock | 2 | permission 1 → 0 |
| `04 §6.2`: RUN all pairs at 0/59/60/160 ms; matching pairs also at 161 ms | 18 | NONE(0) → G04(4) |
| Same: RUN mismatching pairs at 161 ms | 2 | G06(6) → G04(4) |
| Same: ALARM mismatching pairs at 161 ms | 2 | G07(7) → NONE(0) |
| Same: renewed RUN mismatch at 100/101 ms | 2 | 0/6 → 4/4 |
| `04 §1/6.3`: worst crossing | 1 | PWM-off at 1152 → 1001 ms |

[Full report](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/test/acceptance/output/test-results.txt). Production was not inspected or changed. Documentation check: zero findings.