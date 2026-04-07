from __future__ import annotations

from typing import Optional

import numpy as np

from model.components import Capacitor, Inductor, Resistor, VoltageSourceAC, VoltageSourceDC
from solver.base_solver import BaseSolver
from solver.utils import build_group_index, group_connected_nodes, matrix_index_for_node


class TransientSolver(BaseSolver):
	"""Solveur transitoire simple (sources DC/AC et reseau resistif)."""

	def solve(self, circuit, duration: float, time_step: float, start_time: float = 0.0) -> dict[str, object]:
		"""Resout le circuit pour chaque pas de temps et retourne les traces."""
		self._validate_circuit(circuit)
		if duration < 0:
			raise ValueError("La duree doit etre positive")
		if time_step <= 0:
			raise ValueError("Le pas de temps doit etre strictement positif")
		if start_time < 0:
			raise ValueError("Le temps de depart doit etre positif")

		node_groups = group_connected_nodes(circuit)
		_, ground_group_id = self._ensure_ground(circuit, node_groups)
		group_to_idx = build_group_index(node_groups, ground_group_id)
		num_v_vars = len(group_to_idx)

		voltage_sources = self._collect_voltage_sources(circuit)
		num_i_vars = len(voltage_sources)
		total_vars = num_v_vars + num_i_vars
		if total_vars == 0:
			raise ValueError("Aucune equation a resoudre")

		time_values = self._build_time_grid(duration, time_step, start_time)
		node_potentials: dict[int, list[float]] = {node_id: [] for node_id in circuit.nodes}
		dipole_voltages: dict[int, list[float]] = {dipole.id: [] for dipole in circuit.dipoles.values()}
		dipole_currents: dict[int, list[float]] = {
			dipole.id: []
			for dipole in circuit.dipoles.values()
			if isinstance(dipole, (Resistor, Capacitor, Inductor, VoltageSourceDC, VoltageSourceAC))
		}
		capacitor_prev_voltage = {
			dipole.id: float(dipole.voltage)
			for dipole in circuit.dipoles.values()
			if isinstance(dipole, Capacitor)
		}
		inductor_prev_current = {
			dipole.id: float(dipole.current)
			for dipole in circuit.dipoles.values()
			if isinstance(dipole, Inductor)
		}

		for t in time_values:
			A = np.zeros((total_vars, total_vars))
			Z = np.zeros(total_vars)

			self._assemble_resistors(circuit, node_groups, group_to_idx, ground_group_id, A)
			self._assemble_dynamic_elements(
				circuit,
				node_groups,
				group_to_idx,
				ground_group_id,
				A,
				Z,
				time_step,
				capacitor_prev_voltage,
				inductor_prev_current,
			)
			self._assemble_voltage_sources(
				voltage_sources,
				node_groups,
				group_to_idx,
				ground_group_id,
				A,
				Z,
				num_v_vars,
				t,
			)

			try:
				x = np.linalg.solve(A, Z)
			except np.linalg.LinAlgError as exc:
				raise ValueError("Erreur de resolution transitoire: matrice singuliere") from exc

			self._store_solution(
				circuit,
				node_groups,
				group_to_idx,
				ground_group_id,
				voltage_sources,
				x,
				num_v_vars,
				time_step,
				capacitor_prev_voltage,
				inductor_prev_current,
				node_potentials,
				dipole_voltages,
				dipole_currents,
			)
			self._update_dynamic_histories(circuit, capacitor_prev_voltage, inductor_prev_current)

		return {
			"time": time_values,
			"node_potentials": node_potentials,
			"dipole_voltages": dipole_voltages,
			"dipole_currents": dipole_currents,
		}

	def _collect_voltage_sources(self, circuit) -> list[object]:
		return [
			dipole
			for dipole in circuit.dipoles.values()
			if isinstance(dipole, (VoltageSourceDC, VoltageSourceAC))
		]

	def _build_time_grid(self, duration: float, time_step: float, start_time: float = 0.0) -> list[float]:
		steps = int(round(duration / time_step))
		times = [round(start_time + i * time_step, 12) for i in range(steps + 1)]
		if not times:
			return [round(start_time, 12)]
		return times

	def _assemble_resistors(self, circuit, node_groups, group_to_idx, ground_group_id, matrix_a) -> None:
		for dipole in circuit.dipoles.values():
			if not isinstance(dipole, Resistor):
				continue
			idx_a = matrix_index_for_node(dipole.node_a, node_groups, group_to_idx, ground_group_id)
			idx_b = matrix_index_for_node(dipole.node_b, node_groups, group_to_idx, ground_group_id)
			g = 1.0 / dipole.resistance

			if idx_a is not None:
				matrix_a[idx_a, idx_a] += g
				if idx_b is not None:
					matrix_a[idx_a, idx_b] -= g
			if idx_b is not None:
				matrix_a[idx_b, idx_b] += g
				if idx_a is not None:
					matrix_a[idx_b, idx_a] -= g

	def _stamp_conductance(self, idx_a, idx_b, matrix_a, conductance: float) -> None:
		if idx_a is not None:
			matrix_a[idx_a, idx_a] += conductance
			if idx_b is not None:
				matrix_a[idx_a, idx_b] -= conductance
		if idx_b is not None:
			matrix_a[idx_b, idx_b] += conductance
			if idx_a is not None:
				matrix_a[idx_b, idx_a] -= conductance

	def _stamp_current_source(self, idx_a, idx_b, vector_z, current_a_to_b: float) -> None:
		if idx_a is not None:
			vector_z[idx_a] -= current_a_to_b
		if idx_b is not None:
			vector_z[idx_b] += current_a_to_b

	def _assemble_dynamic_elements(
		self,
		circuit,
		node_groups,
		group_to_idx,
		ground_group_id,
		matrix_a,
		vector_z,
		time_step: float,
		capacitor_prev_voltage,
		inductor_prev_current,
	) -> None:
		for dipole in circuit.dipoles.values():
			idx_a = matrix_index_for_node(dipole.node_a, node_groups, group_to_idx, ground_group_id)
			idx_b = matrix_index_for_node(dipole.node_b, node_groups, group_to_idx, ground_group_id)

			if isinstance(dipole, Capacitor):
				if dipole.capacitance <= 0:
					raise ValueError("La capacite doit etre strictement positive")
				g_eq = dipole.capacitance / time_step
				v_prev = float(capacitor_prev_voltage.get(dipole.id, 0.0))
				i_hist = -g_eq * v_prev
				self._stamp_conductance(idx_a, idx_b, matrix_a, g_eq)
				self._stamp_current_source(idx_a, idx_b, vector_z, i_hist)

			elif isinstance(dipole, Inductor):
				if dipole.inductance <= 0:
					raise ValueError("L'inductance doit etre strictement positive")
				g_eq = time_step / dipole.inductance
				i_prev = float(inductor_prev_current.get(dipole.id, 0.0))
				i_hist = i_prev
				self._stamp_conductance(idx_a, idx_b, matrix_a, g_eq)
				self._stamp_current_source(idx_a, idx_b, vector_z, i_hist)

	def _assemble_voltage_sources(
		self,
		voltage_sources,
		node_groups,
		group_to_idx,
		ground_group_id,
		matrix_a,
		vector_z,
		current_var_offset: int,
		time_value: float,
	) -> None:
		for i, source in enumerate(voltage_sources):
			idx_src = current_var_offset + i
			idx_a = matrix_index_for_node(source.node_a, node_groups, group_to_idx, ground_group_id)
			idx_b = matrix_index_for_node(source.node_b, node_groups, group_to_idx, ground_group_id)

			if idx_a is not None:
				matrix_a[idx_src, idx_a] = 1
				matrix_a[idx_a, idx_src] = 1
			if idx_b is not None:
				matrix_a[idx_src, idx_b] = -1
				matrix_a[idx_b, idx_src] = -1

			if isinstance(source, VoltageSourceAC):
				vector_z[idx_src] = source.get_value_at_time(time_value)
			else:
				vector_z[idx_src] = source.dc_voltage

	def _store_solution(
		self,
		circuit,
		node_groups,
		group_to_idx,
		ground_group_id: Optional[int],
		voltage_sources,
		solution,
		current_var_offset: int,
		time_step: float,
		capacitor_prev_voltage,
		inductor_prev_current,
		node_potentials,
		dipole_voltages,
		dipole_currents,
	) -> None:
		for node_id, node in circuit.nodes.items():
			gid = node_groups[node_id]
			if gid == ground_group_id:
				node.potential = 0.0
			else:
				idx = group_to_idx.get(gid)
				if idx is not None:
					node.potential = float(solution[idx])
			node_potentials[node_id].append(float(node.potential))

		for dipole in circuit.dipoles.values():
			dipole_voltages[dipole.id].append(float(dipole.voltage))

		for dipole in circuit.dipoles.values():
			if isinstance(dipole, Resistor):
				dipole.current = dipole.voltage / dipole.resistance
				if dipole.id in dipole_currents:
					dipole_currents[dipole.id].append(float(dipole.current))
			elif isinstance(dipole, Capacitor):
				v_prev = float(capacitor_prev_voltage.get(dipole.id, 0.0))
				dipole.current = dipole.capacitance * (dipole.voltage - v_prev) / time_step
				if dipole.id in dipole_currents:
					dipole_currents[dipole.id].append(float(dipole.current))
			elif isinstance(dipole, Inductor):
				i_prev = float(inductor_prev_current.get(dipole.id, 0.0))
				dipole.current = i_prev + (time_step / dipole.inductance) * dipole.voltage
				if dipole.id in dipole_currents:
					dipole_currents[dipole.id].append(float(dipole.current))

		for i, source in enumerate(voltage_sources):
			idx_src = current_var_offset + i
			source.current = -float(solution[idx_src])
			if source.id in dipole_currents:
				dipole_currents[source.id].append(float(source.current))

	def _update_dynamic_histories(self, circuit, capacitor_prev_voltage, inductor_prev_current) -> None:
		for dipole in circuit.dipoles.values():
			if isinstance(dipole, Capacitor):
				capacitor_prev_voltage[dipole.id] = float(dipole.voltage)
			elif isinstance(dipole, Inductor):
				inductor_prev_current[dipole.id] = float(dipole.current)
