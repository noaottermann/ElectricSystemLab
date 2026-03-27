"""Utilitaires d'import pour les fichiers de circuit."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from model.circuit import Circuit
from .serializer import load_circuit_from_file


def import_circuit(circuit: Circuit, path: Union[Path, str]) -> None:
	"""Importe un circuit depuis un fichier externe."""
	file_path = Path(path)
	if file_path.suffix.lower() != ".json":
		raise ValueError("Format non pris en charge (attendu .json).")
	load_circuit_from_file(circuit, file_path)
