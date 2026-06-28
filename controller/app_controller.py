from __future__ import annotations

from typing import TYPE_CHECKING, Any

from controller.ui_callbacks import UICallbacks, MessageType

if TYPE_CHECKING:
    from view.main_window import MainWindow


class AppController:
	"""Orchestre les intéractions UI globales."""

	def __init__(self, ui_callbacks: UICallbacks, view: MainWindow | None = None) -> None:
		"""Initialise le contrôleur."""
		self.ui_callbacks = ui_callbacks
		self.view = view

	def set_status(self, message: str, timeout_ms: int = 3000) -> None:
		"""Affiche un message dans la barre de statut."""
		self.ui_callbacks.set_status_message(message, timeout_ms)

	def change_language(self, lang: str) -> None:
		"""Change la langue de l'application."""
		pass

	def change_theme(self, theme_name: str) -> None:
		"""Applique un thème visuel."""
		# Cette méthode doit être appelée via les signaux de main_window
		pass

	def toggle_fullscreen(self) -> None:
		"""Bascule le mode plein écran."""
		# Cette méthode doit être appelée via les signaux de main_window
		pass

	def toggle_components_panel(self) -> None:
		"""Affiche ou masque le panneau des composants."""
		# Cette méthode doit être appelée via les signaux de main_window
		pass

	def toggle_toolbar(self) -> None:
		"""Affiche ou masque la barre d'outils."""
		# Cette méthode doit être appelée via les signaux de main_window
		pass

	def change_background_color(self) -> None:
		"""Change la couleur de fond de la vue."""
		color = self.ui_callbacks.pick_color()
		if color is not None:
			self.ui_callbacks.apply_view_background_color(color)

	def show_info(self, title: str, message: str) -> None:
		"""Affiche une boîte d'information standard."""
		self.ui_callbacks.show_message(title, message, MessageType.INFO)

	def show_warning(self, title: str, message: str) -> None:
		"""Affiche une boîte d'avertissement."""
		self.ui_callbacks.show_message(title, message, MessageType.WARNING)

	def show_error(self, title: str, message: str) -> None:
		"""Affiche une boîte d'erreur."""
		self.ui_callbacks.show_message(title, message, MessageType.ERROR)

	def not_implemented(self, feature_name: str) -> None:
		"""Signale une fonctionnalité pas encore prise en charge."""
		self.set_status(f"Fonction non implementee: {feature_name}")
