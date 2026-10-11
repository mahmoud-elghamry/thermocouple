"""Find a spot for a decoupling capacitor beside its IC pin (I-111, `0034` D3).

For one (IC, pin, cap) it tries cap positions on a 0.1 mm grid in the four
orientations, keeps those whose pad on the pin's net is within LIMIT of the pin,
and scores each by what it would collide with: other footprints' courtyards,
other-net pads, other-net tracks and vias (clearance 0.21 mm + half the track
width), barrier bands and the board edge. Read-only unless --apply.
Run with KiCad's python:
    python capnear.py U403 1 C407 [--limit 2.6] [--apply] [--show N] [--soft-vias] [--rip] [--avoid NET,NET] [--step 0.1]
--apply moves the cap to the best spot with no collisions (else lists the best
spots and the tracks in the way, and changes nothing). Re-route afterwards with
`finish.py dangling`, `maze.py`; `pincaps.py` is the gate.
    python capnear.py via REF PAD       # a plane via beside a pad the pour cannot reach
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from rules import domain, BANDS  # noqa: E402

HW = os.path.dirname(HERE)
BOARD = os.environ.get("THERMO24_BOARD", os.path.join(HW, "thermo24.kicad_pcb"))
T, mm = pcbnew.ToMM, pcbnew.FromMM
CLR = 0.21
STEP = float(sys.argv[sys.argv.index("--step") + 1]) if "--step" in sys.argv else 0.1
SOFT_VIAS = "--soft-vias" in sys.argv     # count vias in the way instead of refusing the spot


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


def candidates(b, ic, pin, cap, limit):
    icp = next(p for p in b.FindFootprintByReference(ic).Pads() if p.GetNumber() == pin)
    px, py = T(icp.GetPosition().x), T(icp.GetPosition().y)
    net = icp.GetNetCode()
    fp = b.FindFootprintByReference(cap)
    cnet = {p.GetNumber(): p.GetNetCode() for p in fp.Pads()}
    key = next(n for n, c in cnet.items() if c == net)
    dom = domain(px, py)
    old = (fp.GetPosition(), fp.GetOrientationDegrees())
    others = [f for f in b.GetFootprints() if f.GetReference() != cap]
    crts = [(f.GetReference(), rect(f.GetCourtyard(pcbnew.F_CrtYd).BBox()))
            for f in others if f.GetCourtyard(pcbnew.F_CrtYd).OutlineCount()]
    box = (px - limit - 6, py - limit - 6, px + limit + 6, py + limit + 6)
    pads = [(f.GetReference(), p.GetNetCode(), rect(p.GetBoundingBox())) for f in others for p in f.Pads()
            if overlap(rect(p.GetBoundingBox()), box)]
    tracks = []
    tht = any(p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH for p in fp.Pads())
    for t in b.GetTracks():
        if not overlap(rect(t.GetBoundingBox()), box):
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            q = t.GetPosition()
            tracks.append((t, T(q.x), T(q.y), T(q.x), T(q.y), T(t.GetWidth(pcbnew.F_Cu)) / 2, True))
        elif t.GetLayer() == pcbnew.F_Cu or tht:      # a through-hole part meets every layer
            tracks.append((t, T(t.GetStart().x), T(t.GetStart().y), T(t.GetEnd().x), T(t.GetEnd().y),
                           T(t.GetWidth()) / 2, False))
    out = []
    step = STEP
    nstep = int(limit / step) + 3
    for rot in (0, 90, 180, 270):
        for i in range(-nstep, nstep + 1):
            for j in range(-nstep, nstep + 1):
                x, y = px + i * step, py + j * step
                fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
                fp.SetOrientationDegrees(rot)
                kp = next(p for p in fp.Pads() if p.GetNumber() == key)
                d = math.hypot(T(kp.GetPosition().x) - px, T(kp.GetPosition().y) - py)
                if d > limit:
                    continue
                c = rect(fp.GetCourtyard(pcbnew.F_CrtYd).BBox())
                if c[0] < 0.5 or c[1] < 0.5 or c[2] > 169.5 or c[3] > 144.5:
                    continue
                if any(domain(cx, cy) != dom for cx, cy in ((c[0], c[1]), (c[2], c[3]), (c[0], c[3]), (c[2], c[1]))):
                    continue
                hits = [r for r, cr in crts if overlap(c, cr)]
                if hits:
                    continue
                block = set()
                bad = False
                for p in fp.Pads():
                    pr = rect(p.GetBoundingBox())
                    for r, n, q in pads:
                        if n != p.GetNetCode() and overlap(pr, (q[0] - CLR, q[1] - CLR, q[2] + CLR, q[3] + CLR)):
                            bad = True
                    for k, (t, x1, y1, x2, y2, hw, isvia) in enumerate(tracks):
                        if t.GetNetCode() == p.GetNetCode():
                            continue
                        clr = 1.5 if t.GetNetname() == "CHASSIS" else CLR
                        if seg_rect_dist(x1, y1, x2, y2, pr) < clr + hw:
                            if isvia and not SOFT_VIAS:
                                bad = True
                            block.add(k)
                if not bad:
                    out.append((len(block), round(d, 2), x, y, rot, [tracks[k][0] for k in sorted(block)]))
    fp.SetPosition(old[0])
    fp.SetOrientationDegrees(old[1])
    out.sort(key=lambda o: (o[0], o[1]))
    return out


def main():
    a = sys.argv[1:]
    if a[:1] == ["via"]:
        return via_near(a[1], a[2], float(a[3]) if len(a) > 3 else 2.0)
    if len(a) < 3:
        raise SystemExit(__doc__)
    ic, pin, cap = a[:3]
    limit = float(a[a.index("--limit") + 1]) if "--limit" in a else 2.6
    show = int(a[a.index("--show") + 1]) if "--show" in a else 5
    b = pcbnew.LoadBoard(BOARD)
    out = candidates(b, ic, pin, cap, limit)
    if "--avoid" in a:               # nets that must not be ripped (e.g. XTAL1: crystal traces stay short)
        avoid = set(a[a.index("--avoid") + 1].split(","))
        def hit(n):
            return n in avoid or any(a.endswith("*") and n.startswith(a[:-1]) for a in avoid)
        out = [o for o in out if not any(hit(t.GetNetname().rsplit("/", 1)[-1]) for t in o[5])]
    if not out:
        print(f"capnear {ic}.{pin} {cap}: no spot within {limit} mm (courtyards/pads/vias/domain)")
        sys.exit(2)
    for n, d, x, y, rot, block in out[:show]:
        names = sorted({t.GetNetname().rsplit('/', 1)[-1] for t in block})
        print(f"  {cap} at ({x:.2f}, {y:.2f}) rot {rot}: pad {d} mm from {ic}.{pin}; tracks in the way {n} {names}")
    if "--apply" in a:
        n, d, x, y, rot, block = out[0]
        if n and "--rip" not in a:
            print("capnear: best spot still has tracks in the way - not applied (--rip deletes them)")
            sys.exit(3)
        fp = b.FindFootprintByReference(cap)
        own = {p.GetNetCode() for p in fp.Pads()}
        keep_nets = {"GND", "+5V", "GND_ISO", "+3V3_ISO", "CHASSIS"}   # plane stubs of other parts: never ripped
        for t in block:
            nm = t.GetNetname().rsplit("/", 1)[-1]
            if nm in keep_nets and t.GetNetCode() not in own:
                old_owner = [f.GetReference() for f in b.GetFootprints() for p in f.Pads()
                             if p.GetNetCode() == t.GetNetCode() and (p.HitTest(t.GetStart(), 0) or p.HitTest(t.GetEnd(), 0))]
                if old_owner:
                    raise SystemExit(f"capnear: a {nm} track of {old_owner} is in the way - move that first")
        for t in block:
            b.Remove(t)
        if block:
            print(f"capnear: ripped {len(block)} tracks/vias in the way (re-route with maze.py)")
        gone = [t for t in b.GetTracks()          # only the pad's own net: another net may end under it
                if any(t.GetNetCode() == p.GetNetCode() and (
                       p.HitTest(t.GetPosition() if t.Type() == pcbnew.PCB_VIA_T else t.GetStart(), 0)
                       or (t.Type() != pcbnew.PCB_VIA_T and p.HitTest(t.GetEnd(), 0))) for p in fp.Pads())]
        fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        fp.SetOrientationDegrees(rot)
        for t in gone:
            b.Remove(t)
        direct = straight(b, ic, pin, fp)
        pcbnew.SaveBoard(BOARD, b)
        print(f"capnear: moved {cap} to ({x:.2f}, {y:.2f}) rot {rot}, removed {len(gone)} of its old tracks; "
              f"direct pin track: {'drawn' if direct else 'not clear - leave to maze.py'}")


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


if __name__ == "__main__":
    import guard      # I-115: refuse while KiCad or another tool holds the board
    with guard.claim(str(BOARD), "capnear.py"):
        main()
