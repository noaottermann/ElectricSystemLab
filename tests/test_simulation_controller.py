import unittest

from controller.simulation_controller import SimulationController
from model.circuit import Circuit
from model.components import Resistor, VoltageSourceAC, VoltageSourceDC


class FakeAppController:
    def __init__(self):
        self.messages = []

    def set_status(self, message: str, timeout_ms: int = 3000) -> None:
        self.messages.append((message, timeout_ms))


class TestSimulationController(unittest.TestCase):
    def _build_dc_circuit(self) -> Circuit:
        circuit = Circuit()
        n_gnd = circuit.create_node(0, 0, is_ground=True)
        n_pos = circuit.create_node(0, 10)
        circuit.add_dipole(VoltageSourceDC(circuit.get_next_dipole_id(), n_pos, n_gnd, dc_voltage=10.0))
        circuit.add_dipole(Resistor(circuit.get_next_dipole_id(), n_pos, n_gnd, resistance=5.0))
        return circuit

    def _build_ac_circuit(self) -> Circuit:
        circuit = Circuit()
        n_gnd = circuit.create_node(0, 0, is_ground=True)
        n_pos = circuit.create_node(0, 10)
        circuit.add_dipole(
            VoltageSourceAC(
                circuit.get_next_dipole_id(),
                n_pos,
                n_gnd,
                amplitude=10.0,
                frequency=1.0,
                phase=0.0,
                offset=0.0,
            )
        )
        circuit.add_dipole(Resistor(circuit.get_next_dipole_id(), n_pos, n_gnd, resistance=10.0))
        return circuit

    def test_run_dc_updates_status(self) -> None:
        app = FakeAppController()
        controller = SimulationController(self._build_dc_circuit(), app_controller=app)

        controller.run_dc()

        self.assertTrue(app.messages)
        self.assertIn("Simulation DC terminee", app.messages[-1][0])

    def test_run_transient_returns_result_and_stores_last(self) -> None:
        app = FakeAppController()
        controller = SimulationController(self._build_ac_circuit(), app_controller=app)

        result = controller.run_transient(duration=0.5, time_step=0.25)

        self.assertIsNotNone(result)
        self.assertEqual(result["time"], [0.0, 0.25, 0.5])
        self.assertIs(controller.last_transient_result, result)
        self.assertIn("Simulation transitoire terminee", app.messages[-1][0])

    def test_run_transient_handles_invalid_args(self) -> None:
        app = FakeAppController()
        controller = SimulationController(self._build_dc_circuit(), app_controller=app)

        result = controller.run_transient(duration=1.0, time_step=0.0)

        self.assertIsNone(result)
        self.assertIn("Simulation transitoire impossible", app.messages[-1][0])

    def test_realtime_simulation_progress_without_auto_completion(self) -> None:
        app = FakeAppController()
        controller = SimulationController(self._build_ac_circuit(), app_controller=app)
        updates = []
        finished = []

        started = controller.start_realtime_transient(
            time_step=0.25,
            on_update=lambda result: updates.append(result),
            on_finished=lambda: finished.append(True),
        )
        self.assertTrue(started)
        self.assertTrue(controller.is_realtime_running)

        controller.tick_realtime_transient()
        self.assertEqual(len(updates), 1)
        self.assertTrue(controller.is_realtime_running)

        controller.tick_realtime_transient()
        self.assertEqual(len(updates), 2)
        self.assertTrue(controller.is_realtime_running)
        self.assertEqual(len(finished), 0)
        self.assertGreater(controller.realtime_elapsed_time, 0.0)

    def test_realtime_start_rejects_invalid_params(self) -> None:
        app = FakeAppController()
        controller = SimulationController(self._build_dc_circuit(), app_controller=app)

        started = controller.start_realtime_transient(time_step=0.0)

        self.assertFalse(started)
        self.assertFalse(controller.is_realtime_running)
        self.assertIn("Parametres temps reel invalides", app.messages[-1][0])

    def test_realtime_stop_sets_state(self) -> None:
        app = FakeAppController()
        controller = SimulationController(self._build_dc_circuit(), app_controller=app)

        controller.start_realtime_transient(time_step=0.1)
        controller.stop_realtime_transient()

        self.assertFalse(controller.is_realtime_running)
        self.assertIn("Simulation temps reel arretee", app.messages[-1][0])


if __name__ == "__main__":
    unittest.main()
