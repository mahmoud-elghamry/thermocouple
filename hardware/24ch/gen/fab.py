"""Fabrication outputs for the 24-ch board into production/24ch-reva3-<date>/.

Gerbers + drill (zipped), a JLCPCB/LCSC-style BOM (Comment, Designator,
Footprint, LCSC) and CPL (Designator, Mid X, Mid Y, Layer, Rotation), plus the
schematic PDF. Refuses unless the DRC report shows zero errors.
Run with normal python:  python fab.py
"""
import csv
import datetime
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(HW))
CLI = os.environ.get("KICAD_CLI", r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe")
PCB = os.path.join(HW, "thermo24.kicad_pcb")
SCH = os.path.join(HW, "thermo24.kicad_sch")
BARE = ("#", "H", "TP")      # power symbols, mounting holes, test pads: nothing to buy or place
LAYERS = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"


def run(*args):
    r = subprocess.run([CLI, *args], capture_output=True, text=True)
    if r.returncode not in (0, 5):
        raise SystemExit(f"kicad-cli {' '.join(args[:3])} failed: {r.stderr[-400:]}")
    return r


def drc_ok(out):
    rpt = os.path.join(out, "drc-report.rpt")
    # --save-board: the plotted pours are exactly the ones DRC checked (scripts save boards unfilled)
    run("pcb", "drc", "--schematic-parity", "--refill-zones", "--save-board", "--severity-error", "-o", rpt, PCB)
    txt = open(rpt, encoding="utf-8").read()
    m = re.search(r"\*\* Found (\d+) DRC violations", txt)
    u = re.search(r"\*\* Found (\d+) unconnected pads", txt)
    p = re.search(r"\*\* Found (\d+) Footprint errors", txt)
    counts = tuple(int(x.group(1)) if x else -1 for x in (m, u, p))
    print("DRC errors/unconnected/parity:", counts)
    return counts == (0, 0, 0)


def bom_cpl(out):
    xml = os.path.join(out, "netlist.xml")
    run("sch", "export", "netlist", "--format", "kicadxml", "-o", xml, SCH)
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
    run("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both", "-o", pos, PCB)
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


def main():
    out = os.path.join(ROOT, "production", f"24ch-reva3-{datetime.date.today():%Y%m%d}")
    os.makedirs(out, exist_ok=True)
    if not drc_ok(out):
        raise SystemExit("DRC not clean - no fabrication files written")
    g = os.path.join(out, "gerber")
    os.makedirs(g, exist_ok=True)
    run("pcb", "export", "gerbers", "--check-zones", "--subtract-soldermask", "--layers", LAYERS, "-o", g + os.sep, PCB)
    run("pcb", "export", "drill", "--generate-map", "--map-format", "pdf", "-o", g + os.sep, PCB)
    shutil.make_archive(os.path.join(out, "thermo24-gerbers"), "zip", g)
    bom_cpl(out)
    run("sch", "export", "pdf", "-o", os.path.join(out, "thermo24-schematic.pdf"), SCH)
    print("written:", out)


if __name__ == "__main__":
    main()
