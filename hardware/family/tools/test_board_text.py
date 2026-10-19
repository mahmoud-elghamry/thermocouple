"""Stdlib-only reader, geometry and rule regression tests; no KiCad required."""
import json
import math
import unittest

from board_text import Board
from text_check import check
from text_geom import Shape, gap, arc_points, rect
from text_sexp import parse


PROJECT = {'board': {'design_settings': {'rules': {'min_clearance': .15, 'min_hole_to_hole': .25}}},
           'net_settings': {'classes': [{'name': 'Default', 'clearance': .25, 'priority': 100},
                                       {'name': 'Power', 'clearance': .5, 'priority': 1}],
                            'netclass_patterns': [{'pattern': 'P*', 'netclass': 'Power'}]}}


def board(body='', rules=''):
    return Board.from_text('(kicad_pcb (layers (0 "F.Cu" signal) (2 "B.Cu" signal)) '
                           '(net 0 "") (net 1 "A") (net 2 "POWER") '+body+')', PROJECT, rules)


def via(uid, x, net=1):
    return f'(via (at {x} 0) (size .6) (drill .3) (layers "F.Cu" "B.Cu") (net {net}) (uuid {uid}))'


class ReaderTests(unittest.TestCase):
    def test_parser_comments_escaped_strings_and_errors(self):
        self.assertEqual(parse('(a "x#y" # comment\n (b "q\\\"z"))'), [['a', 'x#y', ['b', 'q"z']]])
        for text in ('(a', 'a)', ')(', '(a "unterminated)', '(a "unterminated'):
            with self.assertRaises(ValueError):
                parse(text)

    def test_rotated_pad_absolute_angle_and_radius(self):
        b = board('''(footprint "X" (layer "F.Cu") (at 10 20 90) (property "Reference" "X1")
          (pad "1" smd roundrect (at 2 0 30) (size 2 1) (roundrect_rratio .25)
            (layers "F.Cu") (net 1) (uuid p)))''')
        pad = b.items[0]
        self.assertAlmostEqual(pad.centre[0], 10)
        self.assertAlmostEqual(pad.centre[1], 18)
        self.assertEqual(pad.angle, 30)  # Already absolute; do not add footprint rotation.
        self.assertEqual(pad.shapes[0].radius, .25)

    def test_oval_slot_offset_and_npth(self):
        b = board('''(footprint "X" (at 0 0) (property "Reference" "X1")
          (pad "1" thru_hole oval (at 0 0 90) (size 3 2) (drill oval 2 1 (offset .5 0))
            (layers "*.Cu") (net 1) (uuid p))
          (pad "" np_thru_hole circle (at 5 0) (size 3 3) (drill 3)
            (layers "*.Cu") (uuid hole)))''')
        pad = next(i for i in b.items if i.uid == 'p')
        self.assertAlmostEqual(pad.centre[1], -.5)
        self.assertAlmostEqual(b.holes[0].centre[1], 0)
        self.assertEqual(b.holes[0].shapes[0].radius, .5)
        self.assertEqual(len(b.holes), 2)
        self.assertFalse(any(i.uid == 'hole' for i in b.items))

    def test_custom_pad_primitives_and_copper_arc(self):
        b = board('''(footprint "X" (at 0 0) (property "Reference" "X1")
          (pad "1" smd custom (at 0 0) (size .2 .2) (layers "F.Cu") (net 1) (uuid p)
            (options (anchor circle)) (primitives
              (gr_line (start 0 0) (end 2 0) (width .2))
              (gr_poly (pts (xy 0 0) (xy 0 1) (xy 1 1)) (width 0) (fill yes)))))
          (arc (start 0 0) (mid 1 1) (end 2 0) (width .2) (layer "F.Cu") (net 2) (uuid arc))''')
        self.assertGreaterEqual(len(b.items[0].shapes), 3)
        arc = next(i for i in b.items if i.uid == 'arc')
        self.assertGreater(len(arc.shapes), 2)
        self.assertIn('arc', arc.extra)

    def test_zone_keepout_and_layer_span(self):
        b = board('''(zone (net 1) (layer "F.Cu") (uuid z)
            (polygon (pts (xy 0 0) (xy 2 0) (xy 2 2))))
          (zone (layers "F&B.Cu") (uuid k) (keepout (tracks not_allowed) (vias allowed))
            (polygon (pts (xy 0 0) (xy 2 0) (xy 2 2))))''')
        self.assertEqual((len(b.zones), len(b.keepouts)), (1, 1))
        self.assertTrue(b.keepouts[0].extra['tracks'])
        self.assertFalse(b.keepouts[0].extra['vias'])
        self.assertEqual(set(b.keepouts[0].layers), {'F.Cu', 'B.Cu'})

    def test_unsupported_copper_and_bad_rules_fail_explicitly(self):
        with self.assertRaisesRegex(ValueError, 'pad shape'):
            board('''(footprint "X" (at 0 0) (pad "1" smd nonsense (at 0 0) (size 1 1)
                         (layers "F.Cu") (net 1) (uuid p)))''')
        with self.assertRaises(ValueError):
            board(rules='(rule "bad" (condition "A.Mystery == \'x\'") (constraint clearance (min .2mm)))')
        with self.assertRaisesRegex(ValueError, 'copper graphic'):
            board('(gr_line (start 0 0) (end 2 2) (width .2) (layer "F.Cu"))')
        with self.assertRaisesRegex(ValueError, 'copper graphic'):
            board('''(footprint "X" (at 0 0)
                (fp_line (start 0 0) (end 2 2) (width .2) (layer "B.Cu")))''')
        with self.assertRaisesRegex(ValueError, 'copper graphic'):
            board('''(footprint "X" (at 0 0) (property "Value" "conductive text" (layer "F.Cu")))''')
        with self.assertRaisesRegex(ValueError, 'footprint-local zone'):
            board('''(footprint "X" (at 0 0) (zone (layer "F.Cu")
               (keepout (tracks not_allowed)) (polygon (pts (xy 0 0) (xy 2 0) (xy 2 2)))))''')


class GeometryTests(unittest.TestCase):
    def test_roundrect_native_drc_epsilon_boundary(self):
        pad = rect((40.015,115.7), (1,1.45), 90, .25)
        track = Shape(((38.9497,115.2595),(40.0408,114.187)), .1)
        self.assertLess(gap(pad,track),.2)
        self.assertGreater(gap(pad,track),.2-.0005)

    def test_capsules_and_roundrect_true_corners(self):
        a = Shape(((0, 0), (2, 0)), .5)
        b = Shape(((1, 2),), .5)
        self.assertAlmostEqual(gap(a, b), 1)
        corner = Shape(((.7, .7),), 0)
        rounded = Shape(((-.5, -.5), (.5, -.5), (.5, .5), (-.5, .5)), .5, True)
        self.assertAlmostEqual(gap(corner, rounded), math.hypot(.2, .2)-.5)

    def test_arc_tessellation_preserves_endpoints_and_sweep(self):
        pts = arc_points((0, 0), (1, 1), (2, 0), .001)
        self.assertEqual(pts[0], (0, 0))
        self.assertEqual(pts[-1], (2, 0))
        self.assertGreater(max(p[1] for p in pts), .999)
        self.assertLess(min(p[1] for p in pts), .001)


class RuleAndCheckerTests(unittest.TestCase):
    def test_keepout_overlap_tangency_and_allowed_via(self):
        area = '''(zone (layer "F.Cu") (uuid k) (keepout (tracks not_allowed) (vias allowed))
                    (polygon (pts (xy -1 -1) (xy 1 -1) (xy 1 1) (xy -1 1))))'''
        def segment(y):
            return f'(segment (start -2 {y}) (end 2 {y}) (width .2) (layer "F.Cu") (net 1) (uuid t))'
        self.assertEqual(check(board(area+segment(1.1)))['keepout_violations'],0)
        self.assertEqual(check(board(area+segment(1.099)))['keepout_violations'],1)
        self.assertEqual(check(board(area+segment(1.2)+via('v',0)))['keepout_violations'],0)

    def test_arc_error_can_conservatively_flag_near_threshold(self):
        b = board('''(arc (start -1 0) (mid 0 1) (end 1 0) (width .2) (layer "F.Cu") (net 1) (uuid a))
          (segment (start -2 1.3503) (end 2 1.3503) (width .1) (layer "F.Cu") (net 2) (uuid b))''',
          '(rule "all" (constraint clearance (min .2mm)))')
        self.assertAlmostEqual(1.3503-.05-1-.1,.2003)  # Ideal gap is above .2.
        self.assertEqual(check(b)['clearance_violations'],1)  # Inflated chords are conservative.
        self.assertTrue(any('arc' in note.lower() for note in b.approximations))

    def test_drc_epsilon_is_reported_and_strict_mode_available(self):
        b = board('''(segment (start 0 0) (end 2 0) (width .2) (layer "F.Cu") (net 1) (uuid a))
          (segment (start 0 .6997) (end 2 .6997) (width .2) (layer "F.Cu") (net 2) (uuid b))''')
        result = check(b)
        self.assertEqual(result['clearance_violations'],0)
        self.assertEqual(len(result['clearance_boundary_cases']),1)
        self.assertEqual(check(b, clearance_epsilon=0)['clearance_violations'],1)

    def test_class_priority_nori_rule_and_reverse_order(self):
        rule = '''(rule "nori" (condition "A.Type == 'Pad' && B.Type == 'Track'")
                       (constraint clearance (min .2mm)))'''
        b = board('''(footprint "X" (at 0 0) (property "Reference" "X1")
                 (pad "1" smd rect (at 0 0) (size 1 1) (layers "F.Cu") (net 2) (uuid p)))
              (segment (start 0 1) (end 2 1) (width .2) (layer "F.Cu") (net 1) (uuid t))''', rule)
        a, t = b.items
        self.assertEqual(b.rules.netclass('POWER'), 'Power')
        self.assertEqual(b.rules.netclass(''), '')
        self.assertEqual(b.rules.clearance(a, t), (.2, 'nori'))
        self.assertEqual(b.rules.clearance(t, a), (.2, 'nori'))
        self.assertFalse(check(b)['clearance_violations'])

    def test_rule_area_membership_and_last_match(self):
        rules = '''(rule "area" (condition "A.intersectsCourtyard('X1') && B.intersectsCourtyard('X1')")
                    (constraint clearance (min .4mm)))
          (rule "own" (condition "A.memberOfFootprint('X1') && B.memberOfFootprint('X1')")
                    (constraint clearance (min .2mm)))'''
        b = board('''(footprint "X" (at 0 0) (property "Reference" "X1")
              (fp_rect (start -2 -2) (end 2 2) (layer "F.CrtYd"))
              (pad "1" smd rect (at 0 0) (size 1 1) (layers "F.Cu") (net 1) (uuid a))
              (pad "2" smd rect (at 1.2 0) (size 1 1) (layers "F.Cu") (net 2) (uuid b)))''', rules)
        self.assertEqual(b.rules.clearance(*b.items), (.2, 'own'))
        self.assertFalse(check(b)['clearance_violations'])

    def test_detects_clearance_and_same_net_hole_and_land(self):
        b = board(via('v1', 0)+via('v2', .1)+via('v3', .65, 2)+'''
          (footprint "X" (at 0 0) (property "Reference" "X1")
              (pad "1" smd rect (at 0 0) (size 1 1) (layers "F.Cu") (net 1) (uuid p)))''')
        result = check(b)
        self.assertTrue(result['clearance_violations'])
        self.assertTrue(result['hole_pairs'])
        self.assertTrue(result['via_land_pairs'])
        json.dumps(result, allow_nan=False)

    def test_heatsink_exemption_and_nominal_spacing(self):
        b = board(via('v1', 0)+via('v2', .55)+'''
          (footprint "X" (at 0 0) (property "Reference" "X1")
              (pad "1" smd rect (at 0 0) (size 1 1) (property pad_prop_heatsink)
                   (layers "F.Cu") (net 1) (uuid p)))''')
        self.assertEqual(check(b)['hole_pairs'], 0)
        self.assertEqual(check(b)['via_land_pairs'], 0)
        self.assertGreater(check(b, include_heatsinks=True)['via_land_pairs'], 0)


if __name__ == '__main__':
    unittest.main()
