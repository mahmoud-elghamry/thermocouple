# hardware/ - which folder is which board

| Folder | Board | Status |
|---|---|---|
| `24ch/` | 24 channels, REV A4, 4 layers | **the board being ordered** (worked in branch `24ch-rev-a4`) |
| `8ch-4l/` | 8 channels, REV B0, 4 layers (130 x 137 mm) | release candidate (`0039`) |
| `8ch-2l/` | the same 8 channels, REV B0-2L, 2 layers for a local fab (150 x 154 mm) | release candidate (`0040`) |
| `40ch/` | 40 thermocouples + 3 PT100, REV A0, 4 layers | release candidate; probably never built (`0043`) |
| `family/` | not a board: the one schematic generator (`gen/`) and the board tools (`tools/`) shared by 8/24/40 | - |
| `8ch-old/` | the old 8-channel REV A2 (MAX31856) | reference only, never ordered again |
| `single-channel/` | the first single-channel board | superseded - do not modify |

Inside a board folder: `<project>.kicad_pro/.kicad_sch/.kicad_pcb` is the design, `gen/` the scripts that
made it, `STATE.md` where it stands, `output/` local scratch (not tracked). The generated schematic pages are
named by what they hold, e.g. `bank_a_1_inputs` (terminals, channel front ends) and `bank_a_2_adc`
(AD7124-8, cold-junction sensors); each page's title block lists its blocks (8ch-4l, 8ch-2l, 40ch; the
24-ch board keeps `bank_a_1` etc. until its own generator in the branch is changed).
Releases are in `production/` (see `production/README.md`).
