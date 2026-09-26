"""Does every symbol's part number actually match its value?

Why this exists. On 2026-09-16 the generator added thirteen new parts for the
LM5164 input stage and every one of them came out carrying the WRONG part
number: all six new capacitors claimed `CC0805KRX7R9BB104`, a 100 nF part, and
all six new resistors claimed `0805W8F1002T5E`, a 10 k part. Nothing warned.
kicad-tool creates a new symbol by cloning an existing one of the same lib_id,
and the clone brings the donor's MPN/Manufacturer/LCSC properties with it.

The values were right, the schematic was right, ERC was clean and the netlist
fingerprint was clean - because none of those look at MPN. The only thing that
would have caught it is an order arriving with six 100 nF capacitors where the
buck converter's input and output capacitors should be.

So: this compares each symbol's MPN against what `passives_catalog.json` says
that VALUE resolves to, and fails on any disagreement. Run it after any run of
`populate_schematic.py` that added parts.

    python check_mpn_consistency.py          # exits non-zero on a mismatch

Symbols whose value is not a catalog entry (ICs, connectors, semiconductors)
are reported as unchecked rather than silently passed - this file should never
give the impression it verified more than it did.
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCH = ROOT / "thermocouple_8ch.kicad_sch"
CATALOG = ROOT / "passives_catalog.json"


def sheets() -> list[tuple[Path, int]]:
    """Every schematic file with the number of times the root uses it.

    Since I-062 the channel parts live in channel.kicad_sch, used eight times.
    Reading only the root checked 56 symbols instead of 128 and still said
    "all match" - so the sub-sheets are found from the root itself, and a
    sheet file that does not exist is an error, not a skipped file.
    """
    root = io.open(SCH, encoding="utf-8").read()
    uses = {}
    for name in re.findall(r'\(property "Sheetfile" "([^"]+)"', root):
        uses[name] = uses.get(name, 0) + 1
    out = [(SCH, 1)]
    for name, count in sorted(uses.items()):
        path = ROOT / name
        if not path.exists():
            raise SystemExit(f"{SCH.name} uses {name}, which does not exist")
        out.append((path, count))
    return out


def main() -> int:
    catalog = json.loads(io.open(CATALOG, encoding="utf-8").read())["parts"]
    bad, unchecked, ok = [], [], 0
    for path, count in sheets():
        b, u, k = check_sheet(catalog, io.open(path, encoding="utf-8").read(),
                              path.name, count)
        bad += b
        unchecked += u
        ok += k
    return report(bad, unchecked, ok)


def check_sheet(catalog, s, name, count):
    """One file; a symbol in a sheet used `count` times counts `count` times."""
    inst = list(re.finditer(r'\n\t\t\(property "Reference" "([A-Z#]+\d+)"', s))
    tag = "" if count == 1 else " (%s x%d)" % (name, count)
    bad, unchecked, ok = [], [], 0
    for i, m in enumerate(inst):
        ref = m.group(1)
        end = inst[i + 1].start() if i + 1 < len(inst) else len(s)
        blk = s[m.start():end]

        def field(key: str) -> str:
            got = re.search(r'\(property "%s" "([^"]*)"' % key, blk)
            return got.group(1) if got else ""

        value, mpn, lcsc = field("Value"), field("MPN"), field("LCSC")
        if ref.startswith("#") or ref.startswith("TP"):
            continue

        entry = catalog.get(value)
        if entry is None:
            unchecked.append("%s (%s)%s" % (ref, value, tag))
            continue
        want_mpn = entry.get("mpn") or ""
        want_lcsc = entry.get("lcsc") or ""
        if mpn != want_mpn or (want_lcsc and lcsc != want_lcsc):
            bad.append("  %-5s value %-18s has MPN %-24s LCSC %-10s "
                       "but %r resolves to %s / %s"
                       % (ref, value, mpn or "(none)", lcsc or "(none)",
                          value, want_mpn, want_lcsc or "(none)"))
        else:
            ok += count
    return bad, unchecked, ok


def report(bad, unchecked, ok) -> int:
    if bad:
        print("FAIL  %d symbol(s) carry a part number that does not match their "
              "value:" % len(bad))
        print("\n".join(bad))
        print("\nThis is the kicad-tool clone-inherits-MPN trap. Fix the MPN, "
              "not the value.")
        return 1

    print("ok    %d symbol(s) checked against passives_catalog.json, all match"
          % ok)
    if unchecked:
        print("      %d not in the catalog, so NOT checked here: %s"
              % (len(unchecked), ", ".join(sorted(unchecked))))
    return 0


def fix() -> int:
    """Rewrite MPN / Manufacturer / LCSC from the catalog where they disagree.

    Only touches symbols whose VALUE is a catalog entry, and only the three
    sourcing properties - never a value, a footprint or a position.
    """
    catalog = json.loads(io.open(CATALOG, encoding="utf-8").read())["parts"]
    for path, _ in sheets():
        fix_sheet(catalog, path)
    return 0


def fix_sheet(catalog, path) -> None:
    s = io.open(path, encoding="utf-8").read()
    inst = list(re.finditer(r'\n\t\t\(property "Reference" "([A-Z#]+\d+)"', s))

    out, last, fixed = [], 0, []
    for i, m in enumerate(inst):
        ref = m.group(1)
        if ref.startswith("#") or ref.startswith("TP"):
            continue
        end = inst[i + 1].start() if i + 1 < len(inst) else len(s)
        blk = s[m.start():end]
        vm = re.search(r'\(property "Value" "([^"]*)"', blk)
        if not vm:
            continue
        entry = catalog.get(vm.group(1))
        if not entry or not entry.get("mpn"):
            continue

        want = {"MPN": entry["mpn"],
                "Manufacturer": entry.get("manufacturer") or "",
                "LCSC": entry.get("lcsc") or ""}
        before = blk
        for key, val in want.items():
            if not val:
                continue
            pat = r'(\(property "%s" ")[^"]*(")' % key
            if re.search(pat, blk):
                blk = re.sub(pat, lambda mm, v=val: mm.group(1) + v + mm.group(2),
                             blk, count=1)
        if blk != before:
            fixed.append("%s -> %s" % (ref, entry["mpn"]))
            out.append(s[last:m.start()])
            out.append(blk)
            last = end

    out.append(s[last:])
    io.open(path, "w", encoding="utf-8").write("".join(out))
    print("%s: corrected %d symbol(s):" % (path.name, len(fixed)))
    for line in fixed:
        print("   " + line)


if __name__ == "__main__":
    sys.exit(fix() if "--fix" in sys.argv else main())
