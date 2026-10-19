"""KiCad-only synthetic tests; optional real-board proofs via ROUTING_BOARD_PROOFS=1.

Use KiCad's Python: python -m unittest -v test_routing_kicad. Plain Python skips
this module's tests when pcbnew is unavailable. No test saves a board.
"""
import ast
import json
import os
from pathlib import Path
import unittest

try:
    import pcbnew as p
except ImportError:
    p = None

from holes import audit as holes
from pourcheck import audit as pours
from route_native import BoardRoutes

ROOT = Path(__file__).resolve().parents[3]


@unittest.skipUnless(p, 'requires KiCad Python / pcbnew')
class NativeTests(unittest.TestCase):
    def setUp(self):
        self.board = p.BOARD()
        self.net = p.NETINFO_ITEM(self.board, 'TEST')
        self.board.Add(self.net)

    def via(self, x=0, y=0):
        v = p.PCB_VIA(self.board)
        v.SetPosition(p.VECTOR2I(p.FromMM(x), p.FromMM(y)))
        v.SetWidth(p.FromMM(.6))
        v.SetDrill(p.FromMM(.3))
        v.SetLayerPair(p.F_Cu, p.B_Cu)
        v.SetNet(self.net)
        self.board.Add(v)
        return v

    def pad(self, x=0, y=0, heatsink=False):
        f = p.FOOTPRINT(self.board)
        f.SetReference('X'+str(len(list(self.board.GetFootprints()))+1))
        self.board.Add(f)
        a = p.PAD(f)
        a.SetNumber('1')
        a.SetAttribute(p.PAD_ATTRIB_SMD)
        a.SetShape(p.PAD_SHAPE_RECT)
        ls = p.LSET()
        ls.AddLayer(p.F_Cu)
        a.SetLayerSet(ls)
        a.SetSize(p.VECTOR2I(p.FromMM(1), p.FromMM(1)))
        a.SetPosition(p.VECTOR2I(p.FromMM(x), p.FromMM(y)))
        a.SetNet(self.net)
        if heatsink:
            a.SetProperty(p.PAD_PROP_HEATSINK)
        f.Add(a)
        return a

    def test_same_net_duplicate_holes_count(self):
        self.via()
        self.via()
        result = holes(self.board)
        self.assertEqual((result['hole_pairs'], result['co_located_pairs']), (1, 1))

    def test_nominal_hole_equality_and_one_micron_violation(self):
        self.via()
        other = self.via(.55)
        self.assertEqual(holes(self.board)['hole_pairs'], 0)
        other.SetPosition(p.VECTOR2I(p.FromMM(.549), 0))
        self.assertEqual(holes(self.board)['hole_pairs'], 1)

    def test_same_net_land_intrusion_and_heatsink_policy(self):
        self.via()
        a = self.pad(.7)
        result = holes(self.board)
        self.assertEqual(result['via_land_pairs'], 1)
        self.assertAlmostEqual(result['land_details'][0]['edge_gap_mm'], .05, places=5)
        a.SetProperty(p.PAD_PROP_HEATSINK)
        self.assertEqual(holes(self.board)['via_land_pairs'], 0)
        self.assertEqual(holes(self.board, include_heatsinks=True)['via_land_pairs'], 1)

    def test_roundrect_hole_gap_uses_copper_not_core(self):
        self.via(.6,.6)
        a = self.pad()
        a.SetShape(p.PAD_SHAPE_ROUNDRECT)
        a.SetRoundRectRadiusRatio(.25)
        self.assertEqual(holes(self.board)['via_land_pairs'],1)

    def test_slot_and_offset_use_native_hole(self):
        a = self.pad(2, 0)
        a.SetAttribute(p.PAD_ATTRIB_PTH)
        a.SetLayerSet(p.LSET.AllCuMask())
        a.SetDrillShape(p.PAD_DRILL_SHAPE_OBLONG)
        a.SetDrillSize(p.VECTOR2I(p.FromMM(2), p.FromMM(1)))
        a.SetOffset(p.VECTOR2I(p.FromMM(.5), 0))
        a.SetOrientationDegrees(90)
        self.via(2, 1.3)
        self.assertEqual(holes(self.board)['hole_pairs'], 1)

    def test_centre_inside_land_saturates(self):
        self.via()
        self.pad()
        result = holes(self.board)
        self.assertEqual(result['via_land_pairs'], 1)
        self.assertAlmostEqual(result['minimum_via_land_gap_mm'], -.15)

    def test_no_fill_fails(self):
        with self.assertRaisesRegex(ValueError, 'no copper zones'):
            pours(self.board)

    def test_pour_direct_indirect_and_unattached(self):
        zone = p.ZONE(self.board)
        zone.SetLayer(p.F_Cu)
        zone.SetNet(self.net)
        poly = p.SHAPE_POLY_SET()
        poly.NewOutline()
        for x, y in ((-2, -2), (2, -2), (2, 2), (-2, 2)):
            poly.Append(p.FromMM(x), p.FromMM(y))
        zone.Outline().Append(poly)
        self.board.Add(zone)
        self.pad()
        self.via(3, 0)
        self.pad(10, 0)
        track = p.PCB_TRACK(self.board)
        track.SetLayer(p.F_Cu)
        track.SetStart(p.VECTOR2I(0, 0))
        track.SetEnd(p.VECTOR2I(p.FromMM(3), 0))
        track.SetWidth(p.FromMM(.2))
        track.SetNet(self.net)
        self.board.Add(track)
        with self.assertRaisesRegex(ValueError, 'lack saved fill'):
            pours(self.board)
        zone.SetFilledPolysList(p.F_Cu, poly)
        zone.SetIsFilled(True)
        result = pours(self.board)
        self.assertEqual((result['directly_attached'], result['reachable_fill'], result['unattached']), (1, 2, 1))

    def test_arc_on_measured_net_refused(self):
        a = self.pad()
        b = self.pad(2, 0)
        arc = p.PCB_ARC(self.board)
        arc.SetNet(self.net)
        self.board.Add(arc)
        with self.assertRaisesRegex(ValueError, 'arcs/unknown'):
            BoardRoutes(self.board).path(a.GetParentFootprint().GetReference()+'.1',
                                         b.GetParentFootprint().GetReference()+'.1')

    def test_offset_pad_measured_from_copper_centre(self):
        self.pad().SetOffset(p.VECTOR2I(p.FromMM(1), 0))
        self.pad(3, 0)
        track = p.PCB_TRACK(self.board)
        track.SetLayer(p.F_Cu)
        track.SetStart(p.VECTOR2I(p.FromMM(1), 0))
        track.SetEnd(p.VECTOR2I(p.FromMM(3), 0))
        track.SetWidth(p.FromMM(.2))
        track.SetNet(self.net)
        self.board.Add(track)
        self.assertEqual(BoardRoutes(self.board).path('X1.1', 'X2.1')['length_mm'], 2)

    def test_cross_net_measurement_refused(self):
        a = self.pad()
        self.pad(1, 0).SetNetCode(0)
        with self.assertRaisesRegex(ValueError, 'share a nonempty net'):
            BoardRoutes(self.board).path(a.GetParentFootprint().GetReference()+'.1', 'X2.1')


@unittest.skipUnless(p and os.environ.get('ROUTING_BOARD_PROOFS') == '1',
                     'real fixtures: set ROUTING_BOARD_PROOFS=1 with KiCad Python')
class BoardProofs(unittest.TestCase):
    def test_current_boards_and_old_snapshot(self):
        cases = [('40ch/thermo40', (0, 0, 0)), ('8ch-new/thermo8', (0, 0, 0)),
                 ('8ch-2l/thermo8', (0, 0, 0)),
                 ('40ch/output/pre-r10/thermo40', (25, 11, 34))]
        for path, expected in cases:
            with self.subTest(board=path):
                result = holes(p.LoadBoard(str(ROOT/'hardware'/(path+'.kicad_pcb'))))
                observed = tuple(result[k] for k in ('hole_pairs', 'co_located_pairs', 'via_land_pairs'))
                print(path, observed)
                self.assertEqual(observed, expected)
                if 'pre-r10' in path:
                    report = ROOT/'hardware/40ch/output/toolkit-proof/pre-r10/drc.json'
                    native = json.loads(report.read_text(encoding='utf-8'))
                    native_pairs = {frozenset(i['uuid'] for i in v['items']) for v in native['violations']
                                    if v['type'] in ('hole_to_hole', 'holes_co_located')}
                    own_pairs = {frozenset((x['a']['uuid'], x['b']['uuid'])) for x in result['hole_details']}
                    self.assertEqual(own_pairs, native_pairs)

    def test_saved_pour_copies(self):
        for folder, stem, count in (('40ch', 'thermo40', 1212), ('8ch-new', 'thermo8', 502),
                                    ('8ch-2l', 'thermo8', 318)):
            with self.subTest(board=folder):
                path = ROOT/'hardware'/folder/'output/toolkit-proof'/(stem+'.kicad_pcb')
                if not path.is_file():
                    self.fail(f'create the refilled output/ proof copy first: {path}')
                result = pours(p.LoadBoard(str(path)))
                self.assertEqual(result['inspected_items'], count)
                self.assertEqual(result['unattached'], 0)
                print(folder, 'pour', result['directly_attached'], result['reachable_fill'], result['unattached'])

    def test_round11_final_pairs_and_shared_runs(self):
        from profiles_checks import apply
        from route_report import measure
        profiles = {'40': {'rtd_adc': 'U1001'}}
        apply(profiles)
        board = p.LoadBoard(str(ROOT/'hardware/40ch/thermo40.kicad_pcb'))
        result = measure(board, profiles['40'])
        # Parse only the literal JSON payload, never execute the scratch script.
        record = ROOT/'hardware/40ch/output/sol/r11_verification_data.py'
        tree = ast.parse(record.read_text(encoding='utf-8'))
        payload = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                       and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'PAYLOAD')
        expected = json.loads(payload)['after_quality']['sense']
        self.assertEqual(len(result['pairs']), len(expected))
        for pair, old in zip(result['pairs'], expected):
            for leg, old_leg in zip(pair['legs'], old['nets'].values()):
                reference = old_leg['resistor_to_adc']
                self.assertAlmostEqual(leg['length_mm'], reference['length_mm'], places=6)
                self.assertEqual(leg['vias'], reference['vias'])
            print(pair['name'], [(x['length_mm'], x['vias']) for x in pair['legs']])
        self.assertEqual(result['disconnected_paths'], 0)
        self.assertEqual(len(result['shared_runs']), 22)
        self.assertTrue(all(x['shared_outside_pad_mm'] == 0 for x in result['shared_runs']))


if __name__ == '__main__':
    unittest.main()
