"""Read KiCad board, project classes and family clearance rules with stdlib only.

API: Board(path), Board.from_text(pcb_text, project_dict, dru_text). CLI prints a
read-only inventory using existing --board/--pcb profiles. Zone polygons are
outlines only; cached filled_polygon data is deliberately ignored. Courtyard
linework uses an enclosing board-axis rectangle (reported approximation).
Copper graphics/text and footprint-local zones are explicitly rejected.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

from text_geom import Item, Shape, move, rect, item_gap, EPS
from text_rules import Rules
from text_sexp import parse, child, children, val, xy, points
from text_shapes import arc_shapes, pad_shapes, drill_shape


class Board:
    def __init__(self, path):
        path = Path(path).resolve()
        paths = [path, path.with_suffix('.kicad_pro'), path.with_suffix('.kicad_dru')]
        raw = [p.read_bytes() for p in paths]  # Require matching copy sidecars, never fallback.
        self._read(raw[0].decode('utf-8-sig'), json.loads(raw[1].decode('utf-8-sig')), raw[2].decode('utf-8-sig'))
        self.path = str(path)
        self.hashes = {p.name: hashlib.sha256(data).hexdigest() for p, data in zip(paths, raw)}

    @classmethod
    def from_text(cls, text, project, rules=''):
        self = cls.__new__(cls)
        self._read(text, project, rules)
        self.path, self.hashes = '<memory>', {}
        return self

    def _read(self, text, project, rule_text):
        roots = parse(text)
        if len(roots) != 1 or roots[0][0] != 'kicad_pcb':
            raise ValueError('expected one kicad_pcb root')
        root = roots[0]
        self.layers = tuple(n[1] for n in child(root, 'layers', [])[1:]
                            if isinstance(n, list) and str(n[1]).endswith('.Cu'))
        if not self.layers:
            raise ValueError('board has no copper layer definitions')
        self.nets = {n[1]: n[-1] for n in children(root, 'net')}
        self.rules = Rules(project, rule_text)
        self.items, self.holes, self.zones, self.keepouts = [], [], [], []
        self.courtyards, self.approximations = {}, set()
        for node in root[1:]:
            if not isinstance(node, list):
                continue
            kind = node[0]
            if kind == 'footprint':
                self._footprint(node)
            elif kind == 'segment':
                self.items.append(self._item(node, 'Track', (Shape((xy(node,'start'),xy(node,'end')),
                                                                          float(val(node,'width'))/2),)))
            elif kind == 'arc':
                shapes = arc_shapes(*(xy(node, k) for k in ('start','mid','end')), float(val(node,'width'))/2)
                self.items.append(self._item(node, 'Track', shapes, extra={'arc': True}))
                self.approximations.add('Copper arcs: chords inflated by <= 0.001 mm sagitta.')
            elif kind == 'via':
                pos = xy(node)
                item = self._item(node, 'Via', (Shape((pos,), float(val(node,'size'))/2),), centre=pos)
                self.items.append(item)
                self.holes.append(self._item(node, 'Via', (Shape((pos,), float(val(node,'drill'))/2),), centre=pos))
            elif kind == 'zone':
                shapes = tuple(Shape(tuple(points(p)), 0., True) for p in children(node, 'polygon'))
                if not shapes:
                    raise ValueError('zone has no outline polygon')
                ko = child(node, 'keepout')
                extra = {k: val(ko, k) == 'not_allowed' for k in ('tracks','vias','pads','copperpour')} if ko else {}
                zone = self._item(node, 'Zone', shapes, extra=extra)
                (self.keepouts if ko else self.zones).append(zone)
            elif self._layers(node):
                raise ValueError(f'unsupported copper graphic/text/item: {kind}')
        for item in self.items:
            item.courts = tuple(ref for ref, court in self.courtyards.items() if item_gap(item,court) <= EPS)

    def _layers(self, node):
        ls = (child(node, 'layers') or child(node, 'layer') or [None])[1:]
        if '*.Cu' in ls:
            return self.layers
        if 'F&B.Cu' in ls:
            return tuple(l for l in self.layers if l in ('F.Cu','B.Cu'))
        if node[0] == 'via' and len(ls) == 2:
            lo, hi = sorted(self.layers.index(l) for l in ls)
            return self.layers[lo:hi+1]
        return tuple(l for l in self.layers if l in ls)

    def _item(self, node, kind, shapes, **kwargs):
        net = child(node, 'net')
        name = self.nets.get(net[1], net[-1]) if net else ''
        return Item(kind, name, self._layers(node), shapes, str(val(node,'uuid')), **kwargs)

    def _footprint(self, node):
        origin, at = xy(node), child(node,'at', [])
        angle = float(at[3]) if len(at) > 3 else 0.
        ref = next((p[2] for p in children(node,'property') if p[1]=='Reference'), '')
        for part in node[1:]:
            if not isinstance(part,list) or not part:
                continue
            if part[0] == 'zone':
                raise ValueError('unsupported footprint-local zone/keepout')
            if (part[0].startswith('fp_') or part[0]=='property') and self._layers(part):
                raise ValueError(f'unsupported footprint copper graphic/text: {part[0]}')
        if ref in self.rules.courtyards:
            self._courtyard(node, ref, origin, angle)
        for pad in children(node,'pad'):
            anchor = move(xy(pad), origin, angle)
            at = child(pad,'at', [])
            absolute = float(at[3]) if len(at) > 3 else 0.
            centre = move(xy(child(pad,'drill',[]),'offset'), anchor, absolute)
            kwargs = dict(ref=ref, num=pad[1], centre=centre, angle=absolute)
            drill = drill_shape(pad, anchor, absolute)
            if drill:
                hole = self._item(pad, 'Pad', (drill,), **{**kwargs, 'centre': anchor})
                hole.layers = self.layers  # Pad holes cross the entire stack, including NPTH.
                self.holes.append(hole)
            if pad[2] == 'np_thru_hole' or not self._layers(pad):
                continue
            shapes = pad_shapes(pad, centre, absolute)
            extra = dict(smd=pad[2]=='smd', heatsink=val(pad,'property')=='pad_prop_heatsink', shape=pad[3])
            self.items.append(self._item(pad, 'Pad', shapes, extra=extra, **kwargs))
            if pad[3] == 'custom':
                self.approximations.add('Custom pads: union of anchor/primitives; unfilled curves use inflated chords.')
            if child(pad,'chamfer'):
                self.approximations.add('Chamfered pad: conservative enclosing rectangle.')

    def _courtyard(self, node, ref, origin, angle):
        pts, exact = [], []
        for g in node[1:]:
            if not isinstance(g,list) or val(g,'layer') not in ('F.CrtYd','B.CrtYd'):
                continue
            if g[0] == 'fp_rect':
                a,b = xy(g,'start'),xy(g,'end')
                exact.append(Shape(tuple(move(p,origin,angle) for p in (a,(b[0],a[1]),b,(a[0],b[1]))),0.,True))
            elif g[0] == 'fp_poly':
                exact.append(Shape(tuple(move(p,origin,angle) for p in points(g)),0.,True))
            elif g[0] in ('fp_line','fp_arc'):
                pts.extend(move(xy(g,k),origin,angle) for k in ('start','end'))
                if g[0] == 'fp_arc':
                    pts.extend(move(p,origin,angle) for p in (xy(g,'mid'),))
        if pts:
            x,y = min(p[0] for p in pts),min(p[1] for p in pts)
            u,v = max(p[0] for p in pts),max(p[1] for p in pts)
            exact.append(rect(((x+u)/2,(y+v)/2),(u-x,v-y)))
            self.approximations.add('Courtyard linework: enclosing board-axis rectangle for area-rule matching.')
        if exact:
            self.courtyards[ref] = Item('Courtyard','',self.layers,tuple(exact),ref=ref)

    def summary(self):
        return dict(board=self.path, hashes=self.hashes, layers=self.layers,
                    items=dict(Counter(i.kind for i in self.items)), holes=len(self.holes),
                    zones=len(self.zones), keepouts=len(self.keepouts),
                    clearance_rules=[n for n,_,_ in self.rules.rules],
                    ignored_constraints=self.rules.ignored, approximations=sorted(self.approximations))


def main():
    from profiles import ACTIVE
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        result = Board(ACTIVE['pcb']).summary()
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
