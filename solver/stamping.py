"""
Implémentations de stamping polymorphes pour tous les composants de circuit.

Ce module fournit les méthodes stamp_dc(), stamp_ac() et stamp_transient()
pour tous les composants, éliminant les vérifications isinstance dans les solveurs.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    from solver.base_solver import StampingContext


# ---------------------------------------------------------------------------
# 1. Résistances et dipôles passifs équivalents (Switch, Ammeter, Voltmeter)
# ---------------------------------------------------------------------------

def stamp_resistor_dc(component, context: StampingContext) -> None:
    """Estampille une résistance en DC."""
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    resistance = float(getattr(component, "resistance", 0.0))
    if resistance <= 0:
        return
    g = 1.0 / resistance
    context.stamp_conductance(idx_a, idx_b, g)


def stamp_resistor_ac(component, context: StampingContext) -> None:
    """Estampille une résistance en AC (admittance réelle 1/R)."""
    stamp_resistor_dc(component, context)


def stamp_resistor_transient(component, context: StampingContext, dt: float = 0.0) -> None:
    """Estampille une résistance en transitoire (admittance 1/R)."""
    stamp_resistor_dc(component, context)


# ---------------------------------------------------------------------------
# 2. Condensateurs
# ---------------------------------------------------------------------------

def stamp_capacitor_dc(component, context: StampingContext) -> None:
    """Estampille un condensateur en DC (circuit ouvert, no-op)."""
    pass


def stamp_capacitor_ac(component, context: StampingContext) -> None:
    """Estampille un condensateur en AC (admittance jωC)."""
    if component.capacitance <= 0:
        raise ValueError("La capacite doit etre strictement positive")
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    g_eq = 1j * context.omega * component.capacitance
    context.stamp_conductance(idx_a, idx_b, g_eq)


def stamp_capacitor_transient(component, context: StampingContext, dt: float = 0.0) -> None:
    """
    Estampille un condensateur en transitoire (schéma compagnon Backward Euler).
    Conductance équivalente : G_eq = C / dt
    Source d'histoire : I_hist = -G_eq * V_prev
    """
    if component.capacitance <= 0:
        raise ValueError("La capacite doit etre strictement positive")
    time_step = dt if dt > 0 else context.dt
    if time_step <= 0:
        raise ValueError("Le pas de temps doit etre strictement positif")

    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    g_eq = component.capacitance / time_step
    v_prev = float(context.capacitor_prev_voltage.get(component.id, 0.0))
    i_hist = -g_eq * v_prev

    context.stamp_conductance(idx_a, idx_b, g_eq)
    context.stamp_current_source(idx_a, idx_b, i_hist)


# ---------------------------------------------------------------------------
# 3. Inductances
# ---------------------------------------------------------------------------

def stamp_inductor_dc(component, context: StampingContext) -> None:
    """Estampille une inductance en DC (no-op)."""
    pass


def stamp_inductor_ac(component, context: StampingContext) -> None:
    """Estampille une inductance en AC (admittance 1/(jωL))."""
    if component.inductance <= 0:
        raise ValueError("L'inductance doit etre strictement positive")
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    g_eq = 1.0 / (1j * context.omega * component.inductance) if context.omega != 0 else 0.0
    context.stamp_conductance(idx_a, idx_b, g_eq)


def stamp_inductor_transient(component, context: StampingContext, dt: float = 0.0) -> None:
    """
    Estampille une inductance en transitoire (schéma compagnon Backward Euler).
    Conductance équivalente : G_eq = dt / L
    Source d'histoire : I_hist = I_prev
    """
    if component.inductance <= 0:
        raise ValueError("L'inductance doit etre strictement positive")
    time_step = dt if dt > 0 else context.dt
    if time_step <= 0:
        raise ValueError("Le pas de temps doit etre strictement positif")

    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    g_eq = time_step / component.inductance
    i_prev = float(context.inductor_prev_current.get(component.id, 0.0))
    i_hist = i_prev

    context.stamp_conductance(idx_a, idx_b, g_eq)
    context.stamp_current_source(idx_a, idx_b, i_hist)


# ---------------------------------------------------------------------------
# 4. Sources de tension (indépendantes)
# ---------------------------------------------------------------------------

def stamp_voltage_source_dc(component, context: StampingContext) -> None:
    """Estampille une source de tension en DC."""
    source_idx = context.voltage_source_indices.get(component.id)
    if source_idx is None:
        return
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    val = float(component.get_dc_value() if hasattr(component, "get_dc_value") else getattr(component, "dc_voltage", 0.0))
    context.stamp_voltage_source_equation(source_idx, idx_a, idx_b, val)


def stamp_voltage_source_ac(component, context: StampingContext) -> None:
    """Estampille une source de tension en AC (phaseur)."""
    source_idx = context.voltage_source_indices.get(component.id)
    if source_idx is None:
        return
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    if hasattr(component, "get_ac_phasor"):
        phasor = component.get_ac_phasor()
    elif hasattr(component, "get_state") and component.get_state().lower() == "dc":
        phasor = 0.0 + 0.0j
    else:
        amplitude = float(getattr(component, "amplitude", 10.0))
        phase_rad = math.radians(float(getattr(component, "phase", 0.0)))
        phasor = amplitude * (math.cos(phase_rad) + 1j * math.sin(phase_rad))
    context.stamp_voltage_source_equation(source_idx, idx_a, idx_b, phasor)


def stamp_voltage_source_transient(component, context: StampingContext, dt: float = 0.0) -> None:
    """Estampille une source de tension en transitoire à l'instant t."""
    source_idx = context.voltage_source_indices.get(component.id)
    if source_idx is None:
        return
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    t = getattr(context, "time", 0.0)
    if hasattr(component, "get_value_at_time"):
        val = float(component.get_value_at_time(t))
    elif hasattr(component, "get_dc_value"):
        val = float(component.get_dc_value())
    else:
        val = float(getattr(component, "dc_voltage", 0.0))
    context.stamp_voltage_source_equation(source_idx, idx_a, idx_b, val)


# ---------------------------------------------------------------------------
# 5. Sources de courant (indépendantes)
# ---------------------------------------------------------------------------

def stamp_current_source_dc(component, context: StampingContext) -> None:
    """Estampille une source de courant en DC."""
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    val = float(component.get_dc_value() if hasattr(component, "get_dc_value") else getattr(component, "dc_current", 0.0))
    context.stamp_current_source(idx_a, idx_b, val)


def stamp_current_source_ac(component, context: StampingContext) -> None:
    """Estampille une source de courant en AC (phaseur)."""
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    if hasattr(component, "get_ac_phasor"):
        phasor = component.get_ac_phasor()
    elif hasattr(component, "get_state") and component.get_state().lower() == "dc":
        phasor = 0.0 + 0.0j
    else:
        amplitude = float(getattr(component, "amplitude", 1.0))
        phase_rad = math.radians(float(getattr(component, "phase", 0.0)))
        phasor = amplitude * (math.cos(phase_rad) + 1j * math.sin(phase_rad))
    context.stamp_current_source(idx_a, idx_b, phasor)


def stamp_current_source_transient(component, context: StampingContext, dt: float = 0.0) -> None:
    """Estampille une source de courant en transitoire à l'instant t."""
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    t = getattr(context, "time", 0.0)
    if hasattr(component, "get_value_at_time"):
        val = float(component.get_value_at_time(t))
    elif hasattr(component, "get_dc_value"):
        val = float(component.get_dc_value())
    else:
        val = float(getattr(component, "dc_current", 0.0))
    context.stamp_current_source(idx_a, idx_b, val)


# ---------------------------------------------------------------------------
# 6. Sources commandées en tension (VCCS et VCVS)
# ---------------------------------------------------------------------------

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


def stamp_vccs_ac(component, context: StampingContext) -> None:
    """Estampille une source de courant commandée en tension (VCCS) en AC."""
    stamp_vccs_dc(component, context)


def stamp_vccs_transient(component, context: StampingContext, dt: float = 0.0) -> None:
    """Estampille une source de courant commandée en tension (VCCS) en transitoire."""
    stamp_vccs_dc(component, context)


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


def stamp_vcvs_ac(component, context: StampingContext) -> None:
    """Estampille une source de tension commandée en tension (VCVS) en AC."""
    stamp_vcvs_dc(component, context)


def stamp_vcvs_transient(component, context: StampingContext, dt: float = 0.0) -> None:
    """Estampille une source de tension commandée en tension (VCVS) en transitoire."""
    stamp_vcvs_dc(component, context)


# ---------------------------------------------------------------------------
# 7. Sources commandées en courant (CCCS et CCVS)
# ---------------------------------------------------------------------------

def stamp_cccs_dc(component, context: StampingContext) -> None:
    """Estampille une source de courant commandée en courant (CCCS) en DC."""
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    gain = float(component.gain)
    ctrl_idx = context.voltage_source_indices.get(component.control_dipole_id)
    if ctrl_idx is not None:
        if idx_a is not None:
            context.matrix_A[idx_a, ctrl_idx] += gain
        if idx_b is not None:
            context.matrix_A[idx_b, ctrl_idx] -= gain
        return

    # Contrôle par un élément non source de tension
    control = context.circuit.dipoles.get(component.control_dipole_id)
    if control is None:
        return

    if context.solver is not None:
        control_current = context.solver._control_current_from_state(
            context.circuit,
            control,
            context.node_groups,
            context.group_to_idx,
            context.ground_group_id,
            context.state_vector,
            context.voltage_source_indices,
        )
    else:
        control_current = float(getattr(control, "current", 0.0))

    current = gain * control_current
    if idx_a is not None:
        context.vector_Z[idx_a] += current
    if idx_b is not None:
        context.vector_Z[idx_b] -= current


def stamp_cccs_ac(component, context: StampingContext) -> None:
    """Estampille une source de courant commandée en courant (CCCS) en AC."""
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    gain = float(component.gain)
    ctrl_idx = context.voltage_source_indices.get(component.control_dipole_id)
    if ctrl_idx is not None:
        if idx_a is not None:
            context.matrix_A[idx_a, ctrl_idx] += gain
        if idx_b is not None:
            context.matrix_A[idx_b, ctrl_idx] -= gain
        return

    control = context.circuit.dipoles.get(component.control_dipole_id)
    if control is None:
        return

    if context.solver is not None:
        control_current = context.solver._control_current_from_state(
            context.circuit,
            control,
            context.node_groups,
            context.group_to_idx,
            context.ground_group_id,
            context.state_vector,
            context.voltage_source_indices,
            is_ac=True,
            omega=context.omega,
        )
    else:
        control_current = 0.0 + 0.0j

    current = gain * control_current
    if idx_a is not None:
        context.vector_Z[idx_a] += current
    if idx_b is not None:
        context.vector_Z[idx_b] -= current


def stamp_cccs_transient(component, context: StampingContext, dt: float = 0.0) -> None:
    """Estampille une source de courant commandée en courant (CCCS) en transitoire."""
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    gain = float(component.gain)
    ctrl_idx = context.voltage_source_indices.get(component.control_dipole_id)
    if ctrl_idx is not None:
        if idx_a is not None:
            context.matrix_A[idx_a, ctrl_idx] += gain
        if idx_b is not None:
            context.matrix_A[idx_b, ctrl_idx] -= gain
        return

    control = context.circuit.dipoles.get(component.control_dipole_id)
    if control is None:
        return

    time_step = dt if dt > 0 else context.dt
    if context.solver is not None:
        control_current = context.solver._control_current_from_state(
            context.circuit,
            control,
            context.node_groups,
            context.group_to_idx,
            context.ground_group_id,
            context.state_vector,
            context.voltage_source_indices,
            time_value=context.time,
            time_step=time_step,
            capacitor_prev_voltage=context.capacitor_prev_voltage,
            inductor_prev_current=context.inductor_prev_current,
        )
    else:
        control_current = float(getattr(control, "current", 0.0))

    current = gain * control_current
    if idx_a is not None:
        context.vector_Z[idx_a] += current
    if idx_b is not None:
        context.vector_Z[idx_b] -= current


def stamp_ccvs_dc(component, context: StampingContext) -> None:
    """Estampille une source de tension commandée en courant (CCVS) en DC."""
    control = context.circuit.dipoles.get(component.control_dipole_id)
    if control is None:
        return
    source_idx = context.voltage_source_indices.get(component.id)
    if source_idx is None:
        return
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    if idx_a is not None:
        context.matrix_A[source_idx, idx_a] = 1
        context.matrix_A[idx_a, source_idx] = 1
    if idx_b is not None:
        context.matrix_A[source_idx, idx_b] = -1
        context.matrix_A[idx_b, source_idx] = -1

    ctrl_idx = context.voltage_source_indices.get(control.id)
    if ctrl_idx is not None:
        context.matrix_A[source_idx, ctrl_idx] -= float(component.transresistance)
    else:
        if context.solver is not None:
            control_current = context.solver._control_current_from_state(
                context.circuit,
                control,
                context.node_groups,
                context.group_to_idx,
                context.ground_group_id,
                context.state_vector,
                context.voltage_source_indices,
            )
        else:
            control_current = float(getattr(control, "current", 0.0))
        context.vector_Z[source_idx] = float(component.transresistance) * control_current


def stamp_ccvs_ac(component, context: StampingContext) -> None:
    """Estampille une source de tension commandée en courant (CCVS) en AC."""
    control = context.circuit.dipoles.get(component.control_dipole_id)
    if control is None:
        return
    source_idx = context.voltage_source_indices.get(component.id)
    if source_idx is None:
        return
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    if idx_a is not None:
        context.matrix_A[source_idx, idx_a] = 1
        context.matrix_A[idx_a, source_idx] = 1
    if idx_b is not None:
        context.matrix_A[source_idx, idx_b] = -1
        context.matrix_A[idx_b, source_idx] = -1

    ctrl_idx = context.voltage_source_indices.get(control.id)
    if ctrl_idx is not None:
        context.matrix_A[source_idx, ctrl_idx] -= float(component.transresistance)
    else:
        if context.solver is not None:
            control_current = context.solver._control_current_from_state(
                context.circuit,
                control,
                context.node_groups,
                context.group_to_idx,
                context.ground_group_id,
                context.state_vector,
                context.voltage_source_indices,
                is_ac=True,
                omega=context.omega,
            )
        else:
            control_current = 0.0 + 0.0j
        context.vector_Z[source_idx] = float(component.transresistance) * control_current


def stamp_ccvs_transient(component, context: StampingContext, dt: float = 0.0) -> None:
    """Estampille une source de tension commandée en courant (CCVS) en transitoire."""
    control = context.circuit.dipoles.get(component.control_dipole_id)
    if control is None:
        return
    source_idx = context.voltage_source_indices.get(component.id)
    if source_idx is None:
        return
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    if idx_a is not None:
        context.matrix_A[source_idx, idx_a] = 1
        context.matrix_A[idx_a, source_idx] = 1
    if idx_b is not None:
        context.matrix_A[source_idx, idx_b] = -1
        context.matrix_A[idx_b, source_idx] = -1

    ctrl_idx = context.voltage_source_indices.get(control.id)
    if ctrl_idx is not None:
        context.matrix_A[source_idx, ctrl_idx] -= float(component.transresistance)
    else:
        time_step = dt if dt > 0 else context.dt
        if context.solver is not None:
            control_current = context.solver._control_current_from_state(
                context.circuit,
                control,
                context.node_groups,
                context.group_to_idx,
                context.ground_group_id,
                context.state_vector,
                context.voltage_source_indices,
                time_value=context.time,
                time_step=time_step,
                capacitor_prev_voltage=context.capacitor_prev_voltage,
                inductor_prev_current=context.inductor_prev_current,
            )
        else:
            control_current = float(getattr(control, "current", 0.0))
        context.vector_Z[source_idx] = float(component.transresistance) * control_current


# ---------------------------------------------------------------------------
# 8. Diodes et LEDs
# ---------------------------------------------------------------------------

def _limit_diode_voltage(v_new: float, v_old: float, vt: float = 0.026) -> float:
    """Limiteur de tension type SPICE pnjlim pour assurer une convergence rapide et robuste."""
    if v_new > 0.0 and v_new > v_old:
        if v_old <= 0.0:
            return min(v_new, 0.6)
        elif v_new - v_old > 2.0 * vt:
            delta = v_new - v_old
            return v_old + 2.0 * vt + math.log(1.0 + (delta - 2.0 * vt) / vt) * vt
    return v_new


def stamp_diode_dc(component, context: StampingContext) -> None:
    """Estampille une diode ou LED par linéarisation exponentielle de Shockley avec limitation de tension."""
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    v_a = 0.0 if idx_a is None else float(context.state_vector[idx_a])
    v_b = 0.0 if idx_b is None else float(context.state_vector[idx_b])
    v_d_raw = v_a - v_b
    v_d_old = float(getattr(component, "voltage", 0.0))
    vt = max(float(getattr(component, "ideality_factor", 1.0)) * float(getattr(component, "thermal_voltage", 0.026)), 1e-6)
    v_d = _limit_diode_voltage(v_d_raw, v_d_old, vt)
    current, conductance = _compute_diode_linearization(v_d, component)
    i_eq = current - conductance * v_d
    context.stamp_conductance(idx_a, idx_b, conductance)
    context.stamp_current_source(idx_a, idx_b, i_eq)


def stamp_diode_ac(component, context: StampingContext) -> None:
    """Estampille une diode en AC (admittance dynamique aux bornes du point de repos)."""
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    v_d = float(getattr(component, "voltage", 0.0))
    _, conductance = _compute_diode_linearization(v_d, component)
    context.stamp_conductance(idx_a, idx_b, conductance)


def stamp_diode_transient(component, context: StampingContext, dt: float = 0.0) -> None:
    """Estampille une diode en transitoire."""
    stamp_diode_dc(component, context)


def _compute_diode_linearization(v_d: float, component) -> tuple[float, float]:
    """Calcule le courant et la conductance linéarisée d'une diode (modèle Shockley borné)."""
    isrc = float(getattr(component, "saturation_current", 1e-12))
    n = max(float(getattr(component, "ideality_factor", 1.0)), 1e-6)
    vt = max(float(getattr(component, "thermal_voltage", 0.026)), 1e-6)
    exp_arg = max(-40.0, min(40.0, float(v_d) / (n * vt)))
    exp_val = float(np.exp(exp_arg))
    current = isrc * (exp_val - 1.0)
    conductance = (isrc / (n * vt)) * exp_val
    return current, conductance


# ---------------------------------------------------------------------------
# 9. Composants divers / No-op
# ---------------------------------------------------------------------------

def stamp_noop(component, context: StampingContext, *args, **kwargs) -> None:
    """Opération nulle pour les composants passifs ou symboles (Ground, etc.)."""
    pass
