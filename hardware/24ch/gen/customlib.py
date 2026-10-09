"""Project symbol library: parts the KiCad 10 standard library lacks."""
import os
from sexp import Sym, dump

FONT = [Sym("effects"), [Sym("font"), [Sym("size"), 1.27, 1.27]]]


def _pin(kind, x, y, ang, name, num, length=5.08):
    return [Sym("pin"), Sym(kind), Sym("line"), [Sym("at"), x, y, ang], [Sym("length"), length],
            [Sym("name"), name, FONT], [Sym("number"), str(num), FONT]]


def _hide(node):
    node.append([Sym("hide"), Sym("yes")])
    return node


def _prop(k, v, y, hide=False):
    p = [Sym("property"), k, v, [Sym("at"), 0, y, 0],
         [Sym("effects"), [Sym("font"), [Sym("size"), 1.27, 1.27]]] + ([[Sym("hide"), Sym("yes")]] if hide else [])]
    return p


def _symbol(name, w, h, left, right, top, bottom, fp, ds, desc):
    """left/right/top/bottom: lists of (kind, name, number) in drawing order."""
    pins = []
    for i, (k, n, num) in enumerate(left):
        pins.append(_pin(k, -w - 5.08, h - 2.54 - i * 2.54, 0, n, num))
    for i, (k, n, num) in enumerate(right):
        pins.append(_pin(k, w + 5.08, h - 2.54 - i * 2.54, 180, n, num))
    for i, (k, n, num) in enumerate(top):
        pins.append(_pin(k, -((len(top) - 1) * 2.54) / 2 + i * 2.54, h + 5.08, 270, n, num))
    for i, (k, n, num) in enumerate(bottom):
        pins.append(_pin(k, -((len(bottom) - 1) * 2.54) / 2 + i * 2.54, -h - 5.08, 90, n, num))
    body = [Sym("symbol"), f"{name}_0_1",
            [Sym("rectangle"), [Sym("start"), -w, h], [Sym("end"), w, -h],
             [Sym("stroke"), [Sym("width"), 0.254], [Sym("type"), Sym("default")]],
             [Sym("fill"), [Sym("type"), Sym("background")]]]]
    return [Sym("symbol"), name, [Sym("pin_names"), [Sym("offset"), 1.016]],
            [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")],
            [Sym("on_board"), Sym("yes")],
            _prop("Reference", "U", h + 7.62), _prop("Value", name, -h - 7.62),
            _prop("Footprint", fp, 0, True), _prop("Datasheet", ds, 0, True),
            _prop("Description", desc, 0, True),
            body, [Sym("symbol"), f"{name}_1_1"] + pins]


def ad7124():
    left = [("input", f"AIN{i}", n) for i, n in
            zip(range(16), [4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 17, 18, 19, 20, 21])]
    right = [("input", "REFIN1(+)", 12), ("input", "REFIN1(-)", 13), ("passive", "REFOUT", 22),
             ("passive", "REGCAPA", 24), ("passive", "REGCAPD", 1), ("passive", "PSW", 25),
             ("input", "SYNC", 27), ("bidirectional", "CLK", 31), ("input", "~{CS}", 32),
             ("input", "SCLK", 30), ("input", "DIN", 29), ("tri_state", "DOUT/~{RDY}", 28)]
    top = [("power_in", "AVDD", 26), ("power_in", "IOVDD", 2)]
    bottom = [("power_in", "AVSS", 23), ("power_in", "DGND", 3), ("power_in", "EP", 33)]
    return _symbol("AD7124-8", 12.7, 22.86, left, right, top, bottom,
                   "Package_CSP:LFCSP-32-1EP_5x5mm_P0.5mm_EP3.6x3.6mm",
                   "https://www.analog.com/media/en/technical-documentation/data-sheets/ad7124-8.pdf",
                   "8/16-channel 24-bit sigma-delta ADC, PGA, internal reference (CP-32-12, EP to AVSS)")


def adt7310():
    left = [("input", "SCLK", 1), ("input", "DIN", 3), ("input", "~{CS}", 4)]
    right = [("tri_state", "DOUT", 2), ("open_collector", "~{INT}", 5), ("open_collector", "~{CT}", 6)]
    return _symbol("ADT7310", 7.62, 5.08, left, right, [("power_in", "VDD", 8)],
                   [("power_in", "GND", 7)], "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
                   "https://www.analog.com/media/en/technical-documentation/data-sheets/ADT7310.pdf",
                   "+/-0.5 degC 16-bit SPI digital temperature sensor")


def write(path):
    lib = [Sym("kicad_symbol_lib"), [Sym("version"), 20251024],
           [Sym("generator"), "thermo24_gen"], [Sym("generator_version"), "1.0"],
           ad7124(), adt7310()]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(dump(lib) + "\n")
