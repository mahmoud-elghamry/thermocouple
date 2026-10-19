"""Read-only pcbnew adapter for the pure centreline graph; no text-board parser.

Actual copper contacts use native shapes. Arcs on measured nets and non-convex
custom pads fail explicitly rather than silently returning misleading lengths.
"""
from audit_common import layers
from route_graph import Item, Routes, outside_polygon


class BoardRoutes:
    def __init__(self, board):
        import pcbnew
        self.p = pcbnew
        self.board = board
        self.pads = {}
        self.duplicate_labels = set()
        for f in board.GetFootprints():
            for pad in f.Pads():
                if layers(board, pad):
                    label = f.GetReference() + '.' + pad.GetNumber()
                    if label in self.pads:
                        self.duplicate_labels.add(label)
                    self.pads.setdefault(label, pad)
        self.graphs = {}
        self.shapes = {}

    def xy(self, point):
        return self.p.ToMM(point.x), self.p.ToMM(point.y)

    def shape(self, item, layer):
        key = item.native.m_Uuid.AsString(), layer
        if key not in self.shapes:
            self.shapes[key] = item.native.GetEffectiveShape(layer)
        return self.shapes[key]

    def touch(self, a, b):
        return any(self.p.SHAPE.Collide(self.shape(a, l), self.shape(b, l), 1)
                   for l in set(a.layers) & set(b.layers))

    def graph(self, net):
        if net not in self.graphs:
            if any(self.pads[label].GetNetname() == net for label in self.duplicate_labels):
                raise ValueError(f'duplicate copper pad numbers on measured net {net} unsupported')
            items = []
            for pad in self.pads.values():
                if pad.GetNetname() == net:
                    if pad.GetShape() == self.p.PAD_SHAPE_CUSTOM:
                        raise ValueError('custom pad routing metrics unsupported')
                    label = pad.GetParentFootprint().GetReference() + '.' + pad.GetNumber()
                    ls = layers(self.board, pad)
                    centres = {self.xy(pad.ShapePos(l)) for l in ls}
                    if len(centres) != 1:
                        raise ValueError('layer-dependent pad centres unsupported')
                    items.append(Item('pad', ls, (centres.pop(),), label, pad))
            for t in self.board.GetTracks():
                if t.GetNetname() != net:
                    continue
                ls = layers(self.board, t)
                if t.Type() == self.p.PCB_VIA_T:
                    items.append(Item('via', ls, (self.xy(t.GetPosition()),), native=t))
                elif t.Type() == self.p.PCB_TRACE_T:
                    items.append(Item('track', ls, (self.xy(t.GetStart()), self.xy(t.GetEnd())), native=t))
                else:
                    raise ValueError(f'arcs/unknown tracks on measured net {net} unsupported')
            self.graphs[net] = Routes(items, self.touch)
        return self.graphs[net]

    def path(self, source, target):
        a, b = self.pads[source], self.pads[target]
        net = a.GetNetname()
        if not net or net != b.GetNetname():
            raise ValueError(f'{source} and {target} must share a nonempty net')
        return dict(net=net, source=source, target=target, **self.graph(net).path(source, target))

    def outside(self, label):
        pad = self.pads[label]
        polygons = {}
        for layer in layers(self.board, pad):
            poly = pad.GetEffectivePolygon(layer)
            if poly.OutlineCount() != 1 or poly.HasHoles():
                raise ValueError('shared-run clipping requires one pad outline without holes')
            outline = poly.COutline(0)
            polygons[layer] = [self.xy(outline.CPoint(i)) for i in range(outline.PointCount())]
        return lambda layer, a, b: outside_polygon(a, b, polygons[layer])
