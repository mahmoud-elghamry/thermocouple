"""Comparison rules are explicit; every normalised comparison also records raw SHA256."""
import hashlib
import importlib.util
import json
import re
import zipfile
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree_hashes(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file()}


def normal_text(text, roots=(), release_names=()):
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    for root in roots:
        text = text.replace(str(root), '<scratch>')
        text = text.replace(str(root).replace('\\', '/'), '<scratch>')
    for name in release_names:
        text = text.replace(name, '<release>')
    text = re.sub(r'\(uuid "[0-9a-f-]{36}"\)', '(uuid "<generated>")', text)
    text = re.sub(r'\*\* Created on .*?\*\*', '** Created on <time> **', text)
    text = re.sub(r'(?m)^.*(?:CreationDate|TF.CreationDate|# Date:).*$', '<creation-date>', text)
    # Gerber timestamp field; retain every other Gerber command.
    text = re.sub(r'(?m)^(G04 Created by KiCad .*? date |; DRILL file KiCad .*? date )[\dT: -]+(\*?)$',
                  r'\1<time>\2', text)
    # Schematic netlist generator metadata, leaving circuit data intact.
    text = re.sub(r'<date>.*?</date>', '<date><time></date>', text)
    text = re.sub(r'<source>.*?</source>', '<source><scratch></source>', text)
    return text


def compare_file(a, b, roots=(), releases=()):
    raw = (sha(a), sha(b))
    if raw[0] == raw[1]:
        return True, 'SHA256 identical', raw
    if a.suffix == '.zip':
        with zipfile.ZipFile(a) as za, zipfile.ZipFile(b) as zb:
            if sorted(za.namelist()) != sorted(zb.namelist()):
                return False, 'ZIP member names differ', raw
            ok = all(compare_payload(n, za.read(n), zb.read(n), roots, releases) for n in za.namelist())
        return ok, 'ZIP members compared (container dates ignored)', raw
    if a.suffix == '.pdf':
        ok, why = compare_pdf(a, b, roots, releases)
        return ok, why, raw
    try:
        ta, tb = a.read_text(encoding='utf-8'), b.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return False, 'binary bytes differ', raw
    if a.suffix == '.kicad_pcb':
        return canonical_pcb(ta) == canonical_pcb(tb), 'PCB geometry sorted; generated UUIDs ignored', raw
    if a.name == 'MANIFEST.txt':
        # Manifests deliberately contain time, paths and hashes of timestamped files.
        # Other files are compared individually; retain git/version/DRC/BOM/schema names.
        def manifest(t):
            t = normal_text(t, roots, releases)
            t = re.sub(r'(?m)^created: .*$', 'created: <time>', t)
            return re.sub(r'\b[0-9a-f]{64}\b', '<file-sha>', t)
        ta, tb = manifest(ta), manifest(tb)
        # Source path sits above the release roots; validate only this metadata line.
        ta = re.sub(r'(?m)^source board: .*$', 'source board: <scratch-board>', ta)
        tb = re.sub(r'(?m)^source board: .*$', 'source board: <scratch-board>', tb)
    else:
        ta, tb = normal_text(ta, roots, releases), normal_text(tb, roots, releases)
    return ta == tb, 'normalised UUID/time/scratch metadata', raw


def compare_payload(name, a, b, roots, releases):
    if a == b:
        return True
    if name.lower().endswith('.pdf'):
        return compare_pdf(a, b, roots, releases)[0]
    try:
        return normal_text(a.decode('utf-8'), roots, releases) == normal_text(b.decode('utf-8'), roots, releases)
    except UnicodeDecodeError:
        return False


def compare_pdf(a, b, roots=(), releases=()):
    # Structural/render comparison, also for PDF bytes inside ZIP members.
    try:
        import fitz
    except ImportError:
        return False, 'PyMuPDF required to compare nonidentical PDFs'
    def opened(value):
        return fitz.open(stream=value, filetype='pdf') if isinstance(value, bytes) else fitz.open(value)
    def pixels(page):
        markers = [str(r) for r in roots] + list(releases)
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines', []):
                text = ''.join(s['text'] for s in line['spans'])
                if any(marker in text for marker in markers):
                    page.draw_rect(line['bbox'], color=(1, 1, 1), fill=(1, 1, 1), width=0)
        return page.get_pixmap(dpi=96).samples
    with opened(a) as da, opened(b) as db:
        ok = len(da) == len(db) and all(
            normal_text(pa.get_text(), roots, releases) == normal_text(pb.get_text(), roots, releases)
            and pixels(pa) == pixels(pb) for pa, pb in zip(da, db))
    return ok, 'PDF normalised text + pixels (release/path lines masked)'


def canonical_pcb(text):
    # Reuse the donor's pure parser only in the orchestrator gate; no pcbnew import.
    path = Path(__file__).resolve().parents[2] / '24ch' / 'gen' / 'sexp.py'
    spec = importlib.util.spec_from_file_location('donor_sexp', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    movable = {'footprint', 'segment', 'via', 'zone', 'gr_text', 'gr_line', 'gr_arc', 'gr_rect',
               'pad', 'property', 'fp_text', 'fp_line', 'fp_arc', 'fp_rect', 'fp_circle'}
    def canon(n):
        if not isinstance(n, list):
            return ('atom' if isinstance(n, module.Sym) else 'string', n)
        children = [x for x in n if not (isinstance(x, list) and x and x[0] == 'uuid')]
        fixed, objects = [], []
        for x in children:
            (objects if isinstance(x, list) and x and x[0] in movable else fixed).append(canon(x))
        return fixed + sorted(objects, key=lambda x: json.dumps(x, sort_keys=True))
    return canon(module.parse(text))


def compare_tree(a, b):
    fa = {p.relative_to(a) for p in a.rglob('*') if p.is_file()}
    fb = {p.relative_to(b) for p in b.rglob('*') if p.is_file()}
    results = []
    if fa != fb:
        results.append({'ok': False, 'reason': 'file sets differ', 'a_only': list(map(str, fa - fb)),
                        'b_only': list(map(str, fb - fa))})
    for rel in sorted(fa & fb):
        ok, why, hashes = compare_file(a / rel, b / rel, (a, b), (a.name, b.name))
        results.append({'file': str(rel), 'ok': ok, 'reason': why, 'sha256': hashes})
    return results
