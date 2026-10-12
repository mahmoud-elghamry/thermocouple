"""Apply a schematic change to the routed board without re-placing or re-routing it (0036).

Reads ../thermo24.xml (written by build.py) and, on the board:
  * a part whose footprint changed is replaced by the new footprint at the same centre and angle;
  * a part that is new is added at the position given on the command line (REF=X,Y,ROT);
  * a part that is gone is removed;
  * every pad gets the net the netlist gives it; value, MPN, LCSC and the DNP flag follow the schematic.
Tracks and vias of a replaced or removed part's pads, and of nets that no longer exist, are deleted;
re-route what is left with maze.py / finish.py add. Run with KiCad's python:
    python delta.py [--dry] [REF=X,Y,ROT ...] [OLD>NEW@DEG ...]
OLD>NEW@DEG reuses a footprint that leaves the schematic for a new part with the same footprint
(renamed, turned DEG about its centre), so the tracks that already reach its pads are kept.
"""
import os
import sys
import xml.etree.ElementTree as ET

import pcbnew

import guard

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
BOARD = os.environ.get("THERMO24_BOARD", os.path.join(HW, "thermo24.kicad_pcb"))
FPDIR = r"C:\Program Files\KiCad\10.0\share\kicad\footprints"
BOARD_ONLY = ("FID",)
mm, T = pcbnew.FromMM, pcbnew.ToMM


def netlist():
    root = ET.parse(os.path.join(HW, "thermo24.xml")).getroot()
    comps, pads = {}, {}
    for c in root.iter("comp"):
        if c.get("ref").startswith("#"):
            continue
        props = {p.get("name"): p.get("value") for p in c.iter("property")}
        fields = {f.get("name"): f.text or "" for f in c.iter("field")}
        comps[c.get("ref")] = dict(fp=c.findtext("footprint") or "", value=c.findtext("value"),
                                   mpn=fields.get("MPN", ""), lcsc=fields.get("LCSC", ""), dnp="dnp" in props)
    for n in root.iter("net"):
        for node in n.iter("node"):
            pads[(node.get("ref"), node.get("pin"))] = n.get("name")
    return comps, pads


def own_tracks(b, fp):
    """Tracks and vias that touch a pad of fp on that pad's own net."""
    hit = []
    for t in b.GetTracks():
        for p in fp.Pads():
            if p.GetNetCode() == t.GetNetCode() and p.GetNetCode() > 0 and (
                    p.HitTest(t.GetStart()) or (t.Type() != pcbnew.PCB_VIA_T and p.HitTest(t.GetEnd()))):
                hit.append(t)
                break
    return hit


def load_fp(fpid):
    lib, name = fpid.split(":")
    return pcbnew.FootprintLoad(os.path.join(FPDIR, lib + ".pretty"), name)


def net(b, name):
    n = b.FindNet(name)
    if n is None:
        n = pcbnew.NETINFO_ITEM(b, name)
        b.Add(n)
    return n


def main(args):
    dry = "--dry" in args
    place, rename = {}, {}
    for a in args:
        if ">" in a:
            old, rest = a.split(">")
            new, deg = rest.split("@")
            rename[old] = (new, float(deg))
        elif "=" in a:
            ref, xyz = a.split("=")
            place[ref] = tuple(float(v) for v in xyz.split(","))
    comps, pads = netlist()
    b = pcbnew.LoadBoard(BOARD)
    for old, (new, deg) in rename.items():
        f = b.FindFootprintByReference(old)
        f.SetReference(new)
        f.SetOrientationDegrees(f.GetOrientationDegrees() + deg)
        log0 = f"rename {old} -> {new}, turned {deg:g} deg"
        print(log0)
    onboard = {f.GetReference(): f for f in b.GetFootprints()}
    kill, log = {}, []
    for ref, f in onboard.items():
        if ref not in comps and not ref.startswith(BOARD_ONLY):
            kill.update({t.m_Uuid.AsString(): t for t in own_tracks(b, f)})
            log.append(f"remove {ref}")
            if not dry:
                b.Remove(f)
    for ref, c in comps.items():
        f = onboard.get(ref)
        old = f.GetFPIDAsString() if f is not None else None
        if f is None or old != c["fp"]:
            if f is None and ref not in place:
                raise SystemExit(f"delta: {ref} is new; give its position as {ref}=X,Y,ROT")
            new = load_fp(c["fp"])
            if f is not None:
                pos, ang = f.GetPosition(), f.GetOrientationDegrees()
                kill.update({t.m_Uuid.AsString(): t for t in own_tracks(b, f)})
                log.append(f"replace {ref} {old} -> {c['fp']}")
                if not dry:
                    b.Remove(f)
            else:
                x, y, ang = place[ref]
                pos = pcbnew.VECTOR2I(mm(x), mm(y))
                log.append(f"add {ref} {c['fp']} at {x},{y} rot {ang}")
            new.SetFPID(pcbnew.LIB_ID(*c["fp"].split(":")))
            new.SetReference(ref)
            new.SetPosition(pos)
            new.SetOrientationDegrees(ang)
            if not dry:
                b.Add(new)
            f = new
        f.SetValue(c["value"])
        for k in ("mpn", "lcsc"):
            if c[k]:
                f.SetField(k.upper(), c[k])
        if f.IsDNP() != c["dnp"]:
            log.append(f"dnp {ref} -> {c['dnp']}")
            f.SetDNP(c["dnp"])
        for p in f.Pads():
            want = pads.get((ref, p.GetNumber()))
            if want is None or not p.GetNumber():
                continue
            if p.GetNetname() != want:
                log.append(f"net {ref}.{p.GetNumber()} {p.GetNetname()} -> {want}")
                old_net = p.GetNetname()
                for t in b.GetTracks():      # the pad's OLD-net copper would short the new net; another
                    # net's track that only passes under a replaced footprint is never touched (that
                    # cut TC traces on 2026-10-12) - DRC reports it and the part is moved instead
                    if old_net and t.GetNetname() == old_net and (p.HitTest(t.GetStart()) or (
                            t.Type() != pcbnew.PCB_VIA_T and p.HitTest(t.GetEnd()))):
                        kill[t.m_Uuid.AsString()] = t
                if not dry:
                    p.SetNet(net(b, want))
    live = set(pads.values())
    for t in b.GetTracks():
        if t.GetNetCode() > 0 and t.GetNetname() not in live:
            kill[t.m_Uuid.AsString()] = t
    log.append(f"delete {len(kill)} tracks/vias")
    print("\n".join(log))
    if dry:
        return
    for t in kill.values():
        b.Remove(t)
    with guard.claim(BOARD, "delta.py"):
        pcbnew.SaveBoard(BOARD, b)
    print("saved", BOARD)


if __name__ == "__main__":
    main(sys.argv[1:])
