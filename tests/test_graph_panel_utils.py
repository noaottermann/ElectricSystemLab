import unittest

import numpy as np

from view.graph_panel import _nearest_index, _rms


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


if __name__ == "__main__":
    unittest.main()
