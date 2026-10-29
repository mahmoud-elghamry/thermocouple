"""Release packaging for fab.py (I-133): the two ZIPs from the loose files, then a MANIFEST check.

Until 2026-10-25 the ZIPs were made by hand and the MANIFEST before ASSEMBLY-SPEC: the PURCHASING zip
carried an older ACCESSORIES.csv (22 internal rows vs 7 loose) and MANIFEST missed 7 files. Here every
zipped copy of a loose file is compared byte for byte, and the MANIFEST must list every file with its hash.
"""
import hashlib
import os
import subprocess
import sys
import zipfile
from pathlib import Path

PURCHASING = ("ORDER-NOTES.txt", "thermo24-gerbers.zip", "BOM.csv", "CPL.csv", "CPL-JLC.csv", "ASSEMBLY-SPEC.pdf",
              "POWER-ON-TEST.pdf", "POWER-ON-TEST.zip", "thermo24-schematic.pdf", "DNP.txt", "ACCESSORIES.csv")
REVIEWER = ("thermo24-schematic.pdf", "BOM.csv", "thermo24-gerbers.zip", "ASSEMBLY-SPEC.pdf")


def fitz_python():
    """An interpreter with PyMuPDF for assembly_spec.py; ASSEMBLY_PYTHON overrides."""
    override = os.environ.get("ASSEMBLY_PYTHON")
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Python/Python310/python.exe"
    for exe in dict.fromkeys([override] if override else [sys.executable, str(local)]):
        try:
            if subprocess.run([exe, "-B", "-c", "import fitz"], capture_output=True).returncode == 0:
                return exe
        except OSError:
            continue
    raise SystemExit("PyMuPDF missing: set ASSEMBLY_PYTHON to a python with fitz (py -3 -m pip install pymupdf)")


def _zip(path, members):
    """members: (archive name, source file). Refuses a missing source."""
    if os.path.exists(path):
        os.remove(path)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, src in members:
            if not os.path.isfile(src):
                raise SystemExit(f"package: {src} missing - not zipped")
            z.write(src, arc)


def _same(path, out):
    """Every zip member named like a loose release file must be that file, byte for byte."""
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            loose = os.path.join(out, info.filename)
            if os.path.isfile(loose) and z.read(info) != Path(loose).read_bytes():
                raise SystemExit(f"package: {info.filename} in {os.path.basename(path)} differs from the loose file")
    return len(z.infolist())


def zips(out):
    purchasing = os.path.join(out, "PURCHASING-24ch-reva4.zip")
    _zip(purchasing, [(f, os.path.join(out, f)) for f in PURCHASING])
    snap = os.path.join(out, "source-snapshot")
    project = [("kicad-project/" + os.path.relpath(os.path.join(d, f), snap).replace(os.sep, "/"), os.path.join(d, f))
               for d, _, fs in sorted(os.walk(snap)) for f in sorted(fs)]
    reviewer = os.path.join(out, "FOR-REVIEWER-24ch-reva4.zip")
    _zip(reviewer, [(f, os.path.join(out, f)) for f in REVIEWER] + project)
    n = _same(purchasing, out), _same(reviewer, out)
    print(f"package: PURCHASING {n[0]} files, FOR-REVIEWER {n[1]} files, zipped copies identical to the loose files")


def check_manifest(out):
    """MANIFEST.txt lists every other file in the release with its current sha256, and nothing else."""
    listed = {}
    for line in Path(out, "MANIFEST.txt").read_text(encoding="utf-8").split(
            "every output file sha256 (all files in this folder except this one):\n", 1)[1].splitlines():
        digest, name = line.split(None, 1)
        listed[name] = digest
    actual = {p.relative_to(out).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in Path(out).rglob("*") if p.is_file() and p != Path(out, "MANIFEST.txt")}
    if listed != actual:
        bad = sorted(set(listed) ^ set(actual)) + sorted(k for k in set(listed) & set(actual) if listed[k] != actual[k])
        raise SystemExit(f"MANIFEST does not match the release: {bad[:10]}")
    print(f"MANIFEST: {len(actual)} files, every hash matches")
