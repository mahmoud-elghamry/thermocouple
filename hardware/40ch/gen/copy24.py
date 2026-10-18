"""Copy the finished 24-ch board's signal copper onto the 40-ch board (2026-10-14).

The 40-ch places every shared part where the 24-ch has it (place.py from24 / bank_right), so the 24-ch's
routed signals fit under three transforms:
    same      24-ch refs as they are, 3xx -> 8xx           (x, y)            banks A, B, D, control
    shift     24-ch 2xx -> 3xx                             (x + 74, y)       bank C
    turn      24-ch 3xx -> 9xx                             (W - x, 126 - y)  bank E (bank D turned 180)
A net is copied only when every one of its 24-ch pads maps to a 40-ch pad of ONE 40-ch net at the transformed
position (0.02 mm); nets touching a part the 40-ch moved or lacks are left to the router. Plane-net copper
(fanout stubs and vias) is copied per pad: a plane track with an end on a 24-ch pad whose 40-ch pad sits at
the transformed position on the same plane net, the via at its other end, and vias inside such a pad (exposed
pads); run it on a board whose plane copper was stripped, then fanout.py for the pads still open. Copied items whose DRC fails are deleted afterwards
(`finish.py --board 40 drc` + `delviol.py`). The 24-ch board is only read.
Run with KiCad's python:  python copy24.py IN.kicad_pcb OUT.kicad_pcb
"""
import os
import sys
from collections import defaultdict

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(os.path.dirname(HERE)), "24ch", "thermo24.kicad_pcb")
W, YC2 = 250.0, 126.0
PLANES = {"GND_ISO", "+3V3_ISO", "GND", "+5V", "GND_RS485"}
T, M = pcbnew.ToMM, pcbnew.FromMM


def split(ref):
    pre = "".join(ch for ch in ref if ch.isalpha())
    num = ref[len(pre):]
    return pre, (int(num) if num.isdigit() else -1)


def same(ref):
    pre, n = split(ref)
    return f"{pre}{n + 500}" if 300 <= n < 400 else ref


def shift(ref):
    pre, n = split(ref)
    return f"{pre}{n + 100}" if 200 <= n < 300 else None


def turn(ref):
    pre, n = split(ref)
    return f"{pre}{n + 600}" if 300 <= n < 400 else None


TRANSFORMS = (("same", same, lambda x, y: (x, y)),
              ("shift", shift, lambda x, y: (x + 74.0, y)),
              ("turn", turn, lambda x, y: (W - x, YC2 - y)))


def short(net):
    return net.rsplit("/", 1)[-1]


def main(inp, out):
    src = pcbnew.LoadBoard(SRC)
    dst = pcbnew.LoadBoard(inp)
    pads40 = {}
    for fp in dst.GetFootprints():
        for p in fp.Pads():
            pads40[(fp.GetReference(), p.GetNumber())] = (T(p.GetPosition().x), T(p.GetPosition().y), p.GetNetname())
    nets40 = dst.GetNetsByName()
    pads24 = defaultdict(list)
    for fp in src.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname():
                pads24[p.GetNetname()].append((fp.GetReference(), p.GetNumber(), T(p.GetPosition().x), T(p.GetPosition().y)))
    tracks24 = defaultdict(list)
    for t in src.GetTracks():
        tracks24[t.GetNetname()].append(t)
    taken = set()          # 40-ch nets already filled by an earlier transform
    stats = defaultdict(int)
    for name, refmap, xy in TRANSFORMS:
        for net24, pads in pads24.items():
            if short(net24) in PLANES or not tracks24.get(net24):
                continue
            target = set()
            ok = True
            for ref, num, x, y in pads:
                r40 = refmap(ref)
                q = pads40.get((r40, num)) if r40 else None
                if q is None:
                    ok = False
                    break
                tx, ty = xy(x, y)
                if abs(tx - q[0]) > 0.02 or abs(ty - q[1]) > 0.02 or not q[2]:
                    ok = False
                    break
                target.add(q[2])
            if not ok or len(target) != 1:
                stats[name + " skipped"] += 1
                continue
            net40 = target.pop()
            if (net40, name) in taken or net40 not in nets40:
                continue
            taken.add((net40, name))
            for t in tracks24[net24]:
                if t.Type() == pcbnew.PCB_VIA_T:
                    v = pcbnew.PCB_VIA(dst)
                    x, y = xy(T(t.GetPosition().x), T(t.GetPosition().y))
                    v.SetPosition(pcbnew.VECTOR2I(M(x), M(y)))
                    v.SetWidth(t.GetWidth(pcbnew.F_Cu))
                    v.SetDrill(t.GetDrillValue())
                    v.SetNet(nets40[net40])
                    dst.Add(v)
                else:
                    n = pcbnew.PCB_TRACK(dst)
                    a = xy(T(t.GetStart().x), T(t.GetStart().y))
                    z = xy(T(t.GetEnd().x), T(t.GetEnd().y))
                    n.SetStart(pcbnew.VECTOR2I(M(a[0]), M(a[1])))
                    n.SetEnd(pcbnew.VECTOR2I(M(z[0]), M(z[1])))
                    n.SetWidth(t.GetWidth())
                    n.SetLayer(t.GetLayer())
                    n.SetNet(nets40[net40])
                    dst.Add(n)
                stats[name + " items"] += 1
            stats[name + " nets"] += 1
    planes(src, dst, pads40, nets40, stats)
    pcbnew.SaveBoard(out, dst)
    print("copy24:", dict(stats))


def planes(src, dst, pads40, nets40, stats):
    pads = [(fp.GetReference(), p) for fp in src.GetFootprints() for p in fp.Pads() if short(p.GetNetname()) in PLANES]
    vias = {}
    for t in src.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T and short(t.GetNetname()) in PLANES:
            vias[(t.GetPosition().x, t.GetPosition().y)] = t
    done = set()

    def add_via(v, xy, net):
        x, y = xy(T(v.GetPosition().x), T(v.GetPosition().y))
        if (round(x, 3), round(y, 3)) in done:
            return
        done.add((round(x, 3), round(y, 3)))
        n = pcbnew.PCB_VIA(dst)
        n.SetPosition(pcbnew.VECTOR2I(M(x), M(y)))
        n.SetWidth(v.GetWidth(pcbnew.F_Cu))
        n.SetDrill(v.GetDrillValue())
        n.SetNet(nets40[net])
        dst.Add(n)
        stats["plane vias"] += 1

    for name, refmap, xy in TRANSFORMS:
        ok = {}
        for ref, p in pads:
            r40 = refmap(ref)
            q = pads40.get((r40, p.GetNumber())) if r40 else None
            if q is None:
                continue
            tx, ty = xy(T(p.GetPosition().x), T(p.GetPosition().y))
            if abs(tx - q[0]) <= 0.02 and abs(ty - q[1]) <= 0.02 and short(q[2]) == short(p.GetNetname()):
                ok[id(p)] = q[2]
        live = [(p, ok[id(p)]) for _, p in pads if id(p) in ok]
        for t in src.GetTracks():
            if t.Type() == pcbnew.PCB_VIA_T:
                for p, net in live:
                    if p.GetNetCode() == t.GetNetCode() and p.HitTest(t.GetPosition()):
                        add_via(t, xy, net)
                        break
                continue
            if short(t.GetNetname()) not in PLANES:
                continue
            for p, net in live:
                if p.GetNetCode() != t.GetNetCode():
                    continue
                if p.HitTest(t.GetStart()) or p.HitTest(t.GetEnd()):
                    n = pcbnew.PCB_TRACK(dst)
                    a = xy(T(t.GetStart().x), T(t.GetStart().y))
                    z = xy(T(t.GetEnd().x), T(t.GetEnd().y))
                    n.SetStart(pcbnew.VECTOR2I(M(a[0]), M(a[1])))
                    n.SetEnd(pcbnew.VECTOR2I(M(z[0]), M(z[1])))
                    n.SetWidth(t.GetWidth())
                    n.SetLayer(t.GetLayer())
                    n.SetNet(nets40[net])
                    dst.Add(n)
                    stats["plane tracks"] += 1
                    for end in (t.GetStart(), t.GetEnd()):
                        v = vias.get((end.x, end.y))
                        if v is not None:
                            add_via(v, xy, net)
                    break


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]))
