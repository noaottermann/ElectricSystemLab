import json
import tempfile
import unittest
from pathlib import Path

from model.circuit import Circuit
from model.components import Resistor, VoltageSourceDC
from persistence import serializer, importer, exporter


serialize_circuit = serializer.serialize_circuit
deserialize_circuit = serializer.deserialize_circuit
load_circuit_from_file = serializer.load_circuit_from_file
save_circuit_to_file = serializer.save_circuit_to_file
import_circuit = importer.import_circuit
export_circuit = exporter.export_circuit


class TestIO(unittest.TestCase):
	def setUp(self) -> None:
		self.circuit = Circuit()
		n_gnd = self.circuit.create_node(0, 0, is_ground=True)
		n_pos = self.circuit.create_node(20, 0)
		src = VoltageSourceDC(self.circuit.get_next_dipole_id(), n_pos, n_gnd, dc_voltage=5.0)
		self.circuit.add_dipole(src)
		r1 = Resistor(self.circuit.get_next_dipole_id(), n_pos, n_gnd, resistance=100.0)
		self.circuit.add_dipole(r1)

	def test_serialize_deserialize_roundtrip(self) -> None:
		payload = serialize_circuit(self.circuit)
		self.assertIsInstance(payload, str)
		parsed = json.loads(payload)
		self.assertIn("nodes", parsed)
		self.assertIn("dipoles", parsed)

		target = Circuit()
		deserialize_circuit(target, payload)
		self.assertEqual(len(target.nodes), len(self.circuit.nodes))
		self.assertEqual(len(target.dipoles), len(self.circuit.dipoles))

	def test_save_load_file_roundtrip(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			path = Path(tmp) / "circuit.json"
			save_circuit_to_file(self.circuit, path)

			loaded = Circuit()
			load_circuit_from_file(loaded, path)

			self.assertEqual(len(loaded.nodes), 2)
			self.assertEqual(len(loaded.dipoles), 2)

	def test_import_export_reject_non_json_extensions(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			bad_path = Path(tmp) / "circuit.txt"

			with self.assertRaises(ValueError):
				export_circuit(self.circuit, bad_path)

			with self.assertRaises(ValueError):
				import_circuit(self.circuit, bad_path)

	def test_export_circuit_with_simulation_data(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			path = Path(tmp) / "with_sim.json"
			payload = {
				"time": [0.0, 0.01],
				"node_potentials": {"1": [0.0, 1.0]},
				"dipole_currents": {"1": [0.0, 0.1]},
			}

			export_circuit(self.circuit, path, simulation_data=payload)

			exported = json.loads(path.read_text(encoding="utf-8"))
			self.assertIn("simulation", exported)
			self.assertEqual(exported["simulation"], payload)

	def test_export_simulation_results_to_file(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			path = Path(tmp) / "results.json"
			results = {
				"dc": {
					"nodes": [{"id": 1, "potential": 5.0, "is_ground": False}],
					"dipoles": [{"id": 1, "type": "Resistor", "current": 0.05, "voltage": 5.0}],
				}
			}

			exporter.export_simulation_results_to_file(results, path)

			exported = json.loads(path.read_text(encoding="utf-8"))
			self.assertEqual(exported["type"], "simulation_results")
			self.assertEqual(exported["dc"], results["dc"])

	def test_export_transient_results_to_csv(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			path = Path(tmp) / "traces.csv"
			results = {
				"time": [0.0, 0.1, 0.2],
				"node_potentials": {1: [0.0, 1.0, 2.0]},
				"dipole_currents": {2: [0.0, 0.5, 1.0]},
			}

			exporter.export_transient_results_to_csv(results, path)

			content = path.read_text(encoding="utf-8").splitlines()
			self.assertGreaterEqual(len(content), 2)
			self.assertIn("time,dipole_voltage_1,dipole_2", content[0])
			self.assertIn("0.1,1.0,0.5", content[2])


if __name__ == "__main__":
	unittest.main()
