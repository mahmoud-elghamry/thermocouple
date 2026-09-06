# Thermocouple meter PCB

Editable two-layer KiCad 10 PCB for an ATmega32A, MAX31856, off-board 16x2
LCD, alarm LED and 5 V SPDT relay. The board is 150 x 70 mm. It accepts a
regulated 5 V input and makes 3.3 V locally with an AMS1117-3.3. The MCU and
MAX31856 run at 3.3 V; the LCD runs at 5 V.

The thermocouple front end follows the MAX31856 application guidance:

- BIAS is connected to T-.
- Matched 100 ohm series resistors are fitted in T+ and T-.
- 100 nF is fitted differentially across T+ and T-.
- 10 nF common-mode capacitors are fitted from each input to ground.
- 100 nF local bypass capacitors are fitted at AVDD and DVDD.

Generate the PCB from the deterministic Python source, run DRC, then export
Gerbers, drill files, PDF and 3D previews:

```powershell
& 'C:\Program Files\KiCad\10.0\bin\python.exe' .\generate_board.py
& .\build_outputs.ps1
```

J2 is a standard 16-pin HD44780 LCD header. J4 is a 6-pin AVR ISP header.
The ATmega32 uses its internal 8 MHz clock, so no crystal is required.

PB3 (DIP pin 4) drives Q1 through R4; Q1 switches the K1 coil. D1 clamps the
coil flyback voltage, R5 keeps the relay off during reset, and D2/R6 indicate
the output state. J5 exposes COM/NO/NC. This contact area is intended only for
low-voltage loads in this revision; it is not documented or certified for mains.

## Delivered fabrication files

- `thermocouple_meter.kicad_pcb`: editable KiCad 10 board.
- `drc-report.txt`: zero violations and zero unconnected pads.
- `gerbers/`: copper, solder-mask, silkscreen, outline and drill files.
- `output/thermocouple_meter_gerbers.zip`: fabrication archive.
- `output/thermocouple_meter_layers.pdf`: printable layer plots.
- `output/positions.csv`: component positions.
- `output/pcb_top.png`, `pcb_bottom.png`, `pcb_isometric.png`: 3D previews.
- `output/kicad_happy_pcb_analysis.json`: extra PCB/DFM analysis.
- `output/kicad_happy_gerber_analysis.json`: extra Gerber analysis.

Three global fiducials are included. The router also forbids layer changes in
pad keepouts, eliminating the via-in-pad warnings found during the additional
DFM pass. The remaining PCB-analyzer warning is low test-point coverage, which
is accepted for this hand-assembled educational revision.

This board is for the **MAX31856 final hardware**. MAX6675 is used only as a
Proteus fallback and is not a pin-compatible replacement for MAX31856.
