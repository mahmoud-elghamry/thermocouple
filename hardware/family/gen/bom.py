"""Release BOM grouping copied from 24ch/gen/fab.py; no PCB/fab operations."""
import csv
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

HEADER = ["Comment", "Designator", "Footprint", "LCSC (reference)", "MPN", "Qty"]
BARE = ("#", "H", "TP")


def grouped_bom(root):
    lines, dnp = defaultdict(list), []
    for c in root.iter("comp"):
        fields = {x.get("name"): x.text or "" for x in c.iter("field")}
        fp = (c.findtext("footprint") or "").split(":")[-1]
        if not fp or c.get("ref").startswith(BARE):
            continue
        if any(p.get("name") == "dnp" for p in c.iter("property")):
            dnp.append(c.get("ref"))
            continue
        key = (c.findtext("value"), fp, fields.get("LCSC", ""), fields.get("MPN", ""))
        lines[key].append(c.get("ref"))
    rows = [HEADER]
    for (value, fp, lcsc, mpn), refs in sorted(lines.items(), key=lambda kv: kv[1][0]):
        rows.append([value, ",".join(sorted(refs)), fp, lcsc, mpn, str(len(refs))])
    return rows, sorted(dnp)


def write_bom(xml, out):
    rows, dnp = grouped_bom(ET.parse(xml).getroot())
    with (Path(out) / "BOM.csv").open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    text = "Footprints that stay empty on this order (please do not fit):\n"
    text += (" ".join(dnp) if dnp else "none - every footprint is fitted") + "\n"
    (Path(out) / "DNP.txt").write_text(text, encoding="utf-8")
    count = sum(int(r[-1]) for r in rows[1:])
    print(f"BOM: {len(rows)-1} lines; fitted parts: {count}; DNP: {len(dnp)}")
    return rows, dnp
