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
