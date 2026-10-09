"""Place parts and write KiCad 10 schematic sheets (label-per-pin style)."""
import math
import uuid

from libs import load, pins, bbox
from sexp import Sym, dump

NS = uuid.UUID("6a3c1e0e-24c8-4b51-9a31-7e6f3a2d0b24")
PAPER = {"A4": (297, 210), "A3": (420, 297), "A2": (594, 420), "A1": (841, 594)}
G = 2.54
STUB = 2.54
VERSION = 20260306


def uid(key):
    return str(uuid.uuid5(NS, key))


def snap(v):
    return round(math.ceil(v / G) * G, 2)


def textlen(net, glob):
    return len(net) * 1.27 * 0.62 + (3.5 if glob else 1.0)


def effects(size=1.27, justify=None, hide=False):
    e = [Sym("effects"), [Sym("font"), [Sym("size"), size, size]]]
    if justify:
        e.append([Sym("justify")] + [Sym(j) for j in justify.split()])
    if hide:
        e.append([Sym("hide"), Sym("yes")])
    return e


def prop(name, value, x, y, hide=False, justify=None, angle=0):
    return [Sym("property"), name, value, [Sym("at"), x, y, angle],
            effects(justify=justify, hide=hide)]


def outward(angle):
    a = math.radians(angle + 180)
    return round(math.cos(a)), round(-math.sin(a))


def label_angle(dx, dy):
    return {(-1, 0): 180, (1, 0): 0, (0, -1): 90, (0, 1): 270}[(dx, dy)]


class SheetWriter:
    def __init__(self, sheet, glob_nets, project, root_uuid, sheet_uuid, local_dir):
        self.s, self.glob, self.project = sheet, glob_nets, project
        self.root_uuid, self.sheet_uuid, self.dir = root_uuid, sheet_uuid, local_dir
        self.items, self.libs, self.tside = [], {}, {}

    # -- geometry --------------------------------------------------------
    def _cell(self, part):
        sym = load(part.lib_id, self.dir)
        xmin, ymin, xmax, ymax = bbox(sym)
        side = {"L": 0.0, "R": 0.0, "T": 0.0, "B": 0.0}
        seen = set()
        for num, (nm, px, py, a, u, t) in pins(sym).items():
            if (px, py) in seen:
                continue
            seen.add((px, py))
            net = part.pinmap[num]
            dx, dy = outward(a)
            ln = STUB + (0 if net == "<NC>" else textlen(net, net in self.glob))
            key = {(-1, 0): "L", (1, 0): "R", (0, -1): "T", (0, 1): "B"}[(dx, dy)]
            side[key] = max(side[key], ln)
        used = {k for k in side if side[k] > 0}
        tw = max(len(part.ref), len(part.value)) * 1.27 * 0.62 + 1.5
        if part.ref.startswith("#"):
            ts = "R"
        elif "R" not in used:
            ts, side["R"] = "R", tw
        elif "T" not in used:
            ts, side["T"] = "T", 6.0
        elif "B" not in used:
            ts, side["B"] = "B", 6.0
        else:
            ts = "C"   # corner above the top-right; ICs with pins on all sides
            side["T"] += 4.0
        self.tside[part.ref] = ts
        w = max((xmax - xmin) + side["L"] + side["R"], tw) + 5
        h = (ymax - ymin) + side["T"] + side["B"] + 5
        return sym, (xmin, ymin, xmax, ymax), side, w, h

    def _block(self, parts, maxw):
        """Lay parts out inside one block; return (local placements, w, h)."""
        x = y = rowh = wmax = 0.0
        out = []
        for p in parts:
            sym, bb, side, w, h = self._cell(p)
            if x + w > maxw and x > 0:
                x, y, rowh = 0.0, y + rowh, 0.0
            out.append((p, sym, bb, x + side["L"] - bb[0], y + side["T"] + bb[3] + 2.5))
            x += w
            wmax = max(wmax, x)
            rowh = max(rowh, h)
        return out, wmax, y + rowh

    def layout(self):
        while True:
            pw, ph = PAPER[self.s.paper]
            x0, top, maxw = 15.0, 18.0, pw - 30.0
            placed, titles = [], []
            x, y, rowh = x0, top, 0.0
            for title, parts in self.s.blocks:
                loc, bw, bh = self._block(parts, maxw)
                bw = max(bw, len(title) * 1.75 + 4)
                if x + bw > pw - 15 and x > x0:
                    x, y, rowh = x0, y + rowh + 6, 0.0
                titles.append((title, x, y))
                for p, sym, bb, lx, ly in loc:
                    placed.append((p, sym, snap(x + lx), snap(y + 5 + ly), bb))
                x += bw + 8
                rowh = max(rowh, bh + 5)
            need = y + rowh + 12
            if need <= ph - 15 or self.s.paper == "A1":
                break
            names = list(PAPER)
            self.s.paper = names[names.index(self.s.paper) + 1]
        for title, tx, ty in titles:
            self.items.append([Sym("text"), title, [Sym("exclude_from_sim"), Sym("no")],
                               [Sym("at"), tx, ty + 2, 0], effects(2.0, "left bottom"),
                               [Sym("uuid"), uid(f"{self.s.name}:title:{title}")]])
        return placed

    # -- emission --------------------------------------------------------
    def _label(self, net, x, y, ang, key):
        if net in self.glob:
            just = "left" if ang in (0, 90) else "right"
            return [Sym("global_label"), net, [Sym("shape"), Sym("bidirectional")],
                    [Sym("at"), x, y, ang], [Sym("fields_autoplaced"), Sym("yes")],
                    effects(justify=just), [Sym("uuid"), uid(key)],
                    prop("Intersheetrefs", "${INTERSHEET_REFS}", x, y, hide=True)]
        just = "left bottom" if ang in (0, 90) else "right bottom"
        return [Sym("label"), net, [Sym("at"), x, y, ang], effects(justify=just),
                [Sym("uuid"), uid(key)]]

    def _symbol(self, p, sym, sx, sy, bb):
        self.libs[p.lib_id] = sym
        path = f"/{self.root_uuid}" + (f"/{self.sheet_uuid}" if self.sheet_uuid else "")
        node = [Sym("symbol"), [Sym("lib_id"), p.lib_id], [Sym("at"), sx, sy, 0],
                [Sym("unit"), 1], [Sym("exclude_from_sim"), Sym("no")],
                [Sym("in_bom"), Sym("yes" if p.in_bom else "no")],
                [Sym("on_board"), Sym("yes" if p.on_board else "no")],
                [Sym("dnp"), Sym("yes" if p.dnp else "no")],
                [Sym("uuid"), uid(f"{self.s.name}:sym:{p.ref}")]]
        hide_ref = p.ref.startswith("#")
        ts = self.tside.get(p.ref, "R")
        top, bot, right = sy - bb[3], sy - bb[1], sx + bb[2]
        if ts == "R":
            rpos, vpos = (right + 0.8, sy - 1.0), (right + 0.8, sy + 1.6)
        elif ts == "T":
            rpos, vpos = (sx + bb[0], top - 3.4), (sx + bb[0], top - 1.0)
        elif ts == "B":
            rpos, vpos = (sx + bb[0], bot + 2.0), (sx + bb[0], bot + 4.4)
        else:
            rpos, vpos = (right + 1.0, top - 3.0), (right + 1.0, top - 0.6)
        node.append(prop("Reference", p.ref, *rpos, hide=hide_ref, justify="left"))
        node.append(prop("Value", p.value, *vpos, hide=hide_ref, justify="left"))
        node.append(prop("Footprint", p.footprint, sx, sy, hide=True))
        node.append(prop("Datasheet", "", sx, sy, hide=True))
        node.append(prop("Description", p.desc, sx, sy, hide=True))
        for k, v in (("MPN", p.mpn), ("Manufacturer", p.mfr), ("LCSC", p.lcsc)):
            if v:
                node.append(prop(k, v, sx, sy, hide=True))
        for num in pins(sym):
            node.append([Sym("pin"), num, [Sym("uuid"), uid(f"{self.s.name}:{p.ref}:pin{num}")]])
        node.append([Sym("instances"), [Sym("project"), self.project,
                     [Sym("path"), path, [Sym("reference"), p.ref], [Sym("unit"), 1]]]])
        self.items.append(node)
        seen = set()
        for num, (nm, px, py, a, u, t) in pins(sym).items():
            ax, ay = round(sx + px, 2), round(sy - py, 2)
            if (ax, ay) in seen:
                continue
            seen.add((ax, ay))
            net = p.pinmap[num]
            k = f"{self.s.name}:{p.ref}:{num}"
            if net == "<NC>":
                self.items.append([Sym("no_connect"), [Sym("at"), ax, ay],
                                   [Sym("uuid"), uid(k + ":nc")]])
                continue
            dx, dy = outward(a)
            lx, ly = round(ax + dx * STUB, 2), round(ay + dy * STUB, 2)
            self.items.append([Sym("wire"), [Sym("pts"), [Sym("xy"), ax, ay], [Sym("xy"), lx, ly]],
                               [Sym("stroke"), [Sym("width"), 0], [Sym("type"), Sym("default")]],
                               [Sym("uuid"), uid(k + ":w")]])
            self.items.append(self._label(net, lx, ly, label_angle(dx, dy), k + ":l"))

    def build(self, extra=None):
        placed = self.layout()
        for p, sym, sx, sy, bb in placed:
            self._symbol(p, sym, sx, sy, bb)
        for t in self.s.notes:
            self.items.append(t)
        head = [Sym("kicad_sch"), [Sym("version"), VERSION], [Sym("generator"), "eeschema"],
                [Sym("generator_version"), "10.0"],
                [Sym("uuid"), self.sheet_file_uuid()], [Sym("paper"), self.s.paper],
                [Sym("title_block"), [Sym("title"), self.s.title],
                 [Sym("company"), "Thermo 24-ch protection unit"], [Sym("rev"), "A3"],
                 [Sym("comment"), 1, "Generated by hardware/24ch/gen - edit the generator, not this file"]],
                [Sym("lib_symbols")] + list(self.libs.values())]
        body = head + self.items + (extra or [])
        if not self.sheet_uuid:
            body.append([Sym("sheet_instances"), [Sym("path"), "/", [Sym("page"), "1"]]])
        body.append([Sym("embedded_fonts"), Sym("no")])
        return dump(body) + "\n"

    def sheet_file_uuid(self):
        return self.root_uuid if not self.sheet_uuid else uid(f"file:{self.s.file}")
