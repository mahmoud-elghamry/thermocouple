"""Orthogonal segment geometry shared by the router and the label placer."""
EPS = 1e-6


def on_seg(pt, a, b):
    (x, y), (x1, y1), (x2, y2) = pt, a, b
    if abs(x1 - x2) < EPS:
        return abs(x - x1) < EPS and min(y1, y2) - EPS <= y <= max(y1, y2) + EPS
    return abs(y - y1) < EPS and min(x1, x2) - EPS <= x <= max(x1, x2) + EPS


def seg_hits_box(a, b, bb, m=0.3):
    x0, y0, x1, y1 = bb[0] + m, bb[1] + m, bb[2] - m, bb[3] - m
    if x0 >= x1:  # thin body (a 2-pin part drawn as a line): give it 1.2 mm
        x0, x1 = (bb[0] + bb[2]) / 2 - 0.6, (bb[0] + bb[2]) / 2 + 0.6
    if y0 >= y1:
        y0, y1 = (bb[1] + bb[3]) / 2 - 0.6, (bb[1] + bb[3]) / 2 + 0.6
    sx0, sx1 = sorted((a[0], b[0])); sy0, sy1 = sorted((a[1], b[1]))
    return sx1 > x0 and sx0 < x1 and sy1 > y0 and sy0 < y1
