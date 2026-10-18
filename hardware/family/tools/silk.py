"""Silkscreen: what an installer or a tester needs, placed where it can be read.

Every terminal pin gets its function (channel 1+ ... 24-, +24V/0V/CHAS, C/NO/NC,
A/B/GND), buttons and LEDs get their function, test points their signal; part
references are hidden except where they help service (connectors, ICs, relays
- only if they fit), the Fab layer keeps them all for assembly. A small placer
puts each text on the nearest spot that clears pads, courtyards (bodies hide
silk), other texts and the board edge; texts it cannot fit are listed. Board
title, the contact rating and the barrier outline as before. Idempotent: old
board-level silkscreen is replaced. Run with KiCad's python.
"""

from profiles import ACTIVE as P, ROOT
import math
import os

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = str(P["pcb"])
mm = pcbnew.FromMM
T = pcbnew.ToMM
W, H = P.require("width"), P.require("height")
PAD_CLEAR = 0.2          # silk to exposed copper
EDGE = 0.6


class Placer:
    def __init__(self, b):
        self.b = b
        self.boxes = []
        self.forced = []
        for fp in b.GetFootprints():
            for p in fp.Pads():
                if p.IsOnLayer(pcbnew.F_Cu) or p.IsOnLayer(pcbnew.F_Mask):
                    self._add(p.GetBoundingBox(), PAD_CLEAR)
            fab = [g for g in fp.GraphicalItems()        # body shapes; Fab text is not printed
                   if g.GetLayer() == pcbnew.F_Fab and g.Type() != pcbnew.PCB_TEXT_T]
            for g in fab:                          # the body outline hides silk
                self._add(g.GetBoundingBox(), 0.1)
            cy = fp.GetCourtyard(pcbnew.F_CrtYd)
            if not fab and cy.OutlineCount():     # no body drawn: keep off the courtyard
                self._add(cy.BBox(), 0.0)
            for g in fp.GraphicalItems():
                if g.GetLayer() == pcbnew.F_SilkS:
                    self._add(g.GetBoundingBox(), 0.1)

    def _add(self, bb, grow):
        self.boxes.append((T(bb.GetLeft()) - grow, T(bb.GetTop()) - grow,
                           T(bb.GetRight()) + grow, T(bb.GetBottom()) + grow))

    @staticmethod
    def ink(t):
        """Glyph box of a text: KiCad's bounding box adds line spacing across the line."""
        bb = t.GetBoundingBox()
        x1, y1, x2, y2 = T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())
        h = T(t.GetTextSize().y) * 1.1 + T(t.GetTextThickness())
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        if abs(t.GetTextAngleDegrees()) % 180 == 90:
            return cx - h / 2, y1, cx + h / 2, y2
        return x1, cy - h / 2, x2, cy + h / 2

    def free(self, box):
        x1, y1, x2, y2 = box
        if x1 < EDGE or y1 < EDGE or x2 > W - EDGE or y2 > H - EDGE:
            return False
        return not any(x1 < c and a < x2 and y1 < d and bq < y2 for a, bq, c, d in self.boxes)

    def text(self, s, x, y, size=1.0, rot=0, bold=False, reach=2.0, prefer=(0, 0), must=True):
        """Place s near (x, y); tries offsets up to `reach` mm, nearest first, biased
        towards `prefer` (a direction vector). Returns the text or None."""
        t = pcbnew.PCB_TEXT(self.b)
        t.SetText(s)
        t.SetLayer(pcbnew.F_SilkS)
        sw, sh = size if isinstance(size, tuple) else (size, size)     # (width, height): narrow glyphs fit
        t.SetTextSize(pcbnew.VECTOR2I(mm(sw), mm(sh)))
        t.SetTextThickness(mm(max(0.15, sw * (0.2 if bold else 0.15))))
        t.SetTextAngleDegrees(rot)
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
        t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
        step = 0.2
        n = int(reach / step)
        offs = sorted(((i * step, j * step) for i in range(-n, n + 1) for j in range(-n, n + 1)
                       if math.hypot(i, j) * step <= reach),
                      key=lambda o: math.hypot(*o) - 0.6 * (o[0] * prefer[0] + o[1] * prefer[1]))
        for dx, dy in offs:
            t.SetPosition(pcbnew.VECTOR2I(mm(x + dx), mm(y + dy)))
            box = self.ink(t)
            if self.free(box):
                self.b.Add(t)
                self.boxes.append((box[0] - 0.15, box[1] - 0.15, box[2] + 0.15, box[3] + 0.15))
                return t
        if not must:
            return None
        t.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        self.b.Add(t)
        box = self.ink(t)
        self.boxes.append((box[0] - 0.15, box[1] - 0.15, box[2] + 0.15, box[3] + 0.15))
        self.forced.append(s)
        return t


def line(b, x1, y1, x2, y2, w=0.2):
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetLayer(pcbnew.F_SilkS)
    s.SetWidth(mm(w))
    s.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    s.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
    b.Add(s)


NET_LABELS = {"+24V_RAW": "+24V", "GND": "0V", "CHASSIS": "CHAS", "RS485_A": "A", "RS485_B": "B", "GND_RS485": "GND"}


def net_label(net):
    if net in NET_LABELS:
        return NET_LABELS[net]
    if net.startswith("RTD") and net[3:4].isdigit() and net[4:6] in ("_A", "_B", "_C"):
        return net[3] + net[5]          # PT100 n, wire A/B/C: "1A"
    for end, s in (("_COM", "C"), ("_NO", "NO"), ("_NC", "NC")):
        if net.endswith(end):
            return s
    raise SystemExit(f"silk: no terminal label for net {net}")


def pins(b, ref):
    fp = b.FindFootprintByReference(ref)
    return [(p.GetNumber(), T(p.GetPosition().x), T(p.GetPosition().y))
            for p in sorted(fp.Pads(), key=lambda p: int(p.GetNumber()))]


S = P.require("silk")
FUNC = S["functions"]
REFS_IF_ROOM = S["refs_if_room"]


def main():
    import subprocess, sys
    subprocess.run([sys.executable, os.path.abspath(__file__), "--strip-child"], check=True)
    b = pcbnew.LoadBoard(BOARD)
    for fp in b.GetFootprints():
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
    P = Placer(b)

    # fixed graphics first: barrier outline (functional isolation, not a safety rating),
    # broken where a part straddles it (the isolators are the barrier there)
    bodies = []
    for fp in b.GetFootprints():
        cy = fp.GetCourtyard(pcbnew.F_CrtYd)
        if not cy.OutlineCount():
            continue
        bb = cy.BBox()
        bodies.append((T(bb.GetLeft()) - 0.3, T(bb.GetTop()) - 0.3, T(bb.GetRight()) + 0.3, T(bb.GetBottom()) + 0.3))
    for x1, y1, x2, y2 in S["barriers"]:
        L = math.hypot(x2 - x1, y2 - y1)
        n = int(L / 0.1)
        run = None
        for i in range(n + 1):
            px, py = x1 + (x2 - x1) * i / n, y1 + (y2 - y1) * i / n
            hit = any(a <= px <= c and bq <= py <= d for a, bq, c, d in bodies)
            if not hit and run is None:
                run = (px, py)
            if (hit or i == n) and run is not None:
                if math.hypot(px - run[0], py - run[1]) > 0.5:
                    line(b, run[0], run[1], px, py, 0.25)
                    P.boxes.append((min(run[0], px) - 0.2, min(run[1], py) - 0.2, max(run[0], px) + 0.2, max(run[1], py) + 0.2))
                run = None
    # thermocouple terminals: "+  n  -" - the sign over each pin, the channel number between
    def chan(ref, num):
        return [int(p.GetNetname().split("TC")[1].rstrip("+-")) for p in b.FindFootprintByReference(ref).Pads()
                if p.GetNumber() == num][0]
    for ref in S["horizontal"]:
        ps = pins(b, ref)
        for (n1, x1, y), (n2, x2, _) in zip(ps[0::2], ps[1::2]):
            P.text("+", x1, S["horizontal_y"], 1.0, bold=True, prefer=(0, -1), reach=1.6)
            P.text("-", x2, S["horizontal_y"], 1.0, bold=True, prefer=(0, -1), reach=1.2)
            P.text(f"{chan(ref, n1)}", (x1 + x2) / 2, S["horizontal_y"], (0.6, 0.9), prefer=(0, -1), reach=1.4)
    for ref in S["vertical"]:
        ps = pins(b, ref)
        sx, nx = S.get("vertical_x", {}).get(ref, (S["vertical_sign_x"], S["vertical_number_x"]))
        for (n1, x, y1), (n2, _, y2) in zip(ps[0::2], ps[1::2]):
            P.text("+", sx, y1, 1.0, 90, bold=True, prefer=(0, 1), reach=1.6)
            P.text("-", sx, y2, 1.0, 90, bold=True, prefer=(0, 1), reach=1.6)
            P.text(f"{chan(ref, n1)}", nx, (y1 + y2) / 2, (0.6, 0.8), 90, reach=1.0)
    # J401: no room beside its two pins; the plug's pin 1 is the footprint's triangle
    fixed = S["fixed"][0]
    P.text(*fixed[:4], **fixed[4])
    fixed = S["fixed"][1]
    P.text(*fixed[:4], **fixed[4])
    fixed = S["fixed"][2]
    P.text(*fixed[:4], **fixed[4])

    # power, contacts, bus: function of every terminal, and a title
    # I-113: J601 pin 3 is CHASSIS (shield bar), not a cable shield pin; the run permit is C-NO
    for ref, names, title in S["terminals"]:
        ps = pins(b, ref)
        if S.get("label_by_net"):   # 8/40-ch: the label follows the pad's net, never the pin order
            nets = {p.GetNumber(): p.GetNetname().rsplit("/", 1)[-1] for p in b.FindFootprintByReference(ref).Pads()}
            names = [net_label(nets[num]) for num, x, y in ps]
        label_y, title_y = S.get("terminal_y_at", {}).get(ref, (S["terminal_y"], S["terminal_title_y"]))
        for (num, x, y), s_ in zip(ps, names):
            P.text(s_, x, label_y, 1.0, bold=True, prefer=(0, 1), reach=1.8)
        # title in the free space under the block (the relays sit right below C/NO/NC)
        size = (0.7, 0.9) if len(title) > 8 else 1.0
        P.text(title, ps[min(2, len(ps) - 1)][1], title_y, size, bold=True, prefer=(1, 1), reach=10)
    # RS-485: resistors sit under the pins, so one legend in pin order
    ps = pins(b, S["bus_ref"])
    P.text(S.get("bus_text", "RS-485:  A   B   GND"), ps[1][1], S["bus_y"], 0.9, reach=5, prefer=(0, 1))
    fixed = S["fixed"][3]
    P.text(*fixed[:4], **fixed[4])
    for ref, s in S["jumpers"]:
        fp = b.FindFootprintByReference(ref)
        P.text(s, T(fp.GetPosition().x), T(fp.GetPosition().y), (0.7, 0.8), reach=4.5)
    num, x, y = pins(b, S["lcd_ref"])[0]
    P.text("LCD 1", x - 3.0, y, 0.9, reach=2.5, prefer=(-1, 0))
    num, x, y = pins(b, S["buttons_ref"])[0]
    P.text("PANEL BTN 1 UP 2 DN 3 SET 4 ESC 5 ACK 6 0V", x, y + 3.0, (0.6, 0.8), reach=4, prefer=(0, 1), must=False)
    num, x, y = pins(b, S["isp_ref"])[0]
    P.text("ISP 1", x, y + S.get("isp_dy", 2.6), 0.8, reach=4, prefer=(0, 1))

    # buttons, LEDs, test points, contrast, fuse: function instead of reference
    for ref, s in FUNC.items():
        fp = b.FindFootprintByReference(ref)
        cy = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        x, y, top = T(fp.GetPosition().x), T(fp.GetPosition().y), T(cy.GetTop())
        if ref.startswith("TP"):   # touching its own point only: never between two points
            half = T(cy.GetWidth()) / 2
            w = 0.65 * 0.85 * len(s) / 2
            spots = ((x + half + w + 0.1, y, (1, 0)), (x - half - w - 0.1, y, (-1, 0)),
                     (x, y + half + 0.5, (0, 1)), (x, y - half - 0.5, (0, -1))) + tuple(
                ((x + sx * (half + w - 0.3), y + sy * (half + 0.3), (sx, sy)) for sy in (1, -1) for sx in (-1, 1)))
            if not any(P.text(s, sx, sy, (0.65, 0.8), reach=1.0, prefer=d, must=False) for sx, sy, d in spots):
                P.text(s, x + half + w + 0.1, y, (0.65, 0.8), reach=0.0)
            continue
        P.text(s, x, top - 0.7, 0.8 if ref.startswith("TP") else 1.0, prefer=(0, -1), reach=4.5)

    fixed = S["fixed"][4]
    P.text(*fixed[:4], **fixed[4])
    fixed = S["fixed"][5]
    P.text(*fixed[:4], **fixed[4])

    # references only where they fit near their part
    hidden = 0
    for fp in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
        r = fp.GetReference()
        if r in FUNC or not r.startswith(REFS_IF_ROOM) or r.startswith("JP"):
            continue
        cy = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        cx, top = T(fp.GetPosition().x), T(cy.GetTop())
        t = P.text(r, cx, top - 0.6, 0.8, reach=2.0, prefer=(0, -1), must=False)
        hidden += t is None
    pcbnew.SaveBoard(BOARD, b)
    print(f"silkscreen written; {hidden} optional references left off for lack of room")
    if P.forced:
        print("NOT FREE (placed anyway, check):", P.forced)


def strip():
    """Board-level silkscreen texts and lines all belong to this script."""
    b = pcbnew.LoadBoard(BOARD)
    old = [d for d in b.GetDrawings() if d.GetLayer() == pcbnew.F_SilkS]
    for d in old:
        b.Remove(d)
    pcbnew.SaveBoard(BOARD, b)


if __name__ == "__main__":
    import guard      # I-115: refuse while KiCad or another tool holds the board
    import sys
    if "--strip-child" in sys.argv:
        guard.check_parent(BOARD, 'silk.py')
        strip()
    else:
        with guard.claim(str(BOARD), "silk.py"):
            strip() if "--strip" in sys.argv else main()
