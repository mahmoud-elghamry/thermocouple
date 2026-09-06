"""Close the connections DRC still reports as missing.

Freerouting converges with a handful of connections unfinished on a board this
dense, and the plane-stitching pass only knows how to help a pad that needs a
via.  This step works from the DRC report itself: for every ``unconnected
items`` violation it takes the two positions KiCad names and draws a track
between them, on the same layer, checked against every other piece of copper
first.

Nothing is forced.  A pair that cannot be joined cleanly is reported and left
open, because a track pushed through other copper is worse than a gap you can
see in the report.

Run with KiCad 10's bundled Python, after ``route.py``:

    python close_gaps.py            # uses drc-report.rpt
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pcbnew

import generate_board as gb


ROOT = Path(__file__).resolve().parent
mm = pcbnew.ToMM

ITEM = re.compile(
    r"@\((?P<x>[-\d.]+) mm, (?P<y>[-\d.]+) mm\): "
    r"(?P<kind>Track|Via|Pad \d+|PTH pad \d+) \[(?P<net>[^\]]+)\]"
    r"(?: of (?P<ref>\S+))?(?: on (?P<layer>[FB]\.Cu))?")

LAYERS = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}


def parse_gaps(report: Path) -> list[tuple[str, list[dict]]]:
    """Every 'unconnected items' violation, as a net plus its two endpoints."""
    gaps, current = [], None
    for line in report.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("[unconnected_items]"):
            current = []
            gaps.append(current)
            continue
        if current is None:
            continue
        if line.startswith("["):
            current = None
            continue
        found = ITEM.search(line)
        if found:
            current.append({
                "x": float(found.group("x")),
                "y": float(found.group("y")),
                "net": found.group("net"),
                "layer": found.group("layer"),
                "through": found.group("kind").startswith(("Via", "PTH")),
            })
    return [(g[0]["net"], g) for g in gaps if len(g) >= 2]


def paths(ax: float, ay: float, bx: float, by: float):
    """Candidate routes from A to B, simplest first."""
    yield [(ax, ay), (bx, by)]
    yield [(ax, ay), (bx, ay), (bx, by)]
    yield [(ax, ay), (ax, by), (bx, by)]
    # Escape clear of the pin row first, then run across.  This is what an AVDD
    # pad next to its own DNC neighbours needs: a straight shot would run along
    # the row and clash with the pins either side of it.
    for offset in (1.2, 1.6, 2.2, 3.0, -1.2, -1.6, -2.2, -3.0):
        yield [(ax, ay), (ax, ay + offset), (bx, ay + offset), (bx, by)]
        yield [(ax, ay), (ax + offset, ay), (ax + offset, by), (bx, by)]
        yield [(ax, ay), (ax, ay + offset), (bx, ay + offset),
               (bx, by + offset), (bx, by)]


def item_shapes(item) -> list[tuple]:
    """Geometry of a board item, as segments and points in mm."""
    kind = item.Type()
    if kind == pcbnew.PCB_VIA_T:
        pos = item.GetPosition()
        return [("p", mm(pos.x), mm(pos.y))]
    if kind == pcbnew.PCB_TRACE_T:
        a, b = item.GetStart(), item.GetEnd()
        return [("s", mm(a.x), mm(a.y), mm(b.x), mm(b.y))]
    if kind == pcbnew.PCB_PAD_T:
        pos = item.GetPosition()
        return [("p", mm(pos.x), mm(pos.y))]
    return []


def shape_distance(one, two) -> tuple[float, tuple, tuple]:
    """Closest distance between two shapes and the points that realise it."""
    def sample(shape):
        if shape[0] == "p":
            return [(shape[1], shape[2])]
        _, ax, ay, bx, by = shape
        steps = max(2, int(((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5 / 0.25))
        return [(ax + (bx - ax) * i / steps, ay + (by - ay) * i / steps)
                for i in range(steps + 1)]

    best = (1e9, None, None)
    for p in sample(one):
        for q in sample(two):
            d = ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5
            if d < best[0]:
                best = (d, p, q)
    return best


def find_item(board, net_code: int, x: float, y: float, tolerance: float = 0.01):
    """The board item the DRC report is pointing at."""
    for item in board.GetTracks():
        if item.GetNetCode() != net_code:
            continue
        for pos in (item.GetStart(), item.GetEnd(), item.GetPosition()):
            if abs(mm(pos.x) - x) < tolerance and abs(mm(pos.y) - y) < tolerance:
                return item
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() != net_code:
                continue
            pos = pad.GetPosition()
            if abs(mm(pos.x) - x) < tolerance and abs(mm(pos.y) - y) < tolerance:
                return pad
    return None


def closest_between(board, connectivity, first, second):
    """Nearest pair of points between the two copper islands, and their layer.

    The coordinates DRC prints are each item's anchor, not the place where the
    two islands come closest, so routing anchor-to-anchor usually fails.  Walk
    both galvanically connected sets instead.
    """
    def island(item):
        items = [item]
        try:
            items += list(connectivity.GetConnectedItems(item))
        except Exception:
            pass
        shapes = []
        for entry in items:
            for shape in item_shapes(entry):
                layer = (pcbnew.F_Cu if entry.IsOnLayer(pcbnew.F_Cu)
                         else pcbnew.B_Cu)
                shapes.append((shape, layer))
        return shapes

    best = (1e9, None, None, None)
    for shape_a, layer_a in island(first):
        for shape_b, layer_b in island(second):
            if layer_a != layer_b:
                continue
            d, p, q = shape_distance(shape_a, shape_b)
            if d < best[0]:
                best = (d, p, q, layer_a)
    return best


def stub(point, spot, seg_clear, layer):
    """Straight or L-shaped run from a pad/track end out to its via."""
    px, py = point
    sx, sy = spot
    for path in (((px, py), (sx, sy)),
                 ((px, py), (px, sy), (sx, sy)),
                 ((px, py), (sx, py), (sx, sy))):
        legs = [(p[0], p[1], q[0], q[1]) for p, q in zip(path, path[1:]) if p != q]
        if legs and all(seg_clear(leg, layer) for leg in legs):
            return legs
    return None


def hop(board, tracks, vias, pads, code, origin, target,
        width: float, clearance: float):
    """Route origin -> via -> other layer -> via -> target."""
    margin = width / 2 + clearance
    via_r = 0.3
    via_keep = via_r + clearance
    hole_keep = 0.7

    def seg_clear(seg, layer):
        for ax, ay, bx, by, half, other, tlayer in tracks:
            if other == code or (tlayer is not None and tlayer != layer):
                continue
            if gb.segments_distance(seg, (ax, ay, bx, by)) < margin + half:
                return False
        for ox, oy, half, other, _ in vias:
            if other != code and gb.segment_distance(ox, oy, *seg) < margin + half:
                return False
        for x0, y0, x1, y1, other in pads:
            if other != code and gb.segment_box_distance(seg, (x0, y0, x1, y1)) < margin:
                return False
        # Sample along the segment and allow for its width: an endpoint test
        # alone let a track sit on the barrier edge with half its copper
        # inside the keepout.
        for _, poly in gb.BARRIER_AREAS:
            for step in range(11):
                t = step / 10
                px = seg[0] + (seg[2] - seg[0]) * t
                py = seg[1] + (seg[3] - seg[1]) * t
                for ox, oy in ((0, 0), (margin, 0), (-margin, 0),
                               (0, margin), (0, -margin)):
                    if gb.point_in_polygon(px + ox, py + oy, poly):
                        return False
        return True

    def via_clear(vx, vy):
        for _, poly in gb.BARRIER_AREAS:
            if gb.point_in_polygon(vx, vy, poly):
                return False
        for ax, ay, bx, by, half, other, _ in tracks:
            if other != code and gb.segment_distance(vx, vy, ax, ay, bx, by) < via_keep + half:
                return False
        for ox, oy, half, other, _ in vias:
            gap = ((vx - ox) ** 2 + (vy - oy) ** 2) ** 0.5
            if gap < hole_keep or (other != code and gap < via_keep + half):
                return False
        for x0, y0, x1, y1, other in pads:
            limit = via_r + 0.3 if other == code else via_keep
            if (x0 - limit < vx < x1 + limit) and (y0 - limit < vy < y1 + limit):
                return False
        return True

    def spots(px, py):
        found = []
        step = 0.25
        span = int(10.0 / step)
        for gx in range(-span, span + 1):
            for gy in range(-span, span + 1):
                cx, cy = px + gx * step, py + gy * step
                d = ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5
                if d < 0.9 or d > 10.0:
                    continue
                found.append((d, cx, cy))
        found.sort()
        return found

    for _, ax, ay in spots(*origin)[:400]:
        if not via_clear(ax, ay):
            continue
        stub_a = stub(origin, (ax, ay), seg_clear, pcbnew.F_Cu)
        if stub_a is None:
            continue
        for _, bx, by in spots(*target)[:400]:
            if not via_clear(bx, by):
                continue
            stub_b = stub(target, (bx, by), seg_clear, pcbnew.F_Cu)
            if stub_b is None:
                continue
            for path in ([(ax, ay), (bx, ay), (bx, by)],
                         [(ax, ay), (ax, by), (bx, by)],
                         [(ax, ay), (bx, by)]):
                legs = [(p[0], p[1], q[0], q[1]) for p, q in zip(path, path[1:])
                        if p != q]
                if legs and all(seg_clear(leg, pcbnew.B_Cu) for leg in legs):
                    out = [(*leg, pcbnew.F_Cu) for leg in stub_a]
                    out += [(*leg, pcbnew.B_Cu) for leg in legs]
                    out += [(*leg, pcbnew.F_Cu) for leg in stub_b]
                    return out, [(ax, ay), (bx, by)]
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="drc-report.rpt")
    parser.add_argument("--width", type=float, default=0.35)
    parser.add_argument("--clearance", type=float, default=0.25)
    args = parser.parse_args()

    report = ROOT / args.report
    if not report.exists():
        raise SystemExit(f"No DRC report at {report}; run kicad-cli pcb drc first")

    gaps = parse_gaps(report)
    if not gaps:
        print("DRC reports no missing connections")
        return 0

    board = pcbnew.LoadBoard(str(gb.BOARD_FILE))
    board.BuildConnectivity()
    connectivity = board.GetConnectivity()
    tracks, vias, pads = gb.obstacles(board)
    margin = args.width / 2 + args.clearance

    def clear(seg, code: int, layer: int) -> bool:
        for ax, ay, bx, by, half, other, tlayer in tracks:
            if other == code or (tlayer is not None and tlayer != layer):
                continue
            if gb.segments_distance(seg, (ax, ay, bx, by)) < margin + half:
                return False
        for ox, oy, half, other, _ in vias:
            if other != code and gb.segment_distance(ox, oy, *seg) < margin + half:
                return False
        for x0, y0, x1, y1, other in pads:
            if other != code:
                if gb.segment_box_distance(seg, (x0, y0, x1, y1)) < margin:
                    return False
        # Sample along the segment and allow for its width: an endpoint test
        # alone let a track sit on the barrier edge with half its copper
        # inside the keepout.
        for _, poly in gb.BARRIER_AREAS:
            for step in range(11):
                t = step / 10
                px = seg[0] + (seg[2] - seg[0]) * t
                py = seg[1] + (seg[3] - seg[1]) * t
                for ox, oy in ((0, 0), (margin, 0), (-margin, 0),
                               (0, margin), (0, -margin)):
                    if gb.point_in_polygon(px + ox, py + oy, poly):
                        return False
        return True

    closed, left = 0, []
    for net_name, items in gaps:
        net = board.FindNet(net_name)
        if net is None:
            left.append(f"{net_name}: net not on the board")
            continue
        code = net.GetNetCode()
        a, b = items[0], items[1]
        layers = [LAYERS[a["layer"]]] if a["layer"] else [pcbnew.F_Cu, pcbnew.B_Cu]
        if a["through"] or b["through"]:
            layers = [pcbnew.F_Cu, pcbnew.B_Cu]

        item_a = find_item(board, code, a["x"], a["y"])
        item_b = find_item(board, code, b["x"], b["y"])
        origin = (a["x"], a["y"])
        target = (b["x"], b["y"])
        if item_a is not None and item_b is not None:
            distance, p, q, layer = closest_between(board, connectivity,
                                                    item_a, item_b)
            if p is not None:
                origin, target, layers = p, q, [layer]

        drawn = None
        for layer in layers:
            for path in paths(origin[0], origin[1], target[0], target[1]):
                legs = [(p[0], p[1], q[0], q[1])
                        for p, q in zip(path, path[1:]) if p != q]
                if legs and all(clear(leg, code, layer) for leg in legs):
                    drawn = (layer, legs)
                    break
            if drawn:
                break

        if drawn is None:
            # Same-layer routing is blocked - hop to the other side.  Both of
            # the links this board needs run along a pin row where the top
            # layer is full but the bottom is empty, which is exactly what a
            # via pair is for.
            drawn_hop = hop(board, tracks, vias, pads, code, origin, target,
                            args.width, args.clearance)
            if drawn_hop is None:
                left.append(f"{net_name} between ({a['x']:.2f},{a['y']:.2f}) "
                            f"and ({b['x']:.2f},{b['y']:.2f})")
                continue
            legs, via_points = drawn_hop
            for ax, ay, bx, by, layer in legs:
                gb.add_track(board, net, (ax, ay), (bx, by), layer, args.width)
                tracks.append((ax, ay, bx, by, args.width / 2, code, layer))
            for vx, vy in via_points:
                via = pcbnew.PCB_VIA(board)
                via.SetNet(net)
                via.SetPosition(gb.v(vx, vy))
                via.SetWidth(pcbnew.FromMM(0.6))
                via.SetDrill(pcbnew.FromMM(0.3))
                via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                board.Add(via)
                vias.append((vx, vy, 0.3, code, None))
            closed += 1
            print(f"Closed {net_name} with a via pair and "
                  f"{len(legs)} segment(s)")
            continue
        layer, legs = drawn
        for ax, ay, bx, by in legs:
            gb.add_track(board, net, (ax, ay), (bx, by), layer, args.width)
            tracks.append((ax, ay, bx, by, args.width / 2, code, layer))
        closed += 1
        print(f"Closed {net_name} on {'F.Cu' if layer == pcbnew.F_Cu else 'B.Cu'} "
              f"with {len(legs)} segment(s)")

    gb.fill_zones(board)
    pcbnew.SaveBoard(str(gb.BOARD_FILE), board)
    for item in left:
        print(f"  still open: {item}")
    print(f"Closed {closed} of {len(gaps)} reported gaps")
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main())
