"""Stdlib-only tests for straighten.py (staircase -> 45/90-degree routing); no KiCad required."""
import math
import unittest

from board_text import Board
from straighten import chains, octilinear, plan, turn_ok
from text_geom import segdist

PROJECT = {'board': {'design_settings': {'rules': {'min_clearance': .15, 'min_hole_to_hole': .25}}},
           'net_settings': {'classes': [{'name': 'Default', 'clearance': .2, 'priority': 100}],
                            'netclass_patterns': []}}


def seg(x1, y1, x2, y2, net='"A"', uid=None):
    uid = uid or f's{x1}_{y1}_{x2}_{y2}'.replace('.', 'p').replace('-', 'm')
    return f'(segment (start {x1} {y1}) (end {x2} {y2}) (width .2) (layer "F.Cu") (net {net}) (uuid "{uid}"))'


def staircase(x0=0., y0=0., steps=10, step=.1):
    """Steps of `step` mm right then down, from (x0, y0) to (x0+steps*step, y0+steps*step)."""
    out, x, y = [], x0, y0
    for _ in range(steps):
        out.append(seg(x, y, round(x+step, 4), y)); x = round(x+step, 4)
        out.append(seg(x, y, x, round(y+step, 4))); y = round(y+step, 4)
    return out


def board(*items):
    return Board.from_text('(kicad_pcb (layers (0 "F.Cu" signal) (2 "B.Cu" signal)) ' + ' '.join(items) + ')', PROJECT)


def adds(lines):
    return [[tuple(map(float, p.split(','))) for p in l.split()[4:]] for l in lines if l.startswith('add ')]


class StraightenTests(unittest.TestCase):
    def test_octilinear_paths(self):
        self.assertEqual(octilinear((0, 0), (3, 0)), [[(3, 0)]])
        self.assertEqual(octilinear((0, 0), (2, 2)), [[(2, 2)]])
        diag_first, straight_first = octilinear((0, 0), (3, 1))
        self.assertEqual(diag_first, [(1, 1), (3, 1)])
        self.assertEqual(straight_first, [(2, 0), (3, 1)])
        self.assertTrue(turn_ok((0, 0), (1, 1), (3, 1)))
        self.assertFalse(turn_ok((0, 0), (1, 0), (0, .5)))   # sharper than 90 degrees

    def test_staircase_becomes_one_diagonal_with_end_points_kept(self):
        b = board(*staircase())
        (net, layer, width, pts, seq), = list(chains(b))
        self.assertEqual(len(seq), 20)
        lines, report = plan(b, 'h')
        self.assertEqual(lines[0], '# source sha256 h')
        self.assertEqual(sum(l.startswith('rip ') for l in lines), 20)
        path, = adds(lines)
        self.assertEqual(path, [(0., 0.), (1., 1.)])
        self.assertEqual(report['A']['tiny_after'], 0)

    def test_blocked_diagonal_takes_clear_l_or_keeps_the_run(self):
        # a 1 x 0.5 mm staircase (x then y steps of 0.1 / 0.05) with an other-net track on its
        # diagonal-first route: the result must keep clearance 0.2 + 2 x 0.1 half-width to it
        steps = []
        x, y = 0., 0.
        for _ in range(10):
            steps.append(seg(x, y, round(x+.1, 4), y)); x = round(x+.1, 4)
            steps.append(seg(x, y, x, round(y+.05, 4))); y = round(y+.05, 4)
        blocker = seg(.3, -.4, .3, -.3, '"B"', 'blk')   # blocks the straight-first L only
        lines, _ = plan(board(*steps, blocker), 'h')
        for path in adds(lines):
            for p, q in zip(path, path[1:]):
                self.assertGreaterEqual(segdist(p, q, (.3, -.4), (.3, -.3)), .4 - 1e-6)
        for path in adds(lines):
            for p, q in zip(path, path[1:]):
                d = math.hypot(q[0]-p[0], q[1]-p[1])
                self.assertTrue(abs(p[0]-q[0]) < 1e-6 or abs(p[1]-q[1]) < 1e-6
                                or abs(abs(q[0]-p[0])-abs(q[1]-p[1])) < 1e-6, (p, q))
                self.assertGreater(d, 0)
            self.assertEqual((path[0], path[-1]), ((0., 0.), (1., .5)))
        self.assertEqual(adds(lines), [[(0., 0.), (.5, .5), (1., .5)]])   # diagonal first
        self.assertNotIn('rip blk', lines)

    def test_tapped_segment_stays(self):
        # a same-net track ending on the staircase's copper mid-way must keep its contact
        tap = seg(.55, .5, .55, 1.5, '"A"', 'tap')
        lines, report = plan(board(*staircase(), tap), 'h')
        ripped = {l.split()[1] for l in lines if l.startswith('rip ')}
        self.assertNotIn('tap', ripped)
        self.assertGreater(report['A']['tapped_segments'], 0)
        for path in adds(lines):                       # pieces end on kept joints of the original
            self.assertTrue(all(abs(c*10 - round(c*10)) < 1e-6 for p in (path[0], path[-1]) for c in p))


if __name__ == '__main__':
    unittest.main()
