"""
Constructeur des barres d'outils de l'application Nodal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QMainWindow, QToolBar
from config.constants import UI

if TYPE_CHECKING:
    from view.main_window.actions import ActionManager


class ToolbarBuilder:
    """Construit les barres d'outils de la fenêtre principale."""

    def __init__(self, main_window: QMainWindow, action_manager: ActionManager) -> None:
        self.window = main_window
        self.actions = action_manager
        self.main_toolbar: Optional[QToolBar] = None
        self.sim_toolbar: Optional[QToolBar] = None

    def build_main_toolbar(self) -> QToolBar:
        """Construit la barre d'outils principale."""
        toolbar = QToolBar("Barre Principale", self.window)
        toolbar.setIconSize(QSize(UI.BUTTON_SIZE, UI.BUTTON_SIZE))
        self.window.addToolBar(toolbar)

        action_names = [
            "action_new", "action_open", "action_save", None,
            "action_undo", "action_redo", None,
            "action_cut", "action_copy", "action_paste", "action_delete", "action_rotate", None,
            "action_zoom_in", "action_zoom_out", "action_zoom_reset",
        ]

        for name in action_names:
            if name is None:
                toolbar.addSeparator()
            else:
                act = self.actions.get_action(name)
                if act is not None:
                    toolbar.addAction(act)

        self.main_toolbar = toolbar
        return toolbar

    def build_simulation_toolbar(self) -> QToolBar:
        """Construit la barre d'outils de simulation."""
        toolbar = QToolBar("Barre de Simulation", self.window)
        toolbar.setIconSize(QSize(UI.BUTTON_SIZE, UI.BUTTON_SIZE))
        self.window.addToolBar(toolbar)

        sim_actions = [
            "action_run_dc", "action_run_ac", "action_run_transient", None,
            "action_stop_simulation",
        ]

        for name in sim_actions:
            if name is None:
                toolbar.addSeparator()
            else:
                act = self.actions.get_action(name)
                if act is not None:
                    toolbar.addAction(act)

        self.sim_toolbar = toolbar
        return toolbar
