"""Controleur de simulation."""

from __future__ import annotations

from solver.dc_solver import DCSolver


class SimulationController:
	"""Gere les executions de solveurs."""

	def __init__(self, model, app_controller=None) -> None:
		self.model = model
		self.app_controller = app_controller
		self._dc_solver = DCSolver()

	def run_dc(self) -> None:
		"""Lance une simulation DC."""
		if self.model is None:
			if self.app_controller is not None:
				self.app_controller.set_status("Aucun circuit pour la simulation")
			return
		self._dc_solver.solve(self.model)
		if self.app_controller is not None:
			self.app_controller.set_status("Simulation DC terminee")
