"""Outputs: trip and alarm relays (G6K-2F-Y DC5) and isolated RS-485."""
from model import Part, Sheet, R, C, TP, NC

C100N = ("CC0805KRX7R9BB104", "C49678")
TB3 = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-3_1x03_P5.00mm_Horizontal"


def pump(p, b, drive):
    """Trip drive through a charge pump: only a running square wave on PB3 (OC0A)
    holds the relay; a pin stuck high or low drops it within ~30 ms (schematic review)."""
    return [
        R(f"R{b+1}", "100R", drive, f"{p}_PUMP_IN", "0805W8F1000T5E", "C17408"),
        C(f"C{b+4}", "100n", f"{p}_PUMP_IN", f"{p}_PUMP", "CC0805KRX7R9BB104", "C49678",
          desc="AC coupling"),
        Part(f"D{b+3}", "Device:D_Dual_Series_AKC", "BAT54S", {"1": "GND", "2": f"{p}_GATE", "3": f"{p}_PUMP"},
             "Package_TO_SOT_SMD:SOT-23", "BAT54S,215", "C47546", "Nexperia", "pump rectifier"),
        C(f"C{b+5}", "100n", f"{p}_GATE", "GND", "CC0805KRX7R9BB104", "C49678",
          desc="gate hold; with R gate-GND 100k gives ~10 ms"),
    ]


def relay(n, label, drive, sense, led):
    """n=1 trip: both poles' NO contacts in series, so one welded contact cannot keep
    RUN (review, I-081); NC comes from pole 1 only. n=2 alarm: pole 1 only.
    Read-back of both: the coil low side through 10k (5 V logic)."""
    p, b = ("TRIP", 700) if n == 1 else ("ALM", 710)
    if n == 1:
        contacts = {"3": f"{p}_COM", "2": f"{p}_NC", "4": f"{p}_MID", "6": f"{p}_MID",
                    "5": f"{p}_NO", "7": NC}
        note = "pin 1 coil +; NO path = pin 3 -> 4 -> 6 -> 5 (two poles in series)"
    else:
        contacts = {"3": f"{p}_COM", "2": f"{p}_NC", "4": f"{p}_NO", "6": NC, "5": NC, "7": NC}
        note = "pin 1 coil +; pole 2 unused"
    return [
        Part(f"K{700+n}", "Relay:G6K-2", "G6K-2F-Y DC5", dict(contacts, **{"1": "+5V", "8": f"{p}_LOW"}),
             "Relay_SMD:Relay_DPDT_Omron_G6K-2F-Y", "G6K-2F-Y DC5", "C2982926", "Omron", note),
        Part(f"Q{700+n}", "Transistor_FET:2N7002", "2N7002",
             {"G": f"{p}_GATE", "S": "GND", "D": f"{p}_LOW"},
             "Package_TO_SOT_SMD:SOT-23", "2N7002", "C8545", "CJ"),
    ] + (pump(p, b, drive) if n == 1 else [
        R(f"R{b+1}", "100R", drive, f"{p}_GATE", "0805W8F1000T5E", "C17408")]) + [
        R(f"R{b+2}", "100k", f"{p}_GATE", "GND", "0805W8F1003T5E", "C149504",
          desc="relay off while the MCU is in reset"),
        Part(f"D{b+1}", "Device:D", "1N4148W", {"1": "+5V", "2": f"{p}_LOW"},
             "Diode_SMD:D_SOD-123", "1N4148W-7-F", "C83528", "Diodes Inc", "coil flyback"),
        Part(f"D{b+2}", "Device:LED", label, {"1": f"{p}_LOW", "2": f"{p}_LED_A"},
             "LED_THT:LED_D3.0mm", led[0], led[1], "Everlight", "lit while the coil is energised"),
        R(f"R{b+4}", "1.5k", "+5V", f"{p}_LED_A", "0805W8F1501T5E", "C4310"),
        R(f"R{b+3}", "10k", f"{p}_LOW", sense, "0805W8F1002T5E", "C17414",
          desc="read-back: low when the coil is energised"),
        C(f"C{b+3}", "100n", sense, "GND", *C100N),
        Part(f"J{700+n}", "Connector_Generic:Conn_01x03", f"{p} C-NO-NC",
             {"1": f"{p}_COM", "2": f"{p}_NO", "3": f"{p}_NC"}, TB3,
             "WJ128V-5.0-3P", "C8270", "KANGNEX", "30 VDC / 1 A max, signal loads only"),
    ]


def outputs():
    s = Sheet("OUTPUTS", "outputs.kicad_sch", "Trip and alarm contacts, RS-485", "A3")
    s.block("Trip relay (energised to run) - LOW-VOLTAGE SIGNAL LOAD ONLY",
            relay(1, "RUN", "RUN_PERMIT", "RUN_SENSE", ("3A4GUD", "C52034646")))
    s.block("Alarm relay (warning, never stops the engine by itself)",
            relay(2, "ALARM", "ALARM_DRIVE", "ALARM_SENSE", ("204-10SURD/S530-A3-L", "C99771")))
    s.block("Isolated RS-485 / Modbus RTU (never in the trip path)", [
        Part("U703", "Interface_UART:ADM2587E", "ADM2587EBRWZ", {
            "GND1": "GND", "VCC": "+5V", "RxD": "UART_RX", "~{RE}": "RS485_RE_N",
            "DE": "RS485_DE", "TxD": "UART_TX", "GND2": "GND_RS485", "Visoout": "+3V3_RS485",
            "Visoin": "+3V3_RS485", "Y": "RS485_A", "Z": "RS485_B", "A": "RS485_A", "B": "RS485_B"},
            "Package_SO:SOIC-20W_7.5x12.8mm_P1.27mm", "ADM2587EBRWZ-REEL7", "C12081", "ADI"),
        R("R733", "0R", "RS485_DE", "RS485_RE_N", "0805W8F0000T5E", "C17477", desc="DE and /RE tied"),
        R("R737", "10k", "RS485_DE", "GND", "0805W8F1002T5E", "C17414", desc="driver off during reset/ISP"),
        R("R738", "10k", "UART_RX", "+5V", "0805W8F1002T5E", "C17414", desc="RxD is high-Z while transmitting"),
        C("C735", "10n", "+5V", "GND", "CL21B103KBANNNC", "C1710", desc="pins 2/1 per datasheet"),
        C("C736", "10n", "+3V3_RS485", "GND_RS485", "CL21B103KBANNNC", "C1710", desc="pins 19/20 per datasheet"),
        C("C731", "100n", "+5V", "GND", *C100N), C("C732", "10u", "+5V", "GND", "CL21B106KOQNNNE", "C95841"),
        C("C733", "100n", "+3V3_RS485", "GND_RS485", *C100N),
        C("C734", "10u", "+3V3_RS485", "GND_RS485", "CL21B106KOQNNNE", "C95841"),
        Part("D731", "Diode:SM712_SOT23", "SM712",
             {"A1": "RS485_A", "A2": "RS485_B", "common": "GND_RS485"},
             "Package_TO_SOT_SMD:SOT-23", "SM712.TCT", "C12067", "Semtech", "-7/+12 V RS-485 TVS"),
        Part("JP731", "Connector_Generic:Conn_01x02", "TERM", {"1": "RS485_A", "2": "RS485_TERM_A"},
             "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", "PZ254V-11-02P", "C492401"),
        R("R734", "120R 1%", "RS485_TERM_A", "RS485_B", "0805W8F1200T5E", "C17437"),
        Part("JP732", "Connector_Generic:Conn_01x02", "BIAS_A", {"1": "+3V3_RS485", "2": "RS485_BIAS_A"},
             "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", "PZ254V-11-02P", "C492401"),
        R("R735", "680R 1%", "RS485_BIAS_A", "RS485_A", "0805W8F6800T5E", "C17798"),
        Part("JP733", "Connector_Generic:Conn_01x02", "BIAS_B", {"1": "RS485_B", "2": "RS485_BIAS_B"},
             "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", "PZ254V-11-02P", "C492401"),
        R("R736", "680R 1%", "RS485_BIAS_B", "GND_RS485", "0805W8F6800T5E", "C17798"),
        Part("J703", "Connector_Generic:Conn_01x03", "RS485 A B GND",
             {"1": "RS485_A", "2": "RS485_B", "3": "GND_RS485"}, TB3,
             "WJ128V-5.0-3P", "C8270", "KANGNEX",
             "cable shield bonds at the panel-entry bar, like the TC shields"),
    ])
    s.flags = ["GND_RS485"]
    return s
