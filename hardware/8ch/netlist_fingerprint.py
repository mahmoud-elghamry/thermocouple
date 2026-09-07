"""Canonical fingerprint of a KiCad netlist - the guard for schematic edits.

Redrawing the schematic is supposed to change how it looks and nothing else.
The board is generated from the netlist, so as long as the connectivity is
identical the PCB is provably unaffected and does not need regenerating.

Comparing the .net files directly does not work: UUIDs, symbol positions,
export dates and node ordering all move for reasons that mean nothing
electrically.  This reduces a netlist to the only thing that matters - which
pins are tied together - and to component values and footprints, which decide
what gets placed.

    python netlist_fingerprint.py thermocouple_8ch.net              # print
    python netlist_fingerprint.py before.json thermocouple_8ch.net  # compare

Exits non-zero when the two differ, and prints what moved.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

NET_BLOCK = re.compile(
    r'\(net\s+\(code\s+"?\d+"?\)\s+\(name\s+"([^"]+)"\)(.*?)\n\t\t\)', re.S)
NODE = re.compile(r'\(ref\s+"([^"]+)"\)\s*\n?\s*\(pin\s+"([^"]+)"\)')
COMPONENT = re.compile(
    r'\(comp\s+\(ref\s+"([^"]+)"\)\s*\n\s*\(value\s+"([^"]*)"\)'
    r'(?:\s*\n\s*\(footprint\s+"([^"]*)"\))?')


def fingerprint(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")

    nets = {}
    for name, body in NET_BLOCK.findall(text):
        # Sorted, so node order in the file cannot show up as a difference.
        nets[name] = sorted(f"{ref}.{pin}" for ref, pin in NODE.findall(body))

    components = {}
    for ref, value, footprint in COMPONENT.findall(text):
        components[ref] = {"value": value, "footprint": footprint or ""}

    if not nets or not components:
        raise SystemExit(f"{path}: parsed 0 nets or 0 components - "
                         "the netlist format changed, fix this script")

    return {"nets": nets, "components": components}


def summarise(data: dict) -> str:
    pins = sum(len(nodes) for nodes in data["nets"].values())
    return (f"{len(data['components'])} components, "
            f"{len(data['nets'])} nets, {pins} pins")


def diff(before: dict, after: dict) -> list[str]:
    problems = []

    for label, key in (("net", "nets"), ("component", "components")):
        gone = sorted(set(before[key]) - set(after[key]))
        new = sorted(set(after[key]) - set(before[key]))
        for name in gone:
            problems.append(f"{label} removed: {name}")
        for name in new:
            problems.append(f"{label} added:   {name}")

    for name in sorted(set(before["nets"]) & set(after["nets"])):
        if before["nets"][name] != after["nets"][name]:
            was = set(before["nets"][name])
            now = set(after["nets"][name])
            problems.append(
                f"net {name} changed: "
                f"-{sorted(was - now) or '[]'} +{sorted(now - was) or '[]'}")

    for ref in sorted(set(before["components"]) & set(after["components"])):
        if before["components"][ref] != after["components"][ref]:
            problems.append(f"component {ref} changed: "
                            f"{before['components'][ref]} -> "
                            f"{after['components'][ref]}")
    return problems


def load(path: Path) -> dict:
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return fingerprint(path)


def main(argv: list[str]) -> int:
    if len(argv) == 2:
        data = fingerprint(Path(argv[1]))
        print(json.dumps(data, indent=1, sort_keys=True))
        print(summarise(data), file=sys.stderr)
        return 0

    if len(argv) == 3:
        before, after = load(Path(argv[1])), load(Path(argv[2]))
        print(f"before: {summarise(before)}")
        print(f"after:  {summarise(after)}")
        problems = diff(before, after)
        if not problems:
            print("IDENTICAL - connectivity unchanged, the PCB is unaffected")
            return 0
        print(f"\n{len(problems)} difference(s):")
        for problem in problems[:40]:
            print(f"  {problem}")
        if len(problems) > 40:
            print(f"  ... and {len(problems) - 40} more")
        return 1

    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
