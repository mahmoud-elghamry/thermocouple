"""Fabrication outputs for the 24-ch board into a NEW folder
production/24ch-reva3-<YYYYMMDD-HHMMSS>-<sha256 of the board, 6 hex>/ (never reused).

The source board is only read. A snapshot (board, .kicad_pro, .kicad_dru, schematic set)
is copied into <release>/source-snapshot/; DRC (--schematic-parity --refill-zones
--save-board) runs on that copy, and Gerbers, drill, pos, BOM and PDF come from it. Writes
MANIFEST.txt (git commit, hashes, DRC counts, KiCad version) and ORDER-NOTES.txt (I-106,
I-105). Refuses unless DRC is 0 errors / 0 unconnected / 0 parity errors, and while KiCad
has the board open (guard.py). Any kicad-cli failure stops it.
Run with normal python:  python fab.py
Test: THERMO24_FAB_PCB / THERMO24_FAB_SCH / THERMO24_FAB_OUT point at a copy and a scratch root.
"""
import csv
import datetime
import os
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from collections import defaultdict

import guard

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(HW))
CLI = os.environ.get("KICAD_CLI", r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe")
PCB = os.path.abspath(os.environ.get("THERMO24_FAB_PCB") or os.path.join(HW, "thermo24.kicad_pcb"))
SCH = os.path.abspath(os.environ.get("THERMO24_FAB_SCH") or os.path.join(os.path.dirname(PCB), "thermo24.kicad_sch"))
OUT_ROOT = os.path.abspath(os.environ.get("THERMO24_FAB_OUT") or os.path.join(ROOT, "production"))
BARE = ("#", "H", "TP")      # power symbols, mounting holes, test pads: nothing to buy or place
LAYERS = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"


def run(*args, out=None, ok=(0,)):
    """kicad-cli; exit unless it ran, exited in `ok`, and wrote `out` in this call."""
    if out and os.path.exists(out):
        os.remove(out)
    t0 = time.time() - 2
    try:
        r = subprocess.run([CLI, *args], capture_output=True, text=True)
    except OSError as e:
        raise SystemExit(f"kicad-cli not runnable ({CLI}): {e}")
    if r.returncode not in ok:
        raise SystemExit(f"kicad-cli {' '.join(args[:3])} failed, exit {r.returncode}: {(r.stderr or r.stdout)[-400:]}")
    if out and (not os.path.exists(out) or os.path.getmtime(out) < t0):
        raise SystemExit(f"kicad-cli {' '.join(args[:3])} exit {r.returncode} but wrote no fresh {out}")
    return r


def snapshot(out):
    """Copy the board + its project, rules and schematic set to out/source-snapshot (as thermo24.*)."""
    snap = os.path.join(out, "source-snapshot")
    os.makedirs(snap)
    stem = os.path.splitext(PCB)[0]
    for ext in (".kicad_pcb", ".kicad_pro", ".kicad_dru"):
        if not os.path.exists(stem + ext):
            raise SystemExit(f"missing {stem + ext}: DRC without the project rules would use default 0.2 mm classes")
        shutil.copy2(stem + ext, os.path.join(snap, "thermo24" + ext))
    sd = os.path.dirname(SCH)
    for f in os.listdir(sd):
        if f.endswith(".kicad_sch") or f in ("sym-lib-table", "fp-lib-table"):
            shutil.copy2(os.path.join(sd, f), os.path.join(snap, "thermo24.kicad_sch" if f == os.path.basename(SCH) else f))
    if os.path.isdir(os.path.join(sd, "lib")):
        shutil.copytree(os.path.join(sd, "lib"), os.path.join(snap, "lib"))
    return snap


def drc_counts(out, pcb):
    rpt = os.path.join(out, "drc-report.rpt")
    # --save-board: the plotted pours are exactly the ones DRC checked (scripts save boards unfilled)
    run("pcb", "drc", "--schematic-parity", "--refill-zones", "--save-board", "--severity-error", "-o", rpt, pcb,
        out=rpt, ok=(0, 5))
    txt = open(rpt, encoding="utf-8").read()
    m = re.search(r"\*\* Found (\d+) DRC violations", txt)
    u = re.search(r"\*\* Found (\d+) unconnected pads", txt)
    p = re.search(r"\*\* Found (\d+) Footprint errors", txt)
    counts = tuple(int(x.group(1)) if x else -1 for x in (m, u, p))
    print("DRC errors/unconnected/parity:", counts)
    return counts


def bom_cpl(out, pcb, sch):
    xml = os.path.join(out, "netlist.xml")
    run("sch", "export", "netlist", "--format", "kicadxml", "-o", xml, sch, out=xml)
    lines = defaultdict(list)
    for c in ET.parse(xml).getroot().iter("comp"):
        f = {x.get("name"): x.text or "" for x in c.iter("field")}
        fp = (c.findtext("footprint") or "").split(":")[-1]
        if not fp or c.get("ref").startswith(BARE):
            continue
        key = (c.findtext("value"), fp, f.get("LCSC", ""), f.get("MPN", ""))
        lines[key].append(c.get("ref"))
    with open(os.path.join(out, "BOM-JLCPCB.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC", "MPN", "Qty"])
        for (val, fp, lcsc, mpn), refs in sorted(lines.items(), key=lambda kv: kv[1][0]):
            w.writerow([val, ",".join(sorted(refs)), fp, lcsc, mpn, len(refs)])
    pos = os.path.join(out, "pos.csv")
    run("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both", "-o", pos, pcb, out=pos)
    with open(pos, encoding="utf-8") as fi, open(os.path.join(out, "CPL-JLCPCB.csv"), "w", newline="",
                                                   encoding="utf-8") as fo:
        r, w = csv.DictReader(fi), csv.writer(fo)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for row in r:
            if row["Ref"].startswith(BARE):
                continue
            w.writerow([row["Ref"], row["PosX"] + "mm", row["PosY"] + "mm",
                        "Top" if row["Side"] == "top" else "Bottom", row["Rot"]])
    missing = [refs for (v, fp, l, m), refs in lines.items() if not l]
    print(f"BOM: {len(lines)} lines; without LCSC code: {missing}")
    return len(lines), missing


def board_size(pcb):
    """Bounding box (mm) of the Edge.Cuts lines/rects/arcs in the board file."""
    pts = []
    with open(pcb, encoding="utf-8") as f:
        for chunk in re.split(r"\n\t\((?=gr_)", f.read()):
            if '(layer "Edge.Cuts")' in chunk and chunk.startswith(("gr_line", "gr_rect", "gr_arc")):
                pts += [(float(a), float(b)) for a, b in re.findall(r"\((?:start|end|mid) ([-\d.]+) ([-\d.]+)\)", chunk)]
    if not pts:
        return "unknown (no Edge.Cuts lines found)"
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return f"{max(xs) - min(xs):.1f} x {max(ys) - min(ys):.1f} mm"


def write_order_notes(out, pcb, name):
    txt = f"""ORDER NOTES - {name}
Board: Thermo 24-channel protection unit, REV A3. Size (Edge.Cuts): {board_size(pcb)}.
These are order instructions (I-106). Where and how you assemble is your business; this is what the board needs.

PCB
- 4 layers, FR4, 1.6 mm finished, 1 oz copper on all layers.
- ENIG surface finish (the 0.5 mm LFCSP parts need a flat finish).
- All vias tented (mask over every via).
- Files: gerber/ (Gerbers + drill) and thermo24-gerbers.zip.

ASSEMBLY
- Turnkey: you buy every part from the LCSC codes in BOM-JLCPCB.csv; CPL-JLCPCB.csv is the placement list.
- Top-side assembly. Use our paste layer as is: window-pane paste on the exposed pads (AD7124, LM5164);
  U601's exposed-pad vias are tented, no paste fill through them.
- Wash the flux off after reflow.
- No part substitution without our written approval. Customs and shipping are yours.

CONFORMAL COATING (I-105) - done by NORI if offered, otherwise by us after delivery
Why: 3.2 k in series per leg turns ~10 Mohm of surface leakage into ~4 degC; keep R_leak > ~120 Mohm per node.
1. Wash the assembled board with isopropyl alcohol (IPA), brush the sensor-input area; no flux residue left.
2. Dry completely (oven or warm air, then cool).
3. Mask: connectors J*, pin headers, buttons, relays, the LCD header.
4. Spray acrylic conformal coating to IPC-CC-830, thin even coats on the top and bottom sides.
5. Cure as the coating's datasheet says.
6. Inspect (under UV if the coating has a tracer); remove the masking; re-check the masked parts are clean.
"""
    with open(os.path.join(out, "ORDER-NOTES.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)


def git(*args):
    r = subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else "unknown"


def write_manifest(out, snap, src_sha, counts, bom):
    kv = subprocess.run([CLI, "version"], capture_output=True, text=True).stdout.strip() or "unknown"
    dirty = git("status", "--porcelain")
    lines = [f"MANIFEST {os.path.basename(out)}", f"created: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}",
             f"git commit: {git('rev-parse', 'HEAD')}",
             "git tree: " + ("unknown" if dirty == "unknown" else
                             f"DIRTY ({len(dirty.splitlines())} changed paths)" if dirty else "clean"),
             f"KiCad: {kv}", f"source board: {PCB}", f"source board sha256: {src_sha}",
             f"board after DRC refill (source-snapshot/thermo24.kicad_pcb) sha256: "
             f"{guard.sha256(os.path.join(snap, 'thermo24.kicad_pcb'))}",
             f"DRC (errors, unconnected, parity; --severity-error, refilled zones): {counts}",
             f"BOM lines: {bom[0]}; lines without LCSC code: {len(bom[1])}", "schematic set sha256:"]
    for f in sorted(os.listdir(snap)):
        if f.endswith(".kicad_sch"):
            lines.append(f"  {guard.sha256(os.path.join(snap, f))}  {f}")
    lines.append("every output file sha256 (all files in this folder except this one):")
    for d, _, fs in sorted(os.walk(out)):
        for f in sorted(fs):
            if f != "MANIFEST.txt" or d != out:
                p = os.path.join(d, f)
                lines.append(f"  {guard.sha256(p)}  {os.path.relpath(p, out).replace(os.sep, '/')}")
    with open(os.path.join(out, "MANIFEST.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def release(out, name, src_sha):
    snap = snapshot(out)
    pcb, sch = os.path.join(snap, "thermo24.kicad_pcb"), os.path.join(snap, "thermo24.kicad_sch")
    if guard.sha256(pcb) != src_sha:
        raise SystemExit("the board changed while it was being copied - run again")
    counts = drc_counts(out, pcb)
    if counts != (0, 0, 0):
        raise SystemExit(f"DRC not clean {counts} - no fabrication files written")
    kpy = os.environ.get("KICAD_PYTHON", r"C:\Program Files\KiCad\10.0\bin\python.exe")
    r = subprocess.run([kpy, os.path.join(HERE, "pincaps.py"), pcb], capture_output=True, text=True)
    with open(os.path.join(out, "pincaps.txt"), "w", encoding="utf-8") as f:
        f.write(r.stdout)
    if r.returncode != 0:                 # I-111: decoupling beside its pin is a release gate
        bad = [ln for ln in r.stdout.splitlines() if ln.startswith(("BAD", "pincaps"))]
        raise SystemExit("pincaps.py: caps not beside their pins - no fabrication files written\n"
                         + "\n".join(bad))
    g = os.path.join(out, "gerber")
    os.makedirs(g)
    run("pcb", "export", "gerbers", "--check-zones", "--subtract-soldermask", "--layers", LAYERS, "-o", g + os.sep, pcb)
    run("pcb", "export", "drill", "--generate-map", "--map-format", "pdf", "-o", g + os.sep, pcb)
    names = os.listdir(g)
    if len(names) < len(LAYERS.split(",")) or not any(n.endswith(".drl") for n in names):
        raise SystemExit(f"kicad-cli wrote too few Gerber/drill files: {names}")
    shutil.make_archive(os.path.join(out, "thermo24-gerbers"), "zip", g)
    bom = bom_cpl(out, pcb, sch)
    pdf = os.path.join(out, "thermo24-schematic.pdf")
    run("sch", "export", "pdf", "-o", pdf, sch, out=pdf)
    acc = os.path.join(HW, "accessories.csv")         # I-116: everything not mounted on the board
    if not os.path.exists(acc):
        raise SystemExit("hardware/24ch/accessories.csv missing (I-116)")
    shutil.copy(acc, os.path.join(out, "ACCESSORIES.csv"))
    write_order_notes(out, pcb, name)
    write_manifest(out, snap, src_sha, counts, bom)


def main():
    guard.check(PCB)
    src_sha = guard.sha256(PCB)
    name = f"24ch-reva3-{datetime.datetime.now():%Y%m%d-%H%M%S}-{src_sha[:6]}"
    out = os.path.join(OUT_ROOT, name)
    if os.path.exists(out):
        raise SystemExit(f"release folder exists, refusing to reuse it: {out}")
    os.makedirs(out)
    try:
        release(out, name, src_sha)
    except BaseException:
        os.rename(out, out + "-FAILED")      # never leave a half-written folder that looks like a release
        print(f"NOT A RELEASE - partial output kept in {out}-FAILED")
        raise
    print("written:", out)


if __name__ == "__main__":
    main()
