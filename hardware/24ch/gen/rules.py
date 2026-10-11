"""Net classes, isolation rules, planes and barrier keep-outs for the 24-ch board.

Every net is put in a domain by where its pads are: the sensor island, the
RS-485 bus pocket or the control side. A net with pads in two domains is a
design error and stops the script. Run with KiCad's python after place.py.
"""
import json
import os

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
BOARD = os.path.join(OUT, "thermo24.kicad_pcb")
PRO = os.path.join(OUT, "thermo24.kicad_pro")
DRU = os.path.join(OUT, "thermo24.kicad_dru")
mm = pcbnew.FromMM

ISLAND = [(0, 0), (42, 0), (42, 103), (170, 103), (170, 145), (0, 145)]
CONTROL = [(45, 0), (52, 0), (52, 25), (87, 25), (87, 0), (170, 0), (170, 100), (45, 100)]
POCKET = [(55, 0), (84, 0), (84, 22), (55, 22)]
# the left band starts below U401: the B0505 pins are 2.54 mm apart, so its island
# pins sit inside a 3 mm band; the module itself is the barrier there (rule b0505_area)
BANDS = [[(42, 10.8), (45, 10.8), (45, 100), (42, 100)],
         [(42, 100), (170, 100), (170, 103), (42, 103)],
         [(52, 22), (87, 22), (87, 25), (52, 25)],
         [(52, 0), (55, 0), (55, 22), (52, 22)],
         [(84, 0), (87, 0), (87, 22), (84, 22)]]
PLANES = {  # domain: (In1 net, In2 net, outer-layer pour net)
    "ISLAND": ("GND_ISO", "+3V3_ISO", "GND_ISO"),
    "CONTROL": ("GND", "+5V", "GND"),
    "POCKET": ("GND_RS485", "GND_RS485", "GND_RS485"),
}
CONTACT = {"TRIP_COM", "TRIP_NO", "TRIP_NC", "TRIP_MID", "ALM_COM", "ALM_NO", "ALM_NC"}
PWR24 = {"+24V_RAW", "+24V_FUSED", "+24V_PROT"}


def inside(poly, x, y):
    c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def domain(x, y):
    if inside(POCKET, x, y):
        return "POCKET"
    if inside(ISLAND, x, y):
        return "ISLAND"
    if inside(CONTROL, x, y):
        return "CONTROL"
    return "BAND"


def classify(b):
    doms = {}
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            net = pad.GetNetname()
            if not net:
                continue
            p = pad.GetPosition()
            d = domain(pcbnew.ToMM(p.x), pcbnew.ToMM(p.y))
            if d == "BAND" and fp.GetReference() == "U401":
                d = "ISLAND" if pad.GetNumber() in ("3", "4") else "CONTROL"
            doms.setdefault(net, set()).add((d, fp.GetReference()))
    bad = {n: s for n, s in doms.items() if len({d for d, _ in s}) > 1}
    if bad:
        for n, s in sorted(bad.items()):
            print("DOMAIN CONFLICT", n, sorted(s))
        raise SystemExit("nets span two domains")
    return {n: next(iter(s))[0] for n, s in doms.items()}


def netclass_of(net, dom):
    bare = net.rsplit("/", 1)[-1]
    if bare == "CHASSIS":
        return "Chassis"
    if bare in CONTACT:
        return "Contact"
    if bare in PWR24:
        return "Power24V"
    if dom == "ISLAND":
        return "IslandPower" if bare in ("GND_ISO", "+3V3_ISO", "+5V_ISO_RAW") else "Island"
    if dom == "POCKET":
        return "RS485"
    if bare in ("+5V", "GND"):
        return "CtrlPower"
    return "Default"


CLASSES = {  # name: (track, clearance, via diameter, via drill)
    # 0.15 mm: the AD7124 LFCSP has 0.25 mm between pads, so 0.20 (+ the router's
    # margin) made every ADC pad a violation and Freerouting would not connect them
    "Default": (0.20, 0.15, 0.60, 0.30),
    "Island": (0.20, 0.15, 0.60, 0.30),
    "IslandPower": (0.50, 0.20, 0.80, 0.40),
    "CtrlPower": (0.60, 0.20, 0.80, 0.40),
    "Power24V": (0.80, 0.25, 0.90, 0.50),
    "Contact": (0.80, 1.00, 1.00, 0.60),   # contact-to-contact (30 VDC); 2 mm to the rest is a .kicad_dru rule
    "RS485": (0.40, 0.25, 0.70, 0.35),
    "Chassis": (0.80, 0.25, 0.90, 0.50),
}


def write_project(assign):
    pro = json.load(open(PRO, encoding="utf-8"))
    ns = pro.setdefault("net_settings", {})
    tmpl = dict(ns["classes"][0])
    classes = []
    for i, (name, (tw, cl, vd, vr)) in enumerate(CLASSES.items()):
        c = dict(tmpl)
        c.update(name=name, track_width=tw, clearance=cl, via_diameter=vd, via_drill=vr,
                 priority=2147483647 if name == "Default" else i)
        classes.append(c)
    ns["classes"] = classes
    ns["netclass_patterns"] = [{"netclass": c, "pattern": n}
                               for n, c in sorted(assign.items()) if c != "Default"]
    ns.pop("netclass_assignments", None)
    rules = pro["board"]["design_settings"]["rules"]
    rules.update(min_clearance=0.15, min_track_width=0.2, min_via_diameter=0.5,
                 min_via_annular_width=0.15, min_through_hole_diameter=0.3,
                 min_copper_edge_clearance=0.5, min_hole_clearance=0.25, min_hole_to_hole=0.25)
    json.dump(pro, open(PRO, "w", encoding="utf-8"), indent=2)


def pair(a, b):
    ta = " || ".join(f"A.NetClass == '{x}'" for x in a)
    tb = " || ".join(f"B.NetClass == '{x}'" for x in b)
    ra = " || ".join(f"B.NetClass == '{x}'" for x in a)
    rb = " || ".join(f"A.NetClass == '{x}'" for x in b)
    return f"(({ta}) && ({tb})) || (({rb}) && ({ra}))"


def write_dru():
    isl = ("Island", "IslandPower")
    others = tuple(c for c in CLASSES if c not in isl)
    rest = tuple(c for c in CLASSES if c != "RS485")
    lines = ["(version 1)", "",
             "# Generated by hardware/24ch/gen/rules.py - edit that file.",
             "# FUNCTIONAL isolation for a prototype, not an IEC 61010 qualification.",
             "",
             "# NORI Solutions (fab/assembler, 0033 D2): pad-to-track 0.2 mm minimum. First, so",
             "# every larger rule below overrides it. Vias follow their track/space (0.09 mm;",
             "# the net classes keep 0.15) - confirm with NORI (I-106).",
             '(rule "nori_pad_to_track" (constraint clearance (min 0.2mm))',
             "  (condition \"(A.Type == 'Pad' && B.Type == 'Track') || (B.Type == 'Pad' && A.Type == 'Track')\"))", "",
             "# Pads already joined by tracks or plane vias: one spoke into an outer pour is enough.",
             '(rule "pour_spokes" (constraint min_resolved_spokes 1))', "",
             '(rule "island_to_rest" (constraint clearance (min 3mm))',
             f'  (condition "{pair(isl, others)}"))', "",
             '(rule "rs485_to_rest" (constraint clearance (min 3mm))',
             f'  (condition "{pair(("RS485",), rest)}"))', "",
             '(rule "contact_to_rest" (constraint clearance (min 2mm))',
             f'  (condition "{pair(("Contact",), tuple(c for c in CLASSES if c != "Contact"))}"))', "",
             '(rule "chassis_to_rest" (constraint clearance (min 1.5mm))',
             f'  (condition "{pair(("Chassis",), tuple(c for c in CLASSES if c != "Chassis"))}"))', "",
             "# The B0505S SIP-4 has 2.54 mm pitch (1.04 mm between pads); its 1500 VDC rating",
             "# covers pins 2-3, so inside its courtyard the module is the barrier.",
             '(rule "b0505_area" (constraint clearance (min 1.0mm))',
             "  (condition \"A.intersectsCourtyard('U401') && B.intersectsCourtyard('U401')\"))", "",
             "# K701 pin 7 (pole 2 NC) touches TRIP_MID while the relay is off: contact metal,",
             "# 1.5 mm to the rest. K702's unused pole is floating metal and gets no rule.",
             '(rule "relay_spare_contacts" (constraint clearance (min 1.5mm))',
             "  (condition \"A.NetName == 'unconnected-(K701-Pad7)'\"))", "",
             '(rule "relay_spare_to_contact" (constraint clearance (min 0.3mm))',
             "  (condition \"A.NetName == 'unconnected-(K701-Pad7)' && B.NetClass == 'Contact'\"))", "",
             "# Inside a relay's courtyard its own coil-contact rating is the barrier (contact",
             "# tracks have to leave pins 1.4 mm apart). Only relaxes contact_to_rest: two",
             "# low-voltage nets there keep their normal class clearance.",
             '(rule "relay_area" (constraint clearance (min 0.5mm))',
             "  (condition \"((A.intersectsCourtyard('K701') && B.intersectsCourtyard('K701')) || "
             "(A.intersectsCourtyard('K702') && B.intersectsCourtyard('K702'))) && "
             "(A.NetClass == 'Contact' || B.NetClass == 'Contact')\"))", "",
             "# Relay pads: the G6K's own coil-contact rating covers its pin spacing.",
             '(rule "relay_own_pins" (constraint clearance (min 0.3mm))',
             "  (condition \"(A.memberOfFootprint('K701') && B.memberOfFootprint('K701')) || "
             "(A.memberOfFootprint('K702') && B.memberOfFootprint('K702'))\"))", "",
             "# C610/R607 bridge CHASSIS to GND on purpose.",
             '(rule "chassis_bridge_own_pins" (constraint clearance (min 0.3mm))',
             "  (condition \"(A.memberOfFootprint('C610') && B.memberOfFootprint('C610')) || "
             "(A.memberOfFootprint('R607') && B.memberOfFootprint('R607'))\"))", ""]
    open(DRU, "w", encoding="utf-8", newline="\n").write("\n".join(lines))


def poly_outline(pts):
    chain = pcbnew.SHAPE_LINE_CHAIN()
    for x, y in pts:
        chain.Append(mm(x), mm(y))
    chain.SetClosed(True)
    return chain


def find_net(b, bare):
    for name, n in b.GetNetsByName().items():
        if str(name).rsplit("/", 1)[-1] == bare:
            return n
    raise SystemExit(f"no net {bare}")


def add_zone(b, net, layer, pts, prio, name):
    z = pcbnew.ZONE(b)
    z.SetLayer(layer)
    z.SetNet(find_net(b, net))
    z.Outline().AddOutline(poly_outline(pts))
    z.SetAssignedPriority(prio)
    z.SetZoneName(name)
    z.SetMinThickness(mm(0.25))
    z.SetThermalReliefGap(mm(0.5))
    z.SetThermalReliefSpokeWidth(mm(0.5))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    b.Add(z)


def add_keepout(b, pts, name):
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True)
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET()
    for l in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        ls.AddLayer(l)
    z.SetLayerSet(ls)
    z.Outline().AddOutline(poly_outline(pts))
    z.SetZoneName(name)
    b.Add(z)


def add_thermal_vias(b):
    """Three 0.3 mm vias in U601's exposed pad to the GND planes (decision 0023), on the
    gap between its paste windows (I-110: none under paste; the other gaps are too narrow)."""
    fp = b.FindFootprintByReference("U601")
    ep = [p for p in fp.Pads() if p.GetNumber() == "9"][0]
    c = ep.GetPosition()
    net = b.FindNet("GND")
    for t in list(b.GetTracks()):
        if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == "GND" and \
                abs(t.GetPosition().x - c.x) < mm(2) and abs(t.GetPosition().y - c.y) < mm(2):
            return   # already there
    for dx in (-0.6, 0.0, 0.6):
        for dy in (0.0,):
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(c.x + mm(dx), c.y + mm(dy)))
            v.SetWidth(mm(0.6))
            v.SetDrill(mm(0.3))
            v.SetNet(net)
            b.Add(v)


def main():
    import subprocess, sys
    subprocess.run([sys.executable, os.path.abspath(__file__), "--strip"], check=True)
    b = pcbnew.LoadBoard(BOARD)
    doms = classify(b)
    assign = {n: netclass_of(n, d) for n, d in doms.items()}
    counts = {}
    for c in assign.values():
        counts[c] = counts.get(c, 0) + 1
    print("net classes:", counts)
    import sys
    layers = (pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.F_Cu, pcbnew.B_Cu)
    for dom, pts in (("ISLAND", ISLAND), ("CONTROL", CONTROL), ("POCKET", POCKET)):
        in1, in2, outer = PLANES[dom]
        for layer, net in zip(layers, (in1, in2, outer, outer)):
            if layer in (pcbnew.F_Cu, pcbnew.B_Cu) and "--route-prep" in sys.argv:
                continue   # no outer pours while Freerouting runs (planes In1/In2 only)
            add_zone(b, net, layer, pts, 1 if dom == "POCKET" else 0, f"{dom}_{b.GetLayerName(layer)}")
    for i, pts in enumerate(BANDS):
        add_keepout(b, pts, f"BARRIER_{i}")
    add_thermal_vias(b)
    pcbnew.SaveBoard(BOARD, b)
    write_project(assign)
    write_dru()
    print("zones, keep-outs, net classes and rules written")


def strip():
    """Remove previous zones (child process: SWIG pointers die after Remove)."""
    b = pcbnew.LoadBoard(BOARD)
    zones = list(b.Zones())
    for z in zones:
        b.Remove(z)
    pcbnew.SaveBoard(BOARD, b)
    print(f"removed {len(zones)} old zones")


if __name__ == "__main__":
    import guard      # I-115: refuse while KiCad or another tool holds the board
    with guard.claim(str(BOARD), "rules.py"):
        import sys
        strip() if "--strip" in sys.argv else main()
