"""40-ch RTD bank: one AD7124-8, three 3-wire PT100 inputs + an on-board check resistor (0039 D5, P5).

Per ADI CN-0383 (multiple 3-wire RTDs, low-side reference). Lead A = the single wire at one end of the
element; leads B and C = the two wires at the other end. IOUT0 -> A -> element -> C (return) -> R_ref ->
R_head -> AVSS; IOUT1 -> B, so I1 x r_B cancels I0 x r_A (currents swapped each reading). Both currents
(250 uA each) flow in R_ref: V_ref = 500 uA x 2.49k = 1.245 V (reference detect 0.7-1 V, Astra); gain 16 ->
+/-77.8 mV = 311 ohm full scale. The 330R under R_ref gives the reference buffers 0.165 V headroom.
Excitation and sense reach each lead through separate protection branches, so the excitation current
never flows in a sense resistor. Compliance and fault coverage: CALCULATIONS 10.11.
Pins per RTD r (0..3): AIN4r = IOUT0 out (lead A), AIN4r+1 = IOUT1 out (lead B),
AIN4r+2 / AIN4r+3 = sense A / sense B. All 16 AIN used (IOUT reaches any AIN pin, Astra).
"""
from model import Part, Sheet, R, C, NC, R1206

R2512 = "Resistor_SMD:R_2512_6332Metric"
R1K_2512 = ("25121WF1001T4E", "C54315")     # 1 W: a lead miswired to 24 V puts ~0.4 W in it (Astra)
R2K2_1206 = ("1206W4F2201T5E", "C17948")

ISO, GND = "+3V3_ISO", "GND_ISO"
C100N = ("CC0805KRX7R9BB104", "C49678")
HDR6 = "Connector_Phoenix_MC:PhoenixContact_MC_1,5_6-G-3.81_1x06_P3.81mm_Horizontal"
HDR3 = "Connector_Phoenix_MC:PhoenixContact_MC_1,5_3-G-3.81_1x03_P3.81mm_Horizontal"
CHECK = 4                 # slot 4 = on-board check resistor (0039 P5 (b))
BASE = 1000


def bav(ref, node):
    return Part(ref, "Device:D_Dual_Series_AKC", "BAV199", {"1": GND, "2": ISO, "3": node},
                "Package_TO_SOT_SMD:SOT-23", "BAV199,215", "C40919", "Nexperia", "low-leakage clamp")


def rtd(r):
    """r = 1..4. Leads A, B (same end of the element in 3-wire: A at one end, B and C at the other)."""
    b = BASE + 10 * r
    a, bb, c = f"RTD{r}_A", f"RTD{r}_B", f"RTD{r}_C"
    if r == CHECK:      # on-board check resistor: B and C are one node, no cable
        a, bb, c = "CHK_A", "CHK_BC", "CHK_BC"
    return [
        # excitation branches: 1k (1206, pulse) -> clamp -> 100R -> IOUT pin
        R(f"R{b+1}", "1k 1W", a, f"RTD{r}_XA", *R1K_2512, fp=R2512,
          desc="excitation lead A limiter"),
        bav(f"D{b+1}", f"RTD{r}_XA"),
        R(f"R{b+2}", "100R", f"RTD{r}_XA", f"RTD{r}_IA", "0805W8F1000T5E", "C17408"),
        R(f"R{b+3}", "1k 1W", bb, f"RTD{r}_XB", *R1K_2512, fp=R2512,
          desc="excitation lead B limiter"),
        bav(f"D{b+2}", f"RTD{r}_XB"),
        R(f"R{b+4}", "100R", f"RTD{r}_XB", f"RTD{r}_IB", "0805W8F1000T5E", "C17408"),
        # sense branches: same network as a thermocouple leg (2.2k -> clamp -> 1k)
        R(f"R{b+5}", "2.2k", a, f"RTD{r}_SAC", *R2K2_1206, fp=R1206, mfr="UNI-ROYAL"),
        bav(f"D{b+3}", f"RTD{r}_SAC"),
        R(f"R{b+6}", "1k", f"RTD{r}_SAC", f"RTD{r}_SP", "0805W8F1001T5E", "C17513", mfr="UNI-ROYAL"),
        R(f"R{b+7}", "2.2k", bb, f"RTD{r}_SBC", *R2K2_1206, fp=R1206, mfr="UNI-ROYAL"),
        bav(f"D{b+4}", f"RTD{r}_SBC"),
        R(f"R{b+8}", "1k", f"RTD{r}_SBC", f"RTD{r}_SN", "0805W8F1001T5E", "C17513", mfr="UNI-ROYAL"),
        C(f"C{b+1}", "10n C0G", f"RTD{r}_SP", f"RTD{r}_SN", "GRM2195C1H103JA01D", "C97905", mfr="Murata"),
        C(f"C{b+2}", "1n C0G", f"RTD{r}_SP", "RTD_RET", "CL21C102JBCNNNC", "C1791", mfr="Samsung",
          desc="to RTD_RET: pad leakage sees ~0.5 V instead of ~1.8 V to ground"),
        C(f"C{b+3}", "1n C0G", f"RTD{r}_SN", "RTD_RET", "CL21C102JBCNNNC", "C1791", mfr="Samsung"),
        # return lead C: 1k (1206) into the shared reference node (clamped once, D1091)
        R(f"R{b+9}", "1k 1W", c, "RTD_RET", *R1K_2512, fp=R2512,
          desc="return lead limiter; its drop is outside the ratiometric loop"),
    ]


def rtd_bank(config):
    s = Sheet("RTD", "rtd.kicad_sch", "RTD bank: three 3-wire PT100 inputs + check resistor (isolated island)", paper="A3")
    note = "3-wire PT100, element insulated from the sheath"
    hdr = [Part(f"J{BASE+1}", "Connector_Generic:Conn_01x06", "PT100 1-2 (A B C)",
                {str(3 * i + j + 1): f"RTD{i+1}_{lead}" for i in range(2) for j, lead in enumerate("ABC")},
                HDR6, "WJ15EDGRC-3.81-06P", "C7246", "KANGNEX", "mating plug WJ15EDGK-3.81-06P (C7247); " + note),
           Part(f"J{BASE+2}", "Connector_Generic:Conn_01x03", "PT100 3 (A B C)",
                {str(j + 1): f"RTD3_{lead}" for j, lead in enumerate("ABC")},
                HDR3, "WJ15EDGRC-3.81-03P", "C8406", "KANGNEX", "mating plug WJ15EDGK-3.81-03P (C8413); " + note)]
    s.block("PT100 terminals: A = single-wire end, B + C = the two wires of the other end", hdr)
    for r in range(1, 4):
        s.block(f"PT100 {r}: excitation and sense branches, filter, return", rtd(r))
    s.block("Check channel (0039 P5 (b)): a precision resistor through the same network, read every scan", [
        R(f"R{BASE+95}", "150R 0.1%", "CHK_A", "CHK_BC", "RT0805BRD07150RL", "C513734", mfr="YAGEO",
          desc="check resistor in the PT100 range (~130 degC): proves R_ref, IOUT, gain and the network")]
        + rtd(CHECK))
    ain = {}
    for r in range(4):
        ain[f"AIN{4*r}"] = f"RTD{r+1}_IA"
        ain[f"AIN{4*r+1}"] = f"RTD{r+1}_IB"
        ain[f"AIN{4*r+2}"] = f"RTD{r+1}_SP"
        ain[f"AIN{4*r+3}"] = f"RTD{r+1}_SN"
    u = BASE
    adc = Part(f"U{u+1}", f"{config.library}:AD7124-8", "AD7124-8BCPZ", dict(ain, **{
        "REFIN1(+)": "RTD_RET", "REFIN1(-)": "RTD_REFN", "REFOUT": "REFOUT_R",
        "REGCAPA": "REGCAPA_R", "REGCAPD": "REGCAPD_R", "PSW": NC,
        "SYNC": ISO if config.sync_tied else "SYNC_R", "CLK": NC, "~{CS}": "CS_RTD_ISO", "SCLK": "SCLK_ISO",
        "DIN": "DIN_ISO", "DOUT/~{RDY}": "DOUT_ISO", "AVDD": ISO, "IOVDD": ISO,
        "AVSS": GND, "DGND": GND, "EP": GND}),
        "Package_CSP:LFCSP-32-1EP_5x5mm_P0.5mm_EP3.6x3.6mm", "AD7124-8BCPZ", "C97314", "ADI",
        "RTD bank: IOUT 2 x 250 uA swapped each reading, gain 16, REFIN1 = R_ref (ratiometric), EP to AVSS")
    s.block("AD7124-8 (RTD), reference resistor and decoupling", [
        adc,
        R(f"R{u+92}", "2.49k 0.1%", "RTD_RET", "RTD_REFN", "RT0805BRD072K49L", "C375522",
          mfr="YAGEO", desc="R_ref, Kelvin: REFIN1+ at its top pad, REFIN1- at its bottom pad"),
        R(f"R{u+93}", "330R", "RTD_REFN", GND, "0805W8F3300T5E", "C17630",
          desc="reference-buffer headroom: 500 uA x 330R = 0.165 V >= 0.1 V"),
        C(f"C{u+90}", "100n", "RTD_RET", "RTD_REFN", *C100N, desc="REFIN1 differential filter"),
        bav(f"D{u+91}", "RTD_RET"),
        C(f"C{u+91}", "100n", "REFOUT_R", GND, *C100N, desc="REFOUT, never joined"),
        C(f"C{u+92}", "100n", "REGCAPA_R", GND, *C100N),
        C(f"C{u+93}", "100n", "REGCAPD_R", GND, *C100N),
        C(f"C{u+94}", "100n", ISO, GND, *C100N, desc="AVDD"),
        C(f"C{u+95}", "1u", ISO, GND, "CL21B105KBFNNNE", "C28323", desc="AVDD bulk"),
        C(f"C{u+96}", "100n", ISO, GND, *C100N, desc="IOVDD"),
        C(f"C{u+97}", "1u", ISO, GND, "CL21B105KBFNNNE", "C28323", desc="IOVDD bulk"),
    ])
    return s

