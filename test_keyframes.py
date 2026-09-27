import unittest
from keyframes import snap_interval


class KeyframeTests(unittest.TestCase):
    def test_offset_duplicates_and_fractional_time(self):
        frames = [{"best_effort_timestamp_time": x} for x in ["12", "14", "14", "16"]]
        self.assertEqual(snap_interval(frames, 2.36, 4.36, 20, 10), (2, 6))

    def test_does_not_extend_to_eof_when_scan_is_incomplete(self):
        with self.assertRaisesRegex(ValueError, "No nearby"):
            snap_interval([{"best_effort_timestamp_time": "2"}], 2.1, 4, 100)

    def test_eof_is_a_valid_out_boundary(self):
        self.assertEqual(
            snap_interval([{"best_effort_timestamp_time": "6"}], 6.2, 7.9, 8), (6, 8)
        )

    def test_rejects_invalid_timestamp_and_empty_scan(self):
        for frames in [[], [{"best_effort_timestamp_time": "nan"}]]:
            with self.subTest(frames=frames), self.assertRaises(ValueError):
                snap_interval(frames, 2, 4, 8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
