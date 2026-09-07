"""Generate the readable hierarchical REV A0 schematic."""

import sys

from schematic.catalog import ROOT, TOOL, parts

# The verified kicad-tool virtual environment owns the matching kiutils fork.
# The gate command intentionally uses plain ``python``, so expose that package
# to this process without installing or modifying the user's system Python.
site_packages = TOOL.parent.parent / "Lib" / "site-packages"
if site_packages.exists():
    sys.path.insert(0, str(site_packages))

from schematic.builder import build


def main() -> None:
    if not TOOL.exists():
        raise SystemExit(f"kicad-tool not found: {TOOL}")
    build(parts, ROOT, TOOL)


if __name__ == "__main__":
    main()
