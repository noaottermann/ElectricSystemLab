from __future__ import annotations

from typing import Optional
import numpy as np


class StampingContext:
	"""Contexte pour le stamping des matrices MNA, encapsule tous les paramètres."""

	def __init__(
		self,
		circuit,
		matrix_A: np.ndarray,
		vector_Z: np.ndarray,
		node_groups: dict[int, int],
		group_to_idx: dict[int, int],
		ground_group_id: Optional[int],
		voltage_source_indices: dict[int, int],
		state_vector: np.ndarray,
		omega: float = 0.0,
	) -> None:
		"""
		Initialise le contexte de stamping.
		
		Args:
			circuit: Le circuit à résoudre
			matrix_A: Matrice d'admittance MNA
			vector_Z: Vecteur source MNA
			node_groups: Mapping node_id -> group_id
			group_to_idx: Mapping group_id -> matrix index
			ground_group_id: ID du groupe de masse
			voltage_source_indices: Mapping source_id -> variable index
			state_vector: Vecteur d'état courant
			omega: Pulsation 2πf pour AC (0 pour DC)
		"""
		self.circuit = circuit
		self.matrix_A = matrix_A
		self.vector_Z = vector_Z
		self.node_groups = node_groups
		self.group_to_idx = group_to_idx
		self.ground_group_id = ground_group_id
		self.voltage_source_indices = voltage_source_indices
		self.state_vector = state_vector
		self.omega = float(omega)

	def get_matrix_index(self, node) -> Optional[int]:
		"""Obtient l'index de matrice pour un nœud."""
		if node is None:
			return None
		group_id = self.node_groups.get(node.id)
		if group_id is None or group_id == self.ground_group_id:
			return None
		return self.group_to_idx.get(group_id)

	def stamp_conductance(self, idx_a: Optional[int], idx_b: Optional[int], conductance) -> None:
		"""Estampille une conductance dans la matrice."""
		if idx_a is not None:
			self.matrix_A[idx_a, idx_a] += conductance
			if idx_b is not None:
				self.matrix_A[idx_a, idx_b] -= conductance
		if idx_b is not None:
			self.matrix_A[idx_b, idx_b] += conductance
			if idx_a is not None:
				self.matrix_A[idx_b, idx_a] -= conductance

	def stamp_current_source(self, idx_a: Optional[int], idx_b: Optional[int], current) -> None:
		"""Estampille une source de courant."""
		if idx_a is not None:
			self.vector_Z[idx_a] -= current
		if idx_b is not None:
			self.vector_Z[idx_b] += current

	def stamp_voltage_source_equation(
		self,
		source_index: int,
		idx_a: Optional[int],
		idx_b: Optional[int],
		voltage: float,
	) -> None:
		"""Estampille une équation de source de tension."""
		if idx_a is not None:
			self.matrix_A[source_index, idx_a] = 1
			self.matrix_A[idx_a, source_index] = 1
		if idx_b is not None:
			self.matrix_A[source_index, idx_b] = -1
			self.matrix_A[idx_b, source_index] = -1
		self.vector_Z[source_index] = voltage


class BaseSolver:
	"""Base commune des solveurs de circuit."""

	def _validate_circuit(self, circuit) -> None:
		"""Valide le circuit avant résolution."""
		if circuit is None:
			raise ValueError("Circuit invalide")
		if not getattr(circuit, "nodes", None):
			raise ValueError("Circuit vide")

	def _ensure_ground(self, circuit, node_groups: dict[int, int]) -> tuple[object, Optional[int]]:
		"""Garantit la présence d'une masse et retourne (node, group_id)."""
		ground_node = circuit.get_ground_node()
		if ground_node is not None:
			return ground_node, node_groups.get(ground_node.id)

		first_node = next(iter(circuit.nodes.values()), None)
		if first_node is None:
			raise ValueError("Circuit vide")
		first_node.is_ground = True
		first_node._potential = 0.0
		return first_node, node_groups.get(first_node.id)

	def _has_cccs_non_voltage_control(self, circuit, voltage_source_indices: dict[int, int]) -> bool:
		"""Vérifie s'il existe des CCCS non contrôlées par une source de tension."""
		from model.components import CurrentControlledCurrentSource
		for dipole in circuit.dipoles.values():
			if isinstance(dipole, CurrentControlledCurrentSource):
				if dipole.control_dipole_id not in voltage_source_indices:
					return True
		return False

	def _control_current_from_state(
		self,
		circuit,
		control,
		node_groups,
		group_to_idx,
		ground_group_id,
		state_vector,
		voltage_source_indices,
	) -> float:
		"""Calcule le courant de contrôle depuis le vecteur d'état."""
		from model.components import VoltageSource, VoltageSourceDC
		
		if isinstance(control, (VoltageSource, VoltageSourceDC)):
			idx = voltage_source_indices.get(control.id)
			if idx is not None:
				return -float(state_vector[idx])
		# Pour les autres types de composants, retourner 0.0 par défaut
		return 0.0

