from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from persistence import serializer, importer, exporter

if TYPE_CHECKING:
    from model.circuit import Circuit


class CircuitIOService:
    """Service d'acces aux modules d'E/S du projet."""

    def __init__(self) -> None:
        self._serializer = serializer
        self._importer = importer
        self._exporter = exporter

    def load_circuit_from_file(self, model: Circuit, path: Path | str) -> None:
        self._serializer.load_circuit_from_file(model, path)

    def save_circuit_to_file(self, model: Circuit, path: Path | str) -> None:
        self._serializer.save_circuit_to_file(model, path)

    def import_circuit(self, model: Circuit, path: Path | str) -> None:
        self._importer.import_circuit(model, path)

    def export_circuit(self, model: Circuit, path: Path | str, simulation_data: dict[str, object] | None = None) -> None:
        self._exporter.export_circuit(model, str(path), simulation_data=simulation_data)

    def export_simulation_results(self, results: dict[str, object], path: Path | str) -> None:
        self._exporter.export_simulation_results_to_file(results, path)

    def export_transient_results_csv(self, results: dict[str, object], path: Path | str) -> None:
        self._exporter.export_transient_results_to_csv(results, path)
