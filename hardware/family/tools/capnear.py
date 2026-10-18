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

from profiles import ACTIVE as P, ROOT
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from profiles import geometry
domain, BANDS = geometry()  # noqa: E402

HW = str(P["work_folder"])
BOARD = str(P["pcb"])
T, mm = pcbnew.ToMM, pcbnew.FromMM
CLR = 0.21
STEP = float(sys.argv[sys.argv.index("--step") + 1]) if "--step" in sys.argv else 0.1
SOFT_VIAS = "--soft-vias" in sys.argv     # count vias in the way instead of refusing the spot

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
                if c[0] < 0.5 or c[1] < 0.5 or c[2] > P.require("width") - 0.5 or c[3] > P.require("height") - 0.5:
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
                        clr = 1.5 if t.GetNetname() == P.require("chassis_net") else CLR
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
        keep_nets = set(P.require("plane_domains")) | {P.require("chassis_net")}   # plane stubs of other parts: never ripped
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

# Helpers import the entry module constants; preserve one context when run as a script.
import sys
if __name__ == "__main__":
    sys.modules["capnear"] = sys.modules[__name__]
from capnear_ops import rect, overlap, _pt_seg, _cross, _seg_seg, seg_rect_dist, straight, via_near

if __name__ == "__main__":
    import guard      # I-115: refuse while KiCad or another tool holds the board
    with guard.claim(str(BOARD), "capnear.py"):
        main()
