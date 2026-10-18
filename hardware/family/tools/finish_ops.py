"""Copied algorithms; constants come from the entry tool and its profile."""
from finish import *

def _anchored(b, net_code, p):
    """True if point p sits on an own-net pad or via (moving it would break the joint)."""
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T and t.GetNetCode() == net_code and t.HitTest(p, 0):
            return True
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() == net_code and pad.HitTest(p, 0):
                return True
    return False


def nori(margin=0.012):
    """Push tracks that pass a pad closer than the nori_pad_to_track rule asks (DRC report)
    sideways by the shortfall. Free segment ends drag the joined segments along; a segment
    pinned at one end swings about it. Re-run `drc` after; repeat until clean."""
    d = json.load(open(REPORT, encoding="utf-8"))
    b = pcbnew.LoadBoard(BOARD)
    tracks = {t.m_Uuid.AsString(): t for t in b.GetTracks()}
    pads = {p.m_Uuid.AsString(): p for fp in b.GetFootprints() for p in fp.Pads()}
    moved, skipped = 0, []
    for v in d["violations"]:
        if "nori_pad_to_track" not in v["description"]:
            continue
        want = float(re.search(r"clearance ([0-9.]+) mm", v["description"]).group(1))
        act = float(re.search(r"actual ([0-9.]+) mm", v["description"]).group(1))
        t = next((tracks.get(i["uuid"]) for i in v["items"] if i["uuid"] in tracks), None)
        p = next((pads.get(i["uuid"]) for i in v["items"] if i["uuid"] in pads), None)
        if t is None or p is None:
            skipped.append(v["description"][:40])
            continue
        s, e = t.GetStart(), t.GetEnd()
        sx, sy, ex, ey = (pcbnew.ToMM(c) for c in (s.x, s.y, e.x, e.y))
        L = math.hypot(ex - sx, ey - sy)
        if L < 1e-3:
            continue
        nx, ny = -(ey - sy) / L, (ex - sx) / L
        pp = p.GetPosition()
        px, py = pcbnew.ToMM(pp.x), pcbnew.ToMM(pp.y)
        # the point of the segment nearest the pad centre, and which side the pad is on
        k = max(0.0, min(1.0, ((px - sx) * (ex - sx) + (py - sy) * (ey - sy)) / (L * L)))
        if (px - (sx + k * (ex - sx))) * nx + (py - (sy + k * (ey - sy))) * ny > 0:
            nx, ny = -nx, -ny
        shift = want - act + margin
        fs, fe = not _anchored(b, t.GetNetCode(), s), not _anchored(b, t.GetNetCode(), e)
        if fs and fe:
            ds = de = shift
        elif fs and k < 0.9:
            ds, de = min(shift / max(1 - k, 0.1), 0.15), 0.0      # swing about the pinned end
        elif fe and k > 0.1:
            ds, de = 0.0, min(shift / max(k, 0.1), 0.15)
        else:
            skipped.append(f"{t.GetNetname()} near {p.GetParentFootprint().GetReference()}.{p.GetNumber()}")
            continue
        for old, dd in ((s, ds), (e, de)):
            if dd == 0.0:
                continue
            new = pcbnew.VECTOR2I(old.x + mm(nx * dd), old.y + mm(ny * dd))
            for o in b.GetTracks():     # drag every own-net segment ending here
                if o.Type() == pcbnew.PCB_VIA_T or o.GetNetCode() != t.GetNetCode():
                    continue
                if o.GetStart() == old:
                    o.SetStart(new)
                if o.GetEnd() == old:
                    o.SetEnd(new)
        moved += 1
    pcbnew.SaveBoard(BOARD, b)
    print(f"nori: {moved} tracks pushed, {len(skipped)} left for hand work: {skipped}")


def _copy_without(uuids, tag):
    """Temp copy of the board with these tracks/vias removed; returns its path stem.
    Runs in a child process: after a Remove, pcbnew cannot load another board."""
    tmp = os.path.join(HW, "output", "tmp-dangling")
    os.makedirs(tmp, exist_ok=True)
    stem = os.path.join(tmp, f"t{tag}")
    for ext in (".kicad_pro", ".kicad_dru"):
        src = os.path.splitext(BOARD)[0] + ext
        if os.path.exists(src):
            open(stem + ext, "wb").write(open(src, "rb").read())
    open(stem + ".txt", "w", encoding="utf-8").write(" ".join(uuids))
    subprocess.run([sys.executable, os.path.join(HERE, "finish.py"), "_without", stem], check=True,
                   capture_output=True)
    return stem


def _without(stem):
    want = set(open(stem + ".txt", encoding="utf-8").read().split())
    b = pcbnew.LoadBoard(BOARD)
    for x in [x for x in b.GetTracks() if x.m_Uuid.AsString() in want]:
        b.Remove(x)
    pcbnew.SaveBoard(stem + ".kicad_pcb", b)


def _unconnected(stem):
    """KiCad DRC unconnected count of a temp copy (thread-safe: only runs kicad-cli)."""
    subprocess.run([CLI, "pcb", "drc", "--format", "json", "--severity-error", "--refill-zones", "-o", stem + ".json",
                    stem + ".kicad_pcb"], capture_output=True, text=True)
    return len(json.load(open(stem + ".json", encoding="utf-8"))["unconnected_items"])


def dangling():
    """Delete what KiCad DRC calls track_dangling / via_dangling (leftover router stubs).
    Each candidate is tried alone on a temp copy and deleted only if KiCad's unconnected
    count stays the same; repeats until DRC lists none that are safe to delete."""
    from concurrent.futures import ThreadPoolExecutor
    rep = os.path.join(HW, "output", "finish-warn.json")
    removed, kept = 0, set()
    for _ in range(6):
        subprocess.run([CLI, "pcb", "drc", "--format", "json", "--severity-warning", "--refill-zones",
                        "-o", rep, BOARD], capture_output=True, text=True)
        d = json.load(open(rep, encoding="utf-8"))
        uu = sorted({i["uuid"] for v in d["violations"] if v["type"] in ("track_dangling", "via_dangling")
                     for i in v["items"]} - kept)
        if not uu:
            break
        base = len(d["unconnected_items"])
        stems = [_copy_without({u}, i) for i, u in enumerate(uu)]
        with ThreadPoolExecutor(6) as ex:
            counts = list(ex.map(_unconnected, stems))
        safe = {u for u, c in zip(uu, counts) if c == base}
        kept |= set(uu) - safe
        if not safe:
            break
        if _unconnected(_copy_without(safe, "all")) != base:
            # as a set they break something; take the individually safe ones one at a time
            taken = set()
            for u in sorted(safe):
                if _unconnected(_copy_without(taken | {u}, "one")) == base:
                    taken.add(u)
            kept |= safe - taken
            if not taken:
                print("dangling: nothing more is safe to delete")
                break
            safe = taken
        stem = _copy_without(safe, "all")
        open(BOARD, "wb").write(open(stem + ".kicad_pcb", "rb").read())
        removed += len(safe)
    print(f"dangling: removed {removed} stub tracks/vias, kept {len(kept)} that carry a connection")


