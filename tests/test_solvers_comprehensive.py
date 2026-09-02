"""
Tests unitaires et d'intégration complets pour les modules du solveur :
- solver.stamping (toutes les fonctions de stamp DC/AC/Transitoire pour chaque composant)
- solver.utils (toutes les fonctions de découpage de groupes, MNA, calcul de sources dépendantes)
- solver.base_solver, dc_solver, ac_solver, transient_solver (cas limites et robustesse)
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from model.circuit import Circuit
from model.components import (
    Capacitor,
    CurrentControlledCurrentSource,
    CurrentControlledVoltageSource,
    CurrentSource,
    CurrentSourceAC,
    CurrentSourceDC,
    Diode,
    Ground,
    Inductor,
    LED,
    OpAmp,
    Resistor,
    Switch,
    Transformer,
    Transistor,
    VoltageControlledCurrentSource,
    VoltageControlledVoltageSource,
    VoltageSource,
    VoltageSourceAC,
    VoltageSourceDC,
    Voltmeter,
    Ammeter,
)
from solver import stamping, utils
from solver.base_solver import BaseSolver, StampingContext
from solver.dc_solver import DCSolver
from solver.ac_solver import ACSolver
from solver.transient_solver import TransientSolver
from solver.stamping_registry import validate_registry


def _create_context_2nodes(size: int = 2, total_vars: int = 3) -> StampingContext:
    circuit = Circuit()
    n1 = circuit.create_node(0, 0, is_ground=True)
    n2 = circuit.create_node(100, 0)
    matrix_a = np.zeros((total_vars, total_vars), dtype=np.complex128)
    vector_z = np.zeros(total_vars, dtype=np.complex128)
    node_groups = {n1.id: 1, n2.id: 2}
    group_to_idx = {2: 0}
    ground_group_id = 1
    voltage_source_indices = {10: 1}
    state_vector = np.zeros(total_vars, dtype=np.complex128)
    return StampingContext(
        circuit=circuit,
        matrix_A=matrix_a,
        vector_Z=vector_z,
        node_groups=node_groups,
        group_to_idx=group_to_idx,
        ground_group_id=ground_group_id,
        voltage_source_indices=voltage_source_indices,
        state_vector=state_vector,
        omega=2 * math.pi * 1000.0,
        dt=0.001,
        time=0.01,
        capacitor_prev_voltage={1: 0.0},
        inductor_prev_current={2: 0.0},
    )


# ==============================================================================
# 1. Tests Stamping Functions Direct
# ==============================================================================

def test_stamping_resistor_dc_ac_transient() -> None:
    ctx = _create_context_2nodes()
    circuit = ctx.circuit
    n1, n2 = list(circuit.nodes.values())
    r = Resistor(1, n1, n2, resistance=100.0)

    stamping.stamp_resistor_dc(r, ctx)
    assert abs(ctx.matrix_A[0, 0] - 0.01) < 1e-12

    ctx.matrix_A.fill(0)
    stamping.stamp_resistor_ac(r, ctx)
    assert abs(ctx.matrix_A[0, 0] - 0.01) < 1e-12

    ctx.matrix_A.fill(0)
    stamping.stamp_resistor_transient(r, ctx)
    assert abs(ctx.matrix_A[0, 0] - 0.01) < 1e-12


def test_stamping_capacitor_ac_transient() -> None:
    ctx = _create_context_2nodes()
    circuit = ctx.circuit
    n1, n2 = list(circuit.nodes.values())
    c = Capacitor(1, n1, n2, capacitance=1e-6)

    stamping.stamp_capacitor_ac(c, ctx)
    expected_admittance = 1j * ctx.omega * 1e-6
    assert abs(ctx.matrix_A[0, 0] - expected_admittance) < 1e-12

    ctx.matrix_A.fill(0)
    stamping.stamp_capacitor_transient(c, ctx)
    expected_geq = 1e-6 / ctx.dt
    assert abs(ctx.matrix_A[0, 0] - expected_geq) < 1e-12
    assert abs(ctx.vector_Z[0] - (expected_geq * 0.0)) < 1e-12


def test_stamping_inductor_ac_transient() -> None:
    ctx = _create_context_2nodes()
    circuit = ctx.circuit
    n1, n2 = list(circuit.nodes.values())
    l = Inductor(2, n1, n2, inductance=1e-3)

    stamping.stamp_inductor_ac(l, ctx)
    expected_admittance = 1.0 / (1j * ctx.omega * 1e-3)
    assert abs(ctx.matrix_A[0, 0] - expected_admittance) < 1e-12

    ctx.matrix_A.fill(0)
    stamping.stamp_inductor_transient(l, ctx)
    expected_geq = ctx.dt / 1e-3
    assert abs(ctx.matrix_A[0, 0] - expected_geq) < 1e-12


def test_stamping_voltage_source_dc_ac_transient() -> None:
    ctx = _create_context_2nodes()
    circuit = ctx.circuit
    n1, n2 = list(circuit.nodes.values())
    v_dc = VoltageSourceDC(10, n1, n2, dc_voltage=12.0)

    stamping.stamp_voltage_source_dc(v_dc, ctx)
    assert abs(ctx.vector_Z[1] - 12.0) < 1e-12
    assert abs(ctx.matrix_A[0, 1] - (-1.0)) < 1e-12
    assert abs(ctx.matrix_A[1, 0] - (-1.0)) < 1e-12

    ctx.matrix_A.fill(0)
    ctx.vector_Z.fill(0)
    v_ac = VoltageSourceAC(10, n1, n2, amplitude=5.0, phase=0.0)
    stamping.stamp_voltage_source_ac(v_ac, ctx)
    assert abs(ctx.vector_Z[1] - 5.0) < 1e-12

    ctx.matrix_A.fill(0)
    ctx.vector_Z.fill(0)
    stamping.stamp_voltage_source_transient(v_dc, ctx)
    assert abs(ctx.vector_Z[1] - 12.0) < 1e-12


def test_stamping_current_source_dc_ac_transient() -> None:
    ctx = _create_context_2nodes()
    circuit = ctx.circuit
    n1, n2 = list(circuit.nodes.values())
    i_dc = CurrentSourceDC(20, n1, n2, dc_current=2.5)

    stamping.stamp_current_source_dc(i_dc, ctx)
    assert abs(ctx.vector_Z[0] - 2.5) < 1e-12

    ctx.vector_Z.fill(0)
    i_ac = CurrentSourceAC(20, n1, n2, amplitude=1.5, phase=90.0)
    stamping.stamp_current_source_ac(i_ac, ctx)
    assert abs(ctx.vector_Z[0] - 1.5j) < 1e-6

    ctx.vector_Z.fill(0)
    stamping.stamp_current_source_transient(i_dc, ctx)
    assert abs(ctx.vector_Z[0] - 2.5) < 1e-12


def test_stamping_controlled_sources() -> None:
    ctx = _create_context_2nodes(total_vars=4)
    circuit = ctx.circuit
    n1, n2 = list(circuit.nodes.values())

    # VCCS
    r_ctrl = Resistor(30, n1, n2)
    circuit.add_dipole(r_ctrl)
    vccs = VoltageControlledCurrentSource(31, n1, n2, control_dipole_id=30, transconductance=0.05)
    stamping.stamp_vccs_dc(vccs, ctx)
    assert abs(ctx.matrix_A[0, 0] - 0.05) < 1e-12

    ctx.matrix_A.fill(0)
    stamping.stamp_vccs_ac(vccs, ctx)
    assert abs(ctx.matrix_A[0, 0] - 0.05) < 1e-12

    ctx.matrix_A.fill(0)
    stamping.stamp_vccs_transient(vccs, ctx)
    assert abs(ctx.matrix_A[0, 0] - 0.05) < 1e-12

    # VCVS
    ctx.voltage_source_indices[32] = 2
    vcvs = VoltageControlledVoltageSource(32, n1, n2, control_dipole_id=30, gain=10.0)
    stamping.stamp_vcvs_dc(vcvs, ctx)
    stamping.stamp_vcvs_ac(vcvs, ctx)
    stamping.stamp_vcvs_transient(vcvs, ctx)

    # CCVS
    ctx.voltage_source_indices[33] = 3
    ccvs = CurrentControlledVoltageSource(33, n1, n2, control_dipole_id=30, transresistance=50.0)
    stamping.stamp_ccvs_dc(ccvs, ctx)
    stamping.stamp_ccvs_ac(ccvs, ctx)
    stamping.stamp_ccvs_transient(ccvs, ctx)

    # CCCS
    cccs = CurrentControlledCurrentSource(34, n1, n2, control_dipole_id=30, gain=2.0)
    stamping.stamp_cccs_dc(cccs, ctx)
    stamping.stamp_cccs_ac(cccs, ctx)
    stamping.stamp_cccs_transient(cccs, ctx)


def test_stamping_diode_and_noop() -> None:
    ctx = _create_context_2nodes()
    circuit = ctx.circuit
    n1, n2 = list(circuit.nodes.values())
    diode = Diode(40, n1, n2)

    stamping.stamp_diode_dc(diode, ctx)
    stamping.stamp_diode_ac(diode, ctx)
    stamping.stamp_diode_transient(diode, ctx)

def test_stamping_4nodes_floating() -> None:
    circuit = Circuit()
    n1 = circuit.create_node(0, 0, is_ground=True)
    n2 = circuit.create_node(100, 0)
    n3 = circuit.create_node(200, 0)
    n4 = circuit.create_node(300, 0)
    matrix_a = np.zeros((4, 4), dtype=np.complex128)
    vector_z = np.zeros(4, dtype=np.complex128)
    node_groups = {n1.id: 1, n2.id: 2, n3.id: 3, n4.id: 4}
    group_to_idx = {2: 0, 3: 1, 4: 2}
    ground_group_id = 1
    voltage_source_indices = {10: 3}
    state_vector = np.array([2.0, 1.0, 0.5, -0.1], dtype=np.complex128)
    ctx = StampingContext(
        circuit=circuit,
        matrix_A=matrix_a,
        vector_Z=vector_z,
        node_groups=node_groups,
        group_to_idx=group_to_idx,
        ground_group_id=ground_group_id,
        voltage_source_indices=voltage_source_indices,
        state_vector=state_vector,
        omega=1000.0,
        dt=0.001,
        time=0.01,
        capacitor_prev_voltage={50: 1.0},
        inductor_prev_current={51: 0.05},
    )

    r = Resistor(50, n2, n3, resistance=10.0)
    stamping.stamp_resistor_dc(r, ctx)
    assert abs(ctx.matrix_A[0, 0] - 0.1) < 1e-12
    assert abs(ctx.matrix_A[0, 1] - (-0.1)) < 1e-12
    assert abs(ctx.matrix_A[1, 0] - (-0.1)) < 1e-12
    assert abs(ctx.matrix_A[1, 1] - 0.1) < 1e-12

    c = Capacitor(50, n2, n3, capacitance=1e-6)
    ctx.matrix_A.fill(0)
    stamping.stamp_capacitor_transient(c, ctx)
    geq = 1e-6 / 0.001
    assert abs(ctx.matrix_A[0, 0] - geq) < 1e-12
    assert abs(ctx.vector_Z[0] - (geq * 1.0)) < 1e-12

    l = Inductor(51, n2, n3, inductance=1e-3)
    ctx.matrix_A.fill(0)
    ctx.vector_Z.fill(0)
    stamping.stamp_inductor_transient(l, ctx)
    geq_l = 0.001 / 1e-3
    assert abs(ctx.matrix_A[0, 0] - geq_l) < 1e-12
    assert abs(ctx.vector_Z[0] - (-0.05)) < 1e-12

    vm = Voltmeter(52, n2, n3)
    stamping.stamp_resistor_dc(vm, ctx)
    stamping.stamp_resistor_ac(vm, ctx)
    stamping.stamp_resistor_transient(vm, ctx)

    am = Ammeter(53, n2, n3)
    stamping.stamp_resistor_dc(am, ctx)
    stamping.stamp_resistor_ac(am, ctx)
    stamping.stamp_resistor_transient(am, ctx)


# ==============================================================================
# 2. Tests Solver Utils & MatrixStamper
# ==============================================================================

def test_solver_utils_union_find_and_indexing() -> None:
    circuit = Circuit()
    n1 = circuit.create_node(0, 0, is_ground=True)
    n2 = circuit.create_node(10, 0)
    n3 = circuit.create_node(20, 0)
    n4 = circuit.create_node(30, 0)

    # Fil entre n2 et n3
    circuit.create_wire(n2, n3)

    groups = utils.group_connected_nodes(circuit)
    assert groups[n2.id] == groups[n3.id]
    assert groups[n1.id] != groups[n2.id]

    idx_map = utils.build_group_index(groups, groups[n1.id])
    assert groups[n1.id] not in idx_map
    assert groups[n2.id] in idx_map
    assert groups[n4.id] in idx_map

    idx_n2 = utils.matrix_index_for_node(n2, groups, idx_map, groups[n1.id])
    idx_n3 = utils.matrix_index_for_node(n3, groups, idx_map, groups[n1.id])
    assert idx_n2 == idx_n3
    assert utils.matrix_index_for_node(n1, groups, idx_map, groups[n1.id]) is None


def test_matrix_stamper_computations() -> None:
    circuit = Circuit()
    n1 = circuit.create_node(0, 0, is_ground=True)
    n2 = circuit.create_node(100, 0)
    r = Resistor(1, n1, n2, resistance=10.0)
    circuit.add_dipole(r)

    v_sources = utils.MatrixStamper.collect_voltage_sources(circuit)
    assert len(v_sources) == 0

    v_dc = VoltageSourceDC(2, n1, n2, dc_voltage=10.0)
    circuit.add_dipole(v_dc)
    v_sources = utils.MatrixStamper.collect_voltage_sources(circuit)
    assert len(v_sources) == 1

    i_r = utils.MatrixStamper.compute_resistor_current(5.0, 10.0)
    assert i_r == 0.5

    i_c = utils.MatrixStamper.compute_capacitor_current_ac(1000.0, 1e-6, 10.0)
    assert abs(i_c - 0.01j) < 1e-12

    i_l = utils.MatrixStamper.compute_inductor_current_ac(1000.0, 1e-3, 1.0)
    assert abs(i_l - (-1j)) < 1e-12

    v_src_i = utils.MatrixStamper.compute_voltage_source_current(2, {2: 0}, np.array([3.0]))
    assert v_src_i == -3.0

    i_src_val = utils.MatrixStamper.compute_current_source_dc_current(CurrentSourceDC(3, n1, n2, dc_current=4.0))
    assert i_src_val == 4.0


def test_matrix_stamper_dependent_source_update() -> None:
    circuit = Circuit()
    n1 = circuit.create_node(0, 0)
    n2 = circuit.create_node(100, 0)
    n1.potential = 5.0
    n2.potential = 0.0
    r_ctrl = Resistor(1, n1, n2, resistance=10.0)
    circuit.add_dipole(r_ctrl)

    vccs = VoltageControlledCurrentSource(2, n1, n2, control_dipole_id=1, transconductance=2.0)
    circuit.add_dipole(vccs)
    i_vccs = utils.MatrixStamper.update_dependent_source_current(vccs, circuit)
    assert abs(i_vccs - 10.0) < 1e-6

    cccs = CurrentControlledCurrentSource(3, n1, n2, control_dipole_id=1, gain=3.0)
    circuit.add_dipole(cccs)
    i_cccs = utils.MatrixStamper.update_dependent_source_current(cccs, circuit)
    assert abs(i_cccs - 1.5) < 1e-6


# ==============================================================================
# 3. Tests Solvers Edge Cases & Subcircuits
# ==============================================================================

def test_dc_solver_empty_or_none_circuit() -> None:
    solver = DCSolver()
    solver.solve(None)
    solver.solve(Circuit())


def test_dc_solver_disconnected_subcircuits() -> None:
    circuit = Circuit()
    # Sous-circuit 1
    n1 = circuit.create_node(0, 0, is_ground=True)
    n2 = circuit.create_node(100, 0)
    v1 = VoltageSourceDC(1, n2, n1, dc_voltage=10.0)
    r1 = Resistor(2, n2, n1, resistance=100.0)
    circuit.add_dipole(v1)
    circuit.add_dipole(r1)

    # Sous-circuit 2
    n3 = circuit.create_node(200, 0, is_ground=True)
    n4 = circuit.create_node(300, 0)
    circuit.create_wire(n1, n3)
    v2 = VoltageSourceDC(3, n4, n3, dc_voltage=5.0)
    r2 = Resistor(4, n4, n3, resistance=50.0)
    circuit.add_dipole(v2)
    circuit.add_dipole(r2)

    solver = DCSolver()
    solver.solve(circuit)

    assert abs(r1.current - 0.1) < 1e-6
    assert abs(r2.current - 0.1) < 1e-6


def test_ac_solver_rlc_resonance() -> None:
    circuit = Circuit()
    n1 = circuit.create_node(0, 0, is_ground=True)
    n2 = circuit.create_node(50, 0)
    n3 = circuit.create_node(100, 0)

    # Source AC 1V
    v_ac = VoltageSourceAC(1, n1, n2, amplitude=1.0)
    circuit.add_dipole(v_ac)

    r = Resistor(2, n2, n3, resistance=10.0)
    circuit.add_dipole(r)
    c = Capacitor(3, n3, n1, capacitance=100e-9)
    circuit.add_dipole(c)

    solver = ACSolver()
    results = solver.solve(circuit, start_freq=1e3, stop_freq=100e3, points=20, sweep="log")
    assert len(results["frequencies"]) == 20
    assert len(results["node_voltage_mag"][n3.id]) == 20


def test_transient_solver_rc_charging() -> None:
    circuit = Circuit()
    n1 = circuit.create_node(0, 0, is_ground=True)
    n2 = circuit.create_node(50, 0)
    n3 = circuit.create_node(100, 0)

    v_src = VoltageSourceDC(1, n2, n1, dc_voltage=5.0)
    circuit.add_dipole(v_src)

    r = Resistor(2, n2, n3, resistance=1000.0)
    circuit.add_dipole(r)
    c = Capacitor(3, n3, n1, capacitance=1e-6)
    circuit.add_dipole(c)

    solver = TransientSolver()
    results = solver.solve(circuit, duration=0.005, time_step=0.0001)

    times = results["time"]
    v_c = results["node_potentials"][n3.id]

    assert len(times) == 51
    assert v_c[-1] > 4.5
    assert v_c[0] < 0.5


def test_registry_validation() -> None:
    assert validate_registry() is True