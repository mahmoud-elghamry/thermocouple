"""Plain unittest coverage for extracted graph/geometry and audit CLI contracts."""
import math
import os
from pathlib import Path
import subprocess
import sys
import unittest

from audit_common import positive_mm
from profiles_checks import apply
from route_graph import Item, Routes, crossing, outside_polygon, project, shared_length


def pad(label, xy, layers=('F',)):
    return Item('pad', layers, (xy,), label)


def track(a, b, layer='F'):
    return Item('track', (layer,), (a, b))


def contact(a, b):
    """Exact centreline contacts for synthetic zero-width tracks/point lands."""
    if not set(a.layers) & set(b.layers):
        return False
    if a.kind == b.kind == 'track':
        return crossing(*a.points, *b.points) is not None or any(
            math.dist(pt, project(pt, *b.points)) < 1e-8 for pt in a.points)
    if a.kind == 'track':
        a, b = b, a
    if b.kind == 'track':
        return math.dist(a.centre, project(a.centre, *b.points)) < 1e-8
    return a.centre == b.centre


class GeometryTests(unittest.TestCase):
    def test_projection_clamps_and_degenerate(self):
        self.assertEqual(project((3, 2), (0, 0), (2, 0)), (2, 0))
        self.assertEqual(project((3, 2), (1, 1), (1, 1)), (1, 1))

    def test_crossing_and_parallel(self):
        self.assertEqual(crossing((0, 0), (2, 2), (0, 2), (2, 0)), (1, 1))
        self.assertIsNone(crossing((0, 0), (1, 0), (0, 1), (1, 1)))
        self.assertIsNone(crossing((0, 0), (1, 0), (2, -1), (2, 1)))

    def test_polygon_clips_offcentre_crossing_and_boundary(self):
        polygon = [(1, -1), (2, -1), (2, 1), (1, 1)]
        self.assertAlmostEqual(outside_polygon((0, 0), (10, 0), polygon), 9)
        self.assertAlmostEqual(outside_polygon((0, 1), (3, 1), polygon), 2)
        self.assertEqual(outside_polygon((1.2, 0), (1.8, 0), polygon), 0)
        self.assertAlmostEqual(outside_polygon((0, 2), (3, 2), polygon), 3)
        with self.assertRaises(ValueError):
            outside_polygon((0, 0), (1, 1), [])

    def test_rotated_polygon(self):
        diamond = [(0, -1), (1, 0), (0, 1), (-1, 0)]
        self.assertAlmostEqual(outside_polygon((-2, .5), (2, .5), diamond), 3)

    def test_threshold_validation(self):
        for value in (0, -1, 'nan', 'inf'):
            with self.assertRaises(ValueError):
                positive_mm(value)


class RouteTests(unittest.TestCase):
    def test_midsegment_t_and_crossing(self):
        items = [pad('A', (0, 0)), pad('B', (1, 1)), track((0, 0), (2, 0)), track((1, 0), (1, 1))]
        result = Routes(items, contact).path('A', 'B')
        self.assertEqual((result['length_mm'], result['vias']), (2, 0))

    def test_collinear_join(self):
        items = [pad('A', (0, 0)), pad('B', (3, 0)), track((0, 0), (2, 0)), track((1, 0), (3, 0))]
        self.assertEqual(Routes(items, contact).path('A', 'B')['length_mm'], 3)

    def test_all_layer_via_counts_once_and_tht_counts_zero(self):
        items = [pad('A', (0, 0)), pad('B', (2, 0), ('B',)),
                 track((0, 0), (1, 0)), track((1, 0), (2, 0), 'B')]
        via = Item('via', ('F', 'I1', 'I2', 'B'), ((1, 0),))
        result = Routes(items+[via], contact).path('A', 'B')
        self.assertEqual((result['length_mm'], result['vias']), (2, 1))
        tht = pad('THT', (1, 0), ('F', 'B'))
        self.assertEqual(Routes(items+[tht], contact).path('A', 'B')['vias'], 0)

    def test_disconnected_and_missing(self):
        g = Routes([pad('A', (0, 0)), pad('B', (2, 0))], contact)
        self.assertIsNone(g.path('A', 'B')['length_mm'])
        with self.assertRaises(KeyError):
            g.path('missing', 'A')

    def test_shortest_prefers_length_then_vias(self):
        g = Routes([pad('A', (0, 0)), pad('B', (2, 0))], contact)
        a, b, mid = g.pads['A'], g.pads['B'], ('I', 1, 0)
        g.edge(a, b, 3, 0)
        g.edge(a, mid, 1, 1)
        g.edge(mid, b, 1, 0)
        self.assertEqual(g.path('A', 'B')['vias'], 1)
        g.edge(a, b, 2, 0)
        self.assertEqual(g.path('A', 'B')['vias'], 0)

    def test_shared_partial_reverse_excludes_via_and_pad(self):
        first = [('F', 0, 0), ('F', 5, 0), ('B', 5, 0)]
        second = [('F', 4, 0), ('F', 2, 0), ('F', 0, 0)]
        polygon = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
        outside = lambda layer, a, b: outside_polygon(a, b, polygon)
        self.assertAlmostEqual(shared_length(first, second, outside), 3)
        self.assertEqual(shared_length(first, [('I', 0, 0), ('I', 5, 0)], outside), 0)


class ContractTests(unittest.TestCase):
    def test_profile_configuration(self):
        profiles = {'8': {}, '8l': {}, '40': {'rtd_adc': 'U1001'}, '24': {}}
        apply(profiles)
        self.assertEqual(len(profiles['40']['route_pairs']), 4)
        self.assertEqual(profiles['40']['route_stars'][2][0], 'J1001.4')
        self.assertFalse(profiles['8']['route_pairs'])

    def test_help_needs_no_kicad(self):
        here = Path(__file__).resolve().parent
        for name in ('holes', 'route_report', 'pourcheck'):
            result = subprocess.run([sys.executable, '-B', str(here / (name+'.py')), '--board', '8', '--help'],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('usage:', result.stdout)

    def test_modules_small_and_never_save(self):
        here = Path(__file__).resolve().parent
        for name in ('audit_common', 'holes', 'route_graph', 'route_native', 'route_report', 'pourcheck', 'profiles_checks'):
            text = (here / (name+'.py')).read_text()
            self.assertLess(len(text.splitlines()), 300)
            self.assertNotIn('SaveBoard(', text)
            self.assertNotIn('SaveAs(', text)


if __name__ == '__main__':
    unittest.main()
