"""
Tests unitaires complets pour tous les contrôleurs et services associés.

Couvre :
- AppController (statut, messages, couleur, not_implemented, etc.)
- CircuitController (zoom, centrage, grille, snap, nodes, wire direction, labels, etc.)
- EditController (sélection, filtrage, miroirs, alignement, distribution, undo/redo snapshots)
- FileController (nouveau, ouvrir, sauvegarder, sauvegarder sous, importer, exporter, récents)
- CircuitIOService (sauvegarde, chargement, import, export, export CSV)
- UICallbacks et MessageType
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
import pytest
from PyQt5.QtWidgets import QGraphicsItem

from controller.app_controller import AppController
from controller.circuit_controller import CircuitController
from controller.edit_controller import EditController
from controller.file_controller import FileController
from controller.io_service import CircuitIOService
from controller.ui_callbacks import MessageType, UICallbacks
from model.circuit import Circuit
from model.components import (
    Capacitor,
    CurrentSourceAC,
    CurrentSourceDC,
    Inductor,
    Resistor,
    Switch,
    VoltageSourceAC,
    VoltageSourceDC,
)
from model.node import Node
from model.wire import Wire


class DummyUICallbacks(UICallbacks):
    """Implémentation factice de UICallbacks pour tester les contrôleurs."""

    def __init__(self) -> None:
        self.status_messages: list[tuple[str, int]] = []
        self.shown_messages: list[tuple[str, str, MessageType]] = []
        self.applied_tools: list[str] = []
        self.current_filename: Optional[str] = None
        self.refreshed: bool = False
        self.transform_actions_updated: bool = False
        self.undo_snapshots_count: int = 0
        self.toolbar_geometry_updated: bool = False
        self.grid_toggled: bool = False
        self.snap_toggled: bool = False
        self.nodes_toggled: bool = False
        self.wire_direction_toggled: bool = False
        self.meter_mode: Optional[str] = None
        self.picked_color: Optional[str] = "#123456"
        self.applied_background_color: Optional[str] = None

    def set_status_message(self, message: str, timeout_ms: int = 3000) -> None:
        self.status_messages.append((message, timeout_ms))

    def show_message(
        self,
        title: str,
        message: str,
        message_type: MessageType = MessageType.INFO,
    ) -> None:
        self.shown_messages.append((title, message, message_type))

    def apply_tool(self, tool_name: str) -> None:
        self.applied_tools.append(tool_name)

    def set_current_filename(self, filename: Optional[str]) -> None:
        self.current_filename = filename

    def refresh_scene_from_model(self) -> None:
        self.refreshed = True

    def update_transform_actions_visibility(self) -> None:
        self.transform_actions_updated = True

    def push_undo_snapshot(self) -> None:
        self.undo_snapshots_count += 1

    def update_toolbar_geometry(self) -> None:
        self.toolbar_geometry_updated = True

    def toggle_grid(self) -> None:
        self.grid_toggled = True

    def toggle_snap(self) -> None:
        self.snap_toggled = True

    def toggle_nodes(self) -> None:
        self.nodes_toggled = True

    def toggle_wire_direction(self) -> None:
        self.wire_direction_toggled = True

    def set_meter_label_mode(self, mode: str) -> None:
        self.meter_mode = mode

    def pick_color(self) -> object | None:
        return self.picked_color

    def apply_view_background_color(self, color: object) -> None:
        self.applied_background_color = str(color)


# ==============================================================================
# 1. Tests AppController
# ==============================================================================

def test_app_controller_status_and_messages() -> None:
    callbacks = DummyUICallbacks()
    app = AppController(callbacks)

    app.set_status("Test status message", timeout_ms=5000)
    assert callbacks.status_messages == [("Test status message", 5000)]

    app.show_info("Info Title", "Info body")
    app.show_warning("Warn Title", "Warn body")
    app.show_error("Err Title", "Err body")

    assert len(callbacks.shown_messages) == 3
    assert callbacks.shown_messages[0] == ("Info Title", "Info body", MessageType.INFO)
    assert callbacks.shown_messages[1] == ("Warn Title", "Warn body", MessageType.WARNING)
    assert callbacks.shown_messages[2] == ("Err Title", "Err body", MessageType.ERROR)

    app.not_implemented("Super Feature")
    assert "Super Feature" in callbacks.status_messages[-1][0]


def test_app_controller_color_change() -> None:
    callbacks = DummyUICallbacks()
    callbacks.picked_color = "#abcdef"
    app = AppController(callbacks)

    app.change_background_color()
    assert callbacks.applied_background_color == "#abcdef"

    callbacks.picked_color = None
    app.change_background_color()
    assert callbacks.applied_background_color == "#abcdef"


def test_app_controller_stubs() -> None:
    callbacks = DummyUICallbacks()
    app = AppController(callbacks)
    app.change_language("en")
    app.change_theme("dark")
    app.toggle_fullscreen()
    app.toggle_components_panel()
    app.toggle_toolbar()


# ==============================================================================
# 2. Tests CircuitController
# ==============================================================================

class DummyView:
    def __init__(self) -> None:
        self.scales: list[tuple[float, float]] = []
        self.reset_called = False
        self.center_point = None

    def scale(self, sx: float, sy: float) -> None:
        self.scales.append((sx, sy))

    def resetTransform(self) -> None:
        self.reset_called = True

    def centerOn(self, point: Any) -> None:
        self.center_point = point


class DummyRect:
    def __init__(self, left: float, top: float, width: float, height: float) -> None:
        self._l = left
        self._t = top
        self._w = width
        self._h = height

    def left(self) -> float:
        return self._l

    def right(self) -> float:
        return self._l + self._w

    def top(self) -> float:
        return self._t

    def bottom(self) -> float:
        return self._t + self._h

    def center(self) -> tuple[float, float]:
        return (self._l + self._w / 2, self._t + self._h / 2)

    def united(self, other: DummyRect) -> DummyRect:
        min_l = min(self.left(), other.left())
        max_r = max(self.right(), other.right())
        min_t = min(self.top(), other.top())
        max_b = max(self.bottom(), other.bottom())
        return DummyRect(min_l, min_t, max_r - min_l, max_b - min_t)


class DummyScene:
    def __init__(self) -> None:
        self.grid_toggled = False
        self.snap_toggled = False
        self.nodes_toggled = False
        self.wire_direction_toggled = False
        self.meter_mode = None
        self._items: list[Any] = []
        self.cut_called = False
        self.copy_called = False
        self.paste_called = False

    def toggle_grid(self) -> None:
        self.grid_toggled = True

    def toggle_snap(self) -> None:
        self.snap_toggled = True

    def toggle_nodes(self) -> None:
        self.nodes_toggled = True

    def toggle_wire_direction(self) -> None:
        self.wire_direction_toggled = True

    def set_meter_label_mode(self, mode: str) -> None:
        self.meter_mode = mode

    def selectedItems(self) -> list[Any]:
        return [it for it in self._items if getattr(it, "isSelected", lambda: False)()]

    def items(self) -> list[Any]:
        return self._items

    def clearSelection(self) -> None:
        for it in self._items:
            if hasattr(it, "setSelected"):
                it.setSelected(False)

    def cut_selection(self) -> None:
        self.cut_called = True

    def copy_selection(self) -> None:
        self.copy_called = True

    def paste_selection(self, view_rect: Any = None) -> None:
        self.paste_called = True

    def handle_component_move(self, item: Any) -> None:
        pass

    def finalize_node_move(self, item: Any) -> None:
        pass

    def preview_node_move(self, node: Any, pos: Any) -> None:
        pass

    def _merge_overlaps_and_refresh(self) -> None:
        pass

    def _sync_free_node_items_from_model(self) -> None:
        pass


def test_circuit_controller_zoom_and_views() -> None:
    view = DummyView()
    scene = DummyScene()
    app = AppController(DummyUICallbacks())
    ctrl = CircuitController(window=None, scene=scene, view=view, app_controller=app)

    ctrl.zoom_in()
    assert len(view.scales) == 1
    assert view.scales[0] == (1.25, 1.25)

    ctrl.zoom_out()
    assert len(view.scales) == 2
    assert view.scales[1] == (0.8, 0.8)

    ctrl.reset_zoom()
    assert view.reset_called is True


def test_circuit_controller_toggles() -> None:
    view = DummyView()
    scene = DummyScene()
    callbacks = DummyUICallbacks()
    app = AppController(callbacks)
    ctrl = CircuitController(window=None, scene=scene, view=view, app_controller=app)

    ctrl.toggle_grid()
    assert scene.grid_toggled is True

    ctrl.toggle_snap_grid()
    assert scene.snap_toggled is True

    ctrl.toggle_nodes()
    assert scene.nodes_toggled is True

    ctrl.toggle_wire_direction()
    assert scene.wire_direction_toggled is True

    ctrl.set_meter_label_mode("both")
    assert scene.meter_mode == "both"

    ctrl.toggle_labels()
    ctrl.toggle_fullscreen()
    ctrl.highlight_short_circuit()


# ==============================================================================
# 3. Tests FileController & CircuitIOService
# ==============================================================================

def test_file_controller_new_circuit() -> None:
    circuit = Circuit()
    n1 = circuit.create_node(0, 0)
    circuit.add_dipole(Resistor(1, n1, n1))
    callbacks = DummyUICallbacks()
    fc = FileController(circuit, callbacks)

    fc.new_circuit()
    assert len(circuit.nodes) == 0
    assert len(circuit.dipoles) == 0
    assert callbacks.refreshed is True
    assert callbacks.current_filename is None


def test_file_controller_open_save_cycle(tmp_path: Path) -> None:
    circuit = Circuit()
    n1 = circuit.create_node(0, 0, is_ground=True)
    n2 = circuit.create_node(100, 0)
    r = Resistor(1, n1, n2, resistance=2200.0)
    circuit.add_dipole(r)

    callbacks = DummyUICallbacks()
    fc = FileController(circuit, callbacks)

    file_path = tmp_path / "test_circuit.json"
    saved = fc.save_circuit_to_path(file_path)
    assert saved is True
    assert file_path.exists()
    assert fc.current_path == file_path
    assert file_path in fc.recent_files

    circuit.clear()
    assert len(circuit.nodes) == 0

    opened = fc.open_circuit_from_path(file_path)
    assert opened is True
    assert len(circuit.nodes) == 2
    assert len(circuit.dipoles) == 1
    assert circuit.dipoles[1].resistance == 2200.0


def test_file_controller_export_and_import(tmp_path: Path) -> None:
    circuit = Circuit()
    n1 = circuit.create_node(0, 0)
    callbacks = DummyUICallbacks()
    fc = FileController(circuit, callbacks)

    export_path = tmp_path / "export.json"
    exported = fc.export_circuit_to_path(export_path)
    assert exported is True
    assert export_path.exists()

    csv_path = tmp_path / "results.csv"
    transient_data = {
        "time": [0.0, 0.001, 0.002],
        "node_potentials": {1: [0.0, 5.0, 5.0]},
        "dipole_currents": {1: [0.0, 0.01, 0.01]},
    }
    csv_exported = fc.export_transient_results_csv_to_path(csv_path, transient_data)
    assert csv_exported is True
    assert csv_path.exists()


def test_file_controller_open_invalid_path() -> None:
    circuit = Circuit()
    callbacks = DummyUICallbacks()
    fc = FileController(circuit, callbacks)

    opened = fc.open_circuit_from_path("/invalid/path/that/does/not/exist.json")
    assert opened is False
    assert len(callbacks.shown_messages) == 1
    assert callbacks.shown_messages[0][2] == MessageType.ERROR


def test_io_service_delegations(tmp_path: Path) -> None:
    service = CircuitIOService()
    circuit = Circuit()
    n1 = circuit.create_node(0, 0)
    n2 = circuit.create_node(50, 0)
    circuit.add_dipole(Resistor(1, n1, n2, resistance=470.0))

    file_path = tmp_path / "io_service_test.json"
    service.save_circuit_to_file(circuit, file_path)
    assert file_path.exists()

    circuit_loaded = Circuit()
    service.load_circuit_from_file(circuit_loaded, file_path)
    assert len(circuit_loaded.dipoles) == 1

    import_path = tmp_path / "import_test.json"
    service.export_circuit(circuit, str(import_path))
    assert import_path.exists()

    sim_path = tmp_path / "sim.json"
    service.export_simulation_results({"test": 123}, sim_path)
    assert sim_path.exists()


# ==============================================================================
# 4. Tests EditController
# ==============================================================================

class DummyComponentItem:
    def __init__(self, component: Any, x: float = 0.0, y: float = 0.0) -> None:
        self.component = component
        self._selected = False
        self._pos = (float(x), float(y))

    def flags(self) -> int:
        return 3

    def isSelected(self) -> bool:
        return self._selected

    def setSelected(self, s: bool) -> None:
        self._selected = s

    def pos(self) -> Any:
        from PyQt5.QtCore import QPointF
        return QPointF(self._pos[0], self._pos[1])

    def setPos(self, p: Any) -> None:
        self._pos = (p.x(), p.y())

    def sceneBoundingRect(self) -> Any:
        from PyQt5.QtCore import QRectF
        return QRectF(self._pos[0], self._pos[1], 40, 40)

    def update_model_nodes(self) -> None:
        pass


class DummyNodeItem:
    def __init__(self, node: Node, x: float = 0.0, y: float = 0.0) -> None:
        self.node = node
        self._selected = False
        self._pos = (float(x), float(y))

    def flags(self) -> int:
        return 3

    def isSelected(self) -> bool:
        return self._selected

    def setSelected(self, s: bool) -> None:
        self._selected = s

    def pos(self) -> Any:
        from PyQt5.QtCore import QPointF
        return QPointF(self._pos[0], self._pos[1])

    def setPos(self, p: Any) -> None:
        self._pos = (p.x(), p.y())

    def sceneBoundingRect(self) -> Any:
        from PyQt5.QtCore import QRectF
        return QRectF(self._pos[0], self._pos[1], 10, 10)


class DummyWireItem:
    def __init__(self, wire: Wire) -> None:
        self.wire = wire
        self._selected = False

    def flags(self) -> int:
        return 3

    def isSelected(self) -> bool:
        return self._selected

    def setSelected(self, s: bool) -> None:
        self._selected = s


def test_edit_controller_selections() -> None:
    callbacks = DummyUICallbacks()
    scene = DummyScene()

    c1 = Resistor(1, None, None)
    c2 = Capacitor(2, None, None)
    c3 = VoltageSourceDC(3, None, None)
    n1 = Node(1, 0, 0)
    w1 = Wire(1, n1, n1)

    item1 = DummyComponentItem(c1)
    item2 = DummyComponentItem(c2)
    item3 = DummyComponentItem(c3)
    item_node = DummyNodeItem(n1)
    item_wire = DummyWireItem(w1)

    scene._items = [item1, item2, item3, item_node, item_wire]
    edit_ctrl = EditController(scene=scene, ui_callbacks=callbacks)

    # select_all
    edit_ctrl.select_all()
    assert all(it.isSelected() for it in scene._items)

    # select_none
    edit_ctrl.select_none()
    assert all(not it.isSelected() for it in scene._items)

    # select_invert
    item1.setSelected(True)
    edit_ctrl.select_invert()
    assert item1.isSelected() is False
    assert item2.isSelected() is True
    assert item3.isSelected() is True


def test_edit_controller_filtering() -> None:
    callbacks = DummyUICallbacks()
    scene = DummyScene()

    c_res = Resistor(1, None, None)
    c_cap = Capacitor(2, None, None)
    c_ind = Inductor(3, None, None)
    c_src = VoltageSourceDC(4, None, None)
    n1 = Node(1, 0, 0)
    w1 = Wire(1, n1, n1)

    item_res = DummyComponentItem(c_res)
    item_cap = DummyComponentItem(c_cap)
    item_ind = DummyComponentItem(c_ind)
    item_src = DummyComponentItem(c_src)
    item_node = DummyNodeItem(n1)
    item_wire = DummyWireItem(w1)

    scene._items = [item_res, item_cap, item_ind, item_src, item_node, item_wire]
    edit_ctrl = EditController(scene=scene, ui_callbacks=callbacks)

    # Filtre résistances
    edit_ctrl.filter_resistors()
    assert item_res.isSelected() is True
    assert item_cap.isSelected() is False
    assert item_node.isSelected() is False

    # Filtre condensateurs
    edit_ctrl.select_none()
    edit_ctrl.filter_capacitors()
    assert item_cap.isSelected() is True
    assert item_res.isSelected() is False

    # Filtre inductances
    edit_ctrl.select_none()
    edit_ctrl.filter_inductors()
    assert item_ind.isSelected() is True

    # Filtre sources
    edit_ctrl.select_none()
    edit_ctrl.filter_sources()
    assert item_src.isSelected() is True

    # Filtre nœuds
    edit_ctrl.select_none()
    edit_ctrl.filter_nodes()
    assert item_node.isSelected() is True

    # Filtre fils
    edit_ctrl.select_none()
    edit_ctrl.filter_wires()
    assert item_wire.isSelected() is True


def test_edit_controller_transforms() -> None:
    callbacks = DummyUICallbacks()
    scene = DummyScene()

    item1 = DummyComponentItem(Resistor(1, None, None), x=0.0, y=0.0)
    item2 = DummyComponentItem(Resistor(2, None, None), x=100.0, y=100.0)
    item3 = DummyComponentItem(Resistor(3, None, None), x=200.0, y=200.0)

    scene._items = [item1, item2, item3]
    item1.setSelected(True)
    item2.setSelected(True)
    item3.setSelected(True)

    edit_ctrl = EditController(scene=scene, ui_callbacks=callbacks)

    # Miroir X
    edit_ctrl._mirror_selection("x")
    assert callbacks.undo_snapshots_count >= 1

    # Miroir Y et XY
    edit_ctrl._mirror_selection("y")
    edit_ctrl._mirror_selection("xy")
    assert callbacks.undo_snapshots_count >= 3

    # Alignement gauche, droite, haut, bas
    edit_ctrl._align_selection("left")
    edit_ctrl._align_selection("right")
    edit_ctrl._align_selection("top")
    edit_ctrl._align_selection("bottom")
    assert callbacks.undo_snapshots_count >= 7

    # Distribution X et Y
    edit_ctrl._distribute_selection("x")
    edit_ctrl._distribute_selection("y")
    assert callbacks.undo_snapshots_count >= 9

    # Cut / Copy / Paste
    edit_ctrl.cut()
    assert scene.cut_called is True

    edit_ctrl.copy()
    assert scene.copy_called is True

    edit_ctrl.paste()
    assert scene.paste_called is True


def test_circuit_controller_center_selection_empty_and_multiple() -> None:
    view = DummyView()
    scene = DummyScene()
    app = AppController(DummyUICallbacks())
    ctrl = CircuitController(window=None, scene=scene, view=view, app_controller=app)

    # Sans sélection -> aucun centrage
    ctrl.center_on_selection()
    assert view.center_point is None

    # Avec 2 éléments sélectionnés
    item1 = DummyComponentItem(Resistor(1, None, None), x=0.0, y=0.0)
    item2 = DummyComponentItem(Resistor(2, None, None), x=100.0, y=100.0)
    item1.setSelected(True)
    item2.setSelected(True)
    scene._items = [item1, item2]

    ctrl.center_on_selection()
    assert view.center_point is not None


def test_file_controller_save_current_path_branch(tmp_path: Path) -> None:
    circuit = Circuit()
    n1 = circuit.create_node(0, 0)
    callbacks = DummyUICallbacks()
    fc = FileController(circuit, callbacks)

    file_path = tmp_path / "auto_save.json"
    fc.current_path = file_path

    # Sauvegarde directe sans argument
    saved = fc.save_circuit()
    assert saved is True
    assert file_path.exists()