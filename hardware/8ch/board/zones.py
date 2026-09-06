"""Copper pours, the isolation keepouts, and filling them."""

from __future__ import annotations

import pcbnew

from .config import (BOARD_H, BOARD_W, CONTROL_LOWER_Y, CONTROL_SPLIT_X,
                     CONTROL_X0, CONTROL_X1, RS485_X0, RS485_Y0,
                     SENSOR_X1, ZONE_BOTTOM, ZONE_LEFT, ZONE_TOP)


SENSOR_OUTLINE = [(ZONE_LEFT, ZONE_TOP), (SENSOR_X1, ZONE_TOP),
                  (SENSOR_X1, ZONE_BOTTOM), (ZONE_LEFT, ZONE_BOTTOM)]
CONTROL_OUTLINE = [(CONTROL_X0, ZONE_TOP), (CONTROL_X1, ZONE_TOP),
                   (CONTROL_X1, CONTROL_LOWER_Y),
                   (CONTROL_SPLIT_X, CONTROL_LOWER_Y),
                   (CONTROL_SPLIT_X, ZONE_BOTTOM), (CONTROL_X0, ZONE_BOTTOM)]
RS485_OUTLINE = [(RS485_X0, RS485_Y0), (CONTROL_X1, RS485_Y0),
                 (CONTROL_X1, ZONE_BOTTOM), (RS485_X0, ZONE_BOTTOM)]

# Bands that must stay free of copper.  Emitted both as the gaps between the
# pours and as explicit rule areas, so the autorouter cannot bridge them.
# Clipped to the component area so the chassis/PE ring can still run around the
# outside.  Nothing else wants that corridor: no net has pads in two different
# islands, so no signal has any reason to cross a barrier at all.
KEEPOUT_TOP = ZONE_TOP - 0.5
KEEPOUT_BOTTOM = ZONE_BOTTOM + 0.5
KEEPOUT_RIGHT = CONTROL_X1 + 0.5

BARRIER_AREAS = [
    ("BARRIER_SENSOR_CONTROL",
     [(SENSOR_X1, KEEPOUT_TOP), (CONTROL_X0, KEEPOUT_TOP),
      (CONTROL_X0, KEEPOUT_BOTTOM), (SENSOR_X1, KEEPOUT_BOTTOM)]),
    ("BARRIER_CONTROL_RS485_H",
     [(CONTROL_SPLIT_X, CONTROL_LOWER_Y), (KEEPOUT_RIGHT, CONTROL_LOWER_Y),
      (KEEPOUT_RIGHT, RS485_Y0), (CONTROL_SPLIT_X, RS485_Y0)]),
    ("BARRIER_CONTROL_RS485_V",
     [(CONTROL_SPLIT_X, RS485_Y0), (RS485_X0, RS485_Y0),
      (RS485_X0, KEEPOUT_BOTTOM), (CONTROL_SPLIT_X, KEEPOUT_BOTTOM)]),
]


def add_zone(board: pcbnew.BOARD, net_name: str, layer: int,
             points: list[tuple[float, float]], name: str) -> None:
    net = board.FindNet(net_name) or board.FindNet("/" + net_name)
    if net is None:
        raise RuntimeError(f"Zone net absent: {net_name}")
    zone = pcbnew.ZONE(board)
    zone.SetLayer(layer)
    zone.SetNet(net)
    zone.SetZoneName(name)
    zone.SetMinThickness(pcbnew.FromMM(0.20))
    zone.SetLocalClearance(pcbnew.FromMM(0.30))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    zone.SetThermalReliefGap(pcbnew.FromMM(0.4))
    zone.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.5))
    outline = zone.Outline()
    outline.NewOutline()
    for x, y in points:
        outline.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    board.Add(zone)


def add_keepout(board: pcbnew.BOARD, name: str,
                points: list[tuple[float, float]]) -> None:
    """A rule area that forbids copper but still tolerates existing pads."""
    zone = pcbnew.ZONE(board)
    layers = pcbnew.LSET()
    for layer in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        layers.addLayer(layer)
    zone.SetLayerSet(layers)
    zone.SetIsRuleArea(True)
    zone.SetDoNotAllowTracks(True)
    zone.SetDoNotAllowVias(True)
    zone.SetDoNotAllowZoneFills(True)
    zone.SetDoNotAllowPads(False)
    zone.SetDoNotAllowFootprints(False)
    zone.SetZoneName(name)
    outline = zone.Outline()
    outline.NewOutline()
    for x, y in points:
        outline.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    board.Add(zone)


def add_planes(board: pcbnew.BOARD) -> None:
    """In1 carries the three grounds, In2 the three supplies.

    Keeping both inner layers free of signal routing is the point: every
    outer-layer track then has an uninterrupted return path directly beneath
    it, and the In1/In2 pair forms the interplane capacitance that does most
    of the high-frequency decoupling for the MAX31856 front end.
    """
    for net_name, outline, name in (
        ("GND_SENS", SENSOR_OUTLINE, "SENSOR_GND"),
        ("GND_CTRL", CONTROL_OUTLINE, "CONTROL_GND"),
        ("GND_RS485", RS485_OUTLINE, "RS485_GND"),
    ):
        add_zone(board, net_name, pcbnew.In1_Cu, outline, name)
    for net_name, outline, name in (
        ("+3V3_SENS", SENSOR_OUTLINE, "SENSOR_3V3"),
        ("+5V_CTRL", CONTROL_OUTLINE, "CONTROL_5V"),
        ("+5V_RS485", RS485_OUTLINE, "RS485_5V"),
    ):
        add_zone(board, net_name, pcbnew.In2_Cu, outline, name)
    for name, points in BARRIER_AREAS:
        add_keepout(board, name, points)

OUTER_GROUND_POURS = (
    ("GND_SENS", SENSOR_OUTLINE, "SENSOR"),
    ("GND_CTRL", CONTROL_OUTLINE, "CONTROL"),
    ("GND_RS485", RS485_OUTLINE, "RS485"),
)


def add_outer_ground_pours(board: pcbnew.BOARD) -> int:
    """Ground pour on F.Cu and B.Cu inside each island, after routing.

    Two reasons, both specific to this board:

    * Thermal.  The MAX31856 compensates the cold junction with its own die
      temperature, but the real junction is the terminal screw 15.8 mm away.
      A continuous copper region spanning both keeps them closer to the same
      temperature, which is the part of H-06 that distance alone cannot fix.
    * Shielding and return path for the outer-layer signal tracks.

    Poured last so it fills around the routing instead of fighting it, and only
    if it is not already there, so re-running the finishing step is safe.
    """
    existing = {board.GetArea(i).GetZoneName()
                for i in range(board.GetAreaCount())}
    added = 0
    for net_name, outline, island in OUTER_GROUND_POURS:
        for layer, side in ((pcbnew.F_Cu, "F"), (pcbnew.B_Cu, "B")):
            name = f"{island}_GND_{side}"
            if name in existing:
                continue
            add_zone(board, net_name, layer, outline, name)
            zone = board.GetArea(board.GetAreaCount() - 1)
            # Copper that ends up disconnected is worse than no copper: it
            # floats, and it shows up as isolated_copper in DRC.
            zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
            zone.SetAssignedPriority(1)
            # Solid connection on the outer pours.  These are supplementary
            # copper: the primary ground connection for a through-hole pad is
            # the In1 plane, which keeps its thermal relief for solderability.
            # Thermal spokes here were being blocked by routing, which DRC
            # reports as a starved thermal connection.
            zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
            added += 1
    return added


def fill_zones(board: pcbnew.BOARD) -> None:
    board.BuildConnectivity()
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
