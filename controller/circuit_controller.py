"""Controleur des operations sur la scene de circuit."""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QPointF

from view.node_item import NodeItem


class CircuitController:
	"""Gere les interactions avec la scene et la vue du circuit."""

	def __init__(self, window, scene, view, app_controller=None) -> None:
		self.window = window
		self.scene = scene
		self.view = view
		self.app_controller = app_controller

	def set_tool(self, tool_name: str) -> None:
		"""Change l'outil actif via la fenetre."""
		if hasattr(self.window, "_apply_tool"):
			self.window._apply_tool(tool_name)

	def zoom_in(self) -> None:
		if self.view is not None:
			self.view.scale(1.25, 1.25)

	def zoom_out(self) -> None:
		if self.view is not None:
			self.view.scale(0.8, 0.8)

	def reset_zoom(self) -> None:
		if self.view is not None:
			self.view.resetTransform()

	def center_on_selection(self) -> None:
		if self.view is None or self.scene is None:
			return
		selected_items = self.scene.selectedItems()
		if not selected_items:
			return
		bounding = selected_items[0].sceneBoundingRect()
		for item in selected_items[1:]:
			bounding = bounding.united(item.sceneBoundingRect())
		self.view.centerOn(bounding.center())

	def toggle_grid(self) -> None:
		if self.scene is None:
			return
		if hasattr(self.scene, "toggle_grid"):
			self.scene.toggle_grid()
		else:
			if self.app_controller is not None:
				self.app_controller.not_implemented("Grille")

	def toggle_snap_grid(self) -> None:
		if self.scene is None:
			return
		if hasattr(self.scene, "toggle_snap"):
			self.scene.toggle_snap()
		else:
			if self.app_controller is not None:
				self.app_controller.not_implemented("Aimantation")

	def toggle_nodes(self) -> None:
		if self.scene is None:
			return
		if hasattr(self.scene, "toggle_nodes"):
			self.scene.toggle_nodes()
			return
		for item in self.scene.items():
			if isinstance(item, NodeItem):
				item.setVisible(not item.isVisible())

	def toggle_labels(self) -> None:
		if self.app_controller is not None:
			self.app_controller.not_implemented("Etiquettes")

	def toggle_wire_direction(self) -> None:
		if self.app_controller is not None:
			self.app_controller.not_implemented("Direction du courant")

	def toggle_fullscreen(self) -> None:
		if self.app_controller is not None:
			self.app_controller.toggle_fullscreen()

	def highlight_short_circuit(self) -> None:
		if self.app_controller is not None:
			self.app_controller.not_implemented("Surlignage court-circuit")
