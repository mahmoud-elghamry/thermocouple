"""Incremental finishing of the routed board - never moves a footprint.

Works on ../thermo24.kicad_pcb after a routing result was kept (docs/TOOLS.md,
"24-channel board"). Run with KiCad's python:
    python finish.py drc                 # KiCad DRC -> ../output/finish-drc.json, prints a summary
    python finish.py stubs               # join pads to the via of their own net next to them
    python finish.py strip NET [NET...]  # delete the tracks and vias of these nets (to re-route them)
    python finish.py lock | unlock       # lock every track and via (the router keeps them, but
                                         # cannot shove them either - a fully locked run stalled)
    python finish.py unlock-box x1 y1 x2 y2 [...]   # free only the tracks inside the boxes
    python finish.py add NET LAYER W x1,y1 x2,y2 [...] [via]   # a hand route: track chain, optional via at the end
"""
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
BOARD = os.environ.get("THERMO24_BOARD", os.path.join(HW, "thermo24.kicad_pcb"))   # a copy while KiCad holds the board
REPORT = os.path.join(HW, "output", "finish-drc.json")
CLI = os.environ.get("KICAD_CLI", r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe")
mm = pcbnew.FromMM


def drc(quiet=False):
    subprocess.run([CLI, "pcb", "drc", "--format", "json", "--severity-error", "--refill-zones",
                    "-o", REPORT, BOARD], capture_output=True, text=True)
    d = json.load(open(REPORT, encoding="utf-8"))
    if not quiet:
        kinds = Counter()
        for v in d["violations"]:
            m = re.search(r"rule '([^']+)'", v["description"])
            kinds[m.group(1) if m else v["type"]] += 1
        print(f"DRC: {len(d['violations'])} violations {dict(kinds)}, "
              f"{len(d['unconnected_items'])} unconnected")
    return d


def stubs():
    """A pad and a via of the same net, closer than 3 mm, reported unconnected: add the track."""
    d = drc(quiet=True)
    b = pcbnew.LoadBoard(BOARD)
    vias = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
    added = 0
    for item in d["unconnected_items"]:
        descs = [i["description"] for i in item["items"]]
        pos = [i["pos"] for i in item["items"]]
        if not any(s.startswith("Via") for s in descs):
            continue
        k = 0 if descs[0].startswith("Via") else 1
        vx, vy = pos[k]["x"], pos[k]["y"]
        px, py = pos[1 - k]["x"], pos[1 - k]["y"]
        if math.hypot(vx - px, vy - py) > 3.0 or "pad" not in descs[1 - k].lower():
            continue
        via = min(vias, key=lambda v: math.hypot(pcbnew.ToMM(v.GetPosition().x) - vx,
                                                 pcbnew.ToMM(v.GetPosition().y) - vy))
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(mm(px), mm(py)))
        t.SetEnd(via.GetPosition())
        t.SetWidth(mm(0.3))
        t.SetLayer(pcbnew.B_Cu if "B.Cu" in descs[1 - k] else pcbnew.F_Cu)
        t.SetNet(via.GetNet())
        b.Add(t)
        added += 1
    pcbnew.SaveBoard(BOARD, b)
    print(f"stubs: {added} pad-to-via tracks added")


def strip(nets):
    b = pcbnew.LoadBoard(BOARD)
    gone = [t for t in b.GetTracks() if t.GetNetname().rsplit("/", 1)[-1] in nets]
    for t in gone:
        b.Remove(t)
    pcbnew.SaveBoard(BOARD, b)
    print(f"strip: removed {len(gone)} tracks/vias of {sorted(nets)}")


def unlock_box(boxes):
    """Lock everything, then unlock tracks/vias fully inside any box (x1,y1,x2,y2 mm),
    so a short router run may shove only there."""
    b = pcbnew.LoadBoard(BOARD)
    n = 0
    for t in b.GetTracks():
        bb = t.GetBoundingBox()
        x1, y1 = pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop())
        x2, y2 = pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())
        inside = any(a <= x1 and x2 <= c and bq <= y1 and y2 <= d for a, bq, c, d in boxes)
        t.SetLocked(not inside)
        n += inside
    pcbnew.SaveBoard(BOARD, b)
    print(f"unlock-box: {n} tracks/vias free inside {boxes}, the rest locked")


def rip(path):
    """Delete the tracks whose UUIDs are listed in path (written by maze.py --ripup)."""
    want = {l.strip() for l in open(path, encoding="utf-8") if l.strip()}
    b = pcbnew.LoadBoard(BOARD)
    gone = [t for t in b.GetTracks() if t.m_Uuid.AsString() in want]
    for t in gone:
        b.Remove(t)
    pcbnew.SaveBoard(BOARD, b)
    os.remove(path)
    print(f"rip: removed {len(gone)} of {len(want)} listed tracks")


def lock(state=True):
    b = pcbnew.LoadBoard(BOARD)
    n = 0
    for t in b.GetTracks():
        if t.IsLocked() != state:
            t.SetLocked(state)
            n += 1
    pcbnew.SaveBoard(BOARD, b)
    print(f"{'lock' if state else 'unlock'}: {n} tracks/vias changed")


def add(net, layer, width, pts, end_via):
    b = pcbnew.LoadBoard(BOARD)
    n = [v for k, v in b.GetNetsByName().items() if str(k).rsplit("/", 1)[-1] == net][0]
    lay = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}[layer]
    xy = [pcbnew.VECTOR2I(mm(float(a)), mm(float(c))) for a, c in (p.split(",") for p in pts)]
    for a, z in zip(xy, xy[1:]):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(a)
        t.SetEnd(z)
        t.SetWidth(mm(width))
        t.SetLayer(lay)
        t.SetNet(n)
        b.Add(t)
    if end_via:
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(xy[-1])
        v.SetWidth(mm(0.6))
        v.SetDrill(mm(0.3))
        v.SetNet(n)
        b.Add(v)
    pcbnew.SaveBoard(BOARD, b)
    print(f"add: {len(xy) - 1} segments on {net}{' + via' if end_via else ''}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "drc"
    if cmd == "drc":
        drc()
    elif cmd == "stubs":
        stubs()
        drc()
    elif cmd == "strip":
        strip(set(sys.argv[2:]))
    elif cmd == "lock":
        lock()
    elif cmd == "unlock-box":
        vals = [float(v) for v in sys.argv[2:]]
        unlock_box([tuple(vals[i:i + 4]) for i in range(0, len(vals), 4)])
    elif cmd == "rip":
        rip(os.path.join(HW, "output", "maze-rip.txt"))
    elif cmd == "unlock":
        lock(False)
    elif cmd == "add":
        args = sys.argv[2:]
        via = args[-1] == "via"
        add(args[0], args[1], float(args[2]), args[3:-1] if via else args[3:], via)
    else:
        raise SystemExit(__doc__)
