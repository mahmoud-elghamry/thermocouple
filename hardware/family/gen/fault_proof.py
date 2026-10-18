"""Run three deliberate circuit faults on scratch outputs, then compare exported XML."""
import argparse
import sys
from pathlib import Path

import build
from boards import B24
from compare_release import compare_release


def inject(sheets, fault):
    parts = {p.ref: p for s in sheets for p in s.parts()}
    if fault == "value":
        parts["R111"].value = "FAULT-VALUE"
    elif fault == "swapped-pin":
        nets = parts["R111"]._nets
        nets["1"], nets["2"] = nets["2"], nets["1"]
    elif fault == "removed-part":
        for sheet in sheets:
            sheet.blocks = [(title, [p for p in ps if p.ref != "C111"])
                            for title, ps in sheet.blocks]
    else:
        raise ValueError(fault)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scratch_dir")
    parser.add_argument("release_dir")
    args = parser.parse_args()
    scratch = Path(args.scratch_dir).resolve()
    if scratch == Path(args.release_dir).resolve() or Path(args.release_dir).resolve() in scratch.parents:
        raise SystemExit("scratch output cannot be in the release")
    log, passed = [], 0
    for fault, marker in (("value", "COMPONENT R111 value:"),
                          ("swapped-pin", "NET TC1+"),
                          ("removed-part", "COMPONENT missing C111")):
        out = scratch / fault
        build.generate(B24, out, lambda sheets: inject(sheets, fault))
        diffs = compare_release(out, args.release_dir)
        caught = any(marker in d for d in diffs)
        passed += caught
        line = f"fault-injection {fault}: {'PASS' if caught else 'FAIL'}; {len(diffs)} differences; expected {marker}"
        print(line)
        log.append(line)
    summary = f"fault-injection proof: {passed}/3 detected"
    print(summary)
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / "fault-proof.txt").write_text("\n".join(log + [summary]) + "\n", encoding="utf-8")
    return 0 if passed == 3 else 1


if __name__ == "__main__":
    sys.exit(main())
