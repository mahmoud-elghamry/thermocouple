"""Place every footprint of the 8-ch board REV B0 (0039 step 3, floor plan v1).

Board coordinates: x right, y DOWN, origin top-left, W x H from the Edge.Cuts outline.
Top edge: field terminals (supply, trip, alarm) and the RS-485 pocket (top right).
Middle: 20x4 LCD shadow (98 x 60 mm, standoffs H6-H9) over low parts only; buttons, LEDs and the
panel-button header in the right column. Barrier band below the LCD; the sensor island is the bottom
strip with bank A's two headers on the bottom edge. v2 (2026-10-14): the LCD sits 13 mm lower so
no power or contact path crosses the LCD header row (v1 left 16 such connections unrouted). Clusters are shelf-packed from real courtyards.
Run with KiCad's python; refuses while KiCad or another tool holds the board.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.environ.get("THERMO8_BOARD", os.path.join(os.path.dirname(HERE), "thermo8.kicad_pcb"))
P = 3.81
mm = pcbnew.FromMM
placed = {}
FAILS = []

# floor plan v1 (mm)
W, H = 130.0, 137.0
LCD = (2.0, 27.0, 100.0, 87.0)          # module shadow: only parts lower than ~7 mm underneath
BAND_Y = 91.0                            # barrier band y 91-94; island below
HOLES = {"H5": (4.5, 4.5),               # control, plated to CHASSIS (H4 is a plain NPTH, 0039 P9)
         "H4": (126.0, 40.0),
         "H6": (4.5, 29.5), "H7": (97.5, 29.5), "H8": (4.5, 84.5), "H9": (97.5, 84.5),   # LCD standoffs
         "H1": (4.5, H - 4.5), "H3": (W - 4.5, H - 4.5), "H2": (4.5, 100.0), "H10": (90.0, 113.0)}


def fp_of(b, ref):
    fp = b.FindFootprintByReference(ref)
    if fp is None:
        raise SystemExit(f"no footprint {ref}")
    return fp


def put(b, ref, x, y, rot=0):
    fp = fp_of(b, ref)
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    placed[ref] = (x, y)


def court(fp):
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
    pos = fp.GetPosition()
    return (pcbnew.ToMM(bb.GetX() - pos.x), pcbnew.ToMM(bb.GetY() - pos.y),
            pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight()))


def at(b, ref, x1, y1, rot=0):
    """Put the courtyard's top-left corner at (x1, y1)."""
    fp = fp_of(b, ref)
    fp.SetOrientationDegrees(rot)
    ox, oy, _, _ = court(fp)
    put(b, ref, x1 - ox, y1 - oy, rot)


def pack(b, refs, x1, y1, x2, y2, rot=0, gap=0.35):
    """Shelf-pack refs (in order) into the rectangle; courtyards never overlap."""
    x, y, rowh = x1, y1, 0.0
    for ref in refs:
        fp = fp_of(b, ref)
        fp.SetOrientationDegrees(rot)
        ox, oy, w, h = court(fp)
        if x + w > x2 + 1e-6:
            x, y, rowh = x1, y + rowh + gap, 0.0
        if y + h > y2 + 1e-6:
            FAILS.append(f"{ref} does not fit in ({x1},{y1})-({x2},{y2})")
            put(b, ref, W + 20.0, 10.0 + 6 * len(FAILS), rot)
            continue
        put(b, ref, x - ox, y - oy, rot)
        x += w + gap
        rowh = max(rowh, h)


# ---- bank A (same channel column as the 24-ch) ----------------------------------
COLUMN = [("R", 1, -2.6, 2.9, 90), ("R", 5, 0.0, 2.9, 90), ("R", 2, 2.6, 2.9, 90),
          ("D", 1, -1.9, 8.2, 90), ("D", 2, 1.9, 8.2, 90),
          ("R", 3, -1.9, 13.0, 90), ("R", 4, 1.9, 13.0, 90),
          ("C", 2, -2.6, 17.4, 90), ("C", 1, 0.0, 17.4, 90), ("C", 3, 2.6, 17.4, 90)]


def bank(b, x_pin1, cj_x):
    ypin = H - 8.6
    for h in range(2):
        xp = x_pin1 + h * 33.5
        put(b, f"J{101+h}", xp, ypin, 0)
        for i in range(4):
            k = 4 * h + i + 1
            cx = xp + 2 * P * i + P / 2
            for pre, n, across, depth, rot in COLUMN:
                put(b, f"{pre}{100+10*k+n}", cx + across, ypin - 2.35 - depth, rot)
    xa = x_pin1 + 33.5 - 0.2
    ya = H - 34.0
    put(b, "U101", xa, ya, 0)
    # REGCAPD (pin 1, left) and REGCAPA (pin 24, right) caps nearest their pins (pincaps)
    pack(b, ["C194", "C195", "C196", "C197", "C193"], xa - 12.2, ya - 7.4, xa - 0.2, ya - 3.4, 90)
    pack(b, ["C191", "C192", "C198", "C189"], xa + 0.2, ya - 7.4, xa + 12.2, ya - 3.4, 90)
    for ref, cap, x in (("U102", "C199", cj_x[0]), ("U103", "C190", cj_x[1])):
        put(b, ref, x, ya + 0.2, 0)
        put(b, cap, x + 5.1, ya + 0.2, 90)


# ---- island support and barrier crossings ----------------------------------------
def island(b):
    yb = BAND_Y + 1.5                       # band centre line
    put(b, "U401", 106.0, BAND_Y - 1.04, 0)   # B0505: pins 1-2 (control) above the band, 3-4 below
    for ref, x in (("U403", 72.0), ("U404", 84.5)):
        put(b, ref, x, yb, 270)
    put(b, "R447", 79.6, 104.6, 90)
    put(b, "R446", 87.0, 106.7, 90)
    pack(b, ["R402", "R403", "R404", "U411", "C421", "R445"],
         81.0, yb + 8.5, 96.5, yb + 16.0, 90)
    pack(b, ["C403", "C405", "U402", "C404", "C406", "R401", "TP401", "TP402", "TP407"],
         112.0, yb + 1.0, W - 0.8, yb + 15.0)
    put(b, "J401", 89.0, H - 8.6, 0)
    put(b, "TP405", 79.0, 110.0)
    put(b, "TP406", 83.5, 110.0)
    pack(b, ["U406", "C413", "C414", "TP404", "R416", "R417", "C415", "U407", "C416", "R418",
             "TP403", "R427", "D403", "C418", "R419", "R420", "D401", "R421", "R422", "D402",
             "R423", "R424", "U408", "C417", "Q401", "R425", "R442", "C419",
             "R441", "U409", "R428", "R429", "R440", "Q402"],
         97.0, yb + 15.5, W - 0.8, H - 8.0)


# ---- control side -----------------------------------------------------------------
# relative layouts copied from the routed, DRC-clean 24-ch board (decoupling within the pincaps limits)
MCU_NEAR = {   # ref: (dx, dy, rot) from U501
    "Y501": (-13.16, -0.50, 90), "C501": (-9.00, 4.60, -90), "C502": (-9.00, -5.40, 90),
    "C503": (-8.46, -0.90, 180), "C504": (-2.10, 8.46, -90), "C505": (-0.60, -7.96, 180),
    "C506": (8.46, 0.70, 0), "C507": (2.42, 10.25, 90), "C508": (4.83, 10.25, 90),
    "R501": (7.19, 10.22, 90), "TP501": (10.08, 10.05, 90)}
BUCK_NEAR = {  # from U601 (24-ch buck24.py stage)
    "C602": (-9.0, -2.11, 90), "C603": (-5.5, -2.11, 90), "TP603": (-13.3, -0.6, 0),
    "R605": (-8.0, 1.8, 0), "R606": (-8.0, 4.0, 180), "R601": (-4.4, 4.0, 0), "C604": (5.0, -1.3, 90),
    "L601": (12.6, -0.5, 0), "R602": (3.57, 4.1, 180), "R603": (3.57, 6.3, 0), "C609": (1.73, 8.5, 0),
    "C608": (1.73, 10.7, 0), "R604": (7.5, 7.0, -90), "C605": (16.6, 7.7, -90), "C606": (13.0, 7.7, -90),
    "C607": (10.2, 7.5, -90), "D603": (22.0, 8.5, 90),
    "TP601": (20.5, -3.0, 0), "TP602": (20.5, 1.0, 0)}
ISO_CAPS = {   # from U403: the 24-ch positions of C407-C410
    "C407": (5.84, -7.05, 0), "C408": (4.99, 8.03, -90), "C409": (17.74, -7.05, 0), "C410": (18.64, 7.05, 0)}


def near(b, origin, table):
    ox, oy = origin
    for ref, (dx, dy, rot) in table.items():
        put(b, ref, ox + dx, oy + dy, rot)


def control(b):
    """Floor plan v3: v2 (every power and contact path above the LCD header row J502, a THT wall
    at y ~31 from x 11 to 51) + decoupling beside its pins (24-ch relative layouts, pincaps)."""
    # top edge: tall parts left, then supply, trip and alarm terminals; RS-485 pocket top right
    at(b, "J501", 9.5, 2.0, 0)              # ISP far left: its lines reach the MCU without crossing 24 V
    at(b, "RV501", 19.5, 3.0, 0)
    at(b, "C601", 31.0, 1.5, 0)             # 24 V bulk beside the input protection
    at(b, "J601", 44.0, 0.6, 180)
    at(b, "J701", 61.0, 0.6, 180)
    at(b, "J702", 78.0, 0.6, 180)
    at(b, "J703", 108.0, 0.6, 180)
    put(b, "U703", 116.0, 26.5, 90)
    pack(b, ["JP731", "JP732", "JP733", "D731", "C733", "C734", "C736", "R734", "R735", "R736"],
         103.5, 12.0, W - 0.8, 20.5, 90)
    # above the LCD: relays 3.2 mm left of their terminals (as on the 24-ch), input protection
    at(b, "K701", 59.3, 13.0, 0)
    at(b, "K702", 76.3, 13.0, 0)
    pack(b, ["F601", "D601", "D602"], 28.0, 12.0, 58.9, 26.5)
    d = fp_of(b, "D601").GetPosition()     # turned so FUSED faces F601 and PROT faces D602: no crossing
    put(b, "D601", pcbnew.ToMM(d.x), pcbnew.ToMM(d.y), 180)
    put(b, "C610", 3.2, 12.5, 0)            # CHASSIS-GND bridge beside the plated hole H5, 1.5 mm from 24 V
    put(b, "R607", 3.2, 16.0, 0)
    # under the LCD (low parts only): buck stage right of the J502 row, MCU with its own parts
    put(b, "J502", 12.0, 31.0, 90)          # LCD header, H6 + (7.5, 1.5) as on the 24-ch
    put(b, "U601", 69.0, 43.0, 0)
    near(b, (69.0, 43.0), BUCK_NEAR)
    put(b, "U501", 30.0, 60.0, 0)
    near(b, (30.0, 60.0), MCU_NEAR)
    put(b, "R502", 47.5, 35.5, 0)           # LCD backlight, beside J502 pins 15-16
    pack(b, ["Q701", "R701", "C704", "D703", "C705", "R702", "D701", "R703", "C703", "R704",
             "Q702", "R711", "R712", "D711", "R713", "C713", "R714"], 52.5, 27.6, 79.5, 38.2)  # under the relays
    pack(b, ["R733", "C731", "C732", "C735", "R737", "R738"], 80.0, 28.0, 93.0, 36.0)
    near(b, (72.0, BAND_Y + 1.5), ISO_CAPS)
    pack(b, ["R405", "R430", "R433", "R434", "R439", "C401", "C402"], 55.0, 82.5, 75.0, 86.7, 90)
    # right column, outside the LCD: buttons, LEDs, panel-button header
    for i, ref in enumerate(["SW501", "SW502", "SW503", "SW504", "SW505"]):
        put(b, ref, 111.0, 38.5 + 8.6 * i, 0)
    put(b, "D702", 104.0, 38.0, 0)
    put(b, "D712", 104.0, 45.0, 0)
    at(b, "J503", 122.0, 46.0, 90)
    for ref, (x, y) in HOLES.items():
        put(b, ref, x, y)


def main():
    b = pcbnew.LoadBoard(BOARD)
    bank(b, 15.25, (24.0, 61.9))
    island(b)
    control(b)
    refs = {fp.GetReference() for fp in b.GetFootprints()}
    missing = sorted(refs - set(placed))
    pcbnew.SaveBoard(BOARD, b)
    print(f"placed {len(placed)} of {len(refs)}; not placed: {missing}")
    for f in FAILS:
        print("PACK FAIL:", f)
    boxes = []
    for fp in b.GetFootprints():
        ox, oy, w, h = court(fp)
        p = fp.GetPosition()
        x, y = pcbnew.ToMM(p.x) + ox, pcbnew.ToMM(p.y) + oy
        boxes.append((fp.GetReference(), x, y, x + w, y + h))
    n = 0
    for i, a in enumerate(boxes):
        for c in boxes[i + 1:]:
            if a[1] < c[3] - 0.01 and c[1] < a[3] - 0.01 and a[2] < c[4] - 0.01 and c[2] < a[4] - 0.01:
                n += 1
                print(f"OVERLAP {a[0]} {c[0]}")
        if a[1] < -0.01 or a[2] < -0.01 or a[3] > W + 0.01 or a[4] > H + 0.01:
            print(f"OFF-BOARD {a[0]} ({a[1]:.1f},{a[2]:.1f})-({a[3]:.1f},{a[4]:.1f})")
    print(f"{n} courtyard overlaps")


if __name__ == "__main__":
    os.environ.setdefault("THERMO24_WRITER_CLAIM", os.path.join(os.path.dirname(HERE), "output", ".writer.json"))
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "24ch", "gen"))
    import guard      # I-115: refuse while KiCad or another tool holds the board
    with guard.claim(str(BOARD), "place.py"):
        main()
