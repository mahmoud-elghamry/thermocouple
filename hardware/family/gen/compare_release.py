"""Independent exported-XML/release comparison; no generator/model imports.

python hardware/family/gen/compare_release.py <out_dir> <release_dir>
Only local-net sheet prefixes and auto unconnected net names are normalized.
Every input SHA256 and difference is printed and saved in compare-report.txt.
"""
import argparse
import csv
import hashlib
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from itertools import zip_longest
from pathlib import Path

from bom import grouped_bom, write_bom

CLI = os.environ.get("KICAD_CLI", r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe")
FLAGS = ("dnp", "exclude_from_bom", "exclude_from_board", "exclude_from_sim")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def components(root):
    result = {}
    for c in root.iter("comp"):
        ref = c.attrib["ref"]
        if ref in result:
            raise ValueError(f"duplicate component {ref}")
        fields = {x.attrib["name"]: x.text or "" for x in c.iter("field")}
        if len(fields) != len(list(c.iter("field"))):
            raise ValueError(f"duplicate field on {ref}")
        record = {f"field:{k}": v for k, v in fields.items()}
        for key in ("value", "footprint", "description", "datasheet"):
            record[key] = c.findtext(key) or ""
        props = {x.attrib["name"]: x.get("value", "") for x in c.iter("property")}
        for flag in FLAGS:
            record[flag] = flag in props and props[flag].lower() not in ("no", "false", "0")
        result[ref] = record
    return result


def nets(root):
    # Preserve separate nets after prefix normalization: merging them could hide a split.
    result = defaultdict(list)
    prefixes = {s.get("name") for s in root.findall("design/sheet") if s.get("name")}
    prefixes |= {s.get("names") for s in root.iter("sheetpath") if s.get("names")}
    prefixes.add("/")
    prefixes = sorted(prefixes, key=len, reverse=True)
    for n in root.iter("net"):
        name = n.attrib["name"]
        if name.startswith("/"):
            # Strip only a known hierarchy prefix, preserving slashes in the label itself.
            prefix = next(p for p in prefixes if name.startswith(p))
            name = name[len(prefix):]
        if name.startswith("unconnected-"):
            name = "<unconnected>"
        nodes = tuple(sorted((p.attrib["ref"], p.attrib["pin"]) for p in n.iter("node")))
        result[name].append(nodes)
    return {k: tuple(sorted(v)) for k, v in result.items()}


def compare_roots(actual, expected):
    diffs = []
    a, e = components(actual), components(expected)
    for ref in sorted(e.keys() - a.keys()):
        diffs.append(f"COMPONENT missing {ref}")
    for ref in sorted(a.keys() - e.keys()):
        diffs.append(f"COMPONENT extra {ref}")
    for ref in sorted(a.keys() & e.keys()):
        for key in sorted(a[ref].keys() | e[ref].keys()):
            if a[ref].get(key) != e[ref].get(key):
                diffs.append(f"COMPONENT {ref} {key}: release={e[ref].get(key)!r} actual={a[ref].get(key)!r}")
    an, en = nets(actual), nets(expected)
    for name in sorted(an.keys() | en.keys()):
        if an.get(name) != en.get(name):
            diffs.append(f"NET {name}: release={en.get(name)!r} actual={an.get(name)!r}")
    return diffs


def compare_rows(actual, expected):
    return [f"BOM line {i}: release={e!r} actual={a!r}"
            for i, (a, e) in enumerate(zip_longest(actual, expected), 1) if a != e]


def top_schematic(out):
    tops = [p.with_suffix(".kicad_sch") for p in out.glob("*.kicad_pro")
            if p.with_suffix(".kicad_sch").is_file()]
    if len(tops) != 1:
        raise ValueError(f"expected one root project in {out}, found {tops}")
    return tops[0]


def export(top, xml):
    xml.unlink(missing_ok=True)
    args = [CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", str(xml), str(top)]
    try:
        r = subprocess.run(args, capture_output=True, text=True)
    except OSError as e:
        raise RuntimeError(f"kicad-cli not runnable ({CLI}): {e}") from e
    if r.returncode != 0 or not xml.is_file():
        raise RuntimeError(f"netlist export failed, exit {r.returncode}: {r.stderr or r.stdout}")


def compare_release(out, release):
    out, release = Path(out).resolve(), Path(release).resolve()
    if out == release or release in out.parents:
        raise ValueError("output must not be inside the read-only release")
    top = top_schematic(out)
    xml = out / "compare-netlist.xml"
    log = []
    def report(line):
        print(line)
        log.append(line)
    inputs = set(out.glob("*.kicad_sch")) | set((out / "lib").glob("*.kicad_sym"))
    inputs |= {out / "sym-lib-table", out / "fp-lib-table"}
    inputs |= set(out.glob("*.kicad_pro")) | {release / "netlist.xml", release / "BOM.csv", release / "DNP.txt"}
    inputs |= set((release / "source-snapshot").glob("*.kicad_sch"))
    inputs |= set((release / "source-snapshot" / "lib").glob("*.kicad_sym"))
    for path in sorted(inputs):
        report(f"SHA256 {sha256(path)}  {path}")
    before = {p: sha256(p) for p in inputs}
    export(top, xml)
    report(f"SHA256 {sha256(xml)}  {xml}")
    actual, expected = ET.parse(xml).getroot(), ET.parse(release / "netlist.xml").getroot()
    diffs = compare_roots(actual, expected)
    rows, dnp = write_bom(xml, out)
    with (release / "BOM.csv").open(newline="", encoding="utf-8-sig") as f:
        expected_rows = list(csv.reader(f))
    diffs.extend(compare_rows(rows, expected_rows))
    # Also verify release BOM's own provenance rather than trusting its counts.
    release_rows, release_dnp = grouped_bom(expected)
    diffs.extend("RELEASE " + d for d in compare_rows(release_rows, expected_rows))
    if dnp != release_dnp:
        diffs.append(f"DNP refs: release={release_dnp!r} actual={dnp!r}")
    expected_dnp = (release / "DNP.txt").read_text(encoding="utf-8").splitlines()
    actual_dnp = (out / "DNP.txt").read_text(encoding="utf-8").splitlines()
    if actual_dnp != expected_dnp:
        diffs.append(f"DNP.txt: release={expected_dnp!r} actual={actual_dnp!r}")
    for path, digest in before.items():
        if sha256(path) != digest:
            diffs.append(f"INPUT CHANGED during compare: {path}")
    for diff in diffs:
        report("DIFF " + diff)
    report(f"compare_release: {len(components(actual))}/{len(components(expected))} components; "
           f"{len(nets(actual))}/{len(nets(expected))} net names; "
           f"{len(rows)-1}/{len(expected_rows)-1} BOM lines; {len(diffs)} differences")
    (out / "compare-report.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
    return diffs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out_dir")
    parser.add_argument("release_dir")
    args = parser.parse_args()
    try:
        return 1 if compare_release(args.out_dir, args.release_dir) else 0
    except (OSError, RuntimeError, ValueError, ET.ParseError) as e:
        print(f"compare_release TOOL FAILURE: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
