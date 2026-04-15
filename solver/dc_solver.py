from __future__ import annotations

from typing import Optional

import numpy as np

from model.components import (
    CurrentControlledCurrentSource,
    CurrentControlledVoltageSource,
    CurrentSourceDC,
    Diode,
    LED,
    Resistor,
    VoltageControlledVoltageSource,
    VoltageControlledCurrentSource,
    VoltageSourceDC,
)

class DCSolver:
    """Solveur DC base sur l'analyse nodale."""

    _MAX_ITERATIONS = 30
    _CONVERGENCE_TOL = 1e-6
    _RELAXATION_MIN = 0.1
    _RELAXATION_DECAY = 0.5

    def solve(self, circuit) -> None:
        """Resout un circuit continu par analyse nodale avec sources de tension."""
        if circuit is None:
            print("Circuit invalide")
            return
        # Regroupe les noeuds connectes par des fils
        node_groups = self._group_connected_nodes(circuit)
        
        # Gestion de la masse
        ground_node = circuit.get_ground_node()
        ground_group_id: Optional[int] = None
        if ground_node:
            ground_group_id = node_groups[ground_node.id]
        else:
            if circuit.nodes:
                first_node = list(circuit.nodes.values())[0]
                first_node.is_ground = True
                ground_node = first_node
                ground_group_id = node_groups[first_node.id]
            else:
                print("Circuit vide")
                return

        # Correspondance groupe vers indice de matrice
        group_to_idx = self._build_group_index(node_groups, ground_group_id)
        num_v_vars = len(group_to_idx)

        # Variables de courant des sources de tension
        voltage_sources = self._collect_voltage_sources(circuit)
        num_i_vars = len(voltage_sources)
        total_vars = num_v_vars + num_i_vars
        if total_vars == 0:
            return

        voltage_source_indices = {
            v_src.id: num_v_vars + index for index, v_src in enumerate(voltage_sources)
        }

        x = np.zeros(total_vars)
        for node_id, node in circuit.nodes.items():
            gid = node_groups[node_id]
            if gid == ground_group_id:
                continue
            idx = group_to_idx.get(gid)
            if idx is not None:
                x[idx] = float(node.potential)

        has_nonlinear = any(isinstance(d, (Diode, LED)) for d in circuit.dipoles.values())
        has_cccs_current_control = self._has_cccs_non_voltage_control(circuit, voltage_source_indices)
        iterations = self._MAX_ITERATIONS if (has_nonlinear or has_cccs_current_control) else 1

        diagnostics = {
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

            self._stamp_resistors(circuit, node_groups, group_to_idx, ground_group_id, A)
            self._stamp_current_sources(circuit, node_groups, group_to_idx, ground_group_id, Z)
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
            )
            self._stamp_diodes(circuit, node_groups, group_to_idx, ground_group_id, A, Z, x)
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
            )

            try:
                x_next = np.linalg.solve(A, Z)
            except np.linalg.LinAlgError:
                diagnostics.update(
                    {
                        "converged": False,
                        "iterations": iteration + 1,
                        "max_delta": float("inf"),
                        "residual": float("inf"),
                        "relaxation": 0.0,
                    }
                )
                self.last_diagnostics = diagnostics
                print("Erreur de resolution: matrice singuliere")
                return

            self._refresh_dependent_currents(
                circuit,
                node_groups,
                group_to_idx,
                ground_group_id,
                x_next,
                voltage_source_indices,
            )

            if not (has_nonlinear or has_cccs_current_control):
                x = x_next
                diagnostics.update(
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
            diagnostics.update(
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
            diagnostics["converged"] = False

        self.last_diagnostics = diagnostics
        if not diagnostics["converged"]:
            print(
                "Avertissement: convergence limitee (iter=%d, delta=%.3g, resid=%.3g, relax=%.2f)"
                % (
                    diagnostics["iterations"],
                    diagnostics["max_delta"],
                    diagnostics["residual"],
                    diagnostics["relaxation"],
                )
            )

        # Repartit les resultats
        for node_id, node in circuit.nodes.items():
            group_id = node_groups[node_id]
            if group_id == ground_group_id:
                node.potential = 0.0
            else:
                idx = group_to_idx.get(group_id)
                if idx is not None:
                    new_pot = float(x[idx])
                    node.potential = new_pot

        # Met a jour les courants
        for dipole in circuit.dipoles.values():
            if isinstance(dipole, Resistor):
                dipole.current = dipole.voltage / dipole.resistance
            elif isinstance(dipole, CurrentSourceDC):
                dipole.current = dipole.dc_current
            elif isinstance(dipole, VoltageControlledCurrentSource):
                control = circuit.dipoles.get(dipole.control_dipole_id)
                if control is not None:
                    dipole.current = dipole.transconductance * float(control.voltage)
                else:
                    dipole.current = 0.0
            elif isinstance(dipole, CurrentControlledCurrentSource):
                control = circuit.dipoles.get(dipole.control_dipole_id)
                control_current = self._control_current_from_state(
                    circuit,
                    control,
                    node_groups,
                    group_to_idx,
                    ground_group_id,
                    x,
                    voltage_source_indices,
                )
                dipole.current = dipole.gain * control_current
            elif isinstance(dipole, (Diode, LED)):
                current, _ = self._diode_current_and_conductance(dipole.voltage, dipole)
                dipole.current = current
        for i, v_src in enumerate(voltage_sources):
            idx_src = num_v_vars + i
            v_src.current = -float(x[idx_src])

    def _refresh_dependent_currents(
        self,
        circuit,
        node_groups,
        group_to_idx,
        ground_group_id,
        state_vector,
        voltage_source_indices: dict[int, int],
    ) -> None:
        for _ in range(self._MAX_ITERATIONS):
            max_delta = 0.0
            for dipole in circuit.dipoles.values():
                previous = float(getattr(dipole, "current", 0.0))
                if isinstance(dipole, (VoltageSourceDC, VoltageControlledVoltageSource, CurrentControlledVoltageSource)):
                    idx = voltage_source_indices.get(dipole.id)
                    if idx is not None:
                        dipole.current = -float(state_vector[idx])
                elif isinstance(dipole, VoltageControlledCurrentSource):
                    control = circuit.dipoles.get(dipole.control_dipole_id)
                    if control is not None:
                        dipole.current = dipole.transconductance * float(control.voltage)
                    else:
                        dipole.current = 0.0
                elif isinstance(dipole, CurrentControlledCurrentSource):
                    control = circuit.dipoles.get(dipole.control_dipole_id)
                    control_current = self._control_current_from_state(
                        circuit,
                        control,
                        node_groups,
                        group_to_idx,
                        ground_group_id,
                        state_vector,
                        voltage_source_indices,
                    )
                    dipole.current = dipole.gain * control_current
                max_delta = max(max_delta, abs(float(getattr(dipole, "current", 0.0)) - previous))
            if max_delta <= self._CONVERGENCE_TOL:
                break

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
        """Retourne les sources de tension continues du circuit."""
        voltage_sources = []
        for dipole in circuit.dipoles.values():
            if isinstance(
                dipole,
                (VoltageSourceDC, VoltageControlledVoltageSource, CurrentControlledVoltageSource),
            ):
                voltage_sources.append(dipole)
        return voltage_sources

    def _stamp_resistors(self, circuit, node_groups, group_to_idx, ground_group_id, matrix_a) -> None:
        for dipole in circuit.dipoles.values():
            if not isinstance(dipole, Resistor):
                continue
            idx_a = self._get_matrix_index(dipole.node_a, node_groups, group_to_idx, ground_group_id)
            idx_b = self._get_matrix_index(dipole.node_b, node_groups, group_to_idx, ground_group_id)
            g = 1.0 / dipole.resistance
            if idx_a is not None:
                matrix_a[idx_a, idx_a] += g
                if idx_b is not None:
                    matrix_a[idx_a, idx_b] -= g
            if idx_b is not None:
                matrix_a[idx_b, idx_b] += g
                if idx_a is not None:
                    matrix_a[idx_b, idx_a] -= g

    def _stamp_current_sources(self, circuit, node_groups, group_to_idx, ground_group_id, vector_z) -> None:
        for dipole in circuit.dipoles.values():
            if not isinstance(dipole, CurrentSourceDC):
                continue
            idx_a = self._get_matrix_index(dipole.node_a, node_groups, group_to_idx, ground_group_id)
            idx_b = self._get_matrix_index(dipole.node_b, node_groups, group_to_idx, ground_group_id)
            current = float(dipole.dc_current)
            if idx_a is not None:
                vector_z[idx_a] -= current
            if idx_b is not None:
                vector_z[idx_b] += current

    def _stamp_vccs_sources(self, circuit, node_groups, group_to_idx, ground_group_id, matrix_a) -> None:
        for dipole in circuit.dipoles.values():
            if not isinstance(dipole, VoltageControlledCurrentSource):
                continue
            control = circuit.dipoles.get(dipole.control_dipole_id)
            if control is None:
                continue
            idx_a = self._get_matrix_index(dipole.node_a, node_groups, group_to_idx, ground_group_id)
            idx_b = self._get_matrix_index(dipole.node_b, node_groups, group_to_idx, ground_group_id)
            idx_c = self._get_matrix_index(control.node_a, node_groups, group_to_idx, ground_group_id)
            idx_d = self._get_matrix_index(control.node_b, node_groups, group_to_idx, ground_group_id)
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
    ) -> None:
        for dipole in circuit.dipoles.values():
            if not isinstance(dipole, CurrentControlledCurrentSource):
                continue
            idx_a = self._get_matrix_index(dipole.node_a, node_groups, group_to_idx, ground_group_id)
            idx_b = self._get_matrix_index(dipole.node_b, node_groups, group_to_idx, ground_group_id)
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
    ) -> None:
        for i, v_src in enumerate(voltage_sources):
            idx_src = current_var_offset + i
            idx_a = self._get_matrix_index(v_src.node_a, node_groups, group_to_idx, ground_group_id)
            idx_b = self._get_matrix_index(v_src.node_b, node_groups, group_to_idx, ground_group_id)
            if idx_a is not None:
                matrix_a[idx_src, idx_a] = 1
                matrix_a[idx_a, idx_src] = 1
            if idx_b is not None:
                matrix_a[idx_src, idx_b] = -1
                matrix_a[idx_b, idx_src] = -1

            if isinstance(v_src, VoltageSourceDC):
                vector_z[idx_src] = v_src.dc_voltage
                continue

            if isinstance(v_src, VoltageControlledVoltageSource):
                control = circuit.dipoles.get(v_src.control_dipole_id)
                if control is None:
                    continue
                idx_c = self._get_matrix_index(control.node_a, node_groups, group_to_idx, ground_group_id)
                idx_d = self._get_matrix_index(control.node_b, node_groups, group_to_idx, ground_group_id)
                gain = float(v_src.gain)
                if idx_c is not None:
                    matrix_a[idx_src, idx_c] -= gain
                if idx_d is not None:
                    matrix_a[idx_src, idx_d] += gain
                continue

            if isinstance(v_src, CurrentControlledVoltageSource):
                control = circuit.dipoles.get(v_src.control_dipole_id)
                if control is None:
                    continue
                ctrl_idx = voltage_source_indices.get(control.id)
                if ctrl_idx is not None:
                    matrix_a[idx_src, ctrl_idx] -= float(v_src.transresistance)
                    continue
                control_current = self._control_current_from_state(
                    circuit,
                    control,
                    node_groups,
                    group_to_idx,
                    ground_group_id,
                    state_vector,
                    voltage_source_indices,
                )
                vector_z[idx_src] = float(v_src.transresistance) * control_current

    def _stamp_diodes(
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
            idx_a = self._get_matrix_index(dipole.node_a, node_groups, group_to_idx, ground_group_id)
            idx_b = self._get_matrix_index(dipole.node_b, node_groups, group_to_idx, ground_group_id)
            v_a = 0.0 if idx_a is None else float(state_vector[idx_a])
            v_b = 0.0 if idx_b is None else float(state_vector[idx_b])
            v_d = v_a - v_b
            current, conductance = self._diode_current_and_conductance(v_d, dipole)
            i_eq = current - conductance * v_d
            self._stamp_conductance(idx_a, idx_b, matrix_a, conductance)
            self._stamp_current_source(idx_a, idx_b, vector_z, i_eq)

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

    def _diode_current_and_conductance(self, voltage: float, dipole: Diode) -> tuple[float, float]:
        isrc = float(dipole.saturation_current)
        n = max(float(dipole.ideality_factor), 1e-6)
        vt = max(float(dipole.thermal_voltage), 1e-6)
        exp_arg = max(-40.0, min(40.0, voltage / (n * vt)))
        exp_val = float(np.exp(exp_arg))
        current = isrc * (exp_val - 1.0)
        conductance = (isrc / (n * vt)) * exp_val
        return current, conductance

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
        visited: Optional[set[int]] = None,
    ) -> float:
        if control is None:
            return 0.0
        if visited is None:
            visited = set()
        control_id = int(getattr(control, "id", 0) or 0)
        if control_id in visited:
            return float(getattr(control, "current", 0.0))
        if control_id:
            visited.add(control_id)
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
        if isinstance(control, VoltageControlledCurrentSource):
            ctrl = circuit.dipoles.get(control.control_dipole_id)
            if ctrl is None:
                return 0.0
            v_c = self._node_voltage_from_state(ctrl.node_a, node_groups, group_to_idx, ground_group_id, state_vector)
            v_d = self._node_voltage_from_state(ctrl.node_b, node_groups, group_to_idx, ground_group_id, state_vector)
            return float(control.transconductance) * (v_c - v_d)
        if isinstance(control, CurrentControlledCurrentSource):
            ctrl = circuit.dipoles.get(control.control_dipole_id)
            return float(control.gain) * self._control_current_from_state(
                circuit,
                ctrl,
                node_groups,
                group_to_idx,
                ground_group_id,
                state_vector,
                voltage_source_indices,
                visited=visited,
            )
        if isinstance(control, (Diode, LED)):
            v_a = self._node_voltage_from_state(control.node_a, node_groups, group_to_idx, ground_group_id, state_vector)
            v_b = self._node_voltage_from_state(control.node_b, node_groups, group_to_idx, ground_group_id, state_vector)
            current, _ = self._diode_current_and_conductance(v_a - v_b, control)
            return current
        return float(getattr(control, "current", 0.0))

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

    def _group_connected_nodes(self, circuit) -> dict[int, int]:
        """Utilise Union-Find pour regrouper les noeuds relies par des fils."""
        parent = {node_id: node_id for node_id in circuit.nodes}

        def find(node_id: int) -> int:
            """Retourne la racine d'un noeud avec compression de chemin."""
            if parent[node_id] == node_id:
                return node_id
            parent[node_id] = find(parent[node_id])
            return parent[node_id]

        def union(left_id: int, right_id: int) -> None:
            """Fusionne deux ensembles de noeuds."""
            root_i = find(left_id)
            root_j = find(right_id)
            if root_i != root_j:
                parent[root_i] = root_j

        for wire in circuit.wires.values():
            if wire.node_a and wire.node_b:
                union(wire.node_a.id, wire.node_b.id)

        return {node_id: find(node_id) for node_id in circuit.nodes}

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
        gid = node_groups[node.id]
        if gid == ground_group_id:
            return None
        return group_to_idx.get(gid)