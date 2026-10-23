# Astra - re-check of F7 (read-only)

Your F5/F6 re-check (`astra-F5F6-recheck-report.md`) found two S2 and one S3. Lane F7 (`lane-F7-report.md`)
changed the scan scheduler and the programming script; timing limits are unchanged (RUN window and scan deadline
1200 ms, loop 20 ms). Uncommitted in the working tree on top of `22e5a80`. Claude re-ran every gate on a clean
build: all PASS; AVR worst pass 19.586/20 ms; measured-clock completion gaps 1035/954/863/906 ms for the jitter
patterns 20/8/20/20, 20/1/20/1, 19/20/3, seeded random (REF due, RUN uninterrupted); 60-day soak PASS.

Same question: **where can this firmware close or keep RUN closed when the spec says it must be open, or lock the
machine out when it must recover.** Check in particular:

1. `src/services/scan.c`: CJ reads two sensors per wait pass; REF self-test started with slot 10 and overlapping
   only slots 10-12, slot 13 held until it ends (`02` 10 as amended, `03` 3); 19 mutable-register checks after the
   final P5 in 7/7/5 batches; P15 now complete-to-complete. Is any check the spec requires per scan skipped,
   reordered against the spec, or able to pass on stale data? Can a REF failure, a G08 at test start, or an ADC
   fault during slots 10-12 leave a scan validated? Your counterexample method: try other cadence sequences
   (each interval <= 20 ms, lengthened to measured cost) and look for any gap > 1200 ms.
2. `program.ps1` and `image_metadata.py`: can a wrong, stale or unpatched image still print PROGRAM PASS?
3. Your earlier findings are closed for real, not just their tests.

Spec: `firmware/spec/`. Code: `firmware/family/src`, `include`, `program.ps1`, `image_metadata.py`; tests only to
check a claim. Report under 800 words: severity, file:line, sequence, spec clause, minimal fix. Reproduce S1/S2 on
the AVR simulator if you can. Say plainly if there is no S1. Do not edit files.
