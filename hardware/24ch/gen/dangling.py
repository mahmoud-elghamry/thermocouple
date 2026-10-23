"""Clean the tracks KiCad's DRC reports as dangling (track_dangling): routing leftovers.

For each reported track: an end that touches nothing is pulled back to the nearest connection point along
the segment (pad, via or track end of the same net), so only the overshoot goes; a track with no
connection left after that is deleted. A via reported as via_dangling is deleted only if no pad loses
its connection without it; the others join two tracks of one layer and stay (2026-10-23).
One pass per run: removing a stub can expose the next one, so run until it prints "clean". Every pass is
checked by DRC; it refuses if any pad would become unconnected.
Run with KiCad's python:  python dangling.py [--apply]   (works on a copy without --apply)
"""
import math
import os
import re
import subprocess
import sys
import tempfile

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import guard  # noqa: E402

BOARD = os.environ.get("THERMO24_BOARD", os.path.join(os.path.dirname(HERE), "thermo24.kicad_pcb"))
CLI = os.environ.get("KICAD_CLI", r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe")
ITEM = re.compile(r"\[(track|via)_dangling\].*?\n.*?\n\s+@\(([-\d.]+) mm, ([-\d.]+) mm\): (Track|Via) \[([^\]]+)\]"
                  r"(?: on (\S+), length ([\d.]+) mm)?")


def drc(board):
    rpt = os.path.join(tempfile.mkdtemp(), "drc.rpt")
    subprocess.run([CLI, "pcb", "drc", "--severity-all", "-o", rpt, board], capture_output=True)
    txt = open(rpt, encoding="utf-8").read()
    unconnected = int(re.search(r"Found (\d+) unconnected pads", txt).group(1))
    return [m.groups() for m in ITEM.finditer(txt)], unconnected


def near(p, x, y):
    return abs(pcbnew.ToMM(p.x) - x) < 0.002 and abs(pcbnew.ToMM(p.y) - y) < 0.002


def find(b, kind, x, y, net, layer, length):
    hits = []
    for t in b.GetTracks():
        is_via = t.Type() == pcbnew.PCB_VIA_T
        if is_via != (kind == "via") or t.GetNetname().rsplit("/", 1)[-1] != net.rsplit("/", 1)[-1]:
            continue
        if is_via and near(t.GetPosition(), x, y):
            hits.append(t)
        elif not is_via and t.GetLayerName() == layer and abs(pcbnew.ToMM(t.GetLength()) - float(length)) < 0.001 \
                and (near(t.GetStart(), x, y) or near(t.GetEnd(), x, y)):
            hits.append(t)
    return hits


def connection_points(b, t):
    M = pcbnew.ToMM
    pts = []
    for o in b.GetTracks():
        if o.GetNetCode() != t.GetNetCode() or o.m_Uuid.AsString() == t.m_Uuid.AsString():
            continue
        if o.Type() == pcbnew.PCB_VIA_T:
            pts.append((M(o.GetPosition().x), M(o.GetPosition().y)))
        elif o.GetLayer() == t.GetLayer():
            pts += [(M(o.GetStart().x), M(o.GetStart().y)), (M(o.GetEnd().x), M(o.GetEnd().y))]
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetCode() == t.GetNetCode() and p.IsOnLayer(t.GetLayer()):
                pts.append((M(p.GetPosition().x), M(p.GetPosition().y)))
    return pts


def via_touches(b, v):
    """Same-net track ends and pads at the via (any layer)."""
    M = pcbnew.ToMM
    x, y, r = M(v.GetPosition().x), M(v.GetPosition().y), M(v.GetWidth(pcbnew.F_Cu)) / 2
    n = 0
    for o in b.GetTracks():
        if o.Type() != pcbnew.PCB_VIA_T and o.GetNetCode() == v.GetNetCode():
            n += sum(math.hypot(M(q.x) - x, M(q.y) - y) <= r for q in (o.GetStart(), o.GetEnd()))
    for f in b.GetFootprints():
        n += sum(p.GetNetCode() == v.GetNetCode() and p.HitTest(v.GetPosition()) for p in f.Pads())
    return n


def trim(b, t):
    """Pull each free end back to the nearest connection on the segment. Returns a description or None."""
    M = pcbnew.ToMM
    s, e = (M(t.GetStart().x), M(t.GetStart().y)), (M(t.GetEnd().x), M(t.GetEnd().y))
    length, tol = math.hypot(e[0] - s[0], e[1] - s[1]), M(t.GetWidth()) / 2 + 0.05
    pts = connection_points(b, t)
    joined = [any(math.hypot(px - q[0], py - q[1]) <= tol for px, py in pts) for q in (s, e)]
    if all(joined):
        return None
    new = [s, e]
    for i, (q, far) in enumerate(((s, e), (e, s))):
        if joined[i]:
            continue
        along = []
        for px, py in pts:
            u = ((px - q[0]) * (far[0] - q[0]) + (py - q[1]) * (far[1] - q[1])) / (length * length)
            d = abs((px - q[0]) * (far[1] - q[1]) - (py - q[1]) * (far[0] - q[0])) / length
            if 0 < u <= 1.0 and d <= tol:
                along.append(u)
        u = min(along) if along else 1.0
        new[i] = (q[0] + u * (far[0] - q[0]), q[1] + u * (far[1] - q[1]))
    if math.hypot(new[1][0] - new[0][0], new[1][1] - new[0][1]) < 0.01:
        return "delete"
    t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(new[0][0]), pcbnew.FromMM(new[0][1])))
    t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(new[1][0]), pcbnew.FromMM(new[1][1])))
    return "trim %.2f -> %.2f mm" % (length, math.hypot(new[1][0] - new[0][0], new[1][1] - new[0][1]))


def main():
    apply = "--apply" in sys.argv
    guard.check(BOARD)
    work = BOARD
    if not apply:
        import shutil
        work = os.path.join(tempfile.mkdtemp(), "probe.kicad_pcb")
        shutil.copy2(BOARD, work)
    items, unconnected = drc(work)
    if unconnected:
        raise SystemExit("unconnected pads before cleaning - refusing")
    b = pcbnew.LoadBoard(work)
    plan, doomed_vias = [], []
    for kind, x, y, _, net, layer, length in items:
        if kind == "via":
            v = find(b, kind, float(x), float(y), net, layer, length)[0]
            if via_touches(b, v) <= 1:          # an end of line: nothing passes through it
                print(f"  delete via {net} @({x}, {y}) (end of line)")
                doomed_vias.append(v)
            else:
                print(f"  keep via {net} @({x}, {y}) (joins tracks)")
            continue
        hit = find(b, kind, float(x), float(y), net, layer, length)
        if len(hit) != 1:
            raise SystemExit(f"cannot match track {net} @({x},{y}): {len(hit)} candidates - nothing saved")
        plan.append((hit[0], net, layer, length))
    doomed = []
    for t, net, layer, length in plan:
        what = trim(b, t) or "delete"            # both ends joined yet dangling per DRC: a duplicate bit
        print(f"  {what:24} track {net} {layer} {length} mm")
        if what == "delete":
            doomed.append(t)
    for t in doomed + doomed_vias:
        b.Remove(t)
    import shutil
    backup = work + ".bak"
    shutil.copy2(work, backup)
    pcbnew.SaveBoard(work, b)
    after, unconnected = drc(work)
    if unconnected:
        shutil.copy2(backup, work)
        raise SystemExit(f"{unconnected} UNCONNECTED pads after the pass - board restored, nothing changed")
    os.remove(backup)
    left = [i for i in after if i[0] == "track"]
    print(f"after: {len(left)} dangling tracks, {len(after) - len(left)} dangling vias, {unconnected} unconnected pads")
    for i in after:
        print("   still:", i[0], i[4], i[5] or "", i[6] or "", "@(%s, %s)" % (i[1], i[2]))
    print(("clean" if not left else "run again") + ("" if apply else " (probe copy only; board unchanged)"))

if __name__ == "__main__":
    if "--apply" in sys.argv:
        with guard.claim(BOARD, "dangling.py"):
            main()
    else:
        main()
