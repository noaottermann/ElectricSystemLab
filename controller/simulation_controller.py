from __future__ import annotations

from typing import TYPE_CHECKING, Any

from solver.ac_solver import ACSolver
from solver.dc_solver import DCSolver
from solver.transient_solver import TransientSolver

if TYPE_CHECKING:
    from model.circuit import Circuit


class SimulationController:
	"""Gère les éxecutions de solveurs."""

	def __init__(self, model: Circuit, app_controller: Any = None) -> None:
		self.model = model
		self.app_controller = app_controller
		self._dc_solver = DCSolver()
		self._ac_solver = ACSolver()
		self._transient_solver = TransientSolver()
		self.last_transient_result = None
		self.last_ac_result = None
		self._realtime_running = False
		self._realtime_time_step = 0.0
		self._realtime_current_time = 0.0
		self._realtime_max_points = 300
		self._realtime_result_buffer = None
		self._realtime_on_update = None
		self._realtime_on_finished = None

	def run_dc(self) -> None:
		"""Lance une simulation DC."""
		if self.model is None:
			if self.app_controller is not None:
				self.app_controller.set_status("Aucun circuit pour la simulation")
			return
		self._dc_solver.solve(self.model)
		if self.app_controller is not None:
			self.app_controller.set_status("Simulation DC terminée")

	def run_ac(
		self,
		start_freq: float,
		stop_freq: float,
		points: int,
		sweep: str = "log",
	):
		"""Lance une simulation AC (phasors)."""
		if self.model is None:
			if self.app_controller is not None:
				self.app_controller.set_status("Aucun circuit pour la simulation")
			return None
		try:
			result = self._ac_solver.solve(
				self.model,
				start_freq=start_freq,
				stop_freq=stop_freq,
				points=points,
				sweep=sweep,
			)
		except ValueError as exc:
			if self.app_controller is not None:
				self.app_controller.set_status(f"Simulation AC impossible: {exc}")
			return None

		self.last_ac_result = result
		if self.app_controller is not None:
			self.app_controller.set_status("Simulation AC terminée")
		return result

	def _solve_transient(self, duration: float, time_step: float, status_message: str | None):
		"""Éxecute le solveur transitoire et met à jour l'état interne."""
		if self.model is None:
			if self.app_controller is not None:
				self.app_controller.set_status("Aucun circuit pour la simulation")
			return None

		try:
			result = self._transient_solver.solve(self.model, duration=duration, time_step=time_step)
		except ValueError as exc:
			if self.app_controller is not None:
				self.app_controller.set_status(f"Simulation transitoire impossible: {exc}")
			return None

		self.last_transient_result = result
		if self.app_controller is not None and status_message:
			self.app_controller.set_status(status_message)
		return result

	def _solve_transient_window(
		self,
		duration: float,
		time_step: float,
		start_time: float,
		status_message: str | None,
	):
		"""Éxecute le solveur transitoire sur une fenêtre temporelle locale."""
		if self.model is None:
			if self.app_controller is not None:
				self.app_controller.set_status("Aucun circuit pour la simulation")
			return None

		try:
			result = self._transient_solver.solve(
				self.model,
				duration=duration,
				time_step=time_step,
				start_time=start_time,
			)
		except ValueError as exc:
			if self.app_controller is not None:
				self.app_controller.set_status(f"Simulation transitoire impossible: {exc}")
			return None

		self.last_transient_result = result
		if self.app_controller is not None and status_message:
			self.app_controller.set_status(status_message)
		return result

	def set_realtime_history_limit(self, max_points: int) -> None:
		"""Configure la taille maximale d'historique conservée en temps réel."""
		self._realtime_max_points = max(20, int(max_points))

	def run_transient(self, duration: float = 1.0, time_step: float = 0.01):
		"""Lance une simulation transitoire avec des paramètres simples."""
		result = self._solve_transient(
			duration=duration,
			time_step=time_step,
			status_message=None,
		)
		if result is None:
			return None

		if self.app_controller is not None:
			self.app_controller.set_status(
				f"Simulation transitoire terminée ({len(result.get('time', []))} points)"
			)
		return result

	@property
	def is_realtime_running(self) -> bool:
		"""Indique si la simulation temps réel est active."""
		return self._realtime_running

	def start_realtime_transient(
		self,
		time_step: float,
		on_update=None,
		on_finished=None,
	) -> bool:
		"""Initialise une simulation transitoire progressive."""
		if self.model is None:
			if self.app_controller is not None:
				self.app_controller.set_status("Aucun circuit pour la simulation")
			return False
		if time_step <= 0:
			if self.app_controller is not None:
				self.app_controller.set_status("Paramètres temps réel invalides")
			return False

		self._realtime_running = True
		self._realtime_time_step = float(time_step)
		self._realtime_current_time = 0.0
		self._realtime_result_buffer = {
			"time": [],
			"node_potentials": {},
			"dipole_voltages": {},
			"dipole_currents": {},
		}
		self._realtime_on_update = on_update
		self._realtime_on_finished = on_finished

		if self.app_controller is not None:
			self.app_controller.set_status("Simulation temps réel démarree")
		return True

	def tick_realtime_transient(self):
		"""Calcule l'état suivant de la simulation temps réel."""
		if not self._realtime_running:
			return None

		start_time = self._realtime_current_time
		next_time = start_time + self._realtime_time_step
		window_result = self._solve_transient_window(
			duration=self._realtime_time_step,
			time_step=self._realtime_time_step,
			start_time=start_time,
			status_message=None,
		)
		if window_result is None:
			self.stop_realtime_transient("Simulation temps réel interrompue")
			return None

		self._realtime_current_time = next_time
		result = self._append_realtime_sample(window_result)
		if callable(self._realtime_on_update):
			self._realtime_on_update(result)

		if self.app_controller is not None:
			self.app_controller.set_status(
				f"Simulation temps réel: t={self._realtime_current_time:.4g}s"
			)

		return result

	def _append_realtime_sample(self, window_result: dict[str, object]) -> dict[str, object]:
		"""Ajoute un échantillon au buffer temps réel en conservant une taille bornée."""
		if self._realtime_result_buffer is None:
			self._realtime_result_buffer = {
				"time": [],
				"node_potentials": {},
				"dipole_voltages": {},
				"dipole_currents": {},
			}

		buffer = self._realtime_result_buffer
		window_times = window_result.get("time", [])
		if not window_times:
			return buffer
		buffer["time"].append(float(window_times[-1]))

		for key in ("node_potentials", "dipole_voltages", "dipole_currents"):
			source_map = window_result.get(key, {})
			target_map = buffer[key]
			for comp_id, values in source_map.items():
				if comp_id not in target_map:
					target_map[comp_id] = []
				if values:
					target_map[comp_id].append(float(values[-1]))
				else:
					target_map[comp_id].append(0.0)

		self._trim_realtime_buffer(buffer)
		self.last_transient_result = buffer
		return buffer

	def _trim_realtime_buffer(self, buffer: dict[str, object]) -> None:
		"""Limite l'historique temps réel pour garder un coût constant."""
		time_values = buffer.get("time", [])
		overflow = len(time_values) - self._realtime_max_points
		if overflow <= 0:
			return

		del time_values[:overflow]
		for key in ("node_potentials", "dipole_voltages", "dipole_currents"):
			series_map = buffer.get(key, {})
			for values in series_map.values():
				del values[:overflow]

	@property
	def realtime_elapsed_time(self) -> float:
		"""Temps simule cumule en mode temps réel."""
		return self._realtime_current_time

	@property
	def realtime_time_step(self) -> float:
		"""Pas de temps du mode temps réel."""
		return self._realtime_time_step

	def stop_realtime_transient(self, status_message: str | None = "Simulation temps réel arrêtée") -> None:
		"""Arrête la simulation temps réel en cours."""
		was_running = self._realtime_running
		on_finished = self._realtime_on_finished

		self._realtime_running = False
		self._realtime_result_buffer = None
		self._realtime_on_update = None
		self._realtime_on_finished = None

		if was_running and self.app_controller is not None and status_message:
			self.app_controller.set_status(status_message)
		if was_running and callable(on_finished):
			on_finished()

	def reset_simulation_state(self) -> None:
		"""Réinitialise les résultats et l'état du modèle."""
		self.stop_realtime_transient(status_message=None)
		self.last_transient_result = None
		self.last_ac_result = None
		if self.model is not None:
			self.model.reset_simulation()
