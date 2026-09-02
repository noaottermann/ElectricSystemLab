import numpy as np
import pytest
from PyQt5.QtWidgets import QApplication

from model.circuit import Circuit
from model.components import Capacitor, Resistor, VoltageSourceDC
from view.graphs_panel import GraphPanel


def test_interactive_graph_panel():
    """Vérifie l'affichage et l'interaction du panneau GraphPanel."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    circuit = Circuit()
    n0 = circuit.create_node(0, 0, is_ground=True)
    n1 = circuit.create_node(100, 0)
    n2 = circuit.create_node(200, 0)

    vsrc = VoltageSourceDC(1, n1, n0, dc_voltage=10.0)
    circuit.add_dipole(vsrc)
    r1 = Resistor(2, n1, n2, resistance=1000.0)
    circuit.add_dipole(r1)
    c1 = Capacitor(3, n2, n0, capacitance=1e-6)
    circuit.add_dipole(c1)

    n1.potential = 10.0
    n2.potential = 5.0
    vsrc.current = 0.005
    r1.current = 0.005
    c1.current = 0.0

    panel = GraphPanel()
    panel.set_dc_results(circuit)

    time_points = np.linspace(0, 1, 50)
    transient_result = {
        "time": time_points,
        "node_potentials": {
            n1.id: 10.0 * (1 - np.exp(-time_points * 2)),
            n2.id: 5.0 * (1 - np.exp(-time_points * 2)),
        },
        "dipole_currents": {
            vsrc.id: 0.005 * np.exp(-time_points * 2),
            r1.id: 0.005 * np.exp(-time_points * 2),
            c1.id: 0.01 * np.exp(-time_points * 2),
        },
        "dipole_voltages": {
            vsrc.id: [10.0] * 50,
            r1.id: [5.0] * 50,
            c1.id: [5.0] * 50,
        },
    }

    panel.set_transient_results(transient_result, circuit)
    assert panel.last_transient_result is not None
