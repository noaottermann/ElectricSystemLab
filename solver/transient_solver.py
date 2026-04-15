from __future__ import annotations

from typing import Optional

import numpy as np

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
	Switch,
	VoltageControlledVoltageSource,
	VoltageControlledCurrentSource,
	VoltageSourceAC,
	VoltageSourceDC,
)
from solver.base_solver import BaseSolver
from solver.utils import build_group_index, group_connected_nodes, matrix_index_for_node


class TransientSolver(BaseSolver):
	"""Solveur transitoire simple (sources DC/AC et reseau resistif)."""

	_MAX_ITERATIONS = 30
	_CONVERGENCE_TOL = 1e-6
	_RELAXATION_MIN = 0.1
	_RELAXATION_DECAY = 0.5

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
			if isinstance(
				dipole,
				(
					Resistor,
					Capacitor,
					Inductor,
					VoltageSourceDC,
					VoltageSourceAC,
					CurrentSourceDC,
					CurrentSourceAC,
					VoltageControlledCurrentSource,
					CurrentControlledCurrentSource,
					VoltageControlledVoltageSource,
					CurrentControlledVoltageSource,
					Diode,
					LED,
				),
			)
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

		voltage_source_indices = {
			source.id: num_v_vars + i for i, source in enumerate(voltage_sources)
		}
		last_solution = np.zeros(total_vars)
		for node_id, node in circuit.nodes.items():
			gid = node_groups[node_id]
			if gid == ground_group_id:
				continue
			idx = group_to_idx.get(gid)
			if idx is not None:
				last_solution[idx] = float(node.potential)

		has_nonlinear = any(isinstance(d, (Diode, LED)) for d in circuit.dipoles.values())
		has_cccs_current_control = self._has_cccs_non_voltage_control(circuit, voltage_source_indices)
		iterations = self._MAX_ITERATIONS if (has_nonlinear or has_cccs_current_control) else 1

		diagnostics: list[dict[str, float | int | bool]] = []
		for t in time_values:
			x = last_solution.copy()
			step_diag = {
				"time": float(t),
				"converged": True,
				"iterations": 0,
				"max_delta": 0.0,
				"residual": 0.0,
				"relaxation": 1.0,
			}
			prev_delta = float("inf")
			prev_residual = float("inf")
			for iteration in range(iterations):
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
				self._assemble_current_sources(
					circuit,
					node_groups,
					group_to_idx,
					ground_group_id,
					Z,
					t,
				)
				self._assemble_vccs_sources(circuit, node_groups, group_to_idx, ground_group_id, A)
				self._assemble_cccs_sources(
					circuit,
					node_groups,
					group_to_idx,
					ground_group_id,
					A,
					Z,
					voltage_source_indices,
					x,
					t,
					time_step,
					capacitor_prev_voltage,
					inductor_prev_current,
				)
				self._assemble_diodes(circuit, node_groups, group_to_idx, ground_group_id, A, Z, x)
				self._assemble_voltage_sources(
					circuit,
					voltage_sources,
					node_groups,
					group_to_idx,
					ground_group_id,
					A,
					Z,
					num_v_vars,
					t,
					x,
					voltage_source_indices,
					time_step,
					capacitor_prev_voltage,
					inductor_prev_current,
				)

				try:
					x_next = np.linalg.solve(A, Z)
				except np.linalg.LinAlgError as exc:
					step_diag.update(
						{
							"converged": False,
							"iterations": iteration + 1,
							"max_delta": float("inf"),
							"residual": float("inf"),
							"relaxation": 0.0,
						}
					)
					diagnostics.append(step_diag)
					raise ValueError("Erreur de resolution transitoire: matrice singuliere") from exc

				if not (has_nonlinear or has_cccs_current_control):
					x = x_next
					step_diag.update(
						{
							"iterations": iteration + 1,
							"max_delta": 0.0,
							"residual": float(np.max(np.abs(A.dot(x_next) - Z))),
							"relaxation": 1.0,
						}
					)
					break

				x_relaxed, delta, residual, relaxation = self._apply_relaxation(
					x,
					x_next,
					A,
					Z,
					prev_delta,
					prev_residual,
				)
				x = x_relaxed
				prev_delta = delta
				prev_residual = residual
				step_diag.update(
					{
						"iterations": iteration + 1,
						"max_delta": float(delta),
						"residual": float(residual),
						"relaxation": float(relaxation),
					}
				)
				if delta <= self._CONVERGENCE_TOL:
					break
			else:
				step_diag["converged"] = False

			if has_nonlinear or has_cccs_current_control:
				diagnostics.append(step_diag)

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
				time_value=t,
				voltage_source_indices=voltage_source_indices,
			)
			self._update_dynamic_histories(circuit, capacitor_prev_voltage, inductor_prev_current)
			last_solution = x

		return {
			"time": time_values,
			"node_potentials": node_potentials,
			"dipole_voltages": dipole_voltages,
			"dipole_currents": dipole_currents,
			"diagnostics": diagnostics,
		}

	def _apply_relaxation(
		self,
		x,
		x_next,
		matrix_a,
		vector_z,
		prev_delta: float,
		prev_residual: float,
	) -> tuple[np.ndarray, float, float, float]:
		"""Applique un amortissement si la mise a jour diverge."""
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

	def _collect_voltage_sources(self, circuit) -> list[object]:
		return [
			dipole
			for dipole in circuit.dipoles.values()
			if isinstance(
				dipole,
				(
					VoltageSourceDC,
					VoltageSourceAC,
					VoltageControlledVoltageSource,
					CurrentControlledVoltageSource,
				),
			)
		]

	def _build_time_grid(self, duration: float, time_step: float, start_time: float = 0.0) -> list[float]:
		steps = int(round(duration / time_step))
		times = [round(start_time + i * time_step, 12) for i in range(steps + 1)]
		if not times:
			return [round(start_time, 12)]
		return times

	def _assemble_resistors(self, circuit, node_groups, group_to_idx, ground_group_id, matrix_a) -> None:
		for dipole in circuit.dipoles.values():
			if not isinstance(dipole, (Resistor, Switch)):
				continue
			idx_a = matrix_index_for_node(dipole.node_a, node_groups, group_to_idx, ground_group_id)
			idx_b = matrix_index_for_node(dipole.node_b, node_groups, group_to_idx, ground_group_id)
			resistance = float(getattr(dipole, "resistance", 0.0))
			if resistance <= 0:
				continue
			g = 1.0 / resistance

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

	def _assemble_current_sources(
		self,
		circuit,
		node_groups,
		group_to_idx,
		ground_group_id,
		vector_z,
		time_value: float,
	) -> None:
		for dipole in circuit.dipoles.values():
			if isinstance(dipole, CurrentSourceDC):
				current = float(dipole.dc_current)
			elif isinstance(dipole, CurrentSourceAC):
				current = float(dipole.get_value_at_time(time_value))
			else:
				continue
			idx_a = matrix_index_for_node(dipole.node_a, node_groups, group_to_idx, ground_group_id)
			idx_b = matrix_index_for_node(dipole.node_b, node_groups, group_to_idx, ground_group_id)
			self._stamp_current_source(idx_a, idx_b, vector_z, current)

	def _assemble_vccs_sources(self, circuit, node_groups, group_to_idx, ground_group_id, matrix_a) -> None:
		for dipole in circuit.dipoles.values():
			if not isinstance(dipole, VoltageControlledCurrentSource):
				continue
			control = circuit.dipoles.get(dipole.control_dipole_id)
			if control is None:
				continue
			idx_a = matrix_index_for_node(dipole.node_a, node_groups, group_to_idx, ground_group_id)
			idx_b = matrix_index_for_node(dipole.node_b, node_groups, group_to_idx, ground_group_id)
			idx_c = matrix_index_for_node(control.node_a, node_groups, group_to_idx, ground_group_id)
			idx_d = matrix_index_for_node(control.node_b, node_groups, group_to_idx, ground_group_id)
			g = float(dipole.transconductance)
			if idx_a is not None and idx_c is not None:
				matrix_a[idx_a, idx_c] += g
			if idx_a is not None and idx_d is not None:
				matrix_a[idx_a, idx_d] -= g
			if idx_b is not None and idx_c is not None:
				matrix_a[idx_b, idx_c] -= g
			if idx_b is not None and idx_d is not None:
				matrix_a[idx_b, idx_d] += g

	def _assemble_cccs_sources(
		self,
		circuit,
		node_groups,
		group_to_idx,
		ground_group_id,
		matrix_a,
		vector_z,
		voltage_source_indices: dict[int, int],
		state_vector,
		time_value: float,
		time_step: float,
		capacitor_prev_voltage,
		inductor_prev_current,
	) -> None:
		for dipole in circuit.dipoles.values():
			if not isinstance(dipole, CurrentControlledCurrentSource):
				continue
			idx_a = matrix_index_for_node(dipole.node_a, node_groups, group_to_idx, ground_group_id)
			idx_b = matrix_index_for_node(dipole.node_b, node_groups, group_to_idx, ground_group_id)
			gain = float(dipole.gain)
			ctrl_idx = voltage_source_indices.get(dipole.control_dipole_id)
			if ctrl_idx is not None:
				if idx_a is not None:
					matrix_a[idx_a, ctrl_idx] += gain
				if idx_b is not None:
					matrix_a[idx_b, ctrl_idx] -= gain
				continue

			control = circuit.dipoles.get(dipole.control_dipole_id)
			control_current = self._control_current_from_state(
				circuit,
				control,
				node_groups,
				group_to_idx,
				ground_group_id,
				state_vector,
				voltage_source_indices,
				time_value,
				time_step,
				capacitor_prev_voltage,
				inductor_prev_current,
			)
			current = gain * control_current
			if idx_a is not None:
				vector_z[idx_a] -= current
			if idx_b is not None:
				vector_z[idx_b] += current

	def _assemble_diodes(
		self,
		circuit,
		node_groups,
		group_to_idx,
		ground_group_id,
		matrix_a,
		vector_z,
		state_vector,
	) -> None:
		for dipole in circuit.dipoles.values():
			if not isinstance(dipole, (Diode, LED)):
				continue
			idx_a = matrix_index_for_node(dipole.node_a, node_groups, group_to_idx, ground_group_id)
			idx_b = matrix_index_for_node(dipole.node_b, node_groups, group_to_idx, ground_group_id)
			v_a = 0.0 if idx_a is None else float(state_vector[idx_a])
			v_b = 0.0 if idx_b is None else float(state_vector[idx_b])
			v_d = v_a - v_b
			current, conductance = self._diode_current_and_conductance(v_d, dipole)
			i_eq = current - conductance * v_d
			self._stamp_conductance(idx_a, idx_b, matrix_a, conductance)
			self._stamp_current_source(idx_a, idx_b, vector_z, i_eq)

	def _assemble_voltage_sources(
		self,
		circuit,
		voltage_sources,
		node_groups,
		group_to_idx,
		ground_group_id,
		matrix_a,
		vector_z,
		current_var_offset: int,
		time_value: float,
		state_vector,
		voltage_source_indices: dict[int, int],
		time_step: float,
		capacitor_prev_voltage,
		inductor_prev_current,
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
				continue
			if isinstance(source, VoltageSourceDC):
				vector_z[idx_src] = source.dc_voltage
				continue
			if isinstance(source, VoltageControlledVoltageSource):
				control = circuit.dipoles.get(source.control_dipole_id)
				if control is None:
					continue
				idx_c = matrix_index_for_node(control.node_a, node_groups, group_to_idx, ground_group_id)
				idx_d = matrix_index_for_node(control.node_b, node_groups, group_to_idx, ground_group_id)
				gain = float(source.gain)
				if idx_c is not None:
					matrix_a[idx_src, idx_c] -= gain
				if idx_d is not None:
					matrix_a[idx_src, idx_d] += gain
				continue
			if isinstance(source, CurrentControlledVoltageSource):
				control = circuit.dipoles.get(source.control_dipole_id)
				if control is None:
					continue
				ctrl_idx = voltage_source_indices.get(control.id)
				if ctrl_idx is not None:
					matrix_a[idx_src, ctrl_idx] -= float(source.transresistance)
					continue
				control_current = self._control_current_from_state(
					circuit,
					control,
					node_groups,
					group_to_idx,
					ground_group_id,
					state_vector,
					voltage_source_indices,
					time_value,
					time_step,
					capacitor_prev_voltage,
					inductor_prev_current,
				)
				vector_z[idx_src] = float(source.transresistance) * control_current

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
		time_value: float,
		voltage_source_indices: dict[int, int],
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
			if isinstance(dipole, (Resistor, Switch)):
				resistance = float(getattr(dipole, "resistance", 0.0))
				dipole.current = dipole.voltage / resistance if resistance else 0.0
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
			elif isinstance(dipole, CurrentSourceDC):
				dipole.current = dipole.dc_current
				if dipole.id in dipole_currents:
					dipole_currents[dipole.id].append(float(dipole.current))
			elif isinstance(dipole, CurrentSourceAC):
				dipole.current = dipole.get_value_at_time(time_value)
				if dipole.id in dipole_currents:
					dipole_currents[dipole.id].append(float(dipole.current))
			elif isinstance(dipole, VoltageControlledCurrentSource):
				control = circuit.dipoles.get(dipole.control_dipole_id)
				if control is not None:
					dipole.current = dipole.transconductance * float(control.voltage)
				else:
					dipole.current = 0.0
				if dipole.id in dipole_currents:
					dipole_currents[dipole.id].append(float(dipole.current))
			elif isinstance(dipole, CurrentControlledCurrentSource):
				control = circuit.dipoles.get(dipole.control_dipole_id)
				control_current = self._control_current_from_state(
					circuit,
					control,
					node_groups,
					group_to_idx,
					ground_group_id,
					solution,
					voltage_source_indices,
					time_value,
					time_step,
					capacitor_prev_voltage,
					inductor_prev_current,
				)
				dipole.current = dipole.gain * control_current
				if dipole.id in dipole_currents:
					dipole_currents[dipole.id].append(float(dipole.current))
			elif isinstance(dipole, (Diode, LED)):
				current, _ = self._diode_current_and_conductance(dipole.voltage, dipole)
				dipole.current = current
				if dipole.id in dipole_currents:
					dipole_currents[dipole.id].append(float(dipole.current))

		for i, source in enumerate(voltage_sources):
			idx_src = current_var_offset + i
			source.current = -float(solution[idx_src])
			if source.id in dipole_currents:
				dipole_currents[source.id].append(float(source.current))

	def _diode_current_and_conductance(self, voltage: float, dipole: Diode) -> tuple[float, float]:
		isrc = float(dipole.saturation_current)
		n = max(float(dipole.ideality_factor), 1e-6)
		vt = max(float(dipole.thermal_voltage), 1e-6)
		exp_arg = max(-40.0, min(40.0, voltage / (n * vt)))
		exp_val = float(np.exp(exp_arg))
		current = isrc * (exp_val - 1.0)
		conductance = (isrc / (n * vt)) * exp_val
		return current, conductance

	def _update_dynamic_histories(self, circuit, capacitor_prev_voltage, inductor_prev_current) -> None:
		for dipole in circuit.dipoles.values():
			if isinstance(dipole, Capacitor):
				capacitor_prev_voltage[dipole.id] = float(dipole.voltage)
			elif isinstance(dipole, Inductor):
				inductor_prev_current[dipole.id] = float(dipole.current)

	def _has_cccs_non_voltage_control(self, circuit, voltage_source_indices: dict[int, int]) -> bool:
		for dipole in circuit.dipoles.values():
			if not isinstance(dipole, CurrentControlledCurrentSource):
				continue
			ctrl_id = dipole.control_dipole_id
			if ctrl_id and ctrl_id not in voltage_source_indices:
				return True
		return False

	def _node_voltage_from_state(
		self,
		node,
		node_groups,
		group_to_idx,
		ground_group_id,
		state_vector,
	) -> float:
		if node is None:
			return 0.0
		gid = node_groups.get(node.id)
		if gid == ground_group_id:
			return 0.0
		idx = group_to_idx.get(gid)
		if idx is None:
			return 0.0
		return float(state_vector[idx])

	def _control_current_from_state(
		self,
		circuit,
		control,
		node_groups,
		group_to_idx,
		ground_group_id,
		state_vector,
		voltage_source_indices: dict[int, int],
		time_value: float,
		time_step: float,
		capacitor_prev_voltage,
		inductor_prev_current,
	) -> float:
		if control is None:
			return 0.0
		ctrl_idx = voltage_source_indices.get(control.id)
		if ctrl_idx is not None:
			return -float(state_vector[ctrl_idx])
		if isinstance(control, Resistor):
			v_a = self._node_voltage_from_state(control.node_a, node_groups, group_to_idx, ground_group_id, state_vector)
			v_b = self._node_voltage_from_state(control.node_b, node_groups, group_to_idx, ground_group_id, state_vector)
			if control.resistance == 0:
				return 0.0
			return (v_a - v_b) / control.resistance
		if isinstance(control, CurrentSourceDC):
			return float(control.dc_current)
		if isinstance(control, CurrentSourceAC):
			return float(control.get_value_at_time(time_value))
		if isinstance(control, Capacitor):
			v_prev = float(capacitor_prev_voltage.get(control.id, 0.0))
			v_now = self._node_voltage_from_state(control.node_a, node_groups, group_to_idx, ground_group_id, state_vector) - \
				self._node_voltage_from_state(control.node_b, node_groups, group_to_idx, ground_group_id, state_vector)
			return control.capacitance * (v_now - v_prev) / time_step
		if isinstance(control, Inductor):
			i_prev = float(inductor_prev_current.get(control.id, 0.0))
			v_now = self._node_voltage_from_state(control.node_a, node_groups, group_to_idx, ground_group_id, state_vector) - \
				self._node_voltage_from_state(control.node_b, node_groups, group_to_idx, ground_group_id, state_vector)
			return i_prev + (time_step / control.inductance) * v_now
		if isinstance(control, VoltageControlledCurrentSource):
			ctrl = circuit.dipoles.get(control.control_dipole_id)
			if ctrl is None:
				return 0.0
			v_c = self._node_voltage_from_state(ctrl.node_a, node_groups, group_to_idx, ground_group_id, state_vector)
			v_d = self._node_voltage_from_state(ctrl.node_b, node_groups, group_to_idx, ground_group_id, state_vector)
			return float(control.transconductance) * (v_c - v_d)
		if isinstance(control, (Diode, LED)):
			v_a = self._node_voltage_from_state(control.node_a, node_groups, group_to_idx, ground_group_id, state_vector)
			v_b = self._node_voltage_from_state(control.node_b, node_groups, group_to_idx, ground_group_id, state_vector)
			current, _ = self._diode_current_and_conductance(v_a - v_b, control)
			return current
		return float(getattr(control, "current", 0.0))
