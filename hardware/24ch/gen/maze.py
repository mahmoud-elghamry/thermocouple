"""Grid maze router for the last few connections the autorouter left open.

Incremental: never moves a footprint or touches existing copper; it only adds
tracks (and vias) for connections KiCad DRC reports unconnected. Clearances are
deliberately conservative: 0.2 mm everywhere (NORI pad-to-track minimum),
2 mm contact-to-rest, 1.5 mm chassis-to-rest, and a route never leaves the
domain (island / control / RS-485 pocket) it starts in, nor enters a barrier
band. Plane nets (GND_ISO, +3V3_ISO, GND, +5V) may end on a new via instead of
reaching the other item. Run with KiCad's python, after `finish.py drc`:
    python maze.py            # route every unconnected item in output/finish-drc.json
    python maze.py --dry-run  # print the plan only
    python maze.py --ripup [--skip ...]  # list signal tracks in the way -> output/maze-rip.txt;
                                         # then `finish.py rip`, then a normal run
    python maze.py --skip NET [NET ...]   # leave these for hand routing (e.g. a decoupling loop
                                          # the maze would make 40 mm long)
"""
import heapq
import json
import math
import os
import sys

import numpy as np
import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rules import domain, BANDS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
BOARD = os.environ.get("THERMO24_BOARD", os.path.join(HW, "thermo24.kicad_pcb"))   # a copy while KiCad holds the board
REPORT = os.path.join(HW, "output", "finish-drc.json")
RES = 0.05                     # grid step, mm
W, H = 170.0, 145.0
NX, NY = int(W / RES), int(H / RES)
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)
VIA_D, VIA_DR, VIA_COST = 0.6, 0.3, 40
CONTACT = {"TRIP_COM", "TRIP_NO", "TRIP_NC", "TRIP_MID", "ALM_COM", "ALM_NO", "ALM_NC"}
PLANE = {"GND_ISO": "ISLAND", "+3V3_ISO": "ISLAND", "GND": "CONTROL", "+5V": "CONTROL"}
mm = pcbnew.FromMM


def bare(n):
    return n.rsplit("/", 1)[-1]


def need(a, b, b_is_pad, b_ref):
    """Clearance in mm between the routed net a and copper of net b (conservative)."""
    if a in CONTACT and b in CONTACT:
        return 1.0                       # contact to contact (30 VDC)
    if (a in CONTACT) != (b in CONTACT):
        return 2.0                       # contact_to_rest, relay coil pins included
    if "CHASSIS" in (a, b):
        return 1.5
    if {a, b} & {"+24V_RAW", "+24V_FUSED", "+24V_PROT", "RS485_A", "RS485_B"}:
        return 0.27
    if b_is_pad or {a, b} & set(PLANE) or a == "" or b == "":
        return 0.21                      # NORI pad-to-track 0.20; power classes 0.20
    return 0.16                          # signal track/via to track: class 0.15


def width_of(net):
    if net in CONTACT:
        return 0.8
    if net in PLANE:
        return 0.25
    return 0.2


def grid_xy(x, y):
    return int(round(x / RES)), int(round(y / RES))


def raster(poly_set, mask):
    """OR the polygons of a SHAPE_POLY_SET into mask (even-odd fill per outline)."""
    for i in range(poly_set.OutlineCount()):
        ol = poly_set.Outline(i)
        pts = np.array([(pcbnew.ToMM(ol.CPoint(k).x), pcbnew.ToMM(ol.CPoint(k).y))
                        for k in range(ol.PointCount())])
        if len(pts) < 3:
            continue
        x0, y0 = np.floor(pts.min(0) / RES).astype(int)
        x1, y1 = np.ceil(pts.max(0) / RES).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, NX - 1), min(y1, NY - 1)
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) * RES, np.arange(y0, y1 + 1) * RES)
        inside = np.zeros(gx.shape, bool)
        xs, ys = pts[:, 0], pts[:, 1]
        xj, yj = np.roll(xs, 1), np.roll(ys, 1)
        for k in range(len(xs)):
            c = ((ys[k] > gy) != (yj[k] > gy)) & \
                (gx < (xj[k] - xs[k]) * (gy - ys[k]) / (yj[k] - ys[k] + 1e-12) + xs[k])
            inside ^= c
        mask[y0:y1 + 1, x0:x1 + 1] |= inside


def shape(item, layer, extra_mm):
    ps = pcbnew.SHAPE_POLY_SET()
    item.TransformShapeToPolygon(ps, layer, mm(extra_mm), mm(0.005), pcbnew.ERROR_OUTSIDE)
    return ps


def items_on(b, layer):
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.IsOnLayer(layer):
                yield p, True, fp.GetReference()
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            yield t, True, ""
        elif t.GetLayer() == layer:
            yield t, False, ""


_CACHE = {}


def obstacles(b, net, net_code, w):
    """Blocked grid per layer for a track of width w on `net` (own-net copper excluded).

    Clearances depend only on the routed net's category, so the other-net
    raster is cached per (category, width) and own-net copper is cut back out."""
    cat = "contact" if net in CONTACT else "chassis" if net == "CHASSIS" else "std"
    key = (cat, w)
    if key not in _CACHE:
        _CACHE[key] = _obstacles_all(b, net, w)
    masks = []
    for li, layer in enumerate(LAYERS):
        m = _CACHE[key][li].copy()
        own = np.zeros((NY, NX), bool)
        for it, is_pad, ref in items_on(b, layer):
            if it.GetNetCode() == net_code:
                raster(shape(it, layer, 0.0), own)
        masks.append(_recompute_without(b, layer, net, net_code, w, m, own))
    return masks


def _recompute_without(b, layer, net, net_code, w, cached, own):
    """Cached mask includes this net's own copper inflated; rebuild only around it."""
    ys, xs = np.nonzero(own)
    if len(xs) == 0:
        return cached
    m = cached.copy()
    pad = int((2.5 + w) / RES)
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad, NX - 1)
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad, NY - 1)
    if (x1 - x0) * (y1 - y0) > 4_000_000:      # net spans the board: full rebuild
        full = np.zeros((NY, NX), bool)
        for it, is_pad, ref in items_on(b, layer):
            if it.GetNetCode() == net_code:
                continue
            raster(shape(it, layer, need(net, bare(it.GetNetname()), is_pad, ref) + w / 2), full)
        return full
    sub = np.zeros((NY, NX), bool)
    box = pcbnew.BOX2I(pcbnew.VECTOR2I(mm(float(x0 * RES)), mm(float(y0 * RES))),
                       pcbnew.VECTOR2L(mm(float((x1 - x0) * RES)), mm(float((y1 - y0) * RES))))
    for it, is_pad, ref in items_on(b, layer):
        if it.GetNetCode() == net_code or not it.GetBoundingBox().Intersects(box):
            continue
        raster(shape(it, layer, need(net, bare(it.GetNetname()), is_pad, ref) + w / 2), sub)
    m[y0:y1 + 1, x0:x1 + 1] = sub[y0:y1 + 1, x0:x1 + 1]
    return m


def _obstacles_all(b, net, w):
    masks = []
    for layer in LAYERS:
        m = np.zeros((NY, NX), bool)
        for it, is_pad, ref in items_on(b, layer):
            r = need(net, bare(it.GetNetname()), is_pad, ref) + w / 2
            raster(shape(it, layer, r), m)
        masks.append(m)
    return masks


def domain_mask(dom, margin):
    ys, xs = np.mgrid[0:NY, 0:NX] * RES
    ok = np.zeros((NY, NX), bool)
    # coarse: evaluate domain on a 0.5 mm lattice and expand
    step = 10
    for gy in range(0, NY, step):
        for gx in range(0, NX, step):
            x, y = gx * RES, gy * RES
            ok[gy:gy + step, gx:gx + step] = domain(x + RES * step / 2, y + RES * step / 2) == dom
    for band in BANDS:
        bx = [p[0] for p in band]
        by = [p[1] for p in band]
        ok &= ~((xs > min(bx) - margin) & (xs < max(bx) + margin) &
                (ys > min(by) - margin) & (ys < max(by) + margin))
    ok &= (xs > 0.6) & (xs < W - 0.6) & (ys > 0.6) & (ys < H - 0.6)
    return ok


def find_item(b, desc, pos):
    """The pad or track the DRC report names at pos (matched by net, since tracks overlap)."""
    x, y = mm(pos["x"]), mm(pos["y"])
    p = pcbnew.VECTOR2I(x, y)
    net = desc.split("[", 1)[1].split("]", 1)[0] if "[" in desc else ""
    if "ad" in desc.split(" [")[0].lower():         # Pad / PTH pad
        for fp in b.GetFootprints():
            for pad in fp.Pads():
                if pad.GetNetname() == net and pad.HitTest(p, mm(0.01)):
                    return pad
    for t in b.GetTracks():
        if t.GetNetname() == net and t.HitTest(p, mm(0.01)):
            return t
    return None


def item_cells(item, layer_idx):
    m = np.zeros((NY, NX), bool)
    raster(shape(item, LAYERS[layer_idx], 0.0), m)
    return m


def astar(blocked, starts, goals, via_ok, via_goal, soft=None, penalty=0.0):
    """starts/goals: list of (layer, gx, gy). via_goal: a via site anywhere ends the route."""
    goal_set = set(goals)
    dist = {}
    heap = []
    tx = np.mean([g[1] for g in goals]) if goals else None
    ty = np.mean([g[2] for g in goals]) if goals else None

    def h(gx, gy):
        if tx is None:
            return 0
        return math.hypot(gx - tx, gy - ty)
    for s in starts:
        dist[s] = 0
        heapq.heappush(heap, (h(s[1], s[2]), 0, s, None))
    prev = {}
    moves = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1),
             (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
    n = 0
    while heap:
        f, g, cur, par = heapq.heappop(heap)
        if cur in prev:
            continue
        prev[cur] = par
        n += 1
        if n > 4_000_000:
            return None
        L, gx, gy = cur
        if cur in goal_set or (via_goal and via_ok[gy, gx]):
            path = [cur]
            while prev[path[-1]] is not None:
                path.append(prev[path[-1]])
            return path[::-1], (via_goal and cur not in goal_set)
        for dx, dy, c in moves:
            nx, ny = gx + dx, gy + dy
            if not (0 <= nx < NX and 0 <= ny < NY) or blocked[L][ny, nx]:
                continue
            if dx and dy and (blocked[L][gy, nx] or blocked[L][ny, gx]):
                continue
            nxt = (L, nx, ny)
            ng = g + c + (penalty if soft is not None and soft[L][ny, nx] else 0.0)
            if ng < dist.get(nxt, 1e18):
                dist[nxt] = ng
                heapq.heappush(heap, (ng + h(nx, ny), ng, nxt, cur))
        if via_ok[gy, gx]:
            nxt = (1 - L, gx, gy)
            ng = g + VIA_COST
            if ng < dist.get(nxt, 1e18):
                dist[nxt] = ng
                heapq.heappush(heap, (ng + h(gx, gy), ng, nxt, cur))
    return None


def simplify(path):
    """Collapse grid steps into straight segments; returns [(layer, [(x,y),...])] and via points."""
    runs, vias = [], []
    cur_layer, pts, last_dir = path[0][0], [path[0][1:]], None
    for a, z in zip(path, path[1:]):
        if z[0] != a[0]:
            pts.append(a[1:])
            runs.append((cur_layer, pts))
            vias.append(a[1:])
            cur_layer, pts, last_dir = z[0], [z[1:]], None
            continue
        d = (z[1] - a[1], z[2] - a[2])
        if d != last_dir and last_dir is not None:
            pts.append(a[1:])
        last_dir = d
    pts.append(path[-1][1:])
    runs.append((cur_layer, pts))
    return runs, vias


def via_sites(free, w):
    """Cells where a via fits: every cell under the via ring (plus margin) is free."""
    grow = int(math.ceil((VIA_D / 2 - w / 2 + 0.02) / RES))
    ok = free.copy()
    for dy in range(-grow, grow + 1):
        for dx in range(-grow, grow + 1):
            if dx * dx + dy * dy > grow * grow or (dx == 0 and dy == 0):
                continue
            sh = np.zeros_like(free)
            sh[max(dy, 0):NY + min(dy, 0), max(dx, 0):NX + min(dx, 0)] =                 free[max(-dy, 0):NY + min(-dy, 0), max(-dx, 0):NX + min(-dx, 0)]
            ok &= sh
    return ok


def route_one(b, item_a, item_b, net, dry):
    nc = item_a.GetNetCode()
    w = width_of(net)
    start_xy = item_a.GetPosition() if hasattr(item_a, "GetNumber") else item_a.GetStart()
    dom = domain(pcbnew.ToMM(start_xy.x), pcbnew.ToMM(start_xy.y))
    blocked = obstacles(b, net, nc, w)
    dm = domain_mask(dom, w / 2 + 0.05)
    blocked = [m | ~dm for m in blocked]
    via_ok = via_sites(~(blocked[0] | blocked[1]), w)
    starts, goals = [], []
    for li in range(2):
        for item, out in ((item_a, starts), (item_b, goals)):
            if item is None or not item.IsOnLayer(LAYERS[li]):
                continue
            cells = item_cells(item, li)
            ys, xs = np.nonzero(cells)
            for gy, gx in zip(ys, xs):
                blocked[li][gy, gx] = False
                out.append((li, gx, gy))
    via_goal = net in PLANE and PLANE[net] == dom
    res = astar(blocked, starts, goals, via_ok, via_goal)
    if res is None:
        print(f"  NO PATH for {net}")
        return False
    path, end_via = res
    runs, vias = simplify(path)
    if end_via:
        vias.append(path[-1][1:])
    length = sum(math.hypot(p[0] - q[0], p[1] - q[1]) * RES for _, pts in runs for p, q in zip(pts, pts[1:]))
    print(f"  {net}: {len(runs)} runs, {len(vias)} vias, {length:.1f} mm")
    if dry:
        return True
    netinfo = item_a.GetNet()
    for li, pts in runs:
        for p, q in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(mm(float(p[0] * RES)), mm(float(p[1] * RES))))
            t.SetEnd(pcbnew.VECTOR2I(mm(float(q[0] * RES)), mm(float(q[1] * RES))))
            t.SetWidth(mm(w))
            t.SetLayer(LAYERS[li])
            t.SetNet(netinfo)
            b.Add(t)
    for v in vias:
        via = pcbnew.PCB_VIA(b)
        via.SetPosition(pcbnew.VECTOR2I(mm(float(v[0] * RES)), mm(float(v[1] * RES))))
        via.SetWidth(mm(VIA_D))
        via.SetDrill(mm(VIA_DR))
        via.SetNet(netinfo)
        b.Add(via)
    return True


RIP_FILE = os.path.join(HW, "output", "maze-rip.txt")
FIRST_FILE = os.path.join(HW, "output", "maze-first.txt")   # nets a rip-up was made for
KEEP = CONTACT | set(PLANE) | {"CHASSIS", "V_BIAS", "VREF_EXT"}
KEEP_PREFIX = ("REGCAP", "REFOUT_", "SYNC_")      # short decoupling/strap nets: never rip


def plan_ripup(b, item_a, item_b, net):
    """Route `net` through other signal tracks at a cost; list the tracks in the way.

    Pads, vias, plane/contact/chassis copper stay hard. The listed tracks are
    deleted by `finish.py rip`, then a normal maze run routes `net` and re-routes
    what was ripped."""
    nc = item_a.GetNetCode()
    w = width_of(net)
    start_xy = item_a.GetPosition() if hasattr(item_a, "GetNumber") else item_a.GetStart()
    dom = domain(pcbnew.ToMM(start_xy.x), pcbnew.ToMM(start_xy.y))
    dm = domain_mask(dom, w / 2 + 0.05)
    hard, soft, tracks = [], [], []
    for li, layer in enumerate(LAYERS):
        h = np.zeros((NY, NX), bool)
        sf = np.zeros((NY, NX), bool)
        for it, is_pad, ref in items_on(b, layer):
            if it.GetNetCode() == nc:
                continue
            on = bare(it.GetNetname())
            sh = shape(it, layer, need(net, on, is_pad, ref) + w / 2)
            if is_pad or on in KEEP or on.startswith(KEEP_PREFIX):
                raster(sh, h)
            else:
                raster(sh, sf)
                tracks.append((li, it))
        hard.append(h | ~dm)
        soft.append(sf)
    starts, goals = [], []
    for li in range(2):
        for item, out in ((item_a, starts), (item_b, goals)):
            if not item.IsOnLayer(LAYERS[li]):
                continue
            ys, xs = np.nonzero(item_cells(item, li))
            for gy, gx in zip(ys, xs):
                hard[li][gy, gx] = False
                out.append((li, gx, gy))
    res = astar(hard, starts, goals, via_sites(~(hard[0] | hard[1]), w), False, soft, 20.0)
    if res is None:
        print(f"  {net}: no path even through soft copper")
        return []
    path = res[0]
    cells = [set(), set()]
    for L, gx, gy in path:
        cells[L].add((gx, gy))
    rip = []
    for li, t in tracks:
        m = np.zeros((NY, NX), bool)
        raster(shape(t, LAYERS[li], need(net, bare(t.GetNetname()), False, "") + w / 2), m)
        ys, xs = np.nonzero(m)
        if any((x, y) in cells[li] for x, y in zip(xs, ys)):
            rip.append(t)
    print(f"  {net}: path of {len(path)} cells crosses {len(rip)} tracks on nets "
          f"{sorted({bare(t.GetNetname()) for t in rip})}")
    return [t.m_Uuid.AsString() for t in rip]


def main():
    dry = "--dry-run" in sys.argv
    ripup = "--ripup" in sys.argv
    skip = set(sys.argv[sys.argv.index("--skip") + 1:]) if "--skip" in sys.argv else set()
    d = json.load(open(REPORT, encoding="utf-8"))
    b = pcbnew.LoadBoard(BOARD)
    done = 0
    first = set()
    if os.path.exists(FIRST_FILE) and not ripup:
        first = {l.strip() for l in open(FIRST_FILE, encoding="utf-8") if l.strip()}
        os.remove(FIRST_FILE)

    def prio(u):          # the nets the rip-up was for take the freed corridor first
        n = u["items"][0]["description"].split("[", 1)[-1].split("]", 1)[0]
        return 0 if bare(n) in first else 1
    for u in sorted(d["unconnected_items"], key=prio):
        a, z = u["items"]
        ia, iz = find_item(b, a["description"], a["pos"]), find_item(b, z["description"], z["pos"])
        if ia is None or iz is None:
            print("item not found:", a["description"][:50], "|", z["description"][:50])
            continue
        net = bare(ia.GetNetname())
        if net in skip:
            print(f"{net}: skipped (hand route)")
            continue
        print(f"{net}: {a['description'][:40]} -> {z['description'][:40]}")
        if ripup:
            uu = plan_ripup(b, ia, iz, net)
            if uu:
                with open(FIRST_FILE, "a", encoding="utf-8") as fh:
                    fh.write(net + "\n")
            with open(RIP_FILE, "a", encoding="utf-8") as fh:
                fh.write("".join(u + "\n" for u in uu))
            continue
        done += route_one(b, ia, iz, net, dry)
        if not dry:
            pcbnew.SaveBoard(BOARD, b)   # each route becomes an obstacle for the next
            b = pcbnew.LoadBoard(BOARD)
            _CACHE.clear()
    print(f"routed {done} of {len(d['unconnected_items'])}")


if __name__ == "__main__":
    main()
