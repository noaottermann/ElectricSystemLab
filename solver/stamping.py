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
    v_a = 0.0 if idx_a is None else float(np.real(context.state_vector[idx_a]))
    v_b = 0.0 if idx_b is None else float(np.real(context.state_vector[idx_b]))
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
# 9. Diodes Zener
# ---------------------------------------------------------------------------

def stamp_zener_diode_dc(component, context: StampingContext) -> None:
    """Estampille une diode Zener avec conduction directe, blocage et claquage Zener."""
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    v_a = 0.0 if idx_a is None else float(np.real(context.state_vector[idx_a]))
    v_b = 0.0 if idx_b is None else float(np.real(context.state_vector[idx_b]))
    v_d_raw = v_a - v_b
    v_d_old = float(getattr(component, "voltage", 0.0))
    vt = max(float(getattr(component, "ideality_factor", 1.0)) * float(getattr(component, "thermal_voltage", 0.026)), 1e-6)
    v_d = _limit_diode_voltage(v_d_raw, v_d_old, vt)

    vz = float(getattr(component, "zener_voltage", 5.1))
    rz = max(float(getattr(component, "zener_resistance", 10.0)), 1e-3)
    izk = float(getattr(component, "zener_current", 1e-3))

    if v_d <= -vz:
        # Régime de conduction Zener inverse
        gz = 1.0 / rz
        current = -izk - gz * (-v_d - vz)
        conductance = gz
    else:
        # Régime direct ou bloqué
        current, conductance = _compute_diode_linearization(v_d, component)

    i_eq = current - conductance * v_d
    context.stamp_conductance(idx_a, idx_b, conductance)
    context.stamp_current_source(idx_a, idx_b, i_eq)


def stamp_zener_diode_ac(component, context: StampingContext) -> None:
    """Estampille une diode Zener en AC."""
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    v_d = float(getattr(component, "voltage", 0.0))
    vz = float(getattr(component, "zener_voltage", 5.1))
    rz = max(float(getattr(component, "zener_resistance", 10.0)), 1e-3)

    if v_d <= -vz:
        conductance = 1.0 / rz
    else:
        _, conductance = _compute_diode_linearization(v_d, component)

    context.stamp_conductance(idx_a, idx_b, conductance)


def stamp_zener_diode_transient(component, context: StampingContext, dt: float = 0.0) -> None:
    """Estampille une diode Zener en transitoire."""
    stamp_zener_diode_dc(component, context)


# ---------------------------------------------------------------------------
# 10. Potentiomètres
# ---------------------------------------------------------------------------

def stamp_potentiometer_dc(component, context: StampingContext) -> None:
    """Estampille un potentiomètre (2 résistances en diviseur de tension)."""
    idx_a = context.get_matrix_index(component.node_a)
    idx_w = context.get_matrix_index(component.node_w)
    idx_b = context.get_matrix_index(component.node_b)

    r1 = float(getattr(component, "r1", 5000.0))
    r2 = float(getattr(component, "r2", 5000.0))

    g1 = 1.0 / max(r1, 1e-3)
    g2 = 1.0 / max(r2, 1e-3)

    context.stamp_conductance(idx_a, idx_w, g1)
    context.stamp_conductance(idx_w, idx_b, g2)


def stamp_potentiometer_ac(component, context: StampingContext) -> None:
    """Estampille un potentiomètre en AC."""
    stamp_potentiometer_dc(component, context)


def stamp_potentiometer_transient(component, context: StampingContext, dt: float = 0.0) -> None:
    """Estampille un potentiomètre en transitoire."""
    stamp_potentiometer_dc(component, context)


# ---------------------------------------------------------------------------
# 11. Amplificateurs Opérationnels (AOP)
# ---------------------------------------------------------------------------

def stamp_opamp_dc(component, context: StampingContext) -> None:
    """Estampille un AOP avec impédance d'entrée, transconductance et résistance de sortie."""
    idx_p = context.get_matrix_index(component.node_in_plus)
    idx_m = context.get_matrix_index(component.node_in_minus)
    idx_out = context.get_matrix_index(component.node_out)

    r_in = max(float(getattr(component, "r_in", 1e6)), 1.0)
    r_out = max(float(getattr(component, "r_out", 10.0)), 1e-3)
    gain = float(getattr(component, "gain", 1e5))

    # Impédance d'entrée différentielle
    context.stamp_conductance(idx_p, idx_m, 1.0 / r_in)

    # Étage de sortie Thévenin / Norton : G_out = 1/R_out, gm = Gain / R_out
    g_out = 1.0 / r_out
    gm = gain / r_out

    # Conductance de sortie sur node_out
    if idx_out is not None:
        context.matrix_A[idx_out, idx_out] += g_out
        if idx_p is not None:
            context.matrix_A[idx_out, idx_p] -= gm
        if idx_m is not None:
            context.matrix_A[idx_out, idx_m] += gm


def stamp_opamp_ac(component, context: StampingContext) -> None:
    """Estampille un AOP en AC."""
    stamp_opamp_dc(component, context)


def stamp_opamp_transient(component, context: StampingContext, dt: float = 0.0) -> None:
    """Estampille un AOP en transitoire avec saturation de tension +/- Vsat."""
    idx_p = context.get_matrix_index(component.node_in_plus)
    idx_m = context.get_matrix_index(component.node_in_minus)
    idx_out = context.get_matrix_index(component.node_out)

    r_in = max(float(getattr(component, "r_in", 1e6)), 1.0)
    r_out = max(float(getattr(component, "r_out", 10.0)), 1e-3)
    gain = float(getattr(component, "gain", 1e5))
    v_sat_pos = float(getattr(component, "v_sat_pos", 15.0))
    v_sat_neg = float(getattr(component, "v_sat_neg", -15.0))

    context.stamp_conductance(idx_p, idx_m, 1.0 / r_in)

    vp = 0.0 if idx_p is None else float(np.real(context.state_vector[idx_p]))
    vm = 0.0 if idx_m is None else float(np.real(context.state_vector[idx_m]))
    v_diff = vp - vm
    v_target = max(v_sat_neg, min(v_sat_pos, gain * v_diff))

    g_out = 1.0 / r_out
    if idx_out is not None:
        context.matrix_A[idx_out, idx_out] += g_out
        context.vector_Z[idx_out] += g_out * v_target


# ---------------------------------------------------------------------------
# 12. Transformateurs
# ---------------------------------------------------------------------------

def stamp_transformer_dc(component, context: StampingContext) -> None:
    """Estampille un transformateur en DC (faibles résistances d'enroulement)."""
    idx_p_pos = context.get_matrix_index(component.node_p_pos)
    idx_p_neg = context.get_matrix_index(component.node_p_neg)
    idx_s_pos = context.get_matrix_index(component.node_s_pos)
    idx_s_neg = context.get_matrix_index(component.node_s_neg)

    # Résistances d'enroulements primaires et secondaires
    context.stamp_conductance(idx_p_pos, idx_p_neg, 1.0 / 0.1)
    context.stamp_conductance(idx_s_pos, idx_s_neg, 1.0 / 0.1)


def stamp_transformer_ac(component, context: StampingContext) -> None:
    """Estampille un transformateur en AC via la matrice d'inductances couplées."""
    idx_p_pos = context.get_matrix_index(component.node_p_pos)
    idx_p_neg = context.get_matrix_index(component.node_p_neg)
    idx_s_pos = context.get_matrix_index(component.node_s_pos)
    idx_s_neg = context.get_matrix_index(component.node_s_neg)

    ratio = max(float(getattr(component, "ratio", 1.0)), 1e-4)
    l1 = max(float(getattr(component, "l1", 1e-3)), 1e-6)
    l2 = max(float(getattr(component, "l2", l1 * (ratio ** 2))), 1e-6)
    k = max(0.01, min(0.9999, float(getattr(component, "coupling", 0.99))))
    m = k * math.sqrt(l1 * l2)

    det_l = (l1 * l2) - (m ** 2)
    omega = max(context.omega, 1e-6)
    factor = 1.0 / (1j * omega * det_l)

    y11 = factor * l2
    y22 = factor * l1
    y12 = -factor * m

    context.stamp_conductance(idx_p_pos, idx_p_neg, y11)
    context.stamp_conductance(idx_s_pos, idx_s_neg, y22)

    # Couplage mutuel entre primaire et secondaire
    if idx_p_pos is not None and idx_s_pos is not None:
        context.matrix_A[idx_p_pos, idx_s_pos] += y12
        context.matrix_A[idx_s_pos, idx_p_pos] += y12
    if idx_p_pos is not None and idx_s_neg is not None:
        context.matrix_A[idx_p_pos, idx_s_neg] -= y12
        context.matrix_A[idx_s_neg, idx_p_pos] -= y12
    if idx_p_neg is not None and idx_s_pos is not None:
        context.matrix_A[idx_p_neg, idx_s_pos] -= y12
        context.matrix_A[idx_s_pos, idx_p_neg] -= y12
    if idx_p_neg is not None and idx_s_neg is not None:
        context.matrix_A[idx_p_neg, idx_s_neg] += y12
        context.matrix_A[idx_s_neg, idx_p_neg] += y12


def stamp_transformer_transient(component, context: StampingContext, dt: float = 0.0) -> None:
    """Estampille un transformateur en transitoire."""
    stamp_transformer_dc(component, context)


# ---------------------------------------------------------------------------
# 13. Transistors Bipolaires (BJT NPN & PNP)
# ---------------------------------------------------------------------------

def stamp_transistor_dc(component, context: StampingContext) -> None:
    """Estampille un transistor BJT (modèle petit-signal et grand-signal avec gain en courant bêta)."""
    idx_c = context.get_matrix_index(component.node_collector)
    idx_b = context.get_matrix_index(component.node_base)
    idx_e = context.get_matrix_index(component.node_emitter)

    beta = max(float(getattr(component, "beta", 100.0)), 1.0)
    r_in = max(float(getattr(component, "r_in", 1000.0)), 1.0)
    v_be0 = float(getattr(component, "v_be0", 0.7))
    is_pnp = str(getattr(component, "transistor_type", "NPN")).upper() == "PNP"

    vb = 0.0 if idx_b is None else float(np.real(context.state_vector[idx_b]))
    ve = 0.0 if idx_e is None else float(np.real(context.state_vector[idx_e]))
    vbe = (ve - vb) if is_pnp else (vb - ve)

    g_be = 1.0 / r_in
    gm = beta * g_be

    # Jonction Base-Émetteur
    context.stamp_conductance(idx_b, idx_e, g_be)
    i_offset = g_be * v_be0
    if is_pnp:
        context.stamp_current_source(idx_e, idx_b, i_offset)
    else:
        context.stamp_current_source(idx_b, idx_e, i_offset)

    # Source de courant commandée Ic = beta * Ib = gm * (Vb - Ve - Vbe0)
    if not is_pnp:
        # NPN : Courant entre C et E
        if idx_c is not None:
            if idx_b is not None:
                context.matrix_A[idx_c, idx_b] += gm
            if idx_e is not None:
                context.matrix_A[idx_c, idx_e] -= gm
            context.vector_Z[idx_c] += gm * v_be0
        if idx_e is not None:
            if idx_b is not None:
                context.matrix_A[idx_e, idx_b] -= gm
            if idx_e is not None:
                context.matrix_A[idx_e, idx_e] += gm
            context.vector_Z[idx_e] -= gm * v_be0
    else:
        # PNP : Courant entre E et C
        if idx_c is not None:
            if idx_e is not None:
                context.matrix_A[idx_c, idx_e] += gm
            if idx_b is not None:
                context.matrix_A[idx_c, idx_b] -= gm
            context.vector_Z[idx_c] += gm * v_be0
        if idx_e is not None:
            if idx_e is not None:
                context.matrix_A[idx_e, idx_e] -= gm
            if idx_b is not None:
                context.matrix_A[idx_e, idx_b] += gm
            context.vector_Z[idx_e] -= gm * v_be0


def stamp_transistor_ac(component, context: StampingContext) -> None:
    """Estampille un transistor BJT en AC (modèle hybride en pi)."""
    idx_c = context.get_matrix_index(component.node_collector)
    idx_b = context.get_matrix_index(component.node_base)
    idx_e = context.get_matrix_index(component.node_emitter)

    beta = max(float(getattr(component, "beta", 100.0)), 1.0)
    r_in = max(float(getattr(component, "r_in", 1000.0)), 1.0)
    g_be = 1.0 / r_in
    gm = beta * g_be

    context.stamp_conductance(idx_b, idx_e, g_be)
    if idx_c is not None:
        if idx_b is not None:
            context.matrix_A[idx_c, idx_b] += gm
        if idx_e is not None:
            context.matrix_A[idx_c, idx_e] -= gm
    if idx_e is not None:
        if idx_b is not None:
            context.matrix_A[idx_e, idx_b] -= gm
        if idx_e is not None:
            context.matrix_A[idx_e, idx_e] += gm


def stamp_transistor_transient(component, context: StampingContext, dt: float = 0.0) -> None:
    """Estampille un transistor BJT en transitoire."""
    stamp_transistor_dc(component, context)


# ---------------------------------------------------------------------------
# 14. Transistors MOSFET (NMOS & PMOS)
# ---------------------------------------------------------------------------

def stamp_mosfet_dc(component, context: StampingContext) -> None:
    """Estampille un transistor MOSFET (modèle Shichman-Hodges)."""
    idx_d = context.get_matrix_index(component.node_drain)
    idx_g = context.get_matrix_index(component.node_gate)
    idx_s = context.get_matrix_index(component.node_source)

    v_th = float(getattr(component, "v_threshold", 2.0))
    kp = float(getattr(component, "transconductance", 0.02))
    is_pmos = str(getattr(component, "mosfet_type", "NMOS")).upper() == "PMOS"

    vg = 0.0 if idx_g is None else float(np.real(context.state_vector[idx_g]))
    vs = 0.0 if idx_s is None else float(np.real(context.state_vector[idx_s]))
    vd = 0.0 if idx_d is None else float(np.real(context.state_vector[idx_d]))

    vgs = (vs - vg) if is_pmos else (vg - vs)
    vds = (vs - vd) if is_pmos else (vd - vs)

    vov = vgs - v_th
    if vov <= 0:
        # Coupure
        gm = 0.0
        gds = 1e-9
        i_ds = 0.0
    elif vds < vov:
        # Régime linéaire
        i_ds = kp * (vov * vds - 0.5 * (vds ** 2))
        gm = kp * vds
        gds = kp * (vov - vds)
    else:
        # Saturation
        i_ds = 0.5 * kp * (vov ** 2)
        gm = kp * vov
        gds = 1e-4

    i_eq = i_ds - gm * vgs - gds * vds
    context.stamp_conductance(idx_d, idx_s, gds)

    if not is_pmos:
        if idx_d is not None:
            if idx_g is not None:
                context.matrix_A[idx_d, idx_g] += gm
            if idx_s is not None:
                context.matrix_A[idx_d, idx_s] -= gm
            context.vector_Z[idx_d] -= i_eq
        if idx_s is not None:
            if idx_g is not None:
                context.matrix_A[idx_s, idx_g] -= gm
            if idx_s is not None:
                context.matrix_A[idx_s, idx_s] += gm
            context.vector_Z[idx_s] += i_eq


def stamp_mosfet_ac(component, context: StampingContext) -> None:
    """Estampille un transistor MOSFET en AC."""
    stamp_mosfet_dc(component, context)


def stamp_mosfet_transient(component, context: StampingContext, dt: float = 0.0) -> None:
    """Estampille un transistor MOSFET en transitoire."""
    stamp_mosfet_dc(component, context)


# ---------------------------------------------------------------------------
# 15. Comparateurs
# ---------------------------------------------------------------------------

def stamp_comparator_dc(component, context: StampingContext) -> None:
    """Estampille un comparateur analogique avec seuil et hystérésis."""
    idx_p = context.get_matrix_index(component.node_in_plus)
    idx_m = context.get_matrix_index(component.node_in_minus)
    idx_out = context.get_matrix_index(component.node_out)

    vp = 0.0 if idx_p is None else float(np.real(context.state_vector[idx_p]))
    vm = 0.0 if idx_m is None else float(np.real(context.state_vector[idx_m]))
    v_diff = vp - vm
    hys = float(getattr(component, "hysteresis", 0.05))
    v_sat_pos = float(getattr(component, "v_sat_pos", 5.0))
    v_sat_neg = float(getattr(component, "v_sat_neg", 0.0))

    if v_diff > hys:
        v_target = v_sat_pos
        component._last_state = 1.0
    elif v_diff < -hys:
        v_target = v_sat_neg
        component._last_state = -1.0
    else:
        v_target = v_sat_pos if getattr(component, "_last_state", 1.0) > 0 else v_sat_neg

    g_out = 1.0 / 10.0
    if idx_out is not None:
        context.matrix_A[idx_out, idx_out] += g_out
        context.vector_Z[idx_out] += g_out * v_target


def stamp_comparator_ac(component, context: StampingContext) -> None:
    """Estampille un comparateur en AC."""
    stamp_comparator_dc(component, context)


def stamp_comparator_transient(component, context: StampingContext, dt: float = 0.0) -> None:
    """Estampille un comparateur en transitoire."""
    stamp_comparator_dc(component, context)


# ---------------------------------------------------------------------------
# 16. Sources Impulsionnelles / Horloges
# ---------------------------------------------------------------------------

def stamp_pulse_voltage_source_dc(component, context: StampingContext) -> None:
    """Estampille une source impulsionnelle en DC (tension initiale)."""
    source_idx = context.voltage_source_indices.get(component.id)
    if source_idx is None:
        return
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    v_init = float(getattr(component, "v_initial", 0.0))

    context.stamp_voltage_source(idx_a, idx_b, source_idx, v_init)


def stamp_pulse_voltage_source_ac(component, context: StampingContext) -> None:
    """Estampille une source impulsionnelle en AC."""
    source_idx = context.voltage_source_indices.get(component.id)
    if source_idx is None:
        return
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    v_pulsed = float(getattr(component, "v_pulsed", 5.0))
    v_init = float(getattr(component, "v_initial", 0.0))
    amplitude = (v_pulsed - v_init) / 2.0

    context.stamp_voltage_source(idx_a, idx_b, source_idx, amplitude)


def stamp_pulse_voltage_source_transient(component, context: StampingContext, dt: float = 0.0) -> None:
    """Estampille une source impulsionnelle en transitoire avec tension dépendante du temps."""
    source_idx = context.voltage_source_indices.get(component.id)
    if source_idx is None:
        return
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    v_instant = float(component.get_value_at_time(context.time))

    context.stamp_voltage_source(idx_a, idx_b, source_idx, v_instant)


# ---------------------------------------------------------------------------
# 17. Portes Logiques Combinatoires
# ---------------------------------------------------------------------------

def stamp_logic_gate_dc(component, context: StampingContext) -> None:
    """Estampille une porte logique en DC avec sortie Thévenin équivalente."""
    idx_out = context.get_matrix_index(component.node_out)
    if idx_out is None:
        return

    r_out = max(float(getattr(component, "r_out", 50.0)), 0.1)
    g_out = 1.0 / r_out
    v_target = float(component.evaluate_output_voltage())

    context.matrix_A[idx_out, idx_out] += g_out
    context.vector_Z[idx_out] += g_out * v_target


def stamp_logic_gate_ac(component, context: StampingContext) -> None:
    """Estampille une porte logique en AC."""
    idx_out = context.get_matrix_index(component.node_out)
    if idx_out is None:
        return
    r_out = max(float(getattr(component, "r_out", 50.0)), 0.1)
    context.matrix_A[idx_out, idx_out] += 1.0 / r_out


def stamp_logic_gate_transient(component, context: StampingContext, dt: float = 0.0) -> None:
    """Estampille une porte logique en transitoire."""
    stamp_logic_gate_dc(component, context)


# ---------------------------------------------------------------------------
# 18. Fusibles
# ---------------------------------------------------------------------------

def stamp_fuse_dc(component, context: StampingContext) -> None:
    """Estampille un fusible en DC."""
    idx_a = context.get_matrix_index(component.node_a)
    idx_b = context.get_matrix_index(component.node_b)
    resistance = float(getattr(component, "resistance", 0.01))
    g = 1.0 / max(resistance, 1e-6)
    context.stamp_conductance(idx_a, idx_b, g)


def stamp_fuse_ac(component, context: StampingContext) -> None:
    """Estampille un fusible en AC."""
    stamp_fuse_dc(component, context)


def stamp_fuse_transient(component, context: StampingContext, dt: float = 0.0) -> None:
    """Estampille un fusible en transitoire et met à jour son état thermique."""
    time_step = dt if dt > 0 else context.dt
    current = float(getattr(component, "current", 0.0))
    component.update_thermal_energy(current, time_step)
    stamp_fuse_dc(component, context)


# ---------------------------------------------------------------------------
# 19. Composants divers / No-op
# ---------------------------------------------------------------------------

def stamp_noop(component, context: StampingContext, *args, **kwargs) -> None:
    """Opération nulle pour les composants passifs ou symboles (Ground, etc.)."""
    pass
