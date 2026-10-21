Findings **1, 2, 4, 5 and 6 are fixed. S3 remains unresolved because protected code exceeds the 8 ms budget.**

- **Timer2:** sticky ISR expiry, atomic deadline handoff and G05 propagation prevent restart until accepted ACK. Proven by the real-ISR test and same-pass scan/handoff race tests.
- **Service abort:** every physical key stops A02–A04 while held, including a press coinciding with a names-only commit. Proven by the service abort matrix.
- **CPU optimizations:** byte-based fault searches and one settings validation/fitted-mask rebuild per pass. Tests cover all 24 fitted channels. EEPROM recovery, service CRC and ADC verification are incremental; LCD cursor division is removed.
- **ACK timestamps:** the adapter uses the driver’s press/emission timestamps. Tests verify the 50 ms boundary across an intervening tick and queued-event age.
- **Live alarms:** newest channel evidence controls alarm clearance. Core tests cover newer hot and cool results against an older completed scan.
- **Boot:** invalid settings/calibration enter CONFIG_LOCK; SET at boot enters SERVICE. Both paths are tested.

The AVR `-Os` simulator’s worst sampled full-pass estimate is **334015 cycles / 41.752 ms**: measured production instructions, excluding fake MCAL execution, plus bounded real MCAL costs and interrupt allowance. This is not an exhaustive WCET proof.

Two protected-source blockers remain against `01` §2:

- `settings_store.c`: ordinary commit alone **76044 cycles / 9.5055 ms**; epoch-wrap commit **109606 / 13.7007 ms**.
- `mcal/spi.c`: normal 30-byte CJ SPI work alone **97020 cycles / 12.1275 ms**.

After deleting all three specified output directories, the required commands exited **0**:

- `build.ps1`: hardware **234**, scan **103**, peripherals **71**, service **287**, review **1969**, integration **2693646**, Timer ISR **11** checks PASS.
- `build_core.ps1`: **125440 checks, 0 failures**.
- `build_acceptance.ps1`: **14182 passed, 0 failed**.

AVR: **54462 B program + 2 B CRC**; **10254 B static RAM**, **11790 B including stack**. Host crossing-to-PWM-stop maximum: **688 ms**; stalled ADC: **88 ms**.

The [integration README](D:/tasks/thermo/.claude/worktrees/24ch-rev-a4/firmware/family/test/integration/README.md) lists every changed file, reasons for the permitted driver/service/scan changes, and timing reproduction commands. Protected files remain unchanged. No git writes were run.