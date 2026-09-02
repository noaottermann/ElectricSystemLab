"""
Gestionnaire des actions (QAction) et raccourcis pour la fenêtre principale.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import QAction, QMainWindow, QWidget
from utils.translator import Translator

if TYPE_CHECKING:
    from view.main_window import MainWindow


class ActionManager:
    """Crée et gère le dictionnaire d'actions QAction pour MainWindow."""

    def __init__(self, main_window: QMainWindow) -> None:
        self.window = main_window
        self.actions: dict[str, QAction] = {}

    def create_action(
        self,
        name: str,
        icon: Optional[QIcon] = None,
        callback: Optional[Callable[..., None]] = None,
        shortcut: Optional[str | QKeySequence] = None,
        checkable: bool = False,
    ) -> QAction:
        """Crée et enregistre une QAction."""
        action = QAction(self.window)
        if icon is not None:
            action.setIcon(icon)
        if callback is not None:
            action.triggered.connect(callback)
        if shortcut is not None:
            action.setShortcut(QKeySequence(shortcut) if isinstance(shortcut, str) else shortcut)
        action.setCheckable(checkable)
        self.actions[name] = action
        return action

    def get_action(self, name: str) -> Optional[QAction]:
        """Récupère une action par son identifiant."""
        return self.actions.get(name)

    def retranslate_actions(self) -> None:
        """Met à jour les libellés de toutes les actions selon la langue active."""
        for name, action in self.actions.items():
            trans_key = name.lower()
            if not trans_key.startswith("action_"):
                trans_key = f"action_{trans_key}"
            if Translator.has_key(trans_key):
                action.setText(Translator.tr(trans_key))
