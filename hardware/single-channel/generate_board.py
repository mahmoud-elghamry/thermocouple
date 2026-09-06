"""Generate the editable KiCad PCB for the ATmega32/MAX31856 meter.

Run with KiCad's bundled Python, not the system Python:
  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" generate_board.py
"""

from __future__ import annotations

import heapq
import math
from pathlib import Path

import pcbnew


ROOT = Path(__file__).resolve().parent
FP_ROOT = Path(r"C:\Program Files\KiCad\10.0\share\kicad\footprints")
OUT = ROOT / "thermocouple_meter.kicad_pcb"

GRID_MM = 0.5
BOARD_W = 150.0
BOARD_H = 70.0
MARGIN = 1.5
TRACK_MM = 0.25
POWER_TRACK_MM = 0.25
CONTACT_TRACK_MM = 1.00
VIA_MM = 0.60
VIA_DRILL_MM = 0.30


def v(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def mm(value: int) -> float:
    return pcbnew.ToMM(value)


board = pcbnew.BOARD()

def add_footprint(lib: str, name: str, ref: str, value: str,
                  x: float, y: float, rotation: float = 0.0) -> pcbnew.FOOTPRINT:
    fp = pcbnew.FootprintLoad(str(FP_ROOT / f"{lib}.pretty"), name)
    if fp is None:
        raise RuntimeError(f"Footprint not found: {lib}:{name}")
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    fp.SetPosition(v(x, y))
    fp.SetOrientationDegrees(rotation)
    board.Add(fp)
    return fp


footprints: dict[str, pcbnew.FOOTPRINT] = {}


def fp(*args, **kwargs):
    item = add_footprint(*args, **kwargs)
    footprints[item.GetReference()] = item
    return item


# Major parts. The LCD is connected by a 1x16 header so it can be panel mounted.
fp("Package_DIP", "DIP-40_W15.24mm", "U1", "ATmega32A-PU", 45, 45, 90)
fp("Package_SO", "TSSOP-14_4.4x5mm_P0.65mm", "U2", "MAX31856MUD+", 22, 26)
fp("Package_TO_SOT_SMD", "SOT-223-3_TabPin2", "U3", "AMS1117-3.3", 24, 57)
fp("Connector_PinHeader_2.54mm", "PinHeader_1x16_P2.54mm_Vertical", "J2", "LCD_16x2", 35, 7, 90)
fp("TerminalBlock_Phoenix", "TerminalBlock_Phoenix_MKDS-1,5-2_1x02_P5.00mm_Horizontal", "J3", "K-TYPE", 6, 25, 90)
fp("TerminalBlock_Phoenix", "TerminalBlock_Phoenix_MKDS-1,5-2_1x02_P5.00mm_Horizontal", "J1", "5V_INPUT", 6, 58, 90)
fp("Connector_PinHeader_2.54mm", "PinHeader_2x03_P2.54mm_Vertical", "J4", "AVR_ISP", 128, 56)
fp("Potentiometer_THT", "Potentiometer_Bourns_3296W_Vertical", "RV1", "10k LCD CONTRAST", 98, 16, 90)

# 100 C alarm output.  PB3 drives both a status LED and a protected 5 V relay.
fp("Relay_THT", "Relay_SPDT_SANYOU_SRD_Series_Form_C", "K1", "SRD-05VDC-SL-C", 112, 38)
fp("TerminalBlock_Phoenix", "TerminalBlock_Phoenix_MKDS-1,5-3_1x03_P5.00mm_Horizontal",
   "J5", "RELAY_COM_NO_NC", 142, 38, 90)
fp("Package_TO_SOT_THT", "TO-92_Inline", "Q1", "2N3904 E-B-C", 102, 54)
fp("Diode_THT", "D_DO-41_SOD81_P7.62mm_Horizontal", "D1", "1N4007 FLYBACK", 109, 49)
fp("LED_THT", "LED_D5.0mm_Clear", "D2", "ALARM LED", 116, 62)

# Input filter and supply decoupling.
res_fp = ("Resistor_SMD", "R_0805_2012Metric")
cap_fp = ("Capacitor_SMD", "C_0805_2012Metric")
cap_big_fp = ("Capacitor_SMD", "C_1210_3225Metric")

fp(*res_fp, "R1", "100R 0.1%", 13.5, 23.5)
fp(*res_fp, "R2", "100R 0.1%", 13.5, 27.5)
fp(*res_fp, "R3", "10k RESET", 65, 50)
fp(*res_fp, "R7", "100R LCD LED", 80, 9)
fp(*res_fp, "R4", "1k RELAY BASE", 96, 54)
fp(*res_fp, "R5", "10k BASE PULLDOWN", 99, 60)
fp(*res_fp, "R6", "1k ALARM LED", 108, 62)

fp(*cap_big_fp, "C1", "10uF 10V", 15, 56)
fp(*cap_big_fp, "C2", "10uF 10V", 33, 56)
fp(*cap_fp, "C3", "100nF MCU VCC", 76, 50)
fp(*cap_fp, "C4", "100nF MCU AVCC", 71, 24)
fp(*cap_fp, "C5", "100nF MAX AVDD", 17.5, 33)
fp(*cap_fp, "C6", "100nF MAX DVDD", 26.5, 33)
fp(*cap_fp, "C7", "100nF TC DIFF", 15.5, 31)
fp(*cap_fp, "C8", "10nF TC+", 11, 35)
fp(*cap_fp, "C9", "10nF TC-", 20, 36)
fp(*cap_fp, "C10", "100nF AREF", 65, 24)

fp("TestPoint", "TestPoint_THTPad_D2.0mm_Drill1.0mm", "TP1", "DRDY", 31, 20)
fp("TestPoint", "TestPoint_THTPad_D2.0mm_Drill1.0mm", "TP2", "FAULT", 31, 23)


def pad(ref: str, number: str) -> pcbnew.PAD:
    item = footprints[ref].FindPadByNumber(str(number))
    if item is None:
        raise RuntimeError(f"Missing pad {ref}.{number}")
    return item


net_endpoints: dict[str, list[tuple[str, str]]] = {
    "GND": [
        ("J1", "2"), ("J2", "1"), ("J2", "5"), ("J2", "16"), ("J4", "6"),
        ("U1", "11"), ("U1", "31"), ("U2", "1"), ("U2", "14"), ("U3", "1"),
        ("C1", "2"), ("C2", "2"), ("C3", "2"), ("C4", "2"), ("C5", "2"),
        ("C6", "2"), ("C8", "2"), ("C9", "2"), ("C10", "2"), ("RV1", "1"),
        ("Q1", "1"), ("R5", "2"), ("D2", "1"),
    ],
    "+5V": [
        ("J1", "1"), ("U3", "3"), ("C1", "1"), ("J2", "2"),
        ("RV1", "3"), ("R7", "1"), ("K1", "2"), ("D1", "1"),
    ],
    "+3V3": [
        ("U3", "2"), ("C2", "1"), ("U1", "10"), ("U1", "30"),
        ("U2", "5"), ("U2", "8"), ("C3", "1"), ("C4", "1"), ("C5", "1"),
        ("C6", "1"), ("R3", "1"), ("J4", "2"),
    ],
    "RESET": [("U1", "9"), ("R3", "2"), ("J4", "5")],
    "SPI_CS": [("U1", "5"), ("U2", "9")],
    "SPI_MOSI": [("U1", "6"), ("U2", "12"), ("J4", "4")],
    "SPI_MISO": [("U1", "7"), ("U2", "11"), ("J4", "1")],
    "SPI_SCK": [("U1", "8"), ("U2", "10"), ("J4", "3")],
    "MAX_DRDY": [("U2", "7"), ("TP1", "1")],
    "MAX_FAULT": [("U2", "13"), ("TP2", "1")],
    "TC_RAW_PLUS": [("J3", "1"), ("R1", "1")],
    "TC_PLUS": [("R1", "2"), ("U2", "4"), ("C7", "1"), ("C8", "1")],
    "TC_RAW_MINUS": [("J3", "2"), ("R2", "1")],
    "TC_MINUS": [("R2", "2"), ("U2", "2"), ("U2", "3"), ("C7", "2"), ("C9", "1")],
    "LCD_VO": [("RV1", "2"), ("J2", "3")],
    "LCD_RS": [("U1", "40"), ("J2", "4")],
    "LCD_E": [("U1", "39"), ("J2", "6")],
    "LCD_D4": [("U1", "36"), ("J2", "11")],
    "LCD_D5": [("U1", "35"), ("J2", "12")],
    "LCD_D6": [("U1", "34"), ("J2", "13")],
    "LCD_D7": [("U1", "33"), ("J2", "14")],
    "LCD_LED_A": [("R7", "2"), ("J2", "15")],
    "AREF": [("U1", "32"), ("C10", "1")],
    "ALARM_GPIO": [("U1", "4"), ("R4", "1"), ("R6", "1")],
    "ALARM_BASE": [("R4", "2"), ("R5", "1"), ("Q1", "2")],
    "RELAY_LOW": [("Q1", "3"), ("K1", "5"), ("D1", "2")],
    "ALARM_LED_A": [("R6", "2"), ("D2", "2")],
    "RELAY_COM": [("K1", "1"), ("J5", "1")],
    "RELAY_NO": [("K1", "3"), ("J5", "2")],
    "RELAY_NC": [("K1", "4"), ("J5", "3")],
}

nets: dict[str, pcbnew.NETINFO_ITEM] = {}
for name, endpoints in net_endpoints.items():
    net = pcbnew.NETINFO_ITEM(board, name)
    board.Add(net)
    nets[name] = net
    for ref, number in endpoints:
        pad(ref, number).SetNet(net)


# Board outline.
outline_points = [(0, 0), (BOARD_W, 0), (BOARD_W, BOARD_H), (0, BOARD_H), (0, 0)]
for a, b in zip(outline_points, outline_points[1:]):
    shape = pcbnew.PCB_SHAPE(board)
    shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
    shape.SetLayer(pcbnew.Edge_Cuts)
    shape.SetStart(v(*a))
    shape.SetEnd(v(*b))
    shape.SetWidth(pcbnew.FromMM(0.1))
    board.Add(shape)


# Four mounting holes.
for index, (x, y) in enumerate(((4, 4), (146, 4), (4, 66), (146, 66)), start=1):
    fp("MountingHole", "MountingHole_3.2mm_M3", f"H{index}", "M3", x, y)

# Three global fiducials improve optical alignment when the SMD parts are
# assembled by pick-and-place.  They are deliberately spread across the board.
for index, (x, y) in enumerate(((10, 8), (140, 8), (140, 62)), start=1):
    fp("Fiducial", "Fiducial_1mm_Mask2mm", f"FID{index}", "FIDUCIAL", x, y)


def add_text(text: str, x: float, y: float, size: float = 1.2, layer=pcbnew.F_SilkS):
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(v(x, y))
    item.SetLayer(layer)
    item.SetTextSize(v(size, size))
    item.SetTextThickness(pcbnew.FromMM(0.18))
    board.Add(item)


add_text("K-TYPE THERMOCOUPLE METER", 78, 66)
add_text("5V REGULATED INPUT", 14, 65, 0.9)
add_text("K-TYPE INPUT", 20, 17, 0.9)
add_text("LCD 16x2", 54, 3, 0.9)
add_text("ALARM >=100C", 113, 67, 0.9)
add_text("COM  NO  NC", 142, 18, 0.8)
add_text("LOW-VOLTAGE LOAD ONLY", 125, 7, 0.8)


# Grid router: two copper layers, orthogonal traces, with vias at layer changes.
nx = int(BOARD_W / GRID_MM) + 1
ny = int(BOARD_H / GRID_MM) + 1
min_cell = int(math.ceil(MARGIN / GRID_MM))
max_x = int(math.floor((BOARD_W - MARGIN) / GRID_MM))
max_y = int(math.floor((BOARD_H - MARGIN) / GRID_MM))


def to_cell(pos: pcbnew.VECTOR2I) -> tuple[int, int]:
    return (round(mm(pos.x) / GRID_MM), round(mm(pos.y) / GRID_MM))


def to_point(cell: tuple[int, int]) -> pcbnew.VECTOR2I:
    return v(cell[0] * GRID_MM, cell[1] * GRID_MM)


def pad_keepout_cells(p: pcbnew.PAD) -> set[tuple[int, int, int]]:
    cells: set[tuple[int, int, int]] = set()
    box = p.GetBoundingBox()
    clearance = 0.34
    x0 = mm(box.GetX()) - clearance
    y0 = mm(box.GetY()) - clearance
    x1 = x0 + mm(box.GetWidth()) + 2 * clearance
    y1 = y0 + mm(box.GetHeight()) + 2 * clearance
    for gx in range(math.floor(x0 / GRID_MM), math.ceil(x1 / GRID_MM) + 1):
        for gy in range(math.floor(y0 / GRID_MM), math.ceil(y1 / GRID_MM) + 1):
            px = gx * GRID_MM
            py = gy * GRID_MM
            if not (x0 <= px <= x1 and y0 <= py <= y1):
                continue
            cells.add((gx, gy, 0))
            cells.add((gx, gy, 1))
    return cells


all_pads = [p for f in footprints.values() for p in f.Pads()]
pad_keepouts = [(p, pad_keepout_cells(p)) for p in all_pads]
via_forbidden_xy = {
    (gx, gy)
    for _, cells in pad_keepouts
    for gx, gy, _ in cells
}

occupied: dict[tuple[int, int, int], str] = {}


def pad_layers(p: pcbnew.PAD) -> list[int]:
    layers = []
    if p.IsOnLayer(pcbnew.F_Cu):
        layers.append(0)
    if p.IsOnLayer(pcbnew.B_Cu):
        layers.append(1)
    return layers or [0]


def pad_route_cell(p: pcbnew.PAD) -> tuple[int, int]:
    """Return a grid point outside an SMD pad for a clean fan-out."""
    pos = p.GetPosition()
    if p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
        return to_cell(pos)

    parent = p.GetParentFootprint()
    center = parent.GetPosition()
    dx = mm(pos.x - center.x)
    dy = mm(pos.y - center.y)
    escape = 1.75
    x = mm(pos.x)
    y = mm(pos.y)
    if abs(dx) >= abs(dy):
        x += escape if dx >= 0 else -escape
    else:
        y += escape if dy >= 0 else -escape
    return (round(x / GRID_MM), round(y / GRID_MM))


def route_one(net_name: str, start_pad: pcbnew.PAD,
              tree: set[tuple[int, int, int]], blocked_other: set[tuple[int, int, int]]):
    start_xy = pad_route_cell(start_pad)
    starts = [(start_xy[0], start_xy[1], layer, -1) for layer in pad_layers(start_pad)]
    target_xyz = tree
    target_xy = {(x, y) for x, y, _ in target_xyz}

    def heuristic(x: int, y: int) -> int:
        return min(abs(x - tx) + abs(y - ty) for tx, ty in target_xy)

    queue = []
    best = {}
    parent = {}
    serial = 0
    for state in starts:
        cost = 0
        heapq.heappush(queue, (heuristic(state[0], state[1]), cost, serial, state))
        best[state] = cost
        parent[state] = None
        serial += 1

    goal = None
    moves = ((1, 0, 0), (-1, 0, 1), (0, 1, 2), (0, -1, 3))
    while queue:
        _, cost, _, state = heapq.heappop(queue)
        x, y, layer, direction = state
        if cost != best.get(state):
            continue
        if (x, y, layer) in target_xyz:
            goal = state
            break

        neighbours = []
        for dx, dy, ndir in moves:
            neighbours.append((x + dx, y + dy, layer, ndir, 10 + (2 if direction not in (-1, ndir) else 0)))
        neighbours.append((x, y, 1 - layer, direction, 80))

        for nx_, ny_, nl, ndir, step in neighbours:
            if not (min_cell <= nx_ <= max_x and min_cell <= ny_ <= max_y):
                continue
            xyz = (nx_, ny_, nl)
            if xyz in occupied and occupied[xyz] != net_name:
                continue
            if nl != layer:
                # Do not place an untented via in or immediately beside a pad.
                # This prevents solder wicking on SMD pads and avoids ambiguous
                # via-in-pad fabrication requirements.
                if (nx_, ny_) in via_forbidden_xy:
                    continue
                via_blocked = False
                for check_layer in (0, 1):
                    for check_dx in (-1, 0, 1):
                        for check_dy in (-1, 0, 1):
                            owner = occupied.get((nx_ + check_dx, ny_ + check_dy, check_layer))
                            if owner is not None and owner != net_name:
                                via_blocked = True
                                break
                        if via_blocked:
                            break
                    if via_blocked:
                        break
                if via_blocked:
                    continue
            if xyz in blocked_other:
                continue
            next_state = (nx_, ny_, nl, ndir)
            next_cost = cost + step
            if next_cost < best.get(next_state, 10**12):
                best[next_state] = next_cost
                parent[next_state] = state
                heapq.heappush(queue, (next_cost + heuristic(nx_, ny_) * 10, next_cost, serial, next_state))
                serial += 1

    if goal is None:
        raise RuntimeError(f"Autorouter failed on {net_name} from pad {start_pad.GetNumber()}")

    path = []
    cursor = goal
    while cursor is not None:
        path.append((cursor[0], cursor[1], cursor[2]))
        cursor = parent[cursor]
    path.reverse()
    return path


def add_track(net, a, b, layer, width_mm):
    if a == b:
        return
    item = pcbnew.PCB_TRACK(board)
    item.SetNet(net)
    item.SetLayer(pcbnew.F_Cu if layer == 0 else pcbnew.B_Cu)
    item.SetWidth(pcbnew.FromMM(width_mm))
    item.SetStart(to_point((a[0], a[1])))
    item.SetEnd(to_point((b[0], b[1])))
    board.Add(item)


def add_pad_stub(net, p: pcbnew.PAD, cell: tuple[int, int], width_mm: float):
    if p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
        return
    end = to_point(cell)
    if p.GetPosition() == end:
        return
    item = pcbnew.PCB_TRACK(board)
    item.SetNet(net)
    item.SetLayer(pcbnew.F_Cu)
    item.SetWidth(pcbnew.FromMM(width_mm))
    item.SetStart(p.GetPosition())
    item.SetEnd(end)
    board.Add(item)


def add_via(net, cell):
    point = to_point((cell[0], cell[1]))
    for candidate in all_pads:
        if (candidate.GetNetCode() == net.GetNetCode()
                and candidate.GetAttribute() != pcbnew.PAD_ATTRIB_SMD
                and candidate.GetBoundingBox().Contains(point)):
            return
    item = pcbnew.PCB_VIA(board)
    item.SetNet(net)
    item.SetPosition(point)
    item.SetWidth(pcbnew.FromMM(VIA_MM))
    item.SetDrill(pcbnew.FromMM(VIA_DRILL_MM))
    item.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(item)


route_order = [
    "TC_RAW_PLUS", "TC_RAW_MINUS", "TC_PLUS", "TC_MINUS",
    "RELAY_COM", "RELAY_NO", "RELAY_NC",
    "SPI_SCK", "SPI_MISO", "SPI_MOSI", "SPI_CS", "+3V3", "+5V",
    "LCD_LED_A", "LCD_VO", "MAX_DRDY", "MAX_FAULT", "RESET", "AREF",
    "LCD_RS", "LCD_E", "LCD_D4", "LCD_D5", "LCD_D6", "LCD_D7",
    "ALARM_GPIO", "ALARM_BASE", "RELAY_LOW", "ALARM_LED_A",
    "GND",
]

# Reserve the short fan-out stubs from SMD pads before routing other nets.
for stub_net_name, stub_endpoints in net_endpoints.items():
    for stub_ref, stub_number in stub_endpoints:
        stub_pad = pad(stub_ref, stub_number)
        if stub_pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
            continue
        route_cell = pad_route_cell(stub_pad)
        pad_cell = to_cell(stub_pad.GetPosition())
        x0, y0 = pad_cell
        x1, y1 = route_cell
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for index in range(steps + 1):
            gx = round(x0 + (x1 - x0) * index / steps)
            gy = round(y0 + (y1 - y0) * index / steps)
            occupied.setdefault((gx, gy, 0), stub_net_name)

for net_name in route_order:
    print(f"Routing {net_name}...", flush=True)
    net = nets[net_name]
    endpoints = [pad(ref, num) for ref, num in net_endpoints[net_name]]
    net_code = net.GetNetCode()
    blocked_other: set[tuple[int, int, int]] = set()
    for candidate, cells in pad_keepouts:
        if candidate.GetNetCode() != net_code:
            blocked_other.update(cells)

    first = endpoints[0]
    first_xy = pad_route_cell(first)
    tree = {(first_xy[0], first_xy[1], layer) for layer in pad_layers(first)}
    all_paths = []
    for endpoint in endpoints[1:]:
        path = route_one(net_name, endpoint, tree, blocked_other)
        all_paths.append(path)
        tree.update(path)

    if net_name in ("RELAY_COM", "RELAY_NO", "RELAY_NC"):
        width = CONTACT_TRACK_MM
    elif net_name in ("+5V", "+3V3", "GND"):
        width = POWER_TRACK_MM
    elif net_name == "RELAY_LOW":
        width = 0.50
    else:
        width = TRACK_MM
    for endpoint in endpoints:
        add_pad_stub(net, endpoint, pad_route_cell(endpoint), width)
    for path in all_paths:
        # Exact pad-to-grid endpoint is handled by the first segment naturally because
        # all placed footprints use a 0.05/0.1 mm compatible grid.
        for a, b in zip(path, path[1:]):
            if a[2] != b[2]:
                add_via(net, a)
            else:
                add_track(net, a, b, a[2], width)
        for xyz in path:
            occupied[xyz] = net_name
        for a, b in zip(path, path[1:]):
            if a[2] != b[2]:
                for layer in (0, 1):
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            occupied.setdefault((a[0] + dx, a[1] + dy, layer), net_name)


print("Routing complete; building connectivity...", flush=True)
board.BuildConnectivity()
print("Saving board...", flush=True)
pcbnew.SaveBoard(str(OUT), board)
print(f"Generated {OUT}")
