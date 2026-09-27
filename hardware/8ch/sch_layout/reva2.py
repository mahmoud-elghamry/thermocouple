# REV A2 changes from the 2026-09-27 pre-fabrication review, applied to the
# label-only base before the layout pass (called from fixes.py).
#   I-065  U10/U11 without the F suffix (open input -> HIGH, CS deselected in
#          reset) + R61 2k2 between U11 OUTF and MISO_CTRL so the AVR wins ISP
#   I-066  Q1 2N7000 (60 V) -> BSS131 (240 V), SOT-23, same G/S/D geometry
#   I-067  R53/R54 22k/4k7 -> 100k/22k: 0.28 mA into PC2's clamp at 58 V
#   I-068  F1 30 V 1206 PTC -> 60 V 0.75 A 1812
#   I-069  D2 drawn unidirectional; D3 ordered as the SMA part "M7"
# Values and part choices: docs/decisions/0022, CALCULATIONS.md section 4.
import json
from kon import K
from geom import load, body

PROPS = {
    "U10": dict(value="ISO7760DWR", fields={"MPN": "ISO7760DWR", "LCSC": "C882724",
                "Description": "Reinforced digital isolation for SPI clock, MOSI, and CS1-CS4; "
                "NOT the F suffix - default output must be HIGH (I-065) | "
                "Manufacturer: Texas Instruments | MPN: ISO7760DWR"}),
    "U11": dict(value="ISO7761DWR", fields={"MPN": "ISO7761DWR", "LCSC": "C2871529",
                "Description": "Reinforced digital isolation for CS5-CS8 and reverse MISO; "
                "NOT the F suffix - default output must be HIGH (I-065) | "
                "Manufacturer: Texas Instruments | MPN: ISO7761DWR"}),
    "Q1": dict(value="BSS131", footprint="Package_TO_SOT_SMD:SOT-23",
               datasheet="../../docs/reference/datasheets/BSS131.pdf",
               fields={"MPN": "BSS131H6327XTSA1", "Manufacturer": "Infineon", "LCSC": "C151498",
                       "Description": "Low-side driver for the 24 V run-permit relay, 240 V: "
                       "its drain sees the battery rail (I-066) | Manufacturer: Infineon | "
                       "MPN: BSS131H6327XTSA1"}),
    "F1": dict(value="PTC 0.75A 60V", footprint="Fuse:Fuse_1812_4532Metric",
               datasheet="../../docs/reference/datasheets/1812L-PTC.pdf",
               fields={"MPN": "1812L075/60GR", "Manufacturer": "LUTE", "LCSC": "C48985874",
                       "Description": "Resettable input over-current protection, 60 V rated "
                       "(I-068); the panel fuse of decision 0020 breaks battery shorts"}),
    "R53": dict(value="100k", fields={"MPN": "0805W8F1003T5E", "LCSC": "C149504",
                "Description": "Run-permit read-back divider, upper leg (I-067)"}),
    "R54": dict(value="22k", fields={"MPN": "0805W8F2202T5E", "LCSC": "C17560",
                "Description": "Run-permit read-back divider, lower leg (I-067)"}),
    "R61": dict(value="2k2", footprint="Resistor_SMD:R_0805_2012Metric",
                fields={"MPN": "0805W8F2201T5E", "LCSC": "C17520",
                        "Description": "ISP series resistor: the AVR overrides U11's MISO "
                        "output while it is programmed (I-065)"}),
    "D2": dict(fields={"Manufacturer": "R+O"}),
    "D3": dict(value="M7", fields={"MPN": "M7", "Manufacturer": "MDD", "LCSC": "C95872",
               "Description": "Relay coil flyback clamp, 1N4007-class in SMA - "
               "do not order the through-hole 1N4007 (I-069)"}),
    # 0023: the plain EP footprint; board/stitching.py puts 0.3 mm thermal
    # vias under the pad instead of the footprint's 0.2 mm ones.
    "U14": dict(footprint="Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.3mm"),
    "U12": dict(fields={"Description": "Shared 1 kV functional-isolation supply for the "
                "measurement island | Manufacturer: XP Power | MPN: IA0505S - not the "
                "regulated 'IA0505S-1WR3' of another maker (I-069)"}),
}


def ok(r):
    assert "rror" not in r[:60], r
    return r


def apply(S):
    k = K(); k.load("sch_components", "sch_wiring", "sch_analysis")
    ok(k.call("replace_component", schematic=S, reference="Q1",
              new_lib_id="Transistor_FET:Q_NMOS_GSD"))
    ok(k.call("replace_component", schematic=S, reference="D2", new_lib_id="Device:D_Zener"))
    # R61 left of U11 pin 7 (OUTF); build's relayout then puts it where extra.py says.
    _, libs, syms = load(S)
    _, t = body(next(s for s in syms if s["ref"] == "U11"), libs)
    x7, y7 = t["7"]
    ok(k.call("add_schematic_component", schematic=S, lib_id="Device:R", reference="R61",
              x=x7 - 6.35, y=y7, rotation=90))
    _, libs, syms = load(S)
    _, rt = body(next(s for s in syms if s["ref"] == "R61"), libs)
    near = min(rt, key=lambda n: abs(rt[n][0] - x7))
    far = "1" if near == "2" else "2"
    labels = json.loads(k.call("list_schematic_labels", schematic=S))["labels"]
    old = [l for l in labels if round(l["x"], 2) == x7 and round(l["y"], 2) == y7]
    assert len(old) == 1 and old[0]["net"] == "MISO_CTRL", old
    ok(k.call("delete_schematic_net_label", schematic=S, net="MISO_CTRL", x=x7, y=y7))
    ok(k.call("add_schematic_net_label", schematic=S, net="MISO_ISO", x=x7, y=y7,
              rotation=old[0]["rotation"]))
    ok(k.call("add_schematic_net_label", schematic=S, net="MISO_ISO",
              x=rt[near][0], y=rt[near][1], rotation=0))
    ok(k.call("add_schematic_net_label", schematic=S, net="MISO_CTRL",
              x=rt[far][0], y=rt[far][1], rotation=0))
    for ref, p in PROPS.items():
        args = {a: p[a] for a in ("value", "footprint", "datasheet") if a in p}
        ok(k.call("edit_schematic_component", schematic=S, reference=ref,
                  fields=p.get("fields", {}), **args))
