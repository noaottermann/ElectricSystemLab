from PyQt5.QtWidgets import QGraphicsEllipseItem, QGraphicsItem
from PyQt5.QtGui import QPen, QBrush, QColor, QPainterPath
from PyQt5.QtCore import Qt, QPointF, QRectF


class NodeItem(QGraphicsEllipseItem):
    """Element graphique representant un noeud libre"""

    RADIUS = 2
    HIT_RADIUS = 8

    def __init__(self, node_model):
        super().__init__(-self.RADIUS, -self.RADIUS, self.RADIUS * 2, self.RADIUS * 2)
        self.node = node_model
        self._drag_active = False
        self._undo_snapshot_taken = False
        self._drag_offset = QPointF(0, 0)
        self._locked = False

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

    def boundingRect(self):
        return QRectF(
            -self.HIT_RADIUS,
            -self.HIT_RADIUS,
            self.HIT_RADIUS * 2,
            self.HIT_RADIUS * 2,
        )

    def shape(self):
        path = QPainterPath()
        path.addEllipse(QPointF(0, 0), self.HIT_RADIUS, self.HIT_RADIUS)
        return path

    def paint(self, painter, option, widget=None):
        # Keep node selection behavior without the default square selection marker.
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        painter.drawEllipse(self.rect())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._locked:
                event.ignore()
                return
            self._drag_active = True
            self._undo_snapshot_taken = False
            self.setCursor(Qt.ClosedHandCursor)
            self._drag_offset = self.pos() - event.scenePos()
            scene = self.scene()
            if scene is not None:
                # Ensure model is aligned before dragging to avoid snapping back.
                self.node.position = (self.pos().x(), self.pos().y())
                if hasattr(scene, "_refresh_wires_for_node"):
                    scene._refresh_wires_for_node(self.node)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_active = False
            self._undo_snapshot_taken = False
            scene = self.scene()
            if scene is not None and getattr(scene, "current_tool", "pointer") != "pointer":
                self.setCursor(Qt.CrossCursor)
            else:
                self.setCursor(Qt.OpenHandCursor)
            scene = self.scene()
            if scene and hasattr(scene, "finalize_node_move"):
                scene.finalize_node_move(self)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_active:
            scene = self.scene()
            if scene is None:
                return
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

    def hoverEnterEvent(self, event):
        scene = self.scene()
        if scene is not None and getattr(scene, "current_tool", "pointer") != "pointer":
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.OpenHandCursor)
        super().hoverEnterEvent(event)

    def hoverMoveEvent(self, event):
        scene = self.scene()
        if scene is not None and getattr(scene, "current_tool", "pointer") != "pointer":
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.OpenHandCursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        scene = self.scene()
        if scene is not None and getattr(scene, "current_tool", "pointer") != "pointer":
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.OpenHandCursor)
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        # La position est deja geree par le flux de drag (mouseMoveEvent/finalize_node_move).
        # Evite un re-snapping implicite a la grille qui peut decaler un noeud connecte
        # a une borne de dipole hors grille.
        return super().itemChange(change, value)

    def set_locked(self, locked):
        self._locked = bool(locked)

    def is_locked(self):
        return self._locked
