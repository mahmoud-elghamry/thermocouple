"""Loading, clearing and saving the board.

KiCad's SWIG bindings degrade for the rest of the process once anything is
removed from a board, so the clearing pass runs in a child process.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pcbnew


def remove_item(board: pcbnew.BOARD, item) -> None:
    """BOARD.Remove() through SWIG.

    The generated wrapper assigns ``item.thisown`` before handing the pointer
    to C++.  After the first removal the board's other containers start giving
    out bare ``SwigPyObject`` values, so that assignment raises even though the
    underlying removal succeeds.  Swallow it here and re-load the board once
    the clearing pass is finished (see ``clear_generated``).
    """
    try:
        board.Remove(item)
    except AttributeError:
        pass


def clear_in_place(path: Path) -> None:
    """Strip previously generated copper and mechanics from the board file.

    Everything this generator creates - tracks, zones, drawings, mounting holes
    and fiducials - is removed so a re-run is deterministic.  Footprints and
    nets that came from the schematic are left alone.

    Runs as its own process (see ``clear_generated``).
    """
    board = pcbnew.LoadBoard(str(path))
    doomed = list(board.GetTracks())
    doomed += [board.GetArea(index) for index in range(board.GetAreaCount())]
    doomed += list(board.GetDrawings())
    doomed += [fp for fp in board.GetFootprints()
               if fp.GetReference().startswith(("H", "FID"))]
    for item in doomed:
        remove_item(board, item)
    pcbnew.SaveBoard(str(path), board)
    print(f"Cleared {len(doomed)} generated items")


def clear_generated(path: Path) -> pcbnew.BOARD:
    """Clear the board in a child process, then load the clean result.

    KiCad's SWIG bindings degrade for the rest of the interpreter's life once
    anything has been removed from a board: every container accessor starts
    returning bare ``SwigPyObject`` values, even for a freshly loaded board.
    Doing the removal in a separate process is the only way to keep re-runs of
    this generator working; the previous version worked around it by requiring
    a fresh board file from ``init_board.py`` before every run.
    """
    board = pcbnew.LoadBoard(str(path))
    has_generated = (list(board.GetTracks()) or board.GetAreaCount()
                     or list(board.GetDrawings()))
    if not has_generated:
        return board
    del board
    entry = Path(__file__).resolve().parent.parent / "generate_board.py"
    subprocess.run([sys.executable, str(entry), "--clear-only"], check=True)

    board = pcbnew.LoadBoard(str(path))
    left = (len(list(board.GetTracks())), board.GetAreaCount(),
            len(list(board.GetDrawings())))
    if left != (0, 0, 0):
        raise RuntimeError(f"Board not fully cleared: {left[0]} tracks, "
                           f"{left[1]} zones, {left[2]} drawings remain")
    return board
