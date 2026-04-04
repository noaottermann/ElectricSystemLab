"""Utilitaires d'export pour les fichiers de circuit."""

from __future__ import annotations

import json
import csv
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


def export_transient_results_to_csv(results: dict[str, Any], path: Union[Path, str]) -> None:
	"""Exporte les traces transitoires vers un fichier CSV plat."""
	file_path = Path(path)
	if file_path.suffix.lower() != ".csv":
		raise ValueError("Format non pris en charge (attendu .csv).")

	time_values = list(results.get("time", []))
	dipole_voltages = results.get("dipole_voltages", {}) or results.get("node_potentials", {}) or {}
	dipole_currents = results.get("dipole_currents", {}) or {}

	columns = ["time"]
	voltage_keys = sorted(dipole_voltages.keys(), key=lambda key: str(key))
	dipole_keys = sorted(dipole_currents.keys(), key=lambda key: str(key))
	columns.extend([f"dipole_voltage_{key}" for key in voltage_keys])
	columns.extend([f"dipole_{key}" for key in dipole_keys])

	row_count = len(time_values)
	for values in list(dipole_voltages.values()) + list(dipole_currents.values()):
		row_count = max(row_count, len(values))

	with file_path.open("w", newline="", encoding="utf-8") as handle:
		writer = csv.DictWriter(handle, fieldnames=columns)
		writer.writeheader()
		for index in range(row_count):
			row: dict[str, Any] = {column: "" for column in columns}
			if index < len(time_values):
				row["time"] = time_values[index]
			for key in voltage_keys:
				values = dipole_voltages.get(key, [])
				if index < len(values):
					row[f"dipole_voltage_{key}"] = values[index]
			for key in dipole_keys:
				values = dipole_currents.get(key, [])
				if index < len(values):
					row[f"dipole_{key}"] = values[index]
			writer.writerow(row)
