"""Guard against source-list drift (I-022).

`sources/*.txt` are the single source of truth for what each firmware target
links. Both `Makefile` and `build.ps1` read them. This checks the lists against
what is actually on disk, in both directions:

  * every path a list names exists under `src/`
  * every `.c` under `src/` is named by at least one list

The second half is the one that matters. A source file nobody links compiles
nowhere, is covered by no test, and looks like working code to the next person
who reads it - which is exactly how the MAX31856 bank driver came to be missing
while a MAX6675 one quietly took its place (I-030).

    python firmware/sources/check_lists.py

Exits non-zero and says what is wrong.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"


def read_list(path: Path) -> list[str]:
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = line.split("#", 1)[0].strip()
        if entry:
            entries.append(entry)
    return entries


def main() -> int:
    lists = sorted(HERE.glob("*.txt"))
    if not lists:
        print(f"no source lists found in {HERE}")
        return 1

    problems: list[str] = []
    listed: dict[str, list[str]] = {}

    for path in lists:
        entries = read_list(path)
        if not entries:
            problems.append(f"{path.name} is empty")
        for entry in entries:
            if not (SRC / entry).is_file():
                problems.append(f"{path.name} names a missing file: src/{entry}")
            listed.setdefault(entry, []).append(path.name)

    on_disk = {
        str(p.relative_to(SRC)).replace("\\", "/")
        for p in SRC.rglob("*.c")
    }
    for orphan in sorted(on_disk - set(listed)):
        problems.append(
            f"src/{orphan} is in no source list - it links into no target")

    if problems:
        print(f"FAIL  {len(problems)} problem(s):")
        for problem in problems:
            print(f"        {problem}")
        return 1

    print(f"ok    {len(lists)} source lists, {len(on_disk)} source files, "
          f"all accounted for")
    for path in lists:
        print(f"        {path.name:<24} {len(read_list(path))} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
