from PyQt5.QtWidgets import QGraphicsLineItem, QGraphicsItem
from PyQt5.QtGui import QPen, QColor, QPainterPath, QPainterPathStroker
from PyQt5.QtCore import Qt, QPointF, QLineF

class WireItem(QGraphicsLineItem):
    def __init__(self, wire_model):
        super().__init__()
        self.wire = wire_model
        self._is_selected = False
        
        self.setPen(QPen(Qt.black, 2))
        self.setFlags(QGraphicsItem.ItemIsSelectable | 
                      QGraphicsItem.ItemIsMovable | 
                      QGraphicsItem.ItemSendsGeometryChanges)
        self.setZValue(0)
        
        self.refresh_geometry()

    def refresh_geometry(self):
        """Reinitialise le fil a partir des coordonnees du modele"""
        if not self.wire.node_a or not self.wire.node_b:
            return

        # Reinitialise le parent a l'origine absolue
        self.prepareGeometryChange()
        self.setPos(0, 0)

        # Coordonnees absolues
        p1 = QPointF(*self.wire.node_a.position)
        p2 = QPointF(*self.wire.node_b.position)

        # Place la ligne a ces coordonnees
        self.setLine(QLineF(p1, p2))

    def shape(self):
        """Retourne une zone de clic plus epaisse pour faciliter la selection du fil"""
        path = QPainterPath()
        path.moveTo(self.line().p1())
        path.lineTo(self.line().p2())
        stroker = QPainterPathStroker()
        stroker.setWidth(12)
        return stroker.createStroke(path)

    def _node_shared_with_dipole(self, node, model):
        """Retourne True si le noeud est reference par un dipole"""
        if node is None:
            return False
        for dipole in model.dipoles.values():
            if dipole.node_a is node or dipole.node_b is node:
                return True
        return False

    def _wire_count_for_node(self, node, model):
        if node is None:
            return 0
        count = 0
        for wire in model.wires.values():
            if wire.node_a is node or wire.node_b is node:
                count += 1
        return count

    def _endpoint_is_shared(self, node, model):
        if node is None:
            return False
        if self._node_shared_with_dipole(node, model):
            return True
        return self._wire_count_for_node(node, model) > 1

    def apply_scene_delta(self, delta, detach_shared_nodes=False, moved_node_ids=None, snap_endpoints=True):
        """Deplace un fil via ses noeuds avec aimantation optionnelle des extremites"""
        scene = self.scene()
        if scene is None:
            return
        model = scene.model
        if model is None:
            return
        if not self.wire.node_a or not self.wire.node_b:
            return


        shared_a = self._endpoint_is_shared(self.wire.node_a, model)
        shared_b = self._endpoint_is_shared(self.wire.node_b, model)

        if detach_shared_nodes:
            if shared_a:
                ax, ay = self.wire.node_a.position
                self.wire.node_a = model.create_node(ax, ay)
                shared_a = False
            if shared_b:
                bx, by = self.wire.node_b.position
                self.wire.node_b = model.create_node(bx, by)
                shared_b = False

        ax, ay = self.wire.node_a.position
        bx, by = self.wire.node_b.position

        if moved_node_ids is None:
            moved_node_ids = set()

        # Si les noeuds ont ete detaches, les extremites peuvent s'aimanter independamment
        # Sinon les extremites attachees doivent etre pilotees par les dipoles deplaces
        should_snap_endpoints = detach_shared_nodes and snap_endpoints

        node_a_id = id(self.wire.node_a)
        if node_a_id not in moved_node_ids:
            if shared_a and not detach_shared_nodes:
                # Conserve l'attache : le dipole selectionne met a jour ce noeud
                moved_node_ids.add(node_a_id)
            else:
                ax += delta.x()
                ay += delta.y()
                if should_snap_endpoints:
                    snapped_a = scene.get_snapped_position(QPointF(ax, ay))
                    self.wire.node_a.position = (snapped_a[0], snapped_a[1])
                else:
                    self.wire.node_a.position = (ax, ay)
                moved_node_ids.add(node_a_id)

        node_b_id = id(self.wire.node_b)
        if node_b_id not in moved_node_ids:
            if shared_b and not detach_shared_nodes:
                # Conserve l'attache : le dipole selectionne met a jour ce noeud
                moved_node_ids.add(node_b_id)
            else:
                bx += delta.x()
                by += delta.y()
                if should_snap_endpoints:
                    snapped_b = scene.get_snapped_position(QPointF(bx, by))
                    self.wire.node_b.position = (snapped_b[0], snapped_b[1])
                else:
                    self.wire.node_b.position = (bx, by)
                moved_node_ids.add(node_b_id)

        self.refresh_geometry()

        if hasattr(scene, "_sync_free_node_items_from_model"):
            scene._sync_free_node_items_from_model()


    def itemChange(self, change, value):
        # Aimantation de position
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            new_pos = value
            grid_size = self.scene().GRID_SIZE
            x = round(new_pos.x() / grid_size) * grid_size
            y = round(new_pos.y() / grid_size) * grid_size
            return QPointF(x, y)

        # Visuels de selection
        if change == QGraphicsItem.ItemSelectedChange:
            is_selected = bool(value)
            self._is_selected = is_selected
            pen = self.pen()
            if is_selected:
                pen.setColor(QColor("#0078d7"))
                pen.setStyle(Qt.DashLine)
                self.setZValue(1)
            else:
                pen.setColor(Qt.black)
                pen.setStyle(Qt.SolidLine)
                self.setZValue(0)
            self.setPen(pen)
            if self.scene() is not None:
                self.scene()._refresh_wires_for_node(self.wire.node_a)
                self.scene()._refresh_wires_for_node(self.wire.node_b)

        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event):
        """Finalise le glisser d'un fil entier"""
        super().mouseReleaseEvent(event)
        
        # Si le fil entier a ete deplace
        if self.pos().manhattanLength() > 0.1:
             if self.scene():
                 self.scene().handle_wire_move(self)