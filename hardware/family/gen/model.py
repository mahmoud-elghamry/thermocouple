"""Circuit model: parts with pin->net maps, grouped into blocks and sheets.

A net that appears on more than one sheet becomes a global label; every
other net is a local label. Pin keys may be pin numbers or pin names; a name
that occurs on several pins (GND, VCC) connects all of them.
"""
from libs import load, pins

NC = "<NC>"   # pin left unconnected on purpose (gets a no-connect flag)


class Part:
    def __init__(self, ref, lib_id, value, nets, footprint, mpn="", lcsc="",
                 mfr="", desc="", dnp=False, in_bom=True, on_board=True):
        self.ref, self.lib_id, self.value = ref, lib_id, value
        self.footprint, self.mpn, self.lcsc, self.mfr = footprint, mpn, lcsc, mfr
        self.desc, self.dnp, self.in_bom, self.on_board = desc, dnp, in_bom, on_board
        self._nets = dict(nets)
        self.pinmap = None   # number -> net, filled by resolve()

    def resolve(self, local_dir):
        sym = load(self.lib_id, local_dir)
        pl = pins(sym)
        out = {}
        for key, net in self._nets.items():
            key = str(key)
            if key in pl:
                out[key] = net
                continue
            hits = [n for n, p in pl.items() if p[0] == key]
            if not hits:
                raise KeyError(f"{self.ref}: no pin '{key}' on {self.lib_id}")
            for n in hits:
                out[n] = net
        missing = [n for n in pl if n not in out]
        if missing:
            raise KeyError(f"{self.ref}: unassigned pins {missing} on {self.lib_id}")
        self.pinmap = out
        return out


class Sheet:
    def __init__(self, name, file, title, paper="A3"):
        self.name, self.file, self.title, self.paper = name, file, title, paper
        self.blocks = []          # (title, [Part])
        self.flags = []           # nets that get a PWR_FLAG here
        self.notes = []           # free text notes

    def block(self, title, parts):
        self.blocks.append((title, list(parts)))

    def parts(self):
        return [p for _, ps in self.blocks for p in ps]


# ---- small part factories -------------------------------------------------

R0805 = "Resistor_SMD:R_0805_2012Metric"
R1206 = "Resistor_SMD:R_1206_3216Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"


def R(ref, value, a, b, mpn="", lcsc="", fp=R0805, desc="", mfr=""):
    return Part(ref, "Device:R", value, {"1": a, "2": b}, fp, mpn, lcsc, mfr, desc)


def C(ref, value, a, b, mpn="", lcsc="", fp=C0805, desc="", mfr=""):
    return Part(ref, "Device:C", value, {"1": a, "2": b}, fp, mpn, lcsc, mfr, desc)


def TP(ref, net):
    return Part(ref, "Connector_Generic:Conn_01x01", net, {"1": net},
                "TestPoint:TestPoint_THTPad_D2.0mm_Drill1.0mm", in_bom=False)
