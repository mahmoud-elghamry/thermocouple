"""Populate the KiCad 10 schematic through kicad-tool.

The .kicad_sch file is never edited as text here.  This script uses the
project's pinned kicad-tool environment for every structural schematic edit.
It is intentionally idempotent so interrupted runs can be resumed.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCH = ROOT / "thermocouple_8ch.kicad_sch"
KICAD_ROOT = Path(r"C:\Program Files\KiCad\10.0")
SYMBOL_ROOT = KICAD_ROOT / "share" / "kicad" / "symbols"
DEFAULT_TOOL = Path(
    r"C:\Users\malgh\AppData\Local\Temp\thermo-kicad-tool-venv\Scripts\kicad-tool.exe"
)
TOOL = Path(os.environ.get("KICAD_TOOL", DEFAULT_TOOL))
os.environ.setdefault("KICAD_CLI", str(KICAD_ROOT / "bin" / "kicad-cli.exe"))


@dataclass
class Part:
    ref: str
    lib_id: str
    at: tuple[float, float]
    value: str
    footprint: str
    nets: dict[str, str] = field(default_factory=dict)
    rotation: int = 0
    manufacturer: str = ""
    mpn: str = ""
    datasheet: str = ""
    function: str = ""


LIB_FILES = {
    "Device": "Device.kicad_sym",
    "MCU_Microchip_ATmega": "MCU_Microchip_ATmega.kicad_sym",
    "Sensor_Temperature": "Sensor_Temperature.kicad_sym",
    "Isolator": "Isolator.kicad_sym",
    "Converter_DCDC": "Converter_DCDC.kicad_sym",
    "Regulator_Linear": "Regulator_Linear.kicad_sym",
    "Interface_UART": "Interface_UART.kicad_sym",
    "Relay": "Relay.kicad_sym",
    "Connector_Generic": "Connector_Generic.kicad_sym",
    "Switch": "Switch.kicad_sym",
    "Transistor_FET": "Transistor_FET.kicad_sym",
    "power": "power.kicad_sym",
}


def run(*args: str, json_output: bool = False) -> dict | str:
    command = [str(TOOL), *map(str, args)]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=os.environ,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if json_output:
        return json.loads(completed.stdout)
    return completed.stdout


def current_symbols() -> dict[str, dict]:
    data = run("sch", "query", "list", str(SCH), "symbols", "--format", "json", json_output=True)
    return {item["ref"]: item for item in data["items"]}


parts: list[Part] = []


def add(part: Part) -> None:
    parts.append(part)


def resistor(ref: str, value: str, at: tuple[float, float], a: str, b: str,
             function: str, rotation: int = 90) -> None:
    add(Part(ref, "Device:R", at, value, "Resistor_SMD:R_0805_2012Metric",
             {"1": a, "2": b}, rotation, function=function))


def capacitor(ref: str, value: str, at: tuple[float, float], a: str, b: str,
              function: str, footprint: str = "Capacitor_SMD:C_0805_2012Metric") -> None:
    add(Part(ref, "Device:C", at, value, footprint, {"1": a, "2": b},
             function=function))


# MCU and eight measurement channels.  The CS map exactly matches board.c.
add(Part(
    "U1", "MCU_Microchip_ATmega:ATmega16L-8P", (42, 174), "ATmega32A-PU",
    # Plain socket pads, not LongPads: at 2.54 mm pitch a 2.4 mm pad leaves
    # 0.14 mm between neighbours, so nothing can be routed between the
    # MCU pins and every signal has to escape around the outside of the
    # package.  1.6 mm pads leave 0.94 mm, enough for one 0.25 mm track.
    "Package_DIP:DIP-40_W15.24mm_Socket",
    {
        "1": "CS1_CTRL", "2": "CS2_CTRL", "3": "CS3_CTRL", "4": "RUN_PERMIT",
        "5": "CS4_CTRL", "6": "MOSI_CTRL", "7": "MISO_CTRL", "8": "SCK_CTRL",
        "9": "RESET_N", "10": "+5V_CTRL", "11": "GND_CTRL", "14": "UART_RX",
        "15": "UART_TX", "16": "BTN_NEXT", "17": "BTN_UP", "18": "BTN_DOWN",
        "19": "BTN_SET", "20": "BTN_ACK", "21": "RS485_DE", "22": "CS5_CTRL",
        "23": "CS6_CTRL", "24": "SPARE_PC2", "25": "SPARE_PC3",
        "26": "SPARE_PC4", "27": "SPARE_PC5", "28": "CS7_CTRL",
        "29": "CS8_CTRL", "30": "+5V_CTRL",
        "31": "GND_CTRL", "32": "AREF", "33": "LCD_D7", "34": "LCD_D6",
        "35": "LCD_D5", "36": "LCD_D4", "37": "SPARE_PA3", "38": "SPARE_PA2",
        "39": "LCD_E", "40": "LCD_RS",
    },
    manufacturer="Microchip Technology", mpn="ATMEGA32A-PU",
    datasheet="https://ww1.microchip.com/downloads/aemDocuments/documents/OTH/ProductDocuments/DataSheets/ATmega32A-DataSheet-Complete-DS40002072A.pdf",
    function="5 V local protection controller; fitted in a DIP-40 socket",
))

channel_rows = [22, 56, 90, 124]
channel_columns = [(12, 70), (158, 216)]
for channel in range(1, 9):
    column = 0 if channel <= 4 else 1
    row_index = (channel - 1) % 4
    connector_x, max_x = channel_columns[column]
    y = channel_rows[row_index]
    max_ref = f"U{channel + 1}"
    jref = f"JTC{channel}"
    add(Part(
        jref, "Connector_Generic:Conn_01x03", (connector_x, y), f"TC{channel}_K_TYPE",
        "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-3_1x03_P5.00mm_Horizontal",
        {"1": f"TC{channel}_RAW_P", "2": f"TC{channel}_RAW_N", "3": "CHASSIS_SHIELD"},
        manufacturer="Phoenix Contact", mpn="1935161",
        function=f"Channel {channel} thermocouple +, -, and cable shield",
    ))
    add(Part(
        max_ref, "Sensor_Temperature:MAX31856", (max_x, y), "MAX31856MUD+",
        "Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
        {
            "1": "GND_SENS", "2": f"TC{channel}_FILT_N", "3": f"TC{channel}_FILT_N",
            "4": f"TC{channel}_FILT_P", "5": "+3V3_SENS", "7": f"CH{channel}_DRDY",
            "8": "+3V3_SENS", "9": f"CS{channel}_SENS", "10": "SCK_SENS",
            "11": f"MISO_CH{channel}", "12": "MOSI_SENS", "13": f"CH{channel}_FAULT",
            "14": "GND_SENS",
        },
        manufacturer="Analog Devices", mpn="MAX31856MUD+",
        datasheet="https://www.analog.com/media/en/technical-documentation/data-sheets/max31856.pdf",
        function=f"Channel {channel} cold-junction compensated K-type converter",
    ))
    rbase = (channel - 1) * 2 + 1
    cbase = (channel - 1) * 5 + 1
    local_x = connector_x + 20
    resistor(f"R{rbase}", "100R 0.1%", (local_x, y - 3), f"TC{channel}_RAW_P",
             f"TC{channel}_FILT_P", f"CH{channel} balanced input series resistor")
    resistor(f"R{rbase + 1}", "100R 0.1%", (local_x, y + 3), f"TC{channel}_RAW_N",
             f"TC{channel}_FILT_N", f"CH{channel} balanced input series resistor")
    capacitor(f"C{cbase}", "100n C0G 50V", (local_x + 9, y), f"TC{channel}_FILT_P",
              f"TC{channel}_FILT_N", f"CH{channel} differential EMI filter")
    capacitor(f"C{cbase + 1}", "10n C0G 50V", (local_x + 15, y - 3),
              f"TC{channel}_FILT_P", "GND_SENS", f"CH{channel} common-mode filter +")
    capacitor(f"C{cbase + 2}", "10n C0G 50V", (local_x + 15, y + 3),
              f"TC{channel}_FILT_N", "GND_SENS", f"CH{channel} common-mode filter -")
    capacitor(f"C{cbase + 3}", "100n X7R", (max_x - 3, y - 13), "+3V3_SENS",
              "GND_SENS", f"CH{channel} MAX31856 AVDD decoupling")
    capacitor(f"C{cbase + 4}", "100n X7R", (max_x + 3, y - 13), "+3V3_SENS",
              "GND_SENS", f"CH{channel} MAX31856 DVDD decoupling")

for channel in range(1, 9):
    resistor(f"R{16 + channel}", "10k", (112 if channel <= 4 else 272,
              channel_rows[(channel - 1) % 4]), "+3V3_SENS", f"CS{channel}_SENS",
              f"CH{channel} CS default-high fail-safe pull-up", rotation=0)

# Two six-channel isolators provide 10 forward SPI/control channels and one reverse MISO.
add(Part(
    "U10", "Isolator:ISO7760DW", (126, 55), "ISO7760FDWR",
    "Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm",
    {"1": "+5V_CTRL", "2": "SCK_CTRL", "3": "MOSI_CTRL", "4": "CS1_CTRL",
     "5": "CS2_CTRL", "6": "CS3_CTRL", "7": "CS4_CTRL", "8": "GND_CTRL",
     "9": "GND_SENS", "10": "CS4_SENS_RAW", "11": "CS3_SENS_RAW",
     "12": "CS2_SENS_RAW", "13": "CS1_SENS_RAW", "14": "MOSI_SENS_RAW",
     "15": "SCK_SENS_RAW", "16": "+3V3_SENS"},
    manufacturer="Texas Instruments", mpn="ISO7760FDWR",
    datasheet="https://www.ti.com/lit/ds/symlink/iso7760.pdf",
    function="Reinforced digital isolation for SPI clock, MOSI, and CS1-CS4",
))
add(Part(
    "U11", "Isolator:ISO7761DW", (126, 98), "ISO7761FDWR",
    "Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm",
    {"1": "+5V_CTRL", "2": "CS5_CTRL", "3": "CS6_CTRL", "4": "CS7_CTRL",
     "5": "CS8_CTRL", "6": "GND_CTRL", "7": "MISO_CTRL",
     "8": "GND_CTRL", "9": "GND_SENS", "10": "MISO_SENS_RAW",
     "11": "ISO_SPARE_SENS", "12": "CS8_SENS_RAW", "13": "CS7_SENS_RAW",
     "14": "CS6_SENS_RAW", "15": "CS5_SENS_RAW", "16": "+3V3_SENS"},
    manufacturer="Texas Instruments", mpn="ISO7761FDWR",
    datasheet="https://www.ti.com/lit/ds/symlink/iso7761.pdf",
    function="Reinforced digital isolation for CS5-CS8 and reverse MISO",
))
capacitor("C41", "100n X7R", (116, 43), "+5V_CTRL", "GND_CTRL", "U10 control-side decoupling")
capacitor("C42", "100n X7R", (136, 43), "+3V3_SENS", "GND_SENS", "U10 sensor-side decoupling")
capacitor("C43", "100n X7R", (116, 112), "+5V_CTRL", "GND_CTRL", "U11 control-side decoupling")
capacitor("C44", "100n X7R", (136, 112), "+3V3_SENS", "GND_SENS", "U11 sensor-side decoupling")

resistor("R25", "33R", (142, 51), "SCK_SENS_RAW", "SCK_SENS", "SPI source termination")
resistor("R26", "33R", (142, 56), "MOSI_SENS_RAW", "MOSI_SENS", "SPI source termination")
resistor("R27", "33R", (142, 101), "MISO_SENS", "MISO_SENS_RAW", "MISO source termination")
for channel in range(1, 9):
    resistor(f"R{35 + channel}", "22R", (148, 63 + channel * 4),
             f"CS{channel}_SENS_RAW", f"CS{channel}_SENS", f"CH{channel} CS edge damping")
for channel in range(1, 9):
    resistor(f"R{44 + channel}", "100R", (98 if channel <= 4 else 244,
             channel_rows[(channel - 1) % 4] + 9), f"MISO_CH{channel}", "MISO_SENS",
             f"CH{channel} SDO bus isolation/damping")

# Power tree: protected 24 V -> 5 V control, plus one shared isolated sensor supply.
add(Part("J1", "Connector_Generic:Conn_01x03", (187, 179), "24V_INPUT",
         "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-3_1x03_P5.00mm_Horizontal",
         {"1": "+24V_RAW", "2": "GND_CTRL", "3": "CHASSIS_SHIELD"},
         function="24 VDC field supply and protective/shield terminal"))
add(Part("F1", "Device:Polyfuse", (200, 174), "PTC 0.5A", "Fuse:Fuse_1206_3216Metric",
         {"1": "+24V_RAW", "2": "+24V_FUSED"}, function="Resettable input over-current protection"))
add(Part("D1", "Device:D_Schottky", (208, 174), "SS34", "Diode_SMD:D_SMA",
         {"2": "+24V_FUSED", "1": "+24V_PROT"}, function="Series reverse-polarity protection"))
add(Part("D2", "Device:D_TVS", (211, 184), "SMBJ33A", "Diode_SMD:D_SMB",
         {"1": "+24V_PROT", "2": "GND_CTRL"}, function="24 V input transient clamp"))
add(Part("U14", "Converter_DCDC:TSR_1-2450", (221, 174), "TSR 1-2450",
         "Converter_DCDC:Converter_DCDC_TRACO_TSR-1_THT", {"1": "+24V_PROT", "2": "GND_CTRL", "3": "+5V_CTRL"},
         manufacturer="Traco Power", mpn="TSR 1-2450",
         datasheet="https://www.tracopower.com/products/tsr1.pdf", function="24 V to regulated 5 V control rail"))
capacitor("C53", "47u 50V", (215, 190), "+24V_PROT", "GND_CTRL", "24 V bulk reservoir", "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm")
capacitor("C54", "2.2u 50V X7R", (218, 190), "+24V_PROT", "GND_CTRL", "Buck input bypass")
capacitor("C55", "10u 10V X7R", (225, 190), "+5V_CTRL", "GND_CTRL", "5 V rail bulk bypass")

add(Part("U12", "Converter_DCDC:IA0305S", (126, 145), "IA0505S",
         "Converter_DCDC:Converter_DCDC_XP_POWER-IAxxxxS_THT",
         {"1": "+5V_CTRL", "2": "GND_CTRL", "4": "NEG5_UNUSED",
          "5": "GND_SENS", "6": "+5V_ISO"},
         manufacturer="XP Power", mpn="IA0505S", datasheet="https://www.xppower.com/pdfs/SF_IA.pdf",
         function="Shared 1 kV functional-isolation supply for the measurement island"))
# LP2985-3.3 is a derived symbol and kicad-tool imports pins from the base
# symbol only, so the base is instantiated and the Value field carries the
# actual ordering part - same pattern the AP2112K used before it.
add(Part("U13", "Regulator_Linear:LP2985-1.8", (158, 145), "LP2985-3.3",
         "Package_TO_SOT_SMD:SOT-23-5",
         # Pin-for-pin identical to the AP2112K it replaces (1 VIN, 2 GND,
         # 3 enable, 4 bypass, 5 VOUT) but rated to 16 V in instead of 6 V.
         # U12 is an unregulated module: at the ~12% load this island draws its
         # output can sit near 6 V, which is the AP2112K's ceiling.  A 16 V part
         # removes that margin problem outright, and does it without moving to a
         # regulated module - every regulated 1 W module available here has a
         # 2.54 mm pin pitch, which would have cut the isolation gap under the
         # supply from 3.23 mm to 0.94 mm.  Keeping the barrier wide matters
         # more than where the regulation happens.
         {"1": "+5V_ISO", "2": "GND_SENS", "3": "+5V_ISO", "5": "+3V3_SENS"},
         manufacturer="Texas Instruments", mpn="LP2985IM5X-3.3/NOPB",
         datasheet="https://www.ti.com/lit/ds/symlink/lp2985.pdf",
         function="Low-noise 3.3 V regulator for the isolated measurement island"))
capacitor("C45", "10u 10V", (117, 145), "+5V_CTRL", "GND_CTRL", "Isolated converter input bypass")
capacitor("C46", "10u 10V", (137, 145), "+5V_ISO", "GND_SENS", "Isolated converter output bypass")
capacitor("C47", "1u X7R", (151, 145), "+5V_ISO", "GND_SENS", "LDO input bypass")
capacitor("C48", "4.7u X7R 16V", (165, 145), "+3V3_SENS", "GND_SENS", "LDO output bypass")

# Controller support, panel LCD, local buttons and ISP.
capacitor("C49", "100n X7R", (25, 158), "+5V_CTRL", "GND_CTRL", "MCU VCC decoupling")
capacitor("C50", "100n X7R", (31, 158), "+5V_CTRL", "GND_CTRL", "MCU AVCC decoupling")
capacitor("C51", "100n X7R", (37, 158), "AREF", "GND_CTRL", "MCU AREF bypass")
capacitor("C52", "10n X7R", (43, 158), "RESET_N", "GND_CTRL", "Reset EMI filter compatible with ISP")
resistor("R28", "10k", (50, 158), "+5V_CTRL", "RESET_N", "MCU reset pull-up", rotation=0)
add(Part("J2", "Connector_Generic:Conn_01x16", (78, 176), "LCD_16x2_HEADER",
         "Connector_PinHeader_2.54mm:PinHeader_1x16_P2.54mm_Vertical",
         {"1": "GND_CTRL", "2": "+5V_CTRL", "3": "LCD_VO", "4": "LCD_RS", "5": "GND_CTRL",
          "6": "LCD_E", "11": "LCD_D4", "12": "LCD_D5", "13": "LCD_D6", "14": "LCD_D7",
          "15": "LCD_LED_A", "16": "GND_CTRL"}, function="Panel-mounted HD44780-compatible LCD"))
add(Part("RV1", "Device:R_Potentiometer", (91, 176), "10k LCD CONTRAST",
         "Potentiometer_THT:Potentiometer_Bourns_3296W_Vertical", {"1": "GND_CTRL", "2": "LCD_VO", "3": "+5V_CTRL"},
         function="LCD contrast adjustment"))
resistor("R29", "220R", (84, 158), "+5V_CTRL", "LCD_LED_A", "LCD backlight current limit")
for index, (name, net) in enumerate((("NEXT", "BTN_NEXT"), ("UP", "BTN_UP"), ("DOWN", "BTN_DOWN"), ("SET", "BTN_SET"), ("ACK", "BTN_ACK")), start=1):
    add(Part(f"SW{index}", "Switch:SW_Push", (99 + index * 8, 183), name,
             "Button_Switch_THT:SW_PUSH_6mm", {"1": net, "2": "GND_CTRL"}, function=f"Local {name} key"))
add(Part("J5", "Connector_Generic:Conn_02x03_Odd_Even", (71, 153), "AVR_ISP",
         "Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical",
         {"1": "MISO_CTRL", "2": "+5V_CTRL", "3": "SCK_CTRL", "4": "MOSI_CTRL", "5": "RESET_N", "6": "GND_CTRL"},
         function="In-system programming and service connector"))
add(Part("J6", "Connector_Generic:Conn_02x05_Odd_Even", (78, 139), "MCU_EXPANSION",
         "Connector_PinHeader_2.54mm:PinHeader_2x05_P2.54mm_Vertical",
         {"1": "SPARE_PA2", "2": "SPARE_PA3", "3": "SPARE_PC2", "4": "SPARE_PC3",
          "5": "SPARE_PC4", "6": "SPARE_PC5", "7": "+5V_CTRL", "8": "GND_CTRL",
          "9": "AREF", "10": "RESET_N"},
         function="Service and future expansion header for unused MCU I/O"))

# Fail-safe 24 V relay: PB3 must be continuously asserted to grant RUN permission.
add(Part("Q1", "Transistor_FET:2N7000", (247, 188), "2N7000",
         # 2N7000 in TO-92: pin 1 = Source, pin 2 = Gate, pin 3 = Drain.
         # An earlier revision had 1/2 swapped, which tied the gate to GND and
         # made the low-side switch permanently off (RUN_PERMIT could never
         # assert).  Keep this mapping aligned with the symbol pin names.
         # TO-92_Inline puts the leads on a 1.27 mm pitch, which leaves 0.22 mm
         # between the RELAY_LOW and RELAY_GATE pads - the package, not the
         # design, would be setting the clearance on a 24 V net.  The _Wide
         # variant forms the same leads to 2.54 mm.
         "Package_TO_SOT_THT:TO-92_Inline_Wide",
         {"1": "GND_CTRL", "2": "RELAY_GATE", "3": "RELAY_LOW"},
         manufacturer="onsemi", mpn="2N7000",
         function="Low-side driver for the 24 V run-permit relay"))
resistor("R30", "100R", (235, 184), "RUN_PERMIT", "RELAY_GATE", "MOSFET gate stopper")
resistor("R31", "100k", (241, 194), "RELAY_GATE", "GND_CTRL", "Relay driver default-off pull-down", rotation=0)
add(Part("K1", "Relay:G5LE-1", (265, 180), "G5LE-1 DC24",
         "Relay_THT:Relay_SPDT_Omron-G5LE-1", {"1": "RELAY_LOW", "2": "+24V_PROT", "3": "RELAY_NO", "4": "RELAY_COM", "5": "RELAY_NC"},
         manufacturer="Omron Electronics", mpn="G5LE-1 DC24", function="Energized-to-run SPDT dry-contact output"))
add(Part("D3", "Device:D", (258, 193), "1N4007", "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal",
         {"1": "+24V_PROT", "2": "RELAY_LOW"}, function="Relay coil flyback clamp"))
resistor("R32", "4.7k 0.25W", (269, 194), "+24V_PROT", "RELAY_LED_A", "24 V relay status LED resistor")
add(Part("D4", "Device:LED", (277, 194), "RUN PERMIT", "LED_THT:LED_D3.0mm",
         {"2": "RELAY_LED_A", "1": "RELAY_LOW"}, function="Run-permit relay status indicator"))
add(Part("J3", "Connector_Generic:Conn_01x03", (286, 180), "RELAY_COM_NO_NC",
         "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-3_1x03_P5.00mm_Horizontal",
         {"1": "RELAY_COM", "2": "RELAY_NO", "3": "RELAY_NC"}, function="Low-voltage dry-contact output; rating pending load confirmation"))

# Isolated two-wire RS-485 port.  Receiver and driver pins share A/B for half duplex.
add(Part("U15", "Interface_UART:ADM2587E", (254, 145), "ADM2587EBRWZ",
         "Package_SO:SOIC-20W_7.5x12.8mm_P1.27mm",
         {"1": "GND_CTRL", "2": "+5V_CTRL", "3": "GND_CTRL", "4": "UART_RX",
          "5": "RS485_RE_N", "6": "RS485_DE", "7": "UART_TX", "8": "+5V_CTRL",
          "9": "GND_CTRL", "10": "GND_CTRL", "11": "GND_RS485", "12": "+5V_RS485",
          "13": "RS485_A", "14": "GND_RS485", "15": "RS485_B", "16": "GND_RS485",
          "17": "RS485_B", "18": "RS485_A", "19": "+5V_RS485", "20": "GND_RS485"},
         manufacturer="Analog Devices", mpn="ADM2587EBRWZ",
         datasheet="https://www.analog.com/media/en/technical-documentation/data-sheets/adm2582e-2587e.pdf",
         function="Signal-and-power-isolated half-duplex RS-485 interface"))
resistor("R33", "0R", (236, 142), "RS485_DE", "RS485_RE_N", "Tie receiver enable to driver enable logic")
add(Part("JP1", "Connector_Generic:Conn_01x02", (277, 135), "TERM_ENABLE",
         "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", {"1": "RS485_A", "2": "RS485_TERM_A"}, function="RS-485 termination enable jumper"))
resistor("R34", "120R 1%", (284, 135), "RS485_TERM_A", "RS485_B", "RS-485 end-of-line termination")
add(Part("JP2", "Connector_Generic:Conn_01x02", (277, 145), "BIAS_A_ENABLE",
         "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", {"1": "+5V_RS485", "2": "RS485_BIAS_A"}, function="RS-485 failsafe bias enable"))
resistor("R35", "680R 1%", (284, 145), "RS485_BIAS_A", "RS485_A", "RS-485 pull-up bias")
add(Part("JP3", "Connector_Generic:Conn_01x02", (277, 155), "BIAS_B_ENABLE",
         "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", {"1": "RS485_B", "2": "RS485_BIAS_B"}, function="RS-485 failsafe bias enable"))
resistor("R44", "680R 1%", (284, 155), "RS485_BIAS_B", "GND_RS485", "RS-485 pull-down bias")
add(Part("D5", "Device:D_TVS", (277, 165), "SMAJ6.0CA", "Diode_SMD:D_SMA",
         {"1": "RS485_A", "2": "GND_RS485"}, function="RS-485 A transient clamp"))
add(Part("D6", "Device:D_TVS", (284, 165), "SMAJ6.0CA", "Diode_SMD:D_SMA",
         {"1": "RS485_B", "2": "GND_RS485"}, function="RS-485 B transient clamp"))
add(Part("J4", "Connector_Generic:Conn_01x04", (291, 145), "RS485_A_B_GND_SHIELD",
         "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-4_1x04_P5.00mm_Horizontal",
         {"1": "RS485_A", "2": "RS485_B", "3": "GND_RS485", "4": "CHASSIS_SHIELD"}, function="Isolated RS-485 field connector"))
capacitor("C56", "100n X7R", (238, 128), "+5V_CTRL", "GND_CTRL", "ADM2587E logic supply decoupling")
capacitor("C57", "10u X7R", (244, 128), "+5V_CTRL", "GND_CTRL", "ADM2587E logic bulk bypass")
capacitor("C58", "100n X7R", (264, 128), "+5V_RS485", "GND_RS485", "ADM2587E isolated-side bypass")
capacitor("C59", "10u X7R", (270, 128), "+5V_RS485", "GND_RS485", "ADM2587E isoPower reservoir")

# Service test points and explicit power sources for clean ERC intent.
for index, (net, at) in enumerate((("GND_CTRL", (177, 194)), ("+5V_CTRL", (182, 194)),
                                   ("GND_SENS", (151, 130)), ("+3V3_SENS", (156, 130)),
                                   ("SCK_SENS", (161, 130)), ("MISO_SENS", (166, 130)),
                                   ("RESET_N", (171, 130)), ("RS485_A", (278, 122)),
                                   ("RS485_B", (284, 122))), start=1):
    add(Part(f"TP{index}", "Connector_Generic:Conn_01x01", at, net,
             "TestPoint:TestPoint_THTPad_D2.0mm_Drill1.0mm", {"1": net}, function=f"Service test point: {net}"))

for index, (net, at) in enumerate((("+24V_RAW", (192, 194)), ("GND_CTRL", (197, 194)),
                                   ("+24V_PROT", (202, 194)),
                                   ("GND_RS485", (212, 194))), start=1):
    add(Part(f"#FLG{index}", "power:PWR_FLAG", at, "PWR_FLAG", "", {"1": net},
             function=f"ERC power-source declaration for {net}"))


def ensure_parts() -> None:
    existing = current_symbols()
    # Replace early imported alias-only symbols with their pin-bearing base symbols.
    replacements = {
        "U1": "MCU_Microchip_ATmega:ATmega16L-8P",
        "U10": "Isolator:ISO7760DW",
        "U11": "Isolator:ISO7761DW",
        "U12": "Converter_DCDC:IA0305S",
        "U13": "Regulator_Linear:LP2985-1.8",
    }
    for ref in ("#FLG3", "#FLG4", "#FLG5", "#FLG6"):
        if ref in existing:
            run("sch", "edit", "symbol", "delete", str(SCH), ref)
            existing.pop(ref)
    for ref, required_lib in replacements.items():
        if ref in existing and existing[ref]["lib_id"] != required_lib:
            run("sch", "edit", "symbol", "delete", str(SCH), ref)
            existing.pop(ref)

    for part in parts:
        is_new = part.ref not in existing
        if is_new:
            prefix = part.lib_id.split(":", 1)[0]
            lib_file = SYMBOL_ROOT / LIB_FILES[prefix]
            run("sch", "edit", "symbol", "add", str(SCH), part.lib_id, part.ref,
                f"{part.at[0]},{part.at[1]}", "--lib-file", str(lib_file), "--format", "text")
            existing[part.ref] = {"ref": part.ref, "lib_id": part.lib_id}
        if is_new or "--refresh-properties" in sys.argv:
            run("sch", "edit", "symbol", "move", str(SCH), part.ref,
                f"{part.at[0]},{part.at[1]}", "--rotation", str(part.rotation))
            description = part.function
            if part.manufacturer or part.mpn:
                description += f" | Manufacturer: {part.manufacturer or 'TBD'} | MPN: {part.mpn or part.value}"
            for key, value in (("Value", part.value), ("Footprint", part.footprint),
                               ("Datasheet", part.datasheet), ("Description", description)):
                if value:
                    run("sch", "edit", "symbol", "set-property", str(SCH), part.ref, key, value)


def ensure_labels() -> None:
    labels = run("sch", "query", "list", str(SCH), "labels", "--format", "json", json_output=True)
    parts_by_ref = {part.ref: part for part in parts}

    # A resumed generation can contain labels from an earlier pin map.  Labels
    # are electrical connections in KiCad, so delete stale labels at the pins
    # whose mapping changed before adding the current ones.  This keeps the
    # generator idempotent and prevents hidden double-net connections.
    corrected_pins = {
        "U10": set(parts_by_ref["U10"].nets),
        "U11": set(parts_by_ref["U11"].nets),
        "U12": set(parts_by_ref["U12"].nets),
        # Q1 pins 1/2 were swapped in an earlier revision; re-seed both.
        "Q1": set(parts_by_ref["Q1"].nets),
        # U13 changed from an AP2112K to an LP2985; the two symbols place their
        # pins differently, so labels left at the old positions would dangle.
        "U13": set(parts_by_ref["U13"].nets),
        **{f"U{channel + 1}": {"11"} for channel in range(1, 9)},
        **{f"#FLG{index}": {"1"} for index in range(1, 5)},
    }
    expected_at_point: dict[tuple[float, float], set[str]] = {}
    for ref, pin_numbers in corrected_pins.items():
        data = run("sch", "query", "symbol", str(SCH), ref, "--format", "json", json_output=True)
        pin_lookup = {pin["number"]: pin for pin in data.get("pins", [])}
        for pin_number in pin_numbers:
            point = pin_lookup[pin_number]["absolute"]
            xy = (round(point["x"], 3), round(point["y"], 3))
            expected_at_point.setdefault(xy, set()).add(parts_by_ref[ref].nets[pin_number])

    obsolete_points = {(207.0, 194.0), (217.0, 194.0)}
    for item in labels["items"]:
        xy = (round(item["at"]["x"], 3), round(item["at"]["y"], 3))
        if ((xy in expected_at_point and item["text"] not in expected_at_point[xy])
                or xy in obsolete_points):
            run("sch", "edit", "label", "delete", str(SCH), item["uuid"])

    labels = run("sch", "query", "list", str(SCH), "labels", "--format", "json", json_output=True)
    existing = {(item["text"], round(item["at"]["x"], 3), round(item["at"]["y"], 3))
                for item in labels["items"]}
    for part in parts:
        data = run("sch", "query", "symbol", str(SCH), part.ref, "--format", "json", json_output=True)
        pins = {pin["number"]: pin for pin in data.get("pins", [])}
        if part.nets and not pins:
            raise RuntimeError(f"{part.ref} ({part.lib_id}) has no imported pins")
        for pin_number, net in part.nets.items():
            if pin_number not in pins:
                raise RuntimeError(f"Missing pin {part.ref}.{pin_number}")
            point = pins[pin_number]["absolute"]
            key = (net, round(point["x"], 3), round(point["y"], 3))
            if key not in existing:
                run("sch", "edit", "label", "add", str(SCH), "local", net,
                    f"{point['x']},{point['y']}", "--format", "text")
                existing.add(key)


# Pins that carry no net on purpose.  Each one gets a schematic no-connect
# marker so ERC stays at zero errors and the intent is recorded in the drawing
# instead of living only in a review document.
#
#   U1.12/13  XTAL2/XTAL1  - the ATmega32A runs from its internal RC oscillator.
#   J2.7-10   LCD D0..D3   - the HD44780 module is driven in 4-bit mode.
#   U2..U9.6  DNC          - MAX31856 "do not connect" pin.
#   U2..U9.7  DRDY         - see below.
#   U2..U9.13 FAULT        - see below.
#   U11.11    OUTE         - spare ISO7761 channel; its input (pin 6) is tied low.
#   U12.4     -Vout        - the isolated module's unused negative rail.
#   U13.4     NC           - AP2112K has no pin 4 function.
#
# DRDY/FAULT are deliberately not brought to the MCU.  Both isolators are fully
# allocated (ISO7760: 6/6 forward, ISO7761: 5 forward + 1 reverse for MISO), so
# crossing sixteen more signals would need a second isolator plus fault-OR
# logic.  The firmware reads the MAX31856 fault register (0x0F) on every sample
# instead.  This is a documented trade-off, not an oversight.
NO_CONNECT_PINS: dict[str, tuple[str, ...]] = {
    "U1": ("12", "13"),
    "J2": ("7", "8", "9", "10"),
    "U11": ("11",),
    "U12": ("4",),
    "U13": ("4",),
    **{f"U{channel + 1}": ("6", "7", "13") for channel in range(1, 9)},
}


def ensure_no_connects() -> None:
    """Add no-connect markers, removing any stale label on the same pin."""
    import uuid as _uuid

    targets: list[tuple[float, float]] = []
    for ref, pin_numbers in NO_CONNECT_PINS.items():
        data = run("sch", "query", "symbol", str(SCH), ref, "--format", "json",
                   json_output=True)
        pins = {pin["number"]: pin for pin in data.get("pins", [])}
        for pin_number in pin_numbers:
            if pin_number not in pins:
                raise RuntimeError(f"Missing pin {ref}.{pin_number}")
            point = pins[pin_number]["absolute"]
            targets.append((round(point["x"], 3), round(point["y"], 3)))

    # kicad-tool rewrites the file on every edit, so label UUIDs from an
    # earlier query go stale after the first delete.  Re-query each round.
    wanted = set(targets)
    while True:
        labels = run("sch", "query", "list", str(SCH), "labels", "--format",
                     "json", json_output=True)
        doomed = next(
            (item for item in labels["items"]
             if (round(item["at"]["x"], 3), round(item["at"]["y"], 3)) in wanted),
            None,
        )
        if doomed is None:
            break
        run("sch", "edit", "label", "delete", str(SCH), doomed["uuid"])

    # Drop markers left behind by a symbol swap: a no-connect at a position
    # that is no longer a pin dangles, and ERC is right to complain.
    text = SCH.read_text(encoding="utf-8")
    wanted_xy = set(targets)
    pattern = re.compile(
        r"\t\(no_connect\n\s*\(at\s+([-\d.]+)\s+([-\d.]+)\s*\)"
        r"(?:[^\n]*\n)*?\t\)\n")

    dropped = 0

    def _prune(match: "re.Match[str]") -> str:
        nonlocal dropped
        xy = (round(float(match.group(1)), 3), round(float(match.group(2)), 3))
        if xy in wanted_xy:
            return match.group(0)
        dropped += 1
        return ""

    pruned = pattern.sub(_prune, text)
    if dropped:
        SCH.write_text(pruned, encoding="utf-8")
        text = pruned
        print(f"Removed {dropped} stale no-connect markers")

    existing = set()
    for match in re.finditer(r"\(no_connect\s*\(at\s+([-\d.]+)\s+([-\d.]+)\s*\)", text):
        existing.add((round(float(match.group(1)), 3), round(float(match.group(2)), 3)))

    missing = [xy for xy in targets if xy not in existing]
    if not missing:
        print(f"No-connect markers already present: {len(targets)}")
        return

    block = "".join(
        '\t(no_connect\n\t\t(at {:g} {:g})\n\t\t(uuid "{}")\n\t)\n'.format(
            x, y, _uuid.uuid4())
        for x, y in missing
    )
    cut = text.rstrip().rfind("\n)")
    if cut < 0:
        raise RuntimeError("Could not locate the schematic closing parenthesis")
    SCH.write_text(text[:cut + 1] + block + text[cut + 1:], encoding="utf-8")
    print(f"Added {len(missing)} no-connect markers")


def prune_dangling_labels() -> None:
    """Delete labels that are not sitting on a pin.

    Connectivity in this schematic is carried entirely by labels placed on pin
    endpoints, so a label anywhere else is dead copper in the drawing and ERC
    reports it as dangling.  They appear when a symbol is swapped for one whose
    pins sit at different coordinates.
    """
    pin_points = set()
    for part in parts:
        data = run("sch", "query", "symbol", str(SCH), part.ref, "--format",
                   "json", json_output=True)
        for pin in data.get("pins", []):
            point = pin["absolute"]
            pin_points.add((round(point["x"], 3), round(point["y"], 3)))

    removed = 0
    while True:
        labels = run("sch", "query", "list", str(SCH), "labels", "--format",
                     "json", json_output=True)
        doomed = next(
            (item for item in labels["items"]
             if (round(item["at"]["x"], 3), round(item["at"]["y"], 3))
             not in pin_points),
            None,
        )
        if doomed is None:
            break
        run("sch", "edit", "label", "delete", str(SCH), doomed["uuid"])
        removed += 1
    if removed:
        print(f"Removed {removed} dangling labels")


if __name__ == "__main__":
    if not TOOL.exists():
        raise SystemExit(f"kicad-tool not found: {TOOL}")
    if "--labels-only" not in sys.argv:
        ensure_parts()
    ensure_labels()
    ensure_no_connects()
    prune_dangling_labels()
    print(f"Populated {SCH} with {len(parts)} symbols")
