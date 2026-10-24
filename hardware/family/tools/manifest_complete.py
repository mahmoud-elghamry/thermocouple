"""Replace the manifest's output hash block with a complete, stable inventory."""
import hashlib
from pathlib import Path

MARKER = 'every output file sha256 (all files in this folder except this one):'


def rewrite_manifest(rel):
    rel = Path(rel)
    path = rel / 'MANIFEST.txt'
    original = path.read_text(encoding='utf-8')
    if MARKER not in original:
        raise ValueError(f'{path}: output hash heading missing')
    metadata = original.split(MARKER, 1)[0].rstrip()
    lines = [metadata, MARKER]
    for file in sorted(p for p in rel.rglob('*') if p.is_file() and p != path):
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        lines.append(f'  {digest}  {file.relative_to(rel).as_posix()}')
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
