"""Controleur de simulation."""

from __future__ import annotations

from solver.ac_solver import ACSolver
from solver.dc_solver import DCSolver
from solver.transient_solver import TransientSolver


class SimulationController:
	"""Gere les executions de solveurs."""

	def __init__(self, model, app_controller=None) -> None:
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
			self.app_controller.set_status("Simulation DC terminee")

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
			self.app_controller.set_status("Simulation AC terminee")
		return result

	def _solve_transient(self, duration: float, time_step: float, status_message: str | None):
		"""Execute le solveur transitoire et met a jour l'etat interne."""
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
		"""Execute le solveur transitoire sur une fenetre temporelle locale."""
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
		"""Configure la taille maximale d'historique conservee en temps reel."""
		self._realtime_max_points = max(20, int(max_points))

	def run_transient(self, duration: float = 1.0, time_step: float = 0.01):
		"""Lance une simulation transitoire avec des parametres simples."""
		result = self._solve_transient(
			duration=duration,
			time_step=time_step,
			status_message=None,
		)
		if result is None:
			return None

		if self.app_controller is not None:
			self.app_controller.set_status(
				f"Simulation transitoire terminee ({len(result.get('time', []))} points)"
			)
		return result

	@property
	def is_realtime_running(self) -> bool:
		"""Indique si la simulation temps reel est active."""
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
				self.app_controller.set_status("Parametres temps reel invalides")
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
			self.app_controller.set_status("Simulation temps reel demarree")
		return True

	def tick_realtime_transient(self):
		"""Calcule l'etat suivant de la simulation temps reel."""
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
			self.stop_realtime_transient("Simulation temps reel interrompue")
			return None

		self._realtime_current_time = next_time
		result = self._append_realtime_sample(window_result)
		if callable(self._realtime_on_update):
			self._realtime_on_update(result)

		if self.app_controller is not None:
			self.app_controller.set_status(
				f"Simulation temps reel: t={self._realtime_current_time:.4g}s"
			)

		return result

	def _append_realtime_sample(self, window_result: dict[str, object]) -> dict[str, object]:
		"""Ajoute un echantillon au buffer temps reel en conservant une taille bornee."""
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
		"""Limite l'historique temps reel pour garder un cout constant."""
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
		"""Temps simule cumule en mode temps reel."""
		return self._realtime_current_time

	@property
	def realtime_time_step(self) -> float:
		"""Pas de temps du mode temps reel."""
		return self._realtime_time_step

	def stop_realtime_transient(self, status_message: str | None = "Simulation temps reel arretee") -> None:
		"""Arrete la simulation temps reel en cours."""
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
