"""Contrôleur des opérations d'affichage et d'interaction sur la scène de circuit."""

from __future__ import annotations

from typing import Any, Optional

from PyQt5.QtCore import QPointF

from view.node_item import NodeItem


class CircuitController:
	"""Gère les interactions avec la scène et la vue du circuit."""

	def __init__(self, window: Any, scene: Any, view: Any, app_controller: Any = None) -> None:
		"""Initialise le contrôleur de circuit.

		Args:
			window: Référence à la fenêtre principale.
			scene: Scène graphique du circuit.
			view: Vue graphique (QGraphicsView).
			app_controller: Contrôleur global de l'application (optionnel).
		"""
		self.window = window
		self.scene = scene
		self.view = view
		self.app_controller = app_controller

	def set_tool(self, tool_name: str) -> None:
		"""Change l'outil actif via la fenêtre.

		Args:
			tool_name: Identifiant de l'outil sélectionné.
		"""
		if hasattr(self.window, "_apply_tool"):
			self.window._apply_tool(tool_name)

	def zoom_in(self) -> None:
		"""Effectue un zoom avant de 25% sur la vue graphique."""
		if self.view is not None:
			self.view.scale(1.25, 1.25)

	def zoom_out(self) -> None:
		"""Effectue un zoom arrière de 20% sur la vue graphique."""
		if self.view is not None:
			self.view.scale(0.8, 0.8)

	def reset_zoom(self) -> None:
		"""Réinitialise les transformations et le niveau de zoom de la vue."""
		if self.view is not None:
			self.view.resetTransform()

	def center_on_selection(self) -> None:
		"""Centre le champ de vue sur les éléments actuellement sélectionnés."""
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
		"""Bascule l'affichage de la grille régulière sur la scène."""
		if self.scene is None:
			return
		if hasattr(self.scene, "toggle_grid"):
			self.scene.toggle_grid()
		else:
			if self.app_controller is not None:
				self.app_controller.not_implemented("Grille")

	def toggle_snap_grid(self) -> None:
		"""Active ou désactive l'aimantation magnétique sur la grille."""
		if self.scene is None:
			return
		if hasattr(self.scene, "toggle_snap"):
			self.scene.toggle_snap()
		else:
			if self.app_controller is not None:
				self.app_controller.not_implemented("Aimantation")

	def toggle_nodes(self) -> None:
		"""Affiche ou masque les marqueurs de nœuds électriques."""
		if self.scene is None:
			return
		if hasattr(self.scene, "toggle_nodes"):
			self.scene.toggle_nodes()
			return
		for item in self.scene.items():
			if isinstance(item, NodeItem):
				item.setVisible(not item.isVisible())

	def toggle_labels(self) -> None:
		"""Active ou désactive l'affichage des étiquettes textuelles de composants."""
		if self.app_controller is not None:
			self.app_controller.not_implemented("Etiquettes")

	def toggle_wire_direction(self) -> None:
		"""Active ou désactive l'affichage des flèches de sens de courant sur les fils."""
		if self.scene is None:
			return
		if hasattr(self.scene, "toggle_wire_direction"):
			self.scene.toggle_wire_direction()
			return
		if self.app_controller is not None:
			self.app_controller.not_implemented("Direction du courant")

	def set_meter_label_mode(self, mode: str) -> None:
		"""Définit le mode d'affichage des valeurs pour les instruments de mesure.

		Args:
			mode: Mode d'affichage ('voltage', 'current', 'both', 'none').
		"""
		if self.scene is None:
			return
		if hasattr(self.scene, "set_meter_label_mode"):
			self.scene.set_meter_label_mode(mode)

	def toggle_fullscreen(self) -> None:
		"""Bascule la fenêtre principale en mode plein écran."""
		if self.app_controller is not None:
			self.app_controller.toggle_fullscreen()

	def highlight_short_circuit(self) -> None:
		"""Met en évidence les courts-circuits détectés sur le schéma."""
		if self.app_controller is not None:
			self.app_controller.not_implemented("Surlignage court-circuit")
