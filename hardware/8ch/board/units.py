"""Millimetre/internal-unit conversion and net-name normalisation."""

from __future__ import annotations

import pcbnew


def v(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def to_mm(value: int) -> float:
    return pcbnew.ToMM(value)


# Functional schematic sheets (decisions/0021). A net that stays inside one
# of them carries its path, /RELAY_RS485/GND_RS485; the rules here name the
# function, not the sheet. Channel nets keep theirs (/TC1/FILT_P -> TC1/FILT_P)
# because check_board.py tells the channels apart by it.
SHEETS = ("POWER", "MCU", "ISOLATION", "RELAY_RS485")


def bare(name: str) -> str:
    """Net name without the root '/' and without a functional sheet path."""
    s = name.lstrip("/")
    head, _, rest = s.partition("/")
    return rest if head in SHEETS and rest else s


def find_net(board: pcbnew.BOARD, name: str):
    """The board net whose bare name is `name`, wherever its sheet is."""
    net = board.FindNet(name) or board.FindNet("/" + name)
    if net is None:
        info = board.GetNetInfo()
        hits = [n for n in (info.GetNetItem(i) for i in range(info.GetNetCount()))
                if n is not None and bare(n.GetNetname()) == bare(name)]
        if len(hits) > 1:
            raise RuntimeError(f"{name} matches {len(hits)} nets")
        net = hits[0] if hits else None
    return net
