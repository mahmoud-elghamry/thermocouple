# Brief - Lane F1d: bring the AVR loop inside 8 ms

Continuation of your F1 session. Claude re-ran your profiler: 334015 cycles / 41.752 ms worst pass, same as you.
Budget `01` 2: worst pass <= 8 ms = 64000 cycles **including** your 25% + 2048 interrupt reserve. Claude's analysis
of where it goes, fix in this order and re-profile after each:

1. **Soft SPI to the TMP126 (`src/mcal/spi.c` `spi_soft_xfer`): 3234 cycles/byte**, the bit timing needs ~4 us per
   bit = ~256 cycles/byte. The cost is `gpio_write`/`gpio_read` through the board pin table and `delay_us` as a
   called loop. Use direct port bit operations on the fixed pins (PB5/PB6/PB7 on the 24-ch, from `board_cfg` at
   compile time via macros, keep the 8/40-ch extension point) and `_delay_us()` constants. Keep the TMP126 timing
   of its data sheet (min clock high/low, setup/hold) and the SIO_WR_N gating order of `02` 2.
2. **CJ reads per pass:** read **one** TMP126 per loop pass (state machine over the six sensors), not 30 bytes in
   one pass. Scan timing of `03` must not change (CJ values are needed once per scan).
3. **Settings / calibration commit (`settings_store.c`): 76044 cycles in one call, 109606 with epoch wrap.**
   Split begin into bounded steps across passes (validate, pack, CRC, compare, then the existing byte machine),
   at most ~8000 cycles per pass. Power-cut and retry behaviour must stay exactly as tested (unit + acceptance +
   integration suites are the oracle). You may edit `settings_store.c`, `settings.c`, `settings_cal.c` and
   `include/services/settings.h` for this, nothing else of the core.
4. **Timer2 ISR: 716 cycles every 1 ms (~9 % of the CPU).** Bring it under ~250 cycles (key sampling as a few
   shift operations, no calls through the pin table). It also delays every other interrupt.
5. Anything else the profiler shows above ~5000 cycles in one pass.

Then: the profiler's worst pass must be <= 64000 cycles with the reserve, measured over the same phases plus a
pass that contains a commit step, a CJ read, a slot completion and an ACK together. Add the profiler to
`build.ps1` as a gate (fail above 64000) so it can never regress silently; if the profiler run takes more than
~3 minutes, make it a separate script and say so.

Same write rules as F1c plus the files named above; never `test/acceptance/`, `test/build_acceptance.ps1`,
`include/common/*`. Done means: outputs deleted, `build.ps1`, `test/build_core.ps1`, `test/build_acceptance.ps1`
exit 0, and the profiler under budget. Report under 400 words: cycles before/after per item, the final worst pass,
the three results with counts, AVR flash/RAM.
