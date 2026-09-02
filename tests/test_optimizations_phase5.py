"""
Tests unitaires pour valider les optimisations de la Phase 5 :
- Tâche 5.1 : Cache d'icônes dans ComponentsPanel (réduction du temps de rendu)
- Tâche 5.2 : Calcul vectorisé et rapide des courants de fils (_compute_wire_current_map)
- Tâche 5.3 : Performances et stabilité des solveurs
"""

from __future__ import annotations

import time
from PyQt5.QtWidgets import QApplication
import pytest

from model.circuit import Circuit
from model.components import Resistor, VoltageSourceDC
from solver.dc_solver import DCSolver
from solver.transient_solver import TransientSolver
from view.canvas.canvas_scene import CircuitScene
from view.components_panel import ComponentsPanel


def _ensure_qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_icon_cache_performance() -> None:
    _ensure_qapp()
    panel = ComponentsPanel()

    # Nettoyage explicite du cache pour mesurer
    panel._icon_cache.clear()

    # Premier passage (froid)
    t0 = time.perf_counter()
    for component_id in ["resistor", "capacitor", "inductor", "source", "diode", "opamp"]:
        panel._build_component_icon({"id": component_id})
    t_cold = time.perf_counter() - t0

    # Deuxième passage (chaud - depuis le cache)
    t1 = time.perf_counter()
    for component_id in ["resistor", "capacitor", "inductor", "source", "diode", "opamp"]:
        panel._build_component_icon({"id": component_id})
    t_hot = time.perf_counter() - t1

    # Le cache doit être significativement plus rapide
    assert t_hot < t_cold
    assert len(panel._icon_cache) >= 6


def test_compute_wire_current_map_single_wire() -> None:
    circuit = Circuit()
    n1 = circuit.create_node(0, 0, is_ground=True)
    n2 = circuit.create_node(100, 0)
    n3 = circuit.create_node(200, 0)

    # Source 10V entre n1 et n2
    src = VoltageSourceDC(1, n1, n2, dc_voltage=10.0)
    circuit.add_dipole(src)

    # Résistance 100 ohms entre n3 et n1
    res = Resistor(2, n3, n1, resistance=100.0)
    circuit.add_dipole(res)

    # Fil entre n2 et n3 (courant = 0.1 A)
    wire = circuit.create_wire(n2, n3)

    DCSolver().solve(circuit)

    scene = CircuitScene(model=circuit)
    current_map = scene._compute_wire_current_map()

    assert wire.id in current_map
    assert abs(abs(current_map[wire.id]) - 0.1) < 1e-6


def test_compute_wire_current_map_mesh_network() -> None:
    circuit = Circuit()
    n1 = circuit.create_node(0, 0, is_ground=True)
    n2 = circuit.create_node(100, 0)
    n3 = circuit.create_node(100, 100)
    n4 = circuit.create_node(0, 100)

    src = VoltageSourceDC(1, n1, n2, dc_voltage=12.0)
    circuit.add_dipole(src)

    res1 = Resistor(2, n2, n3, resistance=100.0)
    circuit.add_dipole(res1)

    w1 = circuit.create_wire(n3, n4)
    w2 = circuit.create_wire(n4, n1)

    DCSolver().solve(circuit)

    scene = CircuitScene(model=circuit)
    current_map = scene._compute_wire_current_map()

    assert abs(abs(current_map[w1.id]) - 0.12) < 1e-6
    assert abs(abs(current_map[w2.id]) - 0.12) < 1e-6