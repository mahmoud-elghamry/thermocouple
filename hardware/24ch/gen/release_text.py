"""Supplier-facing facts shared by fab.py (ORDER-NOTES) and assembly_spec.py (ASSEMBLY-SPEC), so the two agree.

FAB_LIMITS: measured on the A4 board 2026-10-25 (pcbnew: track widths, via sizes, pad drills; netclass and
.kicad_dru clearances). VIAS_NEAR_PADS: the via-to-land list of family `holes.py` on the same board; the
release audit (release_audit.py) fails if the board shows any pair not listed here or any pair on two nets.
"""

FAB_LIMITS = ("track 0.20 mm; spacing 0.15 mm (0.20 mm pad to track; AD7124 LFCSP 0.5 mm pitch); "
              "vias 0.6/0.3 mm (0.15 mm ring, 622 of 631), smallest drill 0.3 mm")
OUTLINE = ("Only the outer rectangle is routed: no milled slots or cut-outs. The isolation gaps between the sensor "
           "side, the control side and the RS-485 block are copper-free areas on all layers, not slots.")
# pad -> (via net, drilled hole to pad copper in mm; negative = the hole cuts into the pad). pcbnew shape collision,
# 2026-10-25: the 0.6 mm copper ring of each of these vias joins its pad.
VIAS_NEAR_PADS = {
    "U405.15": ("CS_CJ6_ISO", -0.075), "U302.6": ("+3V3_ISO", 0.050), "U403.13": ("CS_ADC1_ISO", 0.051),
    "C190.2": ("GND_ISO", 0.057), "U703.10": ("GND", 0.060), "C290.2": ("GND_ISO", 0.065),
    "D402.1": ("GND_ISO", 0.066), "C390.1": ("+3V3_ISO", 0.073), "C503.1": ("+5V", 0.074),
    "C506.1": ("+5V", 0.074), "R733.1": ("RS485_DE", 0.084),
}
VIA_NOTE = ("Vias at pads (same net each; please do not hold the order for these, and tell us if your process needs a "
            "change): the drilled hole of one tented via (net CS_CJ6_ISO) cuts 0.075 mm into the side edge of U405 "
            "pad 15. Ten more tented vias have their drilled hole 0.05-0.08 mm from a pad of their own net, the via "
            "ring joining the pad (U302.6, U403.13, U703.10, C190.2, C290.2, C390.1, C503.1, C506.1, D402.1, R733.1).")
EXPOSED_PADS = ("AD7124-8 x3 (U101, U201, U301) and LM5164 (U601) have a pad underneath that must be soldered. "
                "Please X-ray them if you can and send the images: the power-on test checks the supply voltages "
                "only and does not show whether an exposed pad is soldered.")
ACCESSORIES = ("Please quote the items in ACCESSORIES.csv if you can supply them: mating plugs 3.81 mm 8-pin x6 per "
               "board plus 2 spares per order, 2-pin x1 per board, and the JST XH 6-pin housing with 6 contacts. "
               "Standoffs, jumper shunts, the LCD and its cable we buy locally.")
