import unittest

from model.circuit import Circuit
from model.components import Resistor


class TestCircuit(unittest.TestCase):
	def setUp(self) -> None:
		self.circuit = Circuit()

	def test_merge_nodes_updates_dipoles_and_wires(self) -> None:
		n1 = self.circuit.create_node(0, 0)
		n2 = self.circuit.create_node(20, 0)
		n3 = self.circuit.create_node(40, 0)

		r1 = Resistor(self.circuit.get_next_dipole_id(), n1, n3, resistance=100.0)
		self.circuit.add_dipole(r1)
		wire = self.circuit.create_wire(n2, n3)

		keeper = self.circuit.merge_nodes(n1, n2)

		self.assertIs(keeper, n1)
		self.assertNotIn(n2.id, self.circuit.nodes)
		self.assertIs(r1.node_a, n1)
		self.assertIs(wire.node_a, n1)

	def test_create_wire_rejects_unknown_nodes(self) -> None:
		n1 = self.circuit.create_node(0, 0)
		n2 = self.circuit.create_node(20, 0)
		self.circuit.remove_node(n2.id)

		with self.assertRaises(ValueError):
			self.circuit.create_wire(n1, n2)

	def test_clear_resets_containers_and_counters(self) -> None:
		n1 = self.circuit.create_node(0, 0)
		n2 = self.circuit.create_node(20, 0)
		r1 = Resistor(self.circuit.get_next_dipole_id(), n1, n2, resistance=10.0)
		self.circuit.add_dipole(r1)
		self.circuit.create_wire(n1, n2)

		self.circuit.clear()

		self.assertEqual(len(self.circuit.nodes), 0)
		self.assertEqual(len(self.circuit.dipoles), 0)
		self.assertEqual(len(self.circuit.wires), 0)

		n_new = self.circuit.create_node(10, 10)
		self.assertEqual(n_new.id, 1)
		self.assertEqual(self.circuit.get_next_dipole_id(), 1)


if __name__ == "__main__":
	unittest.main()
