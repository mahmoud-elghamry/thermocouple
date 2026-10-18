"""Release-text gates; plain Python, no KiCad imports or board-file writes."""
import ast
import copy
import csv
import importlib.util
import json
from pathlib import Path
import re
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GOLDEN = HERE.parent / 'tools-test' / 'original24.json'
REF = re.compile(r'\b(?:TP|JP|SW|RV|[CRDUJKQYLF])\d{2,4}\b')


def profile_defs():
    """Load the source data/functions without selection or profiles_new.apply."""
    path = HERE / 'profiles.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    tree.body = [n for n in tree.body if not (
        isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'ACTIVE' for t in n.targets))
        and not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                 and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == 'apply')]
    space = {'__file__': str(path)}
    exec(compile(tree, str(path), 'exec'), space)
    return space


def table(head, rows):
    return '<table><tr>' + ''.join(f'<th>{c}</th>' for c in head) + '</tr>' + ''.join(
        '<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows) + '</table>'


def strings(value):
    if isinstance(value, dict):
        return ' '.join(strings(k) + ' ' + strings(v) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return ' '.join(strings(v) for v in value)
    return value if isinstance(value, str) else ''


class DocsTests(unittest.TestCase):
    def test_original24_byte_identical(self):
        golden = json.loads(GOLDEN.read_text(encoding='utf-8'))
        p = profile_defs()['P24']
        for dnp, key in (('', 'html'), ('U703, J703', 'html_dnp')):
            self.assertEqual(p['assembly_html']('release-golden', dnp, golden['counts'], table).encode(),
                             golden[key].encode())
        self.assertEqual(p['order_notes'](None, 'release-golden', lambda _: '170 x 145 mm').encode(),
                         golden['notes'].encode())

    def build(self):
        self.assertIsNotNone(importlib.util.find_spec('docs_new'), 'missing new board release texts')
        import docs_new
        space = profile_defs()
        # Stand-ins intentionally exclude the concurrently edited profiles_new module.
        profiles = {k: space['Profile'](key=k, assembly=None, assembly_html=None, order_notes=None,
                    exposed_pad_text=None, release_prefix=None, width=None, height=None) for k in ('8', '40')}
        donor = space['P24']
        before = copy.deepcopy(donor)
        docs_new.apply(profiles, donor)
        self.assertEqual(donor, before)
        docs_new.apply(profiles, donor)  # registration is repeatable
        self.assertNotIn('pcbnew', sys.modules)
        return profiles, donor

    def test_board_counts_refs_and_required_keys(self):
        profiles, donor = self.build()
        required = {'assembly', 'assembly_html', 'order_notes', 'exposed_pad_text'}
        for name in ('fab.py', 'assembly_spec.py'):
            tree = ast.parse((HERE / name).read_text(encoding='utf-8'))
            required.update(n.args[0].value for n in ast.walk(tree) if isinstance(n, ast.Call)
                            and isinstance(n.func, ast.Attribute) and n.func.attr == 'require'
                            and isinstance(n.args[0], ast.Constant))
        for key, p in profiles.items():
            with self.subTest(board=key):
                for field in required:
                    self.assertIsNotNone(p.require(field), field)
                folder = ROOT / 'hardware' / ('8ch-new' if key == '8' else '40ch')
                with (folder / 'BOM.csv').open(encoding='utf-8-sig', newline='') as f:
                    rows = list(csv.DictReader(f))
                refs = {r.strip() for row in rows for r in row['Designator'].split(',')}
                pcb = (folder / ('thermo' + key + '.kicad_pcb')).read_text(encoding='utf-8')
                refs |= set(re.findall(r'"Reference" "(TP\d+)"', pcb))   # bare test pads: board only
                counts = dict(lines=len(rows), parts=sum(int(r['Qty']) for r in rows),
                              smd=0, tht='', n_tht=0)
                dnp = (folder / 'DNP.txt').read_text(encoding='utf-8').splitlines()[1].strip()
                dnp = '' if dnp.startswith('none') else dnp
                html = p['assembly_html']('release-' + key, dnp, counts, table)
                notes = p['order_notes'](None, 'release-' + key, lambda _: f"{p['width']:g} x {p['height']:g} mm")
                for content in (html, notes, strings(p['assembly']), p['exposed_pad_text']):
                    self.assertNotRegex(content, r'(?i)\b24[ -]*(?:ch\b|channels?\b|thermocouple channels)')
                    self.assertLessEqual(set(REF.findall(content)), refs)
                self.assertIn(f'Thermo {key}-channel board', html)
                self.assertIn(f'Thermo {key}-channel board', notes)
                self.assertIn(f'all {key} thermocouple channels', html)
                self.assertEqual(set(p['assembly']), set(donor['assembly']))
                self.assertIn('do <b>not</b> program the microcontroller', html)
                self.assertIn('69.2 mA typical' if key == '8' else '70.5 mA typical', html)
                self.assertIn('TP603 (24V)', html)
                self.assertEqual(p['channels'], int(key))
                self.assertIn('U411', strings(p['assembly']['ORIENT']))
                self.assertNotIn('U405', html)
                adc_refs = ('U101',) if key == '8' else ('U101', 'U201', 'U301', 'U801', 'U901', 'U1001')
                for ref in adc_refs:
                    self.assertIn(ref, p['exposed_pad_text'])
                self.assertIn('8-pin x2' if key == '8' else '8-pin x10', html)
                if key == '40':
                    self.assertIn('3 PT100', notes)
                    for text in ('3 PT100', 'U410', 'R1092', 'R1095', '6-pin x1', '3-pin x1'):
                        self.assertIn(text, html)
                else:
                    self.assertNotIn('U410', html)
                    self.assertNotIn('PT100', html)
                # Alternative DNP branch must still contain only real references.
                self.assertLessEqual(set(REF.findall(p['assembly_html']('copy', 'U703', counts, table))), refs)


if __name__ == '__main__':
    unittest.main()
