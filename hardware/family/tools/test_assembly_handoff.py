"""Release handoff contracts exercised with isolated release fixtures."""
import csv
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import unittest
import uuid

HERE = Path(__file__).resolve().parent
SCRATCH = HERE.parents[1] / '8ch-new' / 'output' / 'coord' / 'assembly-tests'
sys.path.insert(0, str(HERE))


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.rel = SCRATCH / uuid.uuid4().hex
        self.rel.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.rel)

    def test_jlc_rows_leave_raw_cpl_and_apply_package_rotation_and_drilled_centre(self):
        self.assertIsNotNone(importlib.util.find_spec('cpl_jlc'))
        from cpl_jlc import adjust_rows
        rows = [['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'],
                ['U501', '10mm', '-20mm', 'Top', '90'],
                ['J501', '30mm', '-40mm', 'Top', '0'],
                ['R1', '5mm', '-6mm', 'Top', '0']]
        packages = {'U501': 'TQFP-44', 'J501': 'PinHeader_2x03', 'R1': 'R_0603'}
        shifted = adjust_rows(rows, packages, {'J501': (2.5, -1.0)}, '8')
        self.assertEqual(rows[1][4], '90')
        self.assertEqual(shifted[1][4], '0.000000')
        self.assertEqual(shifted[2][1:3], ['32.500000mm', '-39.000000mm'])
        self.assertEqual(shifted[2][4], '270.000000')
        self.assertEqual(shifted[3], rows[3])

    def test_manifest_complete_and_idempotent_with_metadata_preserved(self):
        self.assertIsNotNone(importlib.util.find_spec('manifest_complete'))
        from manifest_complete import rewrite_manifest
        (self.rel / 'MANIFEST.txt').write_text('MANIFEST fixture\nsource board sha256: xyz\nevery output file sha256 (all files in this folder except this one):\n  stale  missing.txt\n', encoding='utf-8')
        (self.rel / 'CPL-JLC.csv').write_text('fresh', encoding='utf-8')
        (self.rel / 'source-snapshot').mkdir()
        (self.rel / 'source-snapshot' / 'board.kicad_pcb').write_text('snapshot', encoding='utf-8')
        rewrite_manifest(self.rel)
        first = (self.rel / 'MANIFEST.txt').read_text(encoding='utf-8')
        self.assertIn('source board sha256: xyz', first)
        self.assertIn(hashlib.sha256(b'fresh').hexdigest() + '  CPL-JLC.csv', first)
        self.assertIn('source-snapshot/board.kicad_pcb', first)
        self.assertNotIn('missing.txt', first)
        rewrite_manifest(self.rel)
        self.assertEqual(first, (self.rel / 'MANIFEST.txt').read_text(encoding='utf-8'))

    def test_handoff_names_raw_and_jlc_cpl_and_profile_refs(self):
        self.assertIsNotNone(importlib.util.find_spec('assembly_spec'))
        from assembly_spec import handoff_texts
        profile = {'key': '8l', 'project': 'thermo8', 'channels': 8, 'revision': 'REV B0-2L'}
        which, notes, remark = handoff_texts('8ch-test', profile, {'U101', 'U601'}, {'K701', 'U401'})
        self.assertIn('CPL-JLC.csv', which)
        self.assertIn('CPL.csv', which)
        self.assertIn('POWER-ON-TEST.zip', which)
        self.assertIn('CPL-JLC.csv', notes)
        self.assertIn('CPL.csv', notes)
        self.assertIn('U101', remark)
        self.assertNotIn('U201', remark)
        self.assertLessEqual(len(remark), 500)


if __name__ == '__main__':
    unittest.main()
