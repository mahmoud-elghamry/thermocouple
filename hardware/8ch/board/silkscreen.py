"""Board outline, mechanics and everything printed on the silkscreen."""

from __future__ import annotations

import pcbnew

from .config import (BLOCK_PITCH, BLOCK_W, BLOCK_X0, BOARD_DATE, BOARD_H,
                     BOARD_NAME, BOARD_REV, BOARD_W, CONTROL_SPLIT_X,
                     CONTROL_X0, RS485_X0, SENSOR_X1)
from .placement import FIDUCIALS, MOUNTING_HOLES, add_board_footprint
from .units import to_mm, v


def footprint_boxes(board: pcbnew.BOARD) -> tuple[list, list]:
    """Courtyard boxes and copper-bearing pad boxes, in mm."""
    courtyards, pads = [], []
    for fp in board.GetFootprints():
        shape = fp.GetCourtyard(pcbnew.F_CrtYd)
        if shape is None or not shape.OutlineCount():
            shape = fp.GetCourtyard(pcbnew.B_CrtYd)
        if shape is not None and shape.OutlineCount():
            box = shape.BBox()
            x0, y0 = to_mm(box.GetX()), to_mm(box.GetY())
            courtyards.append((x0, y0, x0 + to_mm(box.GetWidth()),
                               y0 + to_mm(box.GetHeight())))
        for pad in fp.Pads():
            box = pad.GetBoundingBox()
            x0, y0 = to_mm(box.GetX()), to_mm(box.GetY())
            pads.append((x0, y0, x0 + to_mm(box.GetWidth()),
                         y0 + to_mm(box.GetHeight())))
    return courtyards, pads


def boxes_overlap(a, boxes, margin: float = 0.0) -> bool:
    ax0, ay0, ax1, ay1 = a
    for bx0, by0, bx1, by1 in boxes:
        if (ax0 - margin < bx1 and bx0 < ax1 + margin
                and ay0 - margin < by1 and by0 < ay1 + margin):
            return True
    return False


def _textfootprint_boxes(board: pcbnew.BOARD) -> list[tuple[float, float, float, float]]:
    boxes = []
    for item in board.GetDrawings():
        if not isinstance(item, pcbnew.PCB_TEXT):
            continue
        if item.GetLayer() not in (pcbnew.F_SilkS, pcbnew.B_SilkS):
            continue
        box = item.GetBoundingBox()
        x0, y0 = to_mm(box.GetX()), to_mm(box.GetY())
        boxes.append((x0, y0, x0 + to_mm(box.GetWidth()),
                      y0 + to_mm(box.GetHeight())))
    return boxes


def place_reference_text(board: pcbnew.BOARD) -> int:
    """Move each reference designator somewhere it can actually be read.

    Leaving them at the footprint default produces silkscreen printed on top of
    other parts' outlines and over through-hole pads, which is how a board ends
    up needing the PDF next to it during assembly and rework (H-07 is about
    having them at all; this is about them being usable).

    Candidates are tried in order and the first clear one wins; anything that
    cannot be placed clear is left where it is and shows up in DRC.
    """
    size = 0.8
    courtyards, pads = footprint_boxes(board)
    placed: list[tuple[float, float, float, float]] = _textfootprint_boxes(board)
    moved = 0
    for fp in board.GetFootprints():
        ref = fp.Reference()
        if not ref.IsVisible():
            continue
        text = fp.GetReference()
        half_w = len(text) * size * 0.35
        half_h = size * 0.6
        shape = fp.GetCourtyard(pcbnew.F_CrtYd)
        if shape is None or not shape.OutlineCount():
            shape = fp.GetCourtyard(pcbnew.B_CrtYd)
        box = shape.BBox()
        x0, y0 = to_mm(box.GetX()), to_mm(box.GetY())
        x1, y1 = x0 + to_mm(box.GetWidth()), y0 + to_mm(box.GetHeight())
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

        candidates = []
        for gap in (0.35, 0.9, 1.6, 2.4):
            candidates += [
                (cx, y0 - half_h - gap),
                (cx, y1 + half_h + gap),
                (x0 - half_w - gap, cy),
                (x1 + half_w + gap, cy),
            ]
        for tx, ty in candidates:
            area = (tx - half_w, ty - half_h, tx + half_w, ty + half_h)
            if tx - half_w < 0.5 or tx + half_w > BOARD_W - 0.5:
                continue
            if ty - half_h < 0.5 or ty + half_h > BOARD_H - 0.5:
                continue
            if boxes_overlap(area, courtyards) or boxes_overlap(area, pads, 0.1):
                continue
            if boxes_overlap(area, placed, 0.15):
                continue
            ref.SetPosition(v(tx, ty))
            ref.SetTextAngle(pcbnew.EDA_ANGLE(0, pcbnew.DEGREES_T))
            ref.SetLayer(pcbnew.F_SilkS)
            ref.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
            placed.append(area)
            moved += 1
            break
    return moved


def add_outline(board: pcbnew.BOARD) -> None:
    points = [(0, 0), (BOARD_W, 0), (BOARD_W, BOARD_H), (0, BOARD_H), (0, 0)]
    for a, b in zip(points, points[1:]):
        shape = pcbnew.PCB_SHAPE(board)
        shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
        shape.SetLayer(pcbnew.Edge_Cuts)
        shape.SetStart(v(*a))
        shape.SetEnd(v(*b))
        shape.SetWidth(pcbnew.FromMM(0.1))
        board.Add(shape)


def add_text(board: pcbnew.BOARD, text: str, x: float, y: float,
             size: float = 1.0, layer=pcbnew.F_SilkS, rotation: float = 0.0,
             centre: bool = True) -> None:
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(v(x, y))
    item.SetLayer(layer)
    item.SetTextSize(v(size, size))
    item.SetTextThickness(pcbnew.FromMM(max(0.12, size * 0.15)))
    item.SetTextAngle(pcbnew.EDA_ANGLE(rotation, pcbnew.DEGREES_T))
    if centre:
        item.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    if layer in (pcbnew.B_SilkS, pcbnew.B_Cu):
        item.SetMirrored(True)
    board.Add(item)


def add_mechanics_and_silkscreen(board: pcbnew.BOARD) -> None:
    for index, (x, y) in enumerate(MOUNTING_HOLES, start=1):
        add_board_footprint(board, "MountingHole",
                            "MountingHole_3.2mm_M3_ISO7380_Pad_TopBottom",
                            f"H{index}", x, y, net_name="CHASSIS_SHIELD")
    for index, (x, y) in enumerate(FIDUCIALS, start=1):
        add_board_footprint(board, "Fiducial", "Fiducial_1mm_Mask2mm",
                            f"FID{index}", x, y)

    # Free silkscreen text goes in the empty corridors, not on top of parts.
    # The band y = 45..70 across the sensor island is clear: the top channel
    # blocks end at y = 31.5 and the bottom ones start at y = 108.5.
    add_text(board, "8-CHANNEL K-TYPE PROTECTION CONTROLLER", 70.0, 50.0, 1.6)
    add_text(board, "ENGINEERING PROTOTYPE - NOT FIELD CERTIFIED", 70.0, 53.5, 0.9)
    add_text(board, f"{BOARD_NAME}  REV {BOARD_REV}  {BOARD_DATE}", 70.0, 56.5, 0.9)
    add_text(board, "SHARED ISOLATED SENSOR ISLAND - CHANNELS ARE NOT "
                    "ISOLATED FROM EACH OTHER", 70.0, 60.0, 0.9)
    add_text(board, "THERMOCOUPLE TERMINALS:  1 = T+   2 = T-   3 = SHIELD",
             70.0, 63.0, 0.9)

    # Channel numbers sit in the corridor between blocks, clear of the filter
    # parts.  Putting them under the terminal block collided with the series
    # resistors on every channel.
    for channel in range(1, 9):
        slot = (channel - 1) % 4
        x0 = BLOCK_X0 + slot * BLOCK_PITCH
        top = channel <= 4
        x = x0 + 19.5 if top else x0 + BLOCK_W - 19.5
        add_text(board, f"CH{channel}", x, 7.0 if top else 133.0, 1.2)

    add_text(board, "ISOLATION BARRIER - NO COPPER",
             (SENSOR_X1 + CONTROL_X0) / 2, 56.0, 0.9, rotation=90)
    add_text(board, "ISOLATION BARRIER",
             (CONTROL_SPLIT_X + RS485_X0) / 2, 128.0, 0.8, rotation=90)
    add_text(board, "LCD 16x2  4-BIT", 177.0, 5.0, 0.9)
    add_text(board, "NEXT   UP   DOWN   SET   ACK", 231.0, 40.0, 0.9, rotation=90)
    add_text(board, "24 VDC IN", 170.0, 124.5, 0.9)
    add_text(board, "RUN-PERMIT DRY CONTACT", 227.0, 62.0, 0.9)
    add_text(board, "LOW-VOLTAGE LOAD ONLY", 227.0, 65.0, 0.9)
    add_text(board, "ISOLATED RS-485", 232.0, 138.0, 0.9)
    add_text(board, "CHASSIS / PE RING", 60.0, 138.5, 0.9)
