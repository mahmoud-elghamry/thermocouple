"""Parts cost of one 24-ch board from LCSC prices (jlcsearch), plus JLC assembly fees.

Reads ../thermo24.xml (written by build.py), groups parts by LCSC code and asks
jlcsearch for the unit price, stock and basic/extended flag. Prints a table and
writes ../output/cost.csv. Run with normal python:  python cost.py [boards]
"""
import csv
import json
import os
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
EXTENDED_FEE = 3.0   # USD per extended part type per order (JLCPCB standard assembly)


def lookup(code):
    url = f"https://jlcsearch.tscircuit.com/api/search?q={code}&limit=5"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                comps = json.load(r).get("components", [])
            for c in comps:
                if f"C{c['lcsc']}" == code:
                    return c
            return None
        except OSError:
            time.sleep(2)
    return None


def main():
    boards = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    groups = defaultdict(list)
    for comp in ET.parse(os.path.join(HW, "thermo24.xml")).getroot().iter("comp"):
        ref = comp.get("ref")
        if ref.startswith(("#", "H", "TP")):
            continue
        f = {x.get("name"): x.text or "" for x in comp.iter("field")}
        groups[(f.get("LCSC", ""), comp.findtext("value"))].append(ref)
    rows, total, ext, missing = [], 0.0, set(), []
    for (code, value), refs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        if not code:
            missing.append((value, refs))
            continue
        c = lookup(code)
        time.sleep(0.4)
        if c is None:
            missing.append((value, refs))
            continue
        line = c["price"] * len(refs)
        total += line
        if not c.get("is_basic"):
            ext.add(code)          # the setup fee is per LCSC code, not per BOM line
        rows.append([code, c["mfr"], value, len(refs), c["price"], round(line, 3), c["stock"],
                     "basic" if c.get("is_basic") else "extended", " ".join(sorted(refs)[:6])])
    out = os.path.join(HW, "output", "cost.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["LCSC", "MPN", "value", "qty", "unit_usd", "line_usd", "stock", "jlc", "refs"])
        w.writerows(rows)
    for r in sorted(rows, key=lambda r: -r[5])[:15]:
        print(f"{r[0]:>10} {r[1][:24]:24} x{r[3]:<3} ${r[4]:<8} = ${r[5]:<8} stock {r[6]:<8} {r[7]}")
    low = [r for r in rows if r[6] < r[3] * boards]
    print(f"\nparts per board (qty-1 prices): ${total:.2f}   lines: {len(rows)}   extended codes: {len(ext)}")
    print(f"JLC extended-part fees for one order: ${len(ext) * EXTENDED_FEE:.0f}")
    print("stock short for", boards, "boards:", [(r[0], r[1], r[6]) for r in low])
    print("no LCSC price:", [(v, len(r)) for v, r in missing])


if __name__ == "__main__":
    main()
