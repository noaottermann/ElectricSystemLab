"""
Solveur DC utilisant l'analyse nodale modifiée (MNA) et le stamping polymorphe.
"""

from __future__ import annotations

import logging
from typing import Optional
import numpy as np

from model.components import (
    Ammeter,
    CurrentControlledCurrentSource,
    CurrentControlledVoltageSource,
    CurrentSource,
    CurrentSourceAC,
    CurrentSourceDC,
    Diode,
    LED,
    Resistor,
    Switch,
    Voltmeter,
    VoltageControlledCurrentSource,
    VoltageControlledVoltageSource,
    VoltageSource,
    VoltageSourceAC,
    VoltageSourceDC,
    Comparator,
    LogicGate,
    MOSFET,
    Transistor,
    ZenerDiode,
)
from solver.base_solver import BaseSolver, StampingContext
import solver.stamping_registry  # noqa: F401 - Garantit l'enregistrement des méthodes polymorphes

logger = logging.getLogger(__name__)


class DCSolver(BaseSolver):
    """Solveur DC basé sur l'analyse nodale modifiée polymorphe."""

    def solve(self, circuit) -> None:
        """Résout un circuit en régime continu par analyse nodale modifiée."""
        if circuit is None:
            logger.warning("Circuit invalide")
            return
        if not getattr(circuit, "nodes", None):
            logger.warning("Circuit vide")
            return

        # 1. Regroupe les noeuds connectés par des fils (Union-Find)
        node_groups = self._group_connected_nodes(circuit)

        # 2. Gestion de la masse
        ground_node, ground_group_id = self._ensure_ground(circuit, node_groups)

        # 3. Indexation des variables de potentiel nodaux
        group_to_idx = self._build_group_index(node_groups, ground_group_id)
        num_v_vars = len(group_to_idx)

        # 4. Collecte des variables de courant pour les sources de tension
        voltage_sources = self._collect_voltage_sources(circuit)
        num_i_vars = len(voltage_sources)
        total_vars = num_v_vars + num_i_vars
        if total_vars == 0:
            return

        voltage_source_indices = {
            int(getattr(v_src, "id", index)): num_v_vars + index for index, v_src in enumerate(voltage_sources)
        }

        # 5. Vecteur d'état initial
        x = np.zeros(total_vars)
        for node_id, node in circuit.nodes.items():
            gid = node_groups[node_id]
            if gid == ground_group_id:
                continue
            idx = group_to_idx.get(gid)
            if idx is not None:
                x[idx] = float(node.potential)

        has_nonlinear = any(
            isinstance(d, (Diode, LED, ZenerDiode, Transistor, MOSFET, Comparator, LogicGate))
            for d in circuit.dipoles.values()
        )
        has_dependent = self._has_dependent_non_voltage_control(circuit, voltage_source_indices)
        iterations = self._MAX_ITERATIONS if (has_nonlinear or has_dependent) else 1

        diagnostics = {
            "converged": True,
            "iterations": 0,
            "max_delta": 0.0,
            "residual": 0.0,
            "relaxation": 1.0,
        }
        prev_delta = float("inf")
        prev_residual = float("inf")

        # 6. Boucle de résolution (Newton-Raphson / Relaxation pour non-linéaire)
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
                solver=self,
            )

            # Assemblage polymorphe des équations du circuit
            for dipole in circuit.dipoles.values():
                if hasattr(dipole, "stamp_dc"):
                    dipole.stamp_dc(context)
                else:
                    logger.warning("Composant %s sans methode stamp_dc", type(dipole).__name__)

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
                logger.error("Erreur de resolution: matrice singuliere")
                return

            self._refresh_dependent_currents(
                circuit,
                node_groups,
                group_to_idx,
                ground_group_id,
                x_next,
                voltage_source_indices,
            )

            if not (has_nonlinear or has_dependent):
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
            logger.warning(
                "Convergence limitee (iter=%d, delta=%.3g, resid=%.3g, relax=%.2f)",
                diagnostics["iterations"],
                diagnostics["max_delta"],
                diagnostics["residual"],
                diagnostics["relaxation"],
            )

        # 7. Répartition des potentiels sur les noeuds
        for node_id, node in circuit.nodes.items():
            gid = node_groups[node_id]
            if gid == ground_group_id:
                node.potential = 0.0
            else:
                idx = group_to_idx.get(gid)
                if idx is not None:
                    node.potential = float(x[idx])

        # 8. Mise à jour des courants dans les composants
        for dipole in circuit.dipoles.values():
            if isinstance(dipole, (Resistor, Switch, Voltmeter, Ammeter)):
                resistance = float(getattr(dipole, "resistance", 0.0))
                dipole.current = dipole.voltage / resistance if resistance else 0.0
            elif isinstance(dipole, (CurrentSource, CurrentSourceDC)):
                dipole.current = float(dipole.get_dc_value() if hasattr(dipole, "get_dc_value") else getattr(dipole, "dc_current", 0.0))
            elif isinstance(dipole, CurrentSourceAC):
                dipole.current = 0.0
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
                val = dipole.gain * control_current
                dipole.current = float(val.real if isinstance(val, complex) else val)
            elif isinstance(dipole, (Diode, LED)):
                current, _ = self._diode_current_and_conductance(dipole.voltage, dipole)
                dipole.current = float(current)

        for i, v_src in enumerate(voltage_sources):
            idx_src = num_v_vars + i
            setattr(v_src, "current", -float(x[idx_src]))

    def _refresh_dependent_currents(
        self,
        circuit,
        node_groups: dict[int, int],
        group_to_idx: dict[int, int],
        ground_group_id: Optional[int],
        state_vector: np.ndarray,
        voltage_source_indices: dict[int, int],
    ) -> None:
        """Met à jour les courants des sources dépendantes."""
        for _ in range(self._MAX_ITERATIONS):
            max_delta = 0.0
            for dipole in circuit.dipoles.values():
                previous = float(getattr(dipole, "current", 0.0))
                if isinstance(dipole, (VoltageSource, VoltageSourceDC, VoltageControlledVoltageSource, CurrentControlledVoltageSource)):
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
                    val = dipole.gain * control_current
                    dipole.current = float(val.real if isinstance(val, complex) else val)
                max_delta = max(max_delta, abs(float(getattr(dipole, "current", 0.0)) - previous))
            if max_delta <= self._CONVERGENCE_TOL:
                break