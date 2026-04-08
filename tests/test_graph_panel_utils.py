import unittest

import numpy as np

from view.graphs_panel import _nearest_index, _pad_range, _rms, _trace_value_at_time


class TestGraphPanelUtils(unittest.TestCase):
    def test_rms_empty(self):
        self.assertEqual(_rms(np.array([])), 0.0)

    def test_rms_signal(self):
        values = np.array([1.0, -1.0, 1.0, -1.0])
        self.assertAlmostEqual(_rms(values), 1.0, places=7)

    def test_nearest_index_empty(self):
        self.assertEqual(_nearest_index(np.array([]), 0.5), 0)

    def test_nearest_index_nominal(self):
        time_values = np.array([0.0, 0.1, 0.2, 0.3])
        self.assertEqual(_nearest_index(time_values, 0.24), 2)

    def test_trace_value_at_time_nominal(self):
        time_values = np.array([0.0, 0.1, 0.2, 0.3])
        values = np.array([0.0, 1.0, 2.0, 3.0])
        index, sample_time, sample_value = _trace_value_at_time(time_values, values, 0.26)
        self.assertEqual(index, 3)
        self.assertAlmostEqual(sample_time, 0.3, places=7)
        self.assertAlmostEqual(sample_value, 3.0, places=7)

    def test_pad_range_expands_constant_values(self):
        lower, upper = _pad_range(5.0, 5.0)
        self.assertLess(lower, 5.0)
        self.assertGreater(upper, 5.0)


if __name__ == "__main__":
    unittest.main()
