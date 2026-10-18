"""Board data only; circuit blocks remain plain functions (owner's 0039 brief)."""
from dataclasses import dataclass, replace
from pathlib import Path

NC = "<NC>"
MCU24 = {
    "PB0": "CS_ADC2", "PB1": "CS_ADC3", "PB2": "CS_CJ1", "PB3": "RUN_PERMIT",
    "PB4": "CS_ADC1", "PB5": "MOSI", "PB6": "MISO", "PB7": "SCK",
    "PC0": "CS_CJ2", "PC1": "CS_CJ3", "PC2": "RUN_SENSE", "PC3": "CS_CJ4",
    "PC4": "CS_CJ5", "PC5": "CS_CJ6", "PC6": "ALARM_DRIVE", "PC7": "ALARM_SENSE",
    "PD0": "UART_RX", "PD1": "UART_TX", "PD2": "BTN_UP", "PD3": "BTN_DOWN",
    "PD4": "BTN_SET", "PD5": "BTN_ESC", "PD6": "BTN_ACK", "PD7": "RS485_DE",
    "PA0": "LCD_RS", "PA1": "LCD_E", "PA2": "REFOK", "PA3": "REFTEST",
    "PA4": "LCD_D4", "PA5": "LCD_D5", "PA6": "LCD_D6", "PA7": "LCD_D7",
    "~{RESET}": "RESET_N", "XTAL1": "XTAL1", "XTAL2": "XTAL2", "AREF": "AREF",
    "VCC": "+5V", "AVCC": "+5V", "GND": "GND",
}


@dataclass(frozen=True)
class Isolator:
    ref: str
    forward_in: tuple
    reverse_out: str
    forward_out: tuple
    reverse_in: str
    caps: tuple


@dataclass(frozen=True)
class Board:
    key: str
    project: str
    root_title: str
    library: str
    bank_count: int
    bank_letters: tuple
    mcu_pins: dict
    chip_selects: tuple
    cs_pullups: tuple                  # (reference, control-side net)
    isolators: tuple
    mounting_holes: tuple             # (number, kind: island/chassis/lcd/plain)
    output_folder: Path
    revision: str
    isolator_title: str
    bank_bases: tuple = (100, 200, 300)   # reference base per bank; 4xx-7xx belong to isolation/MCU/power/outputs
    sio_driver: bool = False              # 0039: gated TMP126 SIO driver instead of R443 22k (I-124)
    decoder: bool = False                 # 0039 D3: 74HC154 chip-select decoder on the island
    rtd: bool = False                     # 0039 D5: RTD bank (four 3-wire PT100)
    sync_tied: bool = False               # 0039 P8: AD7124 SYNC tied to +3V3_ISO, no 10k pull-up

    @property
    def channel_count(self):
        return 8 * self.bank_count


CS24 = ("CS_ADC1", "CS_ADC2", "CS_ADC3") + tuple(f"CS_CJ{i}" for i in range(1, 7))
HOLES = tuple((i, "island") for i in (1, 2, 3, 10)) + ((4, "chassis"), (5, "chassis"))
HOLES += tuple((i, "lcd") for i in range(6, 10))
OUT = Path(__file__).resolve().parents[1] / "out"
B24 = Board(
    "24", "thermo24", "Thermo 24-channel protection unit - REV A3", "thermo24",
    3, tuple("ABC"), MCU24, CS24, tuple((f"R{430+i}", n) for i, n in enumerate(CS24)),
    (
        Isolator("U403", ("SCK", "MOSI", "CS_ADC1", "CS_ADC2", "CS_ADC3"), "MISO_ISO",
                 ("SCLK_ISO_RAW", "DIN_ISO_RAW", "CS_ADC1_ISO", "CS_ADC2_ISO", "CS_ADC3_ISO"),
                 "DOUT_ISO_RAW", ("C407", "C408")),
        Isolator("U404", tuple(f"CS_CJ{i}" for i in range(1, 6)), "REFOK",
                 tuple(f"CS_CJ{i}_ISO" for i in range(1, 6)), "REFOK_ISO", ("C409", "C410")),
        Isolator("U405", ("CS_CJ6", "REFTEST", "GND", "GND", "GND"), NC,
                 ("CS_CJ6_ISO", "REFTEST_ISO", NC, NC, NC), "GND_ISO", ("C411", "C412")),
    ), HOLES, OUT / "24", "A3", "Digital isolators: SPI to the three AD7124 and six TMP126",
)
CS8 = ("CS_ADC1", "CS_CJ1", "CS_CJ2")
B8 = replace(
    B24, key="8", project="thermo8", library="thermo8", revision="B0",
    root_title="Thermo 8-channel protection unit - REV B0", bank_count=1, bank_letters=("A",),
    mcu_pins={p: ("SIO_WR_N" if p == "PC1" else NC if n in set(CS24) - set(CS8) else n)
              for p, n in MCU24.items()},
    chip_selects=CS8,
    cs_pullups=(("R430", "CS_ADC1"), ("R433", "CS_CJ1"), ("R434", "CS_CJ2"), ("R439", "SIO_WR_N")),
    isolators=(
        Isolator("U403", ("SCK", "MOSI", "CS_ADC1", "CS_CJ1", "CS_CJ2"), "MISO_ISO",
                 ("SCLK_ISO_RAW", "DIN_ISO_RAW", "CS_ADC1_ISO", "CS_CJ1_ISO", "CS_CJ2_ISO"),
                 "DOUT_ISO_RAW", ("C407", "C408")),
        Isolator("U404", ("REFTEST", "SIO_WR_N", "GND", "GND", "GND"), "REFOK",
                 ("REFTEST_ISO", "SIO_WR_N_ISO", NC, NC, NC), "REFOK_ISO", ("C409", "C410")),
    ), output_folder=OUT / "8", isolator_title="Digital isolators: SPI to one AD7124 and two TMP126",
    sio_driver=True, sync_tied=True,
    # H4 plain NPTH: on the 8-ch a CHASSIS track to it crossed the relay contacts; H5 + J601 bond CHASSIS
    mounting_holes=tuple((i, "plain") if i == 4 else (i, k) for i, k in HOLES),
)
# 40-ch (0039): chip selects decoded on the island; MCU drives A0-A3 + EN (5 pins instead of 16)
MCU40 = dict(MCU24, PB0="CSA0", PB1="CSA1", PB2="CSA2", PB4="CS_EN", PC0="CSA3", PC1="SIO_WR_N",
             PC3=NC, PC4=NC, PC5=NC)
B40 = replace(
    B24, key="40", project="thermo40", library="thermo40", revision="A0",
    root_title="Thermo 40-channel protection unit, 4 PT100 - REV A0", bank_count=5,
    bank_letters=tuple("ABCDE"), bank_bases=(100, 200, 300, 800, 900), mcu_pins=MCU40,
    chip_selects=("CS_EN",), cs_pullups=(("R430", "CS_EN"), ("R439", "SIO_WR_N")),
    isolators=(
        Isolator("U403", ("SCK", "MOSI", "CSA0", "CSA1", "CSA2"), "MISO_ISO",
                 ("SCLK_ISO_RAW", "DIN_ISO_RAW", "CSA0_ISO", "CSA1_ISO", "CSA2_ISO"),
                 "DOUT_ISO_RAW", ("C407", "C408")),
        Isolator("U404", ("CSA3", "CS_EN", "REFTEST", "SIO_WR_N", "GND"), "REFOK",
                 ("CSA3_ISO", "CS_EN_ISO", "REFTEST_ISO", "SIO_WR_N_ISO", NC), "REFOK_ISO", ("C409", "C410")),
    ), output_folder=OUT / "40",
    isolator_title="Digital isolators: SPI, chip-select address and enable for six AD7124 and ten TMP126",
    sio_driver=True, decoder=True, rtd=True, sync_tied=True,
)
BOARDS = {b.key: b for b in (B24, B8, B40)}
