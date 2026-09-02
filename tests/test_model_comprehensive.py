"""
Tests complets pour le modèle de données :
- model.circuit (operations structurelles, fusion, suppression, sous-circuits, validation)
- model.dipole & model.component (classes de base, pins, transformations, rotation, flip)
- model.components (l'intégralité des 20+ composants avec getters/setters, params, serialization)
"""

from __future__ import annotations

import json
import pytest

from model.circuit import Circuit
from model.component import Component
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
)
from model.dipole import Dipole
from model.node import Node
from model.wire import Wire
from persistence import serializer


# ==============================================================================
# 1. Tests Circuit Methods & Topology
# ==============================================================================

def test_circuit_node_creation_and_removal() -> None:
    c = Circuit()
    n1 = c.create_node(10, 20)
    n2 = c.create_node(30, 40)
    assert n1.id in c.nodes
    assert n2.id in c.nodes

    # Trouver par position
    found = c.get_node_at(10, 20, tolerance=2.0)
    assert found is n1
    assert c.get_node_at(100, 100, tolerance=2.0) is None

    # Créer un dipole et un fil
    r = Resistor(1, n1, n2, resistance=100.0)
    c.add_dipole(r)
    w = c.create_wire(n1, n2)
    assert len(c.wires) == 1

    # Supprimer un nœud doit nettoyer les fils et composants attachés
    c.remove_node(n2)
    assert n2.id not in c.nodes
    assert len(c.wires) == 0
    assert len(c.dipoles) == 0


def test_circuit_merge_nodes() -> None:
    c = Circuit()
    n1 = c.create_node(0, 0, is_ground=True)
    n2 = c.create_node(10, 0, is_ground=False)
    n3 = c.create_node(20, 0, is_ground=False)

    r1 = Resistor(1, n2, n3, resistance=100.0)
    c.add_dipole(r1)

    # Fusionner n1 (masse) et n2 -> n1 doit être conservé
    keeper = c.merge_nodes(n1, n2)
    assert keeper is n1
    assert n2.id not in c.nodes
    assert r1.node_a is n1
    assert n1.is_ground is True

    # Fusionner avec None ou même nœud
    assert c.merge_nodes(n1, None) is n1
    assert c.merge_nodes(n1, n1) is n1


def test_circuit_serialization_via_serializer() -> None:
    c = Circuit()
    n1 = c.create_node(0, 0, is_ground=True)
    n2 = c.create_node(50, 0)
    n3 = c.create_node(100, 0)

    c.add_dipole(VoltageSourceDC(1, n1, n2, dc_voltage=12.0))
    c.add_dipole(Resistor(2, n2, n3, resistance=220.0))
    c.add_dipole(Capacitor(3, n3, n1, capacitance=4.7e-6))
    c.create_wire(n1, n2)

    json_str = serializer.serialize_circuit(c)
    assert "nodes" in json_str
    assert "dipoles" in json_str
    assert "wires" in json_str

    # Recharger dans un nouveau circuit
    c2 = Circuit()
    serializer.deserialize_circuit(c2, json_str)

    assert len(c2.nodes) == 3
    assert len(c2.dipoles) == 3
    assert len(c2.wires) == 1
    assert c2.dipoles[1].dc_voltage == 12.0
    assert c2.dipoles[2].resistance == 220.0
    assert c2.dipoles[3].capacitance == 4.7e-6


# ==============================================================================
# 2. Tests Components (Getters, Setters, Parameters, States)
# ==============================================================================

def test_resistor_properties() -> None:
    n1 = Node(1, 0, 0)
    n2 = Node(2, 10, 0)
    n1.potential = 5.0
    n2.potential = 0.0
    r = Resistor(1, n1, n2, resistance=1000.0)

    assert r.resistance == 1000.0
    r.resistance = 4700.0
    assert r.resistance == 4700.0

    params = r.get_params()
    assert params["resistance"] == 4700.0
    r.set_params({"resistance": 220.0})
    assert r.resistance == 220.0

    assert r.voltage == 5.0
    r.current = 0.02
    assert r.power == 0.1


def test_capacitor_properties() -> None:
    n1 = Node(1, 0, 0)
    n2 = Node(2, 10, 0)
    c = Capacitor(1, n1, n2, capacitance=10e-6)

    assert c.capacitance == 10e-6
    c.set_params({"capacitance": 22e-6})
    assert c.capacitance == 22e-6


def test_inductor_properties() -> None:
    n1 = Node(1, 0, 0)
    n2 = Node(2, 10, 0)
    l = Inductor(1, n1, n2, inductance=1e-3)

    assert l.inductance == 1e-3
    l.set_params({"inductance": 2.2e-3})
    assert l.inductance == 2.2e-3


def test_switch_properties() -> None:
    n1 = Node(1, 0, 0)
    n2 = Node(2, 10, 0)
    sw = Switch(1, n1, n2, state="open")

    assert sw.get_state() == "open"
    assert sw.resistance == sw.resistance_open

    sw.set_state("closed")
    assert sw.get_state() == "closed"
    assert sw.resistance == (sw.resistance_closed if sw.resistance_closed > 0 else 1e-9)


def test_diode_and_led() -> None:
    n1 = Node(1, 0, 0)
    n2 = Node(2, 10, 0)

    d = Diode(1, n1, n2, saturation_current=1e-12, ideality_factor=1.5)
    assert d.saturation_current == 1e-12
    assert d.ideality_factor == 1.5

    led = LED(1, n1, n2, saturation_current=1e-10)
    assert led.saturation_current == 1e-10


def test_voltage_and_current_sources() -> None:
    n1 = Node(1, 0, 0)
    n2 = Node(2, 10, 0)

    # DC Source
    vdc = VoltageSourceDC(1, n1, n2, dc_voltage=5.0)
    assert vdc.dc_voltage == 5.0
    vdc.set_params({"dc_voltage": 9.0})
    assert vdc.dc_voltage == 9.0

    # AC Source
    vac = VoltageSourceAC(2, n1, n2, amplitude=10.0, frequency=50.0, phase=45.0)
    assert vac.amplitude == 10.0
    assert vac.frequency == 50.0
    assert vac.phase == 45.0
    vac.set_params({"amplitude": 12.0, "frequency": 60.0, "phase": 0.0})
    assert vac.frequency == 60.0

    # Current Sources
    idc = CurrentSourceDC(3, n1, n2, dc_current=0.5)
    assert idc.dc_current == 0.5
    iac = CurrentSourceAC(4, n1, n2, amplitude=0.1, frequency=1000.0, phase=90.0)
    assert iac.amplitude == 0.1


def test_controlled_sources() -> None:
    n1 = Node(1, 0, 0)
    n2 = Node(2, 10, 0)

    vcvs = VoltageControlledVoltageSource(1, n1, n2, control_dipole_id=10, gain=5.0)
    assert vcvs.gain == 5.0
    vcvs.set_params({"gain": 10.0})
    assert vcvs.gain == 10.0

    vccs = VoltageControlledCurrentSource(2, n1, n2, control_dipole_id=10, transconductance=0.02)
    assert vccs.transconductance == 0.02

    ccvs = CurrentControlledVoltageSource(3, n1, n2, control_dipole_id=10, transresistance=100.0)
    assert ccvs.transresistance == 100.0

    cccs = CurrentControlledCurrentSource(4, n1, n2, control_dipole_id=10, gain=2.5)
    assert cccs.gain == 2.5


def test_multi_terminal_components() -> None:
    n1 = Node(1, 0, 0)
    n2 = Node(2, 10, 0)
    n3 = Node(3, 20, 0)
    n4 = Node(4, 30, 0)

    # OpAmp
    opamp = OpAmp(1, n1, n2, n3, gain=100000.0)
    assert opamp.node_a is n1
    assert opamp.gain == 100000.0
    assert len(opamp.nodes) >= 3

    # Transformer
    transfo = Transformer(2, n1, n2, n3, n4, ratio=2.0)
    assert transfo.ratio == 2.0
    assert len(transfo.nodes) == 4
    transfo.set_params({"ratio": 5.0})
    assert transfo.get_params()["ratio"] == 5.0

    # Transistor
    bjt = Transistor(3, n1, n2, n3, beta=150.0)
    assert bjt.beta == 150.0
    assert len(bjt.nodes) == 3
    bjt.set_params({"beta": 200.0})
    assert bjt.get_params()["beta"] == 200.0

    # OpAmp
    opamp.set_params({"gain": 50000.0})
    assert opamp.get_params()["gain"] == 50000.0


def test_meters_and_ground() -> None:
    n1 = Node(1, 0, 0)
    n2 = Node(2, 10, 0)
    n1.potential = 3.3
    n2.potential = 0.0

    vm = Voltmeter(1, n1, n2)
    assert abs(vm.voltage - 3.3) < 1e-12
    assert "resistance" in vm.get_params()
    vm.set_params({"resistance": 1e9})
    assert vm.resistance == 1e9

    am = Ammeter(2, n1, n2)
    am.current = 0.05
    assert am.current == 0.05
    assert "resistance" in am.get_params()
    am.set_params({"resistance": 1e-6})
    assert am.resistance == 1e-6

    g = Ground(3, n1)
    assert n1.is_ground is True
    g.disconnect()
    assert n1.is_ground is False


def test_dipole_and_component_transformations() -> None:
    n1 = Node(1, 0, 0)
    n2 = Node(2, 10, 0)
    r = Resistor(1, n1, n2, x=5.0, y=10.0, rotation=45.0)

    # Position & Rotation
    assert r.position == (5.0, 10.0)
    assert r.rotation == 45.0
    assert r.node_count == 2

    # Node replacement
    n3 = Node(3, 20, 0)
    replaced = r.replace_node(n1, n3)
    assert replaced is True
    assert r.node_a is n3

    # Disconnect
    r.disconnect()
    assert r.node_a is None
    assert r.node_b is None


def test_stateful_dipole_generic() -> None:
    n1 = Node(1, 0, 0)
    n2 = Node(2, 10, 0)

    # VoltageSource stateful
    v = VoltageSource(1, n1, n2, state="dc", dc_voltage=5.0, amplitude=10.0, frequency=50.0)
    assert v.get_state() == "dc"
    assert v.get_dc_value() == 5.0
    assert v.get_ac_phasor() == 0.0

    v.set_state("ac")
    assert v.get_state() == "ac"
    assert v.get_dc_value() == 0.0
    assert abs(v.get_ac_phasor() - 10.0) < 1e-6
    assert abs(v.get_value_at_time(0.0) - 0.0) < 1e-6

    params = v.get_params()
    assert params["state"] == "ac"
    assert params["dc_voltage"] == 5.0
    v.set_params({"state": "dc", "dc_voltage": 12.0, "amplitude": 8.0, "frequency": 100.0, "phase": 30.0, "offset": 1.0})
    assert v.dc_voltage == 12.0
    assert v.frequency == 100.0

    # CurrentSource stateful
    i = CurrentSource(2, n1, n2, state="dc", dc_current=1.0, amplitude=2.0)
    assert i.get_dc_value() == 1.0
    i.set_state("ac")
    assert i.get_dc_value() == 0.0
    assert abs(i.get_ac_phasor() - 2.0) < 1e-6
    i.set_params({"state": "dc", "dc_current": 3.0, "amplitude": 4.0, "frequency": 60.0, "phase": 0.0, "offset": 0.0})
    assert i.dc_current == 3.0