"""Controleur de simulation."""

from __future__ import annotations

from solver.dc_solver import DCSolver
from solver.transient_solver import TransientSolver


class SimulationController:
	"""Gere les executions de solveurs."""

	def __init__(self, model, app_controller=None) -> None:
		self.model = model
		self.app_controller = app_controller
		self._dc_solver = DCSolver()
		self._transient_solver = TransientSolver()
		self.last_transient_result = None
		self._realtime_running = False
		self._realtime_time_step = 0.0
		self._realtime_current_time = 0.0
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
		self._realtime_on_update = on_update
		self._realtime_on_finished = on_finished

		if self.app_controller is not None:
			self.app_controller.set_status("Simulation temps reel demarree")
		return True

	def tick_realtime_transient(self):
		"""Calcule l'etat suivant de la simulation temps reel."""
		if not self._realtime_running:
			return None

		next_time = self._realtime_current_time + self._realtime_time_step
		result = self._solve_transient(
			duration=next_time,
			time_step=self._realtime_time_step,
			status_message=None,
		)
		if result is None:
			self.stop_realtime_transient("Simulation temps reel interrompue")
			return None

		self._realtime_current_time = next_time
		if callable(self._realtime_on_update):
			self._realtime_on_update(result)

		if self.app_controller is not None:
			self.app_controller.set_status(
				f"Simulation temps reel: t={self._realtime_current_time:.4g}s"
			)

		return result

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
		self._realtime_on_update = None
		self._realtime_on_finished = None

		if was_running and self.app_controller is not None and status_message:
			self.app_controller.set_status(status_message)
		if was_running and callable(on_finished):
			on_finished()
