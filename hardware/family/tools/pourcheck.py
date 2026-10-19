"""Inspect attachments to SAVED native zone fill; never refill or save a board.

Use a refilled output/ copy with --pcb. No fill is an error, never a clean
result. Direct geometric touch and a path to any fill are distinct counts.
Connectivity includes tracks, pads, vias and zones, but does not certify neck
width, thermal capacity or attachment to the largest island. DRC remains the gate.
"""
import argparse
from audit_common import emit, identity, layers, load_board, selected_board


def audit(board, nets=()):
    import pcbnew as p
    zones = [z for z in board.Zones() if not z.GetIsRuleArea()]
    if nets:
        unknown = set(nets) - {z.GetNetname() for z in zones}
        if unknown:
            raise ValueError(f'no zones for nets: {sorted(unknown)} (use full net names)')
        zones = [z for z in zones if z.GetNetname() in nets]
    if not zones:
        raise ValueError('no copper zones to inspect')
    fills, missing, empty = {}, [], []
    for z in zones:
        for layer in layers(board, z):
            poly = z.GetFilledPolysList(layer)
            if not z.IsFilled():
                missing.append(dict(uuid=z.m_Uuid.AsString(), net=z.GetNetname(), layer=board.GetLayerName(layer)))
            elif not poly.OutlineCount():
                empty.append(dict(uuid=z.m_Uuid.AsString(), net=z.GetNetname(), layer=board.GetLayerName(layer)))
            else:
                fills.setdefault(z.GetNetname(), []).append((layer, poly, z.m_Uuid.AsString()))
    if missing:
        raise ValueError(f'{len(missing)} zone/layers lack saved fill; refill and save an output/ copy first')
    if not fills:
        raise ValueError('no saved filled copper polygons to inspect')
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    items = [pad for f in board.GetFootprints() for pad in f.Pads() if layers(board, pad)]
    items += [t for t in board.GetTracks() if t.Type() == p.PCB_VIA_T]
    rows = []
    target_nets = {z.GetNetname() for z in zones}
    for item in items:
        if item.GetNetname() not in target_nets:
            continue
        candidates = fills.get(item.GetNetname(), [])
        direct = {uid for l, poly, uid in candidates if item.IsOnLayer(l)
                  and p.SHAPE.Collide(poly, item.GetEffectiveShape(l), 1)}
        reachable = {other.m_Uuid.AsString() for other in conn.GetConnectedItems(item)
                     if other.Type() == p.PCB_ZONE_T}
        reachable &= {uid for _, _, uid in candidates}
        rows.append(dict(**identity(item), direct_zones=sorted(direct), reachable_zones=sorted(reachable)))
    return dict(zone_layers=sum(len(v) for v in fills.values()), empty_zone_layers=empty, inspected_items=len(rows),
                directly_attached=sum(bool(r['direct_zones']) for r in rows),
                reachable_fill=sum(bool(r['reachable_zones']) for r in rows),
                unattached=sum(not r['reachable_zones'] for r in rows), items=rows)


def main():
    profile = selected_board()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--net', action='append', default=[])
    args = parser.parse_args()
    try:
        result = audit(load_board(profile), args.net)
    except ValueError as exc:
        parser.error(str(exc))
    emit(profile, result)
    return int(bool(result['unattached']))


if __name__ == '__main__':
    raise SystemExit(main())
