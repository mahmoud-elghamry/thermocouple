"""Build the REV A0 circuit as seven readable KiCad schematic sheets.

The existing annotated symbols are the source for symbol graphics and fields;
the Python part table remains the source for electrical pin/net intent.  The
writer uses kiutils, the same parser used by the pinned kicad-tool executable,
because kicad-tool 0.5 has no hierarchy or no-connect edit commands.
"""

from __future__ import annotations

import copy
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from kiutils.items.common import ColorRGBA, Effects, Font, Position, Property, Stroke
from kiutils.items.schitems import Text
from kiutils.schematic import (
    Connection,
    GlobalLabel,
    HierarchicalSheet,
    HierarchicalSheetInstance,
    HierarchicalSheetProjectInstance,
    HierarchicalSheetProjectPath,
    Junction,
    LocalLabel,
    NoConnect,
    Schematic,
    SymbolProjectInstance,
    SymbolProjectPath,
)

GRID = 1.27
PROJECT = "thermocouple_8ch"

SHEETS = {
    "power": "01_power.kicad_sch",
    "controller": "02_controller.kicad_sch",
    "channels_1_4": "03_channels_1_4.kicad_sch",
    "channels_5_8": "04_channels_5_8.kicad_sch",
    "isolation": "05_digital_isolation.kicad_sch",
    "rs485": "06_rs485.kicad_sch",
    "relay": "07_relay_output.kicad_sch",
}

NO_CONNECT_PINS = {
    "U1": ("12", "13"),
    "J2": ("7", "8", "9", "10"),
    "U11": ("11",),
    "U12": ("4",),
    "U13": ("4",),
    **{f"U{channel + 1}": ("6", "7", "13") for channel in range(1, 9)},
}

RAILS = {
    "+24V_RAW", "+24V_FUSED", "+24V_PROT", "+5V_CTRL", "+5V_ISO",
    "+3V3_SENS", "+5V_RS485", "GND_CTRL", "GND_SENS", "GND_RS485",
    "CHASSIS_SHIELD",
}


def uid(name: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"thermo-8ch-readable/{name}"))


def snap(value: float) -> float:
    return round(value / GRID) * GRID


def ref_sheet(ref: str) -> str:
    if ref.startswith("JTC"):
        return "channels_1_4" if int(ref[3:]) <= 4 else "channels_5_8"
    if ref.startswith("U") and ref[1:].isdigit() and 2 <= int(ref[1:]) <= 9:
        return "channels_1_4" if int(ref[1:]) <= 5 else "channels_5_8"
    if ref.startswith("C") and ref[1:].isdigit() and 1 <= int(ref[1:]) <= 40:
        return "channels_1_4" if int(ref[1:]) <= 20 else "channels_5_8"
    if ref.startswith("R") and ref[1:].isdigit():
        number = int(ref[1:])
        if 1 <= number <= 8 or 17 <= number <= 20 or 45 <= number <= 48:
            return "channels_1_4"
        if 9 <= number <= 16 or 21 <= number <= 24 or 49 <= number <= 52:
            return "channels_5_8"
        if 25 <= number <= 27 or 36 <= number <= 43:
            return "isolation"
        if number in (28, 29):
            return "controller"
        if 30 <= number <= 32:
            return "relay"
        if number in (33, 34, 35, 44):
            return "rs485"
    if ref in {"U10", "U11", "C41", "C42", "C43", "C44", "TP5", "TP6"}:
        return "isolation"
    if ref in {"U1", "J2", "J5", "J6", "RV1", "C49", "C50", "C51", "C52", "TP7"} or ref.startswith("SW"):
        return "controller"
    if ref in {"U15", "J4", "JP1", "JP2", "JP3", "D5", "D6", "C56", "C57", "C58", "C59", "TP8", "TP9", "#FLG4"}:
        return "rs485"
    if ref in {"Q1", "K1", "D3", "D4", "J3"}:
        return "relay"
    return "power"


def position_for(ref: str) -> tuple[float, float]:
    sheet = ref_sheet(ref)
    if sheet.startswith("channels"):
        channel = int(ref[3:]) if ref.startswith("JTC") else None
        if channel is None and ref.startswith("U"):
            channel = int(ref[1:]) - 1
        if channel is None and ref.startswith("R"):
            n = int(ref[1:])
            channel = (n + 1) // 2 if n <= 16 else (n - 16 if n <= 24 else n - 44)
        if channel is None and ref.startswith("C"):
            channel = (int(ref[1:]) - 1) // 5 + 1
        row = (channel - 1) % 4
        y = 38.10 + row * 43.18
        if ref.startswith("JTC"):
            return 25.40, y
        if ref.startswith("U"):
            return 119.38, y
        if ref.startswith("R"):
            n = int(ref[1:])
            if n <= 16:
                return 50.80, y + (-2.54 if n % 2 else 2.54)
            if n <= 24:
                return 149.86, y - 7.62
            return 154.94, y + 5.08
        index = (int(ref[1:]) - 1) % 5
        return ((76.20, y), (88.90, y - 3.81), (88.90, y + 3.81),
                (111.76, y - 22.86), (127.00, y - 22.86))[index]

    positions = {
        "power": {
            "J1": (25.40, 48.26), "F1": (50.80, 45.72), "D1": (76.20, 45.72),
            "D2": (88.90, 63.50), "U14": (114.30, 45.72), "C53": (91.44, 78.74),
            "C54": (101.60, 78.74), "C55": (132.08, 78.74), "U12": (71.12, 127.00),
            "C45": (43.18, 127.00), "C46": (99.06, 127.00), "U13": (137.16, 127.00),
            "C47": (119.38, 149.86), "C48": (157.48, 149.86),
            "TP1": (187.96, 50.80), "TP2": (203.20, 50.80), "TP3": (218.44, 50.80),
            "TP4": (233.68, 50.80), "#FLG1": (187.96, 76.20),
            "#FLG2": (203.20, 76.20), "#FLG3": (218.44, 76.20),
        },
        "controller": {
            "U1": (60.96, 106.68), "C49": (30.48, 30.48), "C50": (40.64, 30.48),
            "C51": (50.80, 30.48), "C52": (60.96, 30.48), "R28": (73.66, 30.48),
            "J2": (154.94, 63.50), "RV1": (190.50, 63.50), "R29": (177.80, 35.56),
            "J5": (149.86, 121.92), "J6": (190.50, 121.92), "TP7": (101.60, 30.48),
            "SW1": (139.70, 172.72), "SW2": (157.48, 172.72), "SW3": (175.26, 172.72),
            "SW4": (193.04, 172.72), "SW5": (210.82, 172.72),
        },
        "isolation": {
            "U10": (91.44, 63.50), "U11": (91.44, 137.16),
            "C41": (68.58, 30.48), "C42": (114.30, 30.48),
            "C43": (68.58, 170.18), "C44": (114.30, 170.18),
            "R25": (129.54, 55.88), "R26": (129.54, 68.58), "R27": (129.54, 139.70),
            "TP5": (175.26, 55.88), "TP6": (175.26, 139.70),
            **{f"R{35+i}": (165.10, 78.74 + i * 8.89) for i in range(1, 9)},
        },
        "rs485": {
            "U15": (101.60, 101.60), "R33": (63.50, 91.44),
            "C56": (73.66, 58.42), "C57": (86.36, 58.42),
            "C58": (116.84, 58.42), "C59": (129.54, 58.42),
            "JP1": (165.10, 76.20), "R34": (198.12, 76.20),
            "JP2": (165.10, 101.60), "R35": (198.12, 101.60),
            "JP3": (165.10, 127.00), "R44": (198.12, 127.00),
            "D5": (218.44, 91.44), "D6": (218.44, 116.84),
            "J4": (251.46, 101.60), "TP8": (165.10, 154.94),
            "TP9": (198.12, 154.94), "#FLG4": (231.14, 154.94),
        },
        "relay": {
            "R30": (63.50, 101.60), "Q1": (99.06, 101.60), "R31": (83.82, 127.00),
            "K1": (149.86, 91.44), "D3": (149.86, 121.92),
            "R32": (182.88, 121.92), "D4": (213.36, 121.92), "J3": (251.46, 91.44),
        },
    }
    return positions[sheet][ref]


def save(schematic: Schematic, path: Path) -> None:
    schematic.version = "20250114"
    schematic.generator = "eeschema"
    schematic.generatorVersion = "10.0"
    text = schematic.to_sexpr()
    text = re.sub(r"\(uuid ([0-9a-f-]{36})\)", r'(uuid "\1")', text)
    path.write_text(text, encoding="utf-8")


def source_data(root: Path, tool: Path):
    candidates = [root / "thermocouple_8ch.kicad_sch", *(root / name for name in SHEETS.values())]
    sources = []
    symbols = {}
    symbol_source = {}
    lib_symbols = {}
    for path in candidates:
        if not path.exists():
            continue
        schematic = Schematic.from_file(path)
        sources.append(schematic)
        for symbol in schematic.schematicSymbols:
            ref = next((p.value for p in symbol.properties if p.key == "Reference"), "")
            if ref and ref not in symbols:
                symbols[ref] = symbol
                symbol_source[ref] = path
        for symbol in schematic.libSymbols:
            lib_symbols[(symbol.libraryNickname, symbol.entryName)] = symbol
    if not symbols:
        raise RuntimeError("No annotated source symbols found; restore the generated schematic or child sheets")

    offsets = {}
    representatives = {}
    for ref, symbol in symbols.items():
        representatives.setdefault((symbol.libraryNickname, symbol.entryName, symbol.position.angle or 0), ref)
    for key, ref in representatives.items():
        result = subprocess.run(
            [str(tool), "sch", "query", "symbol", str(symbol_source[ref]), ref, "--format", "json"],
            check=True, capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        data = json.loads(result.stdout)
        offsets[key] = {
            pin["number"]: (
                snap(pin["absolute"]["x"] - data["at"]["x"]),
                snap(pin["absolute"]["y"] - data["at"]["y"]),
                snap(pin["absolute"]["x"] - pin["endpoint_absolute"]["x"]),
                snap(pin["absolute"]["y"] - pin["endpoint_absolute"]["y"]),
            )
            for pin in data.get("pins", [])
        }
    return sources[0], symbols, list(lib_symbols.values()), offsets


def wire(points, name, schematic):
    clean = []
    for x, y in points:
        point = (snap(x), snap(y))
        if not clean or point != clean[-1]:
            clean.append(point)
    for index, (a, b) in enumerate(zip(clean, clean[1:])):
        schematic.graphicalItems.append(Connection(
            type="wire", points=[Position(*a), Position(*b)],
            stroke=Stroke(width=0, type="default"), uuid=uid(f"{name}/wire/{index}/{a}/{b}"),
        ))


def add_net(schematic, name, pins, is_global, ordinal):
    points = [(p[0], p[1]) for p in pins]
    if len(points) == 1:
        x, y = points[0]
        dx, dy = pins[0][2], pins[0][3]
        if dx == dy == 0:
            dx = GRID
        end = (x + (5.08 if dx >= 0 else -5.08) if dx else x,
               y + (5.08 if dy >= 0 else -5.08) if dy else y)
        wire([(x, y), end], name, schematic)
        anchor = end
    elif len(points) == 2:
        a, b = points
        if a[0] == b[0] or a[1] == b[1]:
            wire([a, b], name, schematic)
        else:
            lane = snap((a[0] + b[0]) / 2)
            wire([a, (lane, a[1]), (lane, b[1]), b], name, schematic)
        anchor = a
    else:
        right = max(x for x, _ in points)
        lane = snap(min(279.40, right + 5.08 + (ordinal % 7) * 2.54))
        ys = [y for _, y in points]
        for index, point in enumerate(points):
            wire([point, (lane, point[1])], f"{name}/tap/{index}", schematic)
            schematic.junctions.append(Junction(position=Position(lane, point[1]), diameter=0,
                                                  uuid=uid(f"{name}/junction/{index}/{point[1]}")))
        wire([(lane, min(ys)), (lane, max(ys))], f"{name}/trunk", schematic)
        anchor = (lane, min(ys))

    effects = Effects(font=Font(height=1.27, width=1.27))
    if is_global:
        schematic.globalLabels.append(GlobalLabel(text=name, shape="bidirectional",
                                                   position=Position(*anchor), effects=effects,
                                                   uuid=uid(f"{name}/global-label")))
    else:
        schematic.labels.append(LocalLabel(text=name, position=Position(*anchor), effects=effects,
                                           uuid=uid(f"{name}/local-label")))


def make_sheet(template, lib_symbols, sheet_name, refs, parts_by_ref, symbols, offsets, root_uuid, sheet_uuid, cross_nets):
    schematic = Schematic.create_new()
    schematic.uuid = uid(f"child/{sheet_name}")
    schematic.paper = copy.deepcopy(template.paper)
    schematic.titleBlock = copy.deepcopy(template.titleBlock)
    schematic.libSymbols = copy.deepcopy(lib_symbols)
    schematic.sheetInstances = [HierarchicalSheetInstance(instancePath="/", page="1")]
    endpoints = defaultdict(list)

    for ref in sorted(refs):
        part = parts_by_ref[ref]
        symbol = copy.deepcopy(symbols[ref])
        old_x, old_y = symbol.position.X, symbol.position.Y
        new_x, new_y = position_for(ref)
        dx, dy = new_x - old_x, new_y - old_y
        symbol.position.X, symbol.position.Y = new_x, new_y
        for prop in symbol.properties:
            prop.position.X = snap(prop.position.X + dx)
            prop.position.Y = snap(prop.position.Y + dy)
        symbol.instances = [SymbolProjectInstance(
            name=PROJECT,
            paths=[SymbolProjectPath(sheetInstancePath=f"/{root_uuid}/{sheet_uuid}", reference=ref, unit=symbol.unit)],
        )]
        schematic.schematicSymbols.append(symbol)
        key = (symbol.libraryNickname, symbol.entryName, symbol.position.angle or 0)
        for pin, net in part.nets.items():
            if pin in NO_CONNECT_PINS.get(ref, ()):
                continue
            ox, oy, vx, vy = offsets[key][pin]
            endpoints[net].append((snap(new_x + ox), snap(new_y + oy), vx, vy, ref, pin))
        for pin in NO_CONNECT_PINS.get(ref, ()):
            ox, oy, _, _ = offsets[key][pin]
            point = (snap(new_x + ox), snap(new_y + oy))
            schematic.noConnects.append(NoConnect(position=Position(*point), uuid=uid(f"{ref}.{pin}/nc")))

    for ordinal, (net, pins) in enumerate(sorted(endpoints.items())):
        add_net(schematic, net, pins, net in cross_nets or net in RAILS, ordinal)

    schematic.texts.append(Text(
        text=sheet_name.replace("_", " ").upper(), position=Position(20.32, 17.78),
        effects=Effects(font=Font(height=2.54, width=2.54, bold=True)), uuid=uid(f"{sheet_name}/title"),
    ))
    return schematic


def build(parts, root: Path, tool: Path) -> None:
    template, symbols, lib_symbols, offsets = source_data(root, tool)
    parts_by_ref = {part.ref: part for part in parts}
    missing = sorted(set(parts_by_ref) - set(symbols))
    if missing:
        raise RuntimeError(f"Source schematic is missing symbols: {', '.join(missing)}")

    grouped = defaultdict(set)
    net_sheets = defaultdict(set)
    for part in parts:
        sheet = ref_sheet(part.ref)
        grouped[sheet].add(part.ref)
        for pin, net in part.nets.items():
            if pin not in NO_CONNECT_PINS.get(part.ref, ()):
                net_sheets[net].add(sheet)
    cross_nets = {net for net, sheets in net_sheets.items() if len(sheets) > 1}

    root_uuid = template.uuid or uid("root")
    sheet_uuids = {name: uid(f"sheet/{name}") for name in SHEETS}
    for name, filename in SHEETS.items():
        child = make_sheet(template, lib_symbols, name, grouped[name], parts_by_ref, symbols, offsets,
                           root_uuid, sheet_uuids[name], cross_nets)
        save(child, root / filename)

    top = Schematic.create_new()
    top.uuid = root_uuid
    top.paper = copy.deepcopy(template.paper)
    top.titleBlock = copy.deepcopy(template.titleBlock)
    top.libSymbols = copy.deepcopy(lib_symbols)
    top.sheetInstances = [HierarchicalSheetInstance(instancePath="/", page="1")]
    for index, (name, filename) in enumerate(SHEETS.items(), start=2):
        col, row = (index - 2) % 3, (index - 2) // 3
        x, y = 20.32 + col * 88.90, 30.48 + row * 55.88
        suuid = sheet_uuids[name]
        top.sheets.append(HierarchicalSheet(
            position=Position(x, y), width=76.20, height=30.48,
            stroke=Stroke(width=0, type="default"), fill=ColorRGBA(), uuid=suuid,
            sheetName=Property(key="Sheetname", value=name.replace("_", " ").title(),
                               position=Position(x + 2.54, y - 1.27),
                               effects=Effects(font=Font(height=1.27, width=1.27))),
            fileName=Property(key="Sheetfile", value=filename,
                              position=Position(x + 2.54, y + 31.75),
                              effects=Effects(font=Font(height=1.27, width=1.27))),
            instances=[HierarchicalSheetProjectInstance(
                name=PROJECT,
                paths=[HierarchicalSheetProjectPath(sheetInstancePath=f"/{root_uuid}/{suuid}", page=str(index))],
            )],
        ))
    save(top, root / "thermocouple_8ch.kicad_sch")
    print(f"Generated {len(SHEETS)} child sheets with {len(parts)} symbols")
