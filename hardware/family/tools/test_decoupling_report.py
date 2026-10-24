"""Proposed routed-supply limits must expose missing/long/fragmented returns."""
import unittest
from decoupling_report import assess


class CriterionTests(unittest.TestCase):
    def test_reports_failed_conditions_instead_of_relaxing_to_the_current_board(self):
        self.assertEqual(assess(5., 1, True), [])
        self.assertIn('supply path > 5 mm', assess(6.81, 0, True))
        self.assertIn('supply uses > 1 via', assess(11.48, 2, True))
        self.assertIn('return does not reach saved ground fill', assess(1., 0, False))
        self.assertIn('no routed supply path', assess(None, 0, True))


if __name__ == '__main__':
    unittest.main()
