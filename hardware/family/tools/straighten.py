"""Plan clean 45/90-degree routing for the grid router's staircase tracks (I-141); stdlib only.

Usage: python -S straighten.py --board 8|8l|40|24 [--pcb COPY] --out LIST [--report JSON]
A chain is a run of one net's tracks on one layer, same width, joined end to end at points where
nothing else touches (no pad, via, third track or mid-track tap). Chains with at least MIN_TINY
segments shorter than TINY mm are string-pulled: from each kept point the farthest later point
reachable by one or two 0/45/90-degree segments is taken, if those segments keep the resolved
clearance (+MARGIN) to every other-net pad/track/via (text_rules, as text_check), stay out of
keepouts and make no turn sharper than 90 degrees. The two chain ends never move. The route list
(`rip`/`add`, source hash header) is applied to a copy with `finish.py apply`; KiCad DRC, holes
and pour checks remain the gates. Zones are not checked here (refill flows around new tracks).
"""
import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

from board_text import Board
from text_geom import Index, Item, Shape, item_gap, EPS

TINY, MIN_TINY, MARGIN, MIN_PIECE = .15, 4, .005, .05
DIRS = [(math.cos(math.radians(a)), math.sin(math.radians(a))) for a in range(0, 360, 45)]


def key(p):
    return round(p[0], 4), round(p[1], 4)


def octilinear(a, b):
    """One or two 0/45/90-degree paths from a to b: lists of points without a."""
    dx, dy = b[0]-a[0], b[1]-a[1]
    ax, ay = abs(dx), abs(dy)
    if ax < 1e-6 or ay < 1e-6 or abs(ax-ay) < 1e-6:
        return [[b]]
    m = min(ax, ay)
    diag = (a[0]+math.copysign(m, dx), a[1]+math.copysign(m, dy))
    straight = (b[0]-math.copysign(m, dx), b[1]-math.copysign(m, dy))
    return [[diag, b], [straight, b]]


def turn_ok(p, q, r):
    """Direction change at q of at most 90 degrees (interior angle >= 90)."""
    u, v = (q[0]-p[0], q[1]-p[1]), (r[0]-q[0], r[1]-q[1])
    return u[0]*v[0]+u[1]*v[1] >= -EPS


def touches(a, b):
    """Electrical contact: pad/via copper overlaps, tracks only where centre lines meet."""
    r = a.shapes[0].radius + b.shapes[0].radius if a.kind == b.kind == 'Track' else 0.
    return item_gap(a, b) <= -r + 1e-4


def chains(board):
    """Yield (net, layer, width, [points], [track items]) for every maximal end-to-end chain."""
    tracks = [t for t in board.items if t.kind == 'Track' and not t.extra.get('arc')]
    ends = defaultdict(list)
    for t in tracks:
        a, b = t.shapes[0].pts[0], t.shapes[0].pts[-1]
        for p in (a, b):
            ends[(t.net, t.layers[0], key(p))].append(t)
    others = [i for i in board.items if i.kind in ('Pad', 'Via')]
    index, track_index = Index(others), Index(tracks)

    def free(net, layer, p, pair):
        """An inner joint: exactly these two tracks, same width, nothing else of the net there."""
        if len(pair) != 2 or pair[0].shapes[0].radius != pair[1].shapes[0].radius:
            return False
        dot = Item('Track', net, (layer,), (Shape((p,), 0.),))
        for o in index.query(dot, .01):
            if o.net == net and layer in o.layers and item_gap(dot, o) <= 1e-4:
                return False
        for o in track_index.query(dot, .01):
            if o.net == net and o.layers[0] == layer and o not in pair and touches(dot, o):
                return False
        return True

    inner = {k: free(k[0], k[1], k[2], v) for k, v in ends.items()}
    seen = set()
    for t in tracks:
        if id(t) in seen:
            continue
        net, layer = t.net, t.layers[0]
        seq, pts = [t], list(t.shapes[0].pts[::len(t.shapes[0].pts)-1])
        seen.add(id(t))
        for forward in (True, False):
            while True:
                p = pts[-1] if forward else pts[0]
                k = (net, layer, key(p))
                if not inner.get(k):
                    break
                nxt = next(o for o in ends[k] if o is not (seq[-1] if forward else seq[0]))
                if id(nxt) in seen:
                    break
                seen.add(id(nxt))
                a, b = nxt.shapes[0].pts[0], nxt.shapes[0].pts[-1]
                q = b if key(a) == key(p) else a
                if forward:
                    seq.append(nxt); pts.append(q)
                else:
                    seq.insert(0, nxt); pts.insert(0, q)
        yield net, layer, t.shapes[0].radius * 2, pts, seq


class Checker:
    def __init__(self, board):
        self.board = board
        self.index = Index([i for i in board.items if i.kind in ('Pad', 'Track', 'Via')])

    def item(self, net, layer, width, a, b):
        it = Item('Track', net, (layer,), (Shape((a, b), width/2),))
        it.courts = tuple(ref for ref, c in self.board.courtyards.items() if item_gap(it, c) <= EPS)
        return it

    def clear(self, it):
        rules = self.board.rules
        for o in self.index.query(it, rules.maximum + MARGIN):
            if o.net == it.net and it.net:
                continue
            need, _ = rules.clearance(it, o)
            if item_gap(it, o) < need + MARGIN - EPS:
                return False
        for zone in self.board.keepouts:
            if zone.extra.get('tracks') and set(it.layers) & set(zone.layers) and item_gap(it, zone) < -EPS:
                return False
        return True

    def tapped(self, net, layer, pts, seq):
        """Indices of chain segments that a same-net pad, via or other track touches away from the
        chain's two end points: ripping them would cut that connection, so they stay."""
        mine = {id(t) for t in seq}
        dots = [Item('Track', net, (layer,), (Shape((p,), 0.),)) for p in (pts[0], pts[-1])]
        hit = set()
        for k, t in enumerate(seq):
            for o in self.index.query(t, .01):
                # KiCad joins overlapping copper, so any overlap is a contact (a track end touching
                # a staircase's copper without meeting its centre line counts too)
                if o.net != net or id(o) in mine or layer not in o.layers or item_gap(t, o) > 1e-4:
                    continue
                if not any(item_gap(d, o) <= 1e-4 for d in dots):
                    hit.add(k)
        return hit

    def add(self, it):
        for k in self.index.keys(it.box, it.layers):
            self.index.data[k].append(it)


def pull(pts, net, layer, width, check, before=None, after=None):
    """String-pull one piece; `before`/`after` are the kept neighbours' far points (turn checks).
    Return the new point list or None when nothing improves."""
    out, i, n = [pts[0]], 0, len(pts) - 1
    while i < n:
        best = None
        for j in range(n, i, -1):
            for path in octilinear(pts[i], pts[j]):
                cand = [out[-1]] + path
                if any(math.dist(p, q) < MIN_PIECE and k not in (0, len(cand)-2)
                       for k, (p, q) in enumerate(zip(cand, cand[1:]))):
                    continue
                prev = out[-2] if len(out) > 1 else before
                if prev and not turn_ok(prev, cand[0], cand[1]):
                    continue
                if any(not turn_ok(*cand[k:k+3]) for k in range(len(cand)-2)):
                    continue
                nxt = pts[j+1] if j < n else after
                if nxt and not turn_ok(cand[-2], pts[j], nxt):
                    continue
                if all(check.clear(check.item(net, layer, width, p, q)) for p, q in zip(cand, cand[1:])):
                    best = (j, path)
                    break
            if best:
                break
        if not best:                       # keep the original segment
            best = (i+1, [pts[i+1]])
        i, path = best
        out.extend(path)
    return out if len(out) < len(pts) else None


def plan(board, source_hash):
    check, lines, report = Checker(board), [f'# source sha256 {source_hash}'], defaultdict(lambda: defaultdict(int))
    for net, layer, width, pts, seq in chains(board):
        tiny = sum(1 for p, q in zip(pts, pts[1:]) if math.dist(p, q) < TINY)
        if tiny < MIN_TINY:
            continue
        r = report[net]
        r['chains'] += 1; r['tiny_before'] += tiny
        fixed = check.tapped(net, layer, pts, seq)
        short = net.rsplit('/', 1)[-1]      # finish.py add matches the last path element
        if sum(1 for n in {i.net for i in board.items} if n.rsplit('/', 1)[-1] == short) != 1:
            raise SystemExit(f'net name {net} is ambiguous for finish.py add')
        done, k = False, 0
        while k < len(seq):                 # pieces between kept (tapped) segments
            if k in fixed:
                r['tiny_after'] += math.dist(pts[k], pts[k+1]) < TINY
                k += 1
                continue
            e = k
            while e < len(seq) and e not in fixed:
                e += 1
            piece = pts[k:e+1]
            new = pull(piece, net, layer, width, check, pts[k-1] if k else None, pts[e+1] if e < len(seq) else None)                 if len(piece) > 2 else None
            if not new:
                r['tiny_after'] += sum(1 for p, q in zip(piece, piece[1:]) if math.dist(p, q) < TINY)
            else:
                done = True
                for p, q in zip(new, new[1:]):
                    check.add(check.item(net, layer, width, p, q))
                r['segments'] += e - k; r['segments_after'] += len(new) - 1
                r['tiny_after'] += sum(1 for p, q in zip(new, new[1:]) if math.dist(p, q) < TINY)
                lines.extend(f'rip {t.uid}' for t in seq[k:e])
                lines.append(f'add {short} {layer} {width:g} ' + ' '.join(f'{p[0]:.6f},{p[1]:.6f}' for p in new))
            k = e
        r['replaced' if done else 'kept'] += 1
        r['tapped_segments'] += len(fixed)
    return lines, {k: dict(v) for k, v in sorted(report.items())}


def main():
    from profiles import ACTIVE
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', required=True)
    ap.add_argument('--report')
    args = ap.parse_args()
    pcb = Path(ACTIVE['pcb'])
    board = Board(pcb)
    lines, report = plan(board, hashlib.sha256(pcb.read_bytes()).hexdigest())
    Path(args.out).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    total = {k: sum(r.get(k, 0) for r in report.values())
             for k in ('chains', 'replaced', 'kept', 'tiny_before', 'tiny_after', 'segments', 'segments_after')}
    if args.report:
        Path(args.report).write_text(json.dumps(dict(board=str(pcb), total=total, nets=report), indent=1), encoding='utf-8')
    print(json.dumps(total))


if __name__ == '__main__':
    main()
