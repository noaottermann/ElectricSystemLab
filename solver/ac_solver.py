from __future__ import annotations

import math
from typing import Optional

import numpy as np

from model.components import (
    Ammeter,
    Capacitor,
    CurrentControlledCurrentSource,
    CurrentControlledVoltageSource,
    CurrentSource,
    CurrentSourceAC,
    CurrentSourceDC,
    Diode,
    Inductor,
    LED,
    Resistor,
    Voltmeter,
    VoltageControlledCurrentSource,
    VoltageControlledVoltageSource,
    VoltageSource,
    VoltageSourceAC,
    VoltageSourceDC,
)
from solver.base_solver import BaseSolver
from solver.utils import build_group_index, group_connected_nodes, matrix_index_for_node


class ACSolver(BaseSolver):
    """Solveur AC en regime sinusoidal."""

    _MAX_ITERATIONS = 30
    _CONVERGENCE_TOL = 1e-6

    def solve(
        self,
        circuit,
        start_freq: float,
        stop_freq: float,
        points: int,
        sweep: str = "log",
    ) -> dict[str, object]:
        """Resout un circuit en regime sinusoidal sur une plage de frequences."""
        self._validate_circuit(circuit)
        if start_freq <= 0 or stop_freq <= 0:
            raise ValueError("La frequence doit etre strictement positive")
        if stop_freq < start_freq:
            raise ValueError("La frequence de fin doit etre >= a la frequence de debut")
        if points < 1:
            raise ValueError("Le nombre de points doit etre >= 1")
        if sweep not in ("log", "linear"):
            raise ValueError("Type de balayage invalide")

        if any(isinstance(d, (Diode, LED)) for d in circuit.dipoles.values()):
            raise ValueError("Les dipoles non lineaires ne sont pas supportes en AC")

        node_groups = group_connected_nodes(circuit)
        _, ground_group_id = self._ensure_ground(circuit, node_groups)
        group_to_idx = build_group_index(node_groups, ground_group_id)
        num_v_vars = len(group_to_idx)

        voltage_sources = self._collect_voltage_sources(circuit)
        num_i_vars = len(voltage_sources)
        total_vars = num_v_vars + num_i_vars
        if total_vars == 0:
            raise ValueError("Aucune equation a resoudre")

        voltage_source_indices = {
            source.id: num_v_vars + i for i, source in enumerate(voltage_sources)
        }

        freq_values = self._build_frequency_grid(start_freq, stop_freq, points, sweep=sweep)
        node_voltage_mag: dict[int, list[float]] = {node_id: [] for node_id in circuit.nodes}
        node_voltage_phase: dict[int, list[float]] = {node_id: [] for node_id in circuit.nodes}
        dipole_current_mag: dict[int, list[float]] = {dipole.id: [] for dipole in circuit.dipoles.values()}
        dipole_current_phase: dict[int, list[float]] = {dipole.id: [] for dipole in circuit.dipoles.values()}

        for freq in freq_values:
            omega = 2.0 * math.pi * float(freq)
            x = np.zeros(total_vars, dtype=np.complex128)

            has_cccs_current_control = self._has_cccs_non_voltage_control(circuit, voltage_source_indices)
            iterations = self._MAX_ITERATIONS if has_cccs_current_control else 1

            for _ in range(iterations):
                A = np.zeros((total_vars, total_vars), dtype=np.complex128)
                Z = np.zeros(total_vars, dtype=np.complex128)

                self._stamp_resistors(circuit, node_groups, group_to_idx, ground_group_id, A)
                self._stamp_dynamic_elements(circuit, node_groups, group_to_idx, ground_group_id, A, omega)
                self._stamp_current_sources(circuit, node_groups, group_to_idx, ground_group_id, Z, omega)
                self._stamp_vccs_sources(circuit, node_groups, group_to_idx, ground_group_id, A)
                self._stamp_cccs_sources(
                    circuit,
                    node_groups,
                    group_to_idx,
                    ground_group_id,
                    A,
                    Z,
                    voltage_source_indices,
                    x,
                    omega,
                )
                self._stamp_voltage_sources(
                    circuit,
                    voltage_sources,
                    node_groups,
                    group_to_idx,
                    ground_group_id,
                    A,
                    Z,
                    num_v_vars,
                    x,
                    voltage_source_indices,
                    omega,
                )

                try:
                    x_next = np.linalg.solve(A, Z)
                except np.linalg.LinAlgError as exc:
                    raise ValueError("Erreur AC: matrice singuliere") from exc

                if not has_cccs_current_control:
                    x = x_next
                    break

                delta = np.max(np.abs(x_next - x))
                x = x_next
                if delta <= self._CONVERGENCE_TOL:
                    break

            self._store_ac_results(
                circuit,
                node_groups,
                group_to_idx,
                ground_group_id,
                voltage_sources,
                x,
                voltage_source_indices,
                omega,
                node_voltage_mag,
                node_voltage_phase,
                dipole_current_mag,
                dipole_current_phase,
            )

        return {
            "frequency": freq_values,
            "node_voltage_mag": node_voltage_mag,
            "node_voltage_phase": node_voltage_phase,
            "dipole_current_mag": dipole_current_mag,
            "dipole_current_phase": dipole_current_phase,
        }

    def _collect_voltage_sources(self, circuit) -> list[object]:
        return [
            dipole
            for dipole in circuit.dipoles.values()
            if isinstance(
                dipole,
                (VoltageSource, VoltageSourceDC, VoltageSourceAC, VoltageControlledVoltageSource, CurrentControlledVoltageSource),
            )
        ]

    def _build_frequency_grid(self, start_freq: float, stop_freq: float, points: int, sweep: str) -> list[float]:
        if points == 1:
            return [float(start_freq)]
        if sweep == "linear":
            return list(np.linspace(start_freq, stop_freq, points, dtype=float))
        return list(np.logspace(math.log10(start_freq), math.log10(stop_freq), points, dtype=float))

    def _stamp_resistors(self, circuit, node_groups, group_to_idx, ground_group_id, matrix_a) -> None:
        for dipole in circuit.dipoles.values():
            if not isinstance(dipole, (Resistor, Voltmeter, Ammeter)):
                continue
            idx_a = matrix_index_for_node(dipole.node_a, node_groups, group_to_idx, ground_group_id)
            idx_b = matrix_index_for_node(dipole.node_b, node_groups, group_to_idx, ground_group_id)
            g = 1.0 / dipole.resistance
            self._stamp_conductance(idx_a, idx_b, matrix_a, g)

    def _stamp_dynamic_elements(self, circuit, node_groups, group_to_idx, ground_group_id, matrix_a, omega: float) -> None:
        for dipole in circuit.dipoles.values():
            idx_a = matrix_index_for_node(dipole.node_a, node_groups, group_to_idx, ground_group_id)
            idx_b = matrix_index_for_node(dipole.node_b, node_groups, group_to_idx, ground_group_id)

            if isinstance(dipole, Capacitor):
                if dipole.capacitance <= 0:
                    raise ValueError("La capacite doit etre strictement positive")
                g_eq = 1j * omega * dipole.capacitance
                self._stamp_conductance(idx_a, idx_b, matrix_a, g_eq)
            elif isinstance(dipole, Inductor):
                if dipole.inductance <= 0:
                    raise ValueError("L'inductance doit etre strictement positive")
                g_eq = 1.0 / (1j * omega * dipole.inductance) if omega != 0 else 0.0
                self._stamp_conductance(idx_a, idx_b, matrix_a, g_eq)

    def _stamp_current_sources(
        self,
        circuit,
        node_groups,
        group_to_idx,
        ground_group_id,
        vector_z,
        omega: float,
    ) -> None:
        for dipole in circuit.dipoles.values():
            current = None
            if isinstance(dipole, CurrentSourceAC):
                current = self._phasor_from_ac_source(dipole)
            elif isinstance(dipole, CurrentSourceDC):
                current = 0.0
            elif isinstance(dipole, CurrentSource):
                current = self._phasor_from_ac_source(dipole) if dipole.is_ac() else 0.0
            if current is None:
                continue
            idx_a = matrix_index_for_node(dipole.node_a, node_groups, group_to_idx, ground_group_id)
            idx_b = matrix_index_for_node(dipole.node_b, node_groups, group_to_idx, ground_group_id)
            self._stamp_current_source(idx_a, idx_b, vector_z, current)

    def _stamp_vccs_sources(self, circuit, node_groups, group_to_idx, ground_group_id, matrix_a) -> None:
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

    def _stamp_cccs_sources(
        self,
        circuit,
        node_groups,
        group_to_idx,
        ground_group_id,
        matrix_a,
        vector_z,
        voltage_source_indices: dict[int, int],
        state_vector,
        omega: float,
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
            control_current = self._control_current_from_state_ac(
                circuit,
                control,
                node_groups,
                group_to_idx,
                ground_group_id,
                state_vector,
                voltage_source_indices,
                omega,
            )
            current = gain * control_current
            if idx_a is not None:
                vector_z[idx_a] -= current
            if idx_b is not None:
                vector_z[idx_b] += current

    def _stamp_voltage_sources(
        self,
        circuit,
        voltage_sources,
        node_groups,
        group_to_idx,
        ground_group_id,
        matrix_a,
        vector_z,
        current_var_offset: int,
        state_vector,
        voltage_source_indices: dict[int, int],
        omega: float,
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
                vector_z[idx_src] = self._phasor_from_ac_source(source)
                continue
            if isinstance(source, VoltageSourceDC):
                vector_z[idx_src] = 0.0
                continue
            if isinstance(source, VoltageSource):
                vector_z[idx_src] = self._phasor_from_ac_source(source) if source.is_ac() else 0.0
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
                control_current = self._control_current_from_state_ac(
                    circuit,
                    control,
                    node_groups,
                    group_to_idx,
                    ground_group_id,
                    state_vector,
                    voltage_source_indices,
                    omega,
                )
                vector_z[idx_src] = float(source.transresistance) * control_current

    def _store_ac_results(
        self,
        circuit,
        node_groups,
        group_to_idx,
        ground_group_id,
        voltage_sources,
        state_vector,
        voltage_source_indices: dict[int, int],
        omega: float,
        node_voltage_mag,
        node_voltage_phase,
        dipole_current_mag,
        dipole_current_phase,
    ) -> None:
        for node_id, node in circuit.nodes.items():
            gid = node_groups[node_id]
            if gid == ground_group_id:
                voltage = 0.0 + 0.0j
            else:
                idx = group_to_idx.get(gid)
                voltage = 0.0 + 0.0j if idx is None else state_vector[idx]
            node_voltage_mag[node_id].append(float(np.abs(voltage)))
            node_voltage_phase[node_id].append(float(np.degrees(np.angle(voltage))))

        for dipole in circuit.dipoles.values():
            current = self._dipole_current_from_state(
                circuit,
                dipole,
                node_groups,
                group_to_idx,
                ground_group_id,
                state_vector,
                voltage_source_indices,
                omega,
            )
            dipole_current_mag[dipole.id].append(float(np.abs(current)))
            dipole_current_phase[dipole.id].append(float(np.degrees(np.angle(current))))

        for source in voltage_sources:
            idx_src = voltage_source_indices.get(source.id)
            if idx_src is None:
                continue
            source.current = float(np.abs(state_vector[idx_src]))

    def _dipole_current_from_state(
        self,
        circuit,
        dipole,
        node_groups,
        group_to_idx,
        ground_group_id,
        state_vector,
        voltage_source_indices: dict[int, int],
        omega: float,
    ) -> complex:
        if isinstance(dipole, (Resistor, Voltmeter, Ammeter)):
            return self._voltage_across(dipole, node_groups, group_to_idx, ground_group_id, state_vector) / dipole.resistance
        if isinstance(dipole, Capacitor):
            return 1j * omega * dipole.capacitance * self._voltage_across(
                dipole, node_groups, group_to_idx, ground_group_id, state_vector
            )
        if isinstance(dipole, Inductor):
            if omega == 0:
                return 0.0 + 0.0j
            return self._voltage_across(
                dipole, node_groups, group_to_idx, ground_group_id, state_vector
            ) / (1j * omega * dipole.inductance)
        if isinstance(dipole, CurrentSourceAC):
            return self._phasor_from_ac_source(dipole)
        if isinstance(dipole, CurrentSourceDC):
            return 0.0 + 0.0j
        if isinstance(dipole, CurrentSource):
            return self._phasor_from_ac_source(dipole) if dipole.is_ac() else 0.0 + 0.0j
        if isinstance(dipole, VoltageControlledCurrentSource):
            control = circuit.dipoles.get(dipole.control_dipole_id)
            if control is None:
                return 0.0 + 0.0j
            v_c = self._voltage_across(control, node_groups, group_to_idx, ground_group_id, state_vector)
            return float(dipole.transconductance) * v_c
        if isinstance(dipole, CurrentControlledCurrentSource):
            control = circuit.dipoles.get(dipole.control_dipole_id)
            control_current = self._control_current_from_state_ac(
                circuit,
                control,
                node_groups,
                group_to_idx,
                ground_group_id,
                state_vector,
                voltage_source_indices,
                omega,
            )
            return float(dipole.gain) * control_current
        if isinstance(
            dipole,
            (VoltageSource, VoltageSourceDC, VoltageSourceAC, VoltageControlledVoltageSource, CurrentControlledVoltageSource),
        ):
            idx = voltage_source_indices.get(dipole.id)
            if idx is None:
                return 0.0 + 0.0j
            return -state_vector[idx]
        return complex(getattr(dipole, "current", 0.0))

    def _control_current_from_state_ac(
        self,
        circuit,
        control,
        node_groups,
        group_to_idx,
        ground_group_id,
        state_vector,
        voltage_source_indices: dict[int, int],
        omega: float,
        visited: Optional[set[int]] = None,
    ) -> complex:
        if control is None:
            return 0.0 + 0.0j
        if visited is None:
            visited = set()
        control_id = int(getattr(control, "id", 0) or 0)
        if control_id in visited:
            return complex(getattr(control, "current", 0.0))
        if control_id:
            visited.add(control_id)

        ctrl_idx = voltage_source_indices.get(control.id)
        if ctrl_idx is not None:
            return -state_vector[ctrl_idx]
        if isinstance(control, (Resistor, Voltmeter, Ammeter)):
            return self._voltage_across(control, node_groups, group_to_idx, ground_group_id, state_vector) / control.resistance
        if isinstance(control, Capacitor):
            return 1j * omega * control.capacitance * self._voltage_across(
                control, node_groups, group_to_idx, ground_group_id, state_vector
            )
        if isinstance(control, Inductor):
            if omega == 0:
                return 0.0 + 0.0j
            return self._voltage_across(control, node_groups, group_to_idx, ground_group_id, state_vector) / (
                1j * omega * control.inductance
            )
        if isinstance(control, CurrentSourceAC):
            return self._phasor_from_ac_source(control)
        if isinstance(control, CurrentSourceDC):
            return 0.0 + 0.0j
        if isinstance(control, CurrentSource):
            return self._phasor_from_ac_source(control) if control.is_ac() else 0.0 + 0.0j
        if isinstance(control, VoltageControlledCurrentSource):
            ctrl = circuit.dipoles.get(control.control_dipole_id)
            if ctrl is None:
                return 0.0 + 0.0j
            v_c = self._voltage_across(ctrl, node_groups, group_to_idx, ground_group_id, state_vector)
            return float(control.transconductance) * v_c
        if isinstance(control, CurrentControlledCurrentSource):
            ctrl = circuit.dipoles.get(control.control_dipole_id)
            return float(control.gain) * self._control_current_from_state_ac(
                circuit,
                ctrl,
                node_groups,
                group_to_idx,
                ground_group_id,
                state_vector,
                voltage_source_indices,
                omega,
                visited=visited,
            )
        return complex(getattr(control, "current", 0.0))

    def _voltage_across(self, dipole, node_groups, group_to_idx, ground_group_id, state_vector) -> complex:
        v_a = self._node_voltage(dipole.node_a, node_groups, group_to_idx, ground_group_id, state_vector)
        v_b = self._node_voltage(dipole.node_b, node_groups, group_to_idx, ground_group_id, state_vector)
        return v_a - v_b

    def _node_voltage(self, node, node_groups, group_to_idx, ground_group_id, state_vector) -> complex:
        if node is None:
            return 0.0 + 0.0j
        gid = node_groups.get(node.id)
        if gid == ground_group_id:
            return 0.0 + 0.0j
        idx = group_to_idx.get(gid)
        if idx is None:
            return 0.0 + 0.0j
        return state_vector[idx]

    def _phasor_from_ac_source(self, source) -> complex:
        amplitude = float(getattr(source, "amplitude", 0.0))
        phase_deg = float(getattr(source, "phase", 0.0))
        phase_rad = math.radians(phase_deg)
        return amplitude * complex(math.cos(phase_rad), math.sin(phase_rad))

    def _has_cccs_non_voltage_control(self, circuit, voltage_source_indices: dict[int, int]) -> bool:
        for dipole in circuit.dipoles.values():
            if not isinstance(dipole, CurrentControlledCurrentSource):
                continue
            ctrl_id = dipole.control_dipole_id
            if ctrl_id and ctrl_id not in voltage_source_indices:
                return True
        return False

    def _stamp_conductance(self, idx_a, idx_b, matrix_a, conductance: complex) -> None:
        if idx_a is not None:
            matrix_a[idx_a, idx_a] += conductance
            if idx_b is not None:
                matrix_a[idx_a, idx_b] -= conductance
        if idx_b is not None:
            matrix_a[idx_b, idx_b] += conductance
            if idx_a is not None:
                matrix_a[idx_b, idx_a] -= conductance

    def _stamp_current_source(self, idx_a, idx_b, vector_z, current_a_to_b: complex) -> None:
        if idx_a is not None:
            vector_z[idx_a] -= current_a_to_b
        if idx_b is not None:
            vector_z[idx_b] += current_a_to_b
