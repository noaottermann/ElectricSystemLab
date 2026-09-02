"""
Solveur transitoire utilisant l'analyse nodale modifiée et le stamping polymorphe.
"""

from __future__ import annotations

import logging
from typing import Optional
import numpy as np

from model.components import (
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
    Switch,
    VoltageControlledCurrentSource,
    VoltageControlledVoltageSource,
    VoltageSource,
    VoltageSourceAC,
    VoltageSourceDC,
)
from solver.base_solver import BaseSolver, StampingContext
import solver.stamping_registry  # noqa: F401 - Enregistrement automatique des méthodes polymorphes

logger = logging.getLogger(__name__)


class TransientSolver(BaseSolver):
    """Solveur transitoire pas à pas basé sur le schéma compagnon d'Euler implicite."""

    def solve(self, circuit, duration: float, time_step: float, start_time: float = 0.0) -> dict[str, object]:
        """Résout le circuit pour chaque pas de temps et retourne les traces temporelles."""
        self._validate_circuit(circuit)
        if duration < 0:
            raise ValueError("La duree doit etre positive")
        if time_step <= 0:
            raise ValueError("Le pas de temps doit etre strictement positif")
        if start_time < 0:
            raise ValueError("Le temps de depart doit etre positif")

        # 1. Regroupement des nœuds et masse
        node_groups = self._group_connected_nodes(circuit)
        _, ground_group_id = self._ensure_ground(circuit, node_groups)
        group_to_idx = self._build_group_index(node_groups, ground_group_id)
        num_v_vars = len(group_to_idx)

        # 2. Collecte des sources de tension
        voltage_sources = self._collect_voltage_sources(circuit)
        num_i_vars = len(voltage_sources)
        total_vars = num_v_vars + num_i_vars
        if total_vars == 0:
            raise ValueError("Aucune equation a resoudre")

        time_values = self._build_time_grid(duration, time_step, start_time)
        node_potentials: dict[int, list[float]] = {node_id: [] for node_id in circuit.nodes}
        dipole_voltages: dict[int, list[float]] = {dipole.id: [] for dipole in circuit.dipoles.values()}
        dipole_currents: dict[int, list[float]] = {dipole.id: [] for dipole in circuit.dipoles.values()}

        # Historique d'état des condensateurs et inductances
        capacitor_prev_voltage = {
            dipole.id: float(getattr(dipole, "voltage", 0.0))
            for dipole in circuit.dipoles.values()
            if isinstance(dipole, Capacitor)
        }
        inductor_prev_current = {
            dipole.id: float(getattr(dipole, "current", 0.0))
            for dipole in circuit.dipoles.values()
            if isinstance(dipole, Inductor)
        }

        voltage_source_indices = {
            int(getattr(source, "id", i)): num_v_vars + i for i, source in enumerate(voltage_sources)
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
        has_dependent = self._has_dependent_non_voltage_control(circuit, voltage_source_indices)
        iterations = self._MAX_ITERATIONS if (has_nonlinear or has_dependent) else 1

        diagnostics: list[dict[str, float | int | bool]] = []

        # 3. Boucle temporelle
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

                context = StampingContext(
                    circuit=circuit,
                    matrix_A=A,
                    vector_Z=Z,
                    node_groups=node_groups,
                    group_to_idx=group_to_idx,
                    ground_group_id=ground_group_id,
                    voltage_source_indices=voltage_source_indices,
                    state_vector=x,
                    dt=time_step,
                    time=t,
                    capacitor_prev_voltage=capacitor_prev_voltage,
                    inductor_prev_current=inductor_prev_current,
                    solver=self,
                )

                # Assemblage polymorphe
                for dipole in circuit.dipoles.values():
                    if hasattr(dipole, "stamp_transient"):
                        dipole.stamp_transient(context, time_step)
                    elif hasattr(dipole, "stamp_dc"):
                        dipole.stamp_dc(context)
                    else:
                        logger.warning("Composant %s sans methode stamp_transient", type(dipole).__name__)

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

                if not (has_nonlinear or has_dependent):
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

            diagnostics.append(step_diag)
            last_solution = x.copy()

            self._store_solution(
                circuit,
                node_groups,
                group_to_idx,
                ground_group_id,
                voltage_sources,
                x,
                time_step,
                capacitor_prev_voltage,
                inductor_prev_current,
                node_potentials,
                dipole_voltages,
                dipole_currents,
                t,
                voltage_source_indices,
            )

        self.last_diagnostics = diagnostics
        return {
            "time": time_values,
            "node_potentials": node_potentials,
            "dipole_voltages": dipole_voltages,
            "dipole_currents": dipole_currents,
            "diagnostics": diagnostics,
        }

    def _build_time_grid(self, duration: float, time_step: float, start_time: float) -> list[float]:
        """Génère la grille temporelle discrète."""
        times: list[float] = []
        current = float(start_time)
        end_time = float(start_time + duration)
        while current <= end_time + (time_step * 0.1):
            times.append(round(current, 12))
            current += time_step
        if not times:
            return [round(start_time, 12)]
        return times

    def _store_solution(
        self,
        circuit,
        node_groups: dict[int, int],
        group_to_idx: dict[int, int],
        ground_group_id: Optional[int],
        voltage_sources: list[object],
        solution: np.ndarray,
        time_step: float,
        capacitor_prev_voltage: dict[int, float],
        inductor_prev_current: dict[int, float],
        node_potentials: dict[int, list[float]],
        dipole_voltages: dict[int, list[float]],
        dipole_currents: dict[int, list[float]],
        time_value: float,
        voltage_source_indices: dict[int, int],
    ) -> None:
        """Met à jour les nœuds et dipôles, et enregistre la solution du pas courant."""
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
            current = self._control_current_from_state(
                circuit,
                dipole,
                node_groups,
                group_to_idx,
                ground_group_id,
                solution,
                voltage_source_indices,
                time_value=time_value,
                time_step=time_step,
                capacitor_prev_voltage=capacitor_prev_voltage,
                inductor_prev_current=inductor_prev_current,
            )
            val = float(current.real if isinstance(current, complex) else current)
            dipole.current = val
            if dipole.id in dipole_currents:
                dipole_currents[dipole.id].append(val)

        # Mise à jour des historiques pour le prochain pas de temps
        for dipole in circuit.dipoles.values():
            if isinstance(dipole, Capacitor):
                capacitor_prev_voltage[dipole.id] = float(dipole.voltage)
            elif isinstance(dipole, Inductor):
                inductor_prev_current[dipole.id] = float(dipole.current)
