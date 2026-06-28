"""Utilitaires de serialisation pour les modèles de circuit."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from model.circuit import Circuit
from model.components import get_component_registry


def get_component_class_map() -> dict[str, type]:
	"""Retourne la correspondance type -> classe de composant.
	
	Utilise le registre automatique rempli par les décorateurs @register_component
	sur les classes dans model/components.py.
	"""
	return get_component_registry()


def serialize_circuit(circuit: Circuit) -> str:
	"""Sérialise un circuit en JSON."""
	if circuit is None:
		raise ValueError("Circuit manquant")
	return circuit.to_json()


def deserialize_circuit(circuit: Circuit, json_str: str) -> None:
	"""Charge un circuit depuis une chaîne JSON."""
	if circuit is None:
		raise ValueError("Circuit manquant")
	circuit.load_from_json(json_str, get_component_class_map())


def load_circuit_from_file(circuit: Circuit, path: Union[Path, str]) -> None:
	"""Charge un circuit depuis un fichier."""
	file_path = Path(path)
	json_str = file_path.read_text(encoding="utf-8")
	deserialize_circuit(circuit, json_str)


def save_circuit_to_file(circuit: Circuit, path: Union[Path, str]) -> None:
	"""Sauvegarde un circuit vers un fichier."""
	file_path = Path(path)
	json_str = serialize_circuit(circuit)
	file_path.write_text(json_str, encoding="utf-8")
