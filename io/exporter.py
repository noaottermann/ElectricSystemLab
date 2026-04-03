"""Utilitaires d'export pour les fichiers de circuit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, Union

from model.circuit import Circuit
from .serializer import save_circuit_to_file


def export_circuit(
	circuit: Circuit,
	path: Union[Path, str],
	simulation_data: Optional[dict[str, Any]] = None,
) -> None:
	"""Exporte un circuit vers un fichier."""
	file_path = Path(path)
	if file_path.suffix.lower() != ".json":
		raise ValueError("Format non pris en charge (attendu .json).")
	if simulation_data is None:
		save_circuit_to_file(circuit, file_path)
		return

	payload = json.loads(circuit.to_json())
	payload["simulation"] = simulation_data
	file_path.write_text(json.dumps(payload, indent=4), encoding="utf-8")


def export_simulation_results_to_file(results: dict[str, Any], path: Union[Path, str]) -> None:
	"""Exporte uniquement les resultats de simulation vers un fichier JSON."""
	file_path = Path(path)
	if file_path.suffix.lower() != ".json":
		raise ValueError("Format non pris en charge (attendu .json).")
	payload = {
		"type": "simulation_results",
		**results,
	}
	file_path.write_text(json.dumps(payload, indent=4), encoding="utf-8")
