# Calculations

**Every number this design rests on, with its inputs and its formula.**

Why this file exists: the numbers were being computed and then written into a
sentence inside a `docs/ISSUES.md` row. That row gets closed, the number goes
with it, and the next person re-derives it — or worse, trusts a remembered
version of it. A value with no visible derivation is a value nobody can check.

Rules for this file:

* One section per calculation. Inputs, formula, result, and **what the result
  means** — a number with no verdict is not finished.
* Cite the source of every input: a datasheet page, a standard, or a measurement.
* If a number came from a guess, say so. A guess that looks like a calculation
  is worse than an admitted guess.
* When a value changes, update it here and say what moved. Do not delete the
  old one silently.
* This file does not decide anything. Decisions live in `docs/decisions/`, open
  problems in `docs/ISSUES.md`. This is where they get their arithmetic.

---

## 1. Input supply — LM5164 buck, 24 V battery to 5 V

Source: TI `LM5164` datasheet SNVSAU4D (Feb 2026), section 7.2.2.
Context: `docs/decisions/0016`, `I-028`. The supply is an **engine battery**.

### 1.1 Operating envelope

| | Value | Where from |
|---|---|---|
| VIN nominal | 24 V | engine battery |
| VIN minimum | 6 V | LM5164 recommended operating minimum |
| VIN maximum, sustained | 58 V | ISO 16750-2 Test B, suppressed load dump, 24 V system |
| VIN absolute maximum of the part | 100 V | datasheet 5.1 — **not 105 V; there is no headroom above 100** |
| VOUT | 5.0 V | control rail |
| IOUT design | 0.6 A | 0.425 A load + margin |
| IOUT part rating | 1.0 A | datasheet 5.3 |

5 V load, 0.425 A: `IA0505S` ~265 mA + `ADM2587E` **120 mA** + MCU/LCD ~40 mA.

The ADM2587E figure was an estimate of 100 mA until 2026-09-26. Read then
from its datasheet (`datasheets/ADM2587E.pdf`, Rev. C, table 1): 72 mA typical
into 100 Ohm, 98 mA typical into 54 Ohm (a line terminated at both ends),
**120 mA maximum**, the only maximum given. 120 mA is used here. The design
current of 0.6 A still covers it with 41 % margin. `IA0505S` and MCU/LCD are
still estimates.

### 1.2 Switching frequency — R55 (R_RON)

    R_RON [kOhm] = VOUT x 2500 / F_SW [kHz]            (datasheet eq. 15)

Target 300 kHz gives 41.67 kOhm; nearest E96 1 % is **41.2 kOhm**, so

    F_SW = 5.0 x 2500 / 41.2 = 303.4 kHz

Minimum controllable on-time is 50 ns, so the switching frequency folds back
only above `VOUT / (50 ns x F_SW)` = **330 V** — far outside anything reachable.

On-time across the range:

| VIN | t_ON | duty |
|---|---|---|
| 6 V | 2747 ns | 0.833 |
| 9 V | 1831 ns | 0.556 |
| 24 V | 687 ns | 0.208 |
| 58 V | 284 ns | 0.086 |
| 100 V | 165 ns | 0.050 |

**Verdict:** valid over the whole 6–100 V range.

### 1.3 Output voltage — R56 / R57

    VOUT = V_REF x (1 + R_FB1 / R_FB2),  V_REF = 1.2 V  (datasheet 5.5)

R_FB1 = **158 kOhm**, R_FB2 = **49.9 kOhm**, both E96 1 %:

    VOUT = 1.2 x (1 + 158 / 49.9) = 4.9996 V

**Verdict:** 5.000 V to four figures. V_REF tolerance of ±1.5 % dominates.

### 1.4 Inductor — L1

    dI_L = VOUT / (F_SW x L) x (1 - VOUT / VIN)        (datasheet eq. 18)

L = **33 uH**:

| VIN | dI_L | as % of the 1 A rating |
|---|---|---|
| 12 V | 291 mA | 29 % |
| 24 V | 395 mA | 40 % |
| 58 V | 456 mA | 46 % |

TI asks for 30–50 % at nominal input. Peak inductor current at 0.6 A load and
58 V in is `0.6 + 0.456/2` = **0.83 A**.

**Verdict:** in band across the range. The chosen part is rated 2.2 A with
2.9 A saturation, so saturation margin over the 0.83 A peak is **3.5x**, and it
stays clear of the converter's own current limit, which is what actually has to
be exceeded before saturation matters.

### 1.5 Output capacitance

    C_OUT >= dI_L / (8 x F_SW x V_ripple)              (datasheet eq. 21)

For 0.5 % ripple (25 mV) at the worst-case dI_L of 456 mA: **>= 7.5 uF**.
Fitted: 2 x 22 uF 25 V X7R 1210. Ceramic DC-bias derating at 5 V on a 25 V part
is mild, so the effective value stays well above 7.5 uF.

### 1.6 Type-3 ripple injection — R58, C67, C68

The LM5164 is a constant-on-time converter: it needs ripple at FB to run
stably, and the Type-3 network manufactures that ripple without putting it on
the output.

    C_A >= 10 / (F_SW x (R_FB1 || R_FB2))              (datasheet eq. 24)

`R_FB1 || R_FB2` = 37.92 kOhm, so C_A >= **869 pF**. Chosen **3.3 nF**, which
keeps R_A inside TI's practical 100 kOhm–1 MOhm window.

    R_A x C_A <= t_ON(nom) x (VIN - VOUT) / 20 mV      (datasheet eq. 25)

At 24 V this gives R_A <= 198 kOhm. Chosen **R_A = 150 kOhm**, so
R_A x C_A = 4.95e-4:

| VIN | FB ripple | TI wants >= 12 mV |
|---|---|---|
| 6 V | 5.5 mV | **below** |
| 9 V | 14.8 mV | ok |
| 12 V | 19.4 mV | ok |
| 24 V | 26.4 mV | ok |
| 58 V | 30.4 mV | ok |

**Verdict, and the one soft spot in this design:** at the absolute 6 V floor the
injected ripple is 5.5 mV, under TI's 12 mV minimum, so regulation degrades
there. This is not fixable by trading R_A x C_A — at 6 V in and 5 V out the term
`(VIN - VOUT)` is only 1 V, and buying ripple at 6 V costs DC accuracy at 24 V.
It is accepted because 6 V is the extreme cranking floor, not an operating
point: a 24 V system cranking normally dips to 12–16 V, where there is 19 mV,
and the requirement down there is only that the 5 V rail stays above the 4.0 V
brown-out in `firmware/fuses.md` — not that it regulates well.

DC error from the injected ripple is about half its amplitude, scaled up by the
feedback divider: at 24 V that is 13.2 mV at FB, so **55 mV at the output,
1.10 % high**. Acceptable — every 5 V load on this board takes ±5 % or more.

    C_B >= t_settling / (3 x R_FB1)                    (datasheet eq. 26)

For 75 us settling: >= 158 pF, so **220 pF C0G**. C0G because the coupling
capacitor must not lose value with DC bias.

### 1.7 Input under-voltage lockout — R59 / R60

EN/UVLO thresholds are 1.5 V rising and 1.4 V falling (datasheet 5.5). With
R59 = **33.2 kOhm** on top and R60 = **10 kOhm** on the bottom:

    rising  = 1.5 x (33.2 + 10) / 10 = 6.48 V
    falling = 1.4 x (33.2 + 10) / 10 = 6.05 V

**Verdict:** the converter releases at 6.48 V and holds down to 6.05 V, sitting
right on the part's own 6 V minimum. It rides a cranking dip as far as the
silicon can, and will not chatter on the way down.

### 1.8 Input current — sets what everything upstream must carry

Output 5 V x 0.425 A = 2.13 W at 90 % efficiency gives 2.36 W input.
(Was 2.03 W / 2.26 W with the 100 mA ADM2587E estimate. Re-derived
2026-09-26.)

| VIN | input current |
|---|---|
| 24 V | 98 mA |
| 58 V | 41 mA |

**Verdict:** this unit is a ~100 mA load on a vehicle battery. That is the fact
that makes the whole protection problem cheap, and it is why a series clamp was
a credible alternative before the wide-input regulator won on price — a series
element here only ever has to pass 100 mA, not amps.

### 1.9 External panel fuse — rating and inrush

Context: `docs/decisions/0020`, `I-028` (a).

**Worst steady current.** At the 6.0 V cranking floor (1.1), with the input
power from 1.8:

    2.36 W / 6.0 V = 0.39 A

The relay coil (16.7 mA, section 2) is inside the design current's margin.
A 1 A fuse carries 2.5 times the worst case, and 10.2 times the 98 mA it
carries at 24 V.

**Hot-plug inrush.** When the lead is connected, the input capacitors charge
through the only resistance in the path: `F1`, the wiring and `D1`. The
capacitors on `+24V_PROT` are `C53` 22 uF + `C54` 4.7 uF + `C63` 4.7 uF,
about 32 uF. The energy dissipated charging a capacitor through R from a step V
gives

    I²t = V² C / (2 R)

With V = 28 V (a charging battery) and R = 0.090 Ohm (the REV A2 `F1`,
1812L075/60GR, R min from its datasheet; wiring and diode ignored, so worst
case):

    I²t = 28² x 32e-6 / (2 x 0.090) = 0.139 A²s

(0.084 A²s with the 0.15 Ohm assumed for the REV A1 1206 PTC. Updated
2026-09-28 for `I-068`.)

**Verdict:** a fuse with a pre-arc I²t of 1 A²s or more survives the inrush
with about 7x margin. Time-delay fuses at 1 A are normally well above
that, but **check the chosen part's datasheet**, because pre-arc I²t varies by
maker. The 0.090 Ohm is now read from `F1`'s datasheet
(`datasheets/1812L-PTC.pdf`), not assumed.

---

## 2. Earlier calculations, collected

These were computed between 2026-09-08 and 2026-09-15 and were living inside
`docs/ISSUES.md` rows. Moved here so they survive their issues being closed.
Each still carries its issue number.

| # | Quantity | Result | Verdict |
|---|---|---|---|
| `I-016` | `R53`/`R54` divider, 22 k / 4 k7, `RELAY_LOW` to `PC2` | 4.22 V at PC2; 5.28 V if the input reaches 30 V; 0.9 mA; 17.8 mW = **14 %** of the part rating | pass at 24-30 V, **fails the 58 V load dump** (1.2 mA into the clamp, `I-067`); **superseded by 4.3 (100 k / 22 k)** |
| `I-011` | Input filter corner, differential against common mode | 7.96 kHz differential / 159 kHz common mode = **20x ratio** | pass — the differential signal is filtered and common mode is not folded into it |
| `I-045` | Leakage error at the thermocouple input: BAV199 against a 3.3 V TVS | BAV199 3 pA gives **0.024 degC**; the TVS at 2 uA gives **9.8 degC** | this one number chose the part |
| `I-032` | Crystal load capacitance, 22 pF against `CL_actual = C/2 + C_stray` | **+75 ppm**, against a UART budget of about 20 000 ppm, so **267x inside** | pass — an earlier draft called this a problem; it is not |
| — | `K1` relay coil, G5LE-1 DC24 | 16.7 mA | sets `D3`'s flyback rating: an SMA 1 A part is ample |
| — | RS-485 idle bias | 405 mV | above the 200 mV receiver threshold |
| — | `R32`, LED series resistor | 103 mW in a 250 mW part; 4.7 mA through `D4` | pass |
| `I-028` | `C53` ride-through, 47 uF from 24 V down to 6.5 V | 12.5 mJ; at 2.2 W that is **5.7 ms**. Riding 200 ms would need about 1650 uF | **cranking cannot be solved with a bigger capacitor on this board.** What carries cranking is the regulator's minimum input voltage |
| `I-053` | Terminal-block pitch error, 5.00 against 5.08 mm | 0.08 mm per position; 0.16 mm over 3, 0.24 mm over 4 | moot — the real defect turned out to be the position count, not the pitch |

## 3. Not calculated — open

* **ISO 7637-2 fast transients.** The suppressed load dump is handled, but the
  fast pulses — present on a battery, absent on a panel supply — have not been
  worked through. `D2` `SMBJ60A` clamps at 96.8 V against the LM5164's 100 V
  absolute maximum, which is only **3.2 V of margin**, and the negative pulses
  are not covered at all by a unidirectional clamp sitting behind a 100 V
  series Schottky.
* **Isolation barrier**, `I-004` — never verified electrically.
* **Thermal**, **EMC** and **SPICE** — nothing run.

## 4. REV A2 — the pre-fabrication review's fixes (2026-09-28)

Context: `docs/decisions/0022`. Datasheets in `docs/reference/datasheets/`.

### 4.1 `Q1` — BSS131 against the battery rail (`I-066`)

**Voltage.** With the relay off, the drain sits at `+24V_PROT` through the
coil; D3 holds a coil flyback to one diode drop above that rail. The
highest the rail gets is D2's clamp: SMBJ60A, 96.8 V at 6.2 A.

    BSS131 V(BR)DSS 240 V min (datasheet p2) / 96.8 V = 2.48x
    2N7000        60 V                            < 66.7 V, D2's minimum breakdown

**On state.** Coil 16.7 mA (section 2). RDS(on) is at most 20 Ohm at
VGS = 4.5 V and ID = 90 mA (p2):

    drop = 16.7 mA x 20 Ohm = 0.33 V;   coil sees 23.7 V > 18 V must-operate
    P    = 16.7e-3² x 20    = 5.6 mW    (360 mW rating)

**Gate.** VGS(th) is 0.8-1.8 V at 56 uA. The AVR drives about 5 V through
`R30` (100 R), and `R31` (100 k) holds 0 V in reset. So the gate sees 3.2 V
of overdrive above the maximum threshold, and 0.8 V of margin below the
minimum threshold when off.

**Verdict:** pass. ESD Class 0 (<250 V HBM): handle with ESD care at assembly.

### 4.2 `R61` — ISP series resistor on U11's MISO output (`I-065`)

**Contention during ISP.** The AVR drives MISO against U11 OUTF, and U11 can
sit at either rail:

    I = 5 V / 2.2 k = 2.3 mA   against the ISO7761's recommended |IOH|, |IOL| of 4 mA at 5 V
    (1 k would be 5.0 mA - over the recommendation, which is why 2k2)

**Normal operation.** SPI runs at F_CPU/16 = 500 kHz (`mcal/spi.c`: SPR0,
8 MHz), so a half period is 1 us:

    tau = 2.2 k x ~15 pF (AVR pin + trace) = 33 ns    = 3 % of the half period
    ISO7761 propagation delay 11 ns typical           (datasheet)

**LOW level against the AVR's MISO pull-up.** The firmware enables PB6's
internal pull-up, which is 20-50 k (ATmega32A). The worst case is 20 k:

    VIL = 5 V x 2.2 / (2.2 + 20) = 0.50 V   < 0.3 x VCC = 1.5 V

**Verdict:** pass on all three.

### 4.3 `R53`/`R54` — run-permit read-back at 100 k / 22 k (`I-067`)

Replaces the 22 k / 4 k7 row in section 2.

| `RELAY_LOW` | PC2 (open circuit) | Note |
|---|---|---|
| 24 V | 24 x 22 / 122 = **4.33 V** | valid high |
| 28.8 V (charging) | **5.19 V** | below VCC + 0.5 V, so no clamp current |
| 58 V (load dump) | 10.46 V behind 100 k // 22 k = 18.0 k | clamp takes (10.46 - 5.5) / 18.0 k = **0.28 mA** |
| 16.6 V | 3.0 V = 0.6 x VCC | the lowest supply that still reads a valid high |

With 22 k / 4 k7 the same dump gave 58 x 4.7 / 26.7 = 10.2 V and
(58 - 5.5) / 22 k - 5.5 / 4.7 k = **1.2 mA** into the clamp, against the
~1 mA of Microchip AVR182. The lowest valid-high supply was 17.0 V.

    divider current at 58 V: 58 / 122 k = 0.48 mA;  P(R53) = 0.48e-3² x 100 k = 23 mW  (125 mW part)
    leakage error:           1 uA x 18 k = 18 mV   (negligible)

**Verdict:** pass. The read-back is valid over the same range as before and
now survives the design-basis load dump.

### 4.4 `F1` — 1812L075/60GR (`I-068`)

From the datasheet (`datasheets/1812L-PTC.pdf`, LUTE): V max 60 V, I max 40 A,
I hold 0.75 A / I trip 1.50 A at 25 °C, 0.20 s to trip at 8 A, R min
0.090 Ohm, R1 max 0.500 Ohm.

**Hold current against temperature** (the datasheet's derating table, 0.75 A
row), against the 0.39 A cranking-floor load of 1.9:

| Ambient | 25 °C | 40 °C | 50 °C | 60 °C | 70 °C | 85 °C |
|---|---|---|---|---|---|---|
| I hold | 0.75 | 0.63 | 0.57 | 0.49 | 0.45 | 0.35 A |
| holds 0.39 A? | yes | yes | yes | yes | yes | **no** |

At 24 V the load is 98 mA, so the part holds at every rated temperature. For
comparison, the same series' 0.5 A row is 0.35 A at 60 °C.

**Voltage drop** at the cranking floor: 0.39 A x 0.5 Ohm (R1 max) = 0.20 V.

**Voltage rating:** 60 V against the 58 V suppressed load dump, the design
basis of `0016`. The margin is 2 V, and anything above the design basis is
outside every part in the input stage, not only this one.

**Faults between hold and trip.** After the regulator, the LM5164's peak
current limit of 1.25-1.75 A at 5 V (datasheet 6.3.6) caps a fault at about
8.75 W, which is at most ~0.4 A from 24 V. So those faults never reach F1.
Before the regulator, the parts that can fail are D2, C53, C54 and C63, and
they fail towards a short, which trips F1 and the panel fuse.

**Inrush:** 1.9, re-computed with this part's R min: 0.139 A²s.

**Verdict:** pass up to a 70 °C panel ambient. **The panel's maximum ambient
has not been measured**; if it can exceed 70 °C, look again.

## 5. Pre-order review, 2026-09-29 — additional limits

These checks supplement prior calculations; they do not qualify an assembled
unit. No hardware values were changed. Source evidence is in
`production/review-20260929/` and issues I-075 through I-080.

### 5.1 Battery-connected relay and indicator (I-077)

Inputs: accepted design-basis rail excursion 58 V (`0016`); G5LE-1 DC24
coil 1440 ohm +/-10%, 24 V nominal, maximum applied coil voltage 170% at
23 C. Manufacturer: https://www.fa.omron.co.jp/product/item/G5LE-1_DC24/ .
R32 is 4.7 kohm, RK73H2ATTD4701F, 0.25 W per KOA RK73H data sheet
(https://www.koaspeer.com/pdfs/RK73H.pdf). Assume LED drop 2 V and neglect
Q1/series-path voltage drop for this screening calculation.

    maximum specified coil voltage at 23 C = 1.70 x 24 = 40.8 V
    58 / 24 = 2.42 times nominal coil voltage
    coil steady resistive power at 24 V = 24^2 / 1440 = 0.400 W
    coil steady resistive power at 58 V = 58^2 / 1440 = 2.34 W
    R32 at 24 V = (24 - 2)^2 / 4700 = 0.103 W
    R32 at 58 V = (58 - 2)^2 / 4700 = 0.667 W = 2.67 x 0.25 W

**Verdict:** normal nominal-rail operation and transient survival are different
claims. The coil exceeds its published applied-voltage envelope and R32
exceeds its continuous power rating during the assumed excursion. Coil
inductance, pulse duration, temperature and repetition matter; these numbers
do not prove a particular pulse burns either part. A pulse-survival check or
protection change is required; the 100 V buck and 240 V Q1 do not settle it.

**Weight agreed 2026-10-01 (I-077 → low):** the excursion is the ~350 ms load
dump. The coil's thermal time constant is seconds, so its temperature cannot
follow 2.34 W for 350 ms. R32's 0.67 W for 350 ms is inside the short-time
overload that thick-film chips are normally rated for (typically 2.5x rated for
seconds). That rating is not yet read from KOA's datasheet. So this is
"unqualified on paper", not "expected to fail".

### 5.2 U14 thermal vias and routed geometry (I-075/I-076)

Inputs: six actual vias with 0.6 mm pads, 0.4 mm drills in native board
analysis and released Excellon, versus decision 0023's 0.3 mm drills.

    actual nominal annular ring = (0.6 - 0.4) / 2 = 0.10 mm
    intended nominal annular ring = (0.6 - 0.3) / 2 = 0.15 mm

**Verdict:** manufacturing DRC passes; this is a mismatch to the accepted
assembly detail, not proof the fabricator cannot make it. Larger open holes
increase the solder-wicking concern below the exposed pad. Assembler review
of paste/via treatment is required. TI PowerPAD guidance:
https://www.ti.com/lit/an/slma002g/slma002g.pdf .

Route lengths below were computed by summing connected track centreline
lengths between pad centres in `pcb.json` (Euclidean segment length
sqrt(dx^2 + dy^2)); they exclude ground-plane return paths:

| Path | Routed length | Direct pad-centre distance |
|---|---:|---:|
| U14.2 VIN to C54.1 | 12.129 mm | 7.343 mm |
| U14.2 VIN to C63.1 | 19.466 mm | 4.869 mm |
| U14.8 SW to L1.1 | 9.404 mm | — |
| U14.7 BST to C62.1 | 8.940 mm | — |
| U14.5 FB to R56.2 | 8.440 mm | — |

**Verdict:** native `regulator-copper.png` confirms the detours; this is a
layout risk assessment, not a calculated oscillation or temperature. Compare
against TI LM5164 section 7.4's compact loop/wide trace guidance, then verify
the corrected layout physically. https://www.ti.com/lit/ds/symlink/lm5164.pdf .

**After the fix (2026-10-01, `0026`), measured from the board:**

| Path | Before | After |
|---|---:|---:|
| U14.2 VIN to C63.1 | 19.466 mm | **3.53 mm** (one straight 0.8 mm track, y 109.36) |
| U14.2 VIN to C54.1 | 12.129 mm | **7.03 mm** (same track) |
| U14.8 SW to L1.1 | 9.404 mm, 0.2 mm sections | **5.98 mm**, one 1.0 mm track |
| U14.7 BST to C62.1 | 8.940 mm | **3.02 mm**, 0.4 mm |

Thermal vias under U14: 6 x 0.3 / 0.6 mm (ring 0.15 mm), confirmed in the
exported `.drl`. Board minimum ring is now 0.15 mm everywhere (was 0.10 on 41
vias). Still a geometric result; the bench measurement is open (I-076).

### 5.3 Conditional external-voltage fault at a TC terminal (I-080)

Inputs: 24 V accidentally applied to an input with a return to GND_SENS;
100 ohm / 0.125 W series resistor; assumed clamped 3.3 V rail and 0.7 V
diode drop. This assumption only estimates initial stress; the rail has no
dedicated shunt and may rise.

    current = (24 - 3.3 - 0.7) / 100 = 0.20 A
    series-resistor power = 0.20^2 x 100 = 4.0 W
    overload relative to continuous rating = 4.0 / 0.125 = 32 times

**Verdict:** do not claim 24 V miswire survival from MAX31856 input ratings.
Actual current depends on fault return, clamp behaviour and rail movement;
this scenario can threaten the shared sensor supply. It is not a normal
technician acceptance test or an assumed fault requirement.

**Weight agreed 2026-10-01 (I-080 → low):** not a design requirement unless the owner asks for miswire tolerance.

### 5.4 Sensor-island normal-load estimate

Inputs from MAX31856 and ISO7760/61 data sheets: eight converters at 2 mA
maximum each; sensor-side isolator current estimates 5.7 and 6.9 mA at the
1 Mbps/DC table conditions; one selected 10 kohm CS pull-up at 3.3 V.
Actual SPI is 500 kHz; mixed supply voltages/capacitive loading are not
measured. This estimate does not replace the previous whole-board budget.

    load estimate = 8 x 2 + 5.7 + 6.9 + 3.3 / 10 = 28.93 mA
    LDO at assumed 6 V input: (6 - 3.3) x 0.02893 = 0.078 W
    illustrative junction rise at 205.4 C/W = 0.078 x 205.4 = 16 C

**Verdict:** useful normal-current margin against LP2985's 150 mA and the
IA0505S positive output's 100 mA. Not a bound on module no-load voltage,
board temperature, effective C48 capacitance or complete-system thermals.

### 5.5 Corrected system capacity — sizing limits, not a selected design

Inputs: owner clarified 24 thermocouples (decision 0024); current board and
`HAL_TEMPERATURE_BANK_CHANNELS` implement eight; current outline from
`board/config.py` is 250 x 140 mm.

    number of eight-channel acquisition modules = 24 / 8 = 3
    terminal positions if existing T+/T-/shield interface is retained = 24 x 3 = 72

**Verdict:** three acquisition modules cover the count but do not establish a
working network, master, shutdown grouping or system qualification. The current
outline is not an optimized minimum and a new 24-channel board is not assumed
to need three times its area. No 24-channel outline, layer requirement, total
power budget or cost ratio is calculated without a placement/interface study.

## 6. REV A3 planning, 2026-10-08 (`decisions/0030`)

### 6.1 BIAS fight between grounded probes on one island

Inputs: MAX31856 V_BIAS 0.735 V and R_BIAS 2 kOhm, **both typical only, no
min/max** (datasheet p.3); R1-R16 = 100 Ohm per leg; K-type ~41 uV/degC
(section 2). Cable resistance is not known and is left out (it adds to r).

With grounded probes the engine joins every T- line. BIAS current then
flows through each negative leg; the positive leg carries almost none, so
the error is the drop across the negative leg's resistance r.

Two channels, mismatch dV:

    I = dV / (2 R_BIAS + 2 r) = 10 mV / 4.2 kOhm = 2.4 uA
    error = I x r = 2.4 uA x 100 Ohm = 0.24 mV  ->  ~5.8 degC

Eight channels, one source 10 mV above seven equal ones. The engine node
sits near the average:

    I = (7/8 x 10 mV) / (R_BIAS + r) = 8.75 mV / 2.1 kOhm = 4.2 uA
    error = 4.2 uA x 100 Ohm = 0.42 mV  ->  ~10 degC

**Verdict:** degrees of error per 10 mV of mismatch, of **either sign**, so
it can read low. The real mismatch is unknown, because the datasheet gives no
spread. Potential differences between points on the engine block enter the
same network. This is a first-order model, not a measurement. Nothing here
can damage a part: the currents are microamps. **Fix:** `0030` D6.

The `0008` table had two errors. It assumed a ~250 Ohm loop and ignored
R_BIAS, and it wrote 4 uA x 100 Ohm as 0.4 uV; the product is 400 uV.

### 6.2 Panel fuse with three modules on one feed

Section 1.9 gives 0.139 A²s for one module charging its ~32 uF through its
own F1. Three identical modules switched on together, each through its own
F1, draw three times the current at every instant:

    I²t_total = ∫(3 i)² dt = 9 x 0.139 = 1.25 A²s

**Verdict:** above the >= 1 A²s pre-arc floor that `0020` set for one module.
Choose either a fuse with pre-arc I²t of 10 A²s or more, or one fuse per
module. Wiring resistance lowers the real figure; this is the idealized
upper bound.

---

## 7. One 24-channel board (decisions/0031), 2026-10-08

Context: `0031`, I-096/I-102. Candidate budget, **not qualification**.
For this architecture, this section replaces the estimates in 1.1/1.8,
5.4/5.5 and the three-module fuse case in 6.2; their history is retained.
Topology and existing capacitor values were read from REV A2
`hardware/8ch/power.kicad_sch` and `isolation.kicad_sch`.
“Worst” below means the stated screening envelope, including assumptions;
it is not a guaranteed sum of manufacturer maxima. No parts are selected here.

### 7.1 Island load and isolated converter (T4)

AD7124-8 full power, gain 16-128 (covers PGA operation), internal reference,
diagnostics on, excitation/VBIAS off; analog input buffers are already included.
Source: [ADI AD7124-8 Rev F, Table 3 pp.9-10, notes 11/13](https://www.analog.com/media/en/technical-documentation/data-sheets/ad7124-8.pdf).
Internal-reference operation does **not** require the two reference buffers.

    each ADC typ = (875 analog + 55 digital + 50 reference + 4 diagnostics) uA = 0.984 mA
    each ADC max = (1200 + 80 + 70 + 5) uA = 1.355 mA

| 3.3 V load | Typ, mA | Worst, mA | Input/source |
|---|---:|---:|---|
| 3x AD7124-8 | 2.952 | 4.065 | 3 x above; static digital-current test conditions |
| ISO7760 + ISO7761 secondary | 7.100 | 12.600 | Local ISO776x Rev H, 5.12 p.15: 1 Mbps ICC2 typ 3.4 + 3.7; maximum of AC/DC cases 5.7 + 6.9 |
| Up to 3 terminal CJ sensors | 0.900 | 1.500 | Assumed 3 x 0.3 / 0.5 mA; part not chosen |
| Selected CS pull-ups | 0.990 | 1.100 | Assumed 3 simultaneous 10 kOhm pull-ups: 3 x 3.3/10 k; worst 3.465 V / 9.5 kOhm |
| Bias, independent reference check, digital activity allowance | 0.100 | 1.000 | Assumed allocation; high-value TC bias alone is negligible |
| Burnout slot | 0.012 | 0.015 | Assumed 4 uA source per ADC, three banks concurrently; 15 uA allowance; no duty-cycle credit |
| **3.3 V total** | **12.054** | **20.280** | Sum |
| LP2985 ground/enable current, added at module output | 0.350 | 1.000 | Conservative proxy from 50 mA row, including enable allowance; actual load is lower |
| **Module output current** | **12.404** | **21.280** | LDO input = output load + ground/enable current |

Isolators: local `ISO7760.pdf`/`ISO7761.pdf`, Rev H pp.13/15.
Assume 500 kHz SPI, <=15 pF/output, unused inputs held at valid rails.
Tables specify equal supplies; using ICC1 at 5 V and ICC2 at 3.3 V for the
mixed-supply board is an estimate. DC LOW costs more than DC HIGH; an
all-HIGH idle island gives only about 11.2 mA at the module output.

Module model used: **MORNSUN B0505S-1WR3 single-output**, not the fitted
XP IA0505S dual-output. [B_S-1WR3, 2026.09.07-A/7, pp.1-4](https://www.mornsun-power.com/public/uploads/pdf/B_S-1WR3.pdf):
200 mA max/**20 mA min**, 1 W, 78/82% full-load efficiency,
8 mA typical no-load input (no maximum), load regulation specified at
10-100% load. Its typical light-load curve is about 75% at 10% load.
The older [manufacturer explanation](https://www.mornsun-power.com/html/news-detail/blog-posts/217.html)
also says >75% at 10%, but quotes 5 mA no-load; use the newer 8 mA figure.

    loading at nominal 5 V = 12.404/200 = 6.2% typ; 21.280/200 = 10.6% worst
    assume module output 5.5 V typ / 6 V screening high
    assume effective efficiency 65% typ / 50% worst below/near minimum load
    I5_in = max(I_no-load, Viso x Iiso / (V5 x efficiency))
    typ = max(8, 5.5 x 12.404 / (5 x 0.65)) = 21.0 mA -> budget 22 mA
    worst = max(15 assumed, 6 x 21.280 / (4.75 x 0.50)) = 53.8 mA -> budget 55 mA

Effective efficiency includes idle losses: **do not add 8 mA again**.
Neither efficiency below 10% load nor the 6 V ceiling is guaranteed.
Capacity is ample, but **minimum loading fails in typical and idle operation**.
Require a module specified at the actual minimum load, or guaranteed loading
>=20 mA across reset/idle/RUN. An illustrative separate 20 mA preload at the
module output adds <=51 mA to the 5 V budget and <=0.12 W locally at 6 V;
it is not fitted or selected. Put that load upstream of the LDO when assessing
the following thermal numbers. The actual IA0505S needs its own dual-output/
cross-regulation check; these MORNSUN figures cannot qualify it.

LP2985IM5X-3.3/NOPB is covered by
[TI LP2985-N Rev AB, pp.4-6](https://www.ti.com/lit/ds/symlink/lp2985-n.pdf).
Local `LP2985.pdf` could not be decoded (damaged PDF), so use that manufacturer
source: 150 mA, 16 V input, legacy 50 mA dropout <=225 mV over temperature,
ground current 350 uA typ / 900 uA max at 50 mA; thetaJA 205.4 C/W.
Require Viso >=3.465 + 0.225 = **3.69 V**, using assumed +/-5% island rail.
At assumed 4.5 V module minimum there is 0.81 V margin.

    P_LDO = (Viso - 3.3) x I3V3 + Viso x Iground
    typ = (5.5 - 3.3) x 0.012054 + 5.5 x 0.000350 = 28.4 mW
    worst screening = (6 - 3.3) x 0.020280 + 6 x 0.001 = 60.8 mW
    illustrative junction rise = 0.0608 x 205.4 = 12.5 C

**Verdict:** LDO current, dropout and dissipation are comfortable within these
assumptions (85 C ambient -> about 98 C junction, below 125 C). I-003 stays
open: measure startup, idle and running Viso; 6 V is a screening point,
not a verified maximum. LDO output-capacitance/ESR compliance remains necessary.

### 7.2 5 V budget and battery current (T1)

| Control-rail load | Typ, mA | Worst, mA | Formula/source |
|---|---:|---:|---|
| ATmega1284P-AU, 8 MHz | 8.0 | 20.0 | Core 5.6 typ / 9 max at 5 V with peripherals disabled: [Atmel-42719C, Table 29-3 p.411, peripheral increments pp.428-429](https://ww1.microchip.com/downloads/en/DeviceDoc/Atmel-42719-ATmega1284P_Datasheet.pdf); totals are assumed oscillator/peripheral/I/O allowances |
| LCD backlight + logic | 126.5 | 183.0 | Assumed 125 + 1.5 typ, 180 + 3 worst; see resistor below |
| ADM2587E, transmitting | 98.0 | 150.0 | Local Rev C Table 1 p.3: 98 typ at 54 Ohm; 150 is an **assumed allowance**, not its specified max |
| ISO7760 + ISO7761 primary | 9.7 | 22.0 | Local Rev H 5.10 p.13: 1 Mbps 5.0 + 4.7 typ; all-LOW DC max 11.3 + 10.6 rounded up |
| Island DC-DC input | 22.0 | 55.0 | 7.1, includes all island loads and LDO ground current |
| Two LEDs | 4.0 | 5.0 | Assumed 2 mA each; 1.5 kOhm, 2 V LED drop gives (5-2)/1500; allowance covers 5.25 V, 1.8 V, -5% R |
| Control pull-ups, LCD contrast, buck feedback, buttons | 2.0 | 5.0 | Assumed aggregate allocation; negligible button load except pull-ups |
| **Total, two-ended terminated bus** | **270.2** | **440.0** | Sum; both columns assume continuous transmission |

LCD screening proposal: **12 Ohm +/-5%, >=0.5 W** in series with a bare
backlight assumed Vf = 3.5 V typ, >=3.2 V worst. Ityp = (5-3.5)/12 =
125 mA; Iworst = (5.25-3.2)/11.4 = 180 mA; resistor worst dissipation =
(5.25-3.2)^2/11.4 = 0.369 W. Verify brightness, Vf and any built-in resistor
on the locally bought module; the existing 220 Ohm R29 does not establish
this current. Assumed rails: 5 V +/-5%, 3.3 V +/-5%.

ADM2587E correction to 1.1: **120 mA max is specified at 120 Ohm**, not at
54 Ohm. A single termination can use 72 mA typ at the datasheet's 100 Ohm
test load as a conservative proxy for 120 Ohm: total **244.2 mA typ**.
No local termination can still leave a far-end termination. A completely
unterminated/receive-only bus draws less; no unverified saving is credited.
At a single 120 Ohm load, replacing the 150 mA allowance by the published
120 mA gives **410 mA** total. Two 120 Ohm ends are nominally 60 Ohm; 54 Ohm
is the standard heavier test load. Never add termination current on top of
these already-loaded input figures.

Use the **efficiency method of 1.8**: Iin = V5 x I5 / (efficiency x VIN).
Assume 90% typ (as 1.8), 85% worst; not guaranteed efficiency minima.

| Battery/VIN idealized | Buck input typ, mA (5 V, 270.2 mA) | Buck input worst, mA (5.25 V, 440 mA) |
|---|---:|---:|
| 9 V | 166.8 | 302.0 |
| 24 V | 62.5 | 113.2 |
| 32 V | 46.9 | 84.9 |

G6K-2F-Y DC24: [Omron G6K K106-E1, ratings p.2](https://components.omron.com/us-en/system/files/2026-05/datasheet_pdf/K106-E1.pdf)
gives 4.6 mA, 5220 Ohm +/-10% at 23 C; “approx.100 mW” is a family figure.
Actual nominal resistive power is 24^2/5220 = **110 mW per coil**.
Typical RUN uses one coil; screening worst permits both energized.

    two coils worst at 32 V = 2 x 32/(0.9 x 5220) = 13.62 mA
    per coil worst power at 32 V = 32^2/(0.9 x 5220) = 218 mW
    per coil at 58 V = 58^2/(0.9 x 5220) = 716 mW

These are battery loads, not buck-output loads. Coil cold resistance below
23 C is not bounded here. Datasheet 150% maximum is instantaneous, with a
note to apply rated voltage only: **32 V continuous is not established**;
5.1's G5LE pulse discussion cannot qualify a G6K load dump.

For upstream sizing include both coils, 2 mA assumed battery-side dividers/
auxiliaries, assumed D1 drop 0.5 V and F1 R1max 0.5 Ohm (4.4).
Solve Ibat = P5/[0.85 x (Vbat-0.5-0.5 Ibat)] + 2 Vbat/4698 + 0.002.
A **0.50 A 5 V design envelope** covers 440 mA plus the illustrative
51 mA module preload; this reserve does not select that mitigation.

| Battery | Whole-board worst, 440 mA rail | With 0.50 A rail envelope | 1 A fuse / envelope |
|---|---:|---:|---:|
| 9 V | 0.332 A | 0.377 A | 2.65x |
| 24 V | 0.128 A | 0.144 A | 6.94x |
| 32 V | 0.102 A | 0.114 A | 8.78x |

**Verdict:** the isolated converter is ~22/55 mA here, not ~265 mA.
I-096's old load was inflated, but the new LCD and fitted RS-485 bring this
candidate back to **0.270 A typ / 0.440 A screening worst**; do not carry
the old “real ~0.22 A” estimate into this architecture.

### 7.3 LM5164 / L1 / F1 adequacy (T2)

LM5164 local SNVSAU4D pp.4/6: 1 A output; peak current limit
1.25-1.75 A. At the 0.50 A design envelope there is 2x output-current
capacity. Reuse 1.4: dIL = Vout/(f L) x (1-Vout/VIN).
Screen with Lmin = 33 x 0.8 = 26.4 uH and fmin = 270 kHz
(**assumed tolerance bounds**, nominal f = 303.4 kHz from 1.2).

| VIN | dIL at 5.25 V | Peak = 0.50 + dIL/2 | RMS = sqrt(0.50^2 + dIL^2/12) |
|---|---:|---:|---:|
| 9 V | 0.307 A | 0.653 A | 0.508 A |
| 24 V | 0.575 A | 0.788 A | 0.527 A |
| 32 V | 0.616 A | 0.808 A | 0.531 A |
| 58 V | 0.670 A | 0.835 A | 0.536 A |

**L1 verdict:** 33 uH remains suitable; 2.2 A thermal rating is generous
(4.1x the 0.536 A screen), not required by this operating load.
A replacement would need thermal capability above **0.54 A RMS plus
temperature margin**, and saturation capability above the **1.75 A maximum
converter limit plus tolerance/delay margin**, not merely above 0.835 A.
The existing 2.9 A saturation claim in 1.4 was not independently verified
from an L1 datasheet. Do not reduce inductance just because DC load fell.

**F1 verdict:** 4.4's verified hold currents are 0.49 A at 60 C, 0.45 A at
70 C and 0.35 A at 85 C. The 9 V envelope is 0.377 A: adequate through
70 C with **19% hold-current margin**, but not at 85 C. At nominal 24 V
there is 3.12x margin even at 70 C. No current-based case for downsizing F1
across the full cranking/temperature requirement: the 0.5 A row holds only
0.30 A at 70 C.

At a *protected buck VIN* of 6 V, the envelope needs
5.25 x 0.50/(0.85 x 6) + about 5 mA coils/auxiliaries = **0.520 A**.
That exceeds F1's 60/70/85 C hold values; it holds at 50 C (0.57 A).
A 6 V *battery* cannot provide regulated 5 V through D1/F1: UVLO and the
1.6 ripple limit still apply. Near-floor hold-up is therefore not proven.
Requirement for any revised PTC: hold >0.52 A at the specified maximum
ambient, with agreed margin (25% would require >=0.65 A there); retain
>=58 V design-basis voltage capability and coordinate with the panel fuse.
The present 60 V rating still has only 2 V load-dump margin.

**Chain verdict:** sufficient for the stated 9-32 V / <=70 C envelope;
thermal/noise measurements and actual efficiency remain open. The enlarged
board does not require a higher-current buck or L1. F1's hot cranking limit
needs the operating envelope settled before any rating reduction.

### 7.4 One-board panel fuse and inrush (T3)

Direct battery capacitance remains **31.4 uF**: C53 22 + C54/C63 4.7 each.
Assume +20% upper capacitance: 37.68 uF. C64/C65 are **output-side**;
do not add them directly to battery capacitance.
Use 1.9's RC step method and F1 Rmin = 0.090 Ohm (local PTC p.3).

    I2t_input = Vbat^2 x Cin/(2 R)
    28 V nominal C: 28^2 x 31.4e-6/(2 x 0.090) = 0.137 A2s
    32 V, +20% C: 32^2 x 37.68e-6/(2 x 0.090) = 0.214 A2s

Wiring/diode impedance is omitted, as in 1.9. Rmin is a 25 C datum;
using it as a minimum for cold hot-plug is an assumption, not certification.

Downstream startup inventory (assumed +20% ceilings, ceramics not credited
with DC-bias reductions):

| Rail | Nominal C | Upper C | Basis |
|---|---:|---:|---|
| 5 V control | 100 uF | 120 uF | C64/C65 44 + C55 10 + DC-DC input C45 10 + assumed 36 for ADM/MCU/LCD/bypass additions |
| Unregulated island | 11 uF | 13.2 uF | C46 10 + LP2985 input C47 1 |
| 3.3 V island | 10 uF | 12 uF | C48 4.7 + assumed 5.3 for new ADC/CJ/reference decoupling |

    stored downstream energy = 0.5 x (120u x 5.25^2 + 13.2u x 6^2 + 12u x 3.465^2)
                             = 1.96 mJ

Converters prevent treating this as a direct battery RC pulse; stored energy
alone does not determine fuse I2t. LM5164 soft-start is 1.75-4.75 ms
(local p.6). Assume **one successful startup within 20 ms**, including
island startup, no repeated hiccup/restarts. Conservatively give the panel
the full 1.75 A switch-current ceiling continuously, without duty-cycle
credit, plus 0.02 A for battery branches. Thus:

    I2t_start <= 1.77^2 x 0.020 = 0.0627 A2s
    overlapping pulses: I2t_total <= (sqrt(I2t_input) + sqrt(I2t_start))^2
                                    = (sqrt(0.214) + sqrt(0.0627))^2 = 0.509 A2s

The overlap inequality avoids simply adding pulses that could coincide;
the startup allowance includes downstream loads/capacitor charging.
It assumes no additional path bypasses the buck current limit and ignores
unbounded switching overshoot. These are screening bounds to verify at bench.

**Verdict:** **0020 stands for one board**, conditionally: 1 A time-delay,
>=80 V DC, >=10 kA DC interrupt rating, and verified pre-arc I2t >=1 A2s.
Steady margin is 2.65x at 9 V with the 0.50 A rail reserve; the idealized
6 V protected-input envelope is still only 0.520 A. Inrush screening margin
is **1/0.509 = 1.96x** at 32 V including assumed downstream startup.
6.2's 9x multiplier and 1.25 A2s three-module result no longer apply.
Select the exact fuse/holder against DC voltage, prospective battery fault
current, temperature derating and repetitive-pulse limits; no fuse part is
qualified by “time-delay” alone.

### 7.5 Unverified inputs, ranked by effect (T5)

1. **Island supply choice/minimum loading:** MORNSUN is a calculation model,
   not an IA0505S substitute approval. Below-minimum-load output, startup
   overshoot and mixed/reset loads are unbounded; 4.5/5.5/6 V screening,
   65/50% effective efficiency and 15 mA no-load ceiling are assumed.
   A separate 20 mA preload is illustrative; no mitigation is selected.
2. **LCD:** exact module, bare/built-in backlight resistance, Vf 3.5/>=3.2 V,
   useful brightness at 125 mA, logic 1.5/3 mA, and resistor +/-5%/thermal
   behaviour. This dominates the uncertain continuous load.
3. **Startup/fuse:** 20 ms successful startup, no hiccup/repeat pulses,
   1.77 A input ceiling without overshoot, R_F1 >=0.090 Ohm at cold ambient,
   capacitance +20% bounds and added 36/5.3 uF. Exact fuse pre-arc I2t,
   derating, DC interrupt/holder ratings and prospective short current unverified.
4. **Battery/temperature envelope:** 9-32 V sustained, actual minimum at buck
   pins, maximum panel ambient, D1 0.5 V drop, 90/85% buck efficiency and
   the retained suppressed 58 V load-dump basis. F1 can fail the hot
   near-floor hold requirement; neither 6 V battery regulation nor fast
   transient survival is established.
5. **RS-485 operating condition:** termination/topology and transmit duty
   unknown; 150 mA at double termination is an allowance with no specified
   manufacturer maximum. A no-termination saving is not credited.
6. **G6K coil environment:** both-on state is a screening case; resistance
   tolerance is specified at 23 C, not the minimum cold temperature.
   Continuous 32 V and 58 V pulse survival require a separate check.
7. **Isolators/rails/L1:** mixed 5/3.3 V current-table use, <=15 pF outputs,
   valid unused-input levels and 500 kHz SPI; +/-5% rails; L >=26.4 uH,
   f >=270 kHz and L1 saturation/thermal derating. These are not measured.
8. **MCU and auxiliary loads:** 8/20 mA MCU total; 2/5 mA control auxiliaries,
   1/2 mA battery auxiliaries; two ~2 mA LEDs with assumed Vf/R tolerances.
   Final GPIO/oscillator/peripheral configuration is not fixed.
9. **Front-end additions:** three CJ sensors at 0.3/0.5 mA, three selected
   10 kOhm pull-ups, 4 uA burnout source/15 uA combined allowance,
   0.1/1 mA bias/independent-reference/digital allocation. New protection,
   engine-reference current and CJ parts must fit that allowance.
10. **LDO implementation:** 0.35/1 mA ground/enable allowance uses a higher-load
    proxy; output ESR/effective capacitance, package copper and actual
    junction rise are unverified. A module-output preload was assumed
    upstream of the LDO; placing it on 3.3 V changes LDO dissipation.

**Handoff:** W1 to carry these conditional verdicts into I-096/I-102/STATE
and the component/operating-envelope decisions. No hardware, firmware,
issue, state or decision file was changed for this calculation.

### 7.6 W1 addendum: changes from `0032` revision 1 (2026-10-08)

Inputs: G6K-2F-Y DC5 coil ~100 mW nominal (Omron family figure; exact
resistance to read from K106-E1 before the schematic), island preload 270 ohm.

    two DC5 coils on 5 V   = 2 x 0.100 W / 5 V           = 40 mA (was 13.6 mA from the battery)
    preload at module out  = 5.5 V / 270 ohm              = 20.4 mA, 0.11 W
    preload seen at 5 V    = 5.5 x 20.4 / (5 x 0.65)      = 34.5 mA (7.1 efficiency model)
    new 5 V worst          = 440 + 40 + 34.5              = 515 mA (> 0.50 A envelope by 3 %)
    battery at 9 V, worst  = 5.25 x 0.515 / (0.85 x 8.0)  = 0.398 A (8.0 V after D1/F1 drops, 7.2)

Verdict: LM5164 (1 A) and L1 unchanged. F1 hold 0.45 A at 70 degC still covers
0.40 A at 9 V; the envelope should be restated as **0.52 A** and the PTC
requirement in 7.3 (> 0.52 A hold at max ambient for a 6 V protected input)
stands. The DC24 coils no longer load the battery directly.

**7.6 update (`0032` revision 2):** the preload moves to the 3.3 V rail,
150 ohm: 3.3 / 150 = 22.0 mA, 73 mW. Module output becomes 12.4 + 22.0 =
34.4 mA typ (17 % load) and 21.3 + 22.0 = 43.3 mA worst. With assumed 70 %
typ / 60 % worst efficiency at that load: 5.5 x 34.4 / (5 x 0.70) = 54 mA typ,
6 x 43.3 / (4.75 x 0.60) = 91 mA worst at the 5 V input, against 22 + 34.5 =
56.5 mA typ and 55 + 34.5 = 89.5 mA worst before. The 0.52 A envelope stands.
LDO: (5.5 - 3.3) x 34.4 mA + 5.5 x 0.35 mA = 77 mW typ; (6 - 3.3) x 43.3 mA
+ 6 x 1 mA = 123 mW worst, 25 degC rise at 205 C/W; fine.

### 7.7 W1 addendum: island load with the `0032` rev 3-4 parts (2026-10-08)

Changes since 7.1: 3x ISO7761 (was 2), 6x ADT7310 (was 3 allowed), island CS
pull-ups removed (rev 4), preload 150 ohm on 3.3 V (7.6). Same sources and
allocations as 7.1 (ISO776x Rev H p.15 ICC2; CJ 0.3/0.5 mA allocation each).

    3x AD7124            2.952 typ   4.065 worst  mA   (7.1)
    3x ISO7761 side 2    3 x 3.7 = 11.1 typ   3 x 6.9 = 20.7 worst
    6x ADT7310           6 x 0.3 = 1.8 typ    6 x 0.5 = 3.0 worst
    ref/mid/comparator/misc  0.3 typ   1.0 worst
    island load          16.2 typ    28.8 worst
    + preload 22.0       38.2 typ    50.8 worst   (+ LDO ground 0.35 / 1.0)
    module input at 5 V  5.5 x 38.6 / (5 x 0.72) = 59 mA typ;  6 x 51.8 / (4.75 x 0.62) = 106 mA worst
The 7.6 worst total (515 mA) contains the island module input at 55 mA and the
preload's 34.5 mA. Replacing those 89.5 mA with the new 106 mA, and the coils
40 -> 42 mA: 515 - 89.5 + 106 + 2 = **533.5 mA**. That is **above the 0.52 A
envelope of 7.6; restate it as 0.55 A**. Battery at 9 V: 5.25 x 0.534 /
(0.85 x 8.0) = 0.412 A against F1's 0.45 A hold at 70 degC: **8 % margin**,
thin; the PTC choice (I-096, F601) must be checked against this. LDO worst:
(6 - 3.3) x 51.8 mA + 6 x 1 mA = 146 mW, 30 degC rise at 205 C/W: fine.

With the schematic's actual backlight resistor R502 = 22 ohm (7.2 assumed
12 ohm): worst (5.25 - 3.2) / (22 x 0.95) = 98 mA instead of 183 mA, so the
5 V worst becomes 533.5 - 85 = **448.5 mA** and the 9 V battery current
5.25 x 0.449 / (0.85 x 8.0) = **0.347 A (23 % margin on F1 at 70 degC)**. Keep
R502 >= 22 ohm unless the bought LCD proves too dim; then re-run this line.

## 8. Cheaper-parts variant (decisions/0036), 2026-10-12

### 8.1 Parts cost per board

Inputs: `hardware/24ch/output/cost.csv` (2026-10-09, LCSC 10-piece prices, total $104.91) and LCSC
listings read 2026-10-12 (`production/review-20261012-cheaper/*.md`).

    ADT7310 x6 -> TMP126DCKR x6     6 x (5.4045 - 2.2415)      = -18.98
    ISO7761 x3 -> CA-IS3761HW x3    3 x (2.9219 - 1.61)        =  -3.94
    RS-485 block DNP (16 parts)     ADM2587E 7.645 + SM712 0.43 + J703 0.21 + caps/R/JP ~0.36 = -8.64
    3296W trimmer -> BOCHEN         0.96 - 0.19                =  -0.77
    22u 1210 x2 -> SAMWHA           2 x (0.36 - 0.16)          =  -0.40
    R415 removed, R443 22k added                                ~  0.00
    total                                                       = -32.73  ->  104.91 - 32.73 = **$72.2**

At the real order quantity (10 boards buy 30-510 pieces of a line; `frontend-alternatives.md`):
AD7124-8 $8.79 at 30 (-3.6), BAV199 $0.0293 at 300 (-2.5), TMP126 $1.99 at 30 (-1.5): **~$64.6**.
Verdict: about 38 % off the parts. Bare PCB, assembly, accessories and freight are not in this figure.
**2026-10-14, `0036` D9: RS-485 fitted again (+8.64): ~$80.8 at 10-piece prices, ~$73 at order quantity.**

### 8.2 Supply budget effect

* RS-485 not fitted: the 150 mA ADM2587E allowance of 7.7 leaves the 5 V load (worst ~0.30 A instead
  of 0.449 A). Keep 7.7's 0.449 A as the design case: a site may fit the block later (0036 D2).
* Island: ADT7310 worst 3.0 mA total (7.7) is replaced by six TMP126, each below that figure per
  the TI datasheet (supply current per conversion, not re-derived here); R443 adds at most
  3.3 V / 22k = 0.15 mA. The island worst of 7.7 does not rise. Unverified: TMP126 current at
  the conversion rate the firmware will use.

### 8.3 TMP126 write timing through R443 (review item c)

    tau = 22k x ~180 pF (bus: 6 TMP126 + 3 AD7124 + isolator + trace, estimated) = ~4 us
    a written bit must settle ~3 tau = 12 us -> SCLK <= ~40 kHz for TMP126 writes with 22k
The review computed 125 kHz for 10k; 22k halves that. Writes are one 16-bit command per read,
6 sensors per scan: 6 x 32 bits / 40 kHz = ~5 ms per scan, inside the ~0.62 s budget (I-119).
Reads (TMP126 drives SIO directly) and all AD7124 traffic are not slowed. Firmware note (I-119).

### 8.4 JLCPCB turnkey quote, read 2026-10-14 (quote only, nothing ordered)

Owner uploaded the Gerbers of release `24ch-reva3-20261012-205016-b7ff12` and signed in; BOM/CPL
of the same release entered on cart.jlcpcb.com. Settings: 4L FR-4 1.6 mm, ENIG 1U", flying-probe
test, Standard PCBA top side (Economic refused: THT parts), JLC adds 2 x 5 mm rails (170 x 155).
All 86 BOM lines matched to the given LCSC codes (72 unique), no shortfall, LM5164 included.
"Confirm Parts Placement" and "Confirm production file" auto-selected at $0.

| USD | 5 boards | 10 boards |
|---|---|---|
| PCB (eng. fee 25 + ENIG + board) | 60.90 | 80.20 |
| Setup 25.75 + stencil 8.27 + feeders 93.00 (fixed) | 127.02 | 127.02 |
| Components (72 items, incl. attrition) | 358.59 | 645.78 |
| SMT + hand-solder 3.61 + manual (THT) + packaging | 25.18 | 44.20 |
| **Total ex shipping** | **571.69 (114.3/board)** | **897.20 (89.7/board)** |
| Weight | 2.28 kg | 3.63 kg |
| Shipping to Egypt (jlcpcb.com/shipping): FedEx 6-8 d / UPS 3-5 d / DHL 2-5 d | 59.63 / 77.46 / 108.43 | 80.64 / 107.85 / 150.96 |

Bare boards only (no rails, 0.55 kg / 0.98 kg): leaded HASL 40.30 / 55.40, lead-free HASL 45.90 /
61.60, ENIG 59.70 / 77.70; UPS to Egypt ~$47. Import duties/VAT in Egypt are not included (the
calculator does not mark Egypt DDP): UNVERIFIED. Build: PCB 3 days + assembly 5-6 days + transit.

### 8.5 REV A4 gated TMP126 SIO driver (decisions/0041), 2026-10-15 - supersedes 8.3

TMP126 SNIS209C 7.6 (read 2026-10-14): tRISE/tFALL SIO, SCLK, CS **100 ns max**, 30-70 % thresholds;
CIN 20 pF; SIO VOL/VOH at 3 mA. DOUT_ISO bus estimate (main `CALCULATIONS` 9.5): 62-72 pF, ceiling 85 pF.

    A3, R443 22k:      tau = 22k x 62..85 pF = 1.36..1.87 us;  t30-70 = 0.847 tau = 1.15..1.58 us  -> FAILS 100 ns
    A4, U411 + R446:   R = 220 + ~40 (74LVC1G125 at 3.3 V: VOH >= 2.4 V at 24 mA -> ~40 ohm) = ~260 ohm
                       tau = 260 x 85 pF = 22 ns;  t30-70 = 19 ns                          -> OK (5x margin)
    DOUT DC load:      A3 R443 3.3/22k = 150 uA (AD7124 VOH tested at 100 uA) -> marginal
                       A4 R447 3.3/100k = 33 uA                                            -> OK
    Contention if firmware drives SIO_WR_N low while a device drives SIO/DOUT:
                       3.3 V / 260 ohm = ~13 mA, limited by R446; a firmware fault, not a design state.

ESC through D501/D502 (1N4148W) to BTN_UP/BTN_DOWN, ATmega1284P internal pull-up 20-50k at 5 V:

    I = (5 - ~0.6) / 20k..50k = 0.09..0.22 mA;  1N4148W Vf at 0.1-0.2 mA ~0.5-0.6 V (datasheet curve)
    pin reads ~0.6 V  vs  VIL max 0.3 x 5 = 1.5 V                                          -> OK, ~0.9 V margin
    UP pressed alone: D501 reverse-biased (cathode held high through D502 by DOWN's pull-up) -> DOWN stays high

Correction (Astra review 2, 2026-10-15): the 85 pF ceiling is too low - six TMP126 inputs alone are 120 pF
(20 pF each). At ~180 pF: tau = 260 x 180 pF = 47 ns, t30-70 = ~40 ns -> still OK (2.5x margin).

Charge pump (RUN_PERMIT, R701 100R, C704/C705 100n, R702 100k; Astra review 2, simplified 5 V, 50 % duty):
gate ~1.4-2.9 V at 100 Hz (not enough), 3.8-4.1 V at 1 kHz, 4.1-4.2 V at 2 kHz -> firmware PWM >= 1 kHz, from
completed scans only (I-118); decay to 1 V ~15-30 ms after the drive stops. Measure the gate at the bench.

Unverified: real bus capacitance after layout extraction; CA-IS3761 channel delay (firmware has ~8 us
per half SCLK period at 62.5 kHz, so ns-level delays do not matter).

## 9. New 8-channel board (0039)

> Sections 9.1-10.9 and the findings: Codex gpt-6.1-sol, read-only, 2026-10-14, reviewed by Claude. Taken into
> `0039`: 9.5/10.5 -> gated SIO driver (P2, I-124); 10.2 RTD compliance -> new values in 10.10 (P4); 10.7 RTD
> coverage -> P5. TL431 clamp tolerance (9.2) and EEPROM record size (10.8) stay open for the schematic review.

Context: proposed `0039` rev 2, read 2026-10-14. One AD7124-8, two TMP126, two CA-IS3761HW; power chain, MCU, LCD, relays and fitted RS-485 retained.

These are feasibility calculations, **not qualification**. “Worst” means the stated screening envelope, including assumptions; it is not a guaranteed sum of manufacturer maxima. **UNVERIFIED** identifies assumed values or operating conditions. No files were changed.

### 9.1 Island 3.3 V load

Inputs:

* Mid-power ADC operation, gain 32, input buffers enabled, internal reference and diagnostics enabled, internal VBIAS disabled.
* ADC current: typ `(330 + 25 + 50 + 4) = 409 µA`; maximum `(430 + 40 + 70 + 5) = 545 µA`. Reference buffers are unnecessary for internal-reference measurements. [AD7124-8, Table 3](https://www.analog.com/media/en/technical-documentation/data-sheets/ad7124-8.pdf).
* CA-IS3761 side B: 5.1 mA typ at 500 kHz, all channels switching; 8.9 mA maximum of the applicable AC/DC rows. Side A: 6.3 mA typ, 15.3 mA maximum. **UNVERIFIED:** applying separate 5 V and 3.3 V tables to mixed supplies and actual channel activity. [Chipanalog CA-IS376x, §§7.8–7.9](https://e.chipanalog.com/Public/Uploads/uploadfile/files/datasheet/CA-IS376x_datasheet_Version1.05.pdf).
* TMP126: 77 µA typ during conversion; 135 µA maximum through 150 °C. Continuous active-conversion current is deliberately budgeted without duty-cycle savings. [TMP126, §7.5](https://www.ti.com/lit/ds/symlink/tmp126.pdf).
* Auxiliary allocations include REF3030, MCP6001, comparator, divider currents, clamp-divider current and engine-reference current.
* Rail envelope: 3.3 V ±5%; R401 = 150 Ω ±1%.

| Island load | Typ, mA | Worst, mA | Basis |
|---|---:|---:|---|
| One AD7124-8 | 0.409 | 0.545 | Mid-power calculation above |
| Two CA-IS3761 secondary sides | 10.200 | 17.800 | `2 × 5.1 / 8.9` |
| Two TMP126 | 0.154 | 0.270 | `2 × 0.077 / 0.135` |
| Reference, buffer, comparator and passive networks | 0.600 | 1.000 | **UNVERIFIED allocation** |
| R443 contention current | 0.150 | 0.160 | No duty-cycle credit |
| Additional switching/burnout allowance | 0.100 | 0.300 | **UNVERIFIED allocation** |
| **Functional load, excluding preload** | **11.613** | **20.075** | Sum |
| R401 preload | 22.000 | 23.333 | `3.3/150`; `3.465/148.5` |
| **LDO output load** | **33.613** | **43.408** | Sum |
| LDO ground/enable allowance | 0.350 | 1.000 | Retained §7.1 screening allowance |
| **Module output current** | **33.963** | **44.408** | LDO input current |

**Verdict: OK for capacity; preload required.** The maximum functional-load figure cannot establish a minimum load. Typical functional load is only 11.6 mA, below the module’s 20 mA minimum, and reset/idle can draw less.

The table uses mid-power operation. Accidental full-power operation adds approximately 0.575 mA typ / 0.810 mA maximum per TC ADC; it does not threaten supply capacity.

### 9.2 Isolated module, preload, LDO and startup

The fitted manufacturer is **YLPTEC**, not the MORNSUN calculation proxy used in §7.1. Its B0505S-1WR2 sheet specifies 200 mA maximum, **20 mA minimum**, nominal 5 V output and 1 W. Output regulation is specified over 10–100% load. [YLPTEC B_S-1WR2](https://atta.szlcsc.com/upload/public/pdf/source/20240729/EA84979D67E82D095ACC25BE5C806E4D.pdf).

    Module loading = I_module / 200 mA
                   = 17.0% typ / 22.2% worst

    Module output power:
      typ, assumed 5.5 V = 5.5 × 33.963 mA = 0.187 W
      worst, assumed 6 V = 6 × 44.408 mA = 0.266 W

The 5.5/6 V operating points and efficiencies below are **UNVERIFIED**, retained from the section 7 screening method.

**R401 minimum-loading check**

    Minimum preload = 3.135 V / 151.5 Ω = 20.69 mA
    Nominal power   = 3.3² / 150       = 72.6 mW
    Maximum power   = 3.465² / 148.5   = 80.9 mW

The preload alone exceeds 20 mA once the island rail is regulated. It also provides a load for positive clamp injection. Retain **150 Ω, 1206**.

**LDO check**

LP2985 screening limits retained from §7.1: 150 mA rated output; legacy dropout maximum 225 mV at 50 mA over temperature; θJA = 205.4 °C/W. Both calculated loads are below 50 mA. [LP2985-N, §§5.4–5.5](https://www.ti.com/lit/ds/symlink/lp2985-n.pdf).

    Required raw voltage = 3.465 + 0.225 = 3.690 V
    At assumed raw minimum 4.5 V:
      dropout margin = 4.5 − 3.690 = 0.810 V

    P_LDO = (Vraw − 3.3) × I_load + Vraw × I_ground

    Typ   = 2.2 × 33.613 mA + 5.5 × 0.350 mA = 75.9 mW
    Worst = 2.7 × 43.408 mA + 6 × 1.000 mA   = 123.2 mW

    Junction rise = 0.1232 × 205.4 = 25.3 °C
    At 85 °C ambient: Tj ≈ 110.3 °C

**Verdict: OK**, conditional on raw-voltage and thermal assumptions. Actual module sag/ripple and legacy-LDO capacitor/ESR stability remain **UNVERIFIED**.

**Startup**

Use the §7.4 conservative capacitance inventory:

| Rail | Assumed upper capacitance |
|---|---:|
| Control 5 V | 120 µF |
| Raw isolated output | 13.2 µF |
| Island 3.3 V | 12 µF |

    Island-side charging quantity ≈ 13.2 µF × 6 V + 12 µF × 3.465 V
                                  = 120.8 µC

    Illustrative charging time with 100 mA surplus = 120.8 µC / 100 mA
                                                = 1.21 ms

This demonstrates modest stored charge, **not a guaranteed startup time**. The LDO can demand more than the module’s rated current while charging capacitors; the module’s startup/current-limit behaviour is not bounded by the steady-load table. Before the 3.3 V rail reaches approximately 3.03 V, R401 itself draws less than 20 mA.

**Startup verdict: MARGINAL / UNVERIFIED.** Check ramp, overshoot, hiccup and brownout at minimum/maximum 5 V and temperature. Do not remove R401 on the basis of RUN current.

**TL431 clamp**

From `c_iso.py`, R428/R429 = 4.02 kΩ/10 kΩ:

    Vclamp ≈ Vref × (1 + R428/R429) + Iref × R428
           ≈ 2.495 × 1.402 + 2 µA × 4.02 kΩ
           ≈ 3.506 V

    Approximate collector-current ceiling:
      (3.5 − 0.2) / 22 Ω = 150 mA

    R441 at that ceiling = 0.150² × 22 = 0.495 W

The normal startup load does not include 150 mA of clamp current: the clamp should remain off below its threshold. It clamps **3.3 V AVDD**, not the module’s raw 5 V output.

A conservative tolerance stack for the fitted TL431BI, using maximum initial reference, full-temperature deviation, reference-input current and 1% divider corners, gives:

    Vclamp_high ≈ (2.507 + 0.034)
                  × [1 + (4020 × 1.01)/(10000 × 0.99)]
                  + 6.5 µA × 4020 × 1.01
                ≈ 3.610 V

These inputs come from [TL431BI, §6.12](https://www.ti.com/lit/ds/symlink/tl431.pdf). This is a conservative bound rather than a predicted operating voltage, but it leaves no guaranteed margin below the ADC’s 3.6 V operating ceiling, before transient overshoot.

**Clamp verdict: MARGINAL.** Capacity is adequate as a screening estimate; threshold tolerance and transient regulation require resolution for both new boards. Simply lowering R428 can make the clamp conduct against a high-tolerance LDO output.

### 9.3 5 V budget and battery current

Inputs:

* RS-485 fitted and continuously transmitting into the section 7 double-termination screening case.
* ADM2587E: 98 mA typ; 150 mA worst is an **UNVERIFIED allowance**, not a specified maximum.
* LCD logic: 1.5/3 mA; backlight Vf = 3.5/3.2 V, **UNVERIFIED**.
* R502 = 22 Ω ±5%.
* Both DC5 relays energized. Nominal coil resistance 237.5 Ω, ±10% at 23 °C; cold-coil behaviour is a separate assumption.
* MCU, LEDs and auxiliary allocations retained from §7.2.

    LCD typ   = (5 − 3.5)/22 + 1.5 mA        = 69.68 mA
    LCD worst = (5.25 − 3.2)/(22 × 0.95) + 3 = 101.09 mA

    Two relay coils typ   = 2 × 5/237.5           = 42.11 mA
    Two relay coils worst = 2 × 5.25/(237.5 × 0.9) = 49.12 mA

    Module input = Vraw × I_module / (V5 × efficiency)

    Typ   = 5.5 × 33.963 / (5 × 0.72)    = 51.89 mA
    Worst = 6 × 44.408 / (4.75 × 0.62)   = 90.48 mA

Effective efficiency includes converter losses; do not add no-load current again.

| 5 V load | Typ, mA | Worst, mA |
|---|---:|---:|
| MCU | 8.00 | 20.00 |
| LCD | 69.68 | 101.09 |
| ADM2587E | 98.00 | 150.00 |
| Two isolator primary sides | 12.60 | 30.60 |
| Island module input | 51.89 | 90.48 |
| Two relay coils | 42.11 | 49.12 |
| LEDs | 4.00 | 5.00 |
| Pull-ups, contrast and auxiliaries | 2.00 | 5.00 |
| **Total** | **288.27** | **451.28** |

Use **0.50 A** as the 5 V design envelope. An illustrative copper-resistance correction from 23 °C to −40 °C raises the two-coil allowance to approximately 65.3 mA, giving about **467.5 mA** total; this cold-coil model is **UNVERIFIED**.

Battery calculation includes D601 = 0.5 V drop, PTC resistance 0.09 Ω typ / 0.5 Ω worst, buck efficiency 90/85%, and battery-side auxiliaries 1/2 mA:

    Ibat = V5 × I5 / [ηbuck × (Vbat − 0.5 − RPTC × Ibat)] + Iaux

| Battery voltage | Typ current | Screening worst |
|---|---:|---:|
| 18 V | 92.6 mA | 162.0 mA |
| 24 V | 69.2 mA | 120.9 mA |
| 32 V | 51.8 mA | 90.6 mA |

**Verdict: OK within the requested 18–32 V range.** Exact LCD loading, RS-485 loading and efficiencies remain unverified. These figures do not qualify lower cranking voltages.

### 9.4 Buck, PTC, panel fuse and inrush

Retain LM5164, 33 µH L601 and F601. Use the section 7 screening bounds: Lmin = 26.4 µH, fmin = 270 kHz.

    ΔIL = Vout/(f × L) × (1 − Vout/Vin)
    Ipeak = Iout + ΔIL/2
    Irms  = sqrt(Iout² + ΔIL²/12)

At the **0.50 A design envelope**, Vout = 5.25 V:

| Protected buck input | Ripple | Peak | RMS |
|---|---:|---:|---:|
| 18 V | 0.522 A | 0.761 A | 0.522 A |
| 24 V | 0.575 A | 0.788 A | 0.527 A |
| 32 V | 0.616 A | 0.808 A | 0.531 A |
| 58 V, retained transient screen | 0.670 A | 0.835 A | 0.536 A |

LM5164 has 1 A output capability and a 1.25–1.75 A peak-current-limit range. [LM5164, §6.5](https://www.ti.com/lit/ds/symlink/lm5164.pdf).

    Output capacity/design envelope = 1/0.50 = 2.0×
    Minimum peak-limit margin at 32 V = 1.25 − 0.808 = 0.442 A

Retain L601; its saturation requirement still follows the maximum converter limit, not only normal-load peak current.

Using the §7.3 PTC hold values, even the 0.50 A rail envelope draws approximately 0.180 A from an 18 V battery:

    Hold-current margin at 70 °C = 0.45/0.180 = 2.50×
    Hold-current margin at 85 °C = 0.35/0.180 = 1.94×

**Buck/PTC verdict: OK for 18–32 V.**

Input capacitance and resistance are unchanged:

    Cin_upper = (22 + 4.7 + 4.7) × 1.2 = 37.68 µF

    I²t_input = Vbat² × Cin_upper / (2 × 0.090 Ω)
              = 0.214 A²s at 32 V

Retain §7.4’s **UNVERIFIED** successful-startup assumption: one startup within 20 ms, no repeated hiccup, conservative panel-current ceiling 1.77 A.

    I²t_start ≤ 1.77² × 0.020 = 0.0627 A²s

    Combined overlap bound
      ≤ [sqrt(0.214) + sqrt(0.0627)]²
      = 0.509 A²s

    Fuse screening margin = 1/0.509 = 1.96×
    Steady-current margin at 18 V, design envelope = 1/0.180 = 5.56×

**Fuse verdict: OK conditionally; retain 0020:** 1 A time-delay, ≥80 V DC, ≥10 kA DC interruption, verified pre-arc I²t ≥1 A²s. No case for changing its rating from these calculations. Exact fuse/holder and measured startup pulse remain required.

### 9.5 Shared DOUT bus and TMP126 write path

Inputs:

| Contribution | Capacitance |
|---|---:|
| One ADC floating DOUT | 10 pF |
| Two TMP126 SIO pins | 40 pF |
| Reverse isolator input | 2 pF |
| Estimated trace, vias and pads | 10–20 pF |
| **Estimated total** | **62–72 pF** |
| **Screening ceiling** | **85 pF** |

Trace estimate: approximately 100–150 mm aggregate routed length, at an assumed 0.7–1.2 pF/cm plus pad/via allowance. **UNVERIFIED until layout extraction.**

The ADC output-capacitance figure is from its logic-output table; TMP126 specifies 20 pF input capacitance and isolator CI is 2 pF.

For R443 = 22 kΩ:

    τ = R × C = 1.36–1.58 µs estimated; 1.87 µs at 85 pF

    Conservative write clock:
      f ≤ 1 / [2 × (3τ + 10 ns)]
        ≈ 89 kHz at 85 pF

An 8 MHz AVR’s **62.5 kHz** hardware-SPI setting satisfies this conservative settling calculation. This applies to the command portion of every TMP126 read as well as register writes.

**RC-settling verdict: OK at 62.5 kHz, conditional on Cbus ≤85 pF.**

Two separate limits remain:

1. **ADC DC loading**

    R443 nominal load when DIN and DOUT oppose:
      3.3/22k = 150 µA

    High-rail/low-resistance corner:
      3.465/(22k × 0.99) = 159 µA

ADC DOUT voltage is specified at **100 µA**, not at 150–159 µA. Deselected-device and isolator-input leakage can add further load. The CA-IS3761 input table permits up to 20 µA leakage.

**Verdict: MARGINAL / UNVERIFIED logic levels.** This is outside the specified output-voltage test condition, rather than proof of an absolute-current violation.

2. **TMP126 input edge time**

TMP126 specifies 100 ns maximum SIO rise/fall time; its timing diagram uses 30–70% thresholds. [TMP126, §7.6](https://www.ti.com/lit/ds/symlink/tmp126.pdf).

    t30–70 = ln(0.7/0.3) × τ = 0.8473τ
            ≈ 1.15–1.34 µs; 1.58 µs at 85 pF

**Verdict: FAILS the published edge-time requirement.** Reducing clock frequency fixes settling before sampling, but does not shorten the edge.

**Recommendation:** use an enabled, low-impedance TMP126 command driver and controlled read turnaround on the new board. The 8-ch allocation uses six of ten forward channels—SCLK, DIN, three CS and REFTEST—so **four forward channels remain spare**. A push-pull isolator output must not drive SIO during sensor reads.

### 9.6 Engine-reference FEED/SENSE detection

Circuit inputs from `c_iso.py`:

| Element | Value |
|---|---:|
| Buffered midpoint | 1.65 V nominal |
| R418 | 100 Ω |
| R419 + R420 | 9.98 kΩ |
| R427, midpoint to bias bus | 10 kΩ |
| Each TC− bias | 20 MΩ |
| R421, sense protection | 10 kΩ |
| R422, sense pull-down | 1 MΩ |
| REF_THR divider | 15 kΩ/10 kΩ |
| R442 hysteresis | 1 MΩ |
| C419 sense filter | 100 nF |

Worst masking case: **all eight probes grounded**, so all eight bias resistors can feed the engine node after FEED breaks. Insulated probes do not provide those parallel DC paths. RTD paths are absent.

Define:

    Rbias(N) = R427 + 20 MΩ/N
    Rfeed_connected = 9.98 kΩ || Rbias(N)

    Vsense_connected =
      1.65 × 1 MΩ /
      [1 MΩ + R421 + Rfeed_connected + R418]

    Vsense_broken =
      1.65 × 1 MΩ /
      [1 MΩ + R421 + Rbias(N) + R418]

For N = 8:

    Rbias = 10k + 20M/8 = 2.510 MΩ

    Wire connected: Vsense = 1.6176 V
    FEED broken:    Vsense = 0.4687 V

    Connected margin above 1.32 V = 0.2976 V
    Broken margin below 1.32 V    = 0.8513 V

The approximately 1.63 V source comment omits some series resistance; including R421 gives approximately **1.618 V**.

R442 shifts the nominal threshold:

    REFOK low:  REF_THR ≈ 1.3121 V
    REFOK high: REF_THR ≈ 1.3318 V

With grounded probes:

    V_BIAS connected ≈ 1.6498 V
    V_BIAS broken    ≈ 1.6453 V

The broken-wire current is only approximately 0.469 µA total. V_MID buffering therefore prevents the bias network from materially depressing the source.

Assuming all relevant resistors ±1%, the midpoint at its high corner and bias resistance at its low corner:

    Broken sense upper corner ≈ 0.4802 V at a 3.3 V rail
    Connected sense lower corner ≈ 1.6007 V

Allowing comparator ±8 mV offset and 8.5 mV internal half-hysteresis gives an approximately 1.280 V low threshold corner. [TLV7031, §5.7](https://www.ti.com/lit/ds/symlink/tlv7031.pdf).

    Broken-case remaining corner margin ≈ 1.280 − 0.480 = 0.800 V

C419 gives approximately 71.6 ms time constant after FEED breaks, but the nominal threshold is crossed in approximately **22 ms** because the initial voltage is already near the threshold.

**Verdict: OK for the resistor-network calculation.** Hot protection leakage, cable coupling and actual grounded-probe paths remain **UNVERIFIED**. REFTEST verifies the sense/comparator response; it does not replace a physical cut-FEED test.

### 9.7 Scan latency

The retained 24-ch setting is **mid-power, 25 SPS post-filter**, not a generic 25 SPS sinc filter. `0032` rev 3 and `docs/reference/review-20261009-astra.md` establish this setting.

Use FILTER = `111`, POST_FILTER = `011`; nominal switched-channel settling is 42.331 ms. At a −5% ADC clock:

    Tslot = 42.331/0.95 = 44.559 ms

A proposed complete bank cycle is:

| Operation | Slots |
|---|---:|
| Eight TC readings | 8 |
| One rotating burnout check | 1 |
| Internal-reference/REF3030 comparison | 1 |
| Zero check | 1 |
| Nonzero check | 1 |
| Rotating common-mode check | 1 |
| AVDD/6 | 1 |
| Additional gain-ratio reading | 1 |
| **Total** | **15** |

    Conversion schedule = 15 × 44.559 = 668.4 ms

SPI assumption: **500 kHz**, the §7.1 budget assumption; no implemented 24-ch firmware clock is established.

Allow 64 SPI bits per ADC operation, 15 result transactions plus six extra configuration/status transactions:

    ADC bus time ≤ 21 × 64/500k = 2.69 ms

For two CJ reads, conservatively clock complete CRC frames at 62.5 kHz:

    CJ time = 2 × 48/62.5k = 1.54 ms

Add 7.5 ms CJ conversion availability and a **UNVERIFIED 20 ms** bounded software/configuration allowance:

    Cycle screen ≈ 668.4 + 2.69 + 1.54 + 7.5 + 20
                 ≈ 700 ms

With prompt per-result trip evaluation and 30 ms allowed for pump/relay release:

    Including an extra filter interval:
      response screen ≈ 700 + 44.6 + 30 = 775 ms

**Verdict: OK as a proposed schedule; UNVERIFIED in firmware and hardware.** Temperature samples must not wait for the next complete-scan processing pass.

One rotating burnout check revisits each channel in approximately **5.6 s**; common-mode checks revisit each of 16 inputs in approximately **11.2 s**. These are diagnostic intervals, not one-second open-wire coverage. If every channel requires a burnout test every second, this schedule must change.

### 9.8 Firmware resources

ATmega1284P provides 128 KiB flash, 16 KiB SRAM and 4 KiB EEPROM. [Microchip ATmega1284P](https://ww1.microchip.com/downloads/en/DeviceDoc/Atmel-42719-ATmega1284P_Datasheet.pdf).

`0029`/`0038` specify record content and validation behaviour, but do **not** define a byte layout. Proposed explicit serialization:

| Record field | Bytes |
|---|---:|
| Magic | 2 |
| Format version | 1 |
| Channel identity | 1 |
| Generation/sequence | 4 |
| Setpoint, signed fixed-point | 4 |
| Hysteresis | 2 |
| Sensor type | 1 |
| Mode/flags | 1 |
| CRC | 2 |
| Commit marker | 1 |
| Reserved | 5 |
| **One record** | **24** |

    Eight channels, A/B records = 8 × 2 × 24 = 384 B

With 128 B global A/B settings, 32 B bank calibration and 1024 B event allocation:

    EEPROM total = 384 + 128 + 32 + 1024 = 1568 B
    Free EEPROM  = 4096 − 1568 = 2528 B

Proposed RAM allocation is **40 B/channel**, including raw value, temperature, previous value, filter accumulator, timestamp, burnout baseline, setpoint, hysteresis, type/mode, fault/state and counters.

    Channel RAM = 8 × 40 = 320 B

A conservative total including 512 B communications buffers, 128 B ADC state, 32 B CJ state, 224 B optional Modbus shadow map, 128 B LCD storage, 512 B miscellaneous state and 2048 B stack reserve is:

    SRAM budget = 4004 B ≈ 24% of 16 KiB

K/J tables use approximately 2.5 KiB per `0038`, stored in program memory. A 64 KiB code allocation plus tables, 1 KiB metadata/map allocation and 4 KiB boot reserve is approximately 71.5 KiB.

**Verdict: fits comfortably.** These are allocations, not measured firmware size. A/B serialization, corrupted-type handling and setpoint reconfirmation follow `0038`; do not write native C structures directly to EEPROM.

### 9.9 Board size

Read-only `kicad-tool` queries of `hardware/24ch/thermo24.kicad_pcb` establish:

* Outline: **170 × 145 mm = 24,650 mm²**.
* Footprints: **466**.
* Each TC bank: **97 footprints**.
* Release `4b1601`: **442 BOM parts**; the other 24 footprints are mounting holes, fiducials and test points.

Estimated one-bank reduction:

    BOM parts ≈ 442 − 2 × 97 − 3 isolator/cap parts − 6 CS pull-ups
              = 239

    Footprints ≈ 466 − 194 − 3 − 6 = 263

At the same area per BOM part:

    Area estimate = 24,650 × 239/442 = 13,329 mm²

| Candidate outline | Area | Component density versus 24-ch |
|---|---:|---:|
| 110 × 100 mm | 11,000 mm² | 21% higher |
| 120 × 100 mm | 12,000 mm² | 11% higher |
| 120 × 110 mm | 13,200 mm² | Approximately equal |

**Verdict: MARGINAL for 110–120 × 100 mm; 120 × 110 mm is a reasonable first floor-plan envelope.** The approximately 98 × 60 mm LCD, terminal entry, controls and retained power blocks prevent scaling by channel count alone. This is an area estimate, not a placement result.

## 10. 40-channel board (0039)

Context: five TC banks, ten TMP126, one additional AD7124-8 for four RTDs, one 74HC154 and two CA-IS3761HW. All ADCs convert concurrently. RTDs are assumed insulated from engine/frame.

Common screening assumptions and source limits are those in section 9.

### 10.1 Island 3.3 V load

The RTD allowance includes ADC operation, reference buffers and continuously enabled **two 250 µA sources**, or one 500 µA source. Only the selected RTD is excited; this is not four simultaneous 500 µA loads.

    RTD ADC typ allowance:
      0.409 mA ADC + 0.040 mA reference buffers
      + 0.500 mA excitation + 0.100 mA reserve
      = 1.049 mA

    RTD maximum screening allocation = 1.200 mA

The RTD allowance is conservative and **UNVERIFIED for its final gain/reference configuration**.

74HC154 operates at 3.3 V. Its static maximum supply current is 160 µA over −40 to 125 °C at the datasheet test condition; slow addressing adds little average dynamic load. Use 10 µA typ / 160 µA worst. [Nexperia 74HC154](https://assets.nexperia.com/documents/data-sheet/74HC_HCT154.pdf).

| Island load | Typ, mA | Worst, mA |
|---|---:|---:|
| Five TC ADCs | 2.045 | 2.725 |
| RTD ADC, buffers and excitation | 1.049 | 1.200 |
| Two isolator secondary sides | 10.200 | 17.800 |
| Ten TMP126 | 0.770 | 1.350 |
| 74HC154 | 0.010 | 0.160 |
| References, buffer, comparator and passive networks | 0.600 | 1.000 |
| R443 contention allowance | 0.150 | 0.160 |
| Extra switching, decoder pull-up and burnout allowance | 0.500 | 1.000 |
| **Functional load, excluding preload** | **15.324** | **25.395** |
| R401 preload | 22.000 | 23.333 |
| **LDO output load** | **37.324** | **48.728** |
| LDO ground/enable allowance | 0.350 | 1.000 |
| **Module output current** | **37.674** | **49.728** |

The extra switching allowance covers the larger SCLK/DIN loads and proposed interface logic; recalculate after selecting the actual buffer/multiplexer.

**Verdict: OK for capacity.** Channel count increases the ADC/CJ load modestly; the two isolators and preload dominate.

### 10.2 Module, LDO, preload, startup and RTD excitation

    Module loading = 37.674/200 = 18.8% typ
                     49.728/200 = 24.9% worst

    Module power = 5.5 × 37.674 mA = 0.207 W typ
                   6 × 49.728 mA   = 0.298 W worst

**The existing 1 W module fits.** No higher-power converter is required by the calculated steady load.

**Preload**

Without R401, typical module current is approximately:

    15.324 + 0.350 = 15.674 mA < 20 mA

ADC standby, disabled excitation and CJ idle further reduce it. A worst-case load exceeding 20 mA cannot justify removing the preload.

**Verdict: retain R401 = 150 Ω.** Its minimum regulated-rail current remains 20.69 mA. Forty channels do not establish a guaranteed 20 mA minimum across operating states.

**LDO**

    Ptyp = 2.2 × 37.324 mA + 5.5 × 0.350 mA = 84.0 mW
    Pworst = 2.7 × 48.728 mA + 6 × 1.000 mA = 137.6 mW

    Junction rise ≈ 0.1376 × 205.4 = 28.3 °C
    At 85 °C ambient: Tj ≈ 113.3 °C

    Dropout requirement, calculated load <50 mA:
      Vraw ≥ 3.465 + 0.225 = 3.690 V

**Verdict: OK under the stated envelope.** The 48.7 mA result is close to the 50 mA datasheet row; if final interface loading or full-power firmware pushes it above 50 mA, use the higher-current dropout/ground-current bounds. Even the legacy 575 mV dropout bound requires only 4.04 V raw input, but must be checked against measured module sag.

For startup, allow 30 µF upper island capacitance and retain 13.2 µF raw capacitance:

    Charging quantity ≈ 13.2 µF × 6 + 30 µF × 3.465
                      = 183.2 µC

    Illustrative time at 100 mA surplus = 1.83 ms

**Startup verdict: MARGINAL / UNVERIFIED**, for the same reasons as §9.2. Stored charge fits comfortably within the module’s capacitive-load envelope, but does not prove startup without hiccup. The TL431 threshold-tolerance finding in §9.2 applies unchanged.

**RTD excitation compliance**

The supplied `0039` example is a real failure if excitation flows through 3.2 kΩ protection:

    At nominal excitation:
      Vrequired ≥ 2 × 250 µA × 5.11 kΩ
                  + 250 µA × 3.2 kΩ
                = 3.355 V

    Available compliance = 3.3 − 0.37 = 2.930 V

**Verdict: FAILS**, before RTD and lead drops.

A provisional alternative retaining two 250 µA sources is **Rref ≈3.00 kΩ**, precision/low drift, or a substantially lower-resistance excitation branch. Sense protection can remain separate.

For Rref = 3.00 kΩ, 0.1%; protection = 3.2 kΩ, 1%; PT100 resistance up to approximately 391 Ω; excitation upper allowance +4.5%:

    Vrequired ≈ 522.5 µA × 3003 Ω
                + 261.25 µA × 3232 Ω
                + 261.25 µA × 391 Ω
              ≈ 2.516 V

    At 3.135 V island minimum:
      compliance = 3.135 − 0.37 = 2.765 V
      margin before leads = 2.765 − 2.516 = 0.249 V

    Reference voltage nominal = 500 µA × 3.00 kΩ = 1.500 V
    PT100 maximum signal ≈ 250 µA × 391 Ω = 97.8 mV
    Gain 8 full scale = 1.500/8 = 187.5 mV

**Verdict: OK provisionally**, subject to actual excitation topology, lead resistance, range and tolerances. Rref and excitation protection require a new calculation before freeze; 5.11 kΩ cannot be inherited with the stated 3.2 kΩ excitation resistance.

### 10.3 5 V budget and battery current

Only module loading changes significantly from §9.3.

    Module input typ =
      5.5 × 37.674 / (5 × 0.72) = 57.56 mA

    Module input worst =
      6 × 49.728 / (4.75 × 0.62) = 101.31 mA

| 5 V load | Typ, mA | Worst, mA |
|---|---:|---:|
| MCU | 8.00 | 20.00 |
| LCD | 69.68 | 101.09 |
| ADM2587E | 98.00 | 150.00 |
| Two isolator primary sides | 12.60 | 30.60 |
| Island module input | 57.56 | 101.31 |
| Two relay coils | 42.11 | 49.12 |
| LEDs | 4.00 | 5.00 |
| Control auxiliaries | 2.00 | 5.00 |
| **Total** | **293.94** | **462.12** |

Illustrative −40 °C coil correction raises the total to approximately **478.3 mA**. Retain the **0.50 A design envelope**; exact cold-coil resistance remains unverified.

Using the §9.3 battery equation:

| Battery voltage | Typ current | Screening worst |
|---|---:|---:|
| 18 V | 94.4 mA | 165.9 mA |
| 24 V | 70.5 mA | 123.8 mA |
| 32 V | 52.8 mA | 92.7 mA |

**Verdict: OK for 18–32 V.** The 40-ch board adds approximately 11 mA to the screening-worst 5 V budget compared with the new 8-ch board.

### 10.4 Buck, fuse and inrush

Use the same **0.50 A** design envelope, so the buck ripple, peak/RMS, PTC and panel-fuse calculations in §9.4 apply directly.

    At 32 V:
      Ipeak = 0.808 A < 1.25 A minimum peak limit

    At 18 V battery:
      design-envelope current ≈ 0.180 A

    Panel-fuse screening:
      I²t_total ≤ 0.509 A²s
      1 A²s requirement / screening = 1.96×

The larger island capacitance changes downstream stored energy, not the direct battery capacitor step. At the assumed upper capacitances:

    Edownstream =
      0.5 × [120 µF × 5.25²
             + 13.2 µF × 6²
             + 30 µF × 3.465²]
      ≈ 2.07 mJ

The retained 20 ms startup allowance covers this inventory only if startup succeeds without repeated retries.

**Verdict: OK conditionally.** Retain LM5164, 33 µH L601, existing PTC and the 1 A panel fuse specification. No current-driven power-part change is required.

### 10.5 Shared DOUT capacitance, write timing and separate TMP126 path

**74HC154 contributes no DOUT pin capacitance:** it drives chip selects and does not connect to the data net.

| Shared DOUT contribution | Capacitance |
|---|---:|
| Six ADC floating DOUT pins | 60 pF |
| Ten TMP126 SIO pins | 200 pF |
| Reverse isolator input | 2 pF |
| Decoder | 0 pF |
| Estimated trace/vias/pads | 20–40 pF |
| **Estimated total** | **282–302 pF** |
| **Screening ceiling** | **330 pF** |

For a roughly 220 × 170 mm board, estimate **250–350 mm aggregate DOUT routing**, not simply the board diagonal. Trace capacitance assumes 0.7–1.2 pF/cm plus pad/via allowance. All routing assumptions are **UNVERIFIED**.

R443 is a resistance; its small parasitic capacitance is included in the layout allowance.

    At 300 pF:
      τ = 22k × 300 pF = 6.60 µs
      3τ = 19.80 µs

      fwrite ≤ 1/[2 × (3τ + 10 ns)]
             = 25.24 kHz

    At 330 pF:
      τ = 7.26 µs
      fwrite ≤ 22.95 kHz

**RC verdict: use ≤20 kHz for the retained topology.** The plan’s approximately 25 kHz estimate has little tolerance reserve. The AVR’s slowest standard hardware-SPI clock at 8 MHz is 62.5 kHz, so ≤20 kHz requires software clocking or a different clock-generation arrangement.

The threshold-only calculation is less conservative:

    Time to 0.7 VDD = −ln(0.3) × τ = 1.204τ
    At 330 pF: threshold-only clock ceiling ≈57 kHz

Even that does not justify 62.5 kHz at the screening capacitance.

**Input edge-time check**

    t30–70 = 0.8473τ
            = 5.59 µs at 300 pF
            = 6.15 µs at 330 pF

**Verdict: FAILS TMP126’s 100 ns edge-time requirement.** A 20 kHz clock does not fix this violation.

**ADC DOUT loading**

    Nominal R443 current = 150 µA
    Rail/resistor corner = 159 µA

With five deselected ADC outputs, ten TMP126 inputs and the isolator input, additional permitted leakage can bring the screening load toward **190 µA**.

**Verdict: MARGINAL / UNVERIFIED.** ADC VOH/VOL is specified at 100 µA. Increasing channel count does not multiply the 150 µA resistor current, but increases capacitance and leakage.

The average full-swing charging demand illustrates why capacitance also matters during directly driven reads:

    Icharge ≈ C × V × f
             = 300 pF × 3.3 × 500 kHz
             ≈ 0.495 mA during switching

This is dynamic charging demand, not a DC current to compare directly with the 100 µA voltage specification. Read-edge timing at 500 kHz still requires verification.

**Separate TMP126 line**

The proposed allocation uses **8/10 forward channels**:

    SCLK, DIN, A0–A3, EN, REFTEST = 8
    Spare forward channels      = 2
    Reverse channels            = DOUT + REFOK; neither is spare

A separate TMP126 data net would reduce loading approximately to:

| Net | Estimated capacitance |
|---|---:|
| ADC DOUT, six ADCs plus return circuitry | 75–100 pF |
| TMP126 SIO, ten sensors plus command/return circuitry | 220–245 pF |

A separate line **with the same 22 kΩ drive** still gives approximately 4.8–5.4 µs RC time constant and does not satisfy input edge time.

**Recommended topology:**

* Remove the permanent DIN-to-ADC-DOUT resistive connection.
* Drive TMP126 SIO through an enabled, low-impedance island-side buffer.
* Disable that driver before TMP126 readback.
* Select ADC DOUT or TMP126 SIO into the existing reverse data isolator using controlled return routing.
* Use one spare forward channel for TMP command data if separate from DIN, and the other for direction/control. Alternatively, reuse DIN at the buffer and retain one spare.

One additional forward channel alone does not create a complete bidirectional interface. The return selector and safe driver-disable behaviour must be defined.

For a 245 pF TMP bus:

    To meet 100 ns, 30–70%:
      Rtotal ≤ 100 ns/(0.8473 × 245 pF)
             ≈ 482 Ω

An illustrative **220 Ω series resistor**, with ≤100 Ω buffer resistance, gives:

    t30–70 ≤ 0.8473 × 320 Ω × 245 pF = 66 ns

Buffer resistance, current capability and propagation are **UNVERIFIED until a part is selected**. The resistor does not make push-pull contention acceptable: driver disable is mandatory.

**Recommendation: separate and actively control the TMP126 data path.** Two CA-IS3761HW remain sufficient; no third isolator is required by channel count.

### 10.6 Engine-reference detection with 40 bias paths

Use the equations and circuit values in §9.6. Only grounded TC channels contribute the parallel engine-feed path. The RTD bank is insulated and contributes none.

    Rbias(40) = 10k + 20M/40 = 510 kΩ

    Connected Vsense = 1.6178 V
    FEED-broken Vsense = 1.0855 V

    Margin above 1.32 V when connected = 0.2978 V
    Margin below 1.32 V when broken    = 0.2345 V

The plan’s “36 channels approximately 1.05 V” follows directly from:

    Vsense_broken(36) =
      1.65 × 1M / [1M + 10k + 10k + 20M/36 + 100]
      = 1.0472 V

There is no separate 1.05 V design constant.

| Grounded bias paths | Broken-FEED voltage | Margin below 1.32 V |
|---|---:|---:|
| 8 | 0.4687 V | 0.8513 V |
| 24 | 0.8902 V | 0.4298 V |
| 36 | 1.0472 V | 0.2728 V |
| 40 | 1.0855 V | 0.2345 V |

Including external hysteresis:

    Threshold while connected/REFOK low ≈1.3121 V
    Broken-case margin to that threshold ≈0.2267 V

For 40 grounded paths:

    V_BIAS connected ≈1.6495 V
    V_BIAS broken    ≈1.6390 V

    Broken-case total current ≈1.0855 µA
    Current per grounded bias path ≈27.1 nA

The bias bus remains near midpoint; its resistor paths partially power the engine node after FEED breaks, producing the elevated sense voltage.

At resistor corners used in §9.6:

    Broken sense upper corner ≈1.1038 V
    Low threshold including offset/hysteresis ≈1.2799 V

    Remaining corner margin ≈1.2799 − 1.1038 = 0.1761 V

Positive leakage into the broken sense node can consume that margin. Its approximate Thevenin resistance is:

    Rsense_th ≈1M || 520.1k = 342 kΩ

    Additional current to consume 0.176 V ≈0.176/342k
                                         ≈0.51 µA

This is a sensitivity estimate, **not an accepted leakage allowance**.

C419 gives approximately 34.2 ms broken-wire time constant and approximately **29 ms nominal threshold-crossing time**.

**Verdict: OK for the nominal and stated resistor-corner calculation; MARGINAL against unbounded hot leakage.** No resistor change is required by 40 channels alone. Validate all-grounded, mixed and all-insulated cases with a cut FEED, separately from a cut SENSE.

### 10.7 Scan latency and diagnostic coverage

TC acquisition uses the same 15-slot schedule as §9.7:

    Each TC ADC cycle = 15 ×44.559 =668.4 ms

    Five concurrent banks:
      elapsed conversion time =668.4 ms
      not 5 ×668.4 ms

The RTD ADC requires four measurements with current swapping:

    Four RTDs ×two conversions =eight measurement conversions

Allow four additional internal/diagnostic conversions and **5 ms external settling per excitation configuration**, which is **UNVERIFIED**:

    RTD schedule =
      12 ×44.559 +8 ×5
      =574.7 ms

The maximum allowable settling per configuration before this RTD schedule exceeds the TC conversion schedule is:

    [668.4 −12 ×44.559]/8 ≈16.7 ms

Thus the assumed 5 ms fits; actual RTD/reference filters and lead capacitance must establish the bound.

At 500 kHz, allow 64 bits per ADC transaction:

    TC result reads =5 ×15 =75
    RTD reads =12
    Configuration/status allowance =30 transactions

    Total ADC traffic =117 ×64/500k
                      =15.0 ms

For ten CJ CRC frames on the retained 20 kHz resistor topology:

    CJ bus time =10 ×48/20k =24.0 ms

Add maximum 7.5 ms CJ conversion availability and a **UNVERIFIED 30 ms** bounded software allowance:

    Cycle screen =
      max(668.4,574.7) +15.0 +24.0 +7.5 +30
      ≈745 ms

    Trip-response screen including one extra filter interval
      and 30 ms pump/relay release:
      745 +44.6 +30 ≈820 ms

**Verdict: OK as a concurrent schedule; UNVERIFIED in implementation.** The separate active TMP interface should reduce CJ bus time further.

Required scheduling rules:

* Start and service all six ADCs concurrently.
* Poll deselected ADCs briefly; do not hold CS low while waiting for RDY.
* Evaluate each new temperature immediately.
* Bound retries, LCD work, Modbus handling and EEPROM writes.
* Store timestamps and fault a channel whose acquisition deadline expires.
* A ≤0.5 s watchdog cannot be fed only once per approximately 0.745 s scan. Feed it from verified acquisition progress, while maintaining a separate complete-scan deadline; an independent timer interrupt must not prove scan health.

Diagnostic intervals:

    Burnout revisit per TC channel ≈8 ×0.745 =5.96 s
    Common-mode revisit per AIN ≈16 ×0.745 =11.92 s

These retain the existing rotating-diagnostic concept. They do not satisfy a requirement for every open-wire diagnostic to complete within one second.

**RTD diagnostic gap:** internal zero/nonzero and supply checks fit the timing allocation, but four fully occupied RTD input groups cannot reproduce the TC bank’s independent REF3030 check. Rref drift or some gain errors can remain plausible.

**Verdict: FAILS complete independent RTD reference/gain coverage as currently specified.** Resolve `0039` D5’s independent check before freeze. There is time for an extra precision-resistor measurement if the hardware provides it; timing capacity alone does not provide the check.

### 10.8 Firmware resources: 40 TC + 4 RTD

Use the proposed 24-byte explicit record in §9.8, with type identifiers for K, J and PT100.

    Channel count =40 +4 =44

    EEPROM A/B records =44 ×2 ×24 =2112 B

| EEPROM allocation | Bytes |
|---|---:|
| Channel A/B records | 2112 |
| Global settings A/B | 128 |
| Six-bank calibration allocation | 192 |
| Event allocation | 1024 |
| **Total** | **3456** |
| **Free** | **640** |

**Verdict: fits; EEPROM is the tightest resource.**

If each record grows to 32 bytes while retaining the same extras:

    44 ×2 ×32 +128 +192 +1024 =4160 B

**Verdict: FAILS that enlarged allocation by 64 B.** Keep the serialized record bounded, or reduce the event allocation. A/B records do not require a full configuration-image duplicate.

RAM budget:

| Allocation | Bytes |
|---|---:|
| 44 channels ×40 B | 1760 |
| Communications buffers | 512 |
| Six ADC state/cache allocations | 768 |
| Ten CJ state allocations | 160 |
| Optional Modbus shadow map | 944 |
| LCD/UI storage | 128 |
| Scheduler/global state allowance | 512 |
| Stack reserve | 2048 |
| **Total** | **6832** |
| **Free** | **9552** |

**Verdict: fits comfortably.** A rolling accumulator/IIR allocation is assumed, not an unbounded sample history.

A proposed Modbus map uses ten 16-bit registers per channel, for temperatures, setpoint, hysteresis, type/mode, fault and age/status, plus 32 global registers:

    Map size =44 ×10 +32 =472 registers
    Full shadow storage =472 ×2 =944 B

Generate responses from authoritative channel state where practical. A full map need not fit in one Modbus response.

Flash allocation:

    Common code budget       =64 KiB
    K/J tables, per 0038     ≈2.5 KiB
    PT100 table allocation   ≈1 KiB
    Map/constants allowance  =1 KiB
    Boot reserve             =4 KiB
    Total                   ≈72.5 KiB
    Remaining               ≈55.5 KiB

An illustrative PT100 table spanning −200 to 850 °C in 5 °C steps has:

    Points =(850 −(−200))/5 +1 =211
    At 32-bit resistance entries: 211 ×4 =844 B

Interpolation/quantization error is **UNVERIFIED until checked on the actual table**. Tables belong in flash, not startup-copied SRAM.

**Overall verdict: fits; EEPROM tight if record/event scope grows.** No MCU change is justified by memory capacity. Actual flash size, stack high-water mark and conversion execution time require the family firmware build. Channel masks must cover 44 channels—use byte arrays or an explicitly sized wider representation.

### 10.9 Board-size estimate

Baseline: **170 ×145 mm**, 24,650 mm², **442 BOM parts /466 footprints**; three banks of 97 footprints each.

Estimated base before the RTD circuitry:

    442 +2 ×97 −3 isolator/cap parts
        −9 old CS pull-ups +5 address/enable pull-ups
      =629 BOM parts

Add:

* Decoder, decoupling and island EN definition: approximately three parts.
* RTD ADC, reference resistor, connectors, protection/filter networks and decoupling: **30–50 parts, UNVERIFIED**.
* Controlled TMP command/return interface: approximately **5–10 parts, UNVERIFIED**.

    Estimated BOM parts ≈667–692
    Estimated footprints ≈691–716
      if approximately 24 mechanical/test footprints are retained

At baseline area per BOM part:

    Required area ≈24,650 ×(667–692)/442
                  ≈37,200–38,600 mm²

| Candidate outline | Area | Increase over 24-ch |
|---|---:|---:|
| 220 ×170 mm | 37,400 mm² | 51.7% |
| 220 ×180 mm | 39,600 mm² | 60.6% |

Forty TC channels require 80 terminal positions:

    Terminal pitch length =80 ×3.81 =304.8 mm

That excludes connector end margins, RTD terminals and spacing for CJ thermal regions. Multiple board edges can accommodate it, but the floor plan must demonstrate access and routing.

**Verdict: MARGINAL but plausible at 220 ×170 mm; 220 ×180 mm is a useful reserve envelope.** The proposed 52% area increase matches the estimated component increase closely, leaving little density reserve for the RTD bank and revised data interface. Obtain the preliminary quote using both envelopes, then decide from a to-scale placement.

### 10.10 Findings for the plan (Sol)

* **Retain the 1 W module, LP2985, LM5164, 33 µH inductor and 1 A panel-fuse specification.** Calculated loads fit; both boards still need the 150 Ω preload.
* **The R443 write path fails TMP126’s published edge-time requirement on both boards.** Slow clocks solve sampling-settling time only. Add controlled low-impedance command drive and read turnaround.
* **ADC DOUT loading through 22 kΩ exceeds its 100 µA VOH/VOL test condition.** The new interface should remove that permanent load.
* **Two isolators suffice.** The 40-ch allocation leaves two forward channels spare; separate TMP data also requires direction control and return selection because both reverse channels are occupied.
* **Retained 40-ch resistor-path writes need approximately 20 kHz**, rather than treating 25 kHz as a robust limit; standard AVR hardware SPI cannot reach that rate at 8 MHz.
* **5.11 kΩ Rref with 3.2 kΩ excitation protection fails compliance.** Approximately 3.00 kΩ Rref passes the stated screen, or redesign the excitation protection branch.
* **Four RTD points currently lack an independent Rref/gain check.** Resolve D5 before schematic freeze; available scan time does not close this coverage gap.
* **The inherited TL431 clamp is marginal at tolerance corners:** the conservative threshold bound reaches approximately 3.61 V. Resolve divider/reference tolerance and overshoot before relying on it.
* **Memory fits, but EEPROM needs a bounded record/event allocation.** The proposed 24-byte records fit; 32-byte records plus the stated extras exceed 4 KiB.
* **Use approximately 120 ×110 mm and 220 ×170–180 mm for initial floor plans.** The smaller proposed 8-ch envelope and the 40-ch 220 ×170 mm envelope need placement proof.
### 10.11 PT100 bank: values, compliance, errors, fault coverage (Claude, reviewed by Astra twice, 2026-10-14)

Three PT100 inputs + an on-board 150R 0.1 % check resistor in slot 4 (`0039` P5 (b), after Astra's second review).

Circuit `hardware/family/gen/c_rtd.py`; decision `0039` P4/P5. Source: ADI CN-0383 rev D, "multiple 3-wire
RTDs, reference resistor on the low side" (read 2026-10-14): IOUT0 = IOUT1 = 250 uA with chopping (swap),
a headroom resistor under R_ref because the reference buffers need >= 0.1 V above AVSS, IOUT compliance
AVDD - 0.37 V = 2.93 V at 3.3 V (Astra: the table row includes 250 uA), IOUT reaches any of AIN0-AIN15
(Astra, AD7124-8 table 69), reference detect 0.7-1 V (table 3). CN-0383's own values (5.11k, gain 32) leave
no room for protection resistors (3.355 V > 2.93 V, sec. 10.2), so R_ref is lowered and the gain halved.

| Input | Value |
|---|---|
| I0 = I1 | 250 uA (both in R_ref: 500 uA) |
| R_ref | 2.49k 0.1 % 25 ppm/K (YAGEO RT0805BRD072K49L, LCSC C375522) |
| R_head | 330R 1 % |
| Gain | 16 |
| Excitation branch | 1k 2512 1 W + BAV199 + 100R |
| Sense branch | 2.2k 1206 + BAV199 + 1k; 10n differential, 1n per leg to RTD_RET |
| Return | 1k 2512 1 W per probe into RTD_RET |
| Leads | 50 m, 4 ohm per wire (0.22 mm2) used as the worst case |
| PT100 | 0.385 ohm/degC; 175.9 ohm at 200 degC |

* V_ref = 500 uA x 2.49k = **1.245 V**; at IOUT -10 % and R_ref -0.1 %: 1.119 V, above the 1 V top of
  the reference-detect band. Full scale = 1.245 / 16 = 77.8 mV = 250 uA x **311 ohm** (~ 300 degC).
* REFIN1- = 500 uA x 330R = **0.165 V**; worst (IOUT -10 %, R -1 %) 0.147 V >= 0.1 V. Both buffers on.
* Compliance, worst pin (IOUT0) at full scale: 250 uA x (1k + 100R + 4 + 311) + 500 uA x (4 + 1k + 2.49k
  + 330) = 0.354 + 1.912 = **2.27 V** vs 2.93 V: 0.66 V margin. At 250 ohm 2.25 V (Astra 2.251 V). OK.
* Signal 96 uV/degC. Lead mismatch 0.1 ohm = 0.26 degC. IOUT mismatch cancelled to first order by the swap.
  R_ref 0.1 % = 0.26 degC at 100 ohm. Self-heating 250 uA^2 x 176 ohm = 11 uW; the probe's dissipation
  constant decides the error (UNVERIFIED, small).
* Leakage (Astra): a 10 Mohm contamination path from a sense node at ~1.4 V through 3.2k gives ~0.5 mV
  = ~5 degC. The 1n caps go to RTD_RET: their pads see ~0.5-0.6 V (500 uA crosses the 1k return limiter,
  Astra) instead of ~1.8 V to ground; assembly is washed; hot leakage limit is a bench item (I-120). No
  overall accuracy figure is claimed before the bench.
* Settling: R_ref x 100n = 249 us; 0.01 % after 2.29 ms. Firmware waits, then restarts the filter.
* 24 V on a lead: 20 V across a 1k = 0.4 W -> 2512 1 W; across 2.2k sense = 0.18 W in a 0.25 W 1206;
  clamp current 20 mA into +3V3_ISO, inside the TL431 clamp's ~150 mA (sec. 7.7).

Fault coverage (firmware; all UNVERIFIED until bench fault injection, I-120):

| Fault | Effect | Caught by |
|---|---|---|
| Lead A open / element open | IOUT0 no path, AIN+ floats | out of range / ADC error flag; burnout check |
| Lead B open | IOUT1 no path | swap readings disagree; out of range |
| Lead C or its 1k open; R_ref/R_head open | both currents lose their return | reference detect; out of range |
| A-B or A-C short | ~0 ohm | below -200 degC = fault |
| B-C short | at the element: harmless; at the connector end the return current shares B and C: ~+6 ohm with 4 ohm leads (Astra) | reads ~16 degC HIGH: safe direction (nuisance trip) |
| REFIN cap short | V_ref ~ 0 | reference detect |
| Element or lead of ANY probe to sheath/frame | engine potential pushes current into R_ref: other probes read low (Astra: 6.8 % for one probe via ~10k) | idle test: both currents off, every sense input vs AVSS through the PGA (gain > 1 allows AVSS), must read ~0 V (fault ~0.29 V) |
| R_ref / R_head / IOUT / gain drift | scale error (R_ref +2 % reads 8.25 degC low at 150 degC, Astra) | **check channel: 150R 0.1 % on board through the same network, read every scan** (`0039` P5 (b)); window ~0.3 % = ~1 degC; plus gain-ratio test |

### 10.12 Preliminary cost of the 8-ch and 40-ch boards, scaled from 8.4 (Claude, 2026-10-14) - ESTIMATE

A real JLCPCB quote needs the owner's sign-in and the final Gerbers (8.4); until then the 24-ch quote of 8.4
(10 boards, 4L ENIG, turnkey) is scaled. Every figure is UNVERIFIED.

| USD, 10 boards | 24-ch (8.4, quoted) | 8-ch REV B0 (estimate) | 40-ch (estimate) |
|---|---|---|---|
| Board size | 170 x 145 | 130 x 125 (floor plan v1, 9.11) | ~215 x 140 (floor plan to come) |
| PCB: 25 + (80.20 - 25) x area ratio (with 2 x 5 mm rails) | 80.20 | ~62 | ~93 |
| Setup + stencil + feeders ($3 per extended type) | 127.02 | ~130 | ~150 (about 7 more extended types) |
| Components (8.4: $64.6/board) | 645.78 | ~350 (2 AD7124, 4 TMP126, 1 isolator, ~200 passives fewer) | ~1,060 (3 more AD7124, 4 TMP126, ~270 more parts) |
| SMT + THT + packaging | 44.20 | ~30 | ~70 |
| **Total ex shipping** | **897.20 (89.7/board)** | **~570 (~57/board)** | **~1,370 (~137/board)** |

The component line rests on an AD7124-8 at ~$9-10 each (the largest single item); the fixed setup line makes
the 8-ch's per-board price fall slowly with quantity. Verdict: the 40-ch layout may proceed (0039 D7); the
owner gets the real quote from the release files.

### 9.11 8-ch floor plan v1 and v2 (Claude, 2026-10-14)

`hardware/8ch-new/gen/place.py`: 130 x 125 mm (66 % of the 24-ch area). The 20x4 LCD (98 x 60 mm on standoffs
H6-H9) sets the size: the top edge carries the field terminals and the RS-485 pocket, the LCD shadow holds only
parts lower than ~7 mm (relays G6K 5.2 mm, inductor 4.8 mm; LCD standoffs >= 11 mm), buttons/LEDs/J503 are in
the right column, the barrier band is y 79-82, and the island (bank A, supply, references, engine reference) is
the 43 mm strip below it. 265/265 placed, 0 courtyard overlaps; rules.py: no net in two domains; padcheck 0.
v1 routed (Freerouting 30 passes, 4 threads, ~50 min) to 61 DRC violations / 17 unconnected, then
`finish.py stubs/nori/dangling` 16 / 16: the open ones (relay contacts, +24V, buck SW, chassis bridge) all
had to cross the LCD header row J502 (16 THT pins at 2.54 mm, x 11-51). **v2: 130 x 137 mm**, LCD 13 mm lower,
terminals/relays/input protection above the J502 row, buck and drivers right of it; 0 overlaps.
LCD-on-the-door study (scratch): 115 x 100 mm, 0 overlaps, routed to 64 violations / 15 unconnected.
