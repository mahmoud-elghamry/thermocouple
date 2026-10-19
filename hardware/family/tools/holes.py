"""Audit drill spacing and via-hole/SMD clearance with KiCad's effective shapes.

No board saves. All nets count, including same-net holes/lands. Only pads marked
heatsink in the footprint are exempt by default (reported explicitly). Land gaps
use native shape collision; negative -radius indicates overlap, not its depth.
Hole capsules include slots and drill offsets.
co_located_pairs counts exactly identical centres; KiCad also tolerates nearly
coincident centres, so its spacing/co-location category split can differ.
"""
import argparse
import math
from audit_common import emit, identity, layers, load_board, positive_mm, selected_board


def audit(board, hole_gap=.25, land_gap=.10, include_heatsinks=False):
    import pcbnew as p
    positive_mm(hole_gap)
    positive_mm(land_gap)
    pads = [pad for f in board.GetFootprints() for pad in f.Pads()]
    vias = [t for t in board.GetTracks() if t.Type() == p.PCB_VIA_T]
    holes = [(v, v.GetEffectiveHoleShape()) for v in vias]
    holes += [(a, a.GetEffectiveHoleShape()) for a in pads if a.GetDrillSize().x > 0]
    exempt, lands = [], []
    for pad in pads:
        ls = layers(board, pad)
        if pad.GetAttribute() != p.PAD_ATTRIB_SMD or not ls:
            continue
        if not include_heatsinks and pad.GetProperty() == p.PAD_PROP_HEATSINK:
            exempt.append(identity(pad))
        else:
            box = pad.GetBoundingBox()
            bounds = box.GetLeft(), box.GetTop(), box.GetRight(), box.GetBottom()
            lands.append((pad, [(l, pad.GetEffectiveShape(l)) for l in ls], bounds))
    pairs, intrusions = [], []
    # One IU tolerance avoids classifying a nominal equality as a failure.
    limit = p.FromMM(hole_gap) - 1
    def box(shape):
        a, b, r = shape.GetStart(), shape.GetEnd(), shape.GetWidth()/2
        return min(a.x, b.x)-r, min(a.y, b.y)-r, max(a.x, b.x)+r, max(a.y, b.y)+r
    bounds = [box(shape) for _, shape in holes]
    spans = [set(layers(board, a)) if a.Type() == p.PCB_VIA_T
             else set(board.GetEnabledLayers().CuStack()) for a, _ in holes]
    for k, (a, sa) in enumerate(holes):
        ax, ay, au, av = bounds[k]
        for j, (b, sb) in enumerate(holes[:k]):
            if not spans[k] & spans[j]:
                continue
            bx, by, bu, bv = bounds[j]
            if max(ax-bu, bx-au, ay-bv, by-av) >= limit:
                continue
            if p.SHAPE.Collide(sa, sb, limit):
                pairs.append(dict(a=identity(a), b=identity(b),
                                  co_located=sa.GetCenter() == sb.GetCenter()))
    minimum = None
    def copper_gap(hole, shape, radius, upper):
        # SHAPE.Distance(point) can return distance to a roundrect's core,
        # omitting its corner radius. Shape-to-shape Collide includes real copper.
        if p.SHAPE.Collide(hole,shape,0):
            return -radius
        lo, hi = 0, max(1,int(upper))
        while not p.SHAPE.Collide(hole,shape,hi):
            hi *= 2
            if hi > p.FromMM(10000):
                raise ValueError('invalid/empty pad shape in hole audit')
        while hi-lo > 1:
            mid = (lo+hi)//2
            if p.SHAPE.Collide(hole,shape,mid):
                hi = mid
            else:
                lo = mid
        return lo
    for via in vias:
        radius = via.GetDrillValue() / 2
        pos = via.GetPosition()
        hole = via.GetEffectiveHoleShape()
        for pad, shapes, (x, y, u, v) in lands:
            lower = math.hypot(max(x-pos.x, pos.x-u, 0), max(y-pos.y, pos.y-v, 0)) - radius
            if minimum is not None and lower >= max(p.FromMM(land_gap), minimum):
                continue
            # Respect the span of blind/buried holes as well as through vias.
            candidates = [s for l,s in shapes if via.IsOnLayer(l) and (minimum is None or
                          p.SHAPE.Collide(hole,s,int(max(p.FromMM(land_gap),minimum))+2))]
            gaps = [copper_gap(hole,s,radius,s.Distance(pos)+radius+1) for s in candidates]
            if not gaps:
                continue
            gap = min(gaps)
            minimum = gap if minimum is None else min(minimum, gap)
            if gap < p.FromMM(land_gap) - 1:
                intrusions.append(dict(via=identity(via), land=identity(pad),
                                       edge_gap_mm=p.ToMM(int(gap))))
    return dict(hole_clearance_mm=hole_gap, land_clearance_mm=land_gap,
                holes=len(holes), vias=len(vias), smd_lands=len(lands),
                exempt_heatsinks=exempt, hole_pairs=len(pairs),
                co_located_pairs=sum(x['co_located'] for x in pairs),
                via_land_pairs=len(intrusions),
                violating_vias=len({x['via']['uuid'] for x in intrusions}),
                minimum_via_land_gap_mm=None if minimum is None else p.ToMM(int(minimum)),
                hole_details=pairs, land_details=intrusions)


def main():
    profile = selected_board()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hole-gap', type=positive_mm, default=.25)
    parser.add_argument('--land-gap', type=positive_mm, default=.10)
    parser.add_argument('--include-heatsinks', action='store_true')
    args = parser.parse_args()
    result = audit(load_board(profile), args.hole_gap, args.land_gap, args.include_heatsinks)
    emit(profile, result)
    return int(bool(result['hole_pairs'] or result['via_land_pairs']))


if __name__ == '__main__':
    raise SystemExit(main())
