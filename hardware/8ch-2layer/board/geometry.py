"""Plain 2D geometry. No pcbnew types, so it is testable on its own."""

from __future__ import annotations

import math


def segment_distance(px: float, py: float,
                      ax: float, ay: float, bx: float, by: float) -> float:
    dx, dy = bx - ax, by - ay
    span = dx * dx + dy * dy
    t = 0.0 if span == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / span))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def segments_distance(a, b) -> float:
    """Shortest distance between two 2D segments, 0 if they cross.

    The endpoint-to-segment minimum alone is not enough: two segments that
    cross in an X have all four endpoints far apart, and skipping the
    intersection test let stitching stubs be drawn straight across existing
    tracks.
    """
    (ax, ay, bx, by), (cx, cy, dx_, dy_) = a, b
    r_x, r_y = bx - ax, by - ay
    s_x, s_y = dx_ - cx, dy_ - cy
    denominator = r_x * s_y - r_y * s_x
    if abs(denominator) > 1e-12:
        t = ((cx - ax) * s_y - (cy - ay) * s_x) / denominator
        u = ((cx - ax) * r_y - (cy - ay) * r_x) / denominator
        if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
            return 0.0
    return min(segment_distance(ax, ay, cx, cy, dx_, dy_),
               segment_distance(bx, by, cx, cy, dx_, dy_),
               segment_distance(cx, cy, ax, ay, bx, by),
               segment_distance(dx_, dy_, ax, ay, bx, by))


def segment_box_distance(seg, box) -> float:
    """Distance from a segment to an axis-aligned box, 0 if they intersect."""
    x0, y0, x1, y1 = box
    edges = (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
             ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0)))
    ax, ay, bx, by = seg
    if (x0 <= ax <= x1 and y0 <= ay <= y1) or (x0 <= bx <= x1 and y0 <= by <= y1):
        return 0.0
    return min(segments_distance(seg, (p[0], p[1], q[0], q[1])) for p, q in edges)


def point_in_polygon(x: float, y: float, poly) -> bool:
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y):
            if x < x1 + (y - y1) / (y2 - y1) * (x2 - x1):
                inside = not inside
    return inside
