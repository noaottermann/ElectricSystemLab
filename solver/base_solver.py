from __future__ import annotations

import math
from typing import Any, Optional
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
		dt: float = 0.0,
		time: float = 0.0,
		capacitor_prev_voltage: Optional[dict[int, float]] = None,
		inductor_prev_current: Optional[dict[int, float]] = None,
		solver: Optional[BaseSolver] = None,
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
			dt: Pas de temps pour simulation transitoire (0 pour DC/AC)
			time: Temps instantané pour simulation transitoire
			capacitor_prev_voltage: Tensions précédentes des condensateurs
			inductor_prev_current: Courants précédents des inductances
			solver: Référence optionnelle au solveur appelant
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
		self.dt = float(dt)
		self.time = float(time)
		self.capacitor_prev_voltage = capacitor_prev_voltage or {}
		self.inductor_prev_current = inductor_prev_current or {}
		self.solver = solver

	def get_matrix_index(self, node) -> Optional[int]:
		"""Obtient l'index de matrice pour un nœud."""
		if node is None:
			return None
		group_id = self.node_groups.get(node.id)
		if group_id is None or group_id == self.ground_group_id:
			return None
		return self.group_to_idx.get(group_id)

	def get_node_voltage(self, node) -> float:
		"""Retourne le potentiel estimé pour un nœud."""
		if node is None:
			return 0.0
		idx = self.get_matrix_index(node)
		if idx is None:
			return 0.0
		if idx < len(self.state_vector):
			val = self.state_vector[idx]
			return float(val.real if isinstance(val, complex) else val)
		return float(getattr(node, "potential", 0.0))

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
		voltage: float | complex,
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

	_MAX_ITERATIONS = 30
	_CONVERGENCE_TOL = 1e-6
	_RELAXATION_MIN = 0.1
	_RELAXATION_DECAY = 0.5

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

	def _group_connected_nodes(self, circuit) -> dict[int, int]:
		"""Utilise Union-Find pour regrouper les noeuds relies par des fils."""
		parent = {node_id: node_id for node_id in circuit.nodes}

		def find(node_id: int) -> int:
			if parent[node_id] == node_id:
				return int(node_id)
			parent[node_id] = find(parent[node_id])
			return int(parent[node_id])

		def union(left_id: int, right_id: int) -> None:
			root_i = find(left_id)
			root_j = find(right_id)
			if root_i != root_j:
				parent[root_i] = root_j

		for wire in circuit.wires.values():
			if wire.node_a and wire.node_b:
				union(wire.node_a.id, wire.node_b.id)

		return {node_id: find(node_id) for node_id in circuit.nodes}

	def _build_group_index(self, node_groups: dict[int, int], ground_group_id: Optional[int]) -> dict[int, int]:
		"""Associe chaque groupe de noeuds a un indice de matrice."""
		group_to_idx: dict[int, int] = {}
		next_index = 0
		for gid in set(node_groups.values()):
			if gid == ground_group_id:
				continue
			group_to_idx[gid] = next_index
			next_index += 1
		return group_to_idx

	def _collect_voltage_sources(self, circuit) -> list[Any]:
		"""Retourne les sources de tension (indépendantes et commandées) du circuit."""
		from model.components import (
			VoltageSource,
			VoltageSourceDC,
			VoltageSourceAC,
			PulseVoltageSource,
			VoltageControlledVoltageSource,
			CurrentControlledVoltageSource,
		)
		return [
			dipole
			for dipole in circuit.dipoles.values()
			if isinstance(
				dipole,
				(
					VoltageSource,
					VoltageSourceDC,
					VoltageSourceAC,
					PulseVoltageSource,
					VoltageControlledVoltageSource,
					CurrentControlledVoltageSource,
				),
			)
		]

	def _get_matrix_index(
		self,
		node,
		node_groups: dict[int, int],
		group_to_idx: dict[int, int],
		ground_group_id: Optional[int],
	) -> Optional[int]:
		"""Associe un noeud a son indice de matrice en ignorant le groupe de masse."""
		if node is None:
			return None
		gid = node_groups.get(node.id)
		if gid is None or gid == ground_group_id:
			return None
		return group_to_idx.get(gid)

	def _node_voltage_from_state(
		self,
		node,
		node_groups: dict[int, int],
		group_to_idx: dict[int, int],
		ground_group_id: Optional[int],
		state_vector: np.ndarray,
	) -> float | complex:
		"""Retourne le potentiel d'un nœud depuis le vecteur d'état."""
		if node is None:
			return 0.0
		gid = node_groups.get(node.id)
		if gid is None or gid == ground_group_id:
			return 0.0
		idx = group_to_idx.get(gid)
		if idx is None or idx >= len(state_vector):
			return 0.0
		val = state_vector[idx]
		return complex(val) if isinstance(val, (complex, np.complexfloating)) else float(val)

	def _diode_current_and_conductance(self, voltage: float, dipole) -> tuple[float, float]:
		"""Calcule le courant et la conductance linéarisée d'une diode (modèle Shockley borné)."""
		isrc = float(getattr(dipole, "saturation_current", 1e-12))
		n = max(float(getattr(dipole, "ideality_factor", 1.0)), 1e-6)
		vt = max(float(getattr(dipole, "thermal_voltage", 0.026)), 1e-6)
		exp_arg = max(-40.0, min(40.0, float(voltage) / (n * vt)))
		exp_val = float(np.exp(exp_arg))
		current = isrc * (exp_val - 1.0)
		conductance = (isrc / (n * vt)) * exp_val
		return current, conductance

	def _has_dependent_non_voltage_control(self, circuit, voltage_source_indices: dict[int, int]) -> bool:
		"""Vérifie s'il existe des sources contrôlées dépendant d'un élément autre qu'une source de tension."""
		from model.components import CurrentControlledCurrentSource, CurrentControlledVoltageSource
		for dipole in circuit.dipoles.values():
			if isinstance(dipole, (CurrentControlledCurrentSource, CurrentControlledVoltageSource)):
				ctrl_id = getattr(dipole, "control_dipole_id", None)
				if ctrl_id is not None and ctrl_id not in voltage_source_indices:
					return True
		return False

	def _has_cccs_non_voltage_control(self, circuit, voltage_source_indices: dict[int, int]) -> bool:
		"""Alias de compatibilité pour _has_dependent_non_voltage_control."""
		return self._has_dependent_non_voltage_control(circuit, voltage_source_indices)

	def _control_current_from_state(
		self,
		circuit,
		control,
		node_groups: dict[int, int],
		group_to_idx: dict[int, int],
		ground_group_id: Optional[int],
		state_vector: np.ndarray,
		voltage_source_indices: dict[int, int],
		visited: Optional[set[int]] = None,
		is_ac: bool = False,
		omega: float = 0.0,
		time_value: float = 0.0,
		time_step: float = 0.0,
		capacitor_prev_voltage: Optional[dict[int, float]] = None,
		inductor_prev_current: Optional[dict[int, float]] = None,
	) -> float | complex:
		"""
		Calcule le courant traversant le dipôle de contrôle à partir du vecteur d'état.
		Version unifiée supportant DC, AC et Transitoire avec détection de cycles.
		"""
		from model.components import (
			Resistor, Switch, Ammeter, Voltmeter,
			VoltageSource, VoltageSourceDC, VoltageSourceAC,
			CurrentSource, CurrentSourceDC, CurrentSourceAC,
			Capacitor, Inductor,
			VoltageControlledCurrentSource, CurrentControlledCurrentSource,
			VoltageControlledVoltageSource, CurrentControlledVoltageSource,
			Diode, LED,
		)

		if control is None:
			return 0.0 if not is_ac else 0.0 + 0.0j

		if visited is None:
			visited = set()

		control_id = int(getattr(control, "id", 0) or 0)
		if control_id in visited:
			return float(getattr(control, "current", 0.0)) if not is_ac else complex(getattr(control, "current", 0.0))
		if control_id:
			visited.add(control_id)

		# 1. Sources de tension ayant un indice de courant dans MNA
		ctrl_idx = voltage_source_indices.get(control.id) if voltage_source_indices else None
		if ctrl_idx is not None and ctrl_idx < len(state_vector):
			val = -state_vector[ctrl_idx]
			return complex(val) if isinstance(val, (complex, np.complexfloating)) else float(val)

		# 2. Résistances et dipôles linéaires passifs
		from model.components import Fuse, ZenerDiode
		if isinstance(control, (Resistor, Switch, Ammeter, Voltmeter, Fuse, ZenerDiode)):
			v_a = self._node_voltage_from_state(control.node_a, node_groups, group_to_idx, ground_group_id, state_vector)
			v_b = self._node_voltage_from_state(control.node_b, node_groups, group_to_idx, ground_group_id, state_vector)
			r = float(getattr(control, "resistance", 0.0))
			if r <= 0:
				return 0.0 if not is_ac else 0.0 + 0.0j
			return (v_a - v_b) / r

		# 3. Condensateurs
		if isinstance(control, Capacitor):
			v_a = self._node_voltage_from_state(control.node_a, node_groups, group_to_idx, ground_group_id, state_vector)
			v_b = self._node_voltage_from_state(control.node_b, node_groups, group_to_idx, ground_group_id, state_vector)
			if is_ac:
				return 1j * omega * control.capacitance * (v_a - v_b)
			elif time_step > 0 and capacitor_prev_voltage is not None:
				v_prev = float(capacitor_prev_voltage.get(control.id, 0.0))
				return control.capacitance * ((v_a - v_b) - v_prev) / time_step
			return 0.0

		# 4. Inductances
		if isinstance(control, Inductor):
			v_a = self._node_voltage_from_state(control.node_a, node_groups, group_to_idx, ground_group_id, state_vector)
			v_b = self._node_voltage_from_state(control.node_b, node_groups, group_to_idx, ground_group_id, state_vector)
			if is_ac:
				return (v_a - v_b) / (1j * omega * control.inductance) if omega != 0 else 0.0 + 0.0j
			elif time_step > 0 and inductor_prev_current is not None:
				i_prev = float(inductor_prev_current.get(control.id, 0.0))
				return i_prev + (time_step / control.inductance) * (v_a - v_b)
			return 0.0

		# 5. Sources de courant
		if isinstance(control, (CurrentSource, CurrentSourceDC, CurrentSourceAC)):
			if is_ac:
				if hasattr(control, "get_ac_phasor"):
					return control.get_ac_phasor()
				elif isinstance(control, CurrentSourceAC):
					phi = math.radians(getattr(control, "phase", 0.0))
					amp = float(getattr(control, "amplitude", 1.0))
					return amp * (math.cos(phi) + 1j * math.sin(phi))
				return 0.0 + 0.0j
			elif time_step > 0 or time_value > 0:
				if hasattr(control, "get_value_at_time"):
					return float(control.get_value_at_time(time_value))
				return float(getattr(control, "dc_current", 0.0))
			else:
				if hasattr(control, "get_dc_value"):
					return float(control.get_dc_value())
				return float(getattr(control, "dc_current", 0.0))

		# 6. VCCS
		if isinstance(control, VoltageControlledCurrentSource):
			ctrl = circuit.dipoles.get(control.control_dipole_id) if circuit else None
			if ctrl is None:
				return 0.0 if not is_ac else 0.0 + 0.0j
			v_c = self._node_voltage_from_state(ctrl.node_a, node_groups, group_to_idx, ground_group_id, state_vector)
			v_d = self._node_voltage_from_state(ctrl.node_b, node_groups, group_to_idx, ground_group_id, state_vector)
			return float(control.transconductance) * (v_c - v_d)

		# 7. CCCS (récursif)
		if isinstance(control, CurrentControlledCurrentSource):
			ctrl = circuit.dipoles.get(control.control_dipole_id) if circuit else None
			return float(control.gain) * self._control_current_from_state(
				circuit,
				ctrl,
				node_groups,
				group_to_idx,
				ground_group_id,
				state_vector,
				voltage_source_indices,
				visited=visited,
				is_ac=is_ac,
				omega=omega,
				time_value=time_value,
				time_step=time_step,
				capacitor_prev_voltage=capacitor_prev_voltage,
				inductor_prev_current=inductor_prev_current,
			)

		# 8. Diodes et LEDs
		if isinstance(control, (Diode, LED)):
			if is_ac:
				return 0.0 + 0.0j
			v_a_val = self._node_voltage_from_state(control.node_a, node_groups, group_to_idx, ground_group_id, state_vector)
			v_b_val = self._node_voltage_from_state(control.node_b, node_groups, group_to_idx, ground_group_id, state_vector)
			diff = v_a_val - v_b_val
			v_diff = float(diff.real) if isinstance(diff, (complex, np.complexfloating)) else float(diff)
			current, _ = self._diode_current_and_conductance(v_diff, control)
			return current

		return float(getattr(control, "current", 0.0)) if not is_ac else complex(getattr(control, "current", 0.0))

	def _apply_relaxation(
		self,
		x: np.ndarray,
		x_next: np.ndarray,
		matrix_a: np.ndarray,
		vector_z: np.ndarray,
		prev_delta: float,
		prev_residual: float,
	) -> tuple[np.ndarray, float, float, float]:
		"""Applique un amortissement si la mise à jour diverge."""
		update = x_next - x
		relaxation = 1.0
		while True:
			x_trial = x + relaxation * update
			delta = float(np.max(np.abs(x_trial - x)))
			residual = float(np.max(np.abs(matrix_a.dot(x_trial) - vector_z)))
			if delta <= prev_delta or residual <= prev_residual:
				return x_trial, delta, residual, relaxation
			if relaxation <= self._RELAXATION_MIN:
				return x_trial, delta, residual, relaxation
			relaxation *= self._RELAXATION_DECAY
