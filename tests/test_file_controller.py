import unittest
from pathlib import Path

from controller.file_controller import FileController
from controller.ui_callbacks import MessageType


class _FakeCallbacks:
    def __init__(self) -> None:
        self.status_messages = []
        self.current_filename = None
        self.messages = []

    def set_status_message(self, message: str, timeout_ms: int = 3000) -> None:
        self.status_messages.append((message, timeout_ms))

    def show_message(self, title: str, message: str, message_type: MessageType = MessageType.INFO) -> None:
        self.messages.append((title, message, message_type))

    def apply_tool(self, tool_name: str) -> None:
        return None

    def set_current_filename(self, filename) -> None:
        self.current_filename = filename

    def refresh_scene_from_model(self) -> None:
        return None

    def update_transform_actions_visibility(self) -> None:
        return None

    def push_undo_snapshot(self) -> None:
        return None

    def update_toolbar_geometry(self) -> None:
        return None

    def toggle_grid(self) -> None:
        return None

    def toggle_snap(self) -> None:
        return None

    def toggle_nodes(self) -> None:
        return None

    def toggle_wire_direction(self) -> None:
        return None

    def set_meter_label_mode(self, mode: str) -> None:
        return None


class _FakeModel:
    def __init__(self) -> None:
        self.cleared = False
        self.dipoles = {}

    def clear(self) -> None:
        self.cleared = True


class _FakeDipole:
    def __init__(self, dipole_id: int) -> None:
        self.id = dipole_id
        self.voltage = float(dipole_id)
        self.current = float(dipole_id) / 10.0


class _FakeIOService:
    def __init__(self) -> None:
        self.calls = []

    def load_circuit_from_file(self, model, path: Path) -> None:
        self.calls.append(("load", Path(path)))

    def save_circuit_to_file(self, model, path: Path) -> None:
        self.calls.append(("save", Path(path)))

    def import_circuit(self, model, path: Path) -> None:
        self.calls.append(("import", Path(path)))

    def export_circuit(self, model, path: Path, simulation_data=None) -> None:
        self.calls.append(("export", Path(path), simulation_data))

    def export_simulation_results(self, results, path: Path) -> None:
        self.calls.append(("export_results", Path(path), results))

    def export_transient_results_csv(self, results, path: Path) -> None:
        self.calls.append(("export_csv", Path(path), results))


class FileControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = _FakeModel()
        self.callbacks = _FakeCallbacks()
        self.io_service = _FakeIOService()
        self.controller = FileController(
            self.model,
            self.callbacks,
            io_service=self.io_service,
        )

    def test_open_circuit_from_path_refreshes_scene_and_filename(self) -> None:
        refresh_calls = {"count": 0}
        self.callbacks.refresh_scene_from_model = lambda: refresh_calls.__setitem__("count", refresh_calls["count"] + 1)
        result = self.controller.open_circuit_from_path("sample.json")
        self.assertTrue(result)
        self.assertEqual(refresh_calls["count"], 1)
        self.assertEqual(self.callbacks.current_filename, "sample.json")
        self.assertEqual(self.io_service.calls[0][0], "load")

    def test_save_circuit_requires_current_path(self) -> None:
        self.assertFalse(self.controller.save_circuit())
        self.assertEqual(len(self.io_service.calls), 0)

    def test_save_circuit_to_path_adds_json_suffix(self) -> None:
        result = self.controller.save_circuit_to_path("circuit")
        self.assertTrue(result)
        operation, path = self.io_service.calls[0]
        self.assertEqual(operation, "save")
        self.assertEqual(path.suffix, ".json")
        self.assertEqual(self.callbacks.current_filename, "circuit.json")

    def test_import_updates_scene_and_recent_file(self) -> None:
        refresh_calls = {"count": 0}
        self.callbacks.refresh_scene_from_model = lambda: refresh_calls.__setitem__("count", refresh_calls["count"] + 1)
        result = self.controller.import_circuit_from_path("imported.json")
        self.assertTrue(result)
        self.assertEqual(refresh_calls["count"], 1)
        self.assertEqual(self.callbacks.current_filename, "imported.json")

    def test_export_circuit_passes_simulation_data(self) -> None:
        payload = {"time": [0.0, 0.1]}
        result = self.controller.export_circuit_to_path("exported", simulation_data=payload)
        self.assertTrue(result)
        operation, path, data = self.io_service.calls[0]
        self.assertEqual(operation, "export")
        self.assertEqual(path.suffix, ".json")
        self.assertEqual(data, payload)

    def test_export_csv_without_result_returns_false(self) -> None:
        result = self.controller.export_transient_results_csv_to_path("trace.csv", None)
        self.assertFalse(result)
        self.assertTrue(self.callbacks.messages)

    def test_build_fallback_simulation_results(self) -> None:
        self.model.dipoles = {2: _FakeDipole(2), 1: _FakeDipole(1)}
        fallback = self.controller.build_fallback_simulation_results()
        dipoles = fallback["dc"]["dipoles"]
        self.assertEqual([entry["id"] for entry in dipoles], [1, 2])


if __name__ == "__main__":
    unittest.main()
