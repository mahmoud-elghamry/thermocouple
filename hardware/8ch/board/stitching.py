"""Vias that tie surface-mount supply pads down to the inner planes."""

from __future__ import annotations

import math

import pcbnew

from .copper import add_track
from .geometry import (point_in_polygon, segment_box_distance,
                       segment_distance, segments_distance)
from .units import bare, to_mm, v
from .zones import (BARRIER_AREAS, CONTROL_OUTLINE, RS485_OUTLINE,
                    SENSOR_OUTLINE)


PLANE_NETS = {"GND_SENS", "+3V3_SENS", "GND_CTRL", "+5V_CTRL",
              "GND_RS485", "+5V_RS485"}


def via_fits(padfootprint_boxes, placed, vx: float, vy: float, code: int,
              radius: float = 0.3, clearance: float = 0.3) -> bool:
    """A 0.6 mm via at (vx, vy) that clears every pad and every earlier via."""
    for x0, y0, x1, y1, other in padfootprint_boxes:
        limit = radius + (0.3 if other == code else clearance)
        if (x0 - limit < vx < x1 + limit) and (y0 - limit < vy < y1 + limit):
            return False
    # Two vias 0.3 mm apart is a drilled slot, not two vias.  Checking pads
    # alone put 128 hole-clearance errors on the board.
    for ox, oy in placed:
        if math.hypot(vx - ox, vy - oy) < 2 * radius + 0.35:
            return False
    return True


def add_channel_supply_vias(board: pcbnew.BOARD) -> int:
    """Drop a fixed via on each MAX31856 supply pin, before routing.

    AVDD (pin 5) and DVDD (pin 8) are the two pins that must reach the
    +3V3_SENS plane, and they sit in the middle of a pin row that the
    autorouter fills with the channel's own signals.  Left to the router, some
    channels got a via and some did not - and a supply pin that has to be
    rescued afterwards ends up with a different, longer connection than its
    neighbours.

    On a board measuring microvolts, eight channels that are not laid out
    identically are eight channels that do not behave identically.  So the
    supply escape is designed here, the same way on every channel, and the
    router has to work around it.
    """
    reach = 1.40
    added = 0
    skipped: list[str] = []
    placed_vias: list[tuple[float, float]] = []
    padfootprint_boxes = []
    for other in board.GetFootprints():
        for other_pad in other.Pads():
            box = other_pad.GetBoundingBox()
            x0, y0 = to_mm(box.GetX()), to_mm(box.GetY())
            padfootprint_boxes.append((x0, y0, x0 + to_mm(box.GetWidth()),
                              y0 + to_mm(box.GetHeight()), other_pad.GetNetCode()))
    # The isolators and the RS-485 transceiver need the same treatment: their
    # supply pins sit between signal pins on a 1.27 mm row, so a pour cannot
    # reach them and the router has to be told to leave room for a via.
    # Only the eight measurement channels.  Extending this to the isolators
    # and the transceiver made the board worse, not better: their supply pins
    # sit between signal pins the router still has to reach, and the extra
    # fixed vias cost more routability than they bought.
    refs = [f"U{channel + 1}" for channel in range(1, 9)]
    for ref in refs:
        fp = next((f for f in board.GetFootprints()
                   if f.GetReference() == ref), None)
        if fp is None:
            raise RuntimeError(f"{ref} is not on the board")
        centre = fp.GetPosition()
        for pad in fp.Pads():
            if bare(pad.GetNetname()) != "+3V3_SENS":
                continue
            pos = pad.GetPosition()
            px, py = to_mm(pos.x), to_mm(pos.y)
            dx, dy = to_mm(pos.x - centre.x), to_mm(pos.y - centre.y)
            # Straight out of the pin row, not along the diagonal to the
            # package centre, so the via stays in its own pin's channel.
            if abs(dy) >= abs(dx):
                options = [(0.0, math.copysign(r, dy)) for r in (reach, 1.55, 1.7, 2.2, 2.9)]
                options += [(math.copysign(r, dx), 0.0) for r in (1.6, 1.9, 2.6)]
            else:
                options = [(math.copysign(r, dx), 0.0) for r in (reach, 1.55, 1.7, 2.2, 2.9)]
                options += [(0.0, math.copysign(r, dy)) for r in (1.6, 1.9, 2.6)]
            spot = None
            for ox, oy in options:
                cx, cy = px + ox, py + oy
                if via_fits(padfootprint_boxes, placed_vias, cx, cy, pad.GetNetCode()):
                    spot = (cx, cy)
                    break
            if spot is None:
                skipped.append(f"{ref}.{pad.GetNumber()}")
                continue
            vx, vy = spot
            net = board.FindNet(pad.GetNetname())
            add_track(board, net, (px, py), (vx, vy), pcbnew.F_Cu, 0.3)
            via = pcbnew.PCB_VIA(board)
            via.SetNet(net)
            via.SetPosition(v(vx, vy))
            via.SetWidth(pcbnew.FromMM(0.6))
            via.SetDrill(pcbnew.FromMM(0.3))
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            board.Add(via)
            placed_vias.append((vx, vy))
            added += 1
    if skipped:
        print("  no room for a fixed supply via at: " + ", ".join(skipped))
    return added


def add_plane_stitching(board: pcbnew.BOARD, via_mm: float = 0.8,
                        drill_mm: float = 0.4,
                        clearance: float = 0.25) -> tuple[int, list[str]]:
    """Give every unconnected SMD supply pad a via down to its plane.

    THT pads span all four layers already; SMD pads do not, so a decoupling
    capacitor with no via near it is not decoupling anything.  Freerouting's
    fanout places most of these but not all - it escaped 280 of 407 SMD pins on
    this board.

    Runs after routing, so both the via *and* the short stub that reaches it
    are checked against the copper that is already there, against the isolation
    keepouts, and against hole-to-hole and solder-mask spacing.  Checking only
    the via position was not enough: the stubs crossed existing tracks.  Pads
    with no clear position are reported rather than forced.
    """
    via_r = via_mm / 2
    stub_w = 0.3
    keep = via_r + clearance                 # via copper to foreign copper
    pad_keep = via_r + 0.35                  # via to any pad: mask + hole room
    hole_keep = 0.75                         # drill centre to drill centre

    tracks, vias, pads, drilled = [], [], [], []
    for item in board.GetTracks():
        code = item.GetNetCode()
        if item.Type() == pcbnew.PCB_VIA_T:
            pos = item.GetPosition()
            # PCB_VIA::GetWidth() needs an explicit layer in KiCad 10; the
            # no-argument overload trips a wxWidgets assert that opens a modal
            # dialog and hangs a headless run.
            vias.append((to_mm(pos.x), to_mm(pos.y),
                         to_mm(item.GetWidth(pcbnew.F_Cu)) / 2, code))
        else:
            a, b = item.GetStart(), item.GetEnd()
            tracks.append((to_mm(a.x), to_mm(a.y), to_mm(b.x), to_mm(b.y),
                           to_mm(item.GetWidth()) / 2, code))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            box = pad.GetBoundingBox()
            x0, y0 = to_mm(box.GetX()), to_mm(box.GetY())
            pads.append((x0, y0, x0 + to_mm(box.GetWidth()),
                         y0 + to_mm(box.GetHeight()), pad.GetNetCode()))
            if pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                pos = pad.GetPosition()
                drilled.append((to_mm(pos.x), to_mm(pos.y)))

    def via_is_clear(vx: float, vy: float, code: int) -> bool:
        for _, poly in BARRIER_AREAS:
            if point_in_polygon(vx, vy, poly):
                return False
        for ax, ay, bx, by, half, other in tracks:
            if other != code and segment_distance(vx, vy, ax, ay, bx, by) < keep + half:
                return False
        for ox, oy, half, other in vias:
            gap = math.hypot(vx - ox, vy - oy)
            if gap < hole_keep or (other != code and gap < keep + half):
                return False
        for ox, oy in drilled:
            if math.hypot(vx - ox, vy - oy) < hole_keep + 0.5:
                return False
        for x0, y0, x1, y1, other in pads:
            limit = pad_keep if other == code else keep
            if (x0 - limit < vx < x1 + limit) and (y0 - limit < vy < y1 + limit):
                return False
        return True

    def stub_is_clear(seg, code: int) -> bool:
        margin = stub_w / 2 + clearance
        for ax, ay, bx, by, half, other in tracks:
            if other == code:
                continue
            if segments_distance(seg, (ax, ay, bx, by)) < margin + half:
                return False
        for x0, y0, x1, y1, other in pads:
            if other == code:
                continue
            if segment_box_distance(seg, (x0, y0, x1, y1)) < margin:
                return False
        for ox, oy, half, other in vias:
            if other == code:
                continue
            if segment_distance(ox, oy, *seg) < margin + half:
                return False
        return True

    added, stranded = 0, []
    connectivity = board.GetConnectivity()
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if bare(pad.GetNetname()) not in PLANE_NETS:
                continue
            if pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue          # through-hole pads already span every layer
            # A pad on a plane net is only actually on the plane if it can
            # reach a via; the plane itself lives on an inner layer.
            if any(item.Type() == pcbnew.PCB_VIA_T
                   for item in connectivity.GetConnectedItems(pad)):
                continue
            pos = pad.GetPosition()
            px, py = to_mm(pos.x), to_mm(pos.y)
            code = pad.GetNetCode()
            centre = fp.GetPosition()
            dx, dy = to_mm(pos.x - centre.x), to_mm(pos.y - centre.y)
            length = math.hypot(dx, dy) or 1.0
            ux, uy = dx / length, dy / length
            # Search a grid around the pad, nearest first, and bias slightly
            # towards the outward direction so the stub does not run back under
            # its own component.  Rays alone rejected every candidate on the
            # densely routed sensor island.
            candidates = []
            step = 0.25
            span = int(6.0 / step)
            for gx in range(-span, span + 1):
                for gy in range(-span, span + 1):
                    ox, oy = gx * step, gy * step
                    distance = math.hypot(ox, oy)
                    if distance < 1.1 or distance > 6.0:
                        continue
                    outward = (ox * ux + oy * uy) / distance
                    candidates.append((distance - outward * 0.6, px + ox, py + oy))
            candidates.sort()
            spot = None
            for _, cx, cy in candidates:
                if via_is_clear(cx, cy, code) and stub_is_clear((px, py, cx, cy), code):
                    spot = (cx, cy)
                    break
            if spot is None:
                stranded.append(f"{fp.GetReference()}.{pad.GetNumber()} "
                                f"[{pad.GetNetname()}]")
                continue
            vx, vy = spot
            net = board.FindNet(pad.GetNetname())
            add_track(board, net, (px, py), (vx, vy),
                      pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu,
                      stub_w)
            via = pcbnew.PCB_VIA(board)
            via.SetNet(net)
            via.SetPosition(v(vx, vy))
            via.SetWidth(pcbnew.FromMM(via_mm))
            via.SetDrill(pcbnew.FromMM(drill_mm))
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            board.Add(via)
            vias.append((vx, vy, via_r, code))
            tracks.append((px, py, vx, vy, stub_w / 2, code))
            added += 1
    return added, stranded


def stitch_pour_islands(board: pcbnew.BOARD, via_mm: float = 0.8,
                        drill_mm: float = 0.4,
                        clearance: float = 0.3) -> tuple[int, list[str]]:
    """Tie every isolated piece of an outer ground pour down to its plane.

    The pours on F.Cu and B.Cu get cut into separate pieces by the routing
    that runs through them.  A piece that no longer touches the rest of its
    net is floating copper: it does nothing for shielding, it does nothing for
    the return path, and DRC reports it as a missing connection.  One via per
    piece drops it onto the plane on In1 and the problem disappears.

    This has to run *after* the pours are filled, which is why the finishing
    order in ``route.py`` puts the pours before the stitching rather than
    after it.  With the old order the islands did not exist yet when the
    stitching pass looked for them, and seven of them survived to DRC.
    """
    via_r = via_mm / 2
    keep = via_r + clearance
    hole_keep = 0.75
    min_island_mm2 = 1.0

    tracks, vias, pads, drilled = [], [], [], []
    for item in board.GetTracks():
        code = item.GetNetCode()
        if item.Type() == pcbnew.PCB_VIA_T:
            pos = item.GetPosition()
            vias.append((to_mm(pos.x), to_mm(pos.y),
                         to_mm(item.GetWidth(pcbnew.F_Cu)) / 2, code))
        else:
            a, b = item.GetStart(), item.GetEnd()
            tracks.append((to_mm(a.x), to_mm(a.y), to_mm(b.x), to_mm(b.y),
                           to_mm(item.GetWidth()) / 2, code))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            box = pad.GetBoundingBox()
            x0, y0 = to_mm(box.GetX()), to_mm(box.GetY())
            pads.append((x0, y0, x0 + to_mm(box.GetWidth()),
                         y0 + to_mm(box.GetHeight()), pad.GetNetCode()))
            if pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                pos = pad.GetPosition()
                drilled.append((to_mm(pos.x), to_mm(pos.y), pad.GetNetCode()))

    def via_is_clear(vx: float, vy: float, code: int) -> bool:
        for _, poly in BARRIER_AREAS:
            if point_in_polygon(vx, vy, poly):
                return False
        for ax, ay, bx, by, half, other in tracks:
            if other != code and segment_distance(vx, vy, ax, ay, bx, by) < keep + half:
                return False
        for ox, oy, half, other in vias:
            gap = math.hypot(vx - ox, vy - oy)
            if gap < hole_keep or (other != code and gap < keep + half):
                return False
        for ox, oy, _ in drilled:
            if math.hypot(vx - ox, vy - oy) < hole_keep + 0.5:
                return False
        for x0, y0, x1, y1, other in pads:
            limit = via_r + 0.35 if other == code else keep
            if (x0 - limit < vx < x1 + limit) and (y0 - limit < vy < y1 + limit):
                return False
        return True

    # A via only earns its place if it lands inside the inner plane for its
    # own net.  Outside it the via reaches nothing and DRC calls it dangling,
    # which is exactly what happened the first time this ran.
    island_outline = {
        "GND_SENS": SENSOR_OUTLINE, "+3V3_SENS": SENSOR_OUTLINE,
        "GND_CTRL": CONTROL_OUTLINE, "+5V_CTRL": CONTROL_OUTLINE,
        "GND_RS485": RS485_OUTLINE, "+5V_RS485": RS485_OUTLINE,
    }

    added, stranded = 0, []
    for index in range(board.GetAreaCount()):
        zone = board.GetArea(index)
        if zone.GetIsRuleArea():
            continue
        net_name = bare(zone.GetNetname())
        if net_name not in PLANE_NETS:
            continue
        plane = island_outline[net_name]
        code = zone.GetNetCode()
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            if not zone.IsOnLayer(layer):
                continue
            filled = zone.GetFilledPolysList(layer)
            for island in range(filled.OutlineCount()):
                chain = filled.Outline(island)
                box = chain.BBox()
                x0, y0 = to_mm(box.GetX()), to_mm(box.GetY())
                x1 = x0 + to_mm(box.GetWidth())
                y1 = y0 + to_mm(box.GetHeight())
                if (x1 - x0) * (y1 - y0) < min_island_mm2:
                    continue

                def inside(px: float, py: float) -> bool:
                    return chain.PointInside(v(px, py))

                # Already anchored?  A via or a through-hole pad of this net
                # sitting in the piece means it is on the plane already.
                anchored = any(other == code and inside(ox, oy)
                               for ox, oy, _, other in vias)
                anchored = anchored or any(other == code and inside(ox, oy)
                                           for ox, oy, other in drilled)
                if anchored:
                    continue

                spot = None
                step = 0.5
                steps_x = max(1, int((x1 - x0) / step))
                steps_y = max(1, int((y1 - y0) / step))
                for iy in range(steps_y + 1):
                    for ix in range(steps_x + 1):
                        px, py = x0 + ix * step, y0 + iy * step
                        if not inside(px, py):
                            continue
                        # Keep the via's own copper inside the piece.  The
                        # probe used to test at the clearance radius, which is
                        # the spacing to *other* nets, not to the edge of the
                        # copper the via is landing on - that over-constraint
                        # left thin pieces unstitchable.
                        if not all(inside(px + dx, py + dy)
                                   for dx, dy in ((via_r, 0), (-via_r, 0),
                                                  (0, via_r), (0, -via_r))):
                            continue
                        if not point_in_polygon(px, py, plane):
                            continue        # no inner plane here to reach
                        if via_is_clear(px, py, code):
                            spot = (px, py)
                            break
                    if spot:
                        break

                if spot is None:
                    stranded.append(f"{zone.GetZoneName() or zone.GetNetname()} "
                                    f"island at ({x0:.1f},{y0:.1f})")
                    continue
                vx, vy = spot
                via = pcbnew.PCB_VIA(board)
                via.SetNet(zone.GetNet())
                via.SetPosition(v(vx, vy))
                via.SetWidth(pcbnew.FromMM(via_mm))
                via.SetDrill(pcbnew.FromMM(drill_mm))
                via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                board.Add(via)
                vias.append((vx, vy, via_r, code))
                added += 1
    return added, stranded
