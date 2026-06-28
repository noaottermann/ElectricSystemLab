from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

from controller.io_service import CircuitIOService
from controller.ui_callbacks import UICallbacks, MessageType

if TYPE_CHECKING:
    from model.circuit import Circuit


class FileController:
	"""Gère l'ouverture et la sauvegarde des circuits."""

	def __init__(self, model: Circuit, ui_callbacks: UICallbacks, io_service: CircuitIOService | None = None) -> None:
		"""
		Initialise le contrôleur de fichiers.
		
		Args:
			model: Le modèle du circuit
			ui_callbacks: Interface de communication avec la Vue
			io_service: Service d'accès aux modules d'E/S
		"""
		self.model = model
		self.ui_callbacks = ui_callbacks
		self.current_path: Optional[Path] = None
		self.recent_files: list[Path] = []
		self._io_service = io_service or CircuitIOService()

	def new_circuit(self) -> None:
		"""Crée un nouveau circuit vide."""
		if self.model is None:
			return
		self.model.clear()
		self.ui_callbacks.refresh_scene_from_model()
		self.current_path = None
		self.ui_callbacks.set_current_filename(None)
		self._status("Nouveau circuit")

	def open_circuit_from_path(self, path: Path | str) -> bool:
		"""Charge un circuit depuis un chemin fourni."""
		try:
			self._io_service.load_circuit_from_file(self.model, Path(path))
		except Exception as exc:
			self.ui_callbacks.show_message(
				"Erreur",
				f"Impossible d'ouvrir le fichier.\n{exc}",
				MessageType.ERROR,
			)
			return False
		self.ui_callbacks.refresh_scene_from_model()
		resolved = Path(path)
		self._set_current_path(resolved)
		self._status(f"Fichier ouvert: {resolved.name}")
		return True

	def save_circuit(self) -> bool:
		"""Sauvegarde le circuit courant."""
		if self.current_path is None:
			return False
		return self.save_circuit_to_path(self.current_path)

	def save_circuit_to_path(self, path: Path | str) -> bool:
		"""Sauvegarde le circuit vers un chemin fourni."""
		resolved = Path(path)
		if resolved.suffix.lower() != ".json":
			resolved = resolved.with_suffix(".json")
		try:
			self._io_service.save_circuit_to_file(self.model, resolved)
		except Exception as exc:
			self.ui_callbacks.show_message(
				"Erreur",
				f"Impossible de sauvegarder.\n{exc}",
				MessageType.ERROR,
			)
			return False
		self._set_current_path(resolved)
		self._status(f"Sauvegarde: {resolved.name}")
		return True

	def import_circuit_from_path(self, path: Path | str) -> bool:
		"""Importe un circuit depuis un chemin fourni."""
		try:
			self._io_service.import_circuit(self.model, Path(path))
		except Exception as exc:
			self.ui_callbacks.show_message(
				"Erreur",
				f"Import impossible.\n{exc}",
				MessageType.ERROR,
			)
			return False
		self.ui_callbacks.refresh_scene_from_model()
		self._set_current_path(Path(path))
		self._status("Import terminé")
		return True

	def export_circuit_to_path(self, path: Path | str, simulation_data: dict[str, Any] | None = None) -> bool:
		"""Exporte le circuit courant."""
		resolved = Path(path)
		if resolved.suffix.lower() != ".json":
			resolved = resolved.with_suffix(".json")
		try:
			self._io_service.export_circuit(self.model, resolved, simulation_data=simulation_data)
		except Exception as exc:
			self.ui_callbacks.show_message(
				"Erreur",
				f"Export impossible.\n{exc}",
				MessageType.ERROR,
			)
			return False
		self._set_current_path(resolved)
		self._status(f"Export: {resolved.name}")
		return True

	def build_fallback_simulation_results(self) -> dict[str, Any]:
		"""Construit un résumé DC pour export de résultats quand aucun transitoire n'existe."""
		return {
			"dc": {
				"dipoles": [
					{
						"id": dipole.id,
						"type": dipole.__class__.__name__,
						"voltage": dipole.voltage,
						"current": dipole.current,
					}
					for dipole in sorted(self.model.dipoles.values(), key=lambda d: d.id)
				],
			}
		}

	def export_simulation_results_to_path(self, path: Path | str, result: dict[str, Any]) -> bool:
		"""Exporte uniquement les résultats de simulation."""
		resolved = Path(path)
		if resolved.suffix.lower() != ".json":
			resolved = resolved.with_suffix(".json")
		try:
			self._io_service.export_simulation_results(result, resolved)
		except Exception as exc:
			self.ui_callbacks.show_message(
				"Erreur",
				f"Export des résultats impossible.\n{exc}",
				MessageType.ERROR,
			)
			return False
		self._status(f"Résultats exportés: {resolved.name}")
		return True

	def export_transient_results_csv_to_path(self, path: Path | str, result: dict[str, Any] | None) -> bool:
		"""Exporte les traces transitoires dans un fichier CSV."""
		if not result:
			self.ui_callbacks.show_message(
				"Erreur",
				"Aucune simulation transitoire disponible.",
				MessageType.ERROR,
			)
			return False
		resolved = Path(path)
		if resolved.suffix.lower() != ".csv":
			resolved = resolved.with_suffix(".csv")
		try:
			self._io_service.export_transient_results_csv(result, resolved)
		except Exception as exc:
			self.ui_callbacks.show_message(
				"Erreur",
				f"Export CSV impossible.\n{exc}",
				MessageType.ERROR,
			)
			return False
		self._status(f"CSV exporte: {resolved.name}")
		return True

	def _set_current_path(self, path: Path) -> None:
		"""Met à jour le chemin courant et la liste des récents."""
		self.current_path = path
		self._push_recent(path)
		self.ui_callbacks.set_current_filename(path.name)

	def _push_recent(self, path: Path) -> None:
		"""Enregistre un fichier récent."""
		path = path.resolve()
		self.recent_files = [p for p in self.recent_files if p != path]
		self.recent_files.insert(0, path)
		self.recent_files = self.recent_files[:10]

	def _status(self, message: str) -> None:
		"""Affiche un message de statut dans la fenêtre."""
		self.ui_callbacks.set_status_message(message, 3000)

