"""Controleur des operations fichier."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Optional

from PyQt5.QtWidgets import QFileDialog, QMessageBox


def _load_project_io_modules() -> tuple[object, object, object]:
	"""Charge les modules io du projet sans conflit avec le module standard io."""
	project_root = Path(__file__).resolve().parents[1]
	io_dir = project_root / "io"

	pkg_name = "project_io"
	if pkg_name not in sys.modules:
		pkg_spec = importlib.util.spec_from_file_location(
			pkg_name,
			io_dir / "__init__.py",
			submodule_search_locations=[str(io_dir)],
		)
		pkg_module = importlib.util.module_from_spec(pkg_spec)
		sys.modules[pkg_name] = pkg_module
		pkg_spec.loader.exec_module(pkg_module)

	def _load_module(module_name: str):
		full_name = f"{pkg_name}.{module_name}"
		if full_name in sys.modules:
			return sys.modules[full_name]
		module_spec = importlib.util.spec_from_file_location(full_name, io_dir / f"{module_name}.py")
		module = importlib.util.module_from_spec(module_spec)
		sys.modules[full_name] = module
		module_spec.loader.exec_module(module)
		return module

	serializer_module = _load_module("serializer")
	importer_module = _load_module("importer")
	exporter_module = _load_module("exporter")
	return serializer_module, importer_module, exporter_module


class FileController:
	"""Gere l'ouverture et la sauvegarde des circuits."""

	def __init__(self, window, model, scene) -> None:
		self.window = window
		self.model = model
		self.scene = scene
		self.current_path: Optional[Path] = None
		self.recent_files: list[Path] = []
		self._serializer, self._importer, self._exporter = _load_project_io_modules()

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
			self._serializer.load_circuit_from_file(self.model, path)
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
			self._serializer.save_circuit_to_file(self.model, self.current_path)
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
			self._importer.import_circuit(self.model, path)
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

		simulation_data = None
		if getattr(self.window, "include_simulation_in_export", False):
			simulation_controller = getattr(self.window, "simulation_controller", None)
			if simulation_controller is not None:
				simulation_data = getattr(simulation_controller, "last_transient_result", None)
		try:
			self._exporter.export_circuit(self.model, path, simulation_data=simulation_data)
		except Exception as exc:
			QMessageBox.warning(self.window, "Erreur", f"Export impossible.\n{exc}")
			return
		self._status(f"Export: {Path(path).with_suffix('.json').name}")

	def export_simulation_results(self) -> None:
		"""Exporte uniquement les resultats de simulation."""
		path, _ = QFileDialog.getSaveFileName(
			self.window,
			"Exporter les resultats de simulation",
			"",
			"Nodal (*.json);;Tous les fichiers (*.*)",
		)
		if not path:
			return

		simulation_controller = getattr(self.window, "simulation_controller", None)
		if simulation_controller is None:
			QMessageBox.warning(self.window, "Erreur", "Aucun controleur de simulation disponible.")
			return

		result = getattr(simulation_controller, "last_transient_result", None)
		if not result:
			# Fallback: resume l'etat courant du circuit comme resultats DC.
			result = {
				"dc": {
					"nodes": [
						{
							"id": node.id,
							"potential": node.potential,
							"is_ground": node.is_ground,
						}
						for node in sorted(self.model.nodes.values(), key=lambda n: n.id)
					],
					"dipoles": [
						{
							"id": dipole.id,
							"type": dipole.__class__.__name__,
							"current": dipole.current,
							"voltage": dipole.voltage,
						}
						for dipole in sorted(self.model.dipoles.values(), key=lambda d: d.id)
					],
				}
			}

		try:
			self._exporter.export_simulation_results_to_file(result, path)
		except Exception as exc:
			QMessageBox.warning(self.window, "Erreur", f"Export des resultats impossible.\n{exc}")
			return
		self._status(f"Resultats exportes: {Path(path).with_suffix('.json').name}")

	def export_transient_results_csv(self) -> None:
		"""Exporte les traces transitoires dans un fichier CSV."""
		path, _ = QFileDialog.getSaveFileName(
			self.window,
			"Exporter les traces transitoires",
			"",
			"CSV (*.csv);;Tous les fichiers (*.*)",
		)
		if not path:
			return

		simulation_controller = getattr(self.window, "simulation_controller", None)
		if simulation_controller is None:
			QMessageBox.warning(self.window, "Erreur", "Aucun controleur de simulation disponible.")
			return

		result = getattr(simulation_controller, "last_transient_result", None)
		if not result:
			QMessageBox.warning(self.window, "Erreur", "Aucune simulation transitoire disponible.")
			return

		try:
			self._exporter.export_transient_results_to_csv(result, path)
		except Exception as exc:
			QMessageBox.warning(self.window, "Erreur", f"Export CSV impossible.\n{exc}")
			return
		self._status(f"CSV exporte: {Path(path).with_suffix('.csv').name}")

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

