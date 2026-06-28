import unittest

from model import get_component_registry
from model.components import CurrentSourceAC, Resistor, VoltageSourceDC


class TestComponentRegistry(unittest.TestCase):
    def test_registry_exposes_known_components(self) -> None:
        registry = get_component_registry()

        self.assertIs(registry["Resistor"], Resistor)
        self.assertIs(registry["VoltageSourceDC"], VoltageSourceDC)
        self.assertIs(registry["CurrentSourceAC"], CurrentSourceAC)
        self.assertIn("Ground", registry)


if __name__ == "__main__":
    unittest.main()