"""Fabrication outputs for the selected family profile into a NEW folder
production/<profile-prefix>-<YYYYMMDD-HHMMSS>-<board sha256, 6 hex>/ (never reused).

The source board is only read. A snapshot (board, .kicad_pro, .kicad_dru, schematic set)
is copied into <release>/source-snapshot/; DRC (--schematic-parity --refill-zones
--save-board) runs on that copy, and Gerbers, drill, pos, BOM and PDF come from it. Writes
MANIFEST.txt (git commit, hashes, DRC counts, KiCad version) and ORDER-NOTES.txt (I-106,
I-105). Refuses unless DRC is 0 errors / 0 unconnected / 0 parity errors, and while KiCad
has the board open (guard.py). Any kicad-cli failure stops it.
Run with normal python:  python fab.py
Test: THERMO24_FAB_PCB / THERMO24_FAB_SCH / THERMO24_FAB_OUT point at a copy and a scratch root.
"""

from profiles import ACTIVE as P, ROOT
import csv
from pathlib import Path
import datetime
import os
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from collections import defaultdict

import guard
from release_checks import copper_layers

HERE = os.path.dirname(os.path.abspath(__file__))
HW = str(P["work_folder"])
ROOT = str(ROOT)
CLI = os.environ.get("KICAD_CLI", r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe")
PCB = os.path.abspath(os.environ.get("THERMO" + P["key"] + "_FAB_PCB") or str(P["pcb"]))
SCH = os.path.abspath(os.environ.get("THERMO" + P["key"] + "_FAB_SCH") or str(Path(PCB).with_suffix(".kicad_sch")))
OUT_ROOT = os.path.abspath(os.environ.get("THERMO" + P["key"] + "_FAB_OUT") or os.path.join(ROOT, "production"))
BARE = ("#", "H", "TP")      # power symbols, mounting holes, test pads: nothing to buy or place
LAYERS = ','.join(copper_layers(P.get('copper_layers', 4)) +
                  ('F.Paste', 'B.Paste', 'F.SilkS', 'B.SilkS', 'F.Mask', 'B.Mask', 'Edge.Cuts'))


def assembly_python():
    """Use a renderer with PyMuPDF; allow an explicit interpreter override."""
    import sys
    override = os.environ.get('ASSEMBLY_PYTHON')
    local = Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs/Python/Python310/python.exe'
    choices = [override] if override else [sys.executable, str(local)]
    for exe in dict.fromkeys(choices):
        try:
            if subprocess.run([exe, '-B', '-c', 'import fitz'], capture_output=True).returncode == 0:
                return exe
        except OSError:
            continue
    raise SystemExit('PyMuPDF renderer missing: set ASSEMBLY_PYTHON to an interpreter with fitz')

def write_order_notes(out, pcb, name):
    # Written for the supplier: a request for a quotation, not a list of conditions (owner, 2026-10-12).
    txt = P.require("order_notes")(pcb, name, board_size)
    with open(os.path.join(out, "ORDER-NOTES.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)

def git(*args):
    r = subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else "unknown"

def write_manifest(out, snap, src_sha, counts, bom, warnings):
    kv = subprocess.run([CLI, "version"], capture_output=True, text=True).stdout.strip() or "unknown"
    dirty = git("status", "--porcelain")
    lines = [f"MANIFEST {os.path.basename(out)}", f"created: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}",
             f"git commit: {git('rev-parse', 'HEAD')}",
             "git tree: " + ("unknown" if dirty == "unknown" else
                             f"DIRTY ({len(dirty.splitlines())} changed paths)" if dirty else "clean"),
             f"KiCad: {kv}", f"source board: {PCB}", f"source board sha256: {src_sha}",
             f"board after DRC refill (source-snapshot/{P['project']}.kicad_pcb) sha256: "
             f"{guard.sha256(os.path.join(snap, P['project'] + '.kicad_pcb'))}",
             f"DRC (errors, unconnected, parity; --severity-error, refilled zones): {counts}",
             f"DRC warnings (drc-warnings.rpt; both dangling kinds block release): {warnings}",
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
    pcb, sch = os.path.join(snap, (P["project"] + ".kicad_pcb")), os.path.join(snap, (P["project"] + ".kicad_sch"))
    if guard.sha256(pcb) != src_sha:
        raise SystemExit("the board changed while it was being copied - run again")
    counts = drc_counts(out, pcb)
    if counts != (0, 0, 0):
        raise SystemExit(f"DRC not clean {counts} - no fabrication files written")
    warnings = drc_warnings(out, pcb)
    kpy = os.environ.get("KICAD_PYTHON", r"C:\Program Files\KiCad\10.0\bin\python.exe")
    r = subprocess.run([kpy, os.path.join(HERE, "pincaps.py"), "--board", P["key"], "--pcb", pcb], capture_output=True, text=True)
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
    shutil.make_archive(os.path.join(out, (P["project"] + "-gerbers")), "zip", g)
    bom = bom_cpl(out, pcb, sch)
    subprocess.run([kpy, os.path.join(HERE, 'cpl_jlc.py'), '--board', P['key'], out], check=True)
    pdf = os.path.join(out, (P["project"] + "-schematic.pdf"))
    run("sch", "export", "pdf", "-o", pdf, sch, out=pdf)
    acc = os.path.join(HW, "accessories.csv")         # I-116: everything not mounted on the board
    if not os.path.exists(acc):
        raise SystemExit("accessories.csv missing beside selected board (I-116)")
    supplier_accessories(acc, os.path.join(out, "ACCESSORIES.csv"))
    write_order_notes(out, pcb, name)
    write_manifest(out, snap, src_sha, counts, bom, warnings)
    subprocess.run([assembly_python(), '-B', os.path.join(HERE, 'assembly_spec.py'),
                    '--board', P['key'], out], check=True)

def main():
    guard.check(PCB)
    src_sha = guard.sha256(PCB)
    name = f"{P.require('release_prefix')}-{datetime.datetime.now():%Y%m%d-%H%M%S}-{src_sha[:6]}"
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

# Helpers import the entry module constants; preserve one context when run as a script.
import sys
if __name__ == "__main__":
    sys.modules["fab"] = sys.modules[__name__]
from fab_ops import run, snapshot, drc_counts, drc_warnings, bom_cpl, board_size, supplier_accessories

if __name__ == "__main__":
    main()
