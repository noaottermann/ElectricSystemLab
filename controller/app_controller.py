"""Controleur applicatif principal."""

from __future__ import annotations

from typing import Optional

from PyQt5.QtWidgets import QColorDialog, QMessageBox


class AppController:
	"""Orchestre les interactions UI globales."""

	def __init__(self, window, view=None) -> None:
		self.window = window
		self.view = view

	def set_status(self, message: str, timeout_ms: int = 3000) -> None:
		"""Affiche un message dans la barre de statut."""
		if hasattr(self.window, "status_bar") and self.window.status_bar is not None:
			self.window.status_bar.showMessage(message, timeout_ms)

	def change_language(self, lang: str) -> None:
		"""Change la langue de l'application."""
		if hasattr(self.window, "change_language"):
			self.window.change_language(lang)

	def change_theme(self, theme_name: str) -> None:
		"""Applique un theme visuel."""
		if hasattr(self.window, "change_theme"):
			self.window.change_theme(theme_name)

	def toggle_fullscreen(self) -> None:
		"""Bascule le mode plein ecran."""
		if self.window.isFullScreen():
			self.window.showNormal()
		else:
			self.window.showFullScreen()

	def toggle_components_panel(self) -> None:
		"""Affiche ou masque le panneau des composants."""
		panel = getattr(self.window, "components_panel", None)
		if panel is None:
			return
		panel.setVisible(not panel.isVisible())
		if hasattr(self.window, "_update_toolbar_geometry"):
			self.window._update_toolbar_geometry()

	def toggle_toolbar(self) -> None:
		"""Affiche ou masque la barre d'outils."""
		toolbar = getattr(self.window, "toolbar", None)
		if toolbar is None:
			return
		toolbar.setVisible(not toolbar.isVisible())
		if hasattr(self.window, "_update_toolbar_geometry"):
			self.window._update_toolbar_geometry()

	def change_background_color(self) -> None:
		"""Change la couleur de fond de la vue."""
		if self.view is None:
			return
		color = QColorDialog.getColor(parent=self.window)
		if color.isValid():
			self.view.setBackgroundBrush(color)

	def show_info(self, title: str, message: str) -> None:
		"""Affiche une boite d'information standard."""
		QMessageBox.information(self.window, title, message)

	def not_implemented(self, feature_name: str) -> None:
		"""Signale une fonctionnalite pas encore prise en charge."""
		self.set_status(f"Fonction non implementee: {feature_name}")
