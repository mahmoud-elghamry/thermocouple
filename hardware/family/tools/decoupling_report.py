"""PROPOSAL, not a replacement release gate: two-layer ADC bypass paths.

KiCad Python: decoupling_report.py --board 8l --pcb REFILLED_COPY
Proposed limits: <=5 mm actual routed supply path to a 100 nF bypass, <=1 via;
both bypass return and ADC ground must reach saved ground fill. 5 mm reuses the
existing critical-bypass target, not the current board's measured worst case.
This geometric screen cannot prove loop inductance, ground necks or noise.
Owner review/bench evidence is required before adopting or accepting exceptions.
"""
import json
import math


def assess(length, vias, grounded):
    problems = []
    if length is None:
        problems.append('no routed supply path')
    elif length > 5.:
        problems.append('supply path > 5 mm')
    if vias > 1:
        problems.append('supply uses > 1 via')
    if not grounded:
        problems.append('return does not reach saved ground fill')
    return problems


def measure(board):
    import pcbnew as p
    from pourcheck import audit
    from route_native import BoardRoutes
    routes = BoardRoutes(board)
    fill = audit(board)
    attached = {row.get('pad') for row in fill['items'] if row['reachable_zones']}
    ground = [label for label, pad in routes.pads.items()
              if label.startswith('U101.') and pad.GetNetname().rsplit('/', 1)[-1] == 'GND_ISO']
    rows = []
    for pin, designated in (('26', 'C194.1'), ('2', 'C196.1')):
        source = 'U101.'+pin
        pad = routes.pads[source]
        candidates = []
        for label, target in routes.pads.items():
            fp = target.GetParentFootprint()
            if not fp.GetReference().startswith('C') or fp.GetValue() != '100n':
                continue
            if target.GetNetname() != pad.GetNetname():
                continue
            distance = math.hypot(p.ToMM(target.GetPosition().x-pad.GetPosition().x),
                                  p.ToMM(target.GetPosition().y-pad.GetPosition().y))
            if distance > 20.:
                continue
            path = routes.path(source, label)
            if path['length_mm'] is not None:
                candidates.append(path)
        best = min(candidates, key=lambda r: r['length_mm']) if candidates else None
        return_pads = [] if best is None else [fp.GetReference()+'.'+q.GetNumber()
            for fp in board.GetFootprints() if fp.GetReference() == best['target'].split('.')[0]
            for q in fp.Pads() if q.GetNetname().rsplit('/', 1)[-1] == 'GND_ISO']
        grounded = bool(return_pads and ground and all(x in attached for x in return_pads+ground))
        length, vias = (None, 0) if best is None else (best['length_mm'], best['vias'])
        rows.append(dict(source=source, designated=routes.path(source, designated), best=best,
                         ground_pads=ground, return_pads=return_pads, saved_ground_fill=grounded,
                         proposed_limit_failures=assess(length, vias, grounded)))
    return dict(status='PROPOSED criterion; does not alter existing release gate',
                supply_limit_mm=5., supply_via_limit=1, rows=rows)


def main():
    from audit_common import emit, load_board, selected_board
    profile = selected_board()
    if profile['key'] != '8l':
        raise SystemExit('this proposal is specific to profile 8l')
    emit(profile, measure(load_board(profile)))


if __name__ == '__main__':
    main()
