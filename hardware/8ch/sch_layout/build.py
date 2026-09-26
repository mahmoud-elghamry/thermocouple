"""Redraw thermocouple_8ch.kicad_sch as a readable drawing (I-002).

    python hardware/8ch/sch_layout/build.py              # into a scratch copy
    python hardware/8ch/sch_layout/build.py --in-place   # rewrite the schematic

Starts from a label-only schematic - every net carried by labels sitting on
pins, no wires - as committed at BASE (default 05d6abd, the last one before
the redraw), so every run is the same run and nothing depends on what a
previous run left behind. It refuses a base that already has wires: the
router does not know about wires it did not draw. After a generator change,
pass the commit holding the generator's new label-only output as --base. Steps, all of
them writes through Konnect (docs/decisions/0013):

  1. fixes.py     netlist corrections the drawing carries (I-058, I-057)
  2. relayout     channel template (channel.py) + the other blocks (extra.py)
  3. fields       Reference/Value back to where the library anchors them
  4. route.py     short orthogonal wires between pins of the same net that
                  never touch another net's pin, wire or a part body
  5. labels.py    one label per wired group, placed where its text fits
  6. hier.py      split into the A3 root + channel.kicad_sch used 8 times
                  (I-062); rootlayout.py packs the root blocks onto A3

Then the gate, on the hierarchical result: kicad-cli exports the netlist,
netlist_fingerprint.py must report IDENTICAL against netlist-baseline-reva1.json
(which carries the hierarchical net names since I-062), and ERC must have no
errors. A failure leaves the scratch copy for inspection and, with
--in-place, the schematic put back as it was.

Needs konnect and kicad-cli on PATH (docs/TOOLS.md), and KICAD10_SYMBOL_DIR
pointing at KiCad's symbol libraries for the U12 relink.
"""
import json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(HW))
SCH_REL = "hardware/8ch/thermocouple_8ch.kicad_sch"
sys.path.insert(0, HERE)


def run(*cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def main():
    in_place = "--in-place" in sys.argv
    base = sys.argv[sys.argv.index("--base") + 1] if "--base" in sys.argv else "05d6abd"
    work = tempfile.mkdtemp(prefix="sch_layout-")
    # The flat, wired sheet is an intermediate since I-062: it is built in the
    # scratch folder and hier.py turns it into the root + channel sheet.
    sch = os.path.join(work, "thermocouple_8ch.kicad_sch")
    out = HW if in_place else os.path.join(work, "hier")
    originals = {f: open(os.path.join(HW, f), "rb").read()
                 for f in ("thermocouple_8ch.kicad_sch", "channel.kicad_sch")
                 if os.path.exists(os.path.join(HW, f))}
    head = subprocess.run(["git", "-C", REPO, "show", base + ":" + SCH_REL], check=True,
                          capture_output=True).stdout
    if b"(wire" in head:
        raise SystemExit(f"{base} already has wires - pass a label-only --base")
    open(sch, "wb").write(head)
    shutil.copy(os.path.join(HW, "thermocouple_8ch.kicad_pro"), os.path.dirname(sch))
    try:
        build(sch, work)
        flat_net = os.path.join(work, "flat.net")
        run("kicad-cli", "sch", "export", "netlist", "--output", flat_net, sch)
        run(sys.executable, os.path.join(HERE, "hier.py"), sch, flat_net, out)
        gate(os.path.join(out, "thermocouple_8ch.kicad_sch"), work)
    except BaseException:
        if in_place:
            for f, data in originals.items():
                open(os.path.join(HW, f), "wb").write(data)
            print("FAILED - schematic restored; scratch in", work)
        raise
    print("OK -", out)


def build(sch, work):
    import fixes, relayout, channel, extra
    from chmap import channel_refs
    fixes.apply(sch)
    m, _ = channel_refs(sch)
    spec = {}
    for n, refs in m.items():
        r = list(refs); r[6] = "C%d" % (5 * n - 1); r[7] = "C%d" % (5 * n)
        spec.update(channel.channel(channel.UX[n], channel.UY[n], r))
    spec.update(extra.spec())
    k = relayout.apply(sch, spec)
    k.load("sch_components")
    k.call("reset_schematic_field_positions", schematic=sch)
    plan = os.path.join(work, "plan.json")
    run(sys.executable, os.path.join(HERE, "route.py"), sch, plan)
    from kon import K
    pl = json.load(open(plan))
    k = K(); k.load("sch_wiring")
    print(k.call("batch_add_wire", schematic=sch,
                 wires=[{"x1": a[0], "y1": a[1], "x2": b[0], "y2": b[1]} for n, a, b in pl["wires"]]))
    run(sys.executable, os.path.join(HERE, "labels.py"), sch, plan)


def gate(sch, work):
    net = os.path.join(work, "check.net"); erc = os.path.join(work, "erc.rpt")
    run("kicad-cli", "sch", "export", "netlist", "--output", net, sch)
    run(sys.executable, os.path.join(HW, "netlist_fingerprint.py"),
        os.path.join(HW, "netlist-baseline-reva1.json"), net)
    run("kicad-cli", "sch", "erc", "--severity-error", "--severity-warning", "--output", erc, sch)
    report = open(erc, encoding="utf-8").read()
    errors = int(re.search(r"\*\* ERC messages: (\d+)\s+Errors (\d+)", report).group(2))
    kinds = sorted(set(re.findall(r"^\[([a-z_]+)\]", report, re.M)))
    print("ERC:", errors, "errors;", kinds or "no warnings")
    if errors:
        raise SystemExit("ERC errors - see " + erc)


if __name__ == "__main__":
    main()
