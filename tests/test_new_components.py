"""
Tests unitaires complets pour tous les nouveaux composants :
- Modèles, propriétés, états, sérialisation
- Estampage MNA en DC, AC et Transitoire
- Rendu graphique et gestionnaire d'édition
"""

import pytest
import numpy as np
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPainter, QPixmap
from PyQt5.QtWidgets import QStyleOptionGraphicsItem

from model.circuit import Circuit
from model.components import (
    OpAmp,
    Transformer,
    Transistor,
    ZenerDiode,
    Potentiometer,
    MOSFET,
    MOSFET_NMOS,
    MOSFET_PMOS,
    Comparator,
    PulseVoltageSource,
    LogicGate,
    LogicGateAND,
    LogicGateOR,
    LogicGateNOT,
    LogicGateNAND,
    LogicGateNOR,
    LogicGateXOR,
    Fuse,
    Resistor,
    VoltageSourceDC,
    Ground,
)
from solver.dc_solver import DCSolver
from solver.transient_solver import TransientSolver
from solver.ac_solver import ACSolver
from view.component_item import create_component_item
from view.canvas.canvas_editing import EditingManager
from view.components_panel import ComponentsPanel


# Initialisation d'une application Qt pour les tests graphiques
@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ==========================================
# 1. Tests des Modèles
# ==========================================

def test_opamp_model():
    circuit = Circuit()
    n_in_p = circuit.create_node(-30, -12)
    n_in_m = circuit.create_node(-30, 12)
    n_out = circuit.create_node(30, 0)
    opamp = OpAmp(1, n_in_p, n_in_m, n_out, gain=2e5, v_sat_pos=12.0, v_sat_neg=-12.0)
    
    assert opamp.node_in_plus == n_in_p
    assert opamp.node_in_minus == n_in_m
    assert opamp.node_out == n_out
    assert opamp.gain == 2e5
    assert len(opamp.get_terminal_offsets()) == 3

    params = opamp.get_params()
    assert params["gain"] == 2e5
    opamp.set_params({"gain": 1e4, "v_sat_pos": 10.0})
    assert opamp.gain == 1e4
    assert opamp.v_sat_pos == 10.0


def test_transformer_model():
    circuit = Circuit()
    p_p = circuit.create_node(-30, -15)
    p_m = circuit.create_node(-30, 15)
    s_p = circuit.create_node(30, -15)
    s_m = circuit.create_node(30, 15)
    t = Transformer(1, p_p, p_m, s_p, s_m, ratio=0.5, l1=0.01, l2=0.04)
    
    assert t.node_p_pos == p_p
    assert t.node_p_neg == p_m
    assert t.node_s_pos == s_p
    assert t.node_s_neg == s_m
    assert t.ratio == 0.5
    assert len(t.get_terminal_offsets()) == 4


def test_transistor_model_npn_pnp():
    circuit = Circuit()
    c = circuit.create_node(15, -25)
    b = circuit.create_node(-30, 0)
    e = circuit.create_node(15, 25)
    
    q = Transistor(1, c, b, e, transistor_type="NPN", beta=150.0)
    assert q.node_collector == c
    assert q.node_base == b
    assert q.node_emitter == e
    assert q.get_state() == "NPN"
    assert q.beta == 150.0
    
    q.set_state("PNP")
    assert q.get_state() == "PNP"
    assert q.transistor_type == "PNP"


def test_zener_diode_model():
    circuit = Circuit()
    a = circuit.create_node(-30, 0)
    k = circuit.create_node(30, 0)
    z = ZenerDiode(1, a, k, zener_voltage=6.2, zener_resistance=5.0)
    
    assert z.zener_voltage == 6.2
    assert z.zener_resistance == 5.0
    params = z.get_params()
    assert params["zener_voltage"] == 6.2
    z.set_params({"zener_voltage": 3.3})
    assert z.zener_voltage == 3.3


def test_potentiometer_model():
    circuit = Circuit()
    a = circuit.create_node(-30, 0)
    w = circuit.create_node(0, -20)
    b = circuit.create_node(30, 0)
    pot = Potentiometer(1, a, w, b, resistance=10000.0, slider_ratio=0.3)
    
    assert pot.r1 == pytest.approx(3000.0)
    assert pot.r2 == pytest.approx(7000.0)
    pot.set_params({"slider_ratio": 0.8})
    assert pot.r1 == pytest.approx(8000.0)
    assert pot.r2 == pytest.approx(2000.0)


def test_mosfet_model():
    circuit = Circuit()
    d = circuit.create_node(15, -25)
    g = circuit.create_node(-30, 0)
    s = circuit.create_node(15, 25)
    
    m = MOSFET_NMOS(1, d, g, s, v_threshold=1.8)
    assert m.node_drain == d
    assert m.node_gate == g
    assert m.node_source == s
    assert m.mosfet_type == "NMOS"
    assert m.v_threshold == 1.8

    m_p = MOSFET_PMOS(2, d, g, s)
    assert m_p.mosfet_type == "PMOS"


def test_comparator_model():
    circuit = Circuit()
    p = circuit.create_node(-30, -12)
    m = circuit.create_node(-30, 12)
    out = circuit.create_node(30, 0)
    comp = Comparator(1, p, m, out, v_sat_pos=5.0, v_sat_neg=0.0, hysteresis=0.1)
    
    assert comp.v_sat_pos == 5.0
    assert comp.v_sat_neg == 0.0
    assert comp.hysteresis == 0.1


def test_pulse_source_model():
    circuit = Circuit()
    a = circuit.create_node(-30, 0)
    b = circuit.create_node(30, 0)
    pulse = PulseVoltageSource(
        1, a, b,
        v_initial=0.0,
        v_pulsed=5.0,
        delay=0.0,
        rise_time=1e-6,
        fall_time=1e-6,
        pulse_width=1e-3,
        period=2e-3,
    )
    
    # Test waveform computation
    assert pulse.get_value_at_time(0.0) == 0.0
    assert pulse.get_value_at_time(0.5e-3) == 5.0
    assert pulse.get_value_at_time(1.5e-3) == 0.0
    assert pulse.get_value_at_time(2.5e-3) == 5.0


def test_logic_gate_truth_tables():
    circuit = Circuit()
    in1 = circuit.create_node(-30, -10)
    in2 = circuit.create_node(-30, 10)
    out = circuit.create_node(30, 0)

    # AND Gate
    and_gate = LogicGateAND(1, in1, in2, out, v_high=5.0, v_threshold=2.5)
    assert and_gate.evaluate_output_voltage(0.0, 0.0) == 0.0
    assert and_gate.evaluate_output_voltage(5.0, 0.0) == 0.0
    assert and_gate.evaluate_output_voltage(5.0, 5.0) == 5.0

    # OR Gate
    or_gate = LogicGateOR(2, in1, in2, out, v_high=5.0)
    assert or_gate.evaluate_output_voltage(0.0, 0.0) == 0.0
    assert or_gate.evaluate_output_voltage(5.0, 0.0) == 5.0
    assert or_gate.evaluate_output_voltage(5.0, 5.0) == 5.0

    # NOT Gate
    not_gate = LogicGateNOT(3, in1, out, v_high=5.0)
    assert not_gate.evaluate_output_voltage(0.0) == 5.0
    assert not_gate.evaluate_output_voltage(5.0) == 0.0

    # XOR Gate
    xor_gate = LogicGateXOR(4, in1, in2, out, v_high=5.0)
    assert xor_gate.evaluate_output_voltage(0.0, 0.0) == 0.0
    assert xor_gate.evaluate_output_voltage(5.0, 0.0) == 5.0
    assert xor_gate.evaluate_output_voltage(5.0, 5.0) == 0.0


def test_fuse_model():
    circuit = Circuit()
    a = circuit.create_node(-30, 0)
    b = circuit.create_node(30, 0)
    fuse = Fuse(1, a, b, i_nominal=2.0, i2t_rating=10.0)
    
    assert not fuse.blown
    # Accumulate current: i = 1A for 1s => I2t = 1 < 10
    blown = fuse.update_thermal_energy(1.0, 1.0)
    assert not blown
    assert not fuse.blown

    # Large current: i = 10A for 0.2s => I2t = 100 * 0.2 = 20 > 10
    blown = fuse.update_thermal_energy(10.0, 0.2)
    assert blown
    assert fuse.blown


# ==========================================
# 2. Tests de Simulation DC / AC / Transitoire
# ==========================================

def test_potentiometer_dc_simulation():
    """Diviseur potentiométrique : V_in = 10V, R_pot = 10k, curseur = 50% => V_w = 5V."""
    circuit = Circuit()
    n_in = circuit.create_node(0, 0)
    n_w = circuit.create_node(50, 0)
    n_gnd = circuit.create_node(100, 0, is_ground=True)

    v_src = VoltageSourceDC(1, n_in, n_gnd, dc_voltage=10.0)
    gnd = Ground(2, n_gnd)
    pot = Potentiometer(3, n_in, n_w, n_gnd, resistance=10000.0, slider_ratio=0.5)

    circuit.add_dipole(v_src)
    circuit.add_dipole(gnd)
    circuit.add_dipole(pot)

    solver = DCSolver()
    solver.solve(circuit)
    assert n_in.potential == pytest.approx(10.0, rel=1e-3)
    assert n_gnd.potential == pytest.approx(0.0, abs=1e-6)
    assert n_w.potential == pytest.approx(5.0, rel=1e-3)


def test_zener_diode_reverse_breakdown_dc_simulation():
    """Régulateur Zener : Vin = 12V, R = 1k, Zener Vz = 5.1V => V_out ≈ 5.1V."""
    circuit = Circuit()
    n_in = circuit.create_node(0, 0)
    n_out = circuit.create_node(50, 0)
    n_gnd = circuit.create_node(100, 0, is_ground=True)

    v_src = VoltageSourceDC(1, n_in, n_gnd, dc_voltage=12.0)
    gnd = Ground(2, n_gnd)
    r_limit = Resistor(3, n_in, n_out, resistance=1000.0)
    # Cathode sur n_out, Anode sur n_gnd pour être en polarisation inverse
    zener = ZenerDiode(4, n_gnd, n_out, zener_voltage=5.1, zener_resistance=10.0)

    circuit.add_dipole(v_src)
    circuit.add_dipole(gnd)
    circuit.add_dipole(r_limit)
    circuit.add_dipole(zener)

    solver = DCSolver()
    solver.solve(circuit)
    assert n_out.potential == pytest.approx(5.15, rel=0.05)


def test_opamp_buffer_dc_simulation():
    """AOP suiveur de tension (buffer) : V_in = 3.3V, V_out relié à V- => V_out ≈ 3.3V."""
    circuit = Circuit()
    n_in = circuit.create_node(0, 0)
    n_out = circuit.create_node(50, 0)
    n_gnd = circuit.create_node(100, 0, is_ground=True)

    v_src = VoltageSourceDC(1, n_in, n_gnd, dc_voltage=3.3)
    gnd = Ground(2, n_gnd)
    # In+ = n_in, In- = n_out (bouclage), Out = n_out
    opamp = OpAmp(3, n_in, n_out, n_out, gain=1e5)

    circuit.add_dipole(v_src)
    circuit.add_dipole(gnd)
    circuit.add_dipole(opamp)

    solver = DCSolver()
    solver.solve(circuit)
    assert n_out.potential == pytest.approx(3.3, rel=1e-3)


def test_fuse_transient_tripping():
    """Fusible traversé par un fort courant qui fond au cours du temps."""
    circuit = Circuit()
    n_in = circuit.create_node(0, 0)
    n_out = circuit.create_node(50, 0)
    n_gnd = circuit.create_node(100, 0, is_ground=True)

    v_src = VoltageSourceDC(1, n_in, n_gnd, dc_voltage=100.0)
    gnd = Ground(2, n_gnd)
    fuse = Fuse(3, n_in, n_out, i_nominal=2.0, i2t_rating=0.5)
    r_load = Resistor(4, n_out, n_gnd, resistance=10.0)

    circuit.add_dipole(v_src)
    circuit.add_dipole(gnd)
    circuit.add_dipole(fuse)
    circuit.add_dipole(r_load)

    solver = TransientSolver()
    res = solver.solve(circuit, duration=0.05, time_step=0.005)
    assert res is not None
    assert fuse.blown


# ==========================================
# 3. Tests des Items Graphiques & Palette
# ==========================================

def test_component_graphic_items(qapp):
    """Vérifie la création et le rendu vectoriel de tous les items sans exception."""
    circuit = Circuit()
    n1 = circuit.create_node(-30, 0)
    n2 = circuit.create_node(30, 0)
    n3 = circuit.create_node(0, -20)
    n4 = circuit.create_node(0, 20)

    components = [
        OpAmp(1, n1, n2, n3),
        Transformer(2, n1, n2, n3, n4),
        Transistor(3, n1, n2, n3),
        MOSFET(4, n1, n2, n3),
        ZenerDiode(5, n1, n2),
        Potentiometer(6, n1, n3, n2),
        Comparator(7, n1, n2, n3),
        PulseVoltageSource(8, n1, n2),
        LogicGateAND(9, n1, n2, n3),
        LogicGateNOT(10, n1, n2),
        Fuse(11, n1, n2),
    ]

    pixmap = QPixmap(100, 100)
    painter = QPainter(pixmap)
    option = QStyleOptionGraphicsItem()

    for comp in components:
        item = create_component_item(comp)
        assert item is not None
        assert item.get_value_text() != ""
        item.paint(painter, option)

    painter.end()


def test_editing_manager_all_tools():
    """Vérifie que l'EditingManager instancie tous les outils supportés."""
    circuit = Circuit()
    mgr = EditingManager(circuit)

    tools = [
        "resistor", "potentiometer", "capacitor", "inductor", "transformer",
        "source", "pulse_source", "current_source", "diode", "zener_diode",
        "transistor", "mosfet", "opamp", "comparator", "fuse",
        "logic_and", "logic_or", "logic_not", "logic_nand", "logic_nor", "logic_xor",
        "switch", "voltmeter", "ammeter", "ground"
    ]

    for tool in tools:
        comp = mgr.create_component_by_tool(tool, 100.0, 100.0)
        assert comp is not None, f"Échec de création pour l'outil {tool}"
