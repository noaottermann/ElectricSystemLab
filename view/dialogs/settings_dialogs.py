"""
Dialogues pour les paramètres et préférences d'application.
"""

from __future__ import annotations

from typing import Optional

from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QVBoxLayout,
    QWidget,
)
from utils.translator import Translator


class PreferencesDialog(QDialog):
    """Dialogue des préférences utilisateur (langue, thème, grille)."""

    def __init__(self, current_lang: str = "fr", current_theme: str = "light", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Préférences")
        self._lang = current_lang
        self._theme = current_theme
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.lang_combo = QComboBox(self)
        self.lang_combo.addItem("Français", "fr")
        self.lang_combo.addItem("English", "en")
        idx_lang = self.lang_combo.findData(self._lang)
        if idx_lang != -1:
            self.lang_combo.setCurrentIndex(idx_lang)
        form.addRow("Langue :", self.lang_combo)

        self.theme_combo = QComboBox(self)
        self.theme_combo.addItem("Clair", "light")
        self.theme_combo.addItem("Sombre", "dark")
        idx_th = self.theme_combo.findData(self._theme)
        if idx_th != -1:
            self.theme_combo.setCurrentIndex(idx_th)
        form.addRow("Thème :", self.theme_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_selected_language(self) -> str:
        return str(self.lang_combo.currentData())

    def get_selected_theme(self) -> str:
        return str(self.theme_combo.currentData())
