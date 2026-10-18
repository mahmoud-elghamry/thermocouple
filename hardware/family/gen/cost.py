"""Offline cost using a saved 24ch/gen/cost.py CSV; never fetch prices.

Same exclusions and LCSC grouping, using the cache's recorded unit_usd.
No total is presented as complete when a code is missing. Prices are historical.
"""
import argparse
import csv
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


def estimate(xml, cache=None):
    groups = defaultdict(list)
    for c in ET.parse(xml).getroot().iter("comp"):
        if c.get("ref").startswith(("#", "H", "TP")) or any(
                p.get("name") == "dnp" for p in c.iter("property")):
            continue
        f = {x.get("name"): x.text or "" for x in c.iter("field")}
        groups[(f.get("LCSC", ""), c.findtext("value"))].append(c.get("ref"))
    if cache is None or not Path(cache).is_file():
        print(f"offline cost: UNAVAILABLE (no cached cost.csv); {len(groups)} groups, "
              f"{sum(map(len, groups.values()))} parts; no network lookup attempted")
        return None
    prices = {}
    with Path(cache).open(newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            price = float(r["unit_usd"])
            if price < 0:
                raise ValueError("negative cached price")
            if r["LCSC"] in prices and prices[r["LCSC"]] != price:
                raise ValueError(f"conflicting cached prices for {r['LCSC']}")
            prices[r["LCSC"]] = price
    missing = sorted({code for code, _ in groups if code not in prices})
    total = sum(prices.get(code, 0) * len(refs) for (code, _), refs in groups.items())
    if missing:
        print(f"offline cost: INCOMPLETE; priced subtotal ${total:.2f}; missing codes {missing}")
        return None
    print(f"offline cost: parts per board ${total:.2f} (historical cache {cache}; excludes assembly)")
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xml")
    parser.add_argument("--cache")
    args = parser.parse_args()
    estimate(args.xml, args.cache)
    return 0


if __name__ == "__main__":
    sys.exit(main())
