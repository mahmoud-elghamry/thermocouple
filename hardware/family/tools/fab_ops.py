"""Copied algorithms; constants come from the entry tool and its profile."""
from fab import *

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
        shutil.copy2(stem + ext, os.path.join(snap, P["project"] + ext))
    sd = os.path.dirname(SCH)
    for f in os.listdir(sd):
        if f.endswith(".kicad_sch") or f in ("sym-lib-table", "fp-lib-table"):
            shutil.copy2(os.path.join(sd, f), os.path.join(snap, (P["project"] + ".kicad_sch") if f == os.path.basename(SCH) else f))
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


def drc_warnings(out, pcb):
    """All warnings remain reviewable; both dangling kinds stop fabrication."""
    from release_checks import warning_summary
    rpt = os.path.join(out, 'drc-warnings.rpt')
    run('pcb', 'drc', '--schematic-parity', '--severity-all', '-o', rpt, pcb,
        out=rpt, ok=(0, 5))
    text = Path(rpt).read_text(encoding='utf-8')
    kinds = defaultdict(int)
    for kind in re.findall(r'^\[([a-z_]+)\]', text, re.M):
        kinds[kind] += 1
    summary = ', '.join(f'{k} {n}' for k, n in sorted(kinds.items())) or 'none'
    Path(out, 'DRC-WARNINGS.txt').write_text(
        'All-severity DRC: ' + summary + '\n'
        'Release blockers: track_dangling and via_dangling (any count).\n', encoding='utf-8')
    print('DRC warnings:', summary)
    try:
        warning_summary(text)
    except ValueError as exc:
        raise SystemExit(f'{exc}; no fabrication files written') from exc
    return summary


def bom_cpl(out, pcb, sch):
    xml = os.path.join(out, "netlist.xml")
    run("sch", "export", "netlist", "--format", "kicadxml", "-o", xml, sch, out=xml)
    lines, dnp = defaultdict(list), []
    for c in ET.parse(xml).getroot().iter("comp"):
        f = {x.get("name"): x.text or "" for x in c.iter("field")}
        fp = (c.findtext("footprint") or "").split(":")[-1]
        if not fp or c.get("ref").startswith(BARE):
            continue
        if any(p.get("name") == "dnp" for p in c.iter("property")):
            dnp.append(c.get("ref"))     # footprint on the board, part not fitted (0036)
            continue
        key = (c.findtext("value"), fp, f.get("LCSC", ""), f.get("MPN", ""))
        lines[key].append(c.get("ref"))
    with open(os.path.join(out, "BOM.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC (reference)", "MPN", "Qty"])
        for (val, fp, lcsc, mpn), refs in sorted(lines.items(), key=lambda kv: kv[1][0]):
            w.writerow([val, ",".join(sorted(refs)), fp, lcsc, mpn, len(refs)])
    pos = os.path.join(out, "pos.csv")
    run("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both", "--exclude-dnp",
        "-o", pos, pcb, out=pos)
    with open(pos, encoding="utf-8") as fi, open(os.path.join(out, "CPL.csv"), "w", newline="",
                                                   encoding="utf-8") as fo:
        r, w = csv.DictReader(fi), csv.writer(fo)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for row in r:
            if row["Ref"].startswith(BARE) or row["Ref"] in dnp:
                continue
            w.writerow([row["Ref"], row["PosX"] + "mm", row["PosY"] + "mm",
                        "Top" if row["Side"] == "top" else "Bottom", row["Rot"]])
    missing = [refs for (v, fp, l, m), refs in lines.items() if not l]
    with open(os.path.join(out, "DNP.txt"), "w", encoding="utf-8") as fh:
        fh.write("Footprints that stay empty on this order (please do not fit):\n"
                 + (" ".join(sorted(dnp)) if dnp else "none - every footprint is fitted") + "\n")
    print(f"BOM: {len(lines)} lines; without LCSC code: {missing}; DNP: {len(dnp)}")
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


def supplier_accessories(src, dst):
    """The supplier's copy of accessories.csv: only what they could supply (an LCSC reference, the
    board standoffs or the RS-485 jumper shunts), no internal status notes (0036 D8)."""
    with open(src, encoding="utf-8") as fi:
        rows = list(csv.DictReader(fi))
    with open(dst, "w", newline="", encoding="utf-8") as fo:
        w = csv.writer(fo)
        w.writerow(["Item", "Qty per board", "Reference part (LCSC)", "MPN", "Maker"])
        for r in rows:
            item = r["Item"]
            if not (r["LCSC"] or item.lower().startswith(("board standoffs", "jumper shunts"))):
                continue
            w.writerow([item, r["Qty per board"], r["LCSC"], r["MPN"], r["Maker"]])


