"""Isolation barrier, island supply, reference, mid-rail and engine reference."""
from model import Part, Sheet, R, C, TP, NC, R1206

ISO, GND_I = "+3V3_ISO", "GND_ISO"
C100N = ("CC0805KRX7R9BB104", "C49678")
C10K = ("0805W8F1002T5E", "C17414")


def c100(ref, a, b, desc=""):
    return C(ref, "100n", a, b, *C100N, desc=desc)


def isolator(ref, a_in, f_out, a_out, f_in, cap1, cap2):
    """a_in: control-side inputs A..E; a_out: island outputs A..E; reverse F."""
    nets = {"Vcc1": "+5V", "GND1": "GND", "Vcc2": ISO, "GND2": GND_I,
            "OUTF": f_out, "INF": f_in}
    for i, ch in enumerate("ABCDE"):
        nets["IN" + ch] = a_in[i]
        nets["OUT" + ch] = a_out[i]
    return [Part(ref, "Isolator:ISO7761DW", "ISO7761DWR", nets,
                 "Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm", "ISO7761DWR", "C2871529", "TI"),
            c100(cap1, "+5V", "GND", "side 1"), c100(cap2, ISO, GND_I, "side 2")]


def isolation():
    s = Sheet("ISOLATION", "isolation.kicad_sch", "Isolation, island supply and references", "A3")
    s.block("Island supply: 1 W isolated module, LDO, minimum-load preload", [
        Part("U401", "Converter_DCDC_Isolated:CRE1S0505SC", "B0505S-1WR2",
             {"-VIN": "GND", "+VIN": "+5V", "-VOUT": GND_I, "+VOUT": "+5V_ISO_RAW"},
             "Converter_DCDC:Converter_DCDC_Murata_CRE1xxxxxxSC_THT", "B0505S-1WR2", "C2992393",
             "YLPTEC", "SIP-4: 1 GND, 2 +Vin, 3 -Vo, 4 +Vo; 1500 VDC; 20 mA minimum load"),
        C("C401", "10u", "+5V", "GND", "CL21A106KAYNNNE", "C15850"),
        c100("C402", "+5V", "GND"),
        C("C403", "10u", "+5V_ISO_RAW", GND_I, "CL21A106KAYNNNE", "C15850"),
        Part("U402", "Regulator_Linear:LP2985-3.3", "LP2985IM5X-3.3",
             {"VIN": "+5V_ISO_RAW", "GND": GND_I, "ON/~{OFF}": "+5V_ISO_RAW", "BP": "LDO_BP",
              "VOUT": ISO}, "Package_TO_SOT_SMD:SOT-23-5", "LP2985IM5X-3.3/NOPB", "C129375", "TI"),
        C("C404", "10n", "LDO_BP", GND_I, "CL21B103KBANNNC", "C1710", desc="bypass, low noise"),
        C("C405", "1u", "+5V_ISO_RAW", GND_I, "CL21B105KBFNNNE", "C28323"),
        C("C406", "4.7u", ISO, GND_I, "CGA0805X7R475K350MT", "C6119943"),
        R("R401", "150R 1%", ISO, GND_I, "1206W4F1500T5E", "C17917", fp=R1206,
          desc="preload: module minimum load and AVDD clamp-current sink (0032 rev 2)"),
        TP("TP401", ISO), TP("TP402", GND_I), TP("TP407", "+5V_ISO_RAW"),
    ])
    cs_c = ["CS_ADC1", "CS_ADC2", "CS_ADC3"] + [f"CS_CJ{i}" for i in range(1, 7)]
    s.block("Digital isolators: SPI to the three AD7124 and six ADT7310", (
        isolator("U403", ["SCK", "MOSI", "CS_ADC1", "CS_ADC2", "CS_ADC3"], "MISO_ISO",
                 ["SCLK_ISO_RAW", "DIN_ISO_RAW", "CS_ADC1_ISO", "CS_ADC2_ISO", "CS_ADC3_ISO"],
                 "DOUT_ISO_RAW", "C407", "C408")
        + isolator("U404", ["CS_CJ1", "CS_CJ2", "CS_CJ3", "CS_CJ4", "CS_CJ5"], "REFOK",
                   [f"CS_CJ{i}_ISO" for i in range(1, 6)], "REFOK_ISO", "C409", "C410")
        + isolator("U405", ["CS_CJ6", "REFTEST", "GND", "GND", "GND"], NC,
                   ["CS_CJ6_ISO", "REFTEST_ISO", NC, NC, NC], GND_I, "C411", "C412")))
    s.block("Series damping, MISO contention resistor, pull-ups", [
        R("R402", "33R", "SCLK_ISO_RAW", "SCLK_ISO", "0805W8F330JT5E", "C17634"),
        R("R403", "33R", "DIN_ISO_RAW", "DIN_ISO", "0805W8F330JT5E", "C17634"),
        R("R404", "33R", "DOUT_ISO", "DOUT_ISO_RAW", "0805W8F330JT5E", "C17634"),
        R("R405", "2k2", "MISO_ISO", "MISO", "0805W8F2201T5E", "C17520", desc="ISP contention"),
        R("R415", "100k", "DOUT_ISO", ISO, "0805W8F1003T5E", "C149504", desc="defined DOUT with all devices deselected"),
    ] + [R(f"R{430+i}", "10k", c, "+5V", *C10K, desc="control CS pull-up during MCU reset")
         for i, c in enumerate(cs_c)])
    s.block("External 3.0 V reference (cross-check of the AD7124 internal reference)", [
        Part("U406", "Reference_Voltage:REF3030", "REF3030AIDBZR",
             {"IN": ISO, "GND": GND_I, "OUT": "VREF_EXT"}, "Package_TO_SOT_SMD:SOT-23",
             "REF3030AIDBZR", "C38423", "TI"),
        c100("C413", ISO, GND_I), c100("C414", "VREF_EXT", GND_I),
        TP("TP404", "VREF_EXT"),
    ])
    s.block("Mid-rail V_MID for the 20M thermocouple bias", [
        R("R416", "100k 1%", ISO, "V_MID_DIV", "0805W8F1003T5E", "C149504"),
        R("R417", "100k 1%", "V_MID_DIV", GND_I, "0805W8F1003T5E", "C149504"),
        c100("C415", "V_MID_DIV", GND_I),
        Part("U407", "Amplifier_Operational:MCP6001-OT", "MCP6001T-I/OT",
             {"1": "V_MID_BUF", "+": "V_MID_DIV", "-": "V_MID_BUF", "V+": ISO, "V-": GND_I},
             "Package_TO_SOT_SMD:SOT-23-5", "MCP6001T-I/OT", "C116490", "Microchip"),
        c100("C416", ISO, GND_I),
        R("R418", "100R", "V_MID_BUF", "V_MID", "0805W8F1000T5E", "C17408", desc="isolates the buffer from capacitance"),
        TP("TP403", "V_MID"),
        R("R427", "10k", "V_MID", "V_BIAS", *C10K,
          desc="bias bus for the 24 R_b and C_cm, separate from the engine-reference feed (review M4)"),
        Part("D403", "Device:D_Dual_Series_AKC", "BAV199", {"1": GND_I, "2": ISO, "3": "V_BIAS"},
             "Package_TO_SOT_SMD:SOT-23", "BAV199,215", "C40919", "Nexperia"),
        c100("C418", "V_BIAS", GND_I), TP("TP405", "V_BIAS"), TP("TP406", "REFOK_ISO"),
    ])
    s.block("AVDD shunt clamp at ~3.5 V (clamp-current sink beyond the preload, review M1)", [
        Part("U409", "Reference_Voltage:TL431DBZ", "TL431",
             {"K": "CLAMP_K", "REF": "CLAMP_REF", "A": GND_I}, "Package_TO_SOT_SMD:SOT-23",
             "TL431BIDBZR", "C41283", "TI", "TI part only: pin 1 = K; 3.5 V = 2.495 x (1 + 4.02k/10k)"),
        R("R428", "4.02k 1%", ISO, "CLAMP_REF", "0805W8F4021T5E", "C17663"),
        R("R429", "10k 1%", "CLAMP_REF", GND_I, "0805W8F1002T5E", "C17414"),
        R("R440", "470R", ISO, "CLAMP_K", "0805W8F4700T5E", "C17710", desc="PNP turns on at ~1.3 mA TL431 current (>=1 mA spec)"),
        Part("Q402", "Transistor_BJT:MMBT3906", "MMBT3906",
             {"B": "CLAMP_K", "E": ISO, "C": "CLAMP_C"}, "Package_TO_SOT_SMD:SOT-23",
             "MMBT3906LT1G", "C53444", "onsemi", "TL431 cathode drives the base directly (schematic review)"),
        R("R441", "22R 1W", "CLAMP_C", GND_I, "25121WF220JT4E", "C118189", fp="Resistor_SMD:R_2512_6332Metric",
          desc="limits the clamp to ~150 mA; 0.5 W at full clamp"),
    ])
    s.block("Engine reference wire: feed + sense, continuity comparator, self-test", [
        Part("J401", "Connector_Generic:Conn_01x02", "ENGINE REF FEED/SENSE",
             {"1": "REF_FEED", "2": "REF_SENSE_IN"},
             "Connector_Phoenix_MC:PhoenixContact_MC_1,5_2-G-3.81_1x02_P3.81mm_Horizontal",
             "WJ15EDGRC-3.81-02P-14-00A", "C8387", "KANGNEX", "two wires joined only at the engine block; plug WJ15EDGK-3.81-02P (C8466)"),
        R("R419", "4.99k", "V_MID", "REF_FEED_A", "FRC1206F4991TS", "C3013259", fp=R1206, desc="1206 for pulse"),
        R("R420", "4.99k", "REF_FEED_A", "REF_FEED", "FRC1206F4991TS", "C3013259", fp=R1206, desc="1206 for pulse"),
        Part("D401", "Device:D_Dual_Series_AKC", "BAV199", {"1": GND_I, "2": ISO, "3": "REF_FEED_A"},
             "Package_TO_SOT_SMD:SOT-23", "BAV199,215", "C40919", "Nexperia"),
        R("R421", "10k", "REF_SENSE_IN", "REF_SENSE", *C10K),
        R("R422", "1M", "REF_SENSE", GND_I, "0805W8F1004T5E", "C17514", desc="1M keeps the injected current small (review M5)"),
        Part("D402", "Device:D_Dual_Series_AKC", "BAV199", {"1": GND_I, "2": ISO, "3": "REF_SENSE"},
             "Package_TO_SOT_SMD:SOT-23", "BAV199,215", "C40919", "Nexperia"),
        R("R423", "15k 1%", ISO, "REF_THR", "0805W8F1502T5E", "C17475"),
        R("R424", "10k 1%", "REF_THR", GND_I, "0805W8F1002T5E", "C17414"),
        Part("U408", "Comparator:TLV7031DBV", "TLV7031DBVR",
             {"1": "REFOK_ISO", "+": "REF_THR", "-": "REF_SENSE", "V+": ISO, "V-": GND_I},
             "Package_TO_SOT_SMD:SOT-23-5", "TLV7031DBVR", "C2869832", "TI",
             "LOW = wire connected (~1.63 V vs 1.32 V); high = broken, and the isolator's default-high on lost island power also reads broken"),
        R("R442", "1M", "REFOK_ISO", "REF_THR", "0805W8F1004T5E", "C17514", desc="~20 mV hysteresis"),
        C("C419", "100n", "REF_SENSE", GND_I, *C100N, desc="sense filter, 0.1 s"),
        c100("C417", ISO, GND_I),
        Part("Q401", "Transistor_FET:2N7002", "2N7002",
             {"G": "REFTEST_ISO", "S": GND_I, "D": "REF_TEST_D"},
             "Package_TO_SOT_SMD:SOT-23", "2N7002", "C8545", "CJ", "self-test: pulls sense low"),
        R("R425", "1k", "REF_TEST_D", "REF_SENSE", "0805W8F1001T5E", "C17513"),
    ])
    s.flags = []
    return s
