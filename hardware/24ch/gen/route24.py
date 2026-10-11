"""Route the 24-ch board with Freerouting (pcbnew -> DSN -> Freerouting -> SES -> pcbnew).

Same method as hardware/8ch/route.py, In1/In2 are planes and fanout.py has already
connected every plane pad (order: rules.py --route-prep, fanout.py, route24.py, rules.py), and DSN clearances get a small pad so Freerouting's
rounding still meets KiCad's DRC. Run with KiCad's python:
    python route24.py --passes 30 --threads 4
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "output"
BOARD = HERE.parent / "thermo24.kicad_pcb"
DSN, SES, LOG = OUT / "thermo24.dsn", OUT / "thermo24.ses", OUT / "freerouting.log"
PAD = 40            # um added to every DSN clearance so Freerouting's rounding meets KiCad DRC
CLASS_CLASS = []    # (class, other classes, clearance mm): .kicad_dru pair rules the router must see
TOOLS = Path(os.environ.get("KICAD_TOOLS_DIR", Path.home() / "AppData/Local/kicad-tools"))
JAR = Path(os.environ.get("FREEROUTING_JAR", TOOLS / "freerouting.jar"))
MIN_TRACK_MM = 0.20


def java():
    if os.environ.get("FREEROUTING_JAVA"):
        return Path(os.environ["FREEROUTING_JAVA"])
    found = sorted((TOOLS / "jre25").glob("*/bin/java.exe"))
    if not found:
        raise SystemExit("no JRE under " + str(TOOLS / "jre25"))
    return found[-1]


def export_dsn():
    OUT.mkdir(exist_ok=True)
    b = pcbnew.LoadBoard(str(BOARD))
    if not pcbnew.ExportSpecctraDSN(b, str(DSN)):
        raise SystemExit("DSN export failed")
    text = DSN.read_text(encoding="utf-8", errors="replace")
    for layer in ("In1.Cu", "In2.Cu"):   # planes; plane pads are fanned out by fanout.py
        pat = re.compile(r"(\(layer\s+" + re.escape(layer) + r"\s*\n\s*\(type\s+)signal(\s*\))")
        text, n = pat.subn(r"\1power\2", text)
        if n != 1:
            raise SystemExit(f"could not mark {layer} as power ({n})")
    text = re.sub(r"\(clearance (\d+)\)", lambda m: f"(clearance {int(m.group(1)) + PAD})", text)
    rules = "".join(f"    (class_class (classes {a} {b}) (rule (clearance {int(clr * 1000) + PAD})))\n"
                    for a, others, clr in CLASS_CLASS for b in others)
    if rules:
        i = text.rindex("  (wiring")
        j = text.rindex(")", 0, i)          # close of (network ...)
        text = text[:j] + rules + "  " + text[j:]
    DSN.write_text(text, encoding="utf-8")
    print("exported", DSN)


def run(passes, threads):
    cmd = [str(java()), "-jar", str(JAR), "-de", str(DSN), "-do", str(SES),
           "-mp", str(passes), "-mt", str(threads)]
    print("running:", " ".join(cmd), flush=True)
    with LOG.open("w", encoding="utf-8") as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, text=True)
    print("\n".join(LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-8:]))
    if r.returncode != 0 or not SES.exists():
        raise SystemExit(f"freerouting failed ({r.returncode}); see {LOG}")


def import_ses():
    b = pcbnew.LoadBoard(str(BOARD))
    if not pcbnew.ImportSpecctraSES(b, str(SES)):
        raise SystemExit("SES import failed")
    narrow = redrilled = 0
    for t in list(b.GetTracks()):
        if t.Type() == pcbnew.PCB_VIA_T:
            w = pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu))
            if w - pcbnew.ToMM(t.GetDrillValue()) < 0.30 - 1e-6:
                t.SetDrill(pcbnew.FromMM(round(w - 0.30, 3)))
                redrilled += 1
        elif pcbnew.ToMM(t.GetWidth()) < MIN_TRACK_MM - 1e-6:
            t.SetWidth(pcbnew.FromMM(MIN_TRACK_MM))
            narrow += 1
    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    pcbnew.SaveBoard(str(BOARD), b)
    print(f"imported {SES.name}: widened {narrow} segments, re-drilled {redrilled} vias, zones refilled")


def main():
    global BOARD, DSN, SES, LOG, PAD
    ap = argparse.ArgumentParser()
    ap.add_argument("--passes", type=int, default=30)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--import-only", action="store_true")
    ap.add_argument("--board", help="route a copy instead of thermo24.kicad_pcb")
    ap.add_argument("--tag", default="", help="suffix for the DSN/SES/log of a parallel run")
    ap.add_argument("--pad", type=int, default=PAD, help="um added to DSN clearances")
    ap.add_argument("--no-pair-rules", action="store_true",
                    help="do not pass the contact (2 mm) / chassis (1.5 mm) pair rules to the router")
    a = ap.parse_args()
    PAD = a.pad
    if a.board:
        BOARD = Path(a.board).resolve()
    if a.tag:
        DSN, SES, LOG = (OUT / f"thermo24-{a.tag}.dsn", OUT / f"thermo24-{a.tag}.ses",
                         OUT / f"freerouting-{a.tag}.log")
    if not a.no_pair_rules:   # 2026-10-09: without them a run gave 29 contact / 9 chassis violations
        classes = ("kicad_default", "Island", "IslandPower", "CtrlPower", "Power24V", "RS485",
                   "Chassis", "Contact")
        CLASS_CLASS.append(("Contact", [c for c in classes if c != "Contact"], 2.0))
        CLASS_CLASS.append(("Chassis", [c for c in classes if c not in ("Chassis", "Contact")], 1.5))
    if not a.import_only:
        export_dsn()
        run(a.passes, a.threads)
    import_ses()


if __name__ == "__main__":
    import guard      # I-115: refuse while KiCad or another tool holds the board
    with guard.claim(str(BOARD), "route24.py"):
        main()
