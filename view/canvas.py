import math
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsLineItem, QGraphicsRectItem, QApplication
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QPainter, QPen, QColor, QTransform, QBrush

# Modele et elements graphiques
from model.components import Resistor, VoltageSourceDC, VoltageSourceAC, Capacitor, Inductor
from .component_item import ComponentItem, create_component_item
from .wire_item import WireItem
from .node_item import NodeItem
from .components_panel import ComponentsListWidget

class CircuitView(QGraphicsView):
    """Vue graphique qui affiche la scene du circuit"""
    def __init__(self, scene, parent=None):
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

    def set_tool_mode(self, tool_name):
        """Configure le comportement de la souris selon l'outil actif"""
        if tool_name == "pointer":
            # Le clic gauche selectionne, le glisser dessine une zone de selection
            self.setDragMode(QGraphicsView.RubberBandDrag)
        else:
            # Mode dessin
            self.setDragMode(QGraphicsView.NoDrag)

    def clear_tool_preview(self):
        self._clear_ghost_preview()

    def wheelEvent(self, event):
        """Ctrl + molette zoome la vue"""
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
        
    def mousePressEvent(self, event):
        if self._handle_pan_press(event):
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._handle_pan_release(event):
            return
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self._handle_pan_move(event):
            return
        super().mouseMoveEvent(event)

    def dragEnterEvent(self, event):
        tool_name = self._drag_component_tool(event)
        if tool_name is None:
            super().dragEnterEvent(event)
            return
        self._ensure_ghost_preview(tool_name)
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        tool_name = self._drag_component_tool(event)
        if tool_name is None:
            super().dragMoveEvent(event)
            return
        self._ensure_ghost_preview(tool_name)
        self._update_ghost_position(event)
        event.acceptProposedAction()

    def dropEvent(self, event):
        tool_name = self._drag_component_tool(event)
        if tool_name is None:
            self._clear_ghost_preview()
            super().dropEvent(event)
            return

        self._drop_component_at(event, tool_name)
        self._clear_ghost_preview()
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._clear_ghost_preview()
        super().dragLeaveEvent(event)

    def _handle_pan_press(self, event):
        if event.button() != Qt.MiddleButton:
            return False
        self._is_panning = True
        self._pan_start_x = event.x()
        self._pan_start_y = event.y()
        self.setCursor(Qt.ClosedHandCursor)
        event.accept()
        return True

    def _handle_pan_release(self, event):
        if event.button() != Qt.MiddleButton:
            return False
        self._is_panning = False
        self.setCursor(Qt.ArrowCursor)
        event.accept()
        return True

    def _handle_pan_move(self, event):
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

    def _drag_component_tool(self, event):
        if not event.mimeData().hasFormat(ComponentsListWidget.MIME_TYPE):
            return None
        component_id = bytes(
            event.mimeData().data(ComponentsListWidget.MIME_TYPE)
        ).decode("utf-8")
        return self._component_id_to_tool(component_id)

    def _update_ghost_position(self, event):
        if self._ghost_preview is None:
            return
        scene_pos = self.mapToScene(event.pos())
        if hasattr(self.scene(), "get_snapped_position"):
            grid_x, grid_y = self.scene().get_snapped_position(scene_pos)
        else:
            grid_x, grid_y = scene_pos.x(), scene_pos.y()
        self._ghost_preview.setPos(grid_x, grid_y)

    def _drop_component_at(self, event, tool_name):
        scene_pos = self.mapToScene(event.pos())
        if hasattr(self.scene(), "get_snapped_position"):
            grid_x, grid_y = self.scene().get_snapped_position(scene_pos)
        else:
            grid_x, grid_y = scene_pos.x(), scene_pos.y()
        self.scene().add_component_at(tool_name, grid_x, grid_y)

    def _component_id_to_tool(self, component_id):
        if component_id.startswith("source_fake_"):
            return "source_dc"
        if component_id.startswith("passive_fake_"):
            return "resistor"
        if component_id.startswith("measurement_fake_"):
            return None

        return component_id

    def _ensure_ghost_preview(self, tool_name):
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

    def _clear_ghost_preview(self):
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

    def __init__(self, model):
        super().__init__()
        self.model = model
  
        limit = 1000000 
        self.setSceneRect(-limit, -limit, limit * 2, limit * 2)
        
        self.current_tool = "pointer"

        # Etat temporaire pour le dessin de fil
        self.drawing_wire = False
        self.temp_wire_item = None
        self.start_pos = (0, 0)
        self._group_move_active = False
        self._drag_started_on_item = False
        self._press_scene_pos = None
        self._suppress_move_until_release = False
        self._selection_snapshot = None

        # Etat d'annulation (stocke des instantanes complets du circuit avant edition)
        self._undo_stack = []
        self._redo_stack = []
        self._max_undo_steps = 100
        self._component_classes = {
            "Resistor": Resistor,
            "VoltageSourceDC": VoltageSourceDC,
            "VoltageSourceAC": VoltageSourceAC,
            "Capacitor": Capacitor,
            "Inductor": Inductor,
        }
        self._clipboard_payload = None
        self._clipboard_paste_count = 0

    def set_tool(self, tool_name):
        """Definit le nom de l'outil actif"""
        if tool_name != "wire" and self.drawing_wire:
            self.cancel_wire_drawing()
        if tool_name != "pointer":
            self.clearSelection()
        self.current_tool = tool_name
        self._update_node_cursors(tool_name)

    def _update_node_cursors(self, tool_name):
        cursor = Qt.OpenHandCursor if tool_name == "pointer" else Qt.CrossCursor
        for item in self.items():
            if isinstance(item, NodeItem):
                item.setCursor(cursor)

    def _clear_item_cursors(self):
        for item in self.items():
            item.unsetCursor()

    def _push_undo_snapshot(self):
        """Enregistre l'etat courant du circuit avant une action qui modifie"""
        if self.model is None:
            return
        snapshot = self.model.to_json()
        if self._undo_stack and self._undo_stack[-1] == snapshot:
            return
        # Les nouvelles editions utilisateur invalident l'historique de retablissement
        self._redo_stack.clear()
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > self._max_undo_steps:
            self._undo_stack.pop(0)

    def undo_last_action(self):
        """Restaure l'instantane le plus recent de la pile d'annulation"""
        if self.model is None or not self._undo_stack:
            return False

        current_snapshot = self.model.to_json()
        previous_snapshot = self._undo_stack.pop()
        self._redo_stack.append(current_snapshot)
        self.model.load_from_json(previous_snapshot, self._component_classes)
        self.refresh_from_model()

        # Reinitialise l'etat d'interaction transitoire apres restauration
        self.cancel_wire_drawing()
        self._reset_press_state()
        self.clearSelection()
        self._group_move_active = False
        return True

    def redo_last_action(self):
        """Reapplique l'instantane annule le plus recent"""
        if self.model is None or not self._redo_stack:
            return False

        current_snapshot = self.model.to_json()
        next_snapshot = self._redo_stack.pop()
        self._undo_stack.append(current_snapshot)
        if len(self._undo_stack) > self._max_undo_steps:
            self._undo_stack.pop(0)

        self.model.load_from_json(next_snapshot, self._component_classes)
        self.refresh_from_model()

        self.cancel_wire_drawing()
        self._reset_press_state()
        self.clearSelection()
        self._group_move_active = False
        return True

    def _clipboard_key(self, x, y):
        return (round(float(x), 6), round(float(y), 6))

    def _component_terminal_positions(self, center_x, center_y, rotation):
        offset = 30
        rad = math.radians(rotation)
        dx = offset * math.cos(rad)
        dy = offset * math.sin(rad)
        return (
            (float(center_x - dx), float(center_y - dy)),
            (float(center_x + dx), float(center_y + dy)),
        )

    def _serialize_component_for_clipboard(self, component_model):
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

    def copy_selection(self):
        selected_items = self.selectedItems()
        if not selected_items:
            return False

        components = []
        wires = []
        free_nodes = []

        seen_component_ids = set()
        seen_wire_ids = set()
        seen_node_ids = set()

        for item in selected_items:
            if isinstance(item, ComponentItem):
                component = getattr(item, "component", None)
                if component is None or component.id in seen_component_ids:
                    continue
                components.append(self._serialize_component_for_clipboard(component))
                seen_component_ids.add(component.id)
                continue

            if isinstance(item, WireItem):
                wire = getattr(item, "wire", None)
                if wire is None or wire.id in seen_wire_ids:
                    continue
                if wire.node_a is None or wire.node_b is None:
                    continue
                ax, ay = wire.node_a.position
                bx, by = wire.node_b.position
                wires.append(
                    {
                        "node_a": [float(ax), float(ay)],
                        "node_b": [float(bx), float(by)],
                    }
                )
                seen_wire_ids.add(wire.id)
                continue

            if isinstance(item, NodeItem):
                node = getattr(item, "node", None)
                if node is None or node.id in seen_node_ids:
                    continue
                if self._is_node_attached_to_dipole(node):
                    continue
                nx, ny = node.position
                free_nodes.append(
                    {
                        "position": [float(nx), float(ny)],
                        "is_ground": bool(node.is_ground),
                    }
                )
                seen_node_ids.add(node.id)

        if not components and not wires and not free_nodes:
            return False

        self._clipboard_payload = {
            "components": components,
            "wires": wires,
            "nodes": free_nodes,
        }
        self._clipboard_paste_count = 0
        return True

    def cut_selection(self):
        if not self.copy_selection():
            return False
        self.delete_selection()
        return True

    def has_clipboard_content(self):
        if not self._clipboard_payload:
            return False
        return bool(
            self._clipboard_payload.get("components")
            or self._clipboard_payload.get("wires")
            or self._clipboard_payload.get("nodes")
        )

    def _clipboard_payload_bounds(self, components, wires, free_nodes):
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

    def _payload_overlaps_existing(self, min_x, min_y, max_x, max_y, margin=0.0):
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

    def _find_free_paste_offset(self, bounds, margin):
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

    def _paste_create_or_get_node(self, node_cache, x, y, is_ground=False):
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

    def _paste_component(self, component_data, offset_x, offset_y, node_cache):
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

    def paste_selection(self, target_scene_pos=None, view_rect=None):
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

        self._clipboard_paste_count += 1
        self._merge_overlaps_and_refresh()
        self._sync_free_node_items_from_model()
        return True

    def _find_free_paste_offset_in_rect(self, bounds, view_rect, margin):
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

    def drawBackground(self, painter, rect):
        """Dessine la grille de points de fond pour l'alignement"""
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        
        # Dessine uniquement les points visibles
        left = int(rect.left()) - (int(rect.left()) % self.GRID_SIZE)
        top = int(rect.top()) - (int(rect.top()) % self.GRID_SIZE)
        
        points = []
        for x in range(left, int(rect.right()), self.GRID_SIZE):
            for y in range(top, int(rect.bottom()), self.GRID_SIZE):
                points.append(QPointF(x, y))
        
        painter.drawPoints(points)

    def snap_to_grid(self, pos):
        """Arrondit une position (x, y) au point de grille le plus proche"""
        gs = self.GRID_SIZE
        x = round(pos.x() / gs) * gs
        y = round(pos.y() / gs) * gs
        return x, y
    
    def get_snapped_position(self, scene_pos):
        """
        Retourne les coordonnees aimantees (x, y)
        Priorite 1 : noeud existant
        Priorite 2 : grille
        """
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
        
        return self.snap_to_grid(scene_pos)

    def get_smart_snapped_component_position(self, component_model, proposed_pos, rotation):
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

    def mousePressEvent(self, event):
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

    def mouseMoveEvent(self, event):
        # Fil fantome
        if self._handle_wire_preview_move(event):
            return
        
        # Deplacement de groupe
        if self._handle_group_move(event):
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Gere les actions au relachement du clic gauche"""
        if event.button() != Qt.LeftButton:
            super().mouseReleaseEvent(event)
            return

        if self._handle_pointer_release(event):
            self._reset_press_state()
            return

        if self.current_tool == "wire" and self.drawing_wire:
            scene_pos = event.scenePos()
            grid_x, grid_y = self.get_snapped_position(scene_pos)
            self.finish_wire_drawing(grid_x, grid_y)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

        self._reset_press_state()

    def _compute_press_grid(self, scene_pos):
        grid_x, grid_y = self.get_snapped_position(scene_pos)
        if self.current_tool == "pointer":
            return self.snap_to_grid(scene_pos)
        return grid_x, grid_y

    def _set_press_state(self, scene_pos, grid_x, grid_y):
        self._press_scene_pos = scene_pos
        self._last_grid_pos = QPointF(grid_x, grid_y)
        self._group_move_active = False
        self._drag_started_on_item = False

    def _reset_press_state(self):
        self._drag_started_on_item = False
        self._press_scene_pos = None
        self._suppress_move_until_release = False
        if self._selection_snapshot is not None:
            for item in self._selection_snapshot:
                item.setSelected(True)
            self._selection_snapshot = None

    def _handle_pointer_press(self, event, scene_pos):
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
            self._drag_started_on_item = True
            self._suppress_move_until_release = False
            return False
        if not (event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier)):
            self.clearSelection()
            self._suppress_move_until_release = True
        return False

    def _handle_tool_press(self, event, grid_x, grid_y):
        if self.current_tool == "wire":
            self.start_wire_drawing(grid_x, grid_y)
            event.accept()
            return True
        if self.current_tool in [
            "resistor",
            "source_dc",
            "source_ac",
            "capacitor",
            "inductor",
        ]:
            self.add_component_at(self.current_tool, grid_x, grid_y)
            event.accept()
            return True
        return False

    def _handle_wire_preview_move(self, event):
        if self.current_tool != "wire" or not self.drawing_wire or not self.temp_wire_item:
            return False
        new_pos = event.scenePos()
        grid_x, grid_y = self.get_snapped_position(new_pos)
        line = self.temp_wire_item.line()
        line.setP2(QPointF(grid_x, grid_y))
        self.temp_wire_item.setLine(line)
        super().mouseMoveEvent(event)
        return True

    def _handle_group_move(self, event):
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
        for selected_item in self.selectedItems():
            if isinstance(selected_item, ComponentItem):
                selected_component_nodes.add(selected_item.component.node_a)
                selected_component_nodes.add(selected_item.component.node_b)
            elif isinstance(selected_item, WireItem):
                node_a = selected_item.wire.node_a
                node_b = selected_item.wire.node_b
                if node_a is not None:
                    selected_wire_endpoint_counts[node_a] = selected_wire_endpoint_counts.get(node_a, 0) + 1
                if node_b is not None:
                    selected_wire_endpoint_counts[node_b] = selected_wire_endpoint_counts.get(node_b, 0) + 1
            elif isinstance(selected_item, NodeItem):
                selected_free_nodes.add(selected_item.node)

        preserve_internal_nodes = set(selected_component_nodes)
        preserve_internal_nodes.update(selected_free_nodes)
        for node, count in selected_wire_endpoint_counts.items():
            if count > 1:
                preserve_internal_nodes.add(node)
        preserve_node_model_ids = {node.id for node in preserve_internal_nodes if node is not None}

        current_grid_x, current_grid_y = self.snap_to_grid(event.scenePos())
        current_grid_pos = QPointF(current_grid_x, current_grid_y)
        grid_delta = current_grid_pos - self._last_grid_pos

        if grid_delta.manhattanLength() > 0:
            if not self._group_move_active:
                self._push_undo_snapshot()
            self._group_move_active = True
            moved_wire_node_ids = set()

            # Deplace d'abord les noeuds libres selectionnes et marque-les comme deja deplaces.
            # Cela evite de deplacer deux fois le meme noeud quand son fil est aussi selectionne.
            for item in self.selectedItems():
                if isinstance(item, NodeItem):
                    item.setPos(item.pos() + grid_delta)
                    item.node.position = (item.pos().x(), item.pos().y())
                    moved_wire_node_ids.add(id(item.node))

            for item in self.selectedItems():
                if isinstance(item, ComponentItem):
                    item.setPos(item.pos() + grid_delta)
                elif isinstance(item, WireItem):
                    detach = True
                    if selected_component_nodes:
                        if item.wire.node_a in selected_component_nodes or item.wire.node_b in selected_component_nodes:
                            detach = False
                    item.apply_scene_delta(
                        grid_delta,
                        detach_shared_nodes=detach,
                        moved_node_ids=moved_wire_node_ids,
                        snap_endpoints=False,
                        preserve_node_model_ids=preserve_node_model_ids,
                    )

            self._sync_free_node_items_from_model()

            self._last_grid_pos = current_grid_pos

        event.accept()
        return True

    def _handle_pointer_release(self, event):
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

    def add_component_at(self, tool_type, x, y):
        """Cree un composant a la position donnee"""
        self._push_undo_snapshot()

        node_a = self.model.create_node(x - 30, y)
        node_b = self.model.create_node(x + 30, y)
        
        dipole = None
        d_id = self.model.get_next_dipole_id()

        # Creation du modele
        if tool_type == "resistor":
            dipole = Resistor(d_id, node_a, node_b, x, y, name=f"R{d_id}")
        elif tool_type == "source_dc":
            dipole = VoltageSourceDC(d_id, node_a, node_b, x, y, name=f"V{d_id}")
        elif tool_type == "source_ac":
            dipole = VoltageSourceAC(d_id, node_a, node_b, x, y, name=f"V{d_id}")
        elif tool_type == "capacitor":
            dipole = Capacitor(d_id, node_a, node_b, x, y, name=f"C{d_id}")
        elif tool_type == "inductor":
            dipole = Inductor(d_id, node_a, node_b, x, y, name=f"L{d_id}")

        if dipole:
            self.model.add_dipole(dipole)

            item = create_component_item(dipole)
            self.addItem(item)

    def handle_component_move(self, component_item):
        """Appelee apres la fin du deplacement d'un composant"""
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

    def _smart_connect_component_to_nearby_dipole_nodes(self, component_item):
        """Aimante et connecte un dipole deplace vers des noeuds proches ou des extremites libres"""
        component_model = component_item.component
        threshold = 15

        # Choisit la meilleure ancre vers un noeud connectable proche
        ax, ay = component_model.node_a.position
        bx, by = component_model.node_b.position
        candidate_a = self._find_nearest_external_connectable_node(component_model, ax, ay, threshold)
        candidate_b = self._find_nearest_external_connectable_node(component_model, bx, by, threshold)

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
        node_ids = {component_model.node_a.id, component_model.node_b.id}
        for item in self.items():
            if isinstance(item, WireItem):
                wire = item.wire
                if wire.node_a.id in node_ids or wire.node_b.id in node_ids:
                    item.refresh_geometry()

    def _find_nearest_external_connectable_node(self, component_model, x, y, threshold):
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

    def _is_free_wire_endpoint(self, node):
        """Retourne True quand le noeud est une extremite de fil libre"""
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

    def _snap_component_terminal_to_node(self, component_item, terminal, target_node):
        """Deplace le composant pour que la borne donnee arrive exactement sur le noeud cible"""
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

    def _reattach_component_terminal_node(self, component_model, attr_name, target_node):
        """Rattache la borne du composant au noeud cible et migre les references de fils"""
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

    def _remove_node_if_unused(self, node):
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

    def _is_node_attached_to_dipole(self, node):
        if node is None:
            return False
        connected = getattr(node, "connected_dipoles", None)
        return bool(connected)

    def _refresh_wires_for_node(self, node):
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

    def _refresh_free_node_items(self):
        # Reconstruit l'affichage des noeuds qui ne sont pas rattaches a des dipoles
        for item in list(self.items()):
            if isinstance(item, NodeItem):
                self.removeItem(item)

        for node in self.model.nodes.values():
            if self._is_node_attached_to_dipole(node):
                continue
            self.addItem(NodeItem(node))

    def _merge_overlaps_and_refresh(self):
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

    def _prune_invalid_and_duplicate_wires(self):
        """Supprime les fils invalides et les doublons"""
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

    def _sync_free_node_items_from_model(self):
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
                self.addItem(new_item)

    def preview_node_move(self, node_model, snapped_pos):
        if node_model is None:
            return
        node_model.position = (snapped_pos.x(), snapped_pos.y())
        self._refresh_wires_for_node(node_model)

    def finalize_node_move(self, node_item):
        if node_item is None or node_item.node is None:
            return
        node = node_item.node
        current_x = node_item.pos().x()
        current_y = node_item.pos().y()

        # Priorite : conserver un rattachement exact a un noeud connectable proche
        snapped_node = self._find_nearest_connectable_node_for_wire(node, current_x, current_y, 15)
        if snapped_node is not None:
            node = self._reattach_wire_node(node, snapped_node)
            x, y = node.position
        else:
            x, y = self.snap_to_grid(node_item.pos())
            node.position = (x, y)
        node_item.setPos(QPointF(x, y))
        self._merge_overlaps_and_refresh()
        self._refresh_wires_for_node(node)
        self._sync_free_node_items_from_model()

    def _find_nearest_connectable_node_for_wire(self, source_node, x, y, threshold):
        """Retourne le noeud connectable le plus proche d'un bout de fil."""
        nearest_node = None
        nearest_dist = None

        for dipole in self.model.dipoles.values():
            for node in (dipole.node_a, dipole.node_b):
                if node is None or node is source_node:
                    continue
                nx, ny = node.position
                dist = ((x - nx) ** 2 + (y - ny) ** 2) ** 0.5
                if dist > threshold:
                    continue
                if nearest_dist is None or dist < nearest_dist:
                    nearest_node = node
                    nearest_dist = dist

        for node in self.model.nodes.values():
            if node is source_node or not self._is_free_wire_endpoint(node):
                continue
            nx, ny = node.position
            dist = ((x - nx) ** 2 + (y - ny) ** 2) ** 0.5
            if dist > threshold:
                continue
            if nearest_dist is None or dist < nearest_dist:
                nearest_node = node
                nearest_dist = dist

        return nearest_node

    def get_wire_snap_position(self, source_node, x, y, threshold=15):
        """Retourne la position d'aimantation pour un bout de fil pendant le drag."""
        target_node = self._find_nearest_connectable_node_for_wire(source_node, x, y, threshold)
        if target_node is not None:
            tx, ty = target_node.position
            return QPointF(tx, ty)
        snapped_x, snapped_y = self.snap_to_grid(QPointF(x, y))
        return QPointF(snapped_x, snapped_y)

    def _reattach_wire_node(self, old_node, target_node):
        if old_node is None or target_node is None or old_node is target_node:
            return target_node

        old_node.position = target_node.position

        return self.model.merge_nodes(old_node, target_node)

    def start_wire_drawing(self, x, y):
        """Demarre le dessin interactif d'un fil"""
        self.drawing_wire = True
        self.start_pos = (x, y)
        
        # Apercu temporaire du fil
        self.temp_wire_item = QGraphicsLineItem(x, y, x, y)
        pen = QPen(Qt.gray, 2, Qt.DashLine)
        self.temp_wire_item.setPen(pen)
        self.addItem(self.temp_wire_item)

    def finish_wire_drawing(self, x, y):
        """Finalise le fil et l'ajoute au modele"""
        
        start_x, start_y = self.start_pos
        
        # Nettoie l'apercu temporaire
        self.removeItem(self.temp_wire_item)
        self.temp_wire_item = None
        self.drawing_wire = False
        
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

    def update_wires_connected_to(self, component_model, new_pos, rotation):
        """Met a jour les fils connectes pendant le deplacement d'un composant"""
        
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

    def cancel_wire_drawing(self):
        """Annule l'operation de dessin de fil en cours"""
        if self.temp_wire_item:
            self.removeItem(self.temp_wire_item)
            self.temp_wire_item = None
        self.drawing_wire = False

    def handle_wire_move(self, wire_item, record_undo=True):
        """Met a jour le modele et reinitialise le visuel apres un deplacement de fil"""
        if record_undo:
            self._push_undo_snapshot()

        # Deplace les deux extremites du fil selon le deplacement de l'item
        delta = wire_item.pos()
        if delta.manhattanLength() > 0.1:
            wire_item.setPos(0, 0)
            wire_item.apply_scene_delta(delta, detach_shared_nodes=True, snap_endpoints=False)
            wire_item.refresh_geometry()
        else:
            wire_item.refresh_geometry()

        self._merge_overlaps_and_refresh()
        self._sync_free_node_items_from_model()

    def rotate_selected_components(self, angle_degrees):
        """Tourne les dipoles selectionnes selon l'angle donne et rafraichit les fils connectes"""
        selected_components = [
            item for item in self.selectedItems() if isinstance(item, ComponentItem)
        ]
        if not selected_components:
            return False

        self._push_undo_snapshot()

        for item in selected_components:
            new_rotation = (item.rotation() + angle_degrees) % 360
            item.setRotation(new_rotation)
            item.component.rotation = float(new_rotation)
            self.update_wires_connected_to(item.component, item.pos(), new_rotation)

        return True

    def delete_selection(self):
        """Supprime tous les elements selectionnes"""
        selected = self.selectedItems()
        if not selected:
            return

        self._push_undo_snapshot()
        candidate_nodes = []

        for item in selected:
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

    def refresh_from_model(self):
        """Vide la scene et la reconstruit a partir du modele"""
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