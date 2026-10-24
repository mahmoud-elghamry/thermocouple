"""Plan dangling cleanup without saving the input PCB (KiCad Python).

Usage: dangling_trim.py --board 40 --pcb COPY --report drc.json --out trim40.txt
The report is regenerated for the input, with all severities and parity enabled.
Only DRC-identified UUIDs are touched. Native shapes find copper contacts, including
mid-segment taps. Plans must be applied to a copy with finish.py and gated again;
the planner makes no claim that a deletion is safe until those gates pass.
"""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

from trim_geometry import junctions, projection, retained_segment


def xy(p):
    import pcbnew
    return pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)


def connections(board, track):
    import pcbnew as p
    start, end = xy(track.GetStart()), xy(track.GetEnd())
    layer = track.GetLayer()
    shape = track.GetEffectiveShape(layer)
    points = []
    others = list(board.GetTracks()) + [q for fp in board.GetFootprints() for q in fp.Pads()]
    for item in others:
        if item.m_Uuid.AsString() == track.m_Uuid.AsString() or item.GetNetCode() != track.GetNetCode():
            continue
        if not item.IsOnLayer(layer) or not p.SHAPE.Collide(shape, item.GetEffectiveShape(layer), 1):
            continue
        if item.Type() == p.PCB_TRACE_T:
            candidates = junctions(start, end, xy(item.GetStart()), xy(item.GetEnd()))
            candidates = [q for q in candidates if item.HitTest(
                p.VECTOR2I(p.FromMM(q[0]), p.FromMM(q[1])), track.GetWidth()//2+1)]
        elif item.Type() == p.PCB_ARC_T:
            raise ValueError('arc touches a dangling candidate; requires manual review')
        else:
            candidates = [projection(xy(item.GetPosition()), start, end)]
        points.extend(candidates)
        # Keep an endpoint inside another copper shape, even if its centre projects elsewhere.
        for q, native in ((start, track.GetStart()), (end, track.GetEnd())):
            if item.HitTest(native, 1):
                points.append(q)
    return points


def via_replacements(board, via, doomed):
    """Retain the via's same-layer bridging function without its unused barrel."""
    import pcbnew as p
    centre = xy(via.GetPosition())
    contacts = {}
    for item in list(board.GetTracks()) + [q for f in board.GetFootprints() for q in f.Pads()]:
        if item.m_Uuid.AsString() in doomed or item.GetNetCode() != via.GetNetCode():
            continue
        for layer in board.GetEnabledLayers().CuStack():
            if not item.IsOnLayer(layer) or not p.SHAPE.Collide(
                    via.GetEffectiveShape(layer), item.GetEffectiveShape(layer), 1):
                continue
            point = projection(centre, xy(item.GetStart()), xy(item.GetEnd())) \
                if item.Type() == p.PCB_TRACE_T else xy(item.GetPosition())
            contacts.setdefault(layer, set()).add(point)
    active = {l: pts for l, pts in contacts.items() if pts}
    if len(active) > 1:
        raise ValueError('reported via joins multiple copper layers; cannot replace with a track')
    lines = []
    for layer, points in active.items():
        if len(points) < 2:
            continue
        anchor = min(points, key=lambda q: (q[0]-centre[0])**2+(q[1]-centre[1])**2)
        for point in sorted(points-{anchor}):
            net = via.GetNetname().rsplit('/', 1)[-1]
            lines.append(f'add {net} {board.GetLayerName(layer)} 0.200000 '
                         f'{anchor[0]:.6f},{anchor[1]:.6f} {point[0]:.6f},{point[1]:.6f}')
    return lines


def plan(board, report):
    import pcbnew as p
    if report.get('unconnected_items') or any(v['severity'] == 'error' for v in report.get('schematic_parity', [])):
        raise ValueError('unclean input: unconnected or schematic parity findings')
    items = {t.m_Uuid.AsString(): t for t in board.GetTracks()}
    uuids = {i['uuid'] for v in report['violations']
             if v['type'] in ('track_dangling', 'via_dangling') for i in v['items']}
    lines, notes = [], []
    for uid in sorted(uuids):
        item = items[uid]
        net = item.GetNetname().rsplit('/', 1)[-1]
        if item.Type() == p.PCB_VIA_T:
            lines.append('rip '+uid)
            lines.extend(via_replacements(board, item, uuids))
            notes.append(f'delete reported via {net} at {xy(item.GetPosition())}; DRC proof required')
            continue
        if item.Type() != p.PCB_TRACE_T:
            raise ValueError('unsupported dangling copper type')
        old = xy(item.GetStart()), xy(item.GetEnd())
        kept = retained_segment(*old, connections(board, item))
        if kept and all(abs(a-b) < 1e-7 for pair, original in zip(kept, old) for a, b in zip(pair, original)):
            # A flagged fragment wholly covered by other copper is a deletion candidate.
            # Connectivity and route metrics MUST prove this on a copy before use.
            kept = None
        lines.append('rip '+uid)
        if kept:
            coords = ' '.join(f'{x:.6f},{y:.6f}' for x, y in kept)
            lines.append(f'add {net} {item.GetLayerName()} {p.ToMM(item.GetWidth()):.6f} {coords}')
        notes.append(f'{uid} {net}: {old} -> {kept}')
    return lines, notes


def main():
    import pcbnew
    from profiles import ACTIVE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    path = Path(ACTIVE['pcb'])
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    rpt = Path(args.report)
    rpt.unlink(missing_ok=True)
    cli = os.environ.get('KICAD_CLI', r'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe')
    result = subprocess.run([cli, 'pcb', 'drc', '--schematic-parity', '--refill-zones', '--severity-all',
                             '--format', 'json', '-o', str(rpt), str(path)], capture_output=True)
    if result.returncode not in (0, 5) or not rpt.is_file():
        raise SystemExit('fresh DRC report generation failed; no trim plan written')
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise SystemExit('input changed during DRC; refusing plan')
    report = json.loads(rpt.read_text(encoding='utf-8'))
    lines, notes = plan(pcbnew.LoadBoard(str(path)), report)
    header = [f'# source sha256 {digest}']
    header += ['# '+note for note in notes]
    Path(args.out).write_text('\n'.join(header+lines)+'\n', encoding='utf-8')
    print(f'{args.out}: {sum(l.startswith("rip ") for l in lines)} rips, '
          f'{sum(l.startswith("add ") for l in lines)} retained segments; validate on a copy')


if __name__ == '__main__':
    main()
