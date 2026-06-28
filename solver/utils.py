from __future__ import annotations

from typing import Optional


def group_connected_nodes(circuit) -> dict[int, int]:
	"""Regroupe les noeuds reliés par des fils via Union-Find."""
	parent = {node_id: node_id for node_id in circuit.nodes}

	def find(node_id: int) -> int:
		if parent[node_id] == node_id:
			return node_id
		parent[node_id] = find(parent[node_id])
		return parent[node_id]

	def union(left_id: int, right_id: int) -> None:
		root_left = find(left_id)
		root_right = find(right_id)
		if root_left != root_right:
			parent[root_left] = root_right

	for wire in circuit.wires.values():
		if wire.node_a and wire.node_b:
			union(wire.node_a.id, wire.node_b.id)

	return {node_id: find(node_id) for node_id in circuit.nodes}


def build_group_index(
	node_groups: dict[int, int], ground_group_id: Optional[int]
) -> dict[int, int]:
	"""Associe chaque groupe hors masse à un indice de matrice."""
	group_to_idx: dict[int, int] = {}
	next_index = 0
	for gid in set(node_groups.values()):
		if gid == ground_group_id:
			continue
		group_to_idx[gid] = next_index
		next_index += 1
	return group_to_idx


def matrix_index_for_node(
	node,
	node_groups: dict[int, int],
	group_to_idx: dict[int, int],
	ground_group_id: Optional[int],
) -> Optional[int]:
	"""Retourne l'indice de matrice d'un noeud (None pour masse)."""
	if node is None:
		return None
	gid = node_groups[node.id]
	if gid == ground_group_id:
		return None
	return group_to_idx.get(gid)


class MatrixStamper:
	"""Classe utilitaire pour les opérations communes de stamping matriciel dans les solveurs.
	
	Encapsule les méthodes réutilisables pour la collecte de composants et le calcul de courants.
	"""

	@staticmethod
	def collect_voltage_sources(circuit) -> list[object]:
		"""Retourne toutes les sources de tension du circuit.
		
		Args:
			circuit: Le circuit à analyser
			
		Returns:
			Liste des sources de tension (VoltageSource, VoltageSourceDC, VCVS, CCVS)
		"""
		from model.components import (
			VoltageSource,
			VoltageSourceDC,
			VoltageSourceAC,
			VoltageControlledVoltageSource,
			CurrentControlledVoltageSource,
		)
		return [
			dipole
			for dipole in circuit.dipoles.values()
			if isinstance(
				dipole,
				(VoltageSource, VoltageSourceDC, VoltageSourceAC, VoltageControlledVoltageSource, CurrentControlledVoltageSource),
			)
		]

	@staticmethod
	def get_voltage_across_dipole(
		dipole,
		node_groups: dict[int, int],
		group_to_idx: dict[int, int],
		ground_group_id: Optional[int],
		state_vector,
	) -> tuple[object, object, object]:
		"""Calcule les tensions aux bornes d'un dipôle.
		
		Args:
			dipole: Le dipôle
			node_groups: Mapping node_id -> group_id
			group_to_idx: Mapping group_id -> matrix index
			ground_group_id: ID du groupe de masse
			state_vector: Vecteur d'état contenant les tensions
			
		Returns:
			Tuple (v_a, v_b, v_d) où v_d = v_a - v_b
		"""
		idx_a = matrix_index_for_node(dipole.node_a, node_groups, group_to_idx, ground_group_id)
		idx_b = matrix_index_for_node(dipole.node_b, node_groups, group_to_idx, ground_group_id)
		
		# Obtenir les tensions (complexes ou réelles selon le contexte)
		v_a = 0.0 if idx_a is None else state_vector[idx_a]
		v_b = 0.0 if idx_b is None else state_vector[idx_b]
		v_d = v_a - v_b
		
		return v_a, v_b, v_d

	@staticmethod
	def compute_resistor_current(voltage: float, resistance: float) -> object:
		"""Calcule le courant à travers une résistance. Supporte réel et complexe."""
		if resistance == 0:
			return 0.0
		return voltage / resistance

	@staticmethod
	def compute_capacitor_current_ac(omega: float, capacitance: float, voltage) -> object:
		"""Calcule le courant AC à travers un condensateur."""
		if omega == 0:
			return 0.0
		return 1j * omega * capacitance * voltage

	@staticmethod
	def compute_inductor_current_ac(omega: float, inductance: float, voltage) -> object:
		"""Calcule le courant AC à travers une inductance."""
		if omega == 0 or inductance == 0:
			return 0.0
		return voltage / (1j * omega * inductance)

	@staticmethod
	def compute_voltage_source_current(source_id: int, voltage_source_indices: dict[int, int], state_vector) -> object:
		"""Calcule le courant d'une source de tension via l'indice MNA."""
		idx = voltage_source_indices.get(source_id)
		return -state_vector[idx] if idx is not None else 0.0

	@staticmethod
	def compute_current_source_dc_current(dipole) -> float:
		"""Obtient le courant DC d'une source de courant."""
		from model.components import CurrentSource
		
		if isinstance(dipole, CurrentSource):
			return dipole.get_dc_value()
		# Supposé être un CurrentSourceDC
		return float(getattr(dipole, 'dc_current', 0.0))

	@staticmethod
	def update_dependent_source_current(
		dipole,
		circuit: object,
		node_groups: Optional[dict] = None,
		group_to_idx: Optional[dict] = None,
		ground_group_id: Optional[int] = None,
		state_vector = None,
		voltage_source_indices: Optional[dict[int, int]] = None,
	) -> float:
		"""Calcule le courant pour une source dépendante (VCCS ou CCCS).
		
		Args:
			dipole: La source dépendante
			circuit: Le circuit
			node_groups: Mapping node_id -> group_id (optionnel)
			group_to_idx: Mapping group_id -> matrix index (optionnel)
			ground_group_id: ID du groupe de masse (optionnel)
			state_vector: Vecteur d'état (optionnel)
			voltage_source_indices: Indices des sources de tension (optionnel)
			
		Returns:
			Le courant de la source dépendante
		"""
		from model.components import VoltageControlledCurrentSource, CurrentControlledCurrentSource, VoltageSource, VoltageSourceDC
		
		if isinstance(dipole, VoltageControlledCurrentSource):
			control = circuit.dipoles.get(dipole.control_dipole_id)
			if control is not None:
				return dipole.transconductance * control.voltage
			return 0.0
		
		elif isinstance(dipole, CurrentControlledCurrentSource):
			control = circuit.dipoles.get(dipole.control_dipole_id)
			if control is None:
				return 0.0
			
			# Calculer le courant de contrôle
			if isinstance(control, (VoltageSource, VoltageSourceDC)):
				if voltage_source_indices and state_vector is not None:
					idx = voltage_source_indices.get(control.id)
					if idx is not None:
						control_current = -float(state_vector[idx])
					else:
						control_current = 0.0
				else:
					# Fallback sur control.voltage
					control_current = control.voltage / getattr(control, 'resistance', 1.0)
		else:
			control_current = control.voltage / getattr(control, 'resistance', 1.0)
		
		return 0.0
