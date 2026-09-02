import math
import pytest

from model.circuit import Circuit
from model.components import (
    Ammeter,
    Capacitor,
    CurrentSourceDC,
    Diode,
    Ground,
    Inductor,
    LogicGate,
    MOSFET_NMOS,
    MOSFET_PMOS,
    OpAmp,
    Resistor,
    Transistor,
    VoltageSourceAC,
    VoltageSourceDC,
    Voltmeter,
    ZenerDiode,
)
from solver.dc_solver import DCSolver
from solver.transient_solver import TransientSolver
from solver.ac_solver import ACSolver


def test_circuit_ohms_law():
    """Loi d'Ohm U = R * I"""
    circuit = Circuit()
    n_gnd = circuit.create_node(0.0, 0.0, is_ground=True)
    n1 = circuit.create_node(100.0, 0.0)

    v_src = VoltageSourceDC(1, n1, n_gnd, dc_voltage=12.0)
    circuit.add_dipole(v_src)
    r1 = Resistor(2, n1, n_gnd, resistance=4.0)
    circuit.add_dipole(r1)

    solver = DCSolver()
    solver.solve(circuit)

    assert pytest.approx(n1.potential, rel=1e-4) == 12.0
    assert pytest.approx(abs(r1.current), rel=1e-3) == 3.0


def test_circuit_voltage_divider():
    """Pont diviseur de tension"""
    circuit = Circuit()
    n_gnd = circuit.create_node(0.0, 0.0, is_ground=True)
    n_in = circuit.create_node(100.0, 0.0)
    n_mid = circuit.create_node(200.0, 0.0)

    circuit.add_dipole(VoltageSourceDC(1, n_in, n_gnd, dc_voltage=10.0))
    circuit.add_dipole(Resistor(2, n_in, n_mid, resistance=3000.0))
    circuit.add_dipole(Resistor(3, n_mid, n_gnd, resistance=2000.0))

    solver = DCSolver()
    solver.solve(circuit)

    assert pytest.approx(n_mid.potential, rel=1e-4) == 4.0


def test_circuit_current_divider():
    """Pont diviseur de courant"""
    circuit = Circuit()
    n_gnd = circuit.create_node(0.0, 0.0, is_ground=True)
    n_top = circuit.create_node(100.0, 0.0)

    circuit.add_dipole(CurrentSourceDC(1, n_gnd, n_top, dc_current=10.0))
    r1 = Resistor(2, n_top, n_gnd, resistance=20.0)
    circuit.add_dipole(r1)
    r2 = Resistor(3, n_top, n_gnd, resistance=80.0)
    circuit.add_dipole(r2)

    solver = DCSolver()
    solver.solve(circuit)

    assert pytest.approx(n_top.potential, rel=1e-4) == 160.0
    assert pytest.approx(abs(r1.current), rel=1e-3) == 8.0
    assert pytest.approx(abs(r2.current), rel=1e-3) == 2.0


def test_circuit_rlc_transient():
    """Circuit RLC série transitoire"""
    circuit = Circuit()
    n_gnd = circuit.create_node(0.0, 0.0, is_ground=True)
    n1 = circuit.create_node(50.0, 0.0)
    n2 = circuit.create_node(100.0, 0.0)
    n3 = circuit.create_node(150.0, 0.0)

    circuit.add_dipole(VoltageSourceDC(1, n1, n_gnd, dc_voltage=10.0))
    circuit.add_dipole(Resistor(2, n1, n2, resistance=10.0))
    circuit.add_dipole(Inductor(3, n2, n3, inductance=1e-3))
    circuit.add_dipole(Capacitor(4, n3, n_gnd, capacitance=1e-5))

    solver = TransientSolver()
    res = solver.solve(circuit, duration=0.005, time_step=5e-5)
    assert "time" in res
    assert len(res["time"]) > 50

    final_v_c = res["node_potentials"][n3.id][-1]
    assert pytest.approx(final_v_c, rel=0.05) == 10.0


def test_circuit_diode_forward_and_reverse():
    """Diode en direct et en inverse"""
    circuit = Circuit()
    n_gnd = circuit.create_node(0.0, 0.0, is_ground=True)
    n_src = circuit.create_node(100.0, 0.0)
    n_d = circuit.create_node(200.0, 0.0)

    circuit.add_dipole(VoltageSourceDC(1, n_src, n_gnd, dc_voltage=5.0))
    d_fwd = Diode(2, n_src, n_d)
    circuit.add_dipole(d_fwd)
    circuit.add_dipole(Resistor(3, n_d, n_gnd, resistance=1000.0))

    solver = DCSolver()
    solver.solve(circuit)

    assert 4.0 < n_d.potential < 4.8
    assert d_fwd.current > 0.001


def test_circuit_zener_regulation():
    """Régulation par diode Zener"""
    circuit = Circuit()
    n_gnd = circuit.create_node(0.0, 0.0, is_ground=True)
    n_in = circuit.create_node(100.0, 0.0)
    n_out = circuit.create_node(200.0, 0.0)

    circuit.add_dipole(VoltageSourceDC(1, n_in, n_gnd, dc_voltage=12.0))
    circuit.add_dipole(Resistor(2, n_in, n_out, resistance=100.0))
    circuit.add_dipole(ZenerDiode(3, n_gnd, n_out, zener_voltage=5.1))

    solver = DCSolver()
    solver.solve(circuit)

    assert 5.0 < n_out.potential < 6.0


def test_circuit_diode_bridge_rectifier():
    """Pont de diodes redresseur Graetz"""
    circuit = Circuit()
    n_gnd = circuit.create_node(0.0, 0.0, is_ground=True)
    n_ac1 = circuit.create_node(100.0, 0.0)
    n_ac2 = circuit.create_node(100.0, 50.0)
    n_plus = circuit.create_node(200.0, 0.0)
    n_minus = n_gnd

    circuit.add_dipole(VoltageSourceAC(1, n_ac1, n_ac2, amplitude=10.0, frequency=50.0))
    circuit.add_dipole(Diode(2, n_ac1, n_plus))
    circuit.add_dipole(Diode(3, n_ac2, n_plus))
    circuit.add_dipole(Diode(4, n_minus, n_ac1))
    circuit.add_dipole(Diode(5, n_minus, n_ac2))
    r_load = Resistor(6, n_plus, n_minus, resistance=500.0)
    circuit.add_dipole(r_load)

    solver = TransientSolver()
    res = solver.solve(circuit, duration=0.04, time_step=0.0005)
    assert "time" in res

    v_load = res["dipole_voltages"][r_load.id]
    assert all(v >= -0.1 for v in v_load)
    assert max(v_load) > 7.0


def test_circuit_bjt_transistor_common_emitter():
    """Transistor BJT NPN émetteur commun"""
    circuit = Circuit()
    n_gnd = circuit.create_node(0.0, 0.0, is_ground=True)
    n_vcc = circuit.create_node(0.0, 100.0)
    n_base_in = circuit.create_node(50.0, 50.0)
    n_base = circuit.create_node(100.0, 50.0)
    n_coll = circuit.create_node(100.0, 100.0)

    circuit.add_dipole(VoltageSourceDC(1, n_vcc, n_gnd, dc_voltage=10.0))
    circuit.add_dipole(VoltageSourceDC(2, n_base_in, n_gnd, dc_voltage=0.8))

    circuit.add_dipole(Resistor(3, n_base_in, n_base, resistance=10000.0))
    rc = Resistor(4, n_vcc, n_coll, resistance=1000.0)
    circuit.add_dipole(rc)

    circuit.add_dipole(Transistor(5, n_coll, n_base, n_gnd, transistor_type="NPN", beta=100.0))

    solver = DCSolver()
    solver.solve(circuit)

    assert n_coll.potential < 10.0


def test_circuit_mosfet_switching():
    """Commutation par MOSFET NMOS"""
    circuit = Circuit()
    n_gnd = circuit.create_node(0.0, 0.0, is_ground=True)
    n_vdd = circuit.create_node(0.0, 100.0)
    n_gate = circuit.create_node(50.0, 50.0)
    n_drain = circuit.create_node(100.0, 100.0)

    circuit.add_dipole(VoltageSourceDC(1, n_vdd, n_gnd, dc_voltage=12.0))
    circuit.add_dipole(VoltageSourceDC(2, n_gate, n_gnd, dc_voltage=5.0))
    circuit.add_dipole(Resistor(3, n_vdd, n_drain, resistance=100.0))

    circuit.add_dipole(MOSFET_NMOS(4, n_drain, n_gate, n_gnd, v_threshold=2.0, transconductance=0.02))

    solver = DCSolver()
    solver.solve(circuit)

    assert n_drain.potential < 6.0


def test_circuit_logic_gates_truth_tables():
    """Tables de vérité de toutes les portes logiques"""
    gates_expected = [
        ("AND", [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 1)]),
        ("OR",  [(0, 0, 0), (1, 0, 1), (0, 1, 1), (1, 1, 1)]),
        ("NAND",[(0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 0)]),
        ("NOR", [(0, 0, 1), (1, 0, 0), (0, 1, 0), (1, 1, 0)]),
        ("XOR", [(0, 0, 0), (1, 0, 1), (0, 1, 1), (1, 1, 0)]),
    ]

    for gate_type, truth_table in gates_expected:
        for in_a, in_b, exp_out in truth_table:
            c = Circuit()
            n_gnd = c.create_node(0.0, 0.0, is_ground=True)
            n_a = c.create_node(50.0, 0.0)
            n_b = c.create_node(50.0, 50.0)
            n_out = c.create_node(100.0, 25.0)

            c.add_dipole(VoltageSourceDC(1, n_a, n_gnd, dc_voltage=5.0 if in_a else 0.0))
            c.add_dipole(VoltageSourceDC(2, n_b, n_gnd, dc_voltage=5.0 if in_b else 0.0))
            c.add_dipole(LogicGate(3, n_a, n_b, n_out, gate_type=gate_type, v_high=5.0))

            solver = DCSolver()
            solver.solve(c)
            expected_v = 5.0 if exp_out else 0.0
            assert pytest.approx(n_out.potential, abs=0.5) == expected_v, f"Failed for {gate_type} with inputs {in_a}, {in_b}"

    for in_a, exp_out in [(0, 1), (1, 0)]:
        c = Circuit()
        n_gnd = c.create_node(0.0, 0.0, is_ground=True)
        n_a = c.create_node(50.0, 0.0)
        n_out = c.create_node(100.0, 0.0)

        c.add_dipole(VoltageSourceDC(1, n_a, n_gnd, dc_voltage=5.0 if in_a else 0.0))
        c.add_dipole(LogicGate(2, n_a, n_out, gate_type="NOT", v_high=5.0))

        solver = DCSolver()
        solver.solve(c)
        expected_v = 5.0 if exp_out else 0.0
        assert pytest.approx(n_out.potential, abs=0.5) == expected_v
