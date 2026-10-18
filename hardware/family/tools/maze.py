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

from profiles import ACTIVE as P, ROOT
import heapq
import json
import math
import os
import sys

import numpy as np
import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from profiles import geometry
domain, BANDS = geometry()  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
HW = str(P["work_folder"])
BOARD = str(P["pcb"])
REPORT = os.path.join(HW, "output", "finish-drc.json")
RES = 0.05                     # grid step, mm
W, H = P.require("width"), P.require("height")
NX, NY = int(W / RES), int(H / RES)
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)
if os.environ.get("THERMO" + P["key"] + "_MAZE_IN2"):     # also In2.Cu (+3V3_ISO plane layer), at a cost per step
    LAYERS += (pcbnew.In2_Cu,)
IN2_PENALTY = 2.0
VIA_D, VIA_DR, VIA_COST = 0.6, 0.3, 40
CONTACT = P.require("contact_nets")
PLANE = P.require("plane_domains")
mm = pcbnew.FromMM

def bare(n):
    return n.rsplit("/", 1)[-1]

def need(a, b, b_is_pad, b_ref):
    """Clearance in mm between the routed net a and copper of net b (conservative)."""
    if a in CONTACT and b in CONTACT:
        return 1.0                       # contact to contact (30 VDC)
    if (a in CONTACT) != (b in CONTACT):
        return 2.0                       # contact_to_rest, relay coil pins included
    if P.require("chassis_net") in (a, b):
        return 1.5
    if {a, b} & P.require("high_clearance_nets"):
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

_CACHE = {}

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
            if t.Type() != pcbnew.PCB_VIA_T:      # a track ending on its own via: start from the via
                for v in b.GetTracks():           # (it reaches every layer)
                    if v.Type() == pcbnew.PCB_VIA_T and v.GetNetname() == net and \
                            (v.HitTest(t.GetStart(), 0) or v.HitTest(t.GetEnd(), 0)):
                        return v
            return t
    return None

def item_cells(item, layer_idx):
    m = np.zeros((NY, NX), bool)
    raster(shape(item, LAYERS[layer_idx], 0.0), m)
    return m

def route_one(b, item_a, item_b, net, dry):
    nc = item_a.GetNetCode()
    w = width_of(net)
    start_xy = item_a.GetPosition() if hasattr(item_a, "GetNumber") else item_a.GetStart()
    dom = domain(pcbnew.ToMM(start_xy.x), pcbnew.ToMM(start_xy.y))
    blocked = obstacles(b, net, nc, w)
    dm = domain_mask(dom, w / 2 + 0.05)
    blocked = [m | ~dm for m in blocked]
    via_ok = via_sites(~np.logical_or.reduce(blocked), w)
    no_via = np.zeros((NY, NX), bool)         # own-net SMD pads: never a via in the pad (solder wicking)
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetCode() == nc and p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
                raster(shape(p, p.GetLayer(), VIA_D / 2 + 0.05), no_via)
    via_ok &= ~no_via
    starts, goals = [], []
    for li in range(len(LAYERS)):
        for item, out in ((item_a, starts), (item_b, goals)):
            if item is None or not item.IsOnLayer(LAYERS[li]):
                continue
            cells = item_cells(item, li)
            ys, xs = np.nonzero(cells)
            for gy, gx in zip(ys, xs):
                blocked[li][gy, gx] = False
                out.append((li, gx, gy))
    via_goal = net in PLANE and PLANE[net] == dom
    soft = None
    if len(LAYERS) > 2:
        soft = [np.zeros((NY, NX), bool), np.zeros((NY, NX), bool), np.ones((NY, NX), bool)]
    res = astar(blocked, starts, goals, via_ok, via_goal, soft, IN2_PENALTY)
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
KEEP = CONTACT | set(PLANE) | P.require("keep_nets")
KEEP_PREFIX = P.require("keep_prefix")

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
    for li in range(len(LAYERS)):
        for item, out in ((item_a, starts), (item_b, goals)):
            if not item.IsOnLayer(LAYERS[li]):
                continue
            ys, xs = np.nonzero(item_cells(item, li))
            for gy, gx in zip(ys, xs):
                hard[li][gy, gx] = False
                out.append((li, gx, gy))
    res = astar(hard, starts, goals, via_sites(~np.logical_or.reduce(hard), w), False, soft, 20.0)
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

# Helpers import the entry module constants; preserve one context when run as a script.
import sys
if __name__ == "__main__":
    sys.modules["maze"] = sys.modules[__name__]
from maze_ops import grid_xy, raster, shape, items_on, obstacles, _recompute_without, _obstacles_all, domain_mask, astar, simplify, via_sites

if __name__ == "__main__":
    import guard      # I-115: refuse while KiCad or another tool holds the board
    with guard.claim(str(BOARD), "maze.py"):
        main()
