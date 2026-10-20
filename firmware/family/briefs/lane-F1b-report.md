Fixed F1b; left uncommitted for Claude.

Overflow now drops the new entry, increments a saturating per-boot loss counter, and raises alarm-only G13. It clears after the queue’s final byte is durable and an ACK is accepted. First-out TRIP gets priority over companion notifications; other G13 save-failure sources remain intact.

Changed under `firmware/family/`: `src/app/{app,ee_owner,service}.c`, `include/app/ee_owner.h`, and `test/integration/{test_app.c,README.md}`. The permitted service change adds `P17 EVENTS_LOST`.

All generated outputs were deleted before the three gates; **all exited 0**:

| Gate | Output counts |
|---|---|
| `build.ps1` | hardware 234; scan 103; peripherals 69; service 287; **integration 2691395 checks PASS** |
| `test/build_core.ps1` | **125435 checks, 0 failures**; S01–S28 PASS |
| `test/build_acceptance.ps1` | **checks=14182 passed=14182 failed=0** |

The 24-channel island-loss burst test recorded **40 lost events**, stored the B02 first-out as the first new TRIP, and recovered RUN through keys without a reset. Additional tests cover early ACK, drain without ACK, the final free queue slot, shared G13 sources, and a nonzero service report.

AVR: **52,642 bytes flash + 2-byte CRC**; **10,016 bytes static RAM**, **11,552 including stack**. `check_docs.py`: **0 findings**.