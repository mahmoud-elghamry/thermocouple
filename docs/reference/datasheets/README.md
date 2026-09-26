# Datasheets

The documents this design was actually reasoned against. Downloaded 2026-09-10.

Tracked on purpose. A hardware project that cites a clamping voltage or an
input range should be able to show where the number came from, and manufacturer
URLs rot. About 23 MB in total.

| File | Part | What it settles here |
|---|---|---|
| `ATmega32A.pdf` | ATmega32A | fuse map (`firmware/fuses.md`): `CKSEL` for internal RC 8 MHz, BOD levels, and that **JTAGEN is programmed from the factory and occupies PC2-PC5** |
| `TSR1-series.pdf` | Traco TSR 1-2450 (`U14`) | input range **6.5-36 V**, which is what carries a cranking dip and what fails on a 58 V load dump (`I-028`) |
| `R-78HB-0.5.pdf` | Recom R-78HB (candidate) | input **9-72 V**, 0.5 A. The wide-input candidate - note the 9 V minimum is *worse* for cranking than the 6.5 V fitted part |
| `G5LE-relay.pdf` | Omron G5LE-1 DC24 (`K1`) | coil 1.44 kOhm / 16.7 mA, must-operate 18 V, **must-release 2.4 V** - why an energised relay does not drop out during a cranking dip |
| `ISO7760.pdf` | TI ISO7760 (`U10`) | six-channel digital isolator, control to sensor island |
| `ISO7761.pdf` | TI ISO7761 (`U11`) | five-forward/one-reverse isolator, carries MISO back |
| `LP2985.pdf` | TI LP2985-3.3 (`U13`) | the 3.3 V sensor-island regulator chosen in `docs/decisions/0002` |
| `LM74930.pdf` | TI LM74930-Q1 | not fitted. An ISO 16750-2 load-dump protection controller, kept as the reference for what the battery case in `I-028` would actually need |
| `MAX31856.pdf` | Maxim MAX31856 (`U2`-`U9`), 19-7534 Rev 0, from LCSC `C116632` (analog.com blocked the workstation), added 2026-09-26 | **T- is biased to ~0.735 V by the BIAS output**, and the typical circuit ties BIAS to T- with a floating thermocouple - so the ungrounded probes of `0008` need no extra resistor (`I-027`). BIAS floats between conversions, which is why the firmware runs continuous mode |

## Not here

Analog Devices blocks automated download, so these two are by URL only:

- **MAX31856** (`U2`..`U9`, the thermocouple front end) -
  https://www.analog.com/media/en/technical-documentation/data-sheets/max31856.pdf
- **ADM2582E/ADM2587E** (`U15`, isolated RS-485) -
  https://www.analog.com/media/en/technical-documentation/data-sheets/adm2582e-2587e.pdf

The MAX31856 is the most important document in this list and it is the one
missing. Fetch it by hand and drop it in.

Also not downloaded: `IA0505S` (`U12`, XP Power), the SMBJ TVS series
(`D2`; Littelfuse blocks download - the SMBJ33A figures used in `I-028` are
33 V standoff, 36.7-40.6 V breakdown, 53.3 V clamping, 600 W at 10/1000 us),
`SS34`, `1N4007`, `2N7000`.

## Adding one

Keep the filename the part name, add a row above saying **what question the
document answers for this project** - not what the part is. A datasheet nobody
can say the purpose of is a 3 MB file nobody opens.
