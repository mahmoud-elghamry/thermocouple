"""JLC placement list from a release snapshot; raw CPL.csv is untouched.

Run with KiCad Python: python cpl_jlc.py RELEASE --board 8|8l|24|40.
"""
import argparse
import csv
from pathlib import Path

from cpl_profiles import PREVIEW_CONFIRMED, rotation
from manifest_complete import rewrite_manifest


def adjust_rows(rows, packages, shifts, key):
    """Return the JLC rows. Board Y points down; CPL Y points up."""
    out = [rows[0][:]]
    for old in rows[1:]:
        row = old[:]
        ref = row[0]
        degrees = rotation(key, packages[ref])
        if degrees:
            row[4] = f'{(float(row[4]) + degrees) % 360:.6f}'
        if ref in shifts:
            dx, dy = shifts[ref]
            row[1] = f'{float(row[1].removesuffix("mm")) + dx:.6f}mm'
            row[2] = f'{float(row[2].removesuffix("mm")) - dy:.6f}mm'
        out.append(row)
    return out


def pad_centre_shift(board, pcbnew):
    shifts = {}
    for fp in board.GetFootprints():
        pads = list(fp.Pads())
        if not any(p.GetDrillSize().x > 0 for p in pads):
            continue
        xs = [p.GetPosition().x for p in pads]
        ys = [p.GetPosition().y for p in pads]
        origin = fp.GetPosition()
        dx = pcbnew.ToMM((min(xs) + max(xs)) // 2 - origin.x)
        dy = pcbnew.ToMM((min(ys) + max(ys)) // 2 - origin.y)
        if abs(dx) > 0.01 or abs(dy) > 0.01:
            shifts[fp.GetReference()] = (dx, dy)
    return shifts


def polarized_refs(rel):
    """Conservative fitted parts needing an orientation check in the preview."""
    refs = set()
    with (rel / 'BOM.csv').open(encoding='utf-8-sig', newline='') as fh:
        for row in csv.DictReader(fh):
            fp = row['Footprint']
            for ref in row['Designator'].split(','):
                if ref.startswith(('U', 'D', 'K', 'Q', 'J', 'JP', 'SW', 'Y')) or 'CP_' in fp:
                    refs.add(ref)
    return sorted(refs, key=lambda s: (s.rstrip('0123456789'), int(s[len(s.rstrip('0123456789')):])))


def generate_jlc(rel, profile):
    """Write CPL-JLC.csv and a review report. Requires KiCad's pcbnew Python."""
    import pcbnew

    rel = Path(rel)
    key = profile['key']
    pcb = rel / 'source-snapshot' / f'{profile["project"]}.kicad_pcb'
    if not pcb.is_file():
        raise FileNotFoundError(f'JLC CPL requires release snapshot board: {pcb}')
    board = pcbnew.LoadBoard(str(pcb))
    shifts = pad_centre_shift(board, pcbnew)
    with (rel / 'pos.csv').open(encoding='utf-8', newline='') as fh:
        packages = {r['Ref']: r['Package'] for r in csv.DictReader(fh)}
    with (rel / 'CPL.csv').open(encoding='utf-8', newline='') as fh:
        rows = list(csv.reader(fh))
    adjusted = adjust_rows(rows, packages, shifts, key)
    with (rel / 'CPL-JLC.csv').open('w', encoding='utf-8', newline='') as fh:
        csv.writer(fh).writerows(adjusted)
    preview = polarized_refs(rel)
    evidence = PREVIEW_CONFIRMED.get(key, 'UNVERIFIED for this board/profile')
    report = (f'JLC placement preview review - {key} ({profile["revision"]})\n'
              f'Package rotation provenance: {evidence}.\n'
              'CPL.csv is the raw KiCad placement list; CPL-JLC.csv has package rotations and drilled-pad centres.\n'
              'Before assembly approval, inspect EVERY reference below in the JLC preview against the silk, polarity, and pin 1.\n'
              'A generated placement list does not certify JLC model orientation.\n'
              f'Polarized/directional refs to check ({len(preview)}): {", ".join(preview)}\n'
              f'Drilled-pad centre shifts ({len(shifts)}): '
              + ', '.join(f'{ref} ({dx:+.3f}, {dy:+.3f}) mm' for ref, (dx, dy) in sorted(shifts.items())) + '\n')
    (rel / 'JLC-PLACEMENT-REVIEW.txt').write_text(report, encoding='utf-8', newline='\n')
    if (rel / 'MANIFEST.txt').exists():
        rewrite_manifest(rel)
    return rel / 'CPL-JLC.csv'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('release')
    parser.add_argument('--board', choices=('24', '8', '8l', '40'), required=True)
    args = parser.parse_args()
    from profiles import PROFILES
    generate_jlc(args.release, PROFILES[args.board])
