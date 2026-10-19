"""Decode pad/custom-primitive copper and slotted drills from board text.

Pad angle is the absolute board-file angle. Footprint angle transforms position
only. KiCad's drill offset shifts copper from the hole anchor, not the hole.
Custom pads are a union of their anchor and primitives. Chamfers conservatively
use the enclosing rectangle. Unsupported shapes/primitives raise ValueError.
"""
import math
from text_geom import Shape, move, rect, arc_points
from text_sexp import child, children, val, xy, points

ARC_ERROR = .001


def width(node):
    return float(val(node, 'width', val(child(node, 'stroke', []), 'width', '0')))


def arc_shapes(a, mid, b, radius):
    pts = arc_points(a, mid, b, ARC_ERROR)
    return tuple(Shape((p, q), radius+ARC_ERROR) for p, q in zip(pts, pts[1:]))


def primitives(node, centre, angle):
    shapes = []
    transform = lambda pt: move(pt, centre, angle)
    for primitive in child(node, 'primitives', [])[1:]:
        kind, r = primitive[0], width(primitive)/2
        filled = val(primitive, 'fill', 'no') == 'yes'
        if kind == 'gr_line':
            shapes.append(Shape((transform(xy(primitive, 'start')), transform(xy(primitive, 'end'))), r))
        elif kind == 'gr_arc':
            shapes.extend(arc_shapes(*(transform(xy(primitive, key)) for key in ('start', 'mid', 'end')), r))
        elif kind in ('gr_poly', 'gr_rect'):
            pts = points(primitive)
            if kind == 'gr_rect':
                a, b = xy(primitive, 'start'), xy(primitive, 'end')
                pts = [a, (b[0], a[1]), b, (a[0], b[1])]
            pts = tuple(map(transform, pts))
            if filled:
                shapes.append(Shape(pts, r, True))
            else:
                shapes.extend(Shape((a,b), r) for a,b in zip(pts, pts[1:]+pts[:1]))
        elif kind == 'gr_circle':
            pos, end = xy(primitive, 'center'), xy(primitive, 'end')
            radius = math.dist(pos, end)
            if filled:
                shapes.append(Shape((transform(pos),), radius+r))
            else:
                count = max(8, math.ceil(math.tau/(2*math.acos(max(-1., 1-min(ARC_ERROR/radius, 1.))))))
                pts = [transform((pos[0]+radius*math.cos(i*math.tau/count),
                                  pos[1]+radius*math.sin(i*math.tau/count))) for i in range(count)]
                shapes.extend(Shape((a,b), r+ARC_ERROR) for a,b in zip(pts, pts[1:]+pts[:1]))
        else:
            raise ValueError(f'unsupported custom pad primitive: {kind}')
    return shapes


def pad_shapes(node, centre, angle):
    w, h = xy(node, 'size')
    kind = node[3]
    if min(w, h) <= 0:
        raise ValueError('pad size must be positive')
    if kind == 'circle':
        if abs(w-h) > 1e-6:
            raise ValueError('non-circular circle pad')
        return (Shape((centre,), w/2),)
    if kind == 'oval':
        radius = min(w,h)/2
        delta = w/2-radius, h/2-radius
        return (Shape(tuple(move((s*delta[0],s*delta[1]), centre, angle) for s in (-1,1)), radius),)
    if kind in ('rect', 'roundrect'):
        ratio = float(val(node, 'roundrect_rratio', '0')) if kind == 'roundrect' else 0.
        if not 0 <= ratio <= .5:
            raise ValueError('invalid roundrect_rratio')
        radius = min(w,h)*ratio if not child(node, 'chamfer') else 0.
        return (rect(centre, (w,h), angle, radius),)
    if kind == 'custom':
        anchor = val(child(node, 'options', []), 'anchor', 'rect')
        if anchor not in ('rect', 'circle'):
            raise ValueError(f'unsupported custom pad anchor {anchor}')
        base = Shape((centre,), w/2) if anchor == 'circle' else rect(centre, (w,h), angle)
        return (base, *primitives(node, centre, angle))
    raise ValueError(f'unsupported pad shape: {kind}')


def drill_shape(node, anchor, angle):
    drill = child(node, 'drill')
    if not drill:
        return None
    dims = [float(x) for x in drill[1:] if isinstance(x, str) and x != 'oval']
    if len(dims) not in (1,2) or min(dims) <= 0:
        raise ValueError('unsupported drill dimensions')
    w, h = dims if len(dims) == 2 else (dims[0], dims[0])
    radius = min(w,h)/2
    delta = w/2-radius, h/2-radius
    return Shape(tuple(move((s*delta[0],s*delta[1]), anchor, angle) for s in (-1,1)), radius)
