"""Release warnings are fail-closed, including malformed or missing summaries."""
from pathlib import Path
import tempfile
import unittest

from release_checks import warning_summary, copper_layers


class WarningTests(unittest.TestCase):
    def test_two_layer_export_does_not_request_disabled_inner_copper(self):
        self.assertEqual(copper_layers(2), ('F.Cu', 'B.Cu'))
        self.assertEqual(copper_layers(4), ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'))

    def test_lists_advisories_and_blocks_both_dangling_kinds(self):
        for kind in ('track_dangling', 'via_dangling'):
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, kind):
                warning_summary(f'[{kind}]: stub\n** Found 1 DRC violations **\n'
                                '** Found 0 unconnected pads **\n** Found 0 Footprint errors **\n')
        result = warning_summary('[silk_overlap]: text\n** Found 1 DRC violations **\n'
                                 '** Found 0 unconnected pads **\n** Found 0 Footprint errors **\n')
        self.assertEqual(result, {'silk_overlap': 1})

    def test_rejects_incomplete_or_regressed_reports(self):
        for text in ('', '** Found 0 DRC violations **',
                     '** Found 0 DRC violations **\n** Found 1 unconnected pads **\n'
                     '** Found 0 Footprint errors **'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                warning_summary(text)

    def test_description_parity_warnings_are_advisory_not_manufacturing_errors(self):
        report = ('** Found 0 DRC violations **\n** Found 0 unconnected pads **\n'
                  '** Found 1 Footprint errors **\n[footprint_symbol_field_mismatch]: Description\n'
                  '    Local override; warning\n')
        self.assertEqual(warning_summary(report), {'footprint_symbol_field_mismatch': 1})


if __name__ == '__main__':
    unittest.main()
