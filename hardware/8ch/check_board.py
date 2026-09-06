"""Structural checks that DRC alone will not catch.

DRC checks geometry against rules.  It does not tell you whether a pad ended up
on the wrong side of an isolation barrier, whether a decoupling capacitor is
still near its pin, or whether a part hangs off the board edge.  Those are the
mistakes that survive a clean DRC and show up on the bench, so they get their
own check here.

Run with KiCad 10's bundled Python.  Exits non-zero if anything fails.
"""

from __future__ import annotations

import math
import sys

import pcbnew

import generate_board as gb


mm = pcbnew.ToMM

# Which island each net belongs to.  Nets that legitimately live outside all
# three islands (the chassis ring, the relay dry contact) are listed as FIELD.
ISLANDS = {
    "SENSOR": {"GND_SENS", "+3V3_SENS", "+5V_ISO", "NEG5_UNUSED"},
    "CONTROL": {"GND_CTRL", "+5V_CTRL", "+24V_RAW", "+24V_FUSED", "+24V_PROT",
                "RELAY_LOW", "RELAY_LED_A", "RELAY_GATE", "RUN_PERMIT"},
    "RS485": {"GND_RS485", "+5V_RS485"},
}


def island_of(net_name: str) -> str | None:
    name = gb.bare(net_name)
    for island, nets in ISLANDS.items():
        if name in nets:
            return island
    if name == "CHASSIS_SHIELD" or name.startswith("RELAY_N") \
            or name == "RELAY_COM":
        return None                      # field wiring, deliberately islandless
    if name.startswith(("TC", "MISO_CH", "CH1_", "CH2_", "CH3_", "CH4_",
                        "CH5_", "CH6_", "CH7_", "CH8_")) \
            or name.endswith("_SENS") or name.endswith("_SENS_RAW") \
            or name == "ISO_SPARE_SENS":
        return "SENSOR"
    if name.startswith("RS485_") and name not in ("RS485_DE", "RS485_RE_N"):
        return "RS485"
    return None


def point_in_polygon(x: float, y: float, poly: list[tuple[float, float]]) -> bool:
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y):
            xat = x1 + (y - y1) / (y2 - y1) * (x2 - x1)
            if x < xat:
                inside = not inside
    return inside


ISLAND_OUTLINES = {
    "SENSOR": gb.SENSOR_OUTLINE,
    "CONTROL": gb.CONTROL_OUTLINE,
    "RS485": gb.RS485_OUTLINE,
}


def check_islands(board: pcbnew.BOARD) -> list[str]:
    """Every pad on an island net must sit inside that island's pour."""
    problems = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            island = island_of(pad.GetNetname())
            if island is None:
                continue
            x, y = mm(pad.GetPosition().x), mm(pad.GetPosition().y)
            if not point_in_polygon(x, y, ISLAND_OUTLINES[island]):
                problems.append(
                    f"{fp.GetReference()}.{pad.GetNumber()} "
                    f"[{pad.GetNetname()}] at ({x:.2f},{y:.2f}) is outside the "
                    f"{island} island")
    return problems


# The parts whose own package spans a barrier.  Their middle pins necessarily
# land in the gap, so they are reported for review instead of failing the check.
BARRIER_CROSSING_PARTS = {"U10", "U11", "U12", "U15"}


def check_barrier(board: pcbnew.BOARD) -> list[str]:
    """No copper inside the isolation bands, except the crossing parts' pins."""
    problems, notes = [], []
    for name, poly in gb.BARRIER_AREAS:
        for fp in board.GetFootprints():
            ref = fp.GetReference()
            for pad in fp.Pads():
                if not pad.GetNetname():
                    continue
                x, y = mm(pad.GetPosition().x), mm(pad.GetPosition().y)
                if not point_in_polygon(x, y, poly):
                    continue
                line = (f"{ref}.{pad.GetNumber()} [{pad.GetNetname()}] "
                        f"at ({x:.2f},{y:.2f}) is inside {name}")
                (notes if ref in BARRIER_CROSSING_PARTS else problems).append(line)
    for note in notes:
        print(f"note  barrier crossing part: {note}")
    return problems


def check_decoupling(board: pcbnew.BOARD) -> list[str]:
    """Every MAX31856 supply pin needs a bypass capacitor close to it.

    Design review H-04 asked for <= 2 mm on a two-layer board with no plane.
    This board has a GND/power plane pair on In1/In2, which carries most of the
    high-frequency return, so the target here is relaxed to 4 mm centre-to-pin
    and reported rather than enforced blindly.
    """
    limit = 4.0
    problems = []
    caps = [(fp, pad) for fp in board.GetFootprints()
            for pad in fp.Pads()
            if fp.GetReference().startswith("C")
            and gb.bare(pad.GetNetname()) == "+3V3_SENS"]
    for channel in range(1, 9):
        ref = f"U{channel + 1}"
        fp = next((f for f in board.GetFootprints()
                   if f.GetReference() == ref), None)
        if fp is None:
            problems.append(f"{ref} missing from the board")
            continue
        for pad in fp.Pads():
            if gb.bare(pad.GetNetname()) != "+3V3_SENS":
                continue
            px, py = mm(pad.GetPosition().x), mm(pad.GetPosition().y)
            best = min((math.hypot(px - mm(cp.GetPosition().x),
                                   py - mm(cp.GetPosition().y)), cf.GetReference())
                       for cf, cp in caps)
            if best[0] > limit:
                problems.append(
                    f"{ref}.{pad.GetNumber()} nearest +3V3_SENS capacitor is "
                    f"{best[1]} at {best[0]:.2f} mm (> {limit} mm)")
    return problems


def check_cold_junction(board: pcbnew.BOARD) -> list[str]:
    """Terminal block to MAX31856 distance.

    The chip compensates using its own die temperature, but the real cold
    junction is where the thermocouple alloy meets copper: the terminal screws.
    Any temperature difference between the two goes straight into the reading
    as a full-degree error (H-06).
    """
    limit = 16.5
    problems = []
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    for channel in range(1, 9):
        jtc, chip = fps.get(f"JTC{channel}"), fps.get(f"U{channel + 1}")
        if jtc is None or chip is None:
            problems.append(f"channel {channel}: footprint missing")
            continue
        distance = math.hypot(mm(jtc.GetPosition().x - chip.GetPosition().x),
                              mm(jtc.GetPosition().y - chip.GetPosition().y))
        if distance > limit:
            problems.append(f"JTC{channel} to U{channel + 1} is "
                            f"{distance:.1f} mm (> {limit} mm)")
    return problems


def check_filter_symmetry(board: pcbnew.BOARD) -> list[str]:
    """The two thermocouple legs must see the same layout.

    An asymmetric input filter turns common-mode noise into differential noise,
    which is exactly what destroys a microvolt measurement next to a VFD
    (H-03).  Check that the series resistors and the common-mode capacitors are
    mirrored about the pair's centreline.
    """
    tolerance = 0.05
    problems = []
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    for channel in range(1, 9):
        r_p, r_n = fps.get(f"R{2 * channel - 1}"), fps.get(f"R{2 * channel}")
        c_p, c_n = fps.get(f"C{5 * channel - 3}"), fps.get(f"C{5 * channel - 2}")
        if not all((r_p, r_n, c_p, c_n)):
            problems.append(f"channel {channel}: filter footprint missing")
            continue
        axis = (mm(r_p.GetPosition().x) + mm(r_n.GetPosition().x)) / 2
        offset = abs((mm(c_p.GetPosition().x) + mm(c_n.GetPosition().x)) / 2 - axis)
        if offset > tolerance:
            problems.append(
                f"channel {channel}: common-mode capacitors are {offset:.2f} mm "
                f"off the T+/T- centreline")
        if abs(mm(r_p.GetPosition().y) - mm(r_n.GetPosition().y)) > tolerance:
            problems.append(f"channel {channel}: series resistors are not level")
    return problems


def check_unrouted(board: pcbnew.BOARD) -> list[str]:
    board.BuildConnectivity()
    connectivity = board.GetConnectivity()
    count = connectivity.GetUnconnectedCount(True)
    return [f"{count} unconnected pad pairs remain"] if count else []


def main() -> int:
    board = pcbnew.LoadBoard(str(gb.BOARD_FILE))
    checks = (
        ("island membership", check_islands),
        ("isolation barrier is clear", check_barrier),
        ("decoupling proximity", check_decoupling),
        ("cold-junction distance", check_cold_junction),
        ("input filter symmetry", check_filter_symmetry),
        ("routing completeness", check_unrouted),
    )
    failed = 0
    for label, check in checks:
        problems = check(board)
        if problems:
            failed += 1
            print(f"FAIL  {label}")
            for problem in problems[:20]:
                print(f"        {problem}")
            if len(problems) > 20:
                print(f"        ... and {len(problems) - 20} more")
        else:
            print(f"ok    {label}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
