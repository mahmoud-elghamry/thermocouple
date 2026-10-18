"""Copied algorithms; constants come from the entry tool and its profile."""
from capnear import *

def rect(bb, grow=0.0):
    return (T(bb.GetLeft()) - grow, T(bb.GetTop()) - grow, T(bb.GetRight()) + grow, T(bb.GetBottom()) + grow)


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _pt_seg(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L = dx * dx + dy * dy
    u = 0.0 if L == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L))
    return math.hypot(px - x1 - u * dx, py - y1 - u * dy)


def _cross(a, b, c, d):
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return o(a, b, c) * o(a, b, d) < 0 and o(c, d, a) * o(c, d, b) < 0


def _seg_seg(ax, ay, bx, by, cx, cy, dx, dy):
    if _cross((ax, ay), (bx, by), (cx, cy), (dx, dy)):
        return 0.0
    return min(_pt_seg(ax, ay, cx, cy, dx, dy), _pt_seg(bx, by, cx, cy, dx, dy),
               _pt_seg(cx, cy, ax, ay, bx, by), _pt_seg(dx, dy, ax, ay, bx, by))


def seg_rect_dist(x1, y1, x2, y2, r):
    """Exact distance from a segment to an axis-aligned rectangle (0 if they touch)."""
    if any(r[0] <= x <= r[2] and r[1] <= y <= r[3] for x, y in ((x1, y1), (x2, y2))):
        return 0.0
    cs = [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]
    if any(_cross((x1, y1), (x2, y2), cs[i], cs[(i + 1) % 4]) for i in range(4)):
        return 0.0
    d = min(_pt_seg(cx, cy, x1, y1, x2, y2) for cx, cy in cs)
    for x, y in ((x1, y1), (x2, y2)):
        d = min(d, math.hypot(max(r[0] - x, 0, x - r[2]), max(r[1] - y, 0, y - r[3])))
    return d


def straight(b, ic, pin, fp, w=0.3):
    """Draw pin -> cap pad as one straight track when no other-net copper is within clearance."""
    icp = next(p for p in b.FindFootprintByReference(ic).Pads() if p.GetNumber() == pin)
    cp = next(p for p in fp.Pads() if p.GetNetCode() == icp.GetNetCode())
    a, z = icp.GetPosition(), cp.GetPosition()
    x1, y1, x2, y2 = T(a.x), T(a.y), T(z.x), T(z.y)
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetCode() != icp.GetNetCode() and seg_rect_dist(x1, y1, x2, y2, rect(p.GetBoundingBox())) < CLR + w / 2:
                return False
    for t in b.GetTracks():
        if t.GetNetCode() == icp.GetNetCode() or not (t.Type() == pcbnew.PCB_VIA_T or t.GetLayer() == pcbnew.F_Cu):
            continue
        if seg_rect_dist(x1, y1, x2, y2, rect(t.GetBoundingBox())) < CLR + w / 2:
            return False
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(a)
    t.SetEnd(z)
    t.SetWidth(mm(w))
    t.SetLayer(pcbnew.F_Cu)
    t.SetNet(icp.GetNet())
    b.Add(t)
    return True


def via_near(ref, num, rmax=2.0):
    """Plane via next to a pad: nearest spot (0.1 mm grid) clear of other-net copper on
    every layer, joined to the pad by a 0.3 mm track that is also clear. Saves the board."""
    b = pcbnew.LoadBoard(BOARD)
    pd = next(p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num)
    cx, cy, code = T(pd.GetPosition().x), T(pd.GetPosition().y), pd.GetNetCode()
    obs = []
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetCode() != code:
                obs.append((rect(p.GetBoundingBox()), 0.0, p.GetLayerSet().Contains(pcbnew.F_Cu)))
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                obs.append((rect(p.GetBoundingBox()), 0.05, True))
    box = (cx - rmax - 3, cy - rmax - 3, cx + rmax + 3, cy + rmax + 3)
    own = rect(pd.GetBoundingBox(), 0.15)
    dom = domain(cx, cy)
    obs = [o for o in obs if overlap(o[0], box)]
    segs = [(T(t.GetStart().x), T(t.GetStart().y), T(t.GetEnd().x), T(t.GetEnd().y), T(t.GetWidth(pcbnew.F_Cu) if t.Type() == pcbnew.PCB_VIA_T else t.GetWidth()) / 2,
             t.Type() == pcbnew.PCB_VIA_T or t.GetLayer() == pcbnew.F_Cu)
            for t in b.GetTracks() if t.GetNetCode() != code and overlap(rect(t.GetBoundingBox()), box)]
    best = None
    k = int(rmax / 0.1) + 1
    for i in range(-k, k + 1):
        for j in range(-k, k + 1):
            x, y = cx + i * 0.1, cy + j * 0.1
            d = math.hypot(x - cx, y - cy)
            if d > rmax or (best and d >= best[0]):
                continue
            vr = (x - 0.3, y - 0.3, x + 0.3, y + 0.3)
            if any(domain(vx, vy) != dom for vx, vy in ((vr[0], vr[1]), (vr[2], vr[3]), (vr[0], vr[3]), (vr[2], vr[1]))):
                continue                  # never in a barrier band or another domain
            if overlap(vr, own):          # never a via in the pad (solder wicks down the hole)
                continue
            if any(seg_rect_dist(*s[:4], vr) < CLR + s[4] for s in segs):
                continue
            if any(overlap(vr, (r[0] - CLR - e, r[1] - CLR - e, r[2] + CLR + e, r[3] + CLR + e)) for r, e, _ in obs):
                continue
            if any(seg_rect_dist(cx, cy, x, y, r) < CLR + 0.15 for r, e, top in obs if top) or any(
                    s[5] and _seg_seg(cx, cy, x, y, *s[:4]) < CLR + 0.15 + s[4] for s in segs):
                continue
            best = (d, x, y)
    if not best:
        raise SystemExit(f"via_near {ref}.{num}: no clear spot within {rmax} mm")
    _, x, y = best
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pd.GetPosition())
    t.SetEnd(pcbnew.VECTOR2I(mm(x), mm(y)))
    t.SetWidth(mm(0.3))
    t.SetLayer(pcbnew.F_Cu)
    t.SetNet(pd.GetNet())
    b.Add(t)
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    v.SetWidth(mm(0.6))
    v.SetDrill(mm(0.3))
    v.SetNet(pd.GetNet())
    b.Add(v)
    pcbnew.SaveBoard(BOARD, b)
    print(f"via_near: {ref}.{num} -> via at ({x:.2f}, {y:.2f}), {best[0]:.2f} mm")


