"""
Tests unitaires et d'intégration pour la Phase 3 (Architecture et Refactorisation).

Vérifie :
1. La classe abstraite Component et ses sous-classes multi-bornes (Dipole, OpAmp, Transformer, Transistor).
2. L'intégration de Component dans Circuit (gestion dynamique des bornes, suppression, fusion).
3. Le paquet persistence (sérialisation, import, export).
4. Le module config.constants (centralisation des constantes).
5. Les managers modulaires de canvas (SnapManager, ClipboardManager, SelectionManager, EditingManager).
6. Les modules de dialogs (simulation, composants, préférences).
"""

from __future__ import annotations

import json
import pytest

from config.constants import CANVAS, COMPONENT_DIM, SIMULATION, UI
from model.circuit import Circuit
from model.component import Component
from model.dipole import Dipole, StatefulDipole
from model.components import (
    OpAmp,
    Resistor,
    Switch,
    Transformer,
    Transistor,
    VoltageSourceDC,
    get_component_registry,
)
from persistence import exporter, importer, serializer
from view.canvas.canvas_snap import SnapManager
from view.canvas.canvas_clipboard import ClipboardManager
from view.canvas.canvas_selection import SelectionManager
from view.canvas.canvas_editing import EditingManager
from view.dialogs.simulation_dialogs import ACSweepDialog, TransientDialog
from view.dialogs.settings_dialogs import PreferencesDialog


# ===========================================================================
# 1. Tests de la hiérarchie Component & Dipole
# ===========================================================================

def test_component_base_hierarchy() -> None:
    """Vérifie que Dipole et les composants multi-bornes héritent bien de Component."""
    assert issubclass(Dipole, Component)
    assert issubclass(OpAmp, Component)
    assert issubclass(Transformer, Component)
    assert issubclass(Transistor, Component)
    assert issubclass(Resistor, Component)


def test_dipole_two_terminals() -> None:
    """Vérifie le fonctionnement de Dipole avec node_a et node_b."""
    circuit = Circuit()
    n1 = circuit.create_node(0, 0)
    n2 = circuit.create_node(100, 0)
    n1.potential = 10.0
    n2.potential = 3.0

    res = Resistor(1, n1, n2, resistance=500.0)
    assert res.node_count == 2
    assert res.node_a is n1
    assert res.node_b is n2
    assert res.voltage == 7.0

    # Déconnexion
    res.disconnect()
    assert res.node_a is None
    assert res.node_b is None
    assert len(n1.connected_dipoles) == 0


def test_opamp_three_terminals() -> None:
    """Vérifie le fonctionnement d'OpAmp en tant que composant à 3 bornes."""
    circuit = Circuit()
    n_in_p = circuit.create_node(0, 10)
    n_in_m = circuit.create_node(0, -10)
    n_out = circuit.create_node(100, 0)

    opamp = OpAmp(1, n_in_p, n_in_m, n_out, gain=1e5)
    assert opamp.node_count == 3
    assert opamp.node_in_plus is n_in_p
    assert opamp.node_in_minus is n_in_m
    assert opamp.node_out is n_out
    assert opamp.node_a is n_in_p
    assert opamp.node_b is n_in_m
    assert opamp.node_c is n_out

    # Sérialisation
    d = opamp.to_dict()
    assert d["type"] == "OpAmp"
    assert d["node_a_id"] == n_in_p.id
    assert d["node_b_id"] == n_in_m.id
    assert d["node_c_id"] == n_out.id


def test_transformer_four_terminals() -> None:
    """Vérifie le fonctionnement de Transformer à 4 bornes."""
    circuit = Circuit()
    n1 = circuit.create_node(0, 0)
    n2 = circuit.create_node(0, 40)
    n3 = circuit.create_node(100, 0)
    n4 = circuit.create_node(100, 40)

    transfo = Transformer(1, n1, n2, n3, n4, ratio=2.5)
    assert transfo.node_count == 4
    assert transfo.node_a is n1
    assert transfo.node_b is n2
    assert transfo.node_c is n3
    assert transfo.node_d is n4

    d = transfo.to_dict()
    assert d["type"] == "Transformer"
    assert d["node_a_id"] == n1.id
    assert d["node_b_id"] == n2.id
    assert d["node_c_id"] == n3.id
    assert d["node_d_id"] == n4.id
    assert d["params"]["ratio"] == 2.5


def test_transistor_three_terminals() -> None:
    """Vérifie le fonctionnement de Transistor (Collecteur, Base, Émetteur)."""
    circuit = Circuit()
    nc = circuit.create_node(50, 0)
    nb = circuit.create_node(0, 50)
    ne = circuit.create_node(50, 100)

    bjt = Transistor(1, nc, nb, ne, beta=150.0)
    assert bjt.node_count == 3
    assert bjt.node_collector is nc
    assert bjt.node_base is nb
    assert bjt.node_emitter is ne


# ===========================================================================
# 2. Tests de Circuit avec multi-bornes
# ===========================================================================

def test_circuit_handles_multiterminal_node_removal() -> None:
    """Vérifie que Circuit.remove_node nettoie correctement les composants multi-bornes."""
    circuit = Circuit()
    n1 = circuit.create_node(0, 0)
    n2 = circuit.create_node(0, 40)
    n3 = circuit.create_node(100, 0)
    n4 = circuit.create_node(100, 40)

    transfo = Transformer(circuit.get_next_dipole_id(), n1, n2, n3, n4)
    circuit.add_dipole(transfo)
    assert transfo.id in circuit.dipoles

    # Supprimer la 4ème borne (node_d) doit supprimer le transformateur
    circuit.remove_node(n4.id)
    assert transfo.id not in circuit.dipoles


def test_circuit_merge_nodes_updates_multiterminal() -> None:
    """Vérifie que Circuit.merge_nodes met à jour les références d'un composant 3 bornes."""
    circuit = Circuit()
    n_in_p = circuit.create_node(0, 10)
    n_in_m = circuit.create_node(0, -10)
    n_out = circuit.create_node(100, 0)
    n_extra = circuit.create_node(100, 0)  # superposé à n_out

    opamp = OpAmp(circuit.get_next_dipole_id(), n_in_p, n_in_m, n_extra)
    circuit.add_dipole(opamp)

    # Fusionner n_out et n_extra
    circuit.merge_nodes(n_out, n_extra)

    # n_extra a été fusionné dans n_out (id le plus petit)
    assert opamp.node_out is n_out


# ===========================================================================
# 3. Tests du package persistence
# ===========================================================================

def test_persistence_package_serialization() -> None:
    """Vérifie la sérialisation / désérialisation complète via le package persistence."""
    circuit = Circuit()
    gnd = circuit.create_node(0, 0, is_ground=True)
    n1 = circuit.create_node(0, 100)
    n2 = circuit.create_node(100, 100)

    src = VoltageSourceDC(circuit.get_next_dipole_id(), n1, gnd, dc_voltage=5.0)
    circuit.add_dipole(src)
    res = Resistor(circuit.get_next_dipole_id(), n1, n2, resistance=220.0)
    circuit.add_dipole(res)
    circuit.create_wire(n2, gnd)

    # Sérialisation JSON
    json_str = serializer.serialize_circuit(circuit)
    assert isinstance(json_str, str)
    data = json.loads(json_str)
    assert "nodes" in data
    assert "dipoles" in data
    assert "wires" in data

    # Désérialisation dans un nouveau circuit
    c_new = Circuit()
    serializer.deserialize_circuit(c_new, json_str)
    assert len(c_new.nodes) == 3
    assert len(c_new.dipoles) == 2
    assert len(c_new.wires) == 1


# ===========================================================================
# 4. Tests des constantes de configuration
# ===========================================================================

def test_config_constants() -> None:
    """Vérifie la présence et les types des constantes de configuration."""
    assert CANVAS.GRID_SIZE == 20
    assert CANVAS.WIRE_SNAP_THRESHOLD == 15.0
    assert CANVAS.NODE_SNAP_THRESHOLD == 10.0
    assert COMPONENT_DIM.DEFAULT_WIDTH == 60
    assert SIMULATION.AC_START_FREQ == 1.0
    assert SIMULATION.AC_STOP_FREQ == 1e6
    assert SIMULATION.CONVERGENCE_TOLERANCE == 1e-6
    assert UI.BUTTON_SIZE == 32
    assert UI.STATUS_MESSAGE_TIMEOUT == 3000


# ===========================================================================
# 5. Tests des managers modulaires du canvas
# ===========================================================================

def test_snap_manager() -> None:
    """Vérifie les fonctionnalités de SnapManager."""
    snap = SnapManager(grid_size=20, snap_enabled=True)

    # Snap sur grille
    sx, sy = snap.snap_point((18.0, 42.0))
    assert sx == 20.0
    assert sy == 40.0

    # Recherche de nœud le plus proche
    circuit = Circuit()
    n1 = circuit.create_node(100.0, 100.0)
    n2 = circuit.create_node(200.0, 200.0)

    nearest = snap.find_nearest_node(102.0, 99.0, circuit, threshold=10.0)
    assert nearest is n1

    none_found = snap.find_nearest_node(150.0, 150.0, circuit, threshold=10.0)
    assert none_found is None

    # Contrainte angulaire de fil
    ax, ay = snap.snap_wire_angle((0.0, 0.0), (100.0, 5.0), allow_diagonal=False)
    assert ax == 100.12492197250395 or abs(ay - 0.0) < 1e-3


def test_clipboard_manager() -> None:
    """Vérifie la pile d'annulation et le presse-papier de ClipboardManager."""
    clip = ClipboardManager(max_undo_steps=5)
    assert clip.has_clipboard_data() is False

    clip.push_undo_state('{"state": 1}')
    clip.push_undo_state('{"state": 2}')

    prev = clip.undo(current_snapshot='{"state": 3}')
    assert prev == '{"state": 2}'

    redone = clip.redo(current_snapshot='{"state": 2}')
    assert redone == '{"state": 3}'

    # Copie
    clip.copy({"components": [{"id": 1, "type": "Resistor"}]})
    assert clip.has_clipboard_data() is True
    payload = clip.get_clipboard_payload()
    assert payload is not None
    assert len(payload["components"]) == 1


def test_editing_manager() -> None:
    """Vérifie la fabrique de composants d'EditingManager."""
    circuit = Circuit()
    editing = EditingManager(circuit)

    res = editing.create_component_by_tool("resistor", 100.0, 100.0)
    assert isinstance(res, Resistor)
    assert res.id in circuit.dipoles

    src = editing.create_component_by_tool("source_dc", 200.0, 200.0)
    assert isinstance(src, VoltageSourceDC)
    assert src.id in circuit.dipoles
