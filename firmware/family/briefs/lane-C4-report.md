Replaced the 8/40-channel validity and PT100-placement block with **96 rejection/CONFIG_LOCK assertions**, replacing 5 assertions:

- Wrong board/count identities are rejected (`00 Targets`, `05 §2.1 bytes 3–4`, `§3`).
- Raw channel types **3, 4, 255** are rejected (`05 §2.2`). Value 3 comes from the spec; no `CH_TYPE_PT100` dependency remains.
- Rejected records leave CONFIG_LOCK, RUN and PWM off after ACK (`05 §4`, `04 §6.1`).

The folder audit found no other oversized channel/bank accesses. All unrelated assertions remain unchanged.

Ran once:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File firmware/family/test/build_acceptance.ps1
```

**Exit 1.** MSVC and strict AVR compilation passed. Host execution aborted before the final counts:

| Failure | Expected | Actual |
|---|---|---|
| Wrong-build RAM validation (`05 §2.1/3`) | Return a rejection status | AddressSanitizer stack-buffer-overflow in `set_validate_part`, called by `set_validate` |

The diagnostic identifies the new validation call but does not identify its matrix row. **Completed assertion counts are unavailable; one sanitizer abort was captured.** The existing 14,270-check output file is not from this aborted invocation.

[Recorded result](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/test/acceptance/README.md). No production inspection, fixes, reruns or git writes.