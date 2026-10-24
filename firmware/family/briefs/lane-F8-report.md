# Lane F8 - report (Sol wrote the code; Codex usage limit stopped it during its final gates; Claude ran them)

No timing or specification limit changed.

**REF retry (Astra F7 S2-1).** A REF precheck G08 leaves the attempt pending (`ref_pending`); startup/recovery
also starts pending. Slot 10 retries once per scan. Only a completed pulse with restored REFOK (pass or G09)
updates `last_ref`. The low-wait G08 path also stays pending. G08 trips and requires a fresh ACK.

**Identity (Astra F7 S2-2).** 64-byte constant at 0x1FF80 (`src/app/image_identity.c`): magic, board 24, MCU
signature, version, 12-digit git HEAD, dirty flag. `build.ps1` reads git HEAD/status, checks the link address and
includes the record in the boot CRC (code/data then identity). Service P01 reads the same record.
`program.ps1` requires matching embedded record, sidecar, CRC and SHA-256 plus the current HEAD; `-Release`
selects an approved HEX/sidecar and bypasses only the HEAD check. DIRTY prints in the PASS line.

**Gates, run by Claude on a clean build 2026-10-23 (all exit 0):**

- `test/build_core.ps1`: 125511 checks, 0 failures.
- `test/build_acceptance.ps1`: 14361/14361.
- `build.ps1` (1040 s): cppcheck 0 findings; programming script 67 checks; flash identity CRC 39780 checks (every
  identity byte); scan gap/REF retry 27143 checks; host jitter gaps 1080/968/989/917 ms; AVR worst pass
  155766 cycles / 19.471 ms; AVR measured-clock jitter gaps 1047/956/862/898 ms, REF exercised, RUN
  uninterrupted; AVR REF retry: first scan after the successful retest validates 1100 ms after wire restoration,
  fresh ACK restores RUN, held-high never validates; stack 579/1536 B; startup order PASS.
- Flash 74086 B (code/data 74022 + identity 64), CRC16 36B9; RAM 11335/14336 B incl. stack allowance.
- `test/integration/soak.ps1`: 265362945 checks PASS, 60 simulated days, 1187 power cuts, 595 s.
- `program.ps1 -DryRun`: `PROGRAM PASS board 24 atmega1284p v1.0.0 22e5a80fbc63 DIRTY (DRY RUN ...)`.
