---
status: accepted
date: 2026-09-07
deciders: Zain
---

# Freeze the board at REV A0 and collect hardware changes into REV A1

## Context

A full review on 2026-09-07 found three problems whose fixes touch the board:
a missing crystal (`I-032`), no read-back on the run-permit driver (`I-016`),
and eight silkscreen overlaps plus one dangling via (`I-006`, `I-024`).

The board is already placed, routed, DRC-clean and has Gerbers in
`production/8ch/`. It cost a long session to get there. Nothing in the pipeline
is incremental: `generate_board.py` clears every track, via, zone and drawing,
and `route.py` runs Freerouting from scratch, so **any** board change - even a
silkscreen nudge - means a full regeneration, a fresh route that will not match
the old one, a new DRC run and new Gerbers.

Set against that, none of the three is a defect in what REV A0 does today. The
unit reads eight thermocouples and opens a contact. The crystal matters for
Modbus and for timing determinism; the read-back matters for detecting a failed
relay driver; the silkscreen matters for looks.

## Decision

**REV A0 is frozen.** No agent regenerates the board. The three changes are
collected here as a REV A1 change set, to be applied together in one
regeneration if and when a respin is worth it.

`hardware/8ch/netlist-baseline-reva0.json` records the connectivity REV A0 was
routed from - 167 components, 154 nets, 555 pins. Any schematic edit is checked
against it with `netlist_fingerprint.py`, and a match is the proof that the
board does not need regenerating. That is what allows `I-002` - redrawing the
schematic so a human can read it - to go ahead without touching the PCB.

## The REV A1 change set

Apply all of it at once, or none of it.

### 1. 8 MHz crystal (`I-032`)

`U1` pins 12 and 13 (XTAL1/XTAL2) are unconnected; the ATmega32A runs on its
internal RC oscillator. Add `Y1` (8 MHz, HC-49 or 3225 SMD) with two 22 pF
load capacitors to `GND_CTRL`, close to the pins.

Then in firmware: change `CKSEL` in `firmware/fuses.md` from `0100`
(internal RC 8 MHz) to `1111` with `SUT1..0 = 11` (crystal, 3-8 MHz, slowly
rising power), making the low fuse `0x3F` instead of `0x24`.

### 2. Run-permit driver read-back (`I-016`)

A divider from the `Q1` drain (`RELAY_LOW`, which swings 0 V to +24 V) to
`PC2`, currently `SPARE_PC2`:

- `R53` 22 k from `RELAY_LOW` to a new net `RUN_PERMIT_SENSE`
- `R54` 4.7 k from `RUN_PERMIT_SENSE` to `GND_CTRL`

At +24 V that gives about 4.2 V at the pin - a valid logic high on the 5 V
rail with margin under VCC. Both are `CONTROL` island nets, so the isolation
rules are unaffected.

The firmware is already written and waiting. `hal/run_permit.c` implements the
check; `mcal/board.h` defines `BOARD_HAS_RUN_PERMIT_SENSE`, which is `0`.
**Set it to `1` in the same commit that adds the divider** - not before. On
REV A0 the pin is unconnected and reading it would invent drive faults out of
noise.

JTAG must also be disabled (high fuse `0xD1`, already specified) or `PC2` is
a JTAG pin and reads a constant.

### 3. Silkscreen and the dangling via (`I-006`, `I-024`)

Nine DRC warnings, all cosmetic: six silkscreen overlaps, two silkscreen over
pads, one via on `+3V3_SENS` at (67.80, 25.92) that reaches the plane and
nothing else. They ride along with the respin because they cost nothing once
the board is being regenerated anyway, and are not worth a regeneration on
their own.

## Consequences

**`R-9` (Modbus RTU over RS-485) is deferred.** The ATmega32A's internal RC is
specified to a few percent over voltage and temperature, which is outside what
an asynchronous 8-bit UART frame tolerates. The RS-485 hardware on the board is
complete and correct - `U15` (ADM2587E), termination and bias jumpers, the
isolated island - but a Modbus master will see frame errors that come and go
with panel temperature. `R-9` is not achievable on REV A0 and `docs/GOAL.md`
records it as deferred rather than ready.

**The trip time depends on an RC oscillator.** The calculated worst case is
623 ms against a 1 s requirement (`firmware/include/app/app_config.h`), so
there is margin for the oscillator's drift. It is still a protection device
whose timebase is not a crystal, and that belongs on the record.

**`I-016` stays open.** The unit cannot detect a welded or failed relay driver.

**The prototype is honest about what it is.** REV A0 is an engineering
prototype for bench and site evaluation, not a product build. Freezing it does
not make it more finished than it is; the open issues say what is missing.

## Rejected

**Respin now.** Rejected by the project owner. The board works for what it has
to do next - be built and evaluated - and a respin buys nothing until that
evaluation has happened. Measuring the barrier (`I-004`), the isolated
converter output (`I-003`) and the real trip time (`I-013`) may well produce
more REV A1 changes, and doing one respin that includes those is better than
two.

**Apply only the silkscreen fixes.** Rejected: the regeneration cost is the
same whether one warning is fixed or all nine, and a re-route that nobody
needed is a fresh chance to introduce something worse.
