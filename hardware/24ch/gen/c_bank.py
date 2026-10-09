"""One acquisition bank: 8 thermocouple inputs, AD7124-8, two ADT7310.

Decision 0032 (rev 2): per leg TC -> 2.2k -> BAV199 to the island rails ->
1k -> AIN; 10n differential and 1n per leg at the ADC; 20M from the TC-
terminal to the buffered mid-rail V_MID.
"""
from model import Part, Sheet, R, C, NC

ISO, GND = "+3V3_ISO", "GND_ISO"
HDR_FP = "Connector_Phoenix_MC:PhoenixContact_MC_1,5_8-G-3.81_1x08_P3.81mm_Horizontal"


def channel(b, k):
    n = 8 * (b - 1) + k
    tp, tn = f"TC{n}+", f"TC{n}-"
    pc, nc_ = f"TC{n}_PC", f"TC{n}_NC"
    pa, na = f"TC{n}_PA", f"TC{n}_NA"
    base = 100 * b + 10 * k
    return [
        R(f"R{base+1}", "2.2k", tp, pc, "0805W8F2201T5E", "C17520",
          desc="input limiter, pulse rating to verify", mfr="UNI-ROYAL"),
        R(f"R{base+2}", "2.2k", tn, nc_, "0805W8F2201T5E", "C17520",
          desc="input limiter, pulse rating to verify", mfr="UNI-ROYAL"),
        Part(f"D{base+1}", "Device:D_Dual_Series_AKC", "BAV199", {"1": GND, "2": ISO, "3": pc},
             "Package_TO_SOT_SMD:SOT-23", "BAV199,215", "C40919", "Nexperia", "low-leakage clamp"),
        Part(f"D{base+2}", "Device:D_Dual_Series_AKC", "BAV199", {"1": GND, "2": ISO, "3": nc_},
             "Package_TO_SOT_SMD:SOT-23", "BAV199,215", "C40919", "Nexperia", "low-leakage clamp"),
        R(f"R{base+3}", "1k", pc, pa, "0805W8F1001T5E", "C17513", mfr="UNI-ROYAL"),
        R(f"R{base+4}", "1k", nc_, na, "0805W8F1001T5E", "C17513", mfr="UNI-ROYAL"),
        C(f"C{base+1}", "10n C0G", pa, na, "GRM2195C1H103JA01D", "C97905", mfr="Murata"),
        C(f"C{base+2}", "1n C0G", pa, "V_BIAS", "CL21C102JBCNNNC", "C1791", mfr="Samsung", desc="C0G 50V; to V_BIAS so pad leakage sees ~0 V (review H1)"),
        C(f"C{base+3}", "1n C0G", na, "V_BIAS", "CL21C102JBCNNNC", "C1791", mfr="Samsung", desc="C0G 50V; to V_BIAS (review H1)"),
        R(f"R{base+5}", "20M 1%", tn, "V_BIAS", "FRG1206F2005TS", "C3000606",
          fp="Resistor_SMD:R_1206_3216Metric", desc="common-mode bias at the terminal side; 1206 for surge (review M4)",
          mfr="FOJAN"),
    ]


def bank(b):
    letter = "ABC"[b - 1]
    s = Sheet(f"BANK_{letter}", f"bank_{letter.lower()}.kicad_sch",
              f"Bank {letter}: channels {8*b-7}-{8*b} (isolated island)", paper="A3")
    hdr = []
    for h in range(2):
        nets = {}
        for i in range(4):
            n = 8 * (b - 1) + 4 * h + i + 1
            nets[str(2 * i + 1)] = f"TC{n}+"
            nets[str(2 * i + 2)] = f"TC{n}-"
        hdr.append(Part(f"J{100*b+h+1}", "Connector_Generic:Conn_01x08",
                        f"TC CH{8*b-7+4*h}-{8*b-4+4*h}", nets, HDR_FP,
                        "WJ15EDGRC-3.81-8P", "C14235", "KANGNEX",
                        "pluggable header; mating plug WJ15EDGK-3.81-08P (C14234)"))
    s.block("Thermocouple terminals (TC+ / TC- per channel; shield goes to the panel-entry bar)", hdr)
    for k in range(1, 9):
        s.block(f"Channel {8*(b-1)+k}: limiter, clamp, filter, bias", channel(b, k))
    ain = {}
    for k in range(1, 9):
        n = 8 * (b - 1) + k
        ain[f"AIN{2*k-2}"] = f"TC{n}_PA"
        ain[f"AIN{2*k-1}"] = f"TC{n}_NA"
    u = 100 * b
    adc = Part(f"U{u+1}", "thermo24:AD7124-8", "AD7124-8BCPZ", dict(ain, **{
        "REFIN1(+)": "VREF_EXT", "REFIN1(-)": GND, "REFOUT": f"REFOUT_{letter}",
        "REGCAPA": f"REGCAPA_{letter}", "REGCAPD": f"REGCAPD_{letter}", "PSW": NC,
        "SYNC": f"SYNC_{letter}", "CLK": NC, "~{CS}": f"CS_ADC{b}_ISO", "SCLK": "SCLK_ISO",
        "DIN": "DIN_ISO", "DOUT/~{RDY}": "DOUT_ISO", "AVDD": ISO, "IOVDD": ISO,
        "AVSS": GND, "DGND": GND, "EP": GND}),
        "Package_CSP:LFCSP-32-1EP_5x5mm_P0.5mm_EP3.6x3.6mm", "AD7124-8BCPZ", "C97314", "ADI",
        "internal clock, gain 32, EP to AVSS")
    s.block(f"AD7124-8 #{b} and its decoupling", [
        adc,
        C(f"C{u+91}", "100n", f"REFOUT_{letter}", GND, "CC0805KRX7R9BB104", "C49678", desc="REFOUT, never joined"),
        C(f"C{u+92}", "100n", f"REGCAPA_{letter}", GND, "CC0805KRX7R9BB104", "C49678"),
        C(f"C{u+93}", "100n", f"REGCAPD_{letter}", GND, "CC0805KRX7R9BB104", "C49678"),
        C(f"C{u+94}", "100n", ISO, GND, "CC0805KRX7R9BB104", "C49678", desc="AVDD"),
        C(f"C{u+95}", "1u", ISO, GND, "CL21B105KBFNNNE", "C28323", desc="AVDD bulk"),
        C(f"C{u+96}", "100n", ISO, GND, "CC0805KRX7R9BB104", "C49678", desc="IOVDD"),
        C(f"C{u+97}", "1u", ISO, GND, "CL21B105KBFNNNE", "C28323", desc="IOVDD bulk"),
        C(f"C{u+98}", "100n", "VREF_EXT", GND, "CC0805KRX7R9BB104", "C49678", desc="REFIN1"),
        R(f"R{u+91}", "10k", f"SYNC_{letter}", ISO, "0805W8F1002T5E", "C17414", desc="SYNC held high"),
        C(f"C{u+89}", "100n", "V_BIAS", GND, "CC0805KRX7R9BB104", "C49678", desc="V_BIAS local decoupling"),
    ])
    cj = []
    for i in range(2):
        j = 2 * (b - 1) + i + 1
        cj.append(Part(f"U{u+2+i}", "thermo24:ADT7310", "ADT7310TRZ", {
            "SCLK": "SCLK_ISO", "DIN": "DIN_ISO", "DOUT": "DOUT_ISO", "~{CS}": f"CS_CJ{j}_ISO",
            "~{INT}": NC, "~{CT}": NC, "VDD": ISO, "GND": GND},
            "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "ADT7310TRZ-REEL7", "C578060", "ADI",
            f"cold junction at the seam of header J{100*b+1+i}"))
        cj.append(C(f"C{u+99-9*i}", "100n", ISO, GND, "CC0805KRX7R9BB104", "C49678"))
    s.block("Cold-junction sensors (one per 4-channel header)", cj)
    return s
