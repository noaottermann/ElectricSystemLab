"""
Dialogues pour l'édition des composants et dipôles du circuit.
"""

from __future__ import annotations

from typing import Any, Optional

from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from utils.translator import Translator


class EditStateDialog(QDialog):
    """Dialogue pour modifier l'état d'un dipôle à variantes."""

    def __init__(self, component: Any, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.component = component
        self.setWindowTitle(f"{Translator.tr('dialog_edit_value_title')} - {component.name}")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        layout.addLayout(form_layout)

        self.state_input = QComboBox(self)
        for val, label in self.component.get_state_options():
            self.state_input.addItem(label, val)
        idx = self.state_input.findData(self.component.get_state())
        if idx != -1:
            self.state_input.setCurrentIndex(idx)
        form_layout.addRow(Translator.tr("dialog_edit_value_state"), self.state_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_selected_state(self) -> str:
        """Retourne l'état choisi."""
        return str(self.state_input.currentData())


class EditValueDialog(QDialog):
    """Dialogue pour modifier la valeur principale et l'état d'un dipôle."""

    def __init__(
        self,
        component: Any,
        current_value: float,
        unit: str = "",
        allow_unbounded: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.component = component
        self.current_value = float(current_value)
        self.unit = unit
        self.allow_unbounded = allow_unbounded
        self.setWindowTitle(f"{Translator.tr('dialog_edit_value_title')} - {component.name}")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        layout.addLayout(form_layout)

        self.state_input: Optional[QComboBox] = None
        if hasattr(self.component, "get_state_options") and self.component.get_state_options():
            self.state_input = QComboBox(self)
            for val, label in self.component.get_state_options():
                self.state_input.addItem(label, val)
            idx = self.state_input.findData(self.component.get_state())
            if idx != -1:
                self.state_input.setCurrentIndex(idx)
            form_layout.addRow(Translator.tr("dialog_edit_value_state"), self.state_input)

        self.value_input = QDoubleSpinBox(self)
        min_v = -1e12 if self.allow_unbounded else -1e9
        max_v = 1e12 if self.allow_unbounded else 1e9
        self.value_input.setRange(min_v, max_v)
        self.value_input.setDecimals(6)
        self.value_input.setValue(self.current_value)
        label_text = f"{Translator.tr('dialog_edit_value_label')} ({self.unit})" if self.unit else Translator.tr("dialog_edit_value_label")
        form_layout.addRow(label_text, self.value_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_value(self) -> float:
        """Retourne la valeur numérique saisie."""
        return float(self.value_input.value())

    def get_state(self) -> Optional[str]:
        """Retourne l'état choisi ou None."""
        if self.state_input is not None:
            return str(self.state_input.currentData())
        return None
