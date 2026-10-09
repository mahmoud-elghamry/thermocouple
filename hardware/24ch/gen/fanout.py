"""Pre-route fanout: one via per SMD pad of a plane net, before Freerouting runs.

Planes: In1 = GND_ISO / GND / GND_RS485 (by domain), In2 = +3V3_ISO / +5V /
GND_RS485. Freerouting left ~110 of these pad-to-plane connections open in the
dense input strips, so they are made here deterministically: for each pad the
nearest free spot (via 0.6/0.3, 0.25 mm clearance to every other-net copper)
is searched around the pad and joined with a short 0.3 mm track.
Run with KiCad's python after rules.py --route-prep; idempotent per pad.
"""
import math
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rules import domain, BANDS  # noqa: E402

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.path.join(HW, "thermo24.kicad_pcb")
mm = pcbnew.FromMM
PLANE_NETS = {"GND_ISO", "GND", "GND_RS485", "+3V3_ISO", "+5V"}
VIA_D, VIA_DR, CLR, TRACK = 0.6, 0.3, 0.25, 0.3


def bare(n):
    return n.rsplit("/", 1)[-1]


def main():
    b = pcbnew.LoadBoard(BOARD)
    items = []          # (kind, obj, netcode) of copper to stay clear of
    for fp in b.GetFootprints():
        for p in fp.Pads():
            items.append(p)
    tracks = list(b.GetTracks())
    have = set()        # pads that already reach a via through a track
    for t in tracks:
        if t.Type() == pcbnew.PCB_VIA_T:
            have.add((t.GetNetCode(), t.GetPosition().x, t.GetPosition().y))
    added = skipped = 0
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            net = bare(pad.GetNetname())
            if net not in PLANE_NETS or pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            c = pad.GetPosition()
            if fp.GetReference() in ("U101", "U201", "U301"):
                continue
            if any(nc == pad.GetNetCode() and math.hypot(x - c.x, y - c.y) < mm(2.0)
                   for nc, x, y in have):
                continue
            spot = find_spot(b, pad, items, tracks)
            if spot is None:
                skipped += 1
                print("no spot for", fp.GetReference(), pad.GetNumber(), net)
                continue
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(spot)
            v.SetWidth(mm(VIA_D))
            v.SetDrill(mm(VIA_DR))
            v.SetNet(pad.GetNet())
            b.Add(v)
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(c)
            t.SetEnd(spot)
            t.SetWidth(mm(TRACK))
            t.SetLayer(pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu)
            t.SetNet(pad.GetNet())
            b.Add(t)
            tracks += [v, t]
            have.add((pad.GetNetCode(), spot.x, spot.y))
            added += 1
    for ref in ("U101", "U201", "U301"):
        added += lfcsp(b, ref, items, tracks)
    pcbnew.SaveBoard(BOARD, b)
    print(f"fanout: {added} vias added, {skipped} pads left to the LFCSP handler")


def via(b, pos, net):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pos)
    v.SetWidth(mm(VIA_D))
    v.SetDrill(mm(VIA_DR))
    v.SetNet(net)
    b.Add(v)
    return v


def track(b, a, z, net, w, layer=pcbnew.F_Cu):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(a)
    t.SetEnd(z)
    t.SetWidth(mm(w))
    t.SetLayer(layer)
    t.SetNet(net)
    b.Add(t)
    return t


def lfcsp(b, ref, items, tracks):
    """AD7124 LFCSP: 5 vias on the gap cross of the exposed pad's 4 paste windows
    (1.45 mm squares at +-0.9, I-110: a hole under paste wicks solder, no X-ray at
    NORI); AVSS/DGND/REFIN1- pins tied to the pad on F.Cu; AVDD/IOVDD escape
    straight out with 0.2 mm track. On the routed board some were dropped where a
    B.Cu track crosses the pad (U101: 2, U201: 2, U301: 4)."""
    fp = b.FindFootprintByReference(ref)
    pads = {p.GetNumber(): p for p in fp.Pads() if p.GetNumber()}
    ep = pads["33"]
    c = ep.GetPosition()
    if any(t.Type() == pcbnew.PCB_VIA_T and t.GetPosition() == c for t in tracks):
        return 0
    n = 0
    for dx, dy in ((0, 0), (0, -1.25), (0, 1.25), (-1.25, 0), (1.25, 0)):
        tracks.append(via(b, pcbnew.VECTOR2I(c.x + mm(dx), c.y + mm(dy)), ep.GetNet()))
        n += 1
    for num in ("3", "13", "23"):
        p = pads[num]
        q = p.GetPosition()
        dx, dy = q.x - c.x, q.y - c.y
        if abs(dx) > abs(dy):
            end = pcbnew.VECTOR2I(c.x + (mm(1.5) if dx > 0 else -mm(1.5)), q.y)
        else:
            end = pcbnew.VECTOR2I(q.x, c.y + (mm(1.5) if dy > 0 else -mm(1.5)))
        tracks.append(track(b, q, end, p.GetNet(), 0.25))
    for num in ("2", "26"):
        p = pads[num]
        q = p.GetPosition()
        dx, dy = q.x - c.x, q.y - c.y
        ux, uy = (1 if dx > 0 else -1, 0) if abs(dx) > abs(dy) else (0, 1 if dy > 0 else -1)
        for out in (1.5, 2.0, 2.6):
            pos = pcbnew.VECTOR2I(q.x + ux * mm(out), q.y + uy * mm(out))
            if clear_of(b, pos, p.GetNetCode(), items, tracks, None):
                tracks.append(via(b, pos, p.GetNet()))
                tracks.append(track(b, q, pos, p.GetNet(), 0.2))
                n += 1
                break
        else:
            print("LFCSP: no escape for", ref, num)
    return n


CONTACT = {"TRIP_COM", "TRIP_NO", "TRIP_NC", "TRIP_MID", "ALM_COM", "ALM_NO", "ALM_NC", "CHASSIS"}


def clear_of(b, pos, net, items, tracks, track_from):
    r = mm(VIA_D / 2 + CLR)
    for p in items:
        if p.GetNetCode() == net:
            continue
        extra = mm(1.8) if bare(p.GetNetname()) in CONTACT else 0
        if p.HitTest(pos, r + extra):
            return False
        if track_from is not None and segment_hits(p, track_from, pos):
            return False
    for t in tracks:
        if t.GetNetCode() == net:
            continue
        if t.HitTest(pos, r + mm(TRACK / 2)):
            return False
    return True


def segment_hits(pad, a, z):
    """Does a TRACK-wide segment a->z come within CLR of the pad? (sampled)"""
    acc = mm(TRACK / 2 + CLR)
    for k in range(1, 6):
        x = a.x + (z.x - a.x) * k / 6
        y = a.y + (z.y - a.y) * k / 6
        if pad.HitTest(pcbnew.VECTOR2I(int(x), int(y)), acc):
            return True
    return False


def near_band(x, y, m):
    for band in BANDS:
        xs = [p[0] for p in band]
        ys = [p[1] for p in band]
        if min(xs) - m < x < max(xs) + m and min(ys) - m < y < max(ys) + m:
            return True
    return False


def find_spot(b, pad, items, tracks):
    c = pad.GetPosition()
    fpc = pad.GetParentFootprint().GetPosition()
    base = math.atan2(c.y - fpc.y, c.x - fpc.x) if (c.x, c.y) != (fpc.x, fpc.y) else 0.0
    sz = pad.GetSize()
    half = max(sz.x, sz.y) / 2
    dom = domain(pcbnew.ToMM(c.x), pcbnew.ToMM(c.y))
    for dist in (half + mm(0.55), half + mm(0.9), half + mm(1.3), half + mm(1.8), half + mm(2.4)):
        for k in range(24):
            ang = base + (k // 2 + 1) // 1 * (1 if k % 2 else -1) * math.pi / 12 if k else base
            pos = pcbnew.VECTOR2I(int(c.x + dist * math.cos(ang)), int(c.y + dist * math.sin(ang)))
            x, y = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
            if not (1.0 < x < 169.0 and 1.0 < y < 144.0):
                continue
            if domain(x, y) != dom or near_band(x, y, 0.65):
                continue
            if clear_of(b, pos, pad.GetNetCode(), items, tracks, c):
                return pos
    return None


if __name__ == "__main__":
    main()
