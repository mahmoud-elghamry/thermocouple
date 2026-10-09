"""Controller: ATmega1284P, crystal, ISP, 20x4 LCD header, five buttons."""
from model import Part, Sheet, R, C, TP, NC, R1206

C100N = ("CC0805KRX7R9BB104", "C49678")

MCU_PINS = {
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


def mcu():
    s = Sheet("MCU", "mcu.kicad_sch", "Controller, display and keypad", "A3")
    s.block("ATmega1284P-AU (JTAG fuse must be disabled: PC2-PC5 are used as GPIO)", [
        Part("U501", "MCU_Microchip_ATmega:ATmega1284P-A", "ATmega1284P-AU", MCU_PINS,
             "Package_QFP:TQFP-44_10x10mm_P0.8mm", "ATMEGA1284P-AU", "C33575", "Microchip"),
        C("C503", "100n", "+5V", "GND", *C100N, desc="VCC pin 5"),
        C("C504", "100n", "+5V", "GND", *C100N, desc="VCC pin 17"),
        C("C505", "100n", "+5V", "GND", *C100N, desc="VCC pin 38"),
        C("C506", "100n", "+5V", "GND", *C100N, desc="AVCC"),
        C("C507", "100n", "AREF", "GND", *C100N),
        R("R501", "10k", "+5V", "RESET_N", "0805W8F1002T5E", "C17414"),
        C("C508", "10n", "RESET_N", "GND", "CL21B103KBANNNC", "C1710"),
        Part("Y501", "Device:Crystal", "8MHz", {"1": "XTAL1", "2": "XTAL2"},
             "Crystal:Crystal_SMD_HC49-SD", "X49SM8MSD2SC", "C12674", "Yangxing Tech"),
        C("C501", "22p C0G", "XTAL1", "GND", "CL21C220JBANNNC", "C1804"),
        C("C502", "22p C0G", "XTAL2", "GND", "CL21C220JBANNNC", "C1804"),
        Part("J501", "Connector_Generic:Conn_02x03_Odd_Even", "AVR ISP",
             {"1": "MISO", "2": "+5V", "3": "SCK", "4": "MOSI", "5": "RESET_N", "6": "GND"},
             "Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical", "PZ254V-12-6P",
             "C492420", "XKB Connection", "outside the LCD shadow"),
        TP("TP501", "RESET_N"),
    ])
    s.block("20x4 character LCD (HD44780, 4-bit, bought locally) and keypad", [
        Part("J502", "Connector_Generic:Conn_01x16", "LCD 20x4 HEADER", {
            "1": "GND", "2": "+5V", "3": "LCD_VO", "4": "LCD_RS", "5": "GND", "6": "LCD_E",
            "7": NC, "8": NC, "9": NC, "10": NC, "11": "LCD_D4", "12": "LCD_D5",
            "13": "LCD_D6", "14": "LCD_D7", "15": "LCD_LED_A", "16": "GND"},
            "Connector_PinHeader_2.54mm:PinHeader_1x16_P2.54mm_Vertical",
            "ZX-PZ2.54-1-16PZZ", "C7501270", "XKB Connection"),
        Part("RV501", "Device:R_Potentiometer", "10k CONTRAST",
             {"1": "GND", "2": "LCD_VO", "3": "+5V"},
             "Potentiometer_THT:Potentiometer_Bourns_3296W_Vertical", "3296W-1-103LF",
             "C34846", "Bourns", "outside the LCD shadow"),
        R("R502", "22R", "+5V", "LCD_LED_A", "1206W4F220JT5E", "C17958", fp=R1206,
          desc="backlight ~68 mA at Vf 3.5 V; adjust to the bought module"),
    ] + [Part(f"SW{501+i}", "Switch:SW_Push", n, {"1": f"BTN_{n}", "2": "GND"},
              "Button_Switch_THT:SW_PUSH_6mm", "", "", "",
              "tall actuator needed: LCD face ~24 mm above the board")
         for i, n in enumerate(["UP", "DOWN", "SET", "ESC", "ACK"])])
    return s
