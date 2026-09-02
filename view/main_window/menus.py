"""
Constructeur des menus de l'application Nodal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PyQt5.QtWidgets import QMenu, QMenuBar
from utils.translator import Translator

if TYPE_CHECKING:
    from view.main_window.actions import ActionManager


class MenuBuilder:
    """Construit et gère la barre de menus de la fenêtre principale."""

    def __init__(self, menu_bar: QMenuBar, action_manager: ActionManager) -> None:
        self.menu_bar = menu_bar
        self.actions = action_manager
        self.menu_file: Optional[QMenu] = None
        self.menu_edit: Optional[QMenu] = None
        self.menu_view: Optional[QMenu] = None
        self.menu_simulation: Optional[QMenu] = None
        self.menu_options: Optional[QMenu] = None
        self.menu_help: Optional[QMenu] = None

    def build_menus(self) -> None:
        """Construit l'ensemble des menus standards."""
        self.menu_bar.clear()

        # Fichier
        self.menu_file = self.menu_bar.addMenu(Translator.tr("menu_file") if Translator.has_key("menu_file") else "Fichier")
        self._add_action_to_menu(self.menu_file, "action_new")
        self._add_action_to_menu(self.menu_file, "action_open")
        self._add_action_to_menu(self.menu_file, "action_save")
        self._add_action_to_menu(self.menu_file, "action_save_as")
        self.menu_file.addSeparator()
        self._add_action_to_menu(self.menu_file, "action_import")
        self._add_action_to_menu(self.menu_file, "action_export")
        self._add_action_to_menu(self.menu_file, "action_export_results")
        self._add_action_to_menu(self.menu_file, "action_export_csv")

        # Edition
        self.menu_edit = self.menu_bar.addMenu(Translator.tr("menu_edit") if Translator.has_key("menu_edit") else "Édition")
        self._add_action_to_menu(self.menu_edit, "action_undo")
        self._add_action_to_menu(self.menu_edit, "action_redo")
        self.menu_edit.addSeparator()
        self._add_action_to_menu(self.menu_edit, "action_cut")
        self._add_action_to_menu(self.menu_edit, "action_copy")
        self._add_action_to_menu(self.menu_edit, "action_paste")
        self._add_action_to_menu(self.menu_edit, "action_delete")
        self._add_action_to_menu(self.menu_edit, "action_rotate")

        # Affichage
        self.menu_view = self.menu_bar.addMenu(Translator.tr("menu_view") if Translator.has_key("menu_view") else "Affichage")
        self._add_action_to_menu(self.menu_view, "action_zoom_in")
        self._add_action_to_menu(self.menu_view, "action_zoom_out")
        self._add_action_to_menu(self.menu_view, "action_zoom_reset")
        self.menu_view.addSeparator()
        self._add_action_to_menu(self.menu_view, "action_toggle_grid")
        self._add_action_to_menu(self.menu_view, "action_toggle_snap")

        # Simulation
        self.menu_simulation = self.menu_bar.addMenu(Translator.tr("menu_simulation") if Translator.has_key("menu_simulation") else "Simulation")
        self._add_action_to_menu(self.menu_simulation, "action_run_dc")
        self._add_action_to_menu(self.menu_simulation, "action_run_ac")
        self._add_action_to_menu(self.menu_simulation, "action_run_transient")
        self._add_action_to_menu(self.menu_simulation, "action_stop_simulation")

        # Options / Aide
        self.menu_options = self.menu_bar.addMenu(Translator.tr("menu_options") if Translator.has_key("menu_options") else "Options")
        self._add_action_to_menu(self.menu_options, "action_preferences")

        self.menu_help = self.menu_bar.addMenu(Translator.tr("menu_help") if Translator.has_key("menu_help") else "Aide")
        self._add_action_to_menu(self.menu_help, "action_about")

    def _add_action_to_menu(self, menu: QMenu, action_name: str) -> None:
        action = self.actions.get_action(action_name)
        if action is not None:
            menu.addAction(action)
