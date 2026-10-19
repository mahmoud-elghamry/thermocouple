"""Pure-Python centreline graph extracted from quality10; millimetres throughout.

Supply real copper contact tests through `touch`. Length is shortest centreline
length including pad-centre projections; pad layer changes cost zero and a layer
change through a via counts one. Pours are excluded. This is a routing metric,
not electrical delay, differential impedance, or a replacement for DRC.
"""
from collections import defaultdict
from dataclasses import dataclass
import heapq
import math


def project(point, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    dd = dx * dx + dy * dy
    t = max(0, min(1, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / dd)) if dd else 0
    return a[0] + t * dx, a[1] + t * dy


def crossing(a, b, c, d):
    x, y, u, v = b[0]-a[0], b[1]-a[1], d[0]-c[0], d[1]-c[1]
    den = x*v-y*u
    if abs(den) < 1e-12:
        return None
    t = ((c[0]-a[0])*v-(c[1]-a[1])*u)/den
    s = ((c[0]-a[0])*y-(c[1]-a[1])*x)/den
    return (a[0]+t*x, a[1]+t*y) if -1e-9 <= t <= 1+1e-9 and -1e-9 <= s <= 1+1e-9 else None


@dataclass
class Item:
    kind: str
    layers: tuple
    points: tuple
    label: str = ''
    native: object = None

    @property
    def centre(self):
        return self.points[0]


class Routes:
    def __init__(self, items, touch):
        self.graph = defaultdict(list)
        self.pads = {}
        tracks = [i for i in items if i.kind == 'track']
        split = {id(i): list(i.points) for i in tracks}
        for k, a in enumerate(tracks):
            for b in tracks[:k]:
                if a.layers != b.layers or not touch(a, b):
                    continue
                q = crossing(*a.points, *b.points)
                if q is not None:
                    split[id(a)].append(q)
                    split[id(b)].append(q)
                else:
                    # Preserve the round-11 1 um endpoint rounding convention.
                    for first, second in ((a, b), (b, a)):
                        for pt in first.points:
                            if math.dist(pt, project(pt, *second.points)) < .001:
                                split[id(second)].append(pt)
        lands = [i for i in items if i.kind in ('pad', 'via')]
        for a in lands:
            ns = [self.node(l, a.centre) for l in a.layers]
            for j, u in enumerate(ns):
                for v in ns[:j]:
                    self.edge(u, v, 0, int(a.kind == 'via'))
            if a.kind == 'pad':
                self.pads.setdefault(a.label, ns[0])
            for t in tracks:
                if not set(a.layers) & set(t.layers) or not touch(a, t):
                    continue
                q = project(a.centre, *t.points)
                split[id(t)].append(q)
                self.edge(self.node(t.layers[0], a.centre), self.node(t.layers[0], q), math.dist(a.centre, q))
        for t in tracks:
            ps = sorted(set(split[id(t)]), key=lambda pt: math.dist(pt, t.points[0]))
            for a, b in zip(ps, ps[1:]):
                self.edge(self.node(t.layers[0], a), self.node(t.layers[0], b), math.dist(a, b))
        for k, a in enumerate(lands):
            for b in lands[:k]:
                if not touch(a, b):
                    continue
                for layer in set(a.layers) & set(b.layers):
                    self.edge(self.node(layer, a.centre), self.node(layer, b.centre), math.dist(a.centre, b.centre))

    @staticmethod
    def node(layer, point):
        return layer, round(point[0], 6), round(point[1], 6)

    def edge(self, a, b, length, vias=0):
        if a == b:
            return
        self.graph[a].append((b, length, vias))
        self.graph[b].append((a, length, vias))

    def path(self, source, target):
        start, goal = self.pads[source], self.pads[target]
        heap, best, previous = [(0., 0, start)], {start: (0., 0)}, {}
        while heap:
            length, vias, u = heapq.heappop(heap)
            if best[u] != (length, vias):
                continue
            if u == goal:
                path = [u]
                while path[-1] != start:
                    path.append(previous[path[-1]])
                return dict(length_mm=length, vias=vias, path=path[::-1])
            for v, dd, dv in self.graph[u]:
                score = length + dd, vias + dv
                if score < best.get(v, (math.inf, math.inf)):
                    best[v], previous[v] = score, u
                    heapq.heappush(heap, (*score, v))
        return dict(length_mm=None, vias=None, path=[])


def shared_length(first, second, outside):
    """Shared planar path length outside a common pad (via barrels excluded).

    Both paths must come from the same split graph. Subdivide at their endpoints
    so partial collinear overlap counts too. `outside(layer, a, b)` returns the
    segment length outside the common pad.
    """
    def edges(path):
        return [(a[0], a[1:], b[1:]) for a, b in zip(path, path[1:]) if a[0] == b[0]]
    total, seen = 0., set()
    for layer, a, b in edges(first):
        for other, c, d in edges(second):
            if layer != other or math.dist(a, b) < 1e-9:
                continue
            if any(math.dist(pt, project(pt, a, b)) > 1e-6 for pt in (c, d)):
                # Overlap can extend past a/b; test collinearity on the line.
                dx, dy = b[0]-a[0], b[1]-a[1]
                if any(abs((pt[0]-a[0])*dy-(pt[1]-a[1])*dx) > 1e-6 for pt in (c, d)):
                    continue
            qs = sorted((project(c, a, b), project(d, a, b)), key=lambda pt: math.dist(pt, a))
            u, v = qs
            key = layer, tuple(sorted((u, v)))
            if key in seen or math.dist(u, v) < 1e-9:
                continue
            seen.add(key)
            total += outside(layer, u, v)
    return total


def outside_polygon(a, b, polygon):
    """Segment length outside a simple polygon, including off-centre crossings."""
    if not polygon:
        raise ValueError('empty pad polygon')
    length = math.dist(a, b)
    if length < 1e-12:
        return 0.
    ts = [0., 1.]
    for c, d in zip(polygon, polygon[1:] + polygon[:1]):
        q = crossing(a, b, c, d)
        if q is not None:
            ts.append(min(1., max(0., math.dist(a, q)/length)))
    def inside(pt):
        hit = False
        for c, d in zip(polygon, polygon[1:] + polygon[:1]):
            if math.dist(pt, project(pt, c, d)) < 1e-8:
                return True
            if (c[1] > pt[1]) != (d[1] > pt[1]):
                if pt[0] < (d[0]-c[0])*(pt[1]-c[1])/(d[1]-c[1])+c[0]:
                    hit = not hit
        return hit
    total = 0.
    ts = sorted(set(ts))
    for lo, hi in zip(ts, ts[1:]):
        t = (lo+hi)/2
        if not inside(tuple(x+(y-x)*t for x, y in zip(a, b))):
            total += (hi-lo)*length
    return total
