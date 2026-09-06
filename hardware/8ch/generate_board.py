"""Place the 8-channel thermocouple board and build its copper structure.

Run with KiCad 10's bundled Python, after the board has been synchronised from
the schematic. This script owns everything that is *not* signal routing:

    placement -> board outline -> mechanics -> silkscreen
              -> isolation keepouts -> chassis/PE ring -> supply vias -> planes

Signal routing is done by ``route.py`` (Specctra DSN -> Freerouting -> SES).
Track widths, via sizes and clearances are not defined here; they live in the
KiCad project, written by ``apply_rules.py``, so anyone opening the project sees
the same rules the generator used.

The implementation lives in the ``board`` package - see ``board/__init__.py``
for what is in which module. This file is the entry point and the stable import
surface for ``route.py``, ``check_board.py`` and ``close_gaps.py``.

Re-running this file is deterministic and discards previous routing.
"""

from __future__ import annotations

import argparse

try:                                    # pragma: no cover - environment guard
    import wx
    # A failed wxWidgets assert inside pcbnew opens a modal dialog, which hangs
    # a headless run until somebody clicks it.  Fail loudly in Python instead.
    wx.DisableAsserts()
except Exception:
    pass

import pcbnew

from board import *                     # noqa: F401,F403 - the public surface
from board import BOARD_FILE, clear_generated, clear_in_place


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear-only", action="store_true",
                        help="internal: strip generated items and exit")
    args = parser.parse_args()

    if args.clear_only:
        clear_in_place(BOARD_FILE)
        return

    board = clear_generated(BOARD_FILE)
    place_footprints(board)
    add_outline(board)
    add_mechanics_and_silkscreen(board)
    moved = place_reference_text(board)
    print(f"Placed {moved} reference designators clear of parts and pads")
    board.SetCopperLayerCount(4)
    add_planes(board)
    add_chassis_ring(board)
    supply_vias = add_channel_supply_vias(board)
    print(f"Placed {supply_vias} fixed supply vias on the measurement channels")
    fill_zones(board)
    pcbnew.SaveBoard(str(BOARD_FILE), board)
    print(f"Generated {BOARD_FILE}")


if __name__ == "__main__":
    main()
