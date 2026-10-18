"""Generate a family schematic, gate ERC and check the netlist against the model.

    python hardware/family/gen/build.py 24 --out hardware/family/out/24
"""
import argparse
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections import defaultdict

import customlib
from boards import BOARDS
from model import Part, Sheet
from emit import SheetWriter, uid, effects, prop
from sexp import Sym, dump
from c_bank import bank
from c_rtd import rtd_bank
from c_iso import isolation
from c_mcu import mcu
from c_out import outputs
from c_power import power

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = BOARDS["24"]
OUT = str(CONFIG.output_folder)
LIB = os.path.join(OUT, "lib")
PROJECT = CONFIG.project
ROOT_UUID = uid("root")
CLI = os.environ.get("KICAD_CLI", r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe")


def sheets():
    return [power(), mcu(CONFIG), isolation(CONFIG), outputs()] + [
        bank(b, CONFIG) for b in range(1, CONFIG.bank_count + 1)] + ([rtd_bank(CONFIG)] if CONFIG.rtd else [])


def add_flags(all_sheets):
    for s in all_sheets:
        if s.flags:
            s.block("Power flags (ERC only)", [
                Part(f"#FLG{s.name[:3]}{i}", "power:PWR_FLAG", "PWR_FLAG", {"1": net}, "",
                     in_bom=False, on_board=False) for i, net in enumerate(s.flags)])


PRINTABLE = ("A4", "A3")     # the owner prints A4 or A3 only (2026-10-08)


def paginate(s, all_nets):
    """Split a sheet into A3-or-smaller pages, keeping its blocks in order.

    Fit is tested with every net drawn as a (longer) global label, so the real
    page never comes out bigger than the test page."""
    def fits(blocks):
        t = Sheet(s.name, s.file, s.title, "A4")
        t.blocks = blocks
        SheetWriter(t, all_nets, PROJECT, ROOT_UUID, None, LIB, CONFIG).layout()
        return t.paper in PRINTABLE
    pages, cur = [], []
    for blk in s.blocks:
        if cur and not fits(cur + [blk]):
            pages.append(cur)
            cur = []
        cur.append(blk)
    pages.append(cur)
    if len(pages) == 1:
        s.paper = "A4"
        return [s]
    out = []
    base = s.file[:-len(".kicad_sch")]
    for i, blocks in enumerate(pages, 1):
        t = Sheet(f"{s.name}_{i}", f"{base}_{i}.kicad_sch", f"{s.title} - page {i}/{len(pages)}", "A4")
        t.blocks = blocks
        t.notes = s.notes if i == 1 else []
        out.append(t)
    return out


def root_parts():
    holes = []
    for i, kind in CONFIG.mounting_holes:
        if kind == "chassis":
            holes.append(Part(f"H{i}", "Mechanical:MountingHole_Pad", "M3 CHASSIS", {"1": "CHASSIS"},
                              "MountingHole:MountingHole_3.2mm_M3_Pad"))
        else:
            value = {"island": "M3 NPTH island", "lcd": "M3 LCD standoff", "plain": "M3 NPTH"}[kind]
            holes.append(Part(f"H{i}", "Mechanical:MountingHole", value, {},
                              "MountingHole:MountingHole_3.2mm_M3",
                              desc="insulating spacer" if kind == "island" else ""))
    return holes


def sheet_block(s, x, y, page):
    su = uid(f"sheet:{s.name}")
    w, h = 50.8, 20.32
    return su, [Sym("sheet"), [Sym("at"), x, y], [Sym("size"), w, h],
                [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")],
                [Sym("on_board"), Sym("yes")], [Sym("dnp"), Sym("no")],
                [Sym("fields_autoplaced"), Sym("yes")],
                [Sym("stroke"), [Sym("width"), 0.1524], [Sym("type"), Sym("solid")]],
                [Sym("fill"), [Sym("color"), 0, 0, 0, 0.0]], [Sym("uuid"), su],
                prop("Sheetname", s.name, x, y - 0.7, justify="left bottom"),
                prop("Sheetfile", s.file, x, y + h + 0.6, justify="left top"),
                [Sym("instances"), [Sym("project"), PROJECT,
                 [Sym("path"), f"/{ROOT_UUID}", [Sym("page"), str(page)]]]]]


def generate(config, out, mutate=None):
    """Write sheets only. Optional model mutation is used by fault-proof scratch builds."""
    global CONFIG, OUT, LIB, PROJECT
    CONFIG, OUT, PROJECT = config, os.path.abspath(out), config.project
    LIB = os.path.join(OUT, "lib")
    os.makedirs(OUT, exist_ok=True)
    customlib.write(os.path.join(LIB, f"{CONFIG.library}.kicad_sym"), PROJECT)
    all_sheets = sheets()
    if mutate:
        mutate(all_sheets)
    add_flags(all_sheets)
    all_nets = {n for sh in all_sheets for p in sh.parts() for n in p.resolve(LIB).values()}
    all_sheets = [pg for sh in all_sheets for pg in paginate(sh, all_nets)]
    for f in os.listdir(OUT):       # pages from an earlier split that no longer exist
        if f.endswith(".kicad_sch") and f != f"{PROJECT}.kicad_sch" and f not in {sh.file for sh in all_sheets}:
            os.remove(os.path.join(OUT, f))
    root = Sheet("ROOT", f"{PROJECT}.kicad_sch", CONFIG.root_title, "A3")
    root.block("Mounting holes: island NPTH + insulating spacers, control plated to CHASSIS, LCD standoffs",
               root_parts())
    model_parts = {}
    net_sheets = defaultdict(set)
    for s in all_sheets + [root]:
        for p in s.parts():
            if p.ref in model_parts:
                raise SystemExit(f"duplicate reference {p.ref}")
            model_parts[p.ref] = p
            for net in p.resolve(LIB).values():
                if net != "<NC>":
                    net_sheets[net].add(s.name)
    glob = {n for n, ss in net_sheets.items() if len(ss) > 1}
    blocks = []
    for i, s in enumerate(all_sheets):
        su, blk = sheet_block(s, 25.4 + (i % 5) * 76.2, 120 + (i // 5) * 35.56, i + 2)
        blocks.append(blk)
        text = SheetWriter(s, glob, PROJECT, ROOT_UUID, su, LIB, CONFIG).build()
        with open(os.path.join(OUT, s.file), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    text = SheetWriter(root, glob, PROJECT, ROOT_UUID, None, LIB, CONFIG).build(extra=blocks)
    with open(os.path.join(OUT, root.file), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    write_project()
    fplibs = sorted({p.footprint.split(":")[0] for p in model_parts.values() if p.footprint})
    with open(os.path.join(OUT, "fp-lib-table"), "w", encoding="utf-8", newline="\n") as f:
        f.write("(fp_lib_table\n  (version 7)\n")
        for lib in fplibs:
            f.write(f'  (lib (name "{lib}") (type "KiCad") (uri "${{KICAD10_FOOTPRINT_DIR}}/{lib}.pretty")'
                    ' (options "") (descr ""))\n')
        f.write(")\n")
    print(f"{len(model_parts)} symbols, {len(net_sheets)} nets ({len(glob)} global)")
    big = [f"{sh.file}={sh.paper}" for sh in all_sheets + [root] if sh.paper not in PRINTABLE]
    print("pages:", ", ".join(f"{sh.file}={sh.paper}" for sh in all_sheets + [root]))
    if big:
        raise SystemExit(f"pages larger than A3: {big}")
    return model_parts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board", choices=BOARDS)
    parser.add_argument("--out", help="output directory (default hardware/family/out/<board>)")
    args = parser.parse_args()
    config = BOARDS[args.board]
    parts = generate(config, args.out or config.output_folder)
    ok = run_erc() & check_netlist(parts)
    from bom import write_bom
    write_bom(os.path.join(OUT, f"{PROJECT}.xml"), OUT)
    return 0 if ok else 1


def write_project():
    pro = os.path.join(OUT, f"{PROJECT}.kicad_pro")
    if not os.path.exists(pro):
        with open(pro, "w", encoding="utf-8") as f:
            json.dump({"meta": {"filename": f"{PROJECT}.kicad_pro", "version": 3}}, f, indent=2)
    table = os.path.join(OUT, "sym-lib-table")
    with open(table, "w", encoding="utf-8", newline="\n") as f:
        f.write('(sym_lib_table\n  (version 7)\n'
                f'  (lib (name "{CONFIG.library}")(type "KiCad")'
                f'(uri "${{KIPRJMOD}}/lib/{CONFIG.library}.kicad_sym")'
                '(options "")(descr "project parts"))\n)\n')


def kicad(args, out, ok=(0,)):
    """Run kicad-cli; return (returncode, text of `out`). Exits unless the tool ran,
    returned one of `ok`, and wrote `out` during this call (an old file proves nothing)."""
    if os.path.exists(out):
        os.remove(out)
    t0 = time.time() - 2          # file-system mtime granularity
    try:
        r = subprocess.run([CLI, *args], capture_output=True, text=True)
    except OSError as e:
        raise SystemExit(f"kicad-cli not runnable ({CLI}): {e}")
    if r.returncode not in ok:
        raise SystemExit(f"kicad-cli {' '.join(args[:3])} failed, exit {r.returncode}: "
                         f"{(r.stderr or r.stdout)[-400:]}")
    if not os.path.exists(out) or os.path.getmtime(out) < t0:
        raise SystemExit(f"kicad-cli {' '.join(args[:3])} exit {r.returncode} but wrote no fresh {out}")
    with open(out, encoding="utf-8") as f:
        return r.returncode, f.read()


def run_erc():
    """ERC gate: 0 errors and 0 warnings. kicad-cli exit 5 = violations found (fail, report
    printed); any other non-zero exit, or no fresh report, is a tool failure (exit)."""
    rpt = os.path.join(OUT, "erc-report.rpt")
    rc, txt = kicad(["sch", "erc", "--exit-code-violations", "--severity-error", "--severity-warning",
                     "-o", rpt, os.path.join(OUT, f"{PROJECT}.kicad_sch")], rpt, ok=(0, 5))
    tail = [l for l in txt.splitlines() if "ERC messages" in l or "Errors" in l]
    print("ERC:", " | ".join(tail) or txt[-300:], f"(kicad-cli exit {rc})")
    return rc == 0 and "** ERC messages: 0" in txt


def check_netlist(model_parts):
    xml = os.path.join(OUT, f"{PROJECT}.xml")
    _, txt = kicad(["sch", "export", "netlist", "--format", "kicadxml", "-o", xml,
                    os.path.join(OUT, f"{PROJECT}.kicad_sch")], xml)
    r = ET.fromstring(txt)
    got = {}
    for n in r.iter("net"):
        name = n.get("name").rsplit("/", 1)[-1]
        for nd in n.iter("node"):
            got[(nd.get("ref"), nd.get("pin"))] = name
    bad = 0
    for ref, p in model_parts.items():
        if ref.startswith("#"):
            continue
        for pin, net in p.pinmap.items():
            g = got.get((ref, pin))
            want_nc = net == "<NC>"
            if want_nc and (g is None or g.startswith("unconnected-")):
                continue
            if g != net:
                bad += 1
                if bad <= 20:
                    print(f"  NETLIST MISMATCH {ref}.{pin}: model {net} vs schematic {g}")
    comps = {c.get("ref") for c in r.iter("comp")}
    missing = [x for x in model_parts if not x.startswith("#") and x not in comps]
    print(f"netlist check: {bad} pin mismatches, {len(missing)} missing parts")
    return bad == 0 and not missing


if __name__ == "__main__":
    sys.exit(main())
