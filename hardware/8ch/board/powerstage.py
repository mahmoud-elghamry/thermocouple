"""The LM5164 (U14) power stage, laid out here instead of by the autorouter.

I-076: Freerouting put the input capacitors 12 and 19 mm of track from VIN
and ran SW to L1 through 0.2 mm sections.  TI LM5164 section 7.4 asks for the
input capacitors right at VIN/GND, a short, wide SW node and the bootstrap
capacitor at BST/SW.  So the placement (`placement.py`) puts C63/C54 beside
pins 1-2, C62 beside pins 7-8 and L1 in line with pin 8, and this module draws
the high-current copper before routing.  route.py exports these nets as
"protect", so the router connects the rest around them and cannot move them.

    VIN  C54.1 - C63.1 - U14.2          straight, 0.8 mm
    GND  C54.2 - C63.2 - U14.1          0.8 mm, a GND via at each capacitor
    SW   U14.8 - C62.2 - L1.1           straight at pin 8's level, 1.0 mm
    BST  U14.7 - C62.1                  0.4 mm
"""

from __future__ import annotations

import pcbnew

from .copper import add_track
from .units import to_mm, v

# The nets whose pre-route copper route.py marks "protect" in the DSN.
PROTECTED = {"/+24V_PROT", "/GND_CTRL", "/POWER/SW_5V", "/POWER/BST_5V"}


def _pad(board, ref: str, number: str):
    fp = next(f for f in board.GetFootprints() if f.GetReference() == ref)
    pad = next(p for p in fp.Pads() if p.GetNumber() == number)
    pos = pad.GetPosition()
    return (to_mm(pos.x), to_mm(pos.y)), pad.GetNetname()


def _via(board, net, x: float, y: float) -> None:
    via = pcbnew.PCB_VIA(board)
    via.SetNet(net)
    via.SetPosition(v(x, y))
    via.SetWidth(pcbnew.FromMM(0.6))
    via.SetDrill(pcbnew.FromMM(0.3))
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(via)


def add_power_stage_copper(board: pcbnew.BOARD) -> int:
    f = pcbnew.F_Cu
    net = lambda name: board.FindNet(name)
    c54v, vin = _pad(board, "C54", "1")
    c63v, _ = _pad(board, "C63", "1")
    u2, _ = _pad(board, "U14", "2")
    c54g, gnd = _pad(board, "C54", "2")
    c63g, _ = _pad(board, "C63", "2")
    u1, _ = _pad(board, "U14", "1")
    u8, sw = _pad(board, "U14", "8")
    u7, bst = _pad(board, "U14", "7")
    c62b, _ = _pad(board, "C62", "1")
    l1, _ = _pad(board, "L1", "1")
    # VIN must be one straight line; SW ends inside L1's 3.6 mm-tall pad.
    if abs(c54v[1] - u2[1]) > 0.05 or abs(c63v[1] - u2[1]) > 0.05:
        raise RuntimeError("VIN pads are not in line; re-check placement.py")
    if abs(l1[1] - u8[1]) > 1.3:
        raise RuntimeError("U14.8 is not level with L1's SW pad; re-check placement.py")
    vin_n, gnd_n = net(vin), net(gnd)
    sw_n, bst_n = net(sw), net(bst)
    if not (vin_n and gnd_n and sw_n and bst_n):
        raise RuntimeError("power-stage net missing")
    segments = 0
    for a, b in ((c54v, c63v), (c63v, u2)):
        add_track(board, vin_n, a, b, f, 0.8); segments += 1
    corner = (u1[0] - 1.5, c63g[1])
    for a, b in ((c54g, c63g), (c63g, corner), (corner, u1)):
        add_track(board, gnd_n, a, b, f, 0.8); segments += 1
    for pad in (c54g, c63g):
        spot = (pad[0], pad[1] - 1.5)
        add_track(board, gnd_n, pad, spot, f, 0.8); segments += 1
        _via(board, gnd_n, *spot)
    add_track(board, sw_n, u8, (l1[0], u8[1]), f, 1.0); segments += 1
    knee = (c62b[0], u7[1])
    add_track(board, bst_n, u7, knee, f, 0.4)
    add_track(board, bst_n, knee, c62b, f, 0.4); segments += 2
    return segments
