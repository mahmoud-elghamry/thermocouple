Implemented standalone F2 within the permitted paths: `include/app/ui.h`, four `src/app/ui*.c` files, `test/ui/`, and `test/build_ui.ps1`. Shared files remain unchanged.

Validation:

- `powershell -File firmware/family/test/build_ui.ps1`: **695 UI + 586 gesture checks passed**, zero failures; strict AVR compilation passed.
- `powershell -File firmware/family/test/ui/profile_ui.ps1`: **2,678 samples**, maximum **0.77325 ms**.
- RAM: **556 B static**, reusing the existing app mailbox; largest individual UI stack frame **35 B**.
- `python docs/check_docs.py`: zero findings.

Claude must integrate `ui_init(); ui_bind_candidate(&mailbox);`, call `ui_task(1000)` after `app_step`, forward non-ACK events through `ui_key()`, and report durable completion through `ui_store_result()`. Mailbox submission must skip copying when `candidate == &mailbox`. Recovery, event-history, extrema, newest-alarm, and repeated ACK-result hooks also need connecting.

Exact calls and remaining gaps are in [HANDOFF.md](/D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/test/ui/HANDOFF.md).

The material integration gap is **05 §5**: the existing store rejects repeated confirmed type changes within one edit session. **06 §3** also conflicts with its detail/events examples over status-line placement; the implementation follows the examples. Timing results depend on the documented mailbox integration.