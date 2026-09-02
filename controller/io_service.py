from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from persistence import serializer, importer, exporter

if TYPE_CHECKING:
    from model.circuit import Circuit


class CircuitIOService:
    """Service d'accès et d'orchestration pour les modules d'E/S et de persistance du projet."""

    def __init__(self) -> None:
        """Initialise le service d'E/S avec les modules de persistance sous-jacents."""
        self._serializer = serializer
        self._importer = importer
        self._exporter = exporter

    def load_circuit_from_file(self, model: Circuit, path: Path | str) -> None:
        """Charge la structure d'un circuit depuis un fichier JSON sur disque.

        Args:
            model: Circuit cible à peupler.
            path: Chemin d'accès au fichier à charger.
        """
        self._serializer.load_circuit_from_file(model, path)

    def save_circuit_to_file(self, model: Circuit, path: Path | str) -> None:
        """Sauvegarde la structure d'un circuit dans un fichier JSON sur disque.

        Args:
            model: Circuit à sérialiser.
            path: Chemin cible du fichier.
        """
        self._serializer.save_circuit_to_file(model, path)

    def import_circuit(self, model: Circuit, path: Path | str) -> None:
        """Importe un circuit depuis un fichier externe.

        Args:
            model: Circuit cible à peupler.
            path: Chemin du fichier externe.
        """
        self._importer.import_circuit(model, path)

    def export_circuit(
        self,
        model: Circuit,
        path: Path | str,
        simulation_data: dict[str, object] | None = None,
    ) -> None:
        """Exporte le circuit vers un fichier avec optionnellement des données de simulation.

        Args:
            model: Circuit à exporter.
            path: Chemin cible du fichier exporté.
            simulation_data: Données de simulation additionnelles (optionnel).
        """
        self._exporter.export_circuit(model, str(path), simulation_data=simulation_data)

    def export_simulation_results(self, results: dict[str, object], path: Path | str) -> None:
        """Exporte uniquement les résultats d'une simulation vers un fichier JSON.

        Args:
            results: Dictionnaire contenant les traces et résultats de simulation.
            path: Chemin cible du fichier.
        """
        self._exporter.export_simulation_results_to_file(results, path)

    def export_transient_results_csv(self, results: dict[str, object], path: Path | str) -> None:
        """Exporte les données d'analyse transitoire au format tableau CSV.

        Args:
            results: Dictionnaire contenant l'axe temporel et les séries de potentiel/courant.
            path: Chemin cible du fichier CSV.
        """
        self._exporter.export_transient_results_to_csv(results, path)
