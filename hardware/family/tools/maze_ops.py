"""Copied algorithms; constants come from the entry tool and its profile."""
from maze import *
from maze import _CACHE

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
    if isinstance(item, pcbnew.PAD) and item.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
        # a mounting hole has no copper but blocks every layer (board hole clearance 0.25)
        item.TransformHoleToPolygon(ps, mm(extra_mm + 0.06), mm(0.005), pcbnew.ERROR_OUTSIDE)
        return ps
    item.TransformShapeToPolygon(ps, layer, mm(extra_mm), mm(0.005), pcbnew.ERROR_OUTSIDE)
    return ps


def items_on(b, layer):
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.IsOnLayer(layer) or p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                yield p, True, fp.GetReference()
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            yield t, True, ""
        elif t.GetLayer() == layer:
            yield t, False, ""


def obstacles(b, net, net_code, w):
    """Blocked grid per layer for a track of width w on `net` (own-net copper excluded).

    Clearances depend only on the routed net's category, so the other-net
    raster is cached per (category, width) and own-net copper is cut back out."""
    cat = "contact" if net in CONTACT else "chassis" if net == P.require("chassis_net") else "std"
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
        keepouts(b, layer, w, full)
        return full
    sub = np.zeros((NY, NX), bool)
    box = pcbnew.BOX2I(pcbnew.VECTOR2I(mm(float(x0 * RES)), mm(float(y0 * RES))),
                       pcbnew.VECTOR2L(mm(float((x1 - x0) * RES)), mm(float((y1 - y0) * RES))))
    for it, is_pad, ref in items_on(b, layer):
        if it.GetNetCode() == net_code or not it.GetBoundingBox().Intersects(box):
            continue
        raster(shape(it, layer, need(net, bare(it.GetNetname()), is_pad, ref) + w / 2), sub)
    keepouts(b, layer, w, sub)
    m[y0:y1 + 1, x0:x1 + 1] = sub[y0:y1 + 1, x0:x1 + 1]
    return m


def _obstacles_all(b, net, w):
    masks = []
    for layer in LAYERS:
        m = np.zeros((NY, NX), bool)
        for it, is_pad, ref in items_on(b, layer):
            r = need(net, bare(it.GetNetname()), is_pad, ref) + w / 2
            raster(shape(it, layer, r), m)
        keepouts(b, layer, w, m)
        masks.append(m)
    return masks


def keepouts(b, layer, w, m):
    """Track keep-out rule areas other than the barrier bands (domain_mask has those), e.g. the 2-layer
    board's ADC_GUARD on B.Cu: their bounding box + w/2 is blocked on that layer."""
    for z in b.Zones():
        if not (z.GetIsRuleArea() and z.GetDoNotAllowTracks() and z.IsOnLayer(layer)) or                 z.GetZoneName().startswith("BARRIER"):
            continue
        bb = z.GetBoundingBox()
        x0 = max(int((pcbnew.ToMM(bb.GetLeft()) - w / 2) / RES), 0)
        y0 = max(int((pcbnew.ToMM(bb.GetTop()) - w / 2) / RES), 0)
        x1 = min(int((pcbnew.ToMM(bb.GetRight()) + w / 2) / RES) + 1, NX - 1)
        y1 = min(int((pcbnew.ToMM(bb.GetBottom()) + w / 2) / RES) + 1, NY - 1)
        m[y0:y1 + 1, x0:x1 + 1] = True


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
            for L2 in range(len(blocked)):
                if L2 == L or blocked[L2][gy, gx]:
                    continue
                nxt = (L2, gx, gy)
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
            if not vias or vias[-1] != a[1:]:
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


