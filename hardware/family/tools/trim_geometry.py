"""Centreline geometry for dangling overshoots, independent of pcbnew."""
import math
import hashlib
import re


def require_source_hash(data, text):
    expected = re.search(r'^# source sha256 ([0-9a-f]{64})$', text, re.M)
    if expected and hashlib.sha256(data).hexdigest() != expected[1]:
        raise ValueError('route-list source hash mismatch; refusing stale plan before loading/saving')


def require_rips(want, known):
    missing = set(want)-set(known)
    if missing:
        raise ValueError(f'missing rip UUIDs; refusing partial apply: {sorted(missing)}')


def projection(point, start, end):
    dx, dy = end[0]-start[0], end[1]-start[1]
    norm = dx*dx+dy*dy
    u = 0. if norm == 0 else ((point[0]-start[0])*dx+(point[1]-start[1])*dy)/norm
    u = max(0., min(1., u))
    return (start[0]+u*dx, start[1]+u*dy)


def junctions(a, b, c, d):
    """Projected endpoints plus a true crossing, including mid-span T/X taps."""
    points = [projection(p, a, b) for p in (c, d)]
    ux, uy, vx, vy = b[0]-a[0], b[1]-a[1], d[0]-c[0], d[1]-c[1]
    den = ux*vy-uy*vx
    if abs(den) > 1e-15:
        t = ((c[0]-a[0])*vy-(c[1]-a[1])*vx)/den
        u = ((c[0]-a[0])*uy-(c[1]-a[1])*ux)/den
        if 0 <= t <= 1 and 0 <= u <= 1:
            points.append((a[0]+t*ux, a[1]+t*uy))
    return points


def retained_segment(start, end, points):
    """Keep the span of connections; zero/one connection means a removable stub."""
    dx, dy = end[0]-start[0], end[1]-start[1]
    length = math.hypot(dx, dy)
    if length < 1e-9 or not points:
        return None
    norm = dx*dx+dy*dy
    along = [((x-start[0])*dx+(y-start[1])*dy)/norm for x, y in points]
    lo, hi = max(0., min(along)), min(1., max(along))
    if (hi-lo)*length < 1e-6:
        return None
    return ((start[0]+lo*dx, start[1]+lo*dy), (start[0]+hi*dx, start[1]+hi*dy))
