"""Native tests of dangling plans; never write a board."""
import unittest
import os
from pathlib import Path
import subprocess
import sys
import uuid
try:
    import pcbnew as p
except ImportError:
    p = None


@unittest.skipUnless(p, 'requires KiCad Python')
class PlanTests(unittest.TestCase):
    def test_native_guard_recognises_its_live_parent(self):
        import guard
        folder = Path(__file__).resolve().parents[2] / '8ch-new/output/coord/guard-native' / uuid.uuid4().hex
        folder.mkdir(parents=True)
        board = folder / 'copy.txt'
        board.write_text('copy-only fixture')
        key = 'THERMO' + guard.P['key'] + '_WRITER_CLAIM'
        previous = os.environ.get(key)
        os.environ[key] = str(folder / '.writer.json')
        try:
            with guard.claim(str(board), 'test'):
                code = 'import guard,sys; guard.check_parent(sys.argv[1],"test")'
                r = subprocess.run([sys.executable, '-B', '-c', code, str(board)], capture_output=True)
                self.assertEqual(r.returncode, 0, r.stderr.decode(errors='replace'))
        finally:
            if previous is None:
                os.environ.pop(key)
            else:
                os.environ[key] = previous
            board.unlink()
            folder.rmdir()

    def test_reported_via_that_bridges_offset_same_layer_tracks_gets_a_copper_replacement(self):
        from dangling_trim import plan
        b = p.BOARD(); net = p.NETINFO_ITEM(b, 'TEST'); b.Add(net)
        for a, z in (((0, 0), (1, 0)), ((0, .25), (0, 1))):
            t = p.PCB_TRACK(b); t.SetNet(net); t.SetLayer(p.F_Cu); t.SetWidth(p.FromMM(.2))
            t.SetStart(p.VECTOR2I(*[p.FromMM(x) for x in a]))
            t.SetEnd(p.VECTOR2I(*[p.FromMM(x) for x in z])); b.Add(t)
        v = p.PCB_VIA(b); v.SetNet(net); v.SetPosition(p.VECTOR2I(0, 0))
        v.SetWidth(p.FromMM(.6)); v.SetDrill(p.FromMM(.3)); b.Add(v)
        uid = v.m_Uuid.AsString()
        lines, _ = plan(b, dict(violations=[dict(type='via_dangling', items=[dict(uuid=uid)])]))
        self.assertTrue(any(line.startswith('add TEST F.Cu ') for line in lines))

    def test_redundant_connected_fragment_is_proposed_for_proof_not_left_dangling(self):
        from dangling_trim import plan
        b = p.BOARD()
        net = p.NETINFO_ITEM(b, 'TEST'); b.Add(net)
        tracks = []
        for a, z in (((0, 0), (10, 0)), ((4, 0), (5, 0))):
            t = p.PCB_TRACK(b); t.SetNet(net); t.SetLayer(p.F_Cu); t.SetWidth(p.FromMM(.2))
            t.SetStart(p.VECTOR2I(*[p.FromMM(x) for x in a]))
            t.SetEnd(p.VECTOR2I(*[p.FromMM(x) for x in z])); b.Add(t); tracks.append(t)
        uid = tracks[1].m_Uuid.AsString()
        report = dict(violations=[dict(type='track_dangling',items=[dict(uuid=uid)])])
        lines, _ = plan(b, report)
        self.assertEqual(lines, ['rip '+uid])


if __name__ == '__main__':
    unittest.main()
