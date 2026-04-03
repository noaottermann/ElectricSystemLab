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

	def run_dc(self) -> None:
		"""Lance une simulation DC."""
		if self.model is None:
			if self.app_controller is not None:
				self.app_controller.set_status("Aucun circuit pour la simulation")
			return
		self._dc_solver.solve(self.model)
		if self.app_controller is not None:
			self.app_controller.set_status("Simulation DC terminee")

	def run_transient(self, duration: float = 1.0, time_step: float = 0.01):
		"""Lance une simulation transitoire avec des parametres simples."""
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
		if self.app_controller is not None:
			self.app_controller.set_status(
				f"Simulation transitoire terminee ({len(result.get('time', []))} points)"
			)
		return result
