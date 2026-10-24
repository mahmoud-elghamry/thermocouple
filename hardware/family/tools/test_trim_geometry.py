"""Trim only free extensions; keep every mid-segment tap."""
import unittest
from trim_geometry import retained_segment, junctions, require_rips, require_source_hash


class TrimTests(unittest.TestCase):
    def test_keeps_all_taps_and_removes_only_overshoot(self):
        self.assertEqual(retained_segment((0, 0), (10, 0), [(2, 0), (8, 0)]), ((2., 0.), (8., 0.)))
        self.assertEqual(retained_segment((0, 0), (10, 0), [(0, 0), (6, 0)]), ((0., 0.), (6., 0.)))
        self.assertIsNone(retained_segment((0, 0), (10, 0), [(4, 0)]))

    def test_detects_track_crossing_without_any_endpoint_on_the_segment(self):
        self.assertIn((4., 0.), junctions((0, 0), (10, 0), (4, -2), (4, 2)))

    def test_handles_reversed_diagonal_and_zero_length(self):
        self.assertEqual(retained_segment((10, 10), (0, 0), [(8, 8), (2, 2)]), ((8., 8.), (2., 2.)))
        self.assertIsNone(retained_segment((1, 1), (1, 1), []))

    def test_missing_uuid_is_a_refusal_not_a_partial_apply(self):
        with self.assertRaisesRegex(ValueError, 'missing'):
            require_rips({'present', 'missing'}, {'present'})

    def test_hash_is_enforced_before_any_board_mutation(self):
        with self.assertRaisesRegex(ValueError, 'source hash mismatch'):
            require_source_hash(b'changed', '# source sha256 '+'0'*64)


if __name__ == '__main__':
    unittest.main()
