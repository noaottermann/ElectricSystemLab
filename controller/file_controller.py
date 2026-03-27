"""Controleur des operations fichier."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import QFileDialog, QMessageBox

from model.components import Capacitor, Inductor, Resistor, VoltageSourceAC, VoltageSourceDC


class FileController:
	"""Gere l'ouverture et la sauvegarde des circuits."""

	def __init__(self, window, model, scene) -> None:
		self.window = window
		self.model = model
		self.scene = scene
		self.current_path: Optional[Path] = None
		self.recent_files: list[Path] = []

	def new_circuit(self) -> None:
		"""Cree un nouveau circuit vide."""
		if self.model is None:
			return
		self.model.clear()
		if self.scene is not None:
			self.scene.refresh_from_model()
		self.current_path = None
		self._status("Nouveau circuit")

	def open_circuit(self) -> None:
		"""Ouvre un circuit depuis un fichier."""
		path, _ = QFileDialog.getOpenFileName(
			self.window,
			"Ouvrir un circuit",
			"",
			"Nodal (*.json);;Tous les fichiers (*.*)",
		)
		if not path:
			return
		self.open_circuit_from_path(Path(path))

	def open_circuit_from_path(self, path: Path) -> None:
		"""Charge un circuit depuis un chemin fourni."""
		try:
			json_str = Path(path).read_text(encoding="utf-8")
			self.model.load_from_json(json_str, self._component_class_map())
		except Exception as exc:
			QMessageBox.warning(self.window, "Erreur", f"Impossible d'ouvrir le fichier.\n{exc}")
			return
		if self.scene is not None:
			self.scene.refresh_from_model()
		self._set_current_path(path)
		self._status(f"Fichier ouvert: {path.name}")

	def save_circuit(self) -> None:
		"""Sauvegarde le circuit courant."""
		if self.current_path is None:
			self.save_circuit_as()
			return
		try:
			json_str = self.model.to_json()
			Path(self.current_path).write_text(json_str, encoding="utf-8")
		except Exception as exc:
			QMessageBox.warning(self.window, "Erreur", f"Impossible de sauvegarder.\n{exc}")
			return
		self._status(f"Sauvegarde: {self.current_path.name}")

	def save_circuit_as(self) -> None:
		"""Sauvegarde sous un nouveau nom."""
		path, _ = QFileDialog.getSaveFileName(
			self.window,
			"Enregistrer le circuit",
			"",
			"Nodal (*.json);;Tous les fichiers (*.*)",
		)
		if not path:
			return
		resolved = Path(path)
		if resolved.suffix.lower() != ".json":
			resolved = resolved.with_suffix(".json")
		self.current_path = resolved
		self.save_circuit()

	def import_circuit(self) -> None:
		"""Importe un circuit depuis un fichier externe."""
		path, _ = QFileDialog.getOpenFileName(
			self.window,
			"Importer un circuit",
			"",
			"Nodal (*.json);;Tous les fichiers (*.*)",
		)
		if not path:
			return
		try:
			json_str = Path(path).read_text(encoding="utf-8")
			self.model.load_from_json(json_str, self._component_class_map())
		except Exception as exc:
			QMessageBox.warning(self.window, "Erreur", f"Import impossible.\n{exc}")
			return
		if self.scene is not None:
			self.scene.refresh_from_model()
		self._status("Import termine")

	def export_circuit(self) -> None:
		"""Exporte le circuit courant."""
		path, _ = QFileDialog.getSaveFileName(
			self.window,
			"Exporter le circuit",
			"",
			"Nodal (*.json);;Tous les fichiers (*.*)",
		)
		if not path:
			return
		resolved = Path(path)
		if resolved.suffix.lower() != ".json":
			resolved = resolved.with_suffix(".json")
		try:
			json_str = self.model.to_json()
			resolved.write_text(json_str, encoding="utf-8")
		except Exception as exc:
			QMessageBox.warning(self.window, "Erreur", f"Export impossible.\n{exc}")
			return
		self._status(f"Export: {resolved.name}")

	def _set_current_path(self, path: Path) -> None:
		"""Met a jour le chemin courant et la liste des recents."""
		self.current_path = path
		self._push_recent(path)

	def _push_recent(self, path: Path) -> None:
		"""Enregistre un fichier recent en evitant les doublons."""
		path = path.resolve()
		self.recent_files = [p for p in self.recent_files if p != path]
		self.recent_files.insert(0, path)
		self.recent_files = self.recent_files[:10]

	def _status(self, message: str) -> None:
		"""Affiche un message de statut dans la fenetre."""
		if hasattr(self.window, "status_bar") and self.window.status_bar is not None:
			self.window.status_bar.showMessage(message, 3000)

	def _component_class_map(self) -> dict[str, type]:
		"""Mappe les types de composant vers leurs classes."""
		return {
			"Resistor": Resistor,
			"VoltageSourceDC": VoltageSourceDC,
			"VoltageSourceAC": VoltageSourceAC,
			"Capacitor": Capacitor,
			"Inductor": Inductor,
		}
