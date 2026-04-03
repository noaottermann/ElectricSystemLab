import json
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from model.circuit import Circuit
from model.components import Resistor, VoltageSourceDC


def _load_project_io_modules():
	root = Path(__file__).resolve().parents[1]
	io_dir = root / "io"

	pkg_name = "project_io"
	if pkg_name not in sys.modules:
		pkg_spec = importlib.util.spec_from_file_location(
			pkg_name,
			io_dir / "__init__.py",
			submodule_search_locations=[str(io_dir)],
		)
		pkg_module = importlib.util.module_from_spec(pkg_spec)
		sys.modules[pkg_name] = pkg_module
		pkg_spec.loader.exec_module(pkg_module)

	loaded = {}
	for module_name in ("serializer", "importer", "exporter"):
		full_name = f"{pkg_name}.{module_name}"
		if full_name in sys.modules:
			loaded[module_name] = sys.modules[full_name]
			continue
		module_spec = importlib.util.spec_from_file_location(full_name, io_dir / f"{module_name}.py")
		module = importlib.util.module_from_spec(module_spec)
		sys.modules[full_name] = module
		module_spec.loader.exec_module(module)
		loaded[module_name] = module

	return loaded


_io_modules = _load_project_io_modules()
serialize_circuit = _io_modules["serializer"].serialize_circuit
deserialize_circuit = _io_modules["serializer"].deserialize_circuit
load_circuit_from_file = _io_modules["serializer"].load_circuit_from_file
save_circuit_to_file = _io_modules["serializer"].save_circuit_to_file
import_circuit = _io_modules["importer"].import_circuit
export_circuit = _io_modules["exporter"].export_circuit


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

			_io_modules["exporter"].export_simulation_results_to_file(results, path)

			exported = json.loads(path.read_text(encoding="utf-8"))
			self.assertEqual(exported["type"], "simulation_results")
			self.assertEqual(exported["dc"], results["dc"])


if __name__ == "__main__":
	unittest.main()
