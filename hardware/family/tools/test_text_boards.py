"""Real-board regressions and no-site-packages CLI proofs; no KiCad dependency."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

from board_text import Board
from text_check import check

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


class BoardProofs(unittest.TestCase):
    def test_current_boards_are_clear_without_kicad(self):
        for folder, stem in (('40ch','thermo40'),('8ch-new','thermo8'),('8ch-2l','thermo8')):
            with self.subTest(board=folder):
                path = ROOT/'hardware'/folder/(stem+'.kicad_pcb')
                hashes = {p:hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in (path,path.with_suffix('.kicad_pro'),path.with_suffix('.kicad_dru'))}
                b = Board(path)
                result = check(b)
                numbers = tuple(result[k] for k in ('clearance_violations','keepout_violations','hole_pairs','via_land_pairs'))
                print(folder, numbers, 'boundary cases',len(result['clearance_boundary_cases']))
                self.assertEqual(numbers,(0,0,0,0))
                self.assertEqual(len(result['clearance_boundary_cases']),int(folder=='40ch'))
                for p,digest in hashes.items():
                    self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),digest)

    def test_pre_r10_same_hole_uuid_pairs_as_kicad(self):
        path = ROOT/'hardware/40ch/output/pre-r10/thermo40.kicad_pcb'
        report = path.parent/'drc.json'
        if not path.is_file() or not report.is_file():
            self.skipTest('pre-r10 board + saved KiCad DRC fixture not available')
        native = json.loads(report.read_text(encoding='utf-8-sig'))
        expected = {frozenset(item['uuid'] for item in row['items']) for row in native['violations']
                    if row['type'] in ('hole_to_hole','holes_co_located')}
        result = check(Board(path))
        actual = {frozenset((row['a']['uuid'],row['b']['uuid'])) for row in result['hole_details']}
        self.assertEqual(len(expected),25)
        self.assertEqual(actual,expected)
        self.assertEqual(result['hole_pairs'],25)
        self.assertEqual(result['via_land_pairs'],34)
        print('pre-r10:',len(actual),'identical KiCad hole pairs; lands',result['via_land_pairs'])

    def test_cli_without_site_packages_or_native_imports(self):
        # -S strips site-packages. The hook also catches attempted native imports
        # even if someone catches ImportError and tries a silent fallback.
        script = '''import builtins, runpy, sys
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in ('pcbnew','wx','numpy','shapely','kiutils'):
        raise AssertionError('non-stdlib dependency attempted: '+name)
    return original(name,*args,**kwargs)
builtins.__import__ = guarded
sys.path.insert(0,sys.argv[1])
sys.argv = [sys.argv[1]+'/text_check.py','--board','8']
runpy.run_path(sys.argv[0],run_name='__main__')
'''
        result = subprocess.run([sys.executable,'-S','-c',script,str(HERE)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['clearance_violations'],0)
        self.assertEqual(report['hole_pairs'],0)

    def test_stdlib_import_chain_and_module_size(self):
        seen = set()
        def visit(name):
            if name in seen:
                return
            seen.add(name)
            path = HERE/(name+'.py')
            if not path.exists():
                self.assertIn(name,sys.stdlib_module_names)
                return
            text = path.read_text(encoding='utf-8')
            tree = ast.parse(text)
            if name.startswith('text_') or name=='board_text':
                self.assertLess(len(text.splitlines()),300,name)
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):
                    for alias in node.names:
                        visit(alias.name.split('.')[0])
                elif isinstance(node,ast.ImportFrom) and node.module:
                    visit(node.module.split('.')[0])
                elif (isinstance(node,ast.Call) and isinstance(node.func,ast.Name)
                      and node.func.id=='__import__' and node.args and isinstance(node.args[0],ast.Constant)):
                    visit(node.args[0].value.split('.')[0])
        visit('text_check')
        visit('board_text')


if __name__ == '__main__':
    unittest.main()
