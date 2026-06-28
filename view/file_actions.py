from __future__ import annotations

from typing import Any

from PyQt5.QtWidgets import QFileDialog, QMessageBox


def open_circuit_dialog(window, file_controller) -> None:
    path, _ = QFileDialog.getOpenFileName(
        window,
        "Ouvrir un circuit",
        "",
        "Nodal (*.json);;Tous les fichiers (*.*)",
    )
    if path:
        file_controller.open_circuit_from_path(path)


def save_circuit_as_dialog(window, file_controller) -> None:
    path, _ = QFileDialog.getSaveFileName(
        window,
        "Enregistrer le circuit",
        "",
        "Nodal (*.json);;Tous les fichiers (*.*)",
    )
    if path:
        file_controller.save_circuit_to_path(path)


def import_circuit_dialog(window, file_controller) -> None:
    path, _ = QFileDialog.getOpenFileName(
        window,
        "Importer un circuit",
        "",
        "Nodal (*.json);;Tous les fichiers (*.*)",
    )
    if path:
        file_controller.import_circuit_from_path(path)


def export_circuit_dialog(window, file_controller, simulation_data: dict[str, Any] | None = None) -> None:
    path, _ = QFileDialog.getSaveFileName(
        window,
        "Exporter le circuit",
        "",
        "Nodal (*.json);;Tous les fichiers (*.*)",
    )
    if path:
        file_controller.export_circuit_to_path(path, simulation_data=simulation_data)


def export_simulation_results_dialog(window, file_controller, simulation_controller) -> None:
    path, _ = QFileDialog.getSaveFileName(
        window,
        "Exporter les résultats de simulation",
        "",
        "Nodal (*.json);;Tous les fichiers (*.*)",
    )
    if not path:
        return
    if simulation_controller is None:
        QMessageBox.warning(window, "Erreur", "Aucun contrôleur de simulation disponible.")
        return
    result = getattr(simulation_controller, "last_transient_result", None)
    if not result:
        result = file_controller.build_fallback_simulation_results()
    file_controller.export_simulation_results_to_path(path, result)


def export_transient_csv_dialog(window, file_controller, simulation_controller) -> None:
    path, _ = QFileDialog.getSaveFileName(
        window,
        "Exporter les traces transitoires",
        "",
        "CSV (*.csv);;Tous les fichiers (*.*)",
    )
    if not path:
        return
    if simulation_controller is None:
        QMessageBox.warning(window, "Erreur", "Aucun contrôleur de simulation disponible.")
        return
    result = getattr(simulation_controller, "last_transient_result", None)
    file_controller.export_transient_results_csv_to_path(path, result)
