"""Place every footprint per floor plan v2 (decision 0032).

Board coordinates: x right, y DOWN, origin top-left, 170 x 145 mm.
Sensor island = the L along the bottom (y > 103) and left (x < 42) edges;
barrier band x 42-45 (y < 103) and y 100-103 (x > 42). The three ISO7761
straddle the bottom band, the B0505 the left band. Run with KiCad's python.
Clusters are shelf-packed from real courtyard sizes, so they cannot overlap;
pack() stops if a region is too small.
"""
import os

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(os.path.dirname(HERE), "thermo24.kicad_pcb")
P = 3.81
mm = pcbnew.FromMM
placed = {}
FAILS = []


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
            put(b, ref, 190.0, 10.0 + 6 * len(FAILS), rot)
            continue
        put(b, ref, x - ox, y - oy, rot)
        x += w + gap
        rowh = max(rowh, h)


# ---- banks -----------------------------------------------------------------
# behind one channel, relative to the TC+/TC- pair centre: (prefix, n, across, depth, rot)
COLUMN = [("R", 1, -2.6, 2.9, 90), ("R", 5, 0.0, 2.9, 90), ("R", 2, 2.6, 2.9, 90),
          ("D", 1, -1.9, 8.2, 90), ("D", 2, 1.9, 8.2, 90),
          ("R", 3, -1.9, 13.0, 90), ("R", 4, 1.9, 13.0, 90),
          ("C", 2, -2.6, 17.4, 90), ("C", 1, 0.0, 17.4, 90), ("C", 3, 2.6, 17.4, 90)]


def bank_horizontal(b, bank, x_pin1, cj_x):
    """Banks A and B on the bottom edge; plugs face the bottom edge."""
    ypin = 145 - 8.6
    for h in range(2):
        xp = x_pin1 + h * 33.5
        put(b, f"J{100*bank+h+1}", xp, ypin, 0)
        for i in range(4):
            k = 4 * h + i + 1
            cx = xp + 2 * P * i + P / 2
            for pre, n, across, depth, rot in COLUMN:
                put(b, f"{pre}{100*bank+10*k+n}", cx + across, ypin - 2.35 - depth, rot)
    u = 100 * bank
    xa = x_pin1 + 33.5 - 0.2
    # ADC low, decoupling in one row above it (toward the barrier), so the 16 AIN
    # traces from the channel columns reach the ADC without crossing parts
    put(b, f"U{u+1}", xa, 111.0, 0)
    pack(b, [f"C{u+94}", f"C{u+95}", f"C{u+96}", f"C{u+97}", f"C{u+98}"], xa - 12.2, 103.6, xa - 0.2, 107.6, 90)
    pack(b, [f"C{u+91}", f"C{u+92}", f"C{u+93}", f"R{u+91}", f"C{u+89}"], xa + 0.2, 103.6, xa + 12.2, 107.6, 90)
    for ref, cap, x in ((f"U{u+2}", f"C{u+99}", cj_x[0]), (f"U{u+3}", f"C{u+90}", cj_x[1])):
        put(b, ref, x, 111.2, 0)
        put(b, cap, x + 5.1, 111.2, 90)


def bank_vertical(b, y_pin1):
    """Bank C on the left edge; plugs face the left edge."""
    xpin = 8.6
    for h in range(2):
        yp = y_pin1 + h * 33.5
        put(b, f"J{301+h}", xpin, yp, 270)
        for i in range(4):
            k = 4 * h + i + 1
            cy = yp + 2 * P * i + P / 2
            for pre, n, across, depth, rot in COLUMN:
                put(b, f"{pre}{300+10*k+n}", xpin + 2.35 + depth, cy + across, rot - 90)
    ya = y_pin1 + 33.5 - 0.2
    put(b, "U301", 36.0, ya, 0)
    pack(b, ["C394", "C395", "C396", "C397", "C398"], 31.0, ya - 16.5, 41.8, ya - 3.8, 0)
    pack(b, ["C391", "C392", "C393", "R391", "C389"], 31.0, ya + 3.8, 41.8, ya + 16.5, 0)
    for ref, cap, y in (("U302", "C399", y_pin1 + 9.0), ("U303", "C390", y_pin1 + 33.5 + 22.0)):
        put(b, ref, 36.0, y, 90)
        put(b, cap, 36.0, y + 6.0, 0)


# ---- island support, barrier crossings ---------------------------------------
def island(b):
    # island supply and AVDD clamp, top-left above bank C
    put(b, "U401", 47.8, 5.0, 270)              # B0505: pins 1-2 control (x 47.8/45.3), 3-4 island
    pack(b, ["C403", "C405", "U402", "C404", "C406", "R401", "TP401", "TP402",
             "U409", "R428", "R429", "R440", "Q402", "R441", "TP407"], 8.4, 1.0, 37.6, 18.4)
    # isolators straddling the bottom band (side 1 = control, up)
    for ref, x in (("U403", 71.4), ("U404", 83.9), ("U405", 96.4)):
        put(b, ref, x, 101.5, 270)
    pack(b, ["C408", "C410", "C412", "R402", "R403", "R404", "R415"]
         , 68.2, 107.8, 100.5, 113.8, 90)
    pack(b, ["C407", "C409", "C411", "R405"] + [f"R{430+i}" for i in range(9)],
         64.2, 89.0, 102.6, 95.2, 90)
    # reference, mid-rail, bias bus, engine reference: island corner below bank C
    put(b, "J401", 8.6, 89.5, 270)
    put(b, "TP405", 12.0, 108.0); put(b, "TP406", 16.0, 108.0)
    pack(b, ["U406", "C413", "C414", "TP404", "R416", "R417", "C415", "U407", "C416", "R418",
             "TP403", "R427", "D403", "C418", "R419", "R420", "D401", "R421", "R422", "D402",
             "R423", "R424", "U408", "C417", "Q401", "R425", "R442", "C419"],
         11.5, 86.8, 41.5, 102.6)


# ---- control side -------------------------------------------------------------
def control(b):
    put(b, "C402", 51.0, 13.5, 90)
    put(b, "C401", 48.3, 13.5, 90)
    # RS-485 pocket at the top edge, x 55-84
    put(b, "J703", 58.0 + 3.04, 6.3, 0)
    put(b, "U703", 69.0, 24.0, 90)              # bus pins up, logic pins down
    # bus side above the pocket band (y < 22); U703 bus pins at y 19.35, logic pins at 28.65
    put(b, "JP733", 57.4, 14.2, 0)
    pack(b, ["D731", "C733", "C734", "C736", "R734", "R735", "R736"],
         59.6, 11.6, 83.9, 17.95, 90)
    put(b, "JP731", 57.0, 20.4, 90)
    put(b, "JP732", 77.6, 20.4, 90)
    pack(b, ["R733", "C731", "C732", "C735", "R737", "R738"], 57.0, 31.0, 84.0, 36.0)
    # relays and field terminals
    put(b, "J701", 86.0 + 3.04, 6.3, 0)
    put(b, "J702", 103.1 + 3.04, 6.3, 0)
    put(b, "J601", 120.0 + 3.04, 6.3, 0)
    put(b, "K701", 94.0, 18.5, 0)
    put(b, "K702", 111.0, 18.5, 0)
    pack(b, ["Q701", "R701", "C704", "D703", "C705", "R702", "D701", "R703", "C703", "R704",
             "Q702", "R711", "R712", "D711", "R713", "C713"], 86.0, 24.6, 120.0, 32.0)
    put(b, "R714", 158.5, 57.5, 90)
    put(b, "J501", 88.0, 36.5, 90)
    put(b, "RV501", 108.0, 36.0, 0)
    # buck block, top-right (corner hole H5 kept clear)
    put(b, "F601", 139.5, 15.0, 90)
    put(b, "D601", 144.5, 15.0, 90)
    put(b, "D602", 150.0, 15.0, 90)
    put(b, "C601", 155.5, 15.0, 0)
    put(b, "L601", 161.0, 29.0, 0)
    put(b, "U601", 150.0, 25.5, 0)
    pack(b, ["C602", "C603", "C604", "R601", "R605", "R606", "R602", "R603", "R604",
             "C608", "C609", "TP603"], 121.0, 21.5, 146.0, 33.0)
    pack(b, ["C605", "C606", "C607", "TP601", "TP602"], 121.0, 33.4, 168.5, 37.8)
    put(b, "C610", 128.0, 15.0, 0)
    put(b, "R607", 128.0, 18.5, 0)
    put(b, "D603", 165.0, 15.0, 90)
    # MCU under the LCD (low parts only)
    put(b, "U501", 79.0, 66.0, 0)
    put(b, "Y501", 97.0, 66.0, 0)
    pack(b, ["C501", "C502", "C503", "C504", "C505", "C506", "C507", "C508", "R501", "TP501"],
         66.0, 74.5, 104.0, 80.0, 90)
    put(b, "J502", 57.0, 43.0, 90)              # LCD header along the module's top edge
    put(b, "R502", 101.0, 46.0, 0)
    # keypad + LEDs at the right edge, outside the LCD
    for i, ref in enumerate(["SW501", "SW502", "SW503", "SW504"]):
        put(b, ref, 148.0, 44.0 + 14.0 * i, 0)
    put(b, "SW505", 161.0, 72.0, 90)
    put(b, "D702", 160.0, 47.0, 0)
    put(b, "D712", 160.0, 53.0, 0)
    # mounting: island NPTH, control plated, LCD standoffs
    put(b, "H1", 4.5, 140.5); put(b, "H2", 4.5, 101.0); put(b, "H3", 165.5, 140.5)
    put(b, "H4", 165.5, 92.0); put(b, "H5", 165.5, 4.5); put(b, "H10", 4.5, 4.5)
    for ref, (x, y) in zip(["H6", "H7", "H8", "H9"],
                           [(49.5, 41.5), (142.5, 41.5), (49.5, 96.5), (142.5, 96.5)]):
        put(b, ref, x, y)


def drop_removed(b):
    """Delete footprints whose reference is no longer in the schematic netlist."""
    import xml.etree.ElementTree as ET
    xml = os.path.join(os.path.dirname(HERE), "thermo24.xml")
    keep = {c.get("ref") for c in ET.parse(xml).getroot().iter("comp")}
    gone = [fp for fp in b.GetFootprints() if fp.GetReference() not in keep]
    names = [fp.GetReference() for fp in gone]
    for fp in gone:
        b.Remove(fp)
    if names:
        print("removed (not in schematic):", " ".join(sorted(names)))


def main():
    # after Remove() the SWIG bindings hand out bare pointers for the rest of the
    # process, so deleting is done in a child process
    import subprocess, sys
    subprocess.run([sys.executable, os.path.abspath(__file__), "--drop"], check=True)
    b = pcbnew.LoadBoard(BOARD)
    bank_horizontal(b, 1, 15.25, (24.0, 61.9))
    bank_horizontal(b, 2, 89.25, (104.7, 138.5))
    bank_vertical(b, 22.25)
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
        if a[1] < -0.01 or a[2] < -0.01 or a[3] > 170.01 or a[4] > 145.01:
            print(f"OFF-BOARD {a[0]} ({a[1]:.1f},{a[2]:.1f})-({a[3]:.1f},{a[4]:.1f})")
    print(f"{n} courtyard overlaps")


if __name__ == "__main__":
    import guard      # I-115: refuse while KiCad or another tool holds the board
    with guard.claim(str(BOARD), "place.py"):
        import sys
        if "--drop" in sys.argv:
            bd = pcbnew.LoadBoard(BOARD)
            drop_removed(bd)
            pcbnew.SaveBoard(BOARD, bd)
        else:
            main()
