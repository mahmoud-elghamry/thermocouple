"""Finishing connections the autorouter left open."""

from __future__ import annotations

import math

import pcbnew

from .copper import add_track
from .geometry import (point_in_polygon, segment_box_distance,
                       segment_distance, segments_distance)
from .units import to_mm
from .zones import BARRIER_AREAS


def obstacles(board: pcbnew.BOARD):
    """Copper already on the board, as flat lists the collision checks can use."""
    tracks, vias, pads = [], [], []
    for item in board.GetTracks():
        code = item.GetNetCode()
        if item.Type() == pcbnew.PCB_VIA_T:
            pos = item.GetPosition()
            vias.append((to_mm(pos.x), to_mm(pos.y),
                         to_mm(item.GetWidth(pcbnew.F_Cu)) / 2, code, None))
        else:
            a, b = item.GetStart(), item.GetEnd()
            tracks.append((to_mm(a.x), to_mm(a.y), to_mm(b.x), to_mm(b.y),
                           to_mm(item.GetWidth()) / 2, code, item.GetLayer()))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            box = pad.GetBoundingBox()
            x0, y0 = to_mm(box.GetX()), to_mm(box.GetY())
            pads.append((x0, y0, x0 + to_mm(box.GetWidth()),
                         y0 + to_mm(box.GetHeight()), pad.GetNetCode()))
    return tracks, vias, pads


def drop_dangling_vias(board: pcbnew.BOARD) -> int:
    """Remove vias that ended up connected to nothing.

    The stitching passes place a via wherever they find room; if the copper
    they were aiming at gets re-poured away under them, the via is left
    floating.  A floating via is a hole in the board that does nothing, and
    DRC reports it, so take it out again.
    """
    board.BuildConnectivity()
    connectivity = board.GetConnectivity()
    doomed = []
    for item in board.GetTracks():
        if item.Type() != pcbnew.PCB_VIA_T:
            continue
        connected = connectivity.GetConnectedItems(item)
        if not connected:
            doomed.append(item)
            continue
        # A via that only reaches copper on one layer is a drilled hole that
        # joins nothing.  A stitching via in a pour island looks similar - it
        # touches only zones - but it touches them on two layers, which is the
        # whole point of it, so the test is the layer count, not the item type.
        layers = set()
        for other in connected:
            for layer in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
                if other.IsOnLayer(layer):
                    layers.add(layer)
        if len(layers) < 2:
            doomed.append(item)
    for via in doomed:
        try:
            board.Remove(via)
        except AttributeError:
            pass
    return len(doomed)


def close_open_connections(board: pcbnew.BOARD,
                           width: float = 0.3,
                           clearance: float = 0.25) -> tuple[int, list[str]]:
    """Finish connections the autorouter left open.

    Freerouting converges with a handful of nets unfinished on a board this
    dense.  Each remaining pad is joined to the nearest copper already on its
    own net with a straight or L-shaped track, on the pad's own layer, and
    every candidate is collision-checked against everything else first.  A pad
    that cannot be reached cleanly is reported, not forced - a track pushed
    through other copper is worse than a documented gap.
    """
    margin = width / 2 + clearance
    tracks, vias, pads = obstacles(board)
    connectivity = board.GetConnectivity()

    def clear(seg, code: int, layer: int) -> bool:
        for ax, ay, bx, by, half, other, tlayer in tracks:
            if other == code or (tlayer is not None and tlayer != layer):
                continue
            if segments_distance(seg, (ax, ay, bx, by)) < margin + half:
                return False
        for ox, oy, half, other, _ in vias:
            if other == code:
                continue
            if segment_distance(ox, oy, *seg) < margin + half:
                return False
        for x0, y0, x1, y1, other in pads:
            if other == code:
                continue
            if segment_box_distance(seg, (x0, y0, x1, y1)) < margin:
                return False
        for _, poly in BARRIER_AREAS:
            for step in range(11):
                t = step / 10
                px = seg[0] + (seg[2] - seg[0]) * t
                py = seg[1] + (seg[3] - seg[1]) * t
                for ox, oy in ((0, 0), (margin, 0), (-margin, 0),
                               (0, margin), (0, -margin)):
                    if point_in_polygon(px + ox, py + oy, poly):
                        return False
        return True

    open_pads = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() <= 0:
                continue
            if pad.GetNetname().startswith("unconnected-"):
                continue     # deliberately open: NC markers, DNC, DRDY/FAULT
            kinds = {item.Type() for item in connectivity.GetConnectedItems(pad)}
            if kinds & {pcbnew.PCB_TRACE_T, pcbnew.PCB_VIA_T, pcbnew.PCB_ZONE_T}:
                continue
            open_pads.append((fp, pad))

    added, stranded = 0, []
    for fp, pad in open_pads:
        code = pad.GetNetCode()
        pos = pad.GetPosition()
        px, py = to_mm(pos.x), to_mm(pos.y)
        layer = pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu

        anchors = []
        for ax, ay, bx, by, _, other, tlayer in tracks:
            if other == code and tlayer == layer:
                anchors += [(ax, ay), (bx, by)]
        for ox, oy, _, other, _ in vias:
            if other == code:
                anchors.append((ox, oy))
        for other_fp in board.GetFootprints():
            for other_pad in other_fp.Pads():
                if other_pad is pad or other_pad.GetNetCode() != code:
                    continue
                if not other_pad.IsOnLayer(layer):
                    continue
                opos = other_pad.GetPosition()
                anchors.append((to_mm(opos.x), to_mm(opos.y)))
        anchors.sort(key=lambda a: math.hypot(a[0] - px, a[1] - py))

        drawn = None
        for ax, ay in anchors[:40]:
            if math.hypot(ax - px, ay - py) > 25.0:
                break
            for path in (((px, py), (ax, ay)),
                         ((px, py), (ax, py), (ax, ay)),
                         ((px, py), (px, ay), (ax, ay))):
                legs = [(p[0], p[1], q[0], q[1]) for p, q in zip(path, path[1:])
                        if p != q]
                if legs and all(clear(leg, code, layer) for leg in legs):
                    drawn = legs
                    break
            if drawn:
                break

        if not drawn:
            stranded.append(f"{fp.GetReference()}.{pad.GetNumber()} "
                            f"[{pad.GetNetname()}]")
            continue
        net = board.FindNet(pad.GetNetname())
        for ax, ay, bx, by in drawn:
            add_track(board, net, (ax, ay), (bx, by), layer, width)
            tracks.append((ax, ay, bx, by, width / 2, code, layer))
        added += 1

    return added, stranded
