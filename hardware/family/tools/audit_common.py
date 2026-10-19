"""Read-only audit CLI support; native imports are lazy, reports go to stdout."""
import hashlib
import json
import math
from pathlib import Path


def positive_mm(value):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError('clearance must be finite and positive')
    return value


def selected_board():
    """Use the same --board/--pcb and environment selection as existing tools."""
    from profiles import ACTIVE
    return ACTIVE


def load_board(profile):
    import pcbnew
    path = Path(profile['pcb'])
    if not path.is_file():
        raise ValueError(f'board does not exist: {path}')
    board = pcbnew.LoadBoard(str(path))
    if board is None:
        raise ValueError(f'cannot load board: {path}')
    return board


def identity(item):
    result = {'uuid': item.m_Uuid.AsString(), 'net': item.GetNetname()}
    if hasattr(item, 'GetNumber'):
        result['pad'] = item.GetParentFootprint().GetReference() + '.' + item.GetNumber()
    return result


def emit(profile, result):
    import pcbnew
    path = Path(profile['pcb'])
    result = dict(board=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  kicad=pcbnew.GetBuildVersion(), **result)
    print(json.dumps(result, indent=2, allow_nan=False))


def layers(board, item):
    return tuple(layer for layer in board.GetEnabledLayers().CuStack() if item.IsOnLayer(layer))
