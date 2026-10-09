"""24 V battery input and LM5164 buck to 5 V (REV A2 stage, values unchanged)."""
from model import Part, Sheet, R, C, TP

C1210 = "Capacitor_SMD:C_1210_3225Metric"


def power():
    s = Sheet("POWER", "power.kicad_sch", "Battery input and 5 V buck", "A3")
    s.block("Battery input: external panel fuse (0020), PTC, reverse and surge protection", [
        Part("J601", "Connector_Generic:Conn_01x03", "24V IN",
             {"1": "+24V_RAW", "2": "GND", "3": "CHASSIS"},
             "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-3_1x03_P5.00mm_Horizontal",
             "WJ128V-5.0-3P", "C8270", "KANGNEX"),
        Part("F601", "Device:Polyfuse", "0.75A 60V", {"1": "+24V_RAW", "2": "+24V_FUSED"},
             "Fuse:Fuse_2920_7451Metric", "MF-SM075/60-2", "C210842", "Bourns",
             "hold >0.52 A at max ambient required (CALCULATIONS 7.3); verify derating"),
        Part("D601", "Device:D_Schottky", "SS310", {"K": "+24V_PROT", "A": "+24V_FUSED"},
             "Diode_SMD:D_SMA", "SS310", "C15874", "MDD", "reverse protection"),
        Part("D602", "Device:D_Zener", "SMBJ60A", {"K": "+24V_PROT", "A": "GND"},
             "Diode_SMD:D_SMB", "SMBJ60A", "C49066953", "R+O", "load-dump clamp"),
        C("C601", "22u 100V", "+24V_PROT", "GND", "100YXF22MEFC8X11.5", "C88838",
          fp="Capacitor_THT:CP_Radial_D8.0mm_P3.50mm", mfr="Rubycon"),
        C("C602", "4.7u 100V", "+24V_PROT", "GND", "FS32X475K101EGG", "C381466", fp=C1210),
        C("C603", "4.7u 100V", "+24V_PROT", "GND", "FS32X475K101EGG", "C381466", fp=C1210),
        TP("TP603", "+24V_PROT"),
        C("C610", "1n 2kV", "CHASSIS", "GND", "1206B102K202NT", "C9196", fp="Capacitor_SMD:C_1206_3216Metric",
          desc="ESD return from LCD/keypad to chassis"),
        R("R607", "1M", "CHASSIS", "GND", "1206W4F1004T5E", "C17927", fp="Resistor_SMD:R_1206_3216Metric", desc="static bleed"),
    ])
    s.block("LM5164 buck, 5 V (CALCULATIONS 1.2-1.7)", [
        Part("U601", "Regulator_Switching:LM5164DDA", "LM5164DDAR", {
            "GND": "GND", "VIN": "+24V_PROT", "EN/UVLO": "VIN_UVLO", "RON": "RON_SET",
            "FB": "FB_5V", "PGOOD": "<NC>", "BST": "BST_5V", "SW": "SW_5V", "EP": "GND"},
            "Package_SO:HSOP-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.1mm",
            "LM5164DDAR", "C477928", "TI"),
        C("C604", "2.2n C0G", "BST_5V", "SW_5V", "CL21C222JBFNNNE", "C28260", desc="bootstrap; JLC basic part"),
        Part("L601", "Device:L", "33u 2.2A", {"1": "SW_5V", "2": "+5V"},
             "Inductor_SMD:L_10.4x10.4_H4.8", "SMDRH104R-330MT", "C9936", "Sunlord"),
        C("C605", "22u 25V", "+5V", "GND", "CL32B226KAJNNNE", "C309062", fp=C1210),
        C("C606", "22u 25V", "+5V", "GND", "CL32B226KAJNNNE", "C309062", fp=C1210),
        C("C607", "10u", "+5V", "GND", "CL21B106KOQNNNE", "C95841"),
        Part("D603", "Device:D_Zener", "SMBJ5.0A", {"K": "+5V", "A": "GND"}, "Diode_SMD:D_SMB",
             "SMBJ5.0A", "C83333", "Littelfuse", "5 V crowbar: a shorted high-side FET blows F601 (review M6)"),
        R("R601", "41.2k 1%", "RON_SET", "GND", "FRC0805F4122TS", "C2933440"),
        R("R602", "158k 1%", "+5V", "FB_5V", "RT0805BRD07158KL", "C865205"),
        R("R603", "49.9k 1%", "FB_5V", "GND", "0805W8F4992T5E", "C17719"),
        R("R604", "150k 1%", "SW_5V", "RIPPLE_INJ", "0805W8F1503T5E", "C17470"),
        C("C608", "3.3n", "RIPPLE_INJ", "+5V", "0805B332K500NT", "C1738"),
        C("C609", "220p C0G", "RIPPLE_INJ", "FB_5V", "CC0805JRNPO0BN221", "C113819"),
        R("R605", "33.2k 1%", "+24V_PROT", "VIN_UVLO", "FRC0805F3322TS", "C2933418"),
        R("R606", "10k 1%", "VIN_UVLO", "GND", "0805W8F1002T5E", "C17414"),
        TP("TP601", "GND"), TP("TP602", "+5V"),
    ])
    s.flags = ["GND", "+5V", "+24V_PROT", "CHASSIS"]
    return s
