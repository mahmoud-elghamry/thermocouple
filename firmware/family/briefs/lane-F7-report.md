F7 is complete; timing limits are unchanged.

The scheduler collects CJ data during conversion waits, performs all 19 mutable checks after final P5 in **7/7/5 batches**, and overlaps REF testing only with internal-node slots 10–12. External conversions wait for REF recovery. P15 now reports completion-to-completion gaps.

| Cadence | Host before → after | AVR after |
|---|---:|---:|
| 20/8/20/20 | 1244 → 1080 ms | 1035 ms |
| 20/1/20/1 | 1071 → 968 ms | 954 ms |
| 19/20/3 | 1095 → 989 ms | 863 ms |
| Seeded random ≤20 ms | 994 → 917 ms | 906 ms |

Before values are diagnostic measurements. Final cases validated every scan, exercised REF and maintained RUN.

Programming now verifies production metadata, HEX SHA-256 and stored CRC before invoking avrdude. Masked efuse read-back is accepted. **41 programmer checks passed**, including wrong-image rejection; production DryRun passed.

All required commands exited **0** after cleanup:

- Build: integration **2764973**, F4 **1378434**, gap **22240**, UI **702/586**, Modbus **1576689** checks passed.
- Core: **125511 checks, 0 failures**.
- Acceptance: **14361 passed, 0 failed**.
- Soak: **265362945 checks**, **259194841 passes**, 60 simulated days; wrap/ACK checks and **1187 power cuts** passed in **675.93 seconds**.

AVR worst pass: **156685 cycles / 19.586 ms**, including reserve. Flash: **73638 B** including CRC. RAM: **11328/14336 B** including stack allowance; measured stack: **539/1536 B**.

No unresolved spec gaps. Work remains uncommitted. [Full report](firmware/family/briefs/lane-F7-report.md).