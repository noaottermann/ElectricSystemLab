from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QApplication, QGraphicsEllipseItem, QGraphicsItem


class NodeItem(QGraphicsEllipseItem):
    """Élement graphique représentant un noeud libre"""

    RADIUS = 2
    HIT_RADIUS = 8

    def __init__(self, node_model) -> None:
        """Initialise l'item graphique associé au noeud."""
        super().__init__(-self.RADIUS, -self.RADIUS, self.RADIUS * 2, self.RADIUS * 2)
        self.node = node_model
        self._drag_active = False
        self._drag_started = False
        self._undo_snapshot_taken = False
        self._drag_offset = QPointF(0, 0)
        self._locked = False
        self._snap_candidate = False
        self._select_wire_on_release = False
        self._wire_item_on_click = None
        self._press_scene_pos = None

        self.setFlags(
            QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setZValue(3)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.OpenHandCursor)
        self.setPen(QPen(Qt.NoPen))
        self.setBrush(QBrush(QColor(Qt.black)))
        self.setToolTip(f"Noeud {self.node.id}")

        x, y = self.node.position
        self.setPos(x, y)

    def boundingRect(self) -> QRectF:
        """Retourne la zone interactive plus large que le cercle."""
        return QRectF(
            -self.HIT_RADIUS,
            -self.HIT_RADIUS,
            self.HIT_RADIUS * 2,
            self.HIT_RADIUS * 2,
        )

    def shape(self) -> QPainterPath:
        """Définit une zone de clic autour du noeud."""
        path = QPainterPath()
        path.addEllipse(QPointF(0, 0), self.HIT_RADIUS, self.HIT_RADIUS)
        return path

    def paint(self, painter, option, widget=None) -> None:
        """Dessine le noeud sans marqueur de sélection par défaut."""
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        painter.drawEllipse(self.rect())

    def set_snap_candidate(self, is_candidate: bool) -> None:
        """Marque le noeud comme candidat à l'aimantation."""
        self._snap_candidate = bool(is_candidate)
        if self._snap_candidate:
            self.setBrush(QBrush(QColor(0, 200, 100)))
        else:
            if self.brush().color() == QColor("#0078d7"):
                return
            self.setBrush(QBrush(QColor(Qt.black)))

    def mousePressEvent(self, event) -> None:
        """Démarre un glisser du noeud."""
        if event.button() == Qt.LeftButton:
            if self._locked:
                event.ignore()
                return
            scene = self.scene()
            self._wire_item_on_click = None
            self._select_wire_on_release = False
            self._press_scene_pos = event.scenePos()
            self._drag_started = False
            if scene is not None:
                # Si le noeud est une extremité de fil, sélectionne le fil au clic (après release).
                model = getattr(scene, "model", None)
                if model is not None and getattr(model, "wires", None):
                    for wire in model.wires.values():
                        if wire.node_a is self.node or wire.node_b is self.node:
                            for item in scene.items():
                                if hasattr(item, "wire") and getattr(item, "wire", None) is wire:
                                    self._wire_item_on_click = item
                                    self._select_wire_on_release = True
                                    break
                        if self._wire_item_on_click is not None:
                            break
            self._drag_active = True
            self._undo_snapshot_taken = False
            self.setCursor(Qt.ClosedHandCursor)
            self._drag_offset = self.pos() - event.scenePos()
            if scene is not None:
                # Ensure model is aligned before dragging to avoid snapping back.
                self.node.position = (self.pos().x(), self.pos().y())
                if hasattr(scene, "_refresh_wires_for_node"):
                    scene._refresh_wires_for_node(self.node)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """Finalise un glisser de noeud."""
        if event.button() == Qt.LeftButton:
            self._drag_active = False
            self._undo_snapshot_taken = False
            scene = self.scene()
            if self._select_wire_on_release and not self._drag_started and self._wire_item_on_click is not None:
                if scene is not None and not (event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier)):
                    scene.clearSelection()
                self._wire_item_on_click.setSelected(True)
                self._select_wire_on_release = False
                self._wire_item_on_click = None
                self._press_scene_pos = None
                self._drag_started = False
                if scene is not None and getattr(scene, "current_tool", "pointer") != "pointer":
                    self.setCursor(Qt.CrossCursor)
                else:
                    self.setCursor(Qt.OpenHandCursor)
                event.accept()
                return
            if scene is not None and getattr(scene, "current_tool", "pointer") != "pointer":
                self.setCursor(Qt.CrossCursor)
            else:
                self.setCursor(Qt.OpenHandCursor)
            scene = self.scene()
            if scene and hasattr(scene, "finalize_node_move"):
                scene.finalize_node_move(self)
            self._select_wire_on_release = False
            self._wire_item_on_click = None
            self._press_scene_pos = None
            self._drag_started = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Met à jour la position du noeud pendant le glisser."""
        if self._drag_active:
            scene = self.scene()
            if scene is None:
                return
            if self._press_scene_pos is not None and not self._drag_started:
                drag_distance = (event.scenePos() - self._press_scene_pos).manhattanLength()
                if drag_distance >= QApplication.startDragDistance():
                    self._drag_started = True
                    self._select_wire_on_release = False
            target_pos = event.scenePos() + self._drag_offset
            if hasattr(scene, "get_wire_snap_position"):
                snapped = scene.get_wire_snap_position(
                    self.node, target_pos.x(), target_pos.y()
                )
            else:
                x, y = scene.snap_to_grid(target_pos)
                snapped = QPointF(x, y)

            if not self._undo_snapshot_taken and self.pos() != snapped:
                if hasattr(scene, "_push_undo_snapshot"):
                    scene._push_undo_snapshot()
                self._undo_snapshot_taken = True

            self.setPos(snapped)
            if hasattr(scene, "preview_node_move"):
                scene.preview_node_move(self.node, snapped)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def hoverEnterEvent(self, event) -> None:
        """Met à jour le curseur selon l'outil actif."""
        scene = self.scene()
        if scene is not None and getattr(scene, "current_tool", "pointer") != "pointer":
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.OpenHandCursor)
        super().hoverEnterEvent(event)

    def hoverMoveEvent(self, event) -> None:
        """Met à jour le curseur lors du survol."""
        scene = self.scene()
        if scene is not None and getattr(scene, "current_tool", "pointer") != "pointer":
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.OpenHandCursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        """Restaure le curseur lors de la sortie de survol."""
        scene = self.scene()
        if scene is not None and getattr(scene, "current_tool", "pointer") != "pointer":
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.OpenHandCursor)
        super().hoverLeaveEvent(event)


