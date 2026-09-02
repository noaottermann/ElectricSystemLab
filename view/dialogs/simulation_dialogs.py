"""
Dialogues de paramétrage des simulations (DC, AC, Transitoire).
"""

from __future__ import annotations

from typing import Optional

from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from config.constants import SIMULATION
from utils.translator import Translator


class ACSweepDialog(QDialog):
    """Dialogue de configuration pour le balayage harmonique AC."""

    def __init__(
        self,
        start_freq: float = SIMULATION.AC_START_FREQ,
        stop_freq: float = SIMULATION.AC_STOP_FREQ,
        points: int = SIMULATION.AC_POINTS,
        sweep_type: str = "log",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(Translator.tr("dialog_ac_sweep_title") if Translator.has_key("dialog_ac_sweep_title") else "Paramètres Analyse AC")
        self._start_freq = start_freq
        self._stop_freq = stop_freq
        self._points = points
        self._sweep_type = sweep_type
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        layout.addLayout(form_layout)

        self.start_input = QDoubleSpinBox(self)
        self.start_input.setRange(1e-3, 1e12)
        self.start_input.setDecimals(3)
        self.start_input.setValue(self._start_freq)
        form_layout.addRow("Fréquence de départ (Hz) :", self.start_input)

        self.stop_input = QDoubleSpinBox(self)
        self.stop_input.setRange(1e-3, 1e12)
        self.stop_input.setDecimals(3)
        self.stop_input.setValue(self._stop_freq)
        form_layout.addRow("Fréquence de fin (Hz) :", self.stop_input)

        self.points_input = QSpinBox(self)
        self.points_input.setRange(2, 100000)
        self.points_input.setValue(self._points)
        form_layout.addRow("Nombre de points :", self.points_input)

        self.sweep_combo = QComboBox(self)
        self.sweep_combo.addItem("Logarithmique", "log")
        self.sweep_combo.addItem("Linéaire", "linear")
        idx = self.sweep_combo.findData(self._sweep_type)
        if idx != -1:
            self.sweep_combo.setCurrentIndex(idx)
        form_layout.addRow("Type d'échelle :", self.sweep_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_params(self) -> dict[str, object]:
        return {
            "start_freq": float(self.start_input.value()),
            "stop_freq": float(self.stop_input.value()),
            "points": int(self.points_input.value()),
            "sweep": str(self.sweep_combo.currentData()),
        }


class TransientDialog(QDialog):
    """Dialogue de configuration pour la simulation transitoire."""

    def __init__(
        self,
        duration: float = SIMULATION.TRANSIENT_DURATION,
        time_step: float = SIMULATION.TRANSIENT_TIME_STEP,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(Translator.tr("dialog_transient_title") if Translator.has_key("dialog_transient_title") else "Paramètres Analyse Transitoire")
        self._duration = duration
        self._time_step = time_step
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        layout.addLayout(form_layout)

        self.duration_input = QDoubleSpinBox(self)
        self.duration_input.setRange(1e-9, 1000.0)
        self.duration_input.setDecimals(6)
        self.duration_input.setValue(self._duration)
        form_layout.addRow("Durée (s) :", self.duration_input)

        self.step_input = QDoubleSpinBox(self)
        self.step_input.setRange(1e-12, 100.0)
        self.step_input.setDecimals(8)
        self.step_input.setValue(self._time_step)
        form_layout.addRow("Pas de temps (s) :", self.step_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_params(self) -> dict[str, float]:
        return {
            "duration": float(self.duration_input.value()),
            "time_step": float(self.step_input.value()),
        }
