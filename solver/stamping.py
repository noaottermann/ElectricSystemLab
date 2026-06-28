"""
Implémentations de stamping pour tous les composants de circuit.

Ce module fournit les méthodes stamp_dc() et stamp_ac() polymorphes pour tous les composants,
éliminant les vérifications isinstance dans les solveurs.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from solver.base_solver import StampingContext


def stamp_resistor_dc(component, context: StampingContext) -> None:
    """Estampille une résistance DC."""
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    if component.resistance <= 0:
        return
    g = 1.0 / component.resistance
    context.stamp_conductance(idx_a, idx_b, g)


def stamp_capacitor_ac(component, context: StampingContext) -> None:
    """Estampille un condensateur AC (impédance 1/(jωC))."""
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    if component.capacitance <= 0:
        raise ValueError("La capacité doit être strictement positive")
    g_eq = 1j * context.omega * component.capacitance
    context.stamp_conductance(idx_a, idx_b, g_eq)


def stamp_inductor_ac(component, context: StampingContext) -> None:
    """Estampille une inductance AC (impédance jωL)."""
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    if component.inductance <= 0:
        raise ValueError("L'inductance doit être strictement positive")
    g_eq = 1.0 / (1j * context.omega * component.inductance) if context.omega != 0 else 0.0
    context.stamp_conductance(idx_a, idx_b, g_eq)


def stamp_voltage_source_dc(component, context: StampingContext) -> None:
    """Estampille une source de tension DC."""
    source_idx = context.voltage_source_indices.get(component.id)
    if source_idx is None:
        return
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    voltage = float(component.get_dc_value() if hasattr(component, 'get_dc_value') else component.dc_voltage)
    context.stamp_voltage_source_equation(source_idx, idx_a, idx_b, voltage)


def stamp_voltage_source_ac(component, context: StampingContext) -> None:
    """Estampille une source de tension AC (phaseur)."""
    source_idx = context.voltage_source_indices.get(component.id)
    if source_idx is None:
        return
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    # Extraction de amplitude et phase
    amplitude = float(getattr(component, 'amplitude', 10.0))
    phase = float(getattr(component, 'phase', 0.0))
    # Phaseur: |V| * exp(jφ)
    phase_rad = math.radians(phase)
    phasor = amplitude * (math.cos(phase_rad) + 1j * math.sin(phase_rad))
    context.stamp_voltage_source_equation(source_idx, idx_a, idx_b, phasor)


def stamp_current_source_dc(component, context: StampingContext) -> None:
    """Estampille une source de courant DC."""
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    current = float(component.get_dc_value() if hasattr(component, 'get_dc_value') else component.dc_current)
    context.stamp_current_source(idx_a, idx_b, current)


def stamp_current_source_ac(component, context: StampingContext) -> None:
    """Estampille une source de courant AC (phaseur)."""
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    amplitude = float(getattr(component, 'amplitude', 1.0))
    phase = float(getattr(component, 'phase', 0.0))
    phase_rad = math.radians(phase)
    phasor = amplitude * (math.cos(phase_rad) + 1j * math.sin(phase_rad))
    context.stamp_current_source(idx_a, idx_b, phasor)


def stamp_vccs_dc(component, context: StampingContext) -> None:
    """Estampille une source de courant commandée en tension (VCCS)."""
    control = context.circuit.dipoles.get(component.control_dipole_id)
    if control is None:
        return
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    idx_c = context.get_matrix_index(control.node_a)
    idx_d = context.get_matrix_index(control.node_b)
    g = float(component.transconductance)
    if idx_a is not None and idx_c is not None:
        context.matrix_A[idx_a, idx_c] += g
    if idx_a is not None and idx_d is not None:
        context.matrix_A[idx_a, idx_d] -= g
    if idx_b is not None and idx_c is not None:
        context.matrix_A[idx_b, idx_c] -= g
    if idx_b is not None and idx_d is not None:
        context.matrix_A[idx_b, idx_d] += g


def stamp_cccs_dc(component, context: StampingContext) -> None:
    """Estampille une source de courant commandée en courant (CCCS)."""
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    gain = float(component.gain)
    ctrl_idx = context.voltage_source_indices.get(component.control_dipole_id)
    if ctrl_idx is not None:
        if idx_a is not None:
            context.matrix_A[idx_a, ctrl_idx] += gain
        if idx_b is not None:
            context.matrix_A[idx_b, ctrl_idx] -= gain


def stamp_vcvs_dc(component, context: StampingContext) -> None:
    """Estampille une source de tension commandée en tension (VCVS)."""
    control = context.circuit.dipoles.get(component.control_dipole_id)
    if control is None:
        return
    source_idx = context.voltage_source_indices.get(component.id)
    if source_idx is None:
        return
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    idx_c = context.get_matrix_index(control.node_a)
    idx_d = context.get_matrix_index(control.node_b)
    gain = float(component.gain)
    if idx_a is not None:
        context.matrix_A[source_idx, idx_a] = 1
        context.matrix_A[idx_a, source_idx] = 1
    if idx_b is not None:
        context.matrix_A[source_idx, idx_b] = -1
        context.matrix_A[idx_b, source_idx] = -1
    if idx_c is not None:
        context.matrix_A[source_idx, idx_c] -= gain
    if idx_d is not None:
        context.matrix_A[source_idx, idx_d] += gain


def stamp_ccvs_dc(component, context: StampingContext) -> None:
    """Estampille une source de tension commandée en courant (CCVS)."""
    control = context.circuit.dipoles.get(component.control_dipole_id)
    if control is None:
        return
    source_idx = context.voltage_source_indices.get(component.id)
    if source_idx is None:
        return
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    ctrl_idx = context.voltage_source_indices.get(control.id)
    if ctrl_idx is not None:
        if idx_a is not None:
            context.matrix_A[source_idx, idx_a] = 1
            context.matrix_A[idx_a, source_idx] = 1
        if idx_b is not None:
            context.matrix_A[source_idx, idx_b] = -1
            context.matrix_A[idx_b, source_idx] = -1
        context.matrix_A[source_idx, ctrl_idx] -= float(component.transresistance)


def stamp_diode_dc(component, context: StampingContext) -> None:
    """Estampille une diode par linéarisation."""
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    v_a = 0.0 if idx_a is None else float(context.state_vector[idx_a])
    v_b = 0.0 if idx_b is None else float(context.state_vector[idx_b])
    v_d = v_a - v_b
    current, conductance = _compute_diode_linearization(v_d, component)
    i_eq = current - conductance * v_d
    context.stamp_conductance(idx_a, idx_b, conductance)
    context.stamp_current_source(idx_a, idx_b, i_eq)


def _compute_diode_linearization(v_d: float, component) -> tuple[float, float]:
    """Calcule la conductance et le courant linéarisé d'une diode."""
    v_t = component.ideality_factor * component.thermal_voltage
    i_0 = float(component.saturation_current)
    # Modèle: I = I_0 * (exp(V/V_t) - 1)
    if v_d > 10 * v_t:
        current = i_0 * math.exp(v_d / v_t)
        conductance = current / v_t
    elif v_d < -10 * v_t:
        current = -i_0
        conductance = 1e-12
    else:
        current = i_0 * (math.exp(v_d / v_t) - 1)
        conductance = i_0 / v_t * math.exp(v_d / v_t)
    return current, conductance
