"""Utilitaires de serialisation pour les modeles de circuit."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from model.circuit import Circuit
from model.components import (
	Capacitor,
	CurrentControlledVoltageSource,
	CurrentControlledCurrentSource,
	CurrentSourceAC,
	CurrentSourceDC,
	Diode,
	Inductor,
	LED,
	Resistor,
	VoltageControlledVoltageSource,
	VoltageControlledCurrentSource,
	VoltageSourceAC,
	VoltageSourceDC,
)


def get_component_class_map() -> dict[str, type]:
	"""Retourne la correspondance type -> classe de composant."""
	return {
		"Resistor": Resistor,
		"Capacitor": Capacitor,
		"Inductor": Inductor,
		"VoltageSourceDC": VoltageSourceDC,
		"VoltageSourceAC": VoltageSourceAC,
		"CurrentSourceDC": CurrentSourceDC,
		"CurrentSourceAC": CurrentSourceAC,
		"VoltageControlledCurrentSource": VoltageControlledCurrentSource,
		"CurrentControlledCurrentSource": CurrentControlledCurrentSource,
		"VoltageControlledVoltageSource": VoltageControlledVoltageSource,
		"CurrentControlledVoltageSource": CurrentControlledVoltageSource,
		"Diode": Diode,
		"LED": LED,
	}


def serialize_circuit(circuit: Circuit) -> str:
	"""Serialise un circuit en JSON."""
	if circuit is None:
		raise ValueError("Circuit manquant")
	return circuit.to_json()


def deserialize_circuit(circuit: Circuit, json_str: str) -> None:
	"""Charge un circuit depuis une chaine JSON."""
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
