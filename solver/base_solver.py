from __future__ import annotations

from typing import Optional


class BaseSolver:
	"""Base commune des solveurs de circuit."""

	def _validate_circuit(self, circuit) -> None:
		"""Valide le circuit avant resolution."""
		if circuit is None:
			raise ValueError("Circuit invalide")
		if not getattr(circuit, "nodes", None):
			raise ValueError("Circuit vide")

	def _ensure_ground(self, circuit, node_groups: dict[int, int]) -> tuple[object, Optional[int]]:
		"""Garantit la presence d'une masse et retourne (node, group_id)."""
		ground_node = circuit.get_ground_node()
		if ground_node is not None:
			return ground_node, node_groups.get(ground_node.id)

		first_node = next(iter(circuit.nodes.values()), None)
		if first_node is None:
			raise ValueError("Circuit vide")
		first_node.is_ground = True
		return first_node, node_groups.get(first_node.id)
