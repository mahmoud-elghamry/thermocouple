# Brief - Lane F6: 24-ch only, static analysis, programming script, 60-day soak

Continuation of your F1 session, after F5 is committed. Owner decisions 2026-10-23: the 40-ch board is out of
scope (probably never built) - drop what it costs; the 24-ch board must work well; J support can stay as it is
(it is only a table). Do these in order, re-running the gates after each:

1. **24-ch only.** Remove 40-ch / PT100 / address-decoder code paths and the board-type-40 branches. Shrink the
   arrays to the 24-ch need: `MAX_CHANNELS` 24 and `MAX_BANKS` 3 (Claude has updated `include/common/types.h` and the
   spec for this - see the commit before this run). Keep the 8-ch extension point only where it costs nothing
   (`board_cfg` structure). Keep the EEPROM map addresses of `05` unchanged. Report the RAM saved.
2. **cppcheck gate.** Cppcheck 2.22 is installed at `C:/Program Files/Cppcheck/cppcheck.exe`. Add it to
   `build.ps1` (`--enable=warning,portability,performance --std=c11 -Iinclude`, fail on any finding, inline
   suppression only with a one-line reason). Current findings to fix: `modbus_map.c:116` add a bounds guard in
   `mb_register` (range() already checks, keep it defensive); `settings_store.c:154` pointer arithmetic out of
   bounds before subtraction (parenthesise the offset); `service.c:117/129/134` printf `%u` with signed args.
3. **Programming script for the 24-ch board:** `firmware/family/program.ps1` - avrdude with a USBasp
   (`-c usbasp -p m1284p`), write flash (`build/thermo24_f0.elf` or the current image) and the fuses of `02` 6
   (lfuse 0xF7, hfuse 0xC1, efuse 0xFC), then **read the fuses back and fail on any mismatch**; verify flash; print
   one clear PASS/FAIL line. Find avrdude on this machine (PlatformIO `~/.platformio/packages/tool-avrdude*` or the
   Proteus Arduino tools); use `-B` for a slow first clock (factory fuses = 1 MHz) and say so. A `-DryRun` switch
   prints the commands without a programmer. Model it on `firmware/8ch-legacy/program.ps1` (old ATmega32A).
4. **60-day soak test** in simulated time (host model, accelerated clock): the integrated firmware runs through the
   32-bit millisecond wrap (49.7 days) and the 24-bit uptime field, with random trips, ACKs, faults, UI saves,
   Modbus traffic and power cuts at random points; checks every N simulated minutes that RAM-resident counters,
   queues, event ring, fault registry, stack high-water and timing stay bounded and that trip/ACK behaviour around
   the wrap is unchanged. Keep its run time reasonable (separate script if > 5 min; say how long).

Write rules as F5. Never `test/acceptance/`, `test/build_acceptance.ps1`. Done means: outputs deleted;
`build.ps1` (incl. cppcheck, profiler), `test/build_core.ps1`, `test/build_acceptance.ps1` exit 0 (acceptance may
need the 24-only update from another lane - report its result as is), `program.ps1 -DryRun` runs. Report under 500
words with counts, RAM/flash before/after, cppcheck result, soak duration and result.
