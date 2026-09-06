"""Millimetre/internal-unit conversion and net-name normalisation."""

from __future__ import annotations

import pcbnew


def v(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def to_mm(value: int) -> float:
    return pcbnew.ToMM(value)


def bare(name: str) -> str:
    """KiCad prefixes root-sheet nets with '/'; compare without it."""
    return name.lstrip("/")
