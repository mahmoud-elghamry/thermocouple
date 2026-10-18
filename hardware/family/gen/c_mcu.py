"""Controller: ATmega1284P, crystal, ISP, 20x4 LCD header, five buttons."""
from model import Part, Sheet, R, C, TP, NC, R1206

C100N = ("CC0805KRX7R9BB104", "C49678")



def mcu(config):
    s = Sheet("MCU", "mcu.kicad_sch", "Controller, display and keypad", "A3")
    jtag = "PC2-PC5 are used as GPIO" if config.bank_count == 3 else "PC2 is used as GPIO"
    s.block(f"ATmega1284P-AU (JTAG fuse must be disabled: {jtag})", [
        Part("U501", "MCU_Microchip_ATmega:ATmega1284P-A", "ATmega1284P-AU", config.mcu_pins,
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
             "Potentiometer_THT:Potentiometer_Bourns_3296W_Vertical", "3296W-1-103",
             "C118954", "BOCHEN", "outside the LCD shadow; 3296W outline (0036)"),
        R("R502", "22R", "+5V", "LCD_LED_A", "1206W4F220JT5E", "C17958", fp=R1206,
          desc="backlight ~68 mA at Vf 3.5 V; adjust to the bought module"),
        Part("J503", "Connector_Generic:Conn_01x06", "PANEL BUTTONS",
             {"1": "BTN_UP", "2": "BTN_DOWN", "3": "BTN_SET", "4": "BTN_ESC", "5": "BTN_ACK", "6": "GND"},
             "Connector_JST:JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical", "B6B-XH-A(LF)(SN)", "C144397", "JST",
             "panel buttons on a cable, in parallel with SW501-SW505 (0034 D2)"),
    ] + [Part(f"SW{501+i}", "Switch:SW_Push", n, {"1": f"BTN_{n}", "2": "GND"},
              "Button_Switch_THT:SW_PUSH_6mm", "ZX-QC66-9.5CJ", "C7470135", "Megastar",
              "6x6 THT, 9.5 mm: bench use; the panel buttons go on J503 (0034 D2)")
         for i, n in enumerate(["UP", "DOWN", "SET", "ESC", "ACK"])])
    return s
