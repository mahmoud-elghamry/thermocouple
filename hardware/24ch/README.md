# hardware/24ch — the 24-channel board (REV A3)

One board for all 24 K-type thermocouples (`docs/decisions/0031`), front end
and parts per `docs/decisions/0032` (read all three revisions at its end).
`hardware/8ch/` (REV A2) stays as the reference design and is not modified.

## The schematic is generated

Edit the generator in `gen/`, never the `.kicad_sch` files:

```powershell
cd hardware\24ch\gen
python build.py      # writes the sheets, runs ERC, checks the netlist against the model
```

`build.py` exits non-zero unless ERC has **0 errors and 0 warnings** and every
pin in the exported netlist matches the model in `gen/c_*.py`.

| File | What it holds |
|---|---|
| `gen/c_power.py` | battery input, PTC, protection, LM5164 5 V buck, 5 V crowbar |
| `gen/c_mcu.py` | ATmega1284P, crystal, ISP, LCD header, five buttons |
| `gen/c_iso.py` | B0505S, LP2985, preload, AVDD clamp, 3x ISO7761, REF3030, V_MID/V_BIAS, engine-reference feed/sense |
| `gen/c_out.py` | trip relay (poles in series), alarm relay, isolated RS-485 |
| `gen/c_bank.py` | one bank: 2 headers, 8 input networks, AD7124-8, 2 ADT7310 (used three times) |
| `gen/model.py`, `emit.py`, `libs.py`, `sexp.py`, `customlib.py` | the generator itself |
| `lib/thermo24.kicad_sym` | AD7124-8 and ADT7310 symbols (generated) |

Every page is A4 or A3 (the owner prints nothing bigger): `build.py` splits a
sheet into `<name>_1`, `<name>_2` pages when it would not fit A3, and stops if a
page still comes out larger.

Nets that appear on more than one sheet become global labels automatically;
all others are local. References: banks 1xx/2xx/3xx, isolation 4xx, MCU 5xx,
power 6xx, outputs 7xx.

## The board

Run with KiCad's python (`C:/Program Files/KiCad/10.0/bin/python.exe`), in order:

| Step | Command | What it does |
|---|---|---|
| 1 | `pcb_new.py` (once) | empty 170 x 145 mm 4-layer board |
| 2 | `kicad-tool pcb sync thermo24.kicad_pcb thermo24.kicad_sch` | footprints and nets from the schematic (needs `KICAD10_FOOTPRINT_DIR`) |
| 3 | `place.py` | every footprint per floor plan v2; prints courtyard overlaps (must be 0) |
| 4 | `rules.py` | domains by pad position (a net in two domains stops it), net classes, `.kicad_dru`, planes, barrier keep-outs, U601 thermal vias |
| 5 | `route24.py --passes 30 --threads 4 [--board copy --tag x]` | Freerouting via DSN/SES, then zone refill |
| 6 | `finish.py` / `maze.py` | **incremental only, after a routing result is kept**: DRC, stubs, lock, hand routes (`add`), maze router + rip-up |
| - | `cost.py`, `view.py`, `kicad_ui.ps1`, `padcheck.py` | BOM cost from LCSC; render a region; drive the KiCad GUI; pad-gap check before routing |

Domains: sensor island = x < 42 or y > 103 (mm, y down); barrier bands x 42-45
and y 100-103, 3 mm copper-free on all layers; RS-485 bus pocket x 55-84,
y < 22. `fpinfo.py` lists courtyard sizes.

## Not done yet

See `docs/STATE.md` and I-107 (routing), I-110 (EP vias), I-108 (buttons/silk). Older list:

Routing result and DRC to zero, silkscreen tidy, BOM/LCSC codes for the parts
marked without one, fab outputs, and every "check" item in `0032`.
