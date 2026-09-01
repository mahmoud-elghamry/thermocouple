# K-type thermocouple meter

ATmega32A temperature meter with a 16x2 LCD, K-type thermocouple and a
100 C alarm output that drives an LED and a 5 V relay.

## What to submit

- Proteus simulation: use MAX6675 with
  `firmware/build/thermocouple_meter_max6675.hex`.
- Final physical design: use the MAX31856 KiCad PCB in
  `pcb/thermocouple_meter.kicad_pcb`.
- Manufacturing archive: `pcb/output/thermocouple_meter_gerbers.zip`.
- Full Arabic explanation: `docs/PROJECT_GUIDE_AR.md`.
- MCAL/HAL/APP explanation: `docs/SOFTWARE_ARCHITECTURE_AR.md`.
- Pin-by-pin tables: `docs/CONNECTIONS.md`.
- Real mistakes and faster workflow: `docs/LESSONS_LEARNED_AR.md`.
- Component list: `BOM.csv`.

The two MAX devices are intentionally not mixed: MAX6675 is the stable Proteus
simulation fallback; MAX31856 is the requested final hardware.

The relay contact area is labelled for **low-voltage loads only**. The PCB has
passed KiCad DRC, but it has not yet been manufactured or electrically tested.
