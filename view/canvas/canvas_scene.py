import math
from collections import deque
from typing import Optional

import numpy as np

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QPainter, QPen, QTransform
from PyQt5.QtWidgets import (
    QApplication,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
)

# Modele et elements graphiques
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
    Voltmeter,
    VoltageControlledVoltageSource,
    VoltageControlledCurrentSource,
    VoltageSource,
    VoltageSourceAC,
    VoltageSourceDC,
)
from view.component_item import ComponentItem, create_component_item
from view.wire_item import WireItem
from view.node_item import NodeItem
from view.components_panel import ComponentsListWidget

class CircuitView(QGraphicsView):
    """Vue graphique qui affiche la scene du circuit"""

    def __init__(self, scene, parent=None) -> None:
        """Initialise la vue graphique du circuit."""
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing)
        
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.set_tool_mode("pointer")
        
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.centerOn(0, 0)

        self.setAcceptDrops(True)

        self._ghost_preview = None
        self._ghost_tool_id = None
        
        # Etat de deplacement manuel de la vue
        self._is_panning = False
        self._pan_start_x = 0
        self._pan_start_y = 0
        self._pressed_on_item = False
        self._saved_drag_mode = None

    def set_tool_mode(self, tool_name: str) -> None:
        """Configure le comportement de la souris selon l'outil actif."""
        if tool_name == "pointer":
            # Le clic gauche selectionne, le glisser dessine une zone de selection
            self.setDragMode(QGraphicsView.RubberBandDrag)
        else:
            # Mode dessin
            self.setDragMode(QGraphicsView.NoDrag)

    def clear_tool_preview(self) -> None:
        """Supprime l'apercu de l'outil en cours."""
        self._clear_ghost_preview()

    def wheelEvent(self, event: object) -> None:
        """Ctrl + molette zoome la vue."""
        if event.modifiers() & Qt.ControlModifier:
            zoom_in_factor = 1.25
            zoom_out_factor = 1 / zoom_in_factor

            # Direction de la molette
            if event.angleDelta().y() > 0:
                zoom_factor = zoom_in_factor
            else:
                zoom_factor = zoom_out_factor

            self.scale(zoom_factor, zoom_factor)
        else:
            super().wheelEvent(event)
        
    def mousePressEvent(self, event: object) -> None:
        """Gere le debut des interactions souris."""
        if self._handle_pan_press(event):
            return

        # Evite la selection par rectangle quand un glisser commence sur un item.
        if event.button() == Qt.LeftButton and self.dragMode() == QGraphicsView.RubberBandDrag:
            item_under_cursor = self.itemAt(event.pos())
            if item_under_cursor is not None:
                self._pressed_on_item = True
                self._saved_drag_mode = self.dragMode()
                self.setDragMode(QGraphicsView.NoDrag)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: object) -> None:
        """Gere la fin des interactions souris."""
        if self._handle_pan_release(event):
            return
        super().mouseReleaseEvent(event)

        if event.button() == Qt.LeftButton and self._pressed_on_item:
            if self._saved_drag_mode is not None:
                self.setDragMode(self._saved_drag_mode)
            self._pressed_on_item = False
            self._saved_drag_mode = None

    def mouseMoveEvent(self, event: object) -> None:
        """Gere les mouvements de souris et le panoramique."""
        if self._handle_pan_move(event):
            return
        super().mouseMoveEvent(event)

    def dragEnterEvent(self, event: object) -> None:
        """Active l'apercu lors d'un glisser entrant."""
        tool_name = self._drag_component_tool(event)
        if tool_name is None:
            super().dragEnterEvent(event)
            return
        self._ensure_ghost_preview(tool_name)
        event.acceptProposedAction()

    def dragMoveEvent(self, event: object) -> None:
        """Met a jour l'apercu lors du glisser."""
        tool_name = self._drag_component_tool(event)
        if tool_name is None:
            super().dragMoveEvent(event)
            return
        self._ensure_ghost_preview(tool_name)
        self._update_ghost_position(event)
        event.acceptProposedAction()

    def dropEvent(self, event: object) -> None:
        """Cree un composant lors du depot."""
        tool_name = self._drag_component_tool(event)
        if tool_name is None:
            self._clear_ghost_preview()
            super().dropEvent(event)
            return

        self._drop_component_at(event, tool_name)
        self._clear_ghost_preview()
        event.acceptProposedAction()

    def dragLeaveEvent(self, event: object) -> None:
        """Supprime l'apercu lorsque le glisser sort."""
        self._clear_ghost_preview()
        super().dragLeaveEvent(event)

    def _handle_pan_press(self, event: object) -> bool:
        """Demarre le panoramique via le bouton central."""
        if event.button() != Qt.MiddleButton:
            return False
        self._is_panning = True
        self._pan_start_x = event.x()
        self._pan_start_y = event.y()
        self.setCursor(Qt.ClosedHandCursor)
        event.accept()
        return True

    def _handle_pan_release(self, event: object) -> bool:
        """Finalise le panoramique."""
        if event.button() != Qt.MiddleButton:
            return False
        self._is_panning = False
        self.setCursor(Qt.ArrowCursor)
        event.accept()
        return True

    def _handle_pan_move(self, event: object) -> bool:
        """Deplace la vue pendant le panoramique."""
        if not self._is_panning:
            return False
        dx = event.x() - self._pan_start_x
        dy = event.y() - self._pan_start_y
        self._pan_start_x = event.x()
        self._pan_start_y = event.y()
        self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - dx)
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() - dy)
        event.accept()
        return True

    def _drag_component_tool(self, event: object) -> Optional[str]:
        """Retourne l'outil correspondant au glisser de composant."""
        if not event.mimeData().hasFormat(ComponentsListWidget.MIME_TYPE):
            return None
        component_id = bytes(
            event.mimeData().data(ComponentsListWidget.MIME_TYPE)
        ).decode("utf-8")
        return self._component_id_to_tool(component_id)

    def _update_ghost_position(self, event: object) -> None:
        """Met a jour la position de l'apercu."""
        if self._ghost_preview is None:
            return
        scene_pos = self.mapToScene(event.pos())
        if hasattr(self.scene(), "get_snapped_position"):
            grid_x, grid_y = self.scene().get_snapped_position(scene_pos)
        else:
            grid_x, grid_y = scene_pos.x(), scene_pos.y()
        self._ghost_preview.setPos(grid_x, grid_y)

    def _drop_component_at(self, event: object, tool_name: str) -> None:
        """Ajoute un composant a la position du depot."""
        scene_pos = self.mapToScene(event.pos())
        if hasattr(self.scene(), "get_snapped_position"):
            grid_x, grid_y = self.scene().get_snapped_position(scene_pos)
        else:
            grid_x, grid_y = scene_pos.x(), scene_pos.y()
        self.scene().add_component_at(tool_name, grid_x, grid_y)

    def _component_id_to_tool(self, component_id: str) -> Optional[str]:
        """Convertit un identifiant de composant en outil interne."""
        if component_id.startswith("source_fake_"):
            return "source"
        if component_id.startswith("passive_fake_"):
            return "resistor"
        if component_id.startswith("measurement_fake_"):
            return None

        return component_id

    def _ensure_ghost_preview(self, tool_name: Optional[str]) -> None:
        """Cree l'apercu de placement si necessaire."""
        if tool_name is None:
            self._clear_ghost_preview()
            return

        if self._ghost_preview is not None and self._ghost_tool_id == tool_name:
            return

        self._clear_ghost_preview()
        self._ghost_tool_id = tool_name

        ghost = QGraphicsRectItem(-30, -20, 60, 40)
        pen = QPen(QColor("#7a6a3a"), 2, Qt.DashLine)
        ghost.setPen(pen)
        ghost.setBrush(QBrush(Qt.NoBrush))
        ghost.setOpacity(0.7)
        ghost.setZValue(10)

        if self.scene() is not None:
            self.scene().addItem(ghost)
        self._ghost_preview = ghost

    def _clear_ghost_preview(self) -> None:
        """Supprime l'apercu du composant."""
        if self._ghost_preview is None:
            self._ghost_tool_id = None
            return
        if self.scene() is not None:
            self.scene().removeItem(self._ghost_preview)
        self._ghost_preview = None
        self._ghost_tool_id = None

class CircuitScene(QGraphicsScene):
    """Scene qui heberge les elements et gere la logique d'edition"""
    # Reglages de la grille
    GRID_SIZE = 20
    WIRE_SNAP_THRESHOLD = 15.0
    WIRE_SNAP_ANGLE_WEIGHT = 0.3
    WIRE_SNAP_MIN_ANGLE_DIFF = 15.0
    WIRE_SNAP_VISUAL_FEEDBACK = True

    def __init__(self, model) -> None:
        """Initialise la scene de circuit et son etat interne."""
        super().__init__()
        self.model = model
  
        limit = 1000000 
        self.setSceneRect(-limit, -limit, limit * 2, limit * 2)
        
        self.current_tool = "pointer"

        # Etat temporaire pour le dessin de fil
        self.drawing_wire = False
        self.temp_wire_item: Optional[QGraphicsLineItem] = None
        self.start_pos = (0, 0)
        self._group_move_active = False
        self._drag_started_on_item = False
        self._press_scene_pos: Optional[QPointF] = None
        self._suppress_move_until_release = False
        self._selection_snapshot: Optional[list] = None
        self._snap_candidates: dict[object, float] = {}
        self._last_snap_target = None
        self.show_grid = True
        self.snap_enabled = True
        self.nodes_visible = True
        self.show_voltage_arrows = True
        self.show_current_arrows = True
        self._wire_current_cache: dict[int, float] = {}

        # Etat d'annulation (stocke des instantanes complets du circuit avant edition)
        self._undo_stack: list[dict] = []
        self._redo_stack: list[dict] = []
        self._max_undo_steps = 100
        self._component_classes = {
            "Resistor": Resistor,
            "VoltageSource": VoltageSource,
            "VoltageSourceDC": VoltageSourceDC,
            "VoltageSourceAC": VoltageSourceAC,
            "CurrentSource": CurrentSource,
            "CurrentSourceDC": CurrentSourceDC,
            "CurrentSourceAC": CurrentSourceAC,
            "VoltageControlledCurrentSource": VoltageControlledCurrentSource,
            "CurrentControlledCurrentSource": CurrentControlledCurrentSource,
            "VoltageControlledVoltageSource": VoltageControlledVoltageSource,
            "CurrentControlledVoltageSource": CurrentControlledVoltageSource,
            "Capacitor": Capacitor,
            "Inductor": Inductor,
            "Diode": Diode,
            "LED": LED,
            "Switch": Switch,
            "Ammeter": Ammeter,
            "Voltmeter": Voltmeter,
            "Ground": Ground,
            "Transformer": Transformer,
            "Transistor": Transistor,
            "OpAmp": OpAmp,
        }
        self._clipboard_payload: Optional[dict] = None

    def _capture_snapshot(self) -> Optional[str]:
        """Capture un instantane JSON du circuit."""
        if self.model is None:
            return None
        return self.model.to_json()

    def _restore_snapshot(self, snapshot: str) -> None:
        """Restaure un instantane JSON du circuit."""
        if self.model is None:
            return
        self.model.load_from_json(snapshot, self._component_classes)
        self.refresh_from_model()

    def _push_undo_snapshot(self) -> None:
        """Empile un instantane pour annulation et invalide le redo."""
        snapshot = self._capture_snapshot()
        if snapshot is None:
            return
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > self._max_undo_steps:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo_last_action(self) -> None:
        """Annule la derniere action modifiant le circuit."""
        if not self._undo_stack:
            return
        current = self._capture_snapshot()
        snapshot = self._undo_stack.pop()
        if current is not None:
            self._redo_stack.append(current)
        self._restore_snapshot(snapshot)

    def redo_last_action(self) -> None:
        """Retablit la derniere action annulee."""
        if not self._redo_stack:
            return
        current = self._capture_snapshot()
        snapshot = self._redo_stack.pop()
        if current is not None:
            self._undo_stack.append(current)
        self._restore_snapshot(snapshot)

    def set_tool(self, tool_name: str) -> None:
        """Definit le nom de l'outil actif."""
        if tool_name != "wire" and self.drawing_wire:
            self.cancel_wire_drawing()
        if tool_name != "pointer":
            self.clearSelection()
        self.current_tool = tool_name
        self._update_node_cursors(tool_name)

    def _update_node_cursors(self, tool_name: str) -> None:
        """Met a jour les curseurs des noeuds selon l'outil actif."""
        cursor = Qt.OpenHandCursor if tool_name == "pointer" else Qt.CrossCursor
        for item in self.items():
            if isinstance(item, NodeItem):
                item.setCursor(cursor)

    def toggle_wire_direction(self) -> None:
        """Bascule l'affichage des fleches de courant sur les fils."""
        self.show_current_arrows = not self.show_current_arrows
        self.update_overlay_indicators()

    def update_overlay_indicators(self) -> None:
        """Redessine les indicateurs de tension et de courant."""
        self._wire_current_cache = self._compute_wire_current_map()
        for item in self.items():
            if isinstance(item, (ComponentItem, WireItem)):
                item.update()

    def get_wire_current(self, wire_id: int) -> float:
        """Retourne le courant calcule pour un fil."""
        return float(self._wire_current_cache.get(int(wire_id), 0.0))

    def _compute_wire_current_map(self) -> dict[int, float]:
        """Calcule un courant pour chaque fil a partir des dipoles connectes."""
        if self.model is None:
            return {}

        wires = [wire for wire in self.model.wires.values() if wire.node_a is not None and wire.node_b is not None]
        if not wires:
            return {}

        adjacency: dict[object, list[object]] = {}
        for wire in wires:
            adjacency.setdefault(wire.node_a, []).append(wire.node_b)
            adjacency.setdefault(wire.node_b, []).append(wire.node_a)

        def _dipole_current_for_kcl(dipole: object) -> float:
            current = float(getattr(dipole, "current", 0.0))
            if isinstance(
                dipole,
                (
                    VoltageSource,
                    VoltageControlledVoltageSource,
                    CurrentControlledVoltageSource,
                ),
            ):
                return -current
            return current

        wire_current: dict[int, float] = {}
        eps = 1e-9
        unvisited = set(adjacency.keys())

        while unvisited:
            start_node = unvisited.pop()
            stack = [start_node]
            nodes = [start_node]
            while stack:
                node = stack.pop()
                for neighbor in adjacency.get(node, []):
                    if neighbor in unvisited:
                        unvisited.remove(neighbor)
                        stack.append(neighbor)
                        nodes.append(neighbor)

            node_set = set(nodes)
            component_wires = [
                wire for wire in wires if wire.node_a in node_set and wire.node_b in node_set
            ]
            if not component_wires:
                continue

            node_index = {node: i for i, node in enumerate(nodes)}
            node_count = len(nodes)
            edge_count = len(component_wires)

            B = np.zeros((node_count, edge_count))
            for e_idx, wire in enumerate(component_wires):
                idx_a = node_index.get(wire.node_a)
                idx_b = node_index.get(wire.node_b)
                if idx_a is None or idx_b is None:
                    continue
                B[idx_a, e_idx] = 1.0
                B[idx_b, e_idx] = -1.0

            b = np.zeros(node_count)
            for node, idx in node_index.items():
                total = 0.0
                for dipole in getattr(node, "connected_dipoles", []):
                    current = _dipole_current_for_kcl(dipole)
                    if getattr(dipole, "node_a", None) is node:
                        total += current
                    elif getattr(dipole, "node_b", None) is node:
                        total -= current
                b[idx] = -total

            if np.all(np.abs(b) <= eps):
                for wire in component_wires:
                    wire_current[wire.id] = 0.0
                continue

            bb_t = B @ B.T
            bb_t_inv = np.linalg.pinv(bb_t)
            currents = B.T @ (bb_t_inv @ b)

            for e_idx, wire in enumerate(component_wires):
                value = float(currents[e_idx])
                if abs(value) < 1e-9:
                    value = 0.0
                wire_current[wire.id] = value

        return wire_current
    def has_clipboard_content(self) -> bool:
        """Indique si le presse-papiers contient des elements."""
        if not self._clipboard_payload:
            return False
        return bool(
            self._clipboard_payload.get("components")
            or self._clipboard_payload.get("wires")
            or self._clipboard_payload.get("nodes")
        )

    def _clipboard_key(self, x: float, y: float, decimals: int = 6) -> tuple[float, float]:
        """Normalise une position pour l'index du presse-papiers."""
        return round(float(x), decimals), round(float(y), decimals)

    def _component_terminal_positions(
        self, center_x: float, center_y: float, rotation: float
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        """Calcule les positions des bornes d'un composant."""
        offset = 30
        rad = math.radians(rotation)
        dx = offset * math.cos(rad)
        dy = offset * math.sin(rad)
        return (
            (float(center_x - dx), float(center_y - dy)),
            (float(center_x + dx), float(center_y + dy)),
        )

    def _serialize_component_for_clipboard(self, component_model) -> dict:
        """Serialise un composant pour le presse-papiers."""
        params = {}
        if hasattr(component_model, "get_params"):
            params = dict(component_model.get_params())

        cx, cy = component_model.position
        return {
            "type": component_model.__class__.__name__,
            "name": component_model.name,
            "position": [float(cx), float(cy)],
            "rotation": float(component_model.rotation),
            "params": params,
        }

    def copy_selection(self) -> bool:
        """Copie la selection courante dans le presse-papiers interne."""
        if self.model is None:
            return False
        items = self.selectedItems()
        if not items:
            self._clipboard_payload = None
            return False

        components: list[dict] = []
        wires: list[dict] = []
        free_nodes: list[dict] = []

        selected_nodes = set()
        selected_wire_ids = set()

        for item in items:
            if isinstance(item, ComponentItem):
                component = item.component
                if component is None:
                    continue
                components.append(self._serialize_component_for_clipboard(component))
                if component.node_a is not None:
                    selected_nodes.add(component.node_a)
                if component.node_b is not None:
                    selected_nodes.add(component.node_b)
            elif isinstance(item, WireItem):
                wire = item.wire
                if wire is None:
                    continue
                selected_wire_ids.add(wire.id)
                if wire.node_a is not None:
                    selected_nodes.add(wire.node_a)
                if wire.node_b is not None:
                    selected_nodes.add(wire.node_b)
            elif isinstance(item, NodeItem):
                node = item.node
                if node is None or self._is_node_attached_to_dipole(node):
                    continue
                nx, ny = node.position
                free_nodes.append(
                    {
                        "position": [float(nx), float(ny)],
                        "is_ground": bool(node.is_ground),
                    }
                )
                selected_nodes.add(node)

        for wire in self.model.wires.values():
            if wire.id not in selected_wire_ids:
                if wire.node_a not in selected_nodes or wire.node_b not in selected_nodes:
                    continue
            if wire.node_a is None or wire.node_b is None:
                continue
            ax, ay = wire.node_a.position
            bx, by = wire.node_b.position
            wires.append(
                {
                    "node_a": [float(ax), float(ay)],
                    "node_b": [float(bx), float(by)],
                    "color": wire.color,
                }
            )

        self._clipboard_payload = {
            "components": components,
            "wires": wires,
            "nodes": free_nodes,
        }
        return bool(components or wires or free_nodes)

    def cut_selection(self) -> bool:
        """Coupe la selection (copie puis supprime)."""
        if not self.copy_selection():
            return False
        self.delete_selection()
        return True

    def _clipboard_payload_bounds(
        self, components: list[dict], wires: list[dict], free_nodes: list[dict]
    ) -> Optional[tuple[float, float, float, float]]:
        """Retourne les bornes englobantes du presse-papiers."""
        xs = []
        ys = []

        for component_data in components:
            cx, cy = component_data.get("position", [0.0, 0.0])
            xs.append(float(cx))
            ys.append(float(cy))

        for wire_data in wires:
            ax, ay = wire_data.get("node_a", [0.0, 0.0])
            bx, by = wire_data.get("node_b", [0.0, 0.0])
            xs.extend([float(ax), float(bx)])
            ys.extend([float(ay), float(by)])

        for node_data in free_nodes:
            nx, ny = node_data.get("position", [0.0, 0.0])
            xs.append(float(nx))
            ys.append(float(ny))

        if not xs or not ys:
            return None
        return min(xs), min(ys), max(xs), max(ys)

    def _payload_overlaps_existing(
        self,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
        margin: float = 0.0,
    ) -> bool:
        """Indique si un collage chevauche des elements existants."""
        if self.model is None:
            return False
        min_x -= margin
        min_y -= margin
        max_x += margin
        max_y += margin

        for dipole in self.model.dipoles.values():
            cx, cy = dipole.position
            if min_x <= cx <= max_x and min_y <= cy <= max_y:
                return True

        for node in self.model.nodes.values():
            nx, ny = node.position
            if min_x <= nx <= max_x and min_y <= ny <= max_y:
                return True

        return False

    def _find_free_paste_offset(
        self, bounds: Optional[tuple[float, float, float, float]], margin: float
    ) -> tuple[float, float]:
        """Cherche un decalage libre pour coller sans collision."""
        if bounds is None:
            return 0.0, 0.0
        min_x, min_y, max_x, max_y = bounds
        width = max_x - min_x
        height = max_y - min_y
        step = max(width, height) + margin
        if step <= 0:
            step = float(self.GRID_SIZE)

        candidates = [(0.0, 0.0)]
        for i in range(1, 21):
            shift = float(step * i)
            candidates.extend(
                [
                    (shift, 0.0),
                    (0.0, shift),
                    (-shift, 0.0),
                    (0.0, -shift),
                    (shift, shift),
                    (-shift, shift),
                    (shift, -shift),
                    (-shift, -shift),
                ]
            )

        for offset_x, offset_y in candidates:
            if not self._payload_overlaps_existing(
                min_x + offset_x,
                min_y + offset_y,
                max_x + offset_x,
                max_y + offset_y,
                margin=margin,
            ):
                return offset_x, offset_y

        return float(step), 0.0

    def _paste_create_or_get_node(
        self,
        node_cache: dict[tuple[float, float], object],
        x: float,
        y: float,
        is_ground: bool = False,
    ) -> object:
        """Retourne un noeud existant ou en cree un nouveau."""
        key = self._clipboard_key(x, y)
        existing = node_cache.get(key)
        if existing is not None:
            if is_ground:
                existing.is_ground = True
                existing._potential = 0.0
            return existing

        node = self.model.create_node(float(x), float(y), is_ground=is_ground)
        node_cache[key] = node
        return node

    def _paste_component(
        self,
        component_data: dict,
        offset_x: float,
        offset_y: float,
        node_cache: dict[tuple[float, float], object],
    ) -> Optional[ComponentItem]:
        """Cree un composant a partir d'un bloc de presse-papiers."""
        component_type = component_data.get("type")
        component_cls = self._component_classes.get(component_type)
        if component_cls is None:
            return None

        position = component_data.get("position", [0.0, 0.0])
        center_x = float(position[0]) + float(offset_x)
        center_y = float(position[1]) + float(offset_y)
        rotation = float(component_data.get("rotation", 0.0))

        node_a = self.model.create_node(0.0, 0.0)
        node_b = self.model.create_node(0.0, 0.0)

        dipole_id = self.model.get_next_dipole_id()
        name = component_data.get("name", component_type)
        dipole = component_cls(
            dipole_id,
            node_a,
            node_b,
            x=center_x,
            y=center_y,
            rotation=rotation,
            name=name,
        )

        params = dict(component_data.get("params", {}))
        if hasattr(dipole, "set_params"):
            dipole.set_params(params)

        (ax, ay), (bx, by) = self._component_terminal_positions(center_x, center_y, rotation)
        node_a.position = (ax, ay)
        node_b.position = (bx, by)

        self.model.add_dipole(dipole)
        item = create_component_item(dipole)
        self.addItem(item)
        item.setSelected(True)

        node_cache[self._clipboard_key(ax, ay)] = node_a
        node_cache[self._clipboard_key(bx, by)] = node_b
        return item

    def paste_selection(
        self, target_scene_pos: Optional[QPointF] = None, view_rect=None
    ) -> bool:
        """Colle les elements du presse-papiers dans la scene."""
        if not self._clipboard_payload:
            return False

        components = self._clipboard_payload.get("components", [])
        wires = self._clipboard_payload.get("wires", [])
        free_nodes = self._clipboard_payload.get("nodes", [])
        if not components and not wires and not free_nodes:
            return False

        self._push_undo_snapshot()
        self.clearSelection()

        bounds = self._clipboard_payload_bounds(components, wires, free_nodes)
        if bounds is None:
            return False
        min_x, min_y, max_x, max_y = bounds
        payload_center_x = (min_x + max_x) / 2.0
        payload_center_y = (min_y + max_y) / 2.0

        if target_scene_pos is not None:
            target_x, target_y = self.snap_to_grid(target_scene_pos)
            offset_x = float(target_x) - payload_center_x
            offset_y = float(target_y) - payload_center_y
        else:
            margin = float(self.GRID_SIZE * 2)
            offset = None
            if view_rect is not None:
                offset = self._find_free_paste_offset_in_rect(bounds, view_rect, margin)
            if offset is None:
                offset_x, offset_y = self._find_free_paste_offset(bounds, margin)
            else:
                offset_x, offset_y = offset

        node_cache = {}

        for component_data in components:
            self._paste_component(component_data, offset_x, offset_y, node_cache)

        for node_data in free_nodes:
            nx, ny = node_data.get("position", [0.0, 0.0])
            self._paste_create_or_get_node(
                node_cache,
                float(nx) + offset_x,
                float(ny) + offset_y,
                is_ground=bool(node_data.get("is_ground", False)),
            )

        for wire_data in wires:
            ax, ay = wire_data.get("node_a", [0.0, 0.0])
            bx, by = wire_data.get("node_b", [0.0, 0.0])
            node_a = self._paste_create_or_get_node(node_cache, float(ax) + offset_x, float(ay) + offset_y)
            node_b = self._paste_create_or_get_node(node_cache, float(bx) + offset_x, float(by) + offset_y)
            if node_a is node_b:
                continue
            try:
                wire = self.model.create_wire(node_a, node_b)
            except ValueError:
                continue
            wire_item = WireItem(wire)
            self.addItem(wire_item)
            wire_item.setSelected(True)

        self._merge_overlaps_and_refresh()
        self._sync_free_node_items_from_model()
        return True

    def _find_free_paste_offset_in_rect(
        self,
        bounds: Optional[tuple[float, float, float, float]],
        view_rect: Optional[QRectF],
        margin: float,
    ) -> Optional[tuple[float, float]]:
        """Cherche un decalage libre dans une zone de vue."""
        if bounds is None or view_rect is None:
            return None
        min_x, min_y, max_x, max_y = bounds

        view_left = view_rect.left() + margin
        view_right = view_rect.right() - margin
        view_top = view_rect.top() + margin
        view_bottom = view_rect.bottom() - margin

        min_offset_x = view_left - min_x
        max_offset_x = view_right - max_x
        min_offset_y = view_top - min_y
        max_offset_y = view_bottom - max_y

        if min_offset_x > max_offset_x or min_offset_y > max_offset_y:
            return None

        step = max(1, int(self.GRID_SIZE))
        offsets = []
        start_x = int(min_offset_x // step) * step
        end_x = int(max_offset_x // step) * step
        start_y = int(min_offset_y // step) * step
        end_y = int(max_offset_y // step) * step

        for dx in range(start_x, end_x + step, step):
            for dy in range(start_y, end_y + step, step):
                offsets.append((float(dx), float(dy)))

        offsets.sort(key=lambda v: abs(v[0]) + abs(v[1]))

        for offset_x, offset_y in offsets:
            if not self._payload_overlaps_existing(
                min_x + offset_x,
                min_y + offset_y,
                max_x + offset_x,
                max_y + offset_y,
                margin=margin,
            ):
                return offset_x, offset_y

        return None

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        """Dessine la grille de points de fond pour l'alignement."""
        if not self.show_grid:
            return
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        
        # Dessine uniquement les points visibles
        left = int(rect.left()) - (int(rect.left()) % self.GRID_SIZE)
        top = int(rect.top()) - (int(rect.top()) % self.GRID_SIZE)
        
        points = []
        for x in range(left, int(rect.right()), self.GRID_SIZE):
            for y in range(top, int(rect.bottom()), self.GRID_SIZE):
                points.append(QPointF(x, y))
        
        painter.drawPoints(points)

    def snap_to_grid(self, pos: QPointF) -> tuple[float, float]:
        """Arrondit une position (x, y) au point de grille le plus proche."""
        if not self.snap_enabled:
            return pos.x(), pos.y()
        gs = self.GRID_SIZE
        x = round(pos.x() / gs) * gs
        y = round(pos.y() / gs) * gs
        return x, y
    
    def get_snapped_position(self, scene_pos: QPointF) -> tuple[float, float]:
        """
        Retourne les coordonnees aimantees (x, y)
        Priorite 1 : noeud existant
        Priorite 2 : grille
        """
        if not self.is_snapping_active():
            return scene_pos.x(), scene_pos.y()
        # Seuil d'aimantation en unites de scene
        THRESHOLD = 15.0
        
        mx, my = scene_pos.x(), scene_pos.y()
        
        closest_node_pos = None
        min_dist = float('inf')

        # Trouve le noeud le plus proche
        for node in self.model.nodes.values():
            nx, ny = node.position
            # Calcul de distance
            dist = ((mx - nx)**2 + (my - ny)**2)**0.5
            if dist < min_dist:
                min_dist = dist
                closest_node_pos = (nx, ny)

        if closest_node_pos and min_dist < THRESHOLD:
            return closest_node_pos

        if self.snap_enabled:
            return self.snap_to_grid(scene_pos)
        return scene_pos.x(), scene_pos.y()

    def toggle_grid(self) -> None:
        """Active ou desactive l'affichage de la grille."""
        self.show_grid = not self.show_grid
        if not self.show_grid:
            self._clear_snap_candidates()
        self.update()

    def toggle_snap(self) -> None:
        """Active ou desactive l'aimantation a la grille."""
        self.snap_enabled = not self.snap_enabled
        if not self.snap_enabled:
            self._clear_snap_candidates()

    def is_snapping_active(self) -> bool:
        """Indique si l'aimantation est active."""
        return True

    def toggle_nodes(self) -> None:
        """Affiche ou masque les noeuds libres."""
        self.nodes_visible = not self.nodes_visible
        for item in self.items():
            if isinstance(item, NodeItem):
                item.setVisible(self.nodes_visible)

    def clean_canvas(self) -> None:
        """Nettoie la scene (fusion et suppression des doublons)."""
        self._merge_overlaps_and_refresh()
        self._sync_free_node_items_from_model()

    def _calculate_snap_score(
        self,
        source_pos: tuple[float, float],
        cursor_pos: tuple[float, float],
        target_pos: tuple[float, float],
    ) -> float:
        """Calcule un score d'aimantation (plus petit = meilleur)."""
        sx, sy = source_pos
        cx, cy = cursor_pos
        tx, ty = target_pos

        dist = ((cx - tx) ** 2 + (cy - ty) ** 2) ** 0.5

        if (sx, sy) == (cx, cy):
            return dist

        angle_to_target = math.degrees(math.atan2(ty - sy, tx - sx))
        angle_to_cursor = math.degrees(math.atan2(cy - sy, cx - sx))
        diff = abs(angle_to_target - angle_to_cursor)
        diff = min(diff, 360 - diff)

        angle_penalty = 0.0
        if diff >= self.WIRE_SNAP_MIN_ANGLE_DIFF:
            angle_penalty = diff

        return dist + (angle_penalty * self.WIRE_SNAP_ANGLE_WEIGHT)

    def _update_snap_candidate_visuals(self) -> None:
        """Met a jour le feedback visuel des candidats d'aimantation."""
        if not self.WIRE_SNAP_VISUAL_FEEDBACK:
            return
        target = self._last_snap_target
        for item in self.items():
            if not isinstance(item, NodeItem):
                continue
            node = getattr(item, "node", None)
            is_candidate = node is not None and node is target
            item.set_snap_candidate(is_candidate)

    def _clear_snap_candidates(self) -> None:
        """Reinitialise les candidats d'aimantation."""
        self._snap_candidates.clear()
        self._last_snap_target = None
        self._update_snap_candidate_visuals()

    def get_smart_snapped_component_position(
        self, component_model, proposed_pos: QPointF, rotation: float
    ) -> QPointF:
        """Retourne une position de centre aimantee en temps reel pour un dipole en deplacement

        Si une borne s'approche d'une cible connectable (noeud d'un autre dipole ou
        extremite libre de fil), ajuste le centre pour que la borne tombe exactement
        sur la cible pendant le glisser
        """
        if component_model is None:
            return proposed_pos
        if self._group_move_active and len(self.selectedItems()) > 1:
            return proposed_pos

        threshold = 15
        offset = 30
        rad = math.radians(rotation)
        dx = offset * math.cos(rad)
        dy = offset * math.sin(rad)

        cx, cy = proposed_pos.x(), proposed_pos.y()
        ax, ay = cx - dx, cy - dy
        bx, by = cx + dx, cy + dy

        candidate_a = self._find_nearest_external_connectable_node(component_model, ax, ay, threshold)
        candidate_b = self._find_nearest_external_connectable_node(component_model, bx, by, threshold)

        best = None
        if candidate_a and candidate_b:
            best = ("a", candidate_a[0]) if candidate_a[1] <= candidate_b[1] else ("b", candidate_b[0])
        elif candidate_a:
            best = ("a", candidate_a[0])
        elif candidate_b:
            best = ("b", candidate_b[0])

        if best is None:
            return proposed_pos

        terminal, target_node = best
        tx, ty = target_node.position
        if terminal == "a":
            return QPointF(tx + dx, ty + dy)
        return QPointF(tx - dx, ty - dy)

    def mousePressEvent(self, event: object) -> None:
        """Gere les pressions souris dans la scene."""
        scene_pos = event.scenePos()
        grid_x, grid_y = self._compute_press_grid(scene_pos)
        self._set_press_state(scene_pos, grid_x, grid_y)

        if event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return

        if self.current_tool == "pointer":
            if self._handle_pointer_press(event, scene_pos):
                return
            super().mousePressEvent(event)
            return

        if self._handle_tool_press(event, grid_x, grid_y):
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: object) -> None:
        """Gere les mouvements souris dans la scene."""
        # Fil fantome
        if self._handle_wire_preview_move(event):
            return
        
        # Deplacement de groupe
        if self._handle_group_move(event):
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: object) -> None:
        """Gere les actions au relachement du clic gauche."""
        if event.button() != Qt.LeftButton:
            super().mouseReleaseEvent(event)
            return

        if self._handle_pointer_release(event):
            self._reset_press_state()
            return

        if self.current_tool == "wire" and self.drawing_wire:
            scene_pos = event.scenePos()
            snapped = self.get_wire_snap_position(
                None,
                scene_pos.x(),
                scene_pos.y(),
                self.WIRE_SNAP_THRESHOLD,
                source_pos=self.start_pos,
            )
            self.finish_wire_drawing(snapped.x(), snapped.y())
            event.accept()
        else:
            super().mouseReleaseEvent(event)

        self._reset_press_state()

    def _compute_press_grid(self, scene_pos) -> tuple[float, float]:
        """Calcule la position grille associee au clic."""
        grid_x, grid_y = self.get_snapped_position(scene_pos)
        if self.current_tool == "pointer":
            return self.snap_to_grid(scene_pos)
        return grid_x, grid_y

    def _set_press_state(self, scene_pos, grid_x, grid_y) -> None:
        """Memorise l'etat du clic pour les gestes suivants."""
        self._press_scene_pos = scene_pos
        self._last_grid_pos = QPointF(grid_x, grid_y)
        self._last_drag_pos = QPointF(scene_pos)
        self._group_move_active = False
        self._drag_started_on_item = False

    def _reset_press_state(self) -> None:
        """Reinitialise l'etat du clic apres un geste."""
        self._drag_started_on_item = False
        self._press_scene_pos = None
        self._last_drag_pos = None
        self._suppress_move_until_release = False
        if self._selection_snapshot is not None:
            for item in self._selection_snapshot:
                item.setSelected(True)
            self._selection_snapshot = None

    def _handle_pointer_press(self, event: object, scene_pos: QPointF) -> bool:
        """Gere le clic en mode pointeur."""
        item = self.itemAt(scene_pos, QTransform())
        if isinstance(item, WireItem):
            if item.isSelected() and len(self.selectedItems()) > 1:
                self._selection_snapshot = list(self.selectedItems())
                self._drag_started_on_item = True
                self._suppress_move_until_release = False
                event.accept()
                return True
            if not item.isSelected() and not (event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier)):
                self.clearSelection()
            item.setSelected(True)
            self._drag_started_on_item = True
            self._suppress_move_until_release = False
            return False
        if isinstance(item, NodeItem):
            if item.isSelected() and len(self.selectedItems()) > 1:
                self._selection_snapshot = list(self.selectedItems())
                self._drag_started_on_item = True
                self._suppress_move_until_release = False
                event.accept()
                return True
            if not item.isSelected() and not (event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier)):
                self.clearSelection()
            item.setSelected(True)
            self._drag_started_on_item = False
            self._suppress_move_until_release = False
            return False
        if isinstance(item, ComponentItem):
            if item.isSelected() and not (event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier)):
                # Conserve la selection courante et evite de lancer une selection par zone
                self._drag_started_on_item = True
                self._suppress_move_until_release = False
                event.accept()
                return True
            if not item.isSelected() and not (event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier)):
                # Clic sur un autre dipole: le rendre selectionne immediatement pour deplacer celui-ci.
                self.clearSelection()
                item.setSelected(True)
                self._drag_started_on_item = True
                self._suppress_move_until_release = False
                event.accept()
                return True
            self._drag_started_on_item = True
            self._suppress_move_until_release = False
            return False
        if not (event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier)):
            self.clearSelection()
            self._suppress_move_until_release = True
        return False

    def _handle_tool_press(self, event: object, grid_x: float, grid_y: float) -> bool:
        """Gere le clic en mode outil."""
        if self.current_tool == "wire":
            self.start_wire_drawing(grid_x, grid_y)
            event.accept()
            return True
        if self.current_tool in [
            "resistor",
            "source",
            "current_source",
            "source_dc",
            "source_ac",
            "current_source_dc",
            "current_source_ac",
            "source_vccs",
            "source_vcvs",
            "source_cccs",
            "source_ccvs",
            "capacitor",
            "inductor",
            "diode",
            "transformer",
            "transistor",
            "opamp",
            "led",
            "switch",
            "voltmeter",
            "ammeter",
            "ground",
        ]:
            self.add_component_at(self.current_tool, grid_x, grid_y)
            event.accept()
            return True
        return False

    def _handle_wire_preview_move(self, event: object) -> bool:
        """Met a jour l'apercu du fil pendant le dessin."""
        if self.current_tool != "wire" or not self.drawing_wire or not self.temp_wire_item:
            return False
        new_pos = event.scenePos()
        snapped = self.get_wire_snap_position(
            None,
            new_pos.x(),
            new_pos.y(),
            self.WIRE_SNAP_THRESHOLD,
            source_pos=self.start_pos,
        )
        line = self.temp_wire_item.line()
        line.setP2(QPointF(snapped.x(), snapped.y()))
        self.temp_wire_item.setLine(line)
        super().mouseMoveEvent(event)
        return True

    def _handle_group_move(self, event: object) -> bool:
        """Gere le deplacement de groupe en mode pointeur."""
        if getattr(self, "_wire_drag_active", False):
            return False
        if self.current_tool != "pointer" or not self.selectedItems() or not (event.buttons() & Qt.LeftButton):
            return False
        if not self._drag_started_on_item:
            return False
        if self._suppress_move_until_release:
            return False
        if self._press_scene_pos is not None:
            drag_distance = (event.scenePos() - self._press_scene_pos).manhattanLength()
            if drag_distance < QApplication.startDragDistance():
                return False

        selected_component_nodes = set()
        selected_wire_endpoint_counts = {}
        selected_free_nodes = set()
        selected_wire_items = []
        for selected_item in self.selectedItems():
            if hasattr(selected_item, "is_locked") and selected_item.is_locked():
                continue
            if isinstance(selected_item, ComponentItem):
                selected_component_nodes.add(selected_item.component.node_a)
                selected_component_nodes.add(selected_item.component.node_b)
            elif isinstance(selected_item, WireItem):
                selected_wire_items.append(selected_item)
                node_a = selected_item.wire.node_a
                node_b = selected_item.wire.node_b
                if node_a is not None:
                    selected_wire_endpoint_counts[node_a] = selected_wire_endpoint_counts.get(node_a, 0) + 1
                if node_b is not None:
                    selected_wire_endpoint_counts[node_b] = selected_wire_endpoint_counts.get(node_b, 0) + 1
            elif isinstance(selected_item, NodeItem):
                selected_free_nodes.add(selected_item.node)

        if selected_wire_items and not selected_component_nodes:
            self._detach_selected_wires_from_dipoles(selected_wire_items)
            selected_wire_endpoint_counts = {}
            for selected_item in selected_wire_items:
                node_a = selected_item.wire.node_a
                node_b = selected_item.wire.node_b
                if node_a is not None:
                    selected_wire_endpoint_counts[node_a] = selected_wire_endpoint_counts.get(node_a, 0) + 1
                if node_b is not None:
                    selected_wire_endpoint_counts[node_b] = selected_wire_endpoint_counts.get(node_b, 0) + 1

        preserve_internal_nodes = set(selected_component_nodes)
        preserve_internal_nodes.update(selected_free_nodes)
        for node, count in selected_wire_endpoint_counts.items():
            if count > 1:
                preserve_internal_nodes.add(node)
        preserve_node_model_ids = {node.id for node in preserve_internal_nodes if node is not None}

        use_grid_snap = bool(self.snap_enabled)
        if self._last_drag_pos is None:
            self._last_drag_pos = event.scenePos()
        drag_delta = event.scenePos() - self._last_drag_pos

        current_grid_x, current_grid_y = self.snap_to_grid(event.scenePos())
        current_grid_pos = QPointF(current_grid_x, current_grid_y)
        grid_delta = current_grid_pos - self._last_grid_pos

        move_delta = grid_delta if use_grid_snap else drag_delta

        if move_delta.manhattanLength() > 0:
            if not self._group_move_active:
                self._push_undo_snapshot()
            self._group_move_active = True
            moved_wire_node_ids = set()

            # Deplace d'abord les noeuds libres selectionnes et marque-les comme deja deplaces.
            # Cela evite de deplacer deux fois le meme noeud quand son fil est aussi selectionne.
            for item in self.selectedItems():
                if isinstance(item, NodeItem):
                    if hasattr(item, "is_locked") and item.is_locked():
                        continue
                    item.setPos(item.pos() + move_delta)
                    item.node.position = (item.pos().x(), item.pos().y())
                    moved_wire_node_ids.add(id(item.node))

            for item in self.selectedItems():
                if isinstance(item, ComponentItem):
                    if hasattr(item, "is_locked") and item.is_locked():
                        continue
                    item.setPos(item.pos() + move_delta)
                elif isinstance(item, WireItem):
                    if hasattr(item, "is_locked") and item.is_locked():
                        continue
                    detach = True
                    if selected_component_nodes:
                        if item.wire.node_a in selected_component_nodes or item.wire.node_b in selected_component_nodes:
                            detach = False
                    snap_endpoints = detach and not selected_component_nodes
                    item.apply_scene_delta(
                        move_delta,
                        detach_shared_nodes=detach,
                        moved_node_ids=moved_wire_node_ids,
                        snap_endpoints=False,
                        allow_grid_snap=use_grid_snap,
                        preserve_node_model_ids=preserve_node_model_ids,
                    )

            self._sync_free_node_items_from_model()

            self._last_grid_pos = current_grid_pos
            self._last_drag_pos = event.scenePos()

        event.accept()
        return True

    def _detach_selected_wires_from_dipoles(self, selected_wire_items: list[WireItem]) -> None:
        """Detache les fils selectionnes des noeuds de dipoles en conservant un noeud partage."""
        if self.model is None:
            return

        remap = {}

        for item in selected_wire_items:
            wire = getattr(item, "wire", None)
            if wire is None:
                continue

            for attr in ("node_a", "node_b"):
                node = getattr(wire, attr, None)
                if node is None:
                    continue
                if not self._is_node_attached_to_dipole(node):
                    continue

                new_node = remap.get(node)
                if new_node is None:
                    nx, ny = node.position
                    new_node = self.model.create_node(float(nx), float(ny))
                    remap[node] = new_node

                setattr(wire, attr, new_node)

    def _handle_pointer_release(self, event: object) -> bool:
        """Finalise un deplacement de groupe en mode pointeur."""
        if self.current_tool != "pointer":
            return False
        if not self._group_move_active:
            return False
        for item in self.selectedItems():
            if isinstance(item, ComponentItem):
                self.handle_component_move(item)
            elif isinstance(item, WireItem):
                self.handle_wire_move(item, record_undo=False)

        self._sync_free_node_items_from_model()

        self._group_move_active = False
        event.accept()
        return True

    def add_component_at(self, tool_type: str, x: float, y: float) -> None:
        """Cree un composant a la position donnee."""
        self._push_undo_snapshot()

        node_a = None
        node_b = None
        node_c = None
        node_d = None
        if tool_type == "ground":
            node_a = self.model.create_node(x, y, is_ground=True)
        else:
            node_a = self.model.create_node(x - 30, y)
            node_b = self.model.create_node(x + 30, y)
            if tool_type == "transformer":
                node_c = self.model.create_node(x - 30, y + 20)
                node_d = self.model.create_node(x + 30, y + 20)
        
        dipole = None
        d_id = self.model.get_next_dipole_id()

        def _default_control_id() -> int:
            if self.model is None or not getattr(self.model, "dipoles", None):
                return 0
            existing_ids = sorted(self.model.dipoles.keys())
            return int(existing_ids[0]) if existing_ids else 0

        # Creation du modele
        if tool_type == "resistor":
            dipole = Resistor(d_id, node_a, node_b, x, y, name=f"R{d_id}")
        elif tool_type == "source":
            dipole = VoltageSource(d_id, node_a, node_b, x, y, name=f"V{d_id}")
        elif tool_type == "current_source":
            dipole = CurrentSource(d_id, node_a, node_b, x, y, name=f"I{d_id}")
        elif tool_type == "source_dc":
            dipole = VoltageSourceDC(d_id, node_a, node_b, x, y, name=f"V{d_id}")
        elif tool_type == "source_ac":
            dipole = VoltageSourceAC(d_id, node_a, node_b, x, y, name=f"V{d_id}")
        elif tool_type == "current_source_dc":
            dipole = CurrentSourceDC(d_id, node_a, node_b, x, y, name=f"I{d_id}")
        elif tool_type == "current_source_ac":
            dipole = CurrentSourceAC(d_id, node_a, node_b, x, y, name=f"I{d_id}")
        elif tool_type == "transformer":
            dipole = Transformer(d_id, node_a, node_b, node_c, node_d, x, y, name=f"T{d_id}")
        elif tool_type == "transistor":
            dipole = Transistor(d_id, node_a, node_b, x, y, name=f"Q{d_id}")
        elif tool_type == "opamp":
            dipole = OpAmp(d_id, node_a, node_b, x, y, name=f"A{d_id}")
        elif tool_type == "voltmeter":
            dipole = Voltmeter(d_id, node_a, node_b, x, y, name=f"V{d_id}")
        elif tool_type == "ammeter":
            dipole = Ammeter(d_id, node_a, node_b, x, y, name=f"A{d_id}")
        elif tool_type == "ground":
            dipole = Ground(d_id, node_a, None, x, y)
        elif tool_type == "source_vccs":
            dipole = VoltageControlledCurrentSource(
                d_id,
                node_a,
                node_b,
                x,
                y,
                name=f"G{d_id}",
                control_dipole_id=_default_control_id(),
            )
        elif tool_type == "source_cccs":
            dipole = CurrentControlledCurrentSource(
                d_id,
                node_a,
                node_b,
                x,
                y,
                name=f"F{d_id}",
                control_dipole_id=_default_control_id(),
            )
        elif tool_type == "source_vcvs":
            dipole = VoltageControlledVoltageSource(
                d_id,
                node_a,
                node_b,
                x,
                y,
                name=f"E{d_id}",
                control_dipole_id=_default_control_id(),
            )
        elif tool_type == "source_ccvs":
            dipole = CurrentControlledVoltageSource(
                d_id,
                node_a,
                node_b,
                x,
                y,
                name=f"H{d_id}",
                control_dipole_id=_default_control_id(),
            )
        elif tool_type == "capacitor":
            dipole = Capacitor(d_id, node_a, node_b, x, y, name=f"C{d_id}")
        elif tool_type == "inductor":
            dipole = Inductor(d_id, node_a, node_b, x, y, name=f"L{d_id}")
        elif tool_type == "diode":
            dipole = Diode(d_id, node_a, node_b, x, y, name=f"D{d_id}")
        elif tool_type == "led":
            dipole = LED(d_id, node_a, node_b, x, y, name=f"LED{d_id}")
        elif tool_type == "switch":
            dipole = Switch(d_id, node_a, node_b, x, y, name=f"SW{d_id}")

        if dipole:
            self.model.add_dipole(dipole)

            item = create_component_item(dipole)
            self.addItem(item)

    def handle_component_move(self, component_item: ComponentItem) -> None:
        """Appelee apres la fin du deplacement d'un composant."""
        # Met a jour les coordonnees des noeuds
        component_item.update_model_nodes()

        # Aimantation intelligente : connecte les bornes du dipole deplace aux bornes proches
        self._smart_connect_component_to_nearby_dipole_nodes(component_item)
        
        # Collecte les identifiants des noeuds du composant deplace
        node_ids = {component_item.component.node_a.id, component_item.component.node_b.id}
        
        # Rafraichit les fils connectes a ces noeuds
        for item in self.items():
            if isinstance(item, WireItem):
                wire = item.wire
                if wire.node_a.id in node_ids or wire.node_b.id in node_ids:
                    item.refresh_geometry()

        self._merge_overlaps_and_refresh()
        self._sync_free_node_items_from_model()

    def _smart_connect_component_to_nearby_dipole_nodes(self, component_item: ComponentItem) -> None:
        """Aimante et connecte un dipole deplace vers des noeuds proches."""
        component_model = component_item.component
        threshold = 15

        # Choisit la meilleure ancre vers un noeud connectable proche
        ax, ay = component_model.node_a.position
        bx, by = component_model.node_b.position
        candidate_a = self._find_nearest_external_connectable_node(component_model, ax, ay, threshold)
        candidate_b = self._find_nearest_external_connectable_node(component_model, bx, by, threshold)

        if candidate_a and candidate_b and candidate_a[0] is not candidate_b[0]:
            mapping = self._try_snap_component_between_nodes(
                component_item,
                candidate_a[0],
                candidate_b[0],
                threshold,
            )
            if mapping is not None:
                node_for_a, node_for_b = mapping
                self._reattach_component_terminal_node(component_model, "node_a", node_for_a)
                self._reattach_component_terminal_node(component_model, "node_b", node_for_b)
                component_item.update_model_nodes()
                self._refresh_component_wires(component_model)
                return

        best = None
        if candidate_a and candidate_b:
            best = ("a", candidate_a[0]) if candidate_a[1] <= candidate_b[1] else ("b", candidate_b[0])
        elif candidate_a:
            best = ("a", candidate_a[0])
        elif candidate_b:
            best = ("b", candidate_b[0])

        if best is not None:
            terminal, target_node = best
            self._snap_component_terminal_to_node(component_item, terminal, target_node)
            component_item.update_model_nodes()

        # Reevalue et rattache les deux bornes quand c'est applicable
        used_target_nodes = set()
        for terminal in ("a", "b"):
            if terminal == "a":
                tx, ty = component_model.node_a.position
            else:
                tx, ty = component_model.node_b.position

            candidate = self._find_nearest_external_connectable_node(component_model, tx, ty, threshold)
            if candidate is None:
                continue

            target_node = candidate[0]
            if target_node in used_target_nodes:
                continue

            if terminal == "a" and component_model.node_b is target_node:
                continue
            if terminal == "b" and component_model.node_a is target_node:
                continue

            if terminal == "a":
                self._reattach_component_terminal_node(component_model, "node_a", target_node)
            else:
                self._reattach_component_terminal_node(component_model, "node_b", target_node)

            used_target_nodes.add(target_node)

        # Rafraichit tous les fils lies a ce dipole apres d'eventuels rattachements de noeuds
        self._refresh_component_wires(component_model)

    def _try_snap_component_between_nodes(
        self,
        component_item: ComponentItem,
        node_a,
        node_b,
        threshold: float,
    ) -> Optional[tuple[object, object]]:
        """Tente d'aligner les deux bornes du dipole sur deux noeuds cibles."""
        if node_a is None or node_b is None:
            return None
        ax, ay = node_a.position
        bx, by = node_b.position

        rotation = math.radians(component_item.rotation())
        offset = 30.0
        dx = offset * math.cos(rotation)
        dy = offset * math.sin(rotation)

        center_x = (ax + bx) / 2.0
        center_y = (ay + by) / 2.0

        term_a = (center_x - dx, center_y - dy)
        term_b = (center_x + dx, center_y + dy)

        def _dist(p1, p2) -> float:
            return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5

        direct = _dist((ax, ay), term_a) + _dist((bx, by), term_b)
        swap = _dist((ax, ay), term_b) + _dist((bx, by), term_a)

        if direct <= swap:
            best = ((node_a, node_b), _dist((ax, ay), term_a), _dist((bx, by), term_b))
        else:
            best = ((node_b, node_a), _dist((ax, ay), term_b), _dist((bx, by), term_a))

        (node_for_a, node_for_b), dist_a, dist_b = best
        if dist_a > threshold or dist_b > threshold:
            return None

        component_item.setPos(QPointF(center_x, center_y))
        component_item.update_model_nodes()
        return node_for_a, node_for_b

    def _refresh_component_wires(self, component_model) -> None:
        """Rafraichit les fils relies a un dipole."""
        node_ids = {component_model.node_a.id, component_model.node_b.id}
        for item in self.items():
            if isinstance(item, WireItem):
                wire = item.wire
                if wire.node_a.id in node_ids or wire.node_b.id in node_ids:
                    item.refresh_geometry()

    def _find_nearest_external_connectable_node(
        self, component_model, x: float, y: float, threshold: float
    ) -> Optional[tuple[object, float]]:
        """Retourne (noeud, distance) pour le noeud connectable le plus proche dans le seuil

        Les noeuds connectables sont :
        - les bornes d'autres dipoles
        - les extremites libres de fil (aucun dipole rattache, utilisees par un seul fil)
        """
        nearest_node = None
        nearest_dist = None

        # Candidat 1 : noeuds provenant d'autres dipoles
        for dipole in self.model.dipoles.values():
            if dipole is component_model:
                continue
            for node in (dipole.node_a, dipole.node_b):
                if node is None:
                    continue
                nx, ny = node.position
                dist = ((x - nx) ** 2 + (y - ny) ** 2) ** 0.5
                if dist > threshold:
                    continue
                if nearest_dist is None or dist < nearest_dist:
                    nearest_node = node
                    nearest_dist = dist

        # Candidat 2 : extremites libres de fil non connectees a un dipole
        for node in self.model.nodes.values():
            if not self._is_free_wire_endpoint(node):
                continue
            nx, ny = node.position
            dist = ((x - nx) ** 2 + (y - ny) ** 2) ** 0.5
            if dist > threshold:
                continue
            if nearest_dist is None or dist < nearest_dist:
                nearest_node = node
                nearest_dist = dist

        if nearest_node is None:
            return None
        return nearest_node, nearest_dist

    def _is_free_wire_endpoint(self, node) -> bool:
        """Retourne True quand le noeud est une extremite de fil libre."""
        if node is None:
            return False
        if getattr(node, "connected_dipoles", None):
            if len(node.connected_dipoles) > 0:
                return False

        wire_count = 0
        for wire in self.model.wires.values():
            if wire.node_a is node or wire.node_b is node:
                wire_count += 1
                if wire_count > 1:
                    return False
        return wire_count == 1

    def _snap_component_terminal_to_node(
        self, component_item: ComponentItem, terminal: str, target_node
    ) -> None:
        """Deplace le composant pour que la borne donnee arrive sur le noeud cible."""
        offset = 30
        rotation = math.radians(component_item.rotation())
        dx = offset * math.cos(rotation)
        dy = offset * math.sin(rotation)
        tx, ty = target_node.position

        if terminal == "a":
            cx = tx + dx
            cy = ty + dy
        else:
            cx = tx - dx
            cy = ty - dy

        component_item.setPos(QPointF(cx, cy))

    def _reattach_component_terminal_node(
        self, component_model, attr_name: str, target_node
    ) -> None:
        """Rattache la borne du composant au noeud cible et migre les references."""
        old_node = getattr(component_model, attr_name)
        if old_node is target_node:
            return

        if old_node is not None:
            old_node.position = target_node.position

        if old_node is not None:
            old_node.remove_connection(component_model)

        setattr(component_model, attr_name, target_node)
        target_node.add_connection(component_model)

        merged_node = self.model.merge_nodes(old_node, target_node)
        setattr(component_model, attr_name, merged_node)

    def _remove_node_if_unused(self, node) -> None:
        """Supprime un noeud s'il n'est plus utilise."""
        if node is None:
            return
        if node.id not in self.model.nodes:
            return

        used_by_dipole = any(
            dipole.node_a is node or dipole.node_b is node
            for dipole in self.model.dipoles.values()
        )
        used_by_wire = any(
            wire.node_a is node or wire.node_b is node
            for wire in self.model.wires.values()
        )
        if not used_by_dipole and not used_by_wire:
            self.model.remove_node(node.id)

    def _is_node_attached_to_dipole(self, node) -> bool:
        """Indique si un noeud est rattache a un dipole."""
        if node is None:
            return False
        connected = getattr(node, "connected_dipoles", None)
        return bool(connected)

    def _refresh_wires_for_node(self, node) -> None:
        """Rafraichit les fils relies a un noeud."""
        if node is None:
            return
        highlight_node = False
        for item in self.items():
            if isinstance(item, WireItem):
                wire = item.wire
                if wire.node_a is node or wire.node_b is node:
                    item.refresh_geometry()
                    if getattr(item, "_is_selected", False):
                        highlight_node = True
        for item in self.items():
            if isinstance(item, NodeItem) and getattr(item, "node", None) is node:
                if highlight_node:
                    item.setBrush(QColor("#0078d7"))
                else:
                    item.setBrush(QColor(Qt.black))

    def _refresh_free_node_items(self) -> None:
        """Reconstruit l'affichage des noeuds libres."""
        # Reconstruit l'affichage des noeuds qui ne sont pas rattaches a des dipoles
        for item in list(self.items()):
            if isinstance(item, NodeItem):
                self.removeItem(item)

        for node in self.model.nodes.values():
            if self._is_node_attached_to_dipole(node):
                continue
            item = NodeItem(node)
            item.setVisible(self.nodes_visible)
            self.addItem(item)

    def _merge_overlaps_and_refresh(self) -> bool:
        """Fusionne les noeuds qui se chevauchent et rafraichit la scene."""
        if self.model is None:
            return False

        nodes_changed = self.model.merge_overlapping_nodes()
        wires_changed = self._prune_invalid_and_duplicate_wires()
        if not nodes_changed and not wires_changed:
            return False

        for item in self.items():
            if isinstance(item, WireItem):
                item.refresh_geometry()

        self._sync_free_node_items_from_model()
        return True

    def _prune_invalid_and_duplicate_wires(self) -> bool:
        """Supprime les fils invalides et les doublons."""
        if self.model is None or not self.model.wires:
            return False

        removed_wire_ids = set()
        seen_pairs = {}

        # Conserve le fil avec le plus petit id et supprime les autres
        for wire in sorted(self.model.wires.values(), key=lambda w: w.id):
            node_a = wire.node_a
            node_b = wire.node_b

            # Fil invalide ou reduit a un seul noeud
            if node_a is None or node_b is None or node_a is node_b:
                removed_wire_ids.add(wire.id)
                continue

            # Fil trop court (strictement inferieur a une maille de grille)
            ax, ay = node_a.position
            bx, by = node_b.position
            if (ax - bx) ** 2 + (ay - by) ** 2 < self.GRID_SIZE ** 2:
                removed_wire_ids.add(wire.id)
                continue

            pair = (min(node_a.id, node_b.id), max(node_a.id, node_b.id))
            if pair in seen_pairs:
                removed_wire_ids.add(wire.id)
            else:
                seen_pairs[pair] = wire.id

        if not removed_wire_ids:
            return False

        candidate_unused_nodes = []
        for wire_id in removed_wire_ids:
            wire = self.model.wires.get(wire_id)
            if wire is None:
                continue
            if wire.node_a is not None:
                candidate_unused_nodes.append(wire.node_a)
            if wire.node_b is not None:
                candidate_unused_nodes.append(wire.node_b)
            self.model.remove_wire(wire_id)

        for item in list(self.items()):
            if isinstance(item, WireItem) and item.wire.id in removed_wire_ids:
                self.removeItem(item)

        for node in candidate_unused_nodes:
            self._remove_node_if_unused(node)

        return True

    def _sync_free_node_items_from_model(self) -> None:
        """Synchronise les noeuds libres depuis le modele."""
        # Synchronise les node_item existants avec les positions du modele
        existing_items = {}

        for item in list(self.items()):
            if not isinstance(item, NodeItem):
                continue

            node = getattr(item, "node", None)
            if node is None or node.id not in self.model.nodes or self._is_node_attached_to_dipole(node):
                self.removeItem(item)
                continue

            existing_items[node.id] = item
            x, y = node.position
            item.setPos(QPointF(x, y))

            highlight_node = False
            for wire_item in self.items():
                if isinstance(wire_item, WireItem):
                    wire = wire_item.wire
                    if (wire.node_a is node or wire.node_b is node) and getattr(
                        wire_item, "_is_selected", False
                    ):
                        highlight_node = True
                        break
            if highlight_node:
                item.setBrush(QColor("#0078d7"))
            else:
                item.setBrush(QColor(Qt.black))

        for node in self.model.nodes.values():
            if self._is_node_attached_to_dipole(node):
                continue
            if node.id not in existing_items:
                new_item = NodeItem(node)
                highlight_node = False
                for wire_item in self.items():
                    if isinstance(wire_item, WireItem):
                        wire = wire_item.wire
                        if (wire.node_a is node or wire.node_b is node) and getattr(
                            wire_item, "_is_selected", False
                        ):
                            highlight_node = True
                            break
                if highlight_node:
                    new_item.setBrush(QColor("#0078d7"))
                new_item.setVisible(self.nodes_visible)
                self.addItem(new_item)

    def preview_node_move(self, node_model, snapped_pos: QPointF) -> None:
        """Met a jour un noeud pendant le glisser."""
        if node_model is None:
            return
        node_model.position = (snapped_pos.x(), snapped_pos.y())
        self._refresh_wires_for_node(node_model)

    def finalize_node_move(self, node_item: NodeItem) -> None:
        """Finalise le deplacement d'un noeud libre."""
        if node_item is None or node_item.node is None:
            return
        node = node_item.node
        current_x = node_item.pos().x()
        current_y = node_item.pos().y()

        # Priorite : conserver un rattachement exact a un noeud connectable proche
        snapped_node = self._find_nearest_connectable_node_for_wire(
            node,
            current_x,
            current_y,
            self.WIRE_SNAP_THRESHOLD,
        )
        if snapped_node is not None:
            node = self._reattach_wire_node(node, snapped_node)
            x, y = node.position
        elif self.snap_enabled:
            x, y = self.snap_to_grid(node_item.pos())
            node.position = (x, y)
        else:
            x, y = current_x, current_y
            node.position = (x, y)
        node_item.setPos(QPointF(x, y))
        self._merge_overlaps_and_refresh()
        self._refresh_wires_for_node(node)
        self._sync_free_node_items_from_model()
        self._clear_snap_candidates()

    def _find_nearest_connectable_node_for_wire(
        self,
        source_node,
        x: float,
        y: float,
        threshold: float,
        source_pos: Optional[tuple[float, float]] = None,
    ) -> Optional[object]:
        """Retourne le noeud connectable le plus proche d'un bout de fil."""
        nearest_node = None
        best_score = None
        cursor_pos = (float(x), float(y))
        if source_pos is not None:
            source_pos = (float(source_pos[0]), float(source_pos[1]))
        elif source_node is not None:
            source_pos = (float(source_node.position[0]), float(source_node.position[1]))
        else:
            source_pos = cursor_pos

        self._snap_candidates = {}

        for dipole in self.model.dipoles.values():
            for node in (dipole.node_a, dipole.node_b):
                if node is None or node is source_node:
                    continue
                nx, ny = node.position
                dist = ((x - nx) ** 2 + (y - ny) ** 2) ** 0.5
                if dist > threshold:
                    continue
                score = self._calculate_snap_score(source_pos, cursor_pos, (nx, ny))
                self._snap_candidates[node] = score
                if best_score is None or score < best_score:
                    nearest_node = node
                    best_score = score

        for node in self.model.nodes.values():
            if node is source_node or not self._is_free_wire_endpoint(node):
                continue
            nx, ny = node.position
            dist = ((x - nx) ** 2 + (y - ny) ** 2) ** 0.5
            if dist > threshold:
                continue
            score = self._calculate_snap_score(source_pos, cursor_pos, (nx, ny))
            self._snap_candidates[node] = score
            if best_score is None or score < best_score:
                nearest_node = node
                best_score = score

        self._last_snap_target = nearest_node
        self._update_snap_candidate_visuals()
        return nearest_node

    def get_wire_snap_position(
        self,
        source_node,
        x: float,
        y: float,
        threshold: Optional[float] = None,
        source_pos: Optional[tuple[float, float]] = None,
        allow_grid_snap: bool = True,
    ) -> QPointF:
        """Retourne la position d'aimantation pour un bout de fil pendant le drag."""
        if threshold is None:
            threshold = self.WIRE_SNAP_THRESHOLD
        target_node = self._find_nearest_connectable_node_for_wire(
            source_node,
            x,
            y,
            threshold,
            source_pos=source_pos,
        )
        if target_node is not None:
            tx, ty = target_node.position
            return QPointF(tx, ty)
        self._clear_snap_candidates()
        if allow_grid_snap and self.snap_enabled:
            snapped_x, snapped_y = self.snap_to_grid(QPointF(x, y))
            return QPointF(snapped_x, snapped_y)
        return QPointF(float(x), float(y))

    def _reattach_wire_node(self, old_node, target_node) -> object:
        """Rattache un noeud de fil vers une cible."""
        if old_node is None or target_node is None or old_node is target_node:
            return target_node

        old_node.position = target_node.position

        return self.model.merge_nodes(old_node, target_node)

    def start_wire_drawing(self, x: float, y: float) -> None:
        """Demarre le dessin interactif d'un fil."""
        self.drawing_wire = True
        self.start_pos = (x, y)
        self._clear_snap_candidates()
        
        # Apercu temporaire du fil
        self.temp_wire_item = QGraphicsLineItem(x, y, x, y)
        pen = QPen(Qt.gray, 2, Qt.DashLine)
        self.temp_wire_item.setPen(pen)
        self.addItem(self.temp_wire_item)

    def finish_wire_drawing(self, x: float, y: float) -> None:
        """Finalise le fil et l'ajoute au modele."""
        
        start_x, start_y = self.start_pos
        
        # Nettoie l'apercu temporaire
        self.removeItem(self.temp_wire_item)
        self.temp_wire_item = None
        self.drawing_wire = False
        self._clear_snap_candidates()
        
        # N'ajoute pas de fil de longueur nulle
        if start_x == x and start_y == y:
            return

        # Enregistre la creation du fil comme action annulable independante
        self._push_undo_snapshot()

        # Trouve ou cree le noeud de depart
        node_a = self.model.get_node_at(start_x, start_y)
        if not node_a:
            node_a = self.model.create_node(start_x, start_y)
            
        # Trouve ou cree le noeud d'arrivee
        node_b = self.model.get_node_at(x, y)
        if not node_b:
            node_b = self.model.create_node(x, y)

        # Cree le fil dans le modele
        try:
            wire = self.model.create_wire(node_a, node_b)
            
            # Cree l'element graphique final du fil
            wire_item = WireItem(wire)
            self.addItem(wire_item)
            self._merge_overlaps_and_refresh()
            self._refresh_free_node_items()
            
        except Exception as e:
            print(f"[Erreur] Impossible de créer le fil : {e}")

    def update_wires_connected_to(self, component_model, new_pos: QPointF, rotation: float) -> None:
        """Met a jour les fils connectes pendant le deplacement d'un composant."""
        self._detach_component_from_shared_nodes(component_model)
        
        # Positions des noeuds depuis le centre et la rotation du composant
        cx, cy = new_pos.x(), new_pos.y()
        offset = 30
        rad = math.radians(rotation)
        dx = offset * math.cos(rad)
        dy = offset * math.sin(rad)
        
        # Met a jour le modele en temps reel
        component_model.node_a.position = (cx - dx, cy - dy)
        component_model.node_b.position = (cx + dx, cy + dy)
        component_model.position = (cx, cy)

        # Rafraichit les fils connectes
        node_ids = {component_model.node_a.id, component_model.node_b.id}
        
        for item in self.items():
            if isinstance(item, WireItem): 
                wire = item.wire
                if wire.node_a.id in node_ids or wire.node_b.id in node_ids:
                    item.refresh_geometry()

    def _detach_component_from_shared_nodes(self, component_model) -> None:
        """Detache un dipole d'un noeud partage avec d'autres dipoles si besoin."""
        if component_model is None or self.model is None:
            return

        selected_components = set()
        if self._group_move_active:
            selected_components = {
                item.component for item in self.selectedItems() if isinstance(item, ComponentItem)
            }

        for attr in ("node_a", "node_b"):
            node = getattr(component_model, attr, None)
            if node is None:
                continue
            connected = [
                dipole for dipole in getattr(node, "connected_dipoles", [])
                if dipole is not component_model
            ]
            if not connected:
                continue
            if self._group_move_active and selected_components:
                if all(dipole in selected_components for dipole in connected):
                    continue
            nx, ny = node.position
            new_node = self.model.create_node(float(nx), float(ny))
            node.remove_connection(component_model)
            new_node.add_connection(component_model)
            setattr(component_model, attr, new_node)

    def cancel_wire_drawing(self) -> None:
        """Annule l'operation de dessin de fil en cours."""
        if self.temp_wire_item:
            self.removeItem(self.temp_wire_item)
            self.temp_wire_item = None
        self.drawing_wire = False
        self._clear_snap_candidates()

    def handle_wire_move(self, wire_item: WireItem, record_undo: bool = True) -> None:
        """Met a jour le modele et reinitialise le visuel apres un deplacement de fil."""
        if record_undo:
            self._push_undo_snapshot()

        # Deplace les deux extremites du fil selon le deplacement de l'item
        delta = wire_item.pos()
        if delta.manhattanLength() > 0.1:
            wire_item.setPos(0, 0)
            wire_item.apply_scene_delta(
                delta,
                detach_shared_nodes=True,
                snap_endpoints=False,
                allow_grid_snap=True,
            )
            wire_item.refresh_geometry()
        else:
            wire_item.refresh_geometry()

        self._merge_overlaps_and_refresh()
        self._sync_free_node_items_from_model()

    def rotate_selected_components(self, angle_degrees: float) -> bool:
        """Tourne les dipoles selectionnes selon l'angle donne."""
        selected_components = [
            item for item in self.selectedItems() if isinstance(item, ComponentItem)
        ]
        if not selected_components:
            return False

        self._push_undo_snapshot()

        for item in selected_components:
            if hasattr(item, "is_locked") and item.is_locked():
                continue
            new_rotation = (item.rotation() + angle_degrees) % 360
            item.setRotation(new_rotation)
            item.component.rotation = float(new_rotation)
            self.update_wires_connected_to(item.component, item.pos(), new_rotation)

        return True

    def lock_selection(self) -> None:
        """Verrouille tous les elements selectionnes."""
        for item in self.selectedItems():
            if hasattr(item, "set_locked"):
                item.set_locked(True)

    def unlock_selection(self) -> None:
        """Deverrouille tous les elements selectionnes."""
        for item in self.selectedItems():
            if hasattr(item, "set_locked"):
                item.set_locked(False)

    def delete_selection(self) -> None:
        """Supprime tous les elements selectionnes."""
        selected = self.selectedItems()
        if not selected:
            return

        self._push_undo_snapshot()
        candidate_nodes = []

        for item in selected:
            if hasattr(item, "is_locked") and item.is_locked():
                continue
            # Supprime du modele
            if hasattr(item, 'component'):
                if item.component.node_a is not None:
                    candidate_nodes.append(item.component.node_a)
                if item.component.node_b is not None:
                    candidate_nodes.append(item.component.node_b)
                dipole_id = item.component.id
                self.model.remove_dipole(dipole_id)
            elif isinstance(item, WireItem):
                if item.wire.node_a is not None:
                    candidate_nodes.append(item.wire.node_a)
                if item.wire.node_b is not None:
                    candidate_nodes.append(item.wire.node_b)
                wire_id = item.wire.id
                self.model.remove_wire(wire_id)
            
            # Supprime de la scene
            self.removeItem(item)

        seen_node_ids = set()
        for node in candidate_nodes:
            if node is None or node.id in seen_node_ids:
                continue
            seen_node_ids.add(node.id)
            self._remove_node_if_unused(node)

        self._refresh_free_node_items()

    def refresh_from_model(self) -> None:
        """Vide la scene et la reconstruit a partir du modele."""
        self.clear()
        
        # Ajoute les dipoles
        for dipole in self.model.dipoles.values():
            item = create_component_item(dipole)
            self.addItem(item)
            
        # Ajoute les fils
        for wire in self.model.wires.values():
            wire_item = WireItem(wire)
            self.addItem(wire_item)

        self._refresh_free_node_items()
        self.update_overlay_indicators()