"""
Solveur AC en régime sinusoidal utilisant l'analyse nodale modifiée et le stamping polymorphe.
"""

from __future__ import annotations

import logging
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
    Switch,
    Voltmeter,
    VoltageControlledCurrentSource,
    VoltageControlledVoltageSource,
    VoltageSource,
    VoltageSourceAC,
    VoltageSourceDC,
)
from solver.base_solver import BaseSolver, StampingContext
import solver.stamping_registry  # noqa: F401 - Enregistrement automatique des méthodes polymorphes

logger = logging.getLogger(__name__)


class ACSolver(BaseSolver):
    """Solveur AC en régime sinusoidal sur une plage de fréquences."""

    def solve(
        self,
        circuit,
        start_freq: float,
        stop_freq: float,
        points: int,
        sweep: str = "log",
    ) -> dict[str, object]:
        """Résout un circuit en régime sinusoidal sur une plage de fréquences."""
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

        # 1. Regroupement des nœuds et gestion de la masse
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

        voltage_source_indices = {
            int(getattr(source, "id", i)): num_v_vars + i for i, source in enumerate(voltage_sources)
        }

        # 3. Grille de fréquences
        freq_values = self._build_frequency_grid(start_freq, stop_freq, points, sweep=sweep)
        node_voltage_mag: dict[int, list[float]] = {node_id: [] for node_id in circuit.nodes}
        node_voltage_phase: dict[int, list[float]] = {node_id: [] for node_id in circuit.nodes}
        dipole_current_mag: dict[int, list[float]] = {dipole.id: [] for dipole in circuit.dipoles.values()}
        dipole_current_phase: dict[int, list[float]] = {dipole.id: [] for dipole in circuit.dipoles.values()}

        # 4. Résolution pour chaque fréquence
        for freq in freq_values:
            omega = 2.0 * math.pi * float(freq)
            x = np.zeros(total_vars, dtype=np.complex128)

            has_dependent = self._has_dependent_non_voltage_control(circuit, voltage_source_indices)
            iterations = self._MAX_ITERATIONS if has_dependent else 1

            for _ in range(iterations):
                A = np.zeros((total_vars, total_vars), dtype=np.complex128)
                Z = np.zeros(total_vars, dtype=np.complex128)

                context = StampingContext(
                    circuit=circuit,
                    matrix_A=A,
                    vector_Z=Z,
                    node_groups=node_groups,
                    group_to_idx=group_to_idx,
                    ground_group_id=ground_group_id,
                    voltage_source_indices=voltage_source_indices,
                    state_vector=x,
                    omega=omega,
                    solver=self,
                )

                # Assemblage polymorphe
                for dipole in circuit.dipoles.values():
                    if hasattr(dipole, "stamp_ac"):
                        dipole.stamp_ac(context)
                    elif hasattr(dipole, "stamp_dc"):
                        dipole.stamp_dc(context)
                    else:
                        logger.warning("Composant %s sans methode stamp_ac", type(dipole).__name__)

                try:
                    x_next = np.linalg.solve(A, Z)
                except np.linalg.LinAlgError as exc:
                    raise ValueError("Erreur AC: matrice singuliere") from exc

                if not has_dependent:
                    x = x_next
                    break

                delta = float(np.max(np.abs(x_next - x)))
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
            "frequencies": freq_values,  # Alias pour compatibilité
            "node_voltage_mag": node_voltage_mag,
            "node_voltage_phase": node_voltage_phase,
            "dipole_current_mag": dipole_current_mag,
            "dipole_current_phase": dipole_current_phase,
        }

    def _build_frequency_grid(self, start_freq: float, stop_freq: float, points: int, sweep: str) -> list[float]:
        """Génère la grille de fréquences linéaire ou logarithmique."""
        if points == 1:
            return [float(start_freq)]
        if sweep == "linear":
            return list(np.linspace(start_freq, stop_freq, points, dtype=float))
        return list(np.logspace(math.log10(start_freq), math.log10(stop_freq), points, dtype=float))

    def _voltage_across(
        self,
        dipole,
        node_groups: dict[int, int],
        group_to_idx: dict[int, int],
        ground_group_id: Optional[int],
        state_vector: np.ndarray,
    ) -> complex:
        """Calcule la tension complexe aux bornes d'un dipôle."""
        v_a = self._node_voltage_from_state(dipole.node_a, node_groups, group_to_idx, ground_group_id, state_vector)
        v_b = self._node_voltage_from_state(dipole.node_b, node_groups, group_to_idx, ground_group_id, state_vector)
        return complex(v_a - v_b)

    def _store_ac_results(
        self,
        circuit,
        node_groups: dict[int, int],
        group_to_idx: dict[int, int],
        ground_group_id: Optional[int],
        voltage_sources: list[object],
        state_vector: np.ndarray,
        voltage_source_indices: dict[int, int],
        omega: float,
        node_voltage_mag: dict[int, list[float]],
        node_voltage_phase: dict[int, list[float]],
        dipole_current_mag: dict[int, list[float]],
        dipole_current_phase: dict[int, list[float]],
    ) -> None:
        """Enregistre les grandeurs AC complexes (amplitude et phase) pour le pas de fréquence courant."""
        for node_id, node in circuit.nodes.items():
            gid = node_groups[node_id]
            if gid == ground_group_id:
                node.potential = 0.0
                node_voltage_mag[node_id].append(0.0)
                node_voltage_phase[node_id].append(0.0)
            else:
                idx = group_to_idx.get(gid)
                if idx is not None:
                    val = state_vector[idx]
                    node.potential = float(np.abs(val))
                    node_voltage_mag[node_id].append(float(np.abs(val)))
                    node_voltage_phase[node_id].append(float(np.degrees(np.angle(val))))

        for dipole in circuit.dipoles.values():
            current = self._control_current_from_state(
                circuit,
                dipole,
                node_groups,
                group_to_idx,
                ground_group_id,
                state_vector,
                voltage_source_indices,
                is_ac=True,
                omega=omega,
            )
            dipole.current = float(np.abs(current))
            dipole_current_mag[dipole.id].append(float(np.abs(current)))
            dipole_current_phase[dipole.id].append(float(np.degrees(np.angle(current))))

        for source in voltage_sources:
            idx_src = voltage_source_indices.get(int(getattr(source, "id", -1)))
            if idx_src is not None:
                setattr(source, "current", float(np.abs(state_vector[idx_src])))
