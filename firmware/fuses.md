# Fuse map — ATmega32A, THERMO-8CH REV A0

**A unit whose fuses have not been read back and recorded is not a unit that
has been commissioned.** Programming the flash is half the job; the fuses
decide the clock, the brown-out threshold and which pins exist.

Issues: `I-015`, `I-032`, `I-016`.

---

## The values

| Fuse | Factory default | **Required** |
|---|---|---|
| Low | `0xE1` | **`0x24`** |
| High | `0x99` | **`0xD1`** |
| Lock | `0xFF` | `0xFF` for prototypes — see below |

Program them with `firmware/program.ps1`, which reads them back and fails if
they do not match.

---

## Low fuse `0x24` = `0b0010_0100`

| Bit | Name | Value | Meaning |
|---|---|---|---|
| 7 | BODLEVEL | 0 | brown-out trigger level **4.0 V** |
| 6 | BODEN | 0 | brown-out detector **enabled** |
| 5 | SUT1 | 1 | start-up 6 CK + 65 ms |
| 4 | SUT0 | 0 | (slowly rising power) |
| 3–0 | CKSEL3..0 | 0100 | internal RC oscillator, **8 MHz** |

### CKSEL is the one that will bite you

The factory default is `CKSEL = 0001` — internal RC at **1 MHz**. The firmware
is built with `F_CPU=8000000UL`.

On a fresh chip that has not had its fuses set, every `_delay_ms()` runs **eight
times longer** than the code intends. The 456 ms sensor scan becomes about
3.6 s, and the 1 s trip requirement in `docs/GOAL.md` is missed by roughly four
times.

Nothing reports this. The image is correct, the build is clean, the LCD updates,
the temperatures are right. The unit simply takes four seconds to open a contact
it was specified to open in one. This is `I-032`.

### Brown-out at 4.0 V, not 2.7 V

`docs/ISSUES.md` `I-015` says the right level is 2.7 V "at 3.3 V". That was
wrong, and it is corrected here.

`U1` runs from **`+5V_CTRL`**, not 3.3 V. The 3.3 V rail (`+3V3_SENS`) feeds the
eight MAX31856 converters, and they are on the far side of the isolation
barrier. On a 5 V rail the correct trigger is **4.0 V**: it resets the part
before the supply sags into the region where instruction execution is undefined
and arbitrary code could raise `RUN_PERMIT`.

With BOD disabled — the factory default — a slow supply sag is exactly the
condition under which this unit would permit an engine to run while executing
garbage.

---

## High fuse `0xD1` = `0b1101_0001`

| Bit | Name | Value | Meaning |
|---|---|---|---|
| 7 | OCDEN | 1 | on-chip debug disabled |
| 6 | JTAGEN | 1 | **JTAG disabled** |
| 5 | SPIEN | 0 | serial programming enabled — required for ISP |
| 4 | CKOPT | 1 | low-power oscillator, correct for the internal RC |
| 3 | EESAVE | 0 | **EEPROM preserved through a chip erase** |
| 2 | BOOTSZ1 | 0 | boot size 1024 words (unused) |
| 1 | BOOTSZ0 | 0 | |
| 0 | BOOTRST | 1 | reset vector at 0x0000 |

### JTAG is enabled by default and it takes four pins

`JTAGEN` is programmed (enabled) on a factory chip, and JTAG occupies **PC2,
PC3, PC4 and PC5** — `SPARE_PC2`..`SPARE_PC5` in the schematic.

Any future use of those pins reads a constant value until `JTAGEN` is
unprogrammed. The first one planned is the run-permit driver read-back on PC2
(`I-016`, part of the REV A1 change set in `docs/decisions/0010`).

### EESAVE protects the setpoint

The operator setpoint lives in EEPROM (`src/hal/settings_store.c`, `I-012`).

With `EESAVE` programmed (`0`, as specified here) a chip erase leaves it alone,
so reprogramming a unit in the field keeps its setpoint.

With `EESAVE` unprogrammed — the factory default — reprogramming **erases the
setpoint**. The unit then comes back config-locked: it shows `SET SETPOINT` and
refuses to permit running until an operator stores one. That is the safe
behaviour and it is deliberate, but the site has to be told why, or it looks
like the unit failed.

---

## Lock bits

Leave at `0xFF` while prototyping, so the fuses and the flash can still be read
back for diagnosis.

For production units, consider `0xFC` (LB1, LB2 programmed — further programming
and verification disabled). The trade-off: it prevents reading the image back
from a unit that has come off a machine, which is usually the first thing you
want when something has gone wrong in the field. Do not set it until the design
is settled.

---

## Verification

```powershell
avrdude -c usbasp -p m32 -U lfuse:r:-:h -U hfuse:r:-:h -U lock:r:-:h
```

Expect `0x24`, `0xD1`, `0xff`. `program.ps1` does this automatically and exits
non-zero on a mismatch, but a commissioning record should carry the values read
back from that specific unit, together with the firmware version shown on the
LCD at boot (`APP_FIRMWARE_VERSION` in `include/app/version.h`).

---

## These values assume the internal RC oscillator

The board has no crystal. `U1` pins 12 and 13 (XTAL1/XTAL2) are unconnected —
see the note in `hardware/8ch/populate_schematic.py`.

Adding one is part of the deferred REV A1 change set
(`docs/decisions/0010`, `I-032`). If it is ever fitted, the low fuse changes to
**`0x3F`**: `CKSEL = 1111` and `SUT1..0 = 11` — crystal oscillator, 3–8 MHz,
slowly rising power. The high fuse does not change.
