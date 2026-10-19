"""2-D capsule/polygon geometry and a spatial index in millimetres; stdlib only.

Arcs use chords with bounded sagitta (default 0.001 mm); callers inflate chord
radius by that bound for conservative clearance. Circles/ovals/roundrects are
analytic. Signed gaps inside polygons indicate overlap, not penetration depth.
"""
from collections import defaultdict
from dataclasses import dataclass, field
import math

EPS = 2e-6  # Two nanometres for board-file/float rounding, not routing margin.


def move(point, origin=(0., 0.), angle=0.):
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    x, y = point
    return origin[0]+c*x+s*y, origin[1]-s*x+c*y


def pdist(p, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    dd = dx*dx+dy*dy
    t = max(0., min(1., ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/dd)) if dd else 0.
    return math.hypot(p[0]-a[0]-dx*t, p[1]-a[1]-dy*t)


def cross(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def segdist(a, b, c, d):
    if (max(a[0], b[0])+EPS >= min(c[0], d[0]) and max(c[0], d[0])+EPS >= min(a[0], b[0])
            and max(a[1], b[1])+EPS >= min(c[1], d[1]) and max(c[1], d[1])+EPS >= min(a[1], b[1])):
        if cross(a,b,c)*cross(a,b,d) <= 0 and cross(c,d,a)*cross(c,d,b) <= 0:
            return 0.
    return min(pdist(a,c,d), pdist(b,c,d), pdist(c,a,b), pdist(d,a,b))


def inside(p, poly):
    hit = False
    for a, b in zip(poly, poly[1:]+poly[:1]):
        if (a[1] > p[1]) != (b[1] > p[1]):
            if p[0] < (b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0]:
                hit = not hit
    return hit


@dataclass(eq=False)
class Shape:
    pts: tuple
    radius: float = 0.
    polygon: bool = False

    def __post_init__(self):
        self.pts = tuple(self.pts)
        if not self.pts or self.radius < 0:
            raise ValueError('shape requires points and nonnegative radius')
        self.edges = tuple(zip(self.pts, self.pts[1:]+self.pts[:1])) if self.polygon else ((self.pts[0], self.pts[-1]),)
        self.box = (min(p[0] for p in self.pts)-self.radius, min(p[1] for p in self.pts)-self.radius,
                    max(p[0] for p in self.pts)+self.radius, max(p[1] for p in self.pts)+self.radius)


def gap(a, b):
    if a.polygon and inside(b.pts[0], a.pts) or b.polygon and inside(a.pts[0], b.pts):
        return -a.radius-b.radius
    return min(segdist(p,q,r,s) for p,q in a.edges for r,s in b.edges)-a.radius-b.radius


def rect(centre, size, angle=0., radius=0.):
    w, h = size[0]/2-radius, size[1]/2-radius
    if min(w, h) < -EPS:
        raise ValueError('corner radius exceeds pad half size')
    return Shape(tuple(move(p, centre, angle) for p in ((-w,-h),(w,-h),(w,h),(-w,h))), radius, True)


def arc_points(a, mid, b, error=.001):
    det = 2*cross(a, mid, b)
    if abs(det) < 1e-12:
        raise ValueError('degenerate copper arc')
    aa, mm, bb = sum(x*x for x in a), sum(x*x for x in mid), sum(x*x for x in b)
    centre = ((aa*(mid[1]-b[1])+mm*(b[1]-a[1])+bb*(a[1]-mid[1]))/det,
              (aa*(b[0]-mid[0])+mm*(a[0]-b[0])+bb*(mid[0]-a[0]))/det)
    angles = [math.atan2(p[1]-centre[1], p[0]-centre[0]) for p in (a, mid, b)]
    sweep = (angles[2]-angles[0]) % math.tau
    if (angles[1]-angles[0]) % math.tau > sweep:
        sweep -= math.tau
    radius = math.dist(a, centre)
    step = 2*math.acos(max(-1., 1-min(error/radius, 1.)))
    count = max(2, math.ceil(abs(sweep)/step))
    return [a]+[(centre[0]+radius*math.cos(angles[0]+sweep*i/count),
                 centre[1]+radius*math.sin(angles[0]+sweep*i/count)) for i in range(1,count)]+[b]


@dataclass(eq=False)
class Item:
    kind: str
    net: str
    layers: tuple
    shapes: tuple
    uid: str = ''
    ref: str = ''
    num: str = ''
    centre: tuple = (0., 0.)
    angle: float = 0.
    extra: dict = field(default_factory=dict)
    courts: tuple = ()

    def __post_init__(self):
        self.box = (min(s.box[0] for s in self.shapes), min(s.box[1] for s in self.shapes),
                    max(s.box[2] for s in self.shapes), max(s.box[3] for s in self.shapes))

    def identity(self):
        return dict(uuid=self.uid, kind=self.kind, net=self.net, pad=self.ref+'.'+self.num if self.ref else '')


def item_gap(a, b):
    return min(gap(s, t) for s in a.shapes for t in b.shapes)


class Index:
    def __init__(self, items, cell=2.):
        self.cell, self.data = cell, defaultdict(list)
        for item in items:
            for key in self.keys(item.box, item.layers):
                self.data[key].append(item)

    def keys(self, box, layers):
        x, y, u, v = (math.floor(q/self.cell) for q in box)
        for layer in layers:
            for i in range(x, u+1):
                for j in range(y, v+1):
                    yield layer, i, j

    def query(self, item, margin):
        x,y,u,v = item.box
        seen = set()
        for key in self.keys((x-margin,y-margin,u+margin,v+margin), item.layers):
            for other in self.data.get(key, ()):
                if id(other) not in seen:
                    seen.add(id(other))
                    yield other
