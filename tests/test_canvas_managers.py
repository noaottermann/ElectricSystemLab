"""
Tests unitaires pour les gestionnaires modulaires du canvas :
- SnapManager (aimantation aux points, recherche de nœud, angles de fil)
- ClipboardManager (instantanés JSON, undo/redo, presse-papier)
- SelectionManager (calcul de bounding box, rotation, déplacement)
- EditingManager (création de dipôles et composants multi-bornes par nom d'outil)
"""

from __future__ import annotations

import pytest
from PyQt5.QtCore import QPointF, QRectF
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsRectItem

from model.circuit import Circuit
from model.components import Ground, OpAmp, Resistor, Transformer, Transistor, VoltageSourceDC
from view.canvas.canvas_clipboard import ClipboardManager
from view.canvas.canvas_editing import EditingManager
from view.canvas.canvas_selection import SelectionManager
from view.canvas.canvas_snap import SnapManager


# ==============================================================================
# 1. Tests SnapManager
# ==============================================================================

def test_snap_manager_grid_points() -> None:
    snap = SnapManager(grid_size=20, snap_enabled=True)

    # Point QPointF
    pt = QPointF(23.4, 38.9)
    sx, sy = snap.snap_point(pt)
    assert sx == 20.0
    assert sy == 40.0

    # Tuple
    sx, sy = snap.snap_point((11.0, 29.0))
    assert sx == 20.0
    assert sy == 20.0

    # Snap désactivé
    snap.snap_enabled = False
    sx, sy = snap.snap_point((23.4, 38.9))
    assert sx == 23.4
    assert sy == 38.9


def test_snap_manager_find_nearest_node() -> None:
    snap = SnapManager(grid_size=20)
    circuit = Circuit()
    n1 = circuit.create_node(100, 100)
    n2 = circuit.create_node(200, 200)

    # Proche de n1 (< seuil)
    found = snap.find_nearest_node(102, 98, circuit, threshold=10.0)
    assert found is n1

    # Loin de tout
    found_none = snap.find_nearest_node(150, 150, circuit, threshold=10.0)
    assert found_none is None

    # Circuit None
    assert snap.find_nearest_node(100, 100, None) is None


def test_snap_manager_wire_angle() -> None:
    snap = SnapManager()

    # Angle horizontal
    end_x, end_y = snap.snap_wire_angle((0, 0), (100, 5), allow_diagonal=True)
    assert abs(end_y) < 1e-6
    assert abs(end_x - 100.1249) < 1.0

    # Angle 45°
    end_x, end_y = snap.snap_wire_angle((0, 0), (100, 95), allow_diagonal=True)
    assert abs(end_x - end_y) < 1e-6

    # Même point
    p = snap.snap_wire_angle((50, 50), (50, 50))
    assert p == (50, 50)


# ==============================================================================
# 2. Tests ClipboardManager
# ==============================================================================

def test_clipboard_manager_undo_redo() -> None:
    clip = ClipboardManager(max_undo_steps=5)
    c = Circuit()
    c.create_node(0, 0)

    snap1 = clip.capture_snapshot(c)
    clip.push_undo_state(snap1)

    c.create_node(50, 0)
    snap2 = clip.capture_snapshot(c)
    clip.push_undo_state(snap2)

    # Undo
    prev = clip.undo(current_snapshot=snap2)
    assert prev == snap2
    prev2 = clip.undo(current_snapshot=prev)
    assert prev2 == snap1

    # Redo
    nxt = clip.redo(current_snapshot=prev2)
    assert nxt is not None


def test_clipboard_manager_copy_paste() -> None:
    clip = ClipboardManager()
    assert clip.has_clipboard_data() is False
    assert clip.get_clipboard_payload() is None

    data = {"components": [{"type": "Resistor", "id": 1}]}
    clip.copy(data)
    assert clip.has_clipboard_data() is True

    payload = clip.get_clipboard_payload()
    assert payload == data
    # Modifiant payload ne modifie pas l'interne
    payload["components"].append({"type": "Capacitor"})
    assert len(clip.get_clipboard_payload()["components"]) == 1


# ==============================================================================
# 3. Tests SelectionManager
# ==============================================================================

def test_selection_manager_operations() -> None:
    sel_mgr = SelectionManager()

    item1 = QGraphicsRectItem(0, 0, 50, 50)
    item2 = QGraphicsRectItem(100, 100, 50, 50)

    bounding = sel_mgr.get_selection_bounding_rect([item1, item2])
    assert bounding.left() <= 0.0
    assert bounding.top() <= 0.0
    assert bounding.right() >= 150.0
    assert bounding.bottom() >= 150.0

    # Déplacement
    sel_mgr.move_selection([item1, item2], 10.0, 20.0)
    assert item1.x() == 10.0
    assert item1.y() == 20.0

    # Rotation
    sel_mgr.rotate_selection([item1], angle_step=90.0)
    assert item1.rotation() == 90.0


# ==============================================================================
# 4. Tests EditingManager
# ==============================================================================

def test_editing_manager_component_creation() -> None:
    circuit = Circuit()
    mgr = EditingManager(circuit=circuit)

    # Création résistance
    res = mgr.create_component_by_tool("resistor", 100, 100)
    assert isinstance(res, Resistor)
    assert res.id in circuit.dipoles

    # Création source DC
    src = mgr.create_component_by_tool("source_dc", 200, 100)
    assert isinstance(src, VoltageSourceDC)

    # Création masse
    gnd = mgr.create_component_by_tool("ground", 300, 100)
    assert isinstance(gnd, Ground)

    # Création AOP (multi-bornes)
    op = mgr.create_component_by_tool("opamp", 400, 100)
    assert isinstance(op, OpAmp)

    # Création Transformateur (4 bornes)
    tr = mgr.create_component_by_tool("transformer", 500, 100)
    assert isinstance(tr, Transformer)

    # Création Transistor (3 bornes)
    bjt = mgr.create_component_by_tool("transistor", 600, 100)
    assert isinstance(bjt, Transistor)

    # Outil inconnu
    assert mgr.create_component_by_tool("unknown_tool", 0, 0) is None