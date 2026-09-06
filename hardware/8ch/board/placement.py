"""Where every part sits, and putting them there."""

from __future__ import annotations

import pcbnew

from .config import (BLOCK_PITCH, BLOCK_W, BLOCK_X0, BOARD_H, BOARD_W,
                     CHANNEL_TEMPLATE, FP_ROOT, RING_INSET)
from .units import v


def build_placements() -> dict[str, tuple[float, float, float]]:
    placements: dict[str, tuple[float, float, float]] = {}

    def put(ref: str, x: float, y: float, rotation: float = 0.0) -> None:
        if ref in placements:
            raise RuntimeError(f"Duplicate placement for {ref}")
        placements[ref] = (x, y, rotation)

    # --- eight measurement channels ---------------------------------------
    # Channels 1-4 enter from the top edge, 5-8 from the bottom.  A bottom
    # channel is the top block rotated 180 deg about the middle of the board,
    # so the terminal opening still faces outwards.
    for channel in range(1, 9):
        slot = (channel - 1) % 4
        x0 = BLOCK_X0 + slot * BLOCK_PITCH
        top = channel <= 4
        refs = {
            "JTC": f"JTC{channel}",
            "U": f"U{channel + 1}",
            "R_p": f"R{2 * channel - 1}",
            "R_n": f"R{2 * channel}",
            "C_diff": f"C{5 * channel - 4}",
            "C_cm_p": f"C{5 * channel - 3}",
            "C_cm_n": f"C{5 * channel - 2}",
            "C_avdd": f"C{5 * channel - 1}",
            "C_dvdd": f"C{5 * channel}",
            "R_cs": f"R{16 + channel}",
            "R_miso": f"R{44 + channel}",
        }
        for key, (dx, dy, rot) in CHANNEL_TEMPLATE.items():
            if top:
                put(refs[key], x0 + dx, dy, rot)
            else:
                put(refs[key], x0 + BLOCK_W - dx, BOARD_H - dy, (rot + 180) % 360)

    # --- shared sensor-island infrastructure ------------------------------
    # U10/U11 straddle the barrier: pads 1-8 land in the control island, pads
    # 9-16 in the sensor island, 7.25 mm apart across the package body.
    put("U10", 148.0, 40.0, 180)     # ISO7760, 6 forward channels
    put("U11", 148.0, 72.0, 180)     # ISO7761, 5 forward + MISO reverse
    # Series resistors on the sensor side of each isolator, ordered to match
    # the pad order so the escape fan-out has no crossings.
    for ref, y in (("R39", 30.0), ("R38", 33.0), ("R37", 36.0), ("R36", 39.0),
                   ("R26", 42.0), ("R25", 45.0),
                   ("R27", 63.0), ("R43", 66.0), ("R42", 69.0),
                   ("R41", 72.0), ("R40", 75.0)):
        put(ref, 136.0, y, 0)
    put("C42", 140.0, 31.0)          # +3V3_SENS at U10 pad 16
    put("C44", 140.0, 63.0)          # +3V3_SENS at U11 pad 16
    put("C41", 156.5, 41.5)          # +5V_CTRL at U10 pad 1
    put("C43", 156.5, 82.0)          # +5V_CTRL at U11 pad 1
    put("C45", 156.5, 45.5)          # 10u bulk on the control side

    # Isolated supply for the sensor island.  U12 is rotated 90 deg so its pin
    # row runs across the barrier: +Vin/-Vin stay in the control island and
    # 0V/+Vout reach into the sensor island.
    put("U12", 154.5, 100.0, 270)    # IA0505S isolated DC-DC
    put("U13", 134.0, 100.0, 0)      # AP2112K-3.3 LDO
    put("C46", 134.0, 105.0)
    put("C47", 129.0, 105.0)
    put("C48", 129.0, 100.9)
    for ref, x in (("TP3", 122.0), ("TP4", 127.0), ("TP5", 132.0), ("TP6", 137.0)):
        put(ref, x, 60.0)

    # --- controller, HMI and service headers ------------------------------
    put("J2", 158.0, 9.0, 90)        # 16-way LCD header along the top edge
    put("RV1", 206.0, 10.0, 0)       # contrast
    put("R29", 214.0, 10.0, 0)       # backlight series resistor
    put("U1", 168.0, 60.0, 90)       # ATmega32A in a DIP-40 socket
    put("C49", 190.86, 65.0)         # VCC pin 10
    put("C50", 193.40, 40.0)         # VCC pin 30
    put("C51", 188.32, 40.0)         # AREF pin 32
    put("C52", 185.0, 65.0)          # RESET noise immunity (H-11)
    put("R28", 181.0, 65.0)          # RESET pull-up
    put("TP7", 177.0, 65.0)
    put("J5", 158.0, 68.0, 0)        # AVR ISP
    put("J6", 166.0, 68.0, 0)        # expansion / spare port
    put("TP1", 178.0, 72.0)
    put("TP2", 183.0, 72.0)
    for index, y in enumerate((12.0, 23.0, 34.0, 45.0, 56.0), start=1):
        put(f"SW{index}", 236.0, y, 0)

    # --- protected 24 V input and 5 V rail --------------------------------
    put("J1", 170.0, 131.0, 180)     # pin1 +24V, pin2 GND_CTRL, pin3 chassis
    put("F1", 180.0, 131.0)          # 0.5 A PTC
    put("D1", 187.0, 131.0)          # SS34 reverse-polarity series diode
    put("D2", 195.0, 131.0)          # SMBJ33A transient clamp
    put("C53", 178.0, 122.0)         # 47u bulk
    put("C54", 186.0, 122.0)
    put("C55", 191.0, 122.0)
    put("U14", 197.0, 122.0, 0)      # TSR 1-2450 buck module

    # --- energised-to-run relay -------------------------------------------
    put("R30", 196.0, 96.0)          # gate stopper from RUN_PERMIT
    put("R31", 196.0, 101.0)         # gate pull-down: de-energised by default
    put("Q1", 202.0, 98.0, 0)        # 2N7000 low-side switch
    put("R32", 190.0, 101.0)         # run-permit LED series resistor
    put("D4", 190.0, 96.0)           # run-permit LED
    put("D3", 212.0, 86.0, 90)       # 1N4007 coil flyback clamp
    put("K1", 225.0, 65.0, 0)        # G5LE-1 24 V, energised to allow run
    put("J3", 241.0, 79.0, 90)       # dry contact COM/NO/NC

    # --- isolated RS-485 --------------------------------------------------
    # U15 is rotated 270 deg so the isolation barrier inside the package lines
    # up with the barrier on the board: pads 1-10 (GND_CTRL side) sit at
    # y = 105.35 in the control island, pads 11-20 at y = 114.65 in the RS-485
    # island, with the 6 mm copper gap running underneath the package.
    put("U15", 233.0, 96.0, 270)     # ADM2587E, isolated transceiver + supply
    # 1 mm higher than the obvious spot.  These sit in the strip between the
    # relay courtyard and U15, and at y = 88 that strip left only 1 mm of
    # clear board under the row - not enough for the router to bring
    # +5V_CTRL from C57 down to U15 pin 2.  At y = 87 it gets 2 mm.
    put("C56", 232.0, 87.0)          # +5V_CTRL bypass (control side)
    put("C57", 237.0, 87.0)
    put("R33", 242.0, 87.0)          # ties DE and /RE together
    put("C58", 234.0, 110.0)         # +5V_RS485 bypass (isolated side)
    put("C59", 240.0, 110.0)
    put("R34", 216.0, 110.0)         # 120R termination
    put("JP1", 217.0, 116.0, 0)      # termination enable
    put("R35", 222.0, 110.0)         # 680R bias to +5V_RS485
    put("JP2", 223.0, 116.0, 0)
    put("R44", 228.0, 110.0)         # 680R bias to GND_RS485
    put("JP3", 229.0, 116.0, 0)
    put("TP8", 235.0, 116.0)
    put("TP9", 240.0, 116.0)
    put("D6", 220.0, 123.0)          # SMAJ6.0CA on B
    put("D5", 228.0, 123.0)          # SMAJ6.0CA on A
    put("J4", 238.0, 131.0, 180)     # A / B / GND / shield

    return placements


PLACEMENTS = build_placements()

# Mounting holes double as the chassis/PE bond to the panel, so they are
# plated and carry CHASSIS_SHIELD rather than being bare NPTH.
MOUNTING_HOLES = ((RING_INSET + 2.0, RING_INSET + 2.0),
                  (BOARD_W - RING_INSET - 2.0, RING_INSET + 2.0),
                  (RING_INSET + 2.0, BOARD_H - RING_INSET - 2.0),
                  (BOARD_W - RING_INSET - 2.0, BOARD_H - RING_INSET - 2.0))
FIDUCIALS = ((125.0, 3.0), (200.0, 3.0), (125.0, BOARD_H - 3.0))

def footprint_map(board: pcbnew.BOARD) -> dict[str, pcbnew.FOOTPRINT]:
    return {fp.GetReference(): fp for fp in board.GetFootprints()}


def add_board_footprint(board: pcbnew.BOARD, lib: str, name: str, ref: str,
                        x: float, y: float, net_name: str = "") -> None:
    fp = pcbnew.FootprintLoad(str(FP_ROOT / f"{lib}.pretty"), name)
    if fp is None:
        raise RuntimeError(f"Footprint not found: {lib}:{name}")
    fp.SetReference(ref)
    fp.SetValue(ref)
    fp.SetPosition(v(x, y))
    fp.SetBoardOnly(True)
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    board.Add(fp)
    if net_name:
        net = board.FindNet(net_name) or board.FindNet("/" + net_name)
        if net is None:
            raise RuntimeError(f"Net absent for {ref}: {net_name}")
        for pad in fp.Pads():
            pad.SetNet(net)


def place_footprints(board: pcbnew.BOARD) -> None:
    fps = footprint_map(board)
    missing = sorted(set(fps) - set(PLACEMENTS))
    if missing:
        raise RuntimeError(f"No placement defined for: {', '.join(missing)}")
    unknown = sorted(set(PLACEMENTS) - set(fps))
    if unknown:
        raise RuntimeError(f"Placement for absent parts: {', '.join(unknown)}")
    for ref, (x, y, rotation) in PLACEMENTS.items():
        fp = fps[ref]
        fp.SetPosition(v(x, y))
        fp.SetOrientationDegrees(rotation)
        # H-07: a board without reference designators cannot be assembled or
        # serviced by hand.  Keep them visible; hide the values instead.
        fp.Reference().SetVisible(True)
        fp.Reference().SetTextSize(v(0.8, 0.8))
        fp.Reference().SetTextThickness(pcbnew.FromMM(0.12))
        fp.Value().SetVisible(False)
