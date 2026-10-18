"""Place the 2-layer 8-ch board REV B0-2L: the routed 4-layer board (hardware/8ch-new) spread out.

The 4-layer placement is proven (decoupling at its pins, every power/contact path above the LCD header row),
so it is kept and opened up for routing on two layers: every big part (IC, connector, relay, switch, hole) is
an anchor, every small part rides with the anchor it shares the most signal nets with, and only the anchors
move, by SX x SY. Kept rigid: bank A's terminal strip with its channel columns (pitch of the terminals), the
LCD standoffs with J502 (the module's hole pattern), parts on the barrier band (centred on the new band).
Parts near an edge keep their distance to that edge. The 4-layer board is only read.
Run with KiCad's python:  python place.py
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
BOARD = os.environ.get("THERMO8L_BOARD", os.path.join(HW, "thermo8.kicad_pcb"))
SRC = os.path.join(os.path.dirname(HW), "8ch-new", "thermo8.kicad_pcb")
W0, H0 = 130.0, 137.0
W, H = 150.0, 154.0
SX, SY = W / W0, H / H0
BAND0 = 92.5                       # 4-layer band centre (y 91-94)
POWER = {"GND", "GND_ISO", "GND_RS485", "+5V", "+3V3_ISO", "+24V_PROT", "+24V_RAW", "+24V_FUSED", "V_BIAS"}
STRADDLE = {"U401", "U403", "U404"}
LCD = ("H6", "H7", "H8", "H9", "J502")
EDGE = 12.0
T, mm = pcbnew.ToMM, pcbnew.FromMM


def num(ref):
    d = "".join(c for c in ref if c.isdigit())
    return int(d) if d else -1


def is_anchor(fp):
    r = fp.GetReference()
    return r.startswith(("U", "J", "K", "SW", "Y", "L", "F", "H", "RV")) or len(fp.Pads()) >= 5


def nets(fp):
    return {p.GetNetname().rsplit("/", 1)[-1] for p in fp.Pads()} - POWER - {""}


def move(x, y):
    """Anchor position: scaled, but a part near an edge keeps its distance to that edge."""
    nx = x if x < EDGE else (W - (W0 - x) if x > W0 - EDGE else x * SX)
    ny = y if y < EDGE else (H - (H0 - y) if y > H0 - EDGE else y * SY)
    return nx, ny


def main():
    src = pcbnew.LoadBoard(SRC)
    pos = {fp.GetReference(): (T(fp.GetPosition().x), T(fp.GetPosition().y), fp.GetOrientationDegrees())
           for fp in src.GetFootprints()}
    fps = {fp.GetReference(): fp for fp in src.GetFootprints()}
    group = {}
    bank = [r for r in fps if (r[0] in "RDC" and 110 <= num(r) < 190) or r in ("J101", "J102")]
    for r in bank:
        group[r] = "BANK"
    for r in LCD + ("R502",):              # R502: LCD backlight resistor beside J502 pins 15-16
        group[r] = "LCD"
    for r in ("JP731", "JP732", "JP733", "D731", "C733", "C734", "C736", "R734", "R735", "R736"):
        group[r] = "J703"                   # the bus pack under the RS-485 terminal moves with it
    for r in ("R733", "C731", "C732", "C735", "R737", "R738",          # beside standoff H7
              "Q701", "R701", "C704", "D703", "C705", "R702", "D701", "R703", "C703", "R704",
              "Q702", "R711", "R712", "D711", "R713", "C713", "R714"):  # relay drivers: one pack
        group[r] = "LCD"                    # same shift as the LCD group: they keep their spacing
    for r in ("C602", "C603", "TP603", "R605", "R606", "R601", "C604", "L601", "R602", "R603", "C609", "C608",
              "R604", "C605", "C606", "C607", "D603", "TP601", "TP602"):
        group[r] = "U601"                   # the LM5164 stage stays exactly as on the 4-layer (24-ch) board
    anchors = [r for r, fp in fps.items() if r not in group and is_anchor(fp)]
    for r in anchors + ["J703"]:
        group[r] = r
    for r, fp in fps.items():
        if r in group:
            continue
        x, y, _ = pos[r]
        best = None
        for a in anchors:
            ax, ay, _ = pos[a]
            d = math.hypot(ax - x, ay - y)
            if d > 14.0:
                continue
            key = (-len(nets(fp) & nets(fps[a])), d)
            if best is None or key < best[0]:
                best = (key, a)
        group[r] = best[1] if best else r
    # group displacement
    shift = {}
    for g in set(group.values()):
        members = [r for r, gg in group.items() if gg == g]
        if g == "BANK":
            shift[g] = (W / 2 - W0 / 2, H - H0)                     # centred, same distance to the bottom edge
        elif g == "LCD":
            cx = sum(pos[r][0] for r in LCD[:4]) / 4
            cy = sum(pos[r][1] for r in LCD[:4]) / 4
            shift[g] = (cx * SX - cx, cy * SY - cy)
        elif g in STRADDLE:
            x, y, _ = pos[g]
            shift[g] = (x * SX - x, BAND0 * SY - BAND0)            # stays centred on the band
        else:
            x, y, _ = pos[g]
            nx, ny = move(x, y)
            shift[g] = (nx - x, ny - y)
    shift["U601"] = (shift["U601"][0], shift["U601"][1] + 2.5)   # clear of the relay-driver pack above it
    b = pcbnew.LoadBoard(BOARD)
    n = 0
    for fp in b.GetFootprints():
        r = fp.GetReference()
        if r not in pos:
            print("not on the 4-layer board:", r)
            continue
        x, y, rot = pos[r]
        dx, dy = shift[group[r]]
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(pcbnew.VECTOR2I(mm(x + dx), mm(y + dy)))
        n += 1
    pcbnew.SaveBoard(BOARD, b)
    print(f"placed {n}; groups {len(shift)}")
    overlaps(b)


def overlaps(b):
    boxes = []
    for fp in b.GetFootprints():
        cy = fp.GetCourtyard(pcbnew.F_CrtYd)
        if not cy.OutlineCount():
            continue
        bb = cy.BBox()
        boxes.append((fp.GetReference(), T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())))
    k = 0
    for i, a in enumerate(boxes):
        for c in boxes[i + 1:]:
            if a[1] < c[3] - 0.01 and c[1] < a[3] - 0.01 and a[2] < c[4] - 0.01 and c[2] < a[4] - 0.01:
                k += 1
                print(f"OVERLAP {a[0]} {c[0]}")
        if a[1] < -0.01 or a[2] < -0.01 or a[3] > W + 0.01 or a[4] > H + 0.01:
            print(f"OFF-BOARD {a[0]}")
    print(f"{k} courtyard overlaps")


if __name__ == "__main__":
    os.environ.setdefault("THERMO24_WRITER_CLAIM", os.path.join(HW, "output", ".writer.json"))
    sys.path.insert(0, os.path.join(os.path.dirname(HW), "24ch", "gen"))
    import guard      # I-115
    with guard.claim(str(BOARD), "place.py"):
        main()
