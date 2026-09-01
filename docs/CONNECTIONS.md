# Circuit connections

There are two deliberately separate variants:

- **Physical PCB and final hardware:** MAX31856, because it is the converter
  requested in the assignment and supports K-type thermocouples with cold-junction
  compensation and fault reporting.
- **Proteus simulation fallback:** MAX6675, because the installed MAX31856 model
  raises an internal `DSIM.DLL` access-violation in this Proteus installation.
  This fallback proves the ATmega32, SPI reading, temperature formatting and LCD.

## ATmega32A to MAX31856

| Signal | ATmega32A DIP pin | MAX31856 pin |
|---|---:|---:|
| CS | PB4, pin 5 | CS, pin 9 |
| MOSI | PB5, pin 6 | SDI, pin 12 |
| MISO | PB6, pin 7 | SDO, pin 11 |
| SCK | PB7, pin 8 | SCK, pin 10 |
| 3.3 V | VCC pin 10, AVCC pin 30 | AVDD pin 5, DVDD pin 8 |
| Ground | pins 11 and 31 | AGND pin 1, DGND pin 14 |

MAX31856 DNC pin 6 is left unconnected. DRDY and FAULT are brought to test
points. BIAS pin 2 is connected to the filtered T- node.

At startup, the MAX31856 firmware selects K-type, enables the 50 Hz rejection
filter and a 10 ms open-circuit test once every 16 conversions. It reads CR0 and
CR1 back before accepting the sensor as ready. A failed read/write is reported
as `FAULT: SPI` or `FAULT: INIT`; the associated temperature is marked invalid
instead of being shown or used for the alarm decision.

## ATmega32A to LCD 16x2

| LCD signal | LCD pin | ATmega32A |
|---|---:|---|
| VSS | 1 | Ground |
| VDD | 2 | 5 V |
| VO | 3 | 10k contrast potentiometer wiper |
| RS | 4 | PA0, pin 40 |
| RW | 5 | Ground |
| E | 6 | PA1, pin 39 |
| D4 | 11 | PA4, pin 36 |
| D5 | 12 | PA5, pin 35 |
| D6 | 13 | PA6, pin 34 |
| D7 | 14 | PA7, pin 33 |
| LED A | 15 | 5 V through 100 ohm |
| LED K | 16 | Ground |

LCD pins D0-D3 are left unconnected because the firmware uses 4-bit mode.

### LCD contrast (important in Proteus)

`VEE/VO`, LCD pin 3, must **not** be tied directly to +5 V. That makes the
display backlight visible while the characters disappear. For a quick simulation,
connect pin 3 directly to ground. The final PCB uses a 10 kOhm potentiometer:

- one outer pin to +5 V;
- the other outer pin to ground;
- the wiper to LCD pin 3 (`VEE/VO`).

## ATmega32A to MAX6675 (Proteus fallback)

| Signal | ATmega32A DIP pin | MAX6675 Proteus pin |
|---|---:|---:|
| CS | PB4, pin 5 | CS, pin 6 |
| SO / MISO | PB6, pin 7 | SO, pin 7 |
| SCK | PB7, pin 8 | SCK, pin 5 |

PB5/MOSI is not used by MAX6675 because the device is read-only. The MAX6675
firmware uses SPI mode 1 (data sampled on SCK's falling edge); the MAX31856
firmware also uses SPI mode 1.

MAX6675 `T-`, pin 2, must be connected both to the thermocouple negative lead
and to ground.  Without this ground reference the open-thermocouple detector can
report `FAULT: OPEN` and the temperature frame is not valid.

## Proteus properties

- ATMEGA32 `Program File` for the current MAX6675 simulation:
  `firmware/build/thermocouple_meter_max6675.hex`
- ATMEGA32 `Program File` for a working MAX31856 model:
  `firmware/build/thermocouple_meter_max31856.hex`
- ATMEGA32 `Clock Frequency`: `8MHz`
- ATMEGA32 `CKSEL Fuses`: `(0100) Int.RC 8MHz`
- MAX31856 `TCJ`: `27` (only for the MAX31856 model)
- Thermocouple device: `TCK`
- LCD device: `LM016L`
- MAX6675 `TAMB`: set to `0` for a one-to-one Proteus demonstration where the
  LCD value should equal the TCK setpoint.  Leaving the model default of `25 C`
  adds about 25 C of cold-junction compensation to the displayed value.

Expected MAX6675 display at a 100.0 C thermocouple setting:

```text
Temp: + 100.0°C
Sensor: OK
```

## Alarm LED / relay output

The same application logic is compiled into both HEX variants. The alarm uses
`PB3`, which is physical pin **4** on the ATmega32A DIP-40.

- It turns ON when the measured/displayed temperature reaches `100.0 C`.
- It stays ON while the temperature is between `95.0 C` and `100.0 C`.
- It turns OFF at `95.0 C` or below.
- By default any invalid/faulty sample forces it OFF. This is the safe policy
  for a heater and is controlled by `APP_ALARM_ON_SENSOR_FAULT`.

The separate ON and OFF temperatures are hysteresis. They stop a relay from
rapidly clicking when the reading moves slightly around 100 C.

### Simple Proteus LED test

| From | Part | To |
|---|---|---|
| ATmega32 PB3, physical pin 4 | 330 ohm to 1 kohm resistor | LED anode |
| LED cathode | wire | Ground |

Do not connect a relay coil directly to PB3. For a relay simulation use:

| Connection | Destination |
|---|---|
| PB3, pin 4 | 1 kohm -> 2N3904 base |
| 2N3904 emitter | Ground |
| 2N3904 collector | Relay-coil negative end |
| Relay-coil positive end | +5 V |
| 1N4007 across coil | Cathode to +5 V, anode to collector |

The physical KiCad board already contains this driver as R4, R5, Q1, D1, K1,
plus status LED D2/R6. Relay contacts are exported on J5 as COM, NO and NC.
