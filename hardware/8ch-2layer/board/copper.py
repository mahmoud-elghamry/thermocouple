"""Tracks this project draws itself, rather than leaving to the router."""

from __future__ import annotations

import pcbnew

from .config import BOARD_H, BOARD_W, RING_INSET, RING_WIDTH
from .placement import MOUNTING_HOLES, footprint_map
from .units import bare, to_mm, v


def add_track(board: pcbnew.BOARD, net: pcbnew.NETINFO_ITEM,
              a: tuple[float, float], b: tuple[float, float],
              layer: int, width: float) -> None:
    if a == b:
        return
    track = pcbnew.PCB_TRACK(board)
    track.SetNet(net)
    track.SetLayer(layer)
    track.SetWidth(pcbnew.FromMM(width))
    track.SetStart(v(*a))
    track.SetEnd(v(*b))
    board.Add(track)


def add_chassis_ring(board: pcbnew.BOARD) -> None:
    """Draw the CHASSIS_SHIELD loop and its stubs on B.Cu.

    CHASSIS_SHIELD reaches ten connector screws spread over the whole board, so
    the autorouter treated it as an ordinary net and gave up on it.  It is not
    an ordinary net: it is the cable-shield / protective-earth reference, and
    the right shape for it is a loop just inside the board edge that also bonds
    the four mounting holes.  Drawing it deterministically here keeps it out of
    the router's way and makes its geometry reviewable.
    """
    net = board.FindNet("/CHASSIS_SHIELD") or board.FindNet("CHASSIS_SHIELD")
    if net is None:
        raise RuntimeError("CHASSIS_SHIELD net is missing from the board")

    lo, hi_x, hi_y = RING_INSET, BOARD_W - RING_INSET, BOARD_H - RING_INSET
    loop = [(lo, lo), (hi_x, lo), (hi_x, hi_y), (lo, hi_y), (lo, lo)]
    for a, b in zip(loop, loop[1:]):
        add_track(board, net, a, b, pcbnew.B_Cu, RING_WIDTH)

    # Stubs from the ring up to every shield screw terminal.
    fps = footprint_map(board)
    for fp in fps.values():
        for pad in fp.Pads():
            if bare(pad.GetNetname()) != "CHASSIS_SHIELD":
                continue
            if fp.GetReference().startswith("H"):
                continue          # mounting holes already sit on the ring path
            px, py = to_mm(pad.GetPosition().x), to_mm(pad.GetPosition().y)
            target_y = lo if py < BOARD_H / 2 else hi_y
            add_track(board, net, (px, py), (px, target_y), pcbnew.B_Cu, RING_WIDTH)

    # Bond the mounting holes to the nearest ring corner run.
    for x, y in MOUNTING_HOLES:
        add_track(board, net, (x, y), (x, lo if y < BOARD_H / 2 else hi_y),
                  pcbnew.B_Cu, RING_WIDTH)
        add_track(board, net, (x, y), (lo if x < BOARD_W / 2 else hi_x, y),
                  pcbnew.B_Cu, RING_WIDTH)
