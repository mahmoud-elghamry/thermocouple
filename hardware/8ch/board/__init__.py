"""Board generator for the 8-channel thermocouple protection board.

The whole thing used to be one 1200-line module. Editing it by pattern-matching
put a fix into the wrong function twice on 2026-09-06 and cost two full rebuild
cycles, so it is now split by responsibility:

    config       dimensions, floor plan, the per-channel template - pure data
    units        millimetre conversion, net-name normalisation
    geometry     2D distance maths, no pcbnew types
    boardio      loading, clearing and saving; the SWIG workaround lives here
    placement    where every part sits, and putting it there
    silkscreen   outline, mechanics, reference designators, free text
    zones        copper pours, isolation keepouts, filling
    copper       tracks this project draws itself - the chassis ring
    stitching    vias from supply pads and pour islands down to the planes
    connections  finishing what the autorouter left open

Import from here; `generate_board.py` is the command-line entry point.
"""

from __future__ import annotations

from .config import (BLOCK_PITCH, BLOCK_W, BLOCK_X0, BOARD_DATE, BOARD_FILE,
                     BOARD_H, BOARD_NAME, BOARD_REV, BOARD_W, CHANNEL_TEMPLATE,
                     CONTROL_LOWER_Y, CONTROL_SPLIT_X, CONTROL_X0, CONTROL_X1,
                     FP_ROOT, RING_INSET, RING_WIDTH, ROOT, RS485_X0, RS485_Y0,
                     SENSOR_X1, ZONE_BOTTOM, ZONE_LEFT, ZONE_TOP)
from .units import bare, to_mm, v
from .geometry import (point_in_polygon, segment_box_distance, segment_distance,
                       segments_distance)
from .boardio import clear_generated, clear_in_place, remove_item
from .placement import (FIDUCIALS, MOUNTING_HOLES, PLACEMENTS,
                        add_board_footprint, build_placements, footprint_map,
                        place_footprints)
from .silkscreen import (add_mechanics_and_silkscreen, add_outline, add_text,
                         place_reference_text)
from .zones import (BARRIER_AREAS, CONTROL_OUTLINE, OUTER_GROUND_POURS,
                    RS485_OUTLINE, SENSOR_OUTLINE, add_keepout,
                    add_outer_ground_pours, add_planes, add_zone, fill_zones)
from .copper import add_chassis_ring, add_track
from .stitching import (PLANE_NETS, add_channel_supply_vias,
                        add_plane_stitching, stitch_pour_islands)
from .connections import (close_open_connections, drop_dangling_vias,
                          obstacles)

__all__ = [
    "BARRIER_AREAS", "BLOCK_PITCH", "BLOCK_W", "BLOCK_X0", "BOARD_DATE",
    "BOARD_FILE", "BOARD_H", "BOARD_NAME", "BOARD_REV", "BOARD_W",
    "CHANNEL_TEMPLATE", "CONTROL_LOWER_Y", "CONTROL_OUTLINE",
    "CONTROL_SPLIT_X", "CONTROL_X0", "CONTROL_X1", "FIDUCIALS", "FP_ROOT",
    "MOUNTING_HOLES", "OUTER_GROUND_POURS", "PLACEMENTS", "PLANE_NETS",
    "RING_INSET", "RING_WIDTH", "ROOT", "RS485_OUTLINE", "RS485_X0",
    "RS485_Y0", "SENSOR_OUTLINE", "SENSOR_X1", "ZONE_BOTTOM", "ZONE_LEFT",
    "ZONE_TOP",
    "add_board_footprint", "add_chassis_ring", "add_channel_supply_vias",
    "add_keepout", "add_mechanics_and_silkscreen", "add_outer_ground_pours",
    "add_outline", "add_plane_stitching", "add_planes", "add_text",
    "add_track", "add_zone", "bare", "build_placements", "clear_generated",
    "clear_in_place", "close_open_connections", "drop_dangling_vias", "fill_zones",
    "footprint_map", "obstacles", "place_footprints", "place_reference_text",
    "point_in_polygon", "remove_item", "segment_box_distance",
    "segment_distance", "segments_distance", "stitch_pour_islands",
    "to_mm", "v",
]
