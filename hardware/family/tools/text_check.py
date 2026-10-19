"""Stdlib-only clearance/hole audit: --board X [--pcb P], JSON to stdout.

Checks pad/track/via copper on common layers with resolved family rules,
same/different-net drilled holes, via-hole/SMD land gap, and track/via keepouts.
No filled-zone, board-edge, schematic-parity, thermal, or mask DRC. Unsupported
syntax fails explicitly. Exit 1 = findings; exit 2 = input/unsupported feature.
"""
import argparse
import json
import math
from board_text import Board
from text_geom import Index, item_gap, EPS

# KiCad 10 ADVANCED_CFG::m_DRCEpsilon default, also verified with GetDRCEpsilon().
# https://docs.kicad.org/doxygen/drc__test__provider__copper__clearance_8cpp_source.html
DRC_EPSILON = .0005


def near_boxes(a, b, margin):
    x,y,u,v = a.box
    r,s,t,w = b.box
    return max(x-t,r-u,y-w,s-v) < margin+EPS


def check(board, land_gap=.10, include_heatsinks=False, clearance_epsilon=DRC_EPSILON):
    if not math.isfinite(land_gap) or land_gap <= 0:
        raise ValueError('land gap must be finite and positive')
    if not math.isfinite(clearance_epsilon) or clearance_epsilon < 0:
        raise ValueError('clearance epsilon must be finite and nonnegative')
    items = board.items
    index = Index(items)
    violations, keepout_hits = [], []
    boundary = []
    for a in items:
        for b in index.query(a, board.rules.maximum):
            if id(b) >= id(a) or a.net and a.net == b.net:
                continue
            if not near_boxes(a,b,board.rules.maximum):
                continue
            required, rule = board.rules.clearance(a,b)
            if not near_boxes(a,b,required):
                continue
            distance = item_gap(a,b)
            if distance < required-EPS:
                row = dict(a=a.identity(), b=b.identity(), gap_mm=distance, required_mm=required, rule=rule)
                if distance >= max(0.,required-clearance_epsilon)-EPS and distance >= 0:
                    boundary.append(row)
                else:
                    violations.append(row)
        if a.kind not in ('Track','Via'):
            continue
        for zone in board.keepouts:
            forbidden = zone.extra.get('vias' if a.kind=='Via' else 'tracks')
            if forbidden and set(a.layers)&set(zone.layers) and item_gap(a,zone) < -EPS:
                keepout_hits.append(dict(item=a.identity(), keepout=zone.uid))
    holes = board.holes
    hole_index = Index(holes)
    hole_gap = board.rules.board_rules.get('min_hole_to_hole', .25)
    pairs, lands = [], []
    for a in holes:
        for b in hole_index.query(a,hole_gap):
            if id(b) >= id(a) or not near_boxes(a,b,hole_gap):
                continue
            distance = item_gap(a,b)
            if distance < hole_gap-EPS:
                pairs.append(dict(a=a.identity(), b=b.identity(), gap_mm=distance,
                                  co_located=math.dist(a.centre,b.centre) < 1e-9))
    smds = [i for i in items if i.kind=='Pad' and i.extra['smd']
            and (include_heatsinks or not i.extra['heatsink'])]
    land_index = Index(smds)
    for via in (h for h in holes if h.kind=='Via'):
        for pad in land_index.query(via,land_gap):
            if not near_boxes(via,pad,land_gap):
                continue
            distance = item_gap(via,pad)
            if distance < land_gap-EPS:
                lands.append(dict(via=via.identity(), land=pad.identity(), gap_mm=distance))
    def stable(records):
        return sorted(records, key=lambda row: json.dumps(row,sort_keys=True))
    return dict(clearance_violations=len(violations), keepout_violations=len(keepout_hits),
                hole_clearance_mm=hole_gap, land_clearance_mm=land_gap,
                hole_pairs=len(pairs), co_located_pairs=sum(r['co_located'] for r in pairs),
                via_land_pairs=len(lands), violating_vias=len({r['via']['uuid'] for r in lands}),
                clearance_details=stable(violations), keepout_details=stable(keepout_hits),
                hole_details=stable(pairs), land_details=stable(lands),
                clearance_epsilon_mm=clearance_epsilon, clearance_boundary_cases=stable(boundary),
                limitations=['Zone outlines are unfilled: pour clearance/thermal attachment is not checked.',
                             'Analytic pad corners; clearance epsilon assumes KiCad 10 default (override if configured differently).',
                             'Keepouts test track/via penetration; exact tangency and <=2 nm overlap are tolerated.',
                             'Not full DRC: board-edge, parity, mask and hole-to-foreign-copper checks excluded.',
                             'Co-location uses identical hole centres; KiCad can also classify nearly coincident centres.',
                             'Reported overlap gaps are not penetration-depth measurements.'])


def main():
    from profiles import ACTIVE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--land-gap', type=float, default=.10)
    parser.add_argument('--include-heatsinks', action='store_true')
    parser.add_argument('--clearance-epsilon', type=float, default=DRC_EPSILON)
    args = parser.parse_args()
    try:
        board = Board(ACTIVE['pcb'])
        result = dict(**board.summary(), **check(board, args.land_gap, args.include_heatsinks, args.clearance_epsilon))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, allow_nan=False))
    return int(any(result[k] for k in ('clearance_violations','keepout_violations','hole_pairs','via_land_pairs')))


if __name__ == '__main__':
    raise SystemExit(main())
