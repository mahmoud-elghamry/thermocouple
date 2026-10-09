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
