"""Gate: the entry documents agree with each other and with the decisions.

Why it exists (2026-10-11): the project moved 8ch -> three modules -> one 24-ch
board in a week. Each step wrote a decision file but swept the entry documents
only in part, so GOAL, the root README and ISSUES rows kept describing an older
product (Astra R-10, I-117). This catches the mechanical part of that drift:

1. size limits of the files every agent reads in full;
2. every I-number named in an entry document exists (open or closed) and no
   issue is both open and closed;
3. every decision number named in an entry document has a file;
4. every decision file has a Status line;
5. no phrase listed in docs/superseded.txt appears in an entry document.

Run: python docs/check_docs.py   (exit 0 = clean; 1 = findings printed)
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRY = ["AGENTS.md", "README.md", "docs/GOAL.md", "docs/STATE.md", "docs/ISSUES.md",
         "hardware/24ch/README.md"]
LIMITS = {"AGENTS.md": 150, "docs/STATE.md": 60, "docs/GOAL.md": 120}
ROW = re.compile(r"^\| (I-\d{3}) \|", re.M)


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def main():
    bad = []
    for rel, limit in LIMITS.items():
        n = read(rel).count("\n")
        if n > limit:
            bad.append(f"{rel}: {n} lines, limit {limit}")

    open_ids = ROW.findall(read("docs/ISSUES.md"))
    closed_ids = set(ROW.findall(read("docs/ISSUES-closed.md")))
    for i in sorted({x for x in open_ids if open_ids.count(x) > 1}):
        bad.append(f"docs/ISSUES.md: {i} has more than one row")
    for i in sorted(set(open_ids) & closed_ids):
        bad.append(f"{i} is both open (ISSUES.md) and closed (ISSUES-closed.md)")
    known = set(open_ids) | closed_ids

    ddir = os.path.join(ROOT, "docs", "decisions")
    decisions = {f[:4]: f for f in os.listdir(ddir) if re.match(r"\d{4}-", f)}
    for f in sorted(decisions.values()):
        if not re.search(r"^[*\s]*status\W", read(f"docs/decisions/{f}"), re.M | re.I):
            bad.append(f"docs/decisions/{f}: no Status line")

    phrases = []
    for line in read("docs/superseded.txt").splitlines():
        if line.strip() and not line.startswith("#"):
            phrase, _, why = line.partition("|")
            phrases.append((phrase.strip(), why.strip()))

    for rel in ENTRY:
        text = read(rel)
        low = text.lower()
        for i in sorted(set(re.findall(r"\bI-\d{3}\b", text)) - known):
            bad.append(f"{rel}: {i} is in neither ISSUES.md nor ISSUES-closed.md")
        for d in sorted(set(re.findall(r"`(\d{4})`", text))):
            if d not in decisions:
                bad.append(f"{rel}: decision `{d}` has no file in docs/decisions/")
        for phrase, why in phrases:
            if phrase.lower() in low:
                bad.append(f"{rel}: stale phrase '{phrase}' ({why})")

    for b in bad:
        print("BAD", b)
    print(f"check_docs: {len(bad)} finding(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
