"""Utilitaires d'export pour les fichiers de circuit."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from model.circuit import Circuit
from .serializer import save_circuit_to_file


def export_circuit(circuit: Circuit, path: Union[Path, str]) -> None:
	"""Exporte un circuit vers un fichier."""
	file_path = Path(path)
	if file_path.suffix.lower() != ".json":
		raise ValueError("Format non pris en charge (attendu .json).")
	save_circuit_to_file(circuit, file_path)
