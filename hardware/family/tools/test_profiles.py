"""Plain Python checks: no KiCad executable and no import of pcbnew, even indirectly."""
import ast
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


@contextlib.contextmanager
def scratch_folder():
    # Windows sandbox rejects Python 3.11 TemporaryDirectory's private ACL.
    folder = HERE.parent / 'tools-test' / ('guard-test-' + uuid.uuid4().hex)
    folder.mkdir()
    try:
        yield folder
    finally:
        shutil.rmtree(folder)


def pure_defs(path, names, namespace=None):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    space = namespace or {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), space)
    return space


class ProfilesTests(unittest.TestCase):
    def probe(self, args=(), environ=None):
        settings = {k: v for k, v in os.environ.items() if not k.startswith('THERMO')}
        settings.update(environ or {})
        settings['PYTHONDONTWRITEBYTECODE'] = '1'
        code = ('import sys,json; sys.path.insert(0,sys.argv.pop(1)); import profiles; '
                'p=profiles.ACTIVE; print(json.dumps({k:p[k] for k in '
                '("key","project","adc_refs","width","height","pcb","output","netlist","rtd_adc")},default=str)); '
                'print(json.dumps(sys.argv[1:])); assert "pcbnew" not in sys.modules')
        return subprocess.run([sys.executable, '-B', '-c', code, str(HERE), *args],
                              env=settings, capture_output=True, text=True)

    def test_selection_and_unknown_geometry(self):
        for key, project, refs in (('24', 'thermo24', 3), ('8', 'thermo8', 1), ('40', 'thermo40', 5)):
            r = self.probe(('--board', key, 'lock'))
            self.assertEqual(r.returncode, 0, r.stderr)
            p = json.loads(r.stdout.splitlines()[0])
            self.assertEqual(p['project'], project)
            self.assertEqual(len(p['adc_refs']), refs)
            self.assertEqual(json.loads(r.stdout.splitlines()[1]), ['lock'])
            if key == '40':
                self.assertEqual((p['width'], p['height']), (250.0, 145.0))
                self.assertEqual(p['rtd_adc'], 'U1001')
                self.assertEqual(p['adc_refs'], ['U101', 'U201', 'U301', 'U801', 'U901'])
            elif key == '8':
                self.assertEqual((p['width'], p['height']), (130.0, 137.0))
                self.assertIsNone(p['rtd_adc'])

    def test_confirmed_profiles(self):
        sys.path.insert(0, str(HERE))
        import profiles
        p8, p40 = profiles.PROFILES['8'], profiles.PROFILES['40']
        self.assertEqual(p40['bank_ref_bases'], (100, 200, 300, 800, 900))
        self.assertEqual((p40['decoder_ref'], p40['sio_driver_ref']), ('U410', 'U411'))
        self.assertEqual((p8['revision'], p8['bank_channels'], p8['buck_ref']), ('REV B0', (8,), 'U601'))
        self.assertEqual(p8['mounting_holes'], {'H5': (4.5, 4.5), 'H4': (126, 40), 'H6': (4.5, 29.5),
            'H7': (97.5, 29.5), 'H8': (4.5, 84.5), 'H9': (97.5, 84.5), 'H1': (4.5, 132.5),
            'H3': (125.5, 132.5), 'H2': (4.5, 100), 'H10': (90, 113)})
        self.assertEqual(p8['mounting_hole_types']['H4'], 'plain NPTH (0039 P9)')
        self.assertEqual(p8['mounting_hole_types']['H1'], 'island NPTH')
        self.assertEqual(p8['silk']['horizontal'], ('J101', 'J102'))
        self.assertEqual(p8['assembly'] is None, p8['assembly_html'] is None)
        if p8['assembly'] is not None:  # also valid after the owner's docs_new registration
            self.assertEqual(set(p8['assembly']), {'TESTS', 'REF_TP', 'ORIENT', 'LABEL_AT'})
            self.assertTrue(callable(p8['assembly_html']))
            self.assertTrue(callable(p8['order_notes']))
        self.assertEqual(p8['plane_nets'], profiles.PROFILES['24']['plane_nets'])
        self.assertEqual(len(p8['pin_checks']), 4 + 4 + 4 + 5)

    def test_environment_and_copy_precedence(self):
        r = self.probe(('--board=8', '--pcb', str(HERE.parent / 'tools-test' / 'copy.kicad_pcb'), 'via', 'C1', '2'),
                       {'THERMO_BOARD': '40', 'THERMO8_BOARD': 'unused.kicad_pcb'})
        self.assertEqual(r.returncode, 0, r.stderr)
        p = json.loads(r.stdout.splitlines()[0])
        self.assertEqual(p['key'], '8')
        self.assertTrue(p['pcb'].endswith('copy.kicad_pcb'))
        self.assertTrue(p['netlist'].endswith('copy.xml'))
        self.assertEqual(Path(p['output']).parent, Path(p['pcb']).parent)
        self.assertEqual(json.loads(r.stdout.splitlines()[1]), ['via', 'C1', '2'])
        r = self.probe(environ={'THERMO_BOARD': '24', 'THERMO24_BOARD': 'legacy.kicad_pcb'})
        self.assertEqual(r.returncode, 0)
        self.assertTrue(json.loads(r.stdout.splitlines()[0])['pcb'].endswith('legacy.kicad_pcb'))
        self.assertNotEqual(self.probe(('--board', '36')).returncode, 0)
        self.assertNotEqual(self.probe(('--pcb',)).returncode, 0)

    def test_syntax_and_size(self):
        for p in HERE.glob('*.py'):
            text = p.read_text(encoding='utf-8')
            ast.parse(text)
            self.assertLessEqual(len(text.splitlines()), 300, p.name)
            self.assertFalse(any(ord(c) < 32 and c not in '\n\t\r' for c in text), p.name)

    def test_geometry_pure_functions(self):
        import math
        names = ('_pt_seg', '_cross', '_seg_seg', 'seg_rect_dist', 'overlap')
        original = pure_defs(ROOT / 'hardware/24ch/gen/capnear.py', names, {'math': math})
        family = pure_defs(HERE / 'capnear_ops.py', names, {'math': math})
        for box in ((0, 0, 2, 2), (4, 1, 8, 3)):
            for seg in ((-1, 1, 3, 1), (0, 5, 5, 5), (1, 1, 1, 1)):
                self.assertEqual(original['seg_rect_dist'](*seg, box), family['seg_rect_dist'](*seg, box))
        self.assertEqual(family['_seg_seg'](0, 0, 2, 2, 0, 2, 2, 0), 0)

    def test_profile24_source_constants(self):
        sys.path.insert(0, str(HERE))
        import profiles
        p = profiles.PROFILES['24']
        donor = ROOT / 'hardware/24ch/gen'
        constants = {}
        for name in ('pcb_new', 'pincaps', 'fanout', 'fiducials', 'maze'):
            for n in ast.parse((donor / (name + '.py')).read_text(encoding='utf-8')).body:
                if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name):
                    try:
                        constants[name, n.targets[0].id] = ast.literal_eval(n.value)
                    except (ValueError, TypeError):
                        pass
        self.assertEqual(constants['fiducials', 'TARGETS'], p['fiducials'])
        self.assertEqual(constants['fanout', 'PLANE_NETS'], p['plane_nets'])
        self.assertEqual(constants['maze', 'PLANE'], p['plane_domains'])
        self.assertEqual(constants['maze', 'CONTACT'], p['contact_nets'])
        self.assertEqual(constants['maze', 'KEEP_PREFIX'], p['keep_prefix'])
        self.assertEqual((p['width'], p['height']), (170.0, 145.0))
        # Evaluate the donor list comprehension alone with no imports/pcbnew.
        check = next(n.value for n in ast.parse((donor / 'pincaps.py').read_text(encoding='utf-8')).body
                     if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'CHECK')
        self.assertEqual(eval(compile(ast.Expression(check), 'CHECK', 'eval')), p['pin_checks'])
        self.assertNotIn('pcbnew', sys.modules)

    def test_guard_refusals(self):
        sys.path.insert(0, str(HERE))
        import guard
        with scratch_folder() as folder:
            b = Path(folder) / 'copy.txt'  # guard is path-based; no KiCad file needs writing
            b.write_bytes(b'test fixture')
            lock = Path(folder) / '~copy.txt.lck'
            lock.write_text('owner holds unsaved work')
            with self.assertRaises(SystemExit):
                guard.check(str(b))
            self.assertTrue(lock.exists())
            lock.unlink()
            with self.assertRaises(SystemExit):
                with guard.claim(str(ROOT / 'hardware/24ch/thermo24.kicad_pcb'), 'test'):
                    self.fail('source write allowed')
            claim = Path(folder) / 'claim.json'
            old = os.environ.get('THERMO24_WRITER_CLAIM')
            os.environ['THERMO24_WRITER_CLAIM'] = str(claim)
            try:
                with guard.claim(str(b), 'test'):
                    self.assertTrue(claim.exists())
                    self.assertEqual(json.loads(claim.read_text())['pid'], os.getpid())
                    code = 'import sys; sys.path.insert(0,sys.argv[1]); import guard; guard.check_parent(sys.argv[2],"test")'
                    # Windows venv launchers add a parent hop; use the actual base interpreter.
                    installed = Path(r'C:\Users\malgh\AppData\Local\Programs\Python\Python310\python.exe')
                    child_python = str(installed) if installed.is_file() else getattr(sys, '_base_executable', sys.executable)
                    child = subprocess.run([child_python, '-B', '-c', code, str(HERE), str(b)], capture_output=True, text=True)
                    self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
                    lock.write_text('KiCad opened during claim')
                    child = subprocess.run([child_python, '-B', '-c', code, str(HERE), str(b)], capture_output=True, text=True)
                    self.assertNotEqual(child.returncode, 0)
                    self.assertTrue(lock.exists())
                    lock.unlink()
                self.assertFalse(claim.exists())
            finally:
                if old is None:
                    os.environ.pop('THERMO24_WRITER_CLAIM')
                else:
                    os.environ['THERMO24_WRITER_CLAIM'] = old

    def test_same_failure_is_narrow(self):
        from regress import same_failure
        self.assertTrue(same_failure((1, 1), ('', ''), ('same', 'same')))
        for exits, stdout, hashes in (((1, 0), ('', ''), ('same', 'same')),
                 ((-1, -1), ('', ''), ('same', 'same')), ((1, 1), ('a', 'b'), ('same', 'same')),
                 ((1, 1), ('', ''), ('a', 'b')), ((3221225477, 3221225477), ('', ''), ('same', 'same'))):
            self.assertFalse(same_failure(exits, stdout, hashes))

    def test_metadata_normalisation_is_narrow(self):
        from regress_compare import normal_text
        a = 'G04 Created by KiCad (PCBNEW 10.0.6) date 2026-10-14 11:17:07*\r\nX123Y456D01*\r\n'
        b = a.replace('11:17:07', '11:18:45')
        self.assertEqual(normal_text(a), normal_text(b))
        self.assertNotEqual(normal_text(a), normal_text(b.replace('X123', 'X124')))
        self.assertNotEqual(normal_text(a), normal_text(b.replace('10.0.6', '10.0.7')))
        a = '; DRILL file KiCad 10.0.6 date 2026-10-14T11:17:11\r\nT1C0.300\r\n'
        self.assertEqual(normal_text(a), normal_text(a.replace('11:17:11', '11:18:49')))
        self.assertNotEqual(normal_text(a), normal_text(a.replace('C0.300', 'C0.400')))

    def test_dangling_algorithm_unchanged(self):
        def function(path):
            return next(n for n in ast.parse(path.read_text(encoding='utf-8')).body
                        if isinstance(n, ast.FunctionDef) and n.name == 'dangling')
        donor = function(ROOT / 'hardware/24ch/gen/finish.py')
        family = function(HERE / 'finish_ops.py')
        self.assertEqual(ast.dump(donor, include_attributes=False), ast.dump(family, include_attributes=False))

    def test_pcb_comparator_detects_geometry(self):
        from regress_compare import canonical_pcb
        a = '(kicad_pcb (segment (start 0 0) (end 1 1) (uuid "a")))'
        b = '(kicad_pcb (segment (start 0 0) (end 1 1) (uuid "b")))'
        self.assertEqual(canonical_pcb(a), canonical_pcb(b))
        self.assertNotEqual(canonical_pcb(a), canonical_pcb(b.replace('end 1 1', 'end 1 2')))


if __name__ == '__main__':
    (HERE.parent / 'tools-test').mkdir(exist_ok=True)
    unittest.main(argv=[sys.argv[0]], verbosity=2)
