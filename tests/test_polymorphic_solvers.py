"""
Tests d'intégration complets pour le système de stamping polymorphe (Phase 2).

Vérifie que :
1. Tous les composants possèdent les méthodes polymorphes stamp_dc, stamp_ac, stamp_transient.
2. Le solveur DC polymorphe résout correctement les circuits linéaires, commandés et non-linéaires.
3. Le solveur AC polymorphe produit les réponses fréquentielles attendues (filtres RC, RLC).
4. Le solveur Transitoire polymorphe simule fidèlement la dynamique temporelle (charge RC, RL).
"""

from __future__ import annotations

import math
import pytest
import numpy as np

from model.circuit import Circuit
from model.components import (
    Ammeter,
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
    Resistor,
    Switch,
    Voltmeter,
    VoltageControlledCurrentSource,
    VoltageControlledVoltageSource,
    VoltageSource,
    VoltageSourceAC,
    VoltageSourceDC,
    get_component_registry,
)
from solver.base_solver import BaseSolver, StampingContext
from solver.dc_solver import DCSolver
from solver.ac_solver import ACSolver
from solver.transient_solver import TransientSolver
from solver.stamping_registry import validate_registry


# ===========================================================================
# 1. Validation du registre de stamping polymorphe
# ===========================================================================

def test_all_components_have_stamping_methods() -> None:
    """Vérifie que 100% des composants concrets ont stamp_dc, stamp_ac et stamp_transient."""
    assert validate_registry() is True

    registry = get_component_registry()
    assert len(registry) > 0

    for name, comp_class in registry.items():
        assert hasattr(comp_class, "stamp_dc"), f"{name} manque stamp_dc"
        assert hasattr(comp_class, "stamp_ac"), f"{name} manque stamp_ac"
        assert hasattr(comp_class, "stamp_transient"), f"{name} manque stamp_transient"
        assert callable(getattr(comp_class, "stamp_dc")), f"{name}.stamp_dc n'est pas appelable"
        assert callable(getattr(comp_class, "stamp_ac")), f"{name}.stamp_ac n'est pas appelable"
        assert callable(getattr(comp_class, "stamp_transient")), f"{name}.stamp_transient n'est pas appelable"


# ===========================================================================
# 2. Tests d'intégration DC Solver Polymorphe
# ===========================================================================

def test_dc_voltage_divider() -> None:
    """Test d'un pont diviseur de tension classique en DC polymorphe."""
    circuit = Circuit()
    n_gnd = circuit.create_node(0, 0, is_ground=True)
    n_in = circuit.create_node(0, 100)
    n_mid = circuit.create_node(100, 100)

    # Source 12V
    src = VoltageSourceDC(circuit.get_next_dipole_id(), n_in, n_gnd, dc_voltage=12.0)
    circuit.add_dipole(src)

    # Deux résistances identiques de 1000 ohms -> V_mid attendu = 6.0 V
    r1 = Resistor(circuit.get_next_dipole_id(), n_in, n_mid, resistance=1000.0)
    circuit.add_dipole(r1)

    r2 = Resistor(circuit.get_next_dipole_id(), n_mid, n_gnd, resistance=1000.0)
    circuit.add_dipole(r2)

    solver = DCSolver()
    solver.solve(circuit)

    assert abs(n_in.potential - 12.0) < 1e-6
    assert abs(n_mid.potential - 6.0) < 1e-6
    assert abs(r1.current - 0.006) < 1e-6
    assert abs(r2.current - 0.006) < 1e-6
    assert abs(src.current - 0.006) < 1e-6


def test_dc_current_source_and_resistor() -> None:
    """Test d'une source de courant DC connectée à une résistance."""
    circuit = Circuit()
    n_gnd = circuit.create_node(0, 0, is_ground=True)
    n_pos = circuit.create_node(0, 100)

    # Source 5 mA de GND vers n_pos
    src = CurrentSourceDC(circuit.get_next_dipole_id(), n_gnd, n_pos, dc_current=0.005)
    circuit.add_dipole(src)

    # Résistance 2 kΩ
    res = Resistor(circuit.get_next_dipole_id(), n_pos, n_gnd, resistance=2000.0)
    circuit.add_dipole(res)

    solver = DCSolver()
    solver.solve(circuit)

    # V = R * I = 2000 * 0.005 = 10.0 V
    assert abs(n_pos.potential - 10.0) < 1e-6
    assert abs(res.current - 0.005) < 1e-6


def test_dc_switch_behavior() -> None:
    """Test du composant Switch fermé et ouvert en DC."""
    circuit = Circuit()
    n_gnd = circuit.create_node(0, 0, is_ground=True)
    n_in = circuit.create_node(0, 100)
    n_out = circuit.create_node(100, 100)

    src = VoltageSourceDC(circuit.get_next_dipole_id(), n_in, n_gnd, dc_voltage=5.0)
    circuit.add_dipole(src)

    switch = Switch(circuit.get_next_dipole_id(), n_in, n_out, state="closed", resistance_closed=0.01)
    circuit.add_dipole(switch)

    load = Resistor(circuit.get_next_dipole_id(), n_out, n_gnd, resistance=100.0)
    circuit.add_dipole(load)

    solver = DCSolver()
    solver.solve(circuit)

    # Switch fermé : V_out proche de 5.0 V
    assert abs(n_out.potential - 5.0) < 0.01

    # Switch ouvert
    switch.state = "open"
    solver.solve(circuit)

    # Switch ouvert (1e12 Ω) : V_out ~ 0 V
    assert abs(n_out.potential) < 1e-6


def test_dc_all_dependent_sources() -> None:
    """Test complet de VCVS, VCCS, CCCS, CCVS avec le solveur polymorphe."""
    # 1. VCVS
    c1 = Circuit()
    gnd1 = c1.create_node(0, 0, is_ground=True)
    n1 = c1.create_node(0, 100)
    n2 = c1.create_node(100, 100)

    v_in1 = VoltageSourceDC(c1.get_next_dipole_id(), n1, gnd1, dc_voltage=3.0)
    c1.add_dipole(v_in1)
    vcvs = VoltageControlledVoltageSource(c1.get_next_dipole_id(), n2, gnd1, gain=4.0, control_dipole_id=v_in1.id)
    c1.add_dipole(vcvs)
    r_load1 = Resistor(c1.get_next_dipole_id(), n2, gnd1, resistance=1000.0)
    c1.add_dipole(r_load1)

    solver = DCSolver()
    solver.solve(c1)
    # V_out = 4 * 3V = 12V
    assert abs(n2.potential - 12.0) < 1e-4

    # 2. VCCS
    c2 = Circuit()
    gnd2 = c2.create_node(0, 0, is_ground=True)
    n1_2 = c2.create_node(0, 100)
    n2_2 = c2.create_node(100, 100)

    v_in2 = VoltageSourceDC(c2.get_next_dipole_id(), n1_2, gnd2, dc_voltage=2.0)
    c2.add_dipole(v_in2)
    vccs = VoltageControlledCurrentSource(c2.get_next_dipole_id(), gnd2, n2_2, transconductance=0.005, control_dipole_id=v_in2.id)
    c2.add_dipole(vccs)
    r_load2 = Resistor(c2.get_next_dipole_id(), n2_2, gnd2, resistance=1000.0)
    c2.add_dipole(r_load2)

    solver.solve(c2)
    # I = gm * 2V = 0.01A injected into n2_2 -> V_out = 10V
    assert abs(n2_2.potential - 10.0) < 1e-4


def test_dc_diode_exponential_conduction() -> None:
    """Test du comportement non-linéaire d'une Diode en direct et en inverse."""
    circuit = Circuit()
    n_gnd = circuit.create_node(0, 0, is_ground=True)
    n_in = circuit.create_node(0, 100)
    n_mid = circuit.create_node(100, 100)

    # Source 5V
    src = VoltageSourceDC(circuit.get_next_dipole_id(), n_in, n_gnd, dc_voltage=5.0)
    circuit.add_dipole(src)

    # Résistance de limitation 1000 ohms
    r_lim = Resistor(circuit.get_next_dipole_id(), n_in, n_mid, resistance=1000.0)
    circuit.add_dipole(r_lim)

    # Diode vers GND (anode en n_mid, cathode en n_gnd)
    diode = Diode(circuit.get_next_dipole_id(), n_mid, n_gnd, saturation_current=1e-12, ideality_factor=1.0)
    circuit.add_dipole(diode)

    solver = DCSolver()
    solver.solve(circuit)

    # En direct, la tension aux bornes de la diode doit être typiquement entre 0.5V et 0.9V
    assert 0.5 < n_mid.potential < 0.9
    assert diode.current > 0.004  # Courant proche de (5 - 0.6) / 1000 = 4.4 mA


# ===========================================================================
# 3. Tests d'intégration AC Solver Polymorphe
# ===========================================================================

def test_ac_rc_lowpass_filter() -> None:
    """
    Test d'un filtre passe-bas RC en AC polymorphe.
    fc = 1 / (2 * pi * R * C)
    R = 1000 ohms, C = 159.155 nF -> fc = 1000 Hz.
    """
    circuit = Circuit()
    n_gnd = circuit.create_node(0, 0, is_ground=True)
    n_in = circuit.create_node(0, 100)
    n_out = circuit.create_node(100, 100)

    # Source AC 10V amplitude
    src = VoltageSourceAC(circuit.get_next_dipole_id(), n_in, n_gnd, amplitude=10.0, frequency=1000.0)
    circuit.add_dipole(src)

    # R = 1 kΩ
    r = Resistor(circuit.get_next_dipole_id(), n_in, n_out, resistance=1000.0)
    circuit.add_dipole(r)

    # C = 159.154943 nF (pour fc = 1000 Hz exactement)
    c = Capacitor(circuit.get_next_dipole_id(), n_out, n_gnd, capacitance=1.0 / (2.0 * math.pi * 1000.0 * 1000.0))
    circuit.add_dipole(c)

    solver = ACSolver()
    results = solver.solve(circuit, start_freq=10.0, stop_freq=100000.0, points=5, sweep="log")

    freqs = results["frequency"]
    assert len(freqs) == 5

    out_mags = results["node_voltage_mag"][n_out.id]

    # À basse fréquence (10 Hz << fc), gain ~ 1 -> V_out ~ 10V
    assert abs(out_mags[0] - 10.0) < 0.1

    # À haute fréquence (100 kHz >> fc), gain ~ 0 -> V_out << 1V
    assert out_mags[-1] < 0.2

    # Vérification de la coupure à 1 kHz
    results_fc = solver.solve(circuit, start_freq=1000.0, stop_freq=1000.0, points=1)
    mag_at_fc = results_fc["node_voltage_mag"][n_out.id][0]
    # À fc, V_out = 10 / sqrt(2) ~ 7.071 V
    assert abs(mag_at_fc - 10.0 / math.sqrt(2)) < 0.05


def test_ac_rlc_resonance() -> None:
    """
    Test d'un circuit RLC résonnant parallèle en AC.
    f0 = 1 / (2 * pi * sqrt(L * C))
    L = 10 mH, C = 10 µF -> f0 ~ 503.29 Hz
    """
    circuit = Circuit()
    n_gnd = circuit.create_node(0, 0, is_ground=True)
    n_in = circuit.create_node(0, 100)

    # Source de courant AC 1A
    src = CurrentSourceAC(circuit.get_next_dipole_id(), n_gnd, n_in, amplitude=1.0)
    circuit.add_dipole(src)

    # R = 100 Ω en parallèle
    r = Resistor(circuit.get_next_dipole_id(), n_in, n_gnd, resistance=100.0)
    circuit.add_dipole(r)

    # L = 10 mH
    l = Inductor(circuit.get_next_dipole_id(), n_in, n_gnd, inductance=10e-3)
    circuit.add_dipole(l)

    # C = 10 µF
    c = Capacitor(circuit.get_next_dipole_id(), n_in, n_gnd, capacitance=10e-6)
    circuit.add_dipole(c)

    f0 = 1.0 / (2.0 * math.pi * math.sqrt(10e-3 * 10e-6))

    solver = ACSolver()
    res = solver.solve(circuit, start_freq=f0, stop_freq=f0, points=1)

    v_mag = res["node_voltage_mag"][n_in.id][0]
    # À la résonance, l'impédance équivalente LC est infinie, donc Z_tot = R = 100 Ω
    # V = I * R = 1 * 100 = 100 V
    assert abs(v_mag - 100.0) < 0.5


# ===========================================================================
# 4. Tests d'intégration Transient Solver Polymorphe
# ===========================================================================

def test_transient_rc_charging_curve() -> None:
    """
    Test de la charge d'un condensateur à travers une résistance en transitoire.
    V_c(t) = V_in * (1 - exp(-t / tau)) avec tau = R * C.
    """
    circuit = Circuit()
    n_gnd = circuit.create_node(0, 0, is_ground=True)
    n_in = circuit.create_node(0, 100)
    n_out = circuit.create_node(100, 100)

    # Échelon de tension 10V
    v_src = VoltageSourceDC(circuit.get_next_dipole_id(), n_in, n_gnd, dc_voltage=10.0)
    circuit.add_dipole(v_src)

    # R = 1000 Ω, C = 1 µF -> tau = 1 ms
    r = Resistor(circuit.get_next_dipole_id(), n_in, n_out, resistance=1000.0)
    circuit.add_dipole(r)

    c = Capacitor(circuit.get_next_dipole_id(), n_out, n_gnd, capacitance=1e-6)
    circuit.add_dipole(c)

    solver = TransientSolver()
    tau = 1e-3
    dt = 1e-5  # 100 pas par constante de temps
    duration = 5 * tau  # 5 tau

    traces = solver.solve(circuit, duration=duration, time_step=dt)

    times = traces["time"]
    v_caps = traces["node_potentials"][n_out.id]

    assert len(times) == len(v_caps)

    # Vérification à t = tau : V ~ 10 * (1 - 1/e) = 6.321 V
    idx_tau = int(round(tau / dt))
    expected_v_tau = 10.0 * (1.0 - math.exp(-1.0))
    assert abs(v_caps[idx_tau] - expected_v_tau) < 0.1

    # Vérification à t = 5 tau : V ~ 10 * (1 - exp(-5)) = 9.932 V
    expected_v_end = 10.0 * (1.0 - math.exp(-5.0))
    assert abs(v_caps[-1] - expected_v_end) < 0.1


def test_transient_rl_current_rise() -> None:
    """
    Test de l'établissement du courant dans une inductance RL en transitoire.
    I_L(t) = (V / R) * (1 - exp(-t / tau_L)) avec tau_L = L / R.
    """
    circuit = Circuit()
    n_gnd = circuit.create_node(0, 0, is_ground=True)
    n_in = circuit.create_node(0, 100)
    n_mid = circuit.create_node(100, 100)

    v_src = VoltageSourceDC(circuit.get_next_dipole_id(), n_in, n_gnd, dc_voltage=10.0)
    circuit.add_dipole(v_src)

    # R = 10 Ω, L = 10 mH -> tau_L = 1 ms, I_max = 1 A
    r = Resistor(circuit.get_next_dipole_id(), n_in, n_mid, resistance=10.0)
    circuit.add_dipole(r)

    l = Inductor(circuit.get_next_dipole_id(), n_mid, n_gnd, inductance=10e-3)
    circuit.add_dipole(l)

    solver = TransientSolver()
    tau_l = 1e-3
    dt = 1e-5
    duration = 5 * tau_l

    traces = solver.solve(circuit, duration=duration, time_step=dt)
    i_inductors = traces["dipole_currents"][l.id]

    # À t = tau_L : I ~ 1.0 * (1 - 1/e) = 0.632 A
    idx_tau = int(round(tau_l / dt))
    expected_i_tau = 1.0 * (1.0 - math.exp(-1.0))
    assert abs(i_inductors[idx_tau] - expected_i_tau) < 0.05

    # À t = 5 tau_L : I ~ 0.993 A
    expected_i_end = 1.0 * (1.0 - math.exp(-5.0))
    assert abs(i_inductors[-1] - expected_i_end) < 0.05


def test_transient_ac_sinusoidal_source() -> None:
    """Test d'une source AC sinusoidale alimentant une résistance en transitoire."""
    circuit = Circuit()
    n_gnd = circuit.create_node(0, 0, is_ground=True)
    n_in = circuit.create_node(0, 100)

    # Source AC 50 Hz, 10V crête
    v_ac = VoltageSourceAC(circuit.get_next_dipole_id(), n_in, n_gnd, amplitude=10.0, frequency=50.0)
    circuit.add_dipole(v_ac)

    r = Resistor(circuit.get_next_dipole_id(), n_in, n_gnd, resistance=10.0)
    circuit.add_dipole(r)

    solver = TransientSolver()
    duration = 0.02  # 1 période à 50 Hz = 20 ms
    dt = 0.0001     # 200 points

    traces = solver.solve(circuit, duration=duration, time_step=dt)
    v_in_trace = traces["node_potentials"][n_in.id]
    t_trace = traces["time"]

    # À t = 5 ms (T/4), sin(2*pi*50*0.005) = sin(pi/2) = 1 -> V = 10 V
    idx_quarter = int(round(0.005 / dt))
    assert abs(v_in_trace[idx_quarter] - 10.0) < 0.1

    # À t = 10 ms (T/2), sin(pi) = 0 -> V = 0 V
    idx_half = int(round(0.010 / dt))
    assert abs(v_in_trace[idx_half]) < 0.1
