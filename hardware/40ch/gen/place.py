"""Place every footprint of the 40-ch board REV A0 (0039 step 8, floor plan v2: shared parts from the
finished 24-ch board, gen/pos24.json).

The 24-ch floor plan v2 (0032) extended: x right, y DOWN, origin top-left, 250 x 145 mm.
Sensor island = a U along the left (x < 42), bottom (y > 103) and right (x > 198) edges; barrier bands
x 42-45, y 100-103 and x 195-198. Banks A-C on the bottom edge, D on the left edge (as the 24-ch's C),
E on the right edge (bank D turned 180 degrees), the RTD bank in the top-right corner. Control side
(terminals, RS-485 pocket, LCD, MCU, buck, relays, buttons) as on the 24-ch. Run with KiCad's python.
"""
import os

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.environ.get("THERMO40_BOARD", os.path.join(os.path.dirname(HERE), "thermo40.kicad_pcb"))
W, H = 250.0, 145.0
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
            put(b, ref, W + 20.0, 10.0 + 6 * len(FAILS), rot)
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


# ---- island support, barrier crossings ---------------------------------------
def island(b):
    # island supply and AVDD clamp, top-left above bank C
    put(b, "U401", 47.8, 5.0, 270)              # B0505: pins 1-2 control (x 47.8/45.3), 3-4 island
    pack(b, ["C403", "C405", "U402", "C404", "C406", "R401", "TP401", "TP402",
             "U409", "R428", "R429", "R440", "Q402", "R441", "TP407"], 8.4, 1.0, 37.6, 18.4)
    # isolators straddling the bottom band (side 1 = control, up)
    for ref, x in (("U403", 71.4), ("U404", 83.9)):
        put(b, ref, x, 101.5, 270)
    put(b, "U410", 81.8, 120.0, 0)                     # CS decoder in the gap between banks A and B (0039 D3)
    pack(b, ["C408", "C410", "R402", "R403", "R404", "C420", "R444", "U411", "C421", "R445", "R446",
             "R447"], 69.8, 107.8, 101.0, 113.8, 90)
    pack(b, ["C407", "C409", "R405", "R430", "R439"], 64.2, 89.0, 102.6, 95.2, 90)
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
    put(b, "J503", 143.0, 49.0, 180)                 # panel-button header (0034 D2), as on the 24-ch
    put(b, "H1", 4.5, 140.5); put(b, "H2", 4.5, 101.0); put(b, "H3", W - 4.5, 140.5)
    put(b, "H4", 165.5, 92.0); put(b, "H5", 165.5, 4.5); put(b, "H10", 4.5, 4.5)
    for ref, (x, y) in zip(["H6", "H7", "H8", "H9"],
                           [(49.5, 41.5), (142.5, 41.5), (49.5, 96.5), (142.5, 96.5)]):
        put(b, ref, x, y)


def bank_vertical(b, base, y_pin1):
    """A bank on the left edge (as the 24-ch's bank C); plugs face the left edge."""
    xpin = 8.6
    for h in range(2):
        yp = y_pin1 + h * 33.5
        put(b, f"J{base+1+h}", xpin, yp, 270)
        for i in range(4):
            k = 4 * h + i + 1
            cy = yp + 2 * P * i + P / 2
            for pre, n, across, depth, rot in COLUMN:
                put(b, f"{pre}{base+10*k+n}", xpin + 2.35 + depth, cy + across, rot - 90)
    ya = y_pin1 + 33.5 - 0.2
    put(b, f"U{base+1}", 36.0, ya, 0)
    pack(b, [f"C{base+n}" for n in (94, 95, 96, 97, 98)], 31.0, ya - 16.5, 41.8, ya - 3.8, 0)
    pack(b, [f"C{base+91}", f"C{base+92}", f"C{base+93}", f"R{base+91}", f"C{base+89}"],
         31.0, ya + 3.8, 41.8, ya + 16.5, 0)
    for ref, cap, y in ((f"U{base+2}", f"C{base+99}", y_pin1 + 9.0), (f"U{base+3}", f"C{base+90}", y_pin1 + 55.5)):
        put(b, ref, 36.0, y, 90)
        put(b, cap, 36.0, y + 6.0, 0)


def turn(b, refs, yc):
    """Turn already placed parts 180 degrees about (W/2, yc): bank D's layout becomes bank E's."""
    for ref in refs:
        fp = fp_of(b, ref)
        p = fp.GetPosition()
        x, y = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
        put(b, ref, W - x, 2 * yc - y, fp.GetOrientationDegrees() + 180)


def bank_right(b, yc=63.0):
    """Bank E on the right edge: bank D (already placed from the 24-ch) turned 180 degrees about (W/2, yc)."""
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        pre = "".join(ch for ch in ref if ch.isalpha())
        num = ref[len(pre):]
        if num.isdigit() and 900 <= int(num) < 1000:
            src = fp_of(b, f"{pre}{int(num) - 100}")
            p = src.GetPosition()
            put(b, ref, W - pcbnew.ToMM(p.x), 2 * yc - pcbnew.ToMM(p.y), src.GetOrientationDegrees() + 180)


def pack_multi(b, refs, regions, rot=0):
    """pack() into the first region, then whatever did not fit into the next ones."""
    for k, reg in enumerate(regions):
        n = len(FAILS)
        pack(b, refs, *reg, rot=rot)
        refs = [f.split()[0] for f in FAILS[n:]]
        del FAILS[n:]
        if not refs:
            return
    for r in refs:
        FAILS.append(f"{r} does not fit in any region")


RTD_NEAR = {"C1093": (199.3, 35.3, 90), "C1096": (199.3, 40.6, 270), "C1094": (204.0, 34.6, 180),
            "C1092": (207.7, 35.3, 90), "C1091": (207.7, 39.0, 90), "C1097": (209.9, 35.3, 90),
            "C1095": (209.9, 39.0, 90), "C1090": (205.0, 43.5, 0), "R1092": (201.0, 43.5, 0)}


def rtd(b):
    """RTD bank: terminals on the top edge of the right column, network below and beside bank E."""
    at(b, "J1001", W - 47.0, 0.6, 180)
    at(b, "J1002", W - 19.0, 0.6, 180)
    put(b, "U1001", 203.5, 39.0, 0)
    for ref, (x, y, rot) in RTD_NEAR.items():   # decoupling beside its pins (pincaps), R_ref Kelvin at pins 12-13
        put(b, ref, x, y, rot)
    refs = []
    for r in (1, 2, 3, 4):
        refs += [f"R{1000+10*r+n}" for n in (1, 3, 9)]                 # 2512 limiters first
    for r in (1, 2, 3, 4):
        refs += [f"{p}{1000+10*r+n}" for p, ns in (("R", (2, 4, 5, 6, 7, 8)), ("D", range(1, 6)),
                                                    ("C", range(1, 4))) for n in ns]
    refs += ["R1095", "R1093", "D1091"]
    refs = [r for r in refs if b.FindFootprintByReference(r) and r not in RTD_NEAR]
    pack_multi(b, refs, [(198.6, 12.0, W - 0.8, 33.5), (198.6, 44.5, 208.6, 99.0)])


def at(b, ref, x1, y1, rot=0):
    fp = fp_of(b, ref)
    fp.SetOrientationDegrees(rot)
    ox, oy, _, _ = court(fp)
    put(b, ref, x1 - ox, y1 - oy, rot)


POS24 = os.path.join(HERE, "pos24.json")   # final 24-ch positions (after its pincaps/buck repairs)


def from24(b):
    """Every part the 40-ch shares with the 24-ch goes where it sits on the finished 24-ch board:
    banks A, B (1xx, 2xx) and the control/isolation/power parts (4xx-7xx) unchanged; bank D (8xx)
    takes the 24-ch's left bank C (3xx); bottom bank C (3xx) is bank B moved one bank pitch right."""
    import json
    pos = json.load(open(POS24, encoding="utf-8"))["positions"]
    refs = {fp.GetReference() for fp in b.GetFootprints()}
    for ref in sorted(refs):
        pre = "".join(ch for ch in ref if ch.isalpha())
        num = int(ref[len(pre):]) if ref[len(pre):].isdigit() else -1
        src, dx = None, 0.0
        if 0 <= num < 100 or 100 <= num < 300 or 400 <= num < 800:
            src = ref
        elif 300 <= num < 400:
            src, dx = f"{pre}{num - 100}", 74.0
        elif 800 <= num < 900:
            src = f"{pre}{num - 500}"
        if src and src in pos:
            x, y, rot = pos[src]
            put(b, ref, x + dx, y, rot)


def extras(b):
    """Parts the 24-ch does not have: decoder, SIO driver, the SIO_WR_N pull-up, holes moved."""
    put(b, "U410", 81.8, 120.0, 0)          # CS decoder in the gap between banks A and B (0039 D3)
    put(b, "C420", 81.8, 126.2, 0)
    put(b, "R444", 81.8, 114.2, 0)
    put(b, "U411", 92.5, 105.3, 0)          # SIO driver where the 24-ch's third isolator was (0039 P2)
    for i, ref in enumerate(["C421", "R445", "R446", "R447"]):
        put(b, ref, 95.8 + 2.2 * i, 105.3, 90)
    put(b, "R439", 70.0, 92.0, 90)          # SIO_WR_N pull-up beside the other control pull-ups
    put(b, "H3", W - 4.5, 140.5, 0)


def main():
    b = pcbnew.LoadBoard(BOARD)
    from24(b)
    extras(b)
    bank_right(b)
    rtd(b)
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
    import sys
    os.environ.setdefault("THERMO24_WRITER_CLAIM", os.path.join(os.path.dirname(HERE), "output", ".writer.json"))
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "24ch", "gen"))
    import guard      # I-115: refuse while KiCad or another tool holds the board
    with guard.claim(str(BOARD), "place.py"):
        main()
