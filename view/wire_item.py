from PyQt5.QtCore import QLineF, QPointF, Qt
from PyQt5.QtGui import QColor, QPainterPath, QPainterPathStroker, QPen
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsLineItem

class WireItem(QGraphicsLineItem):
    """Element graphique representant un fil."""

    def __init__(self, wire_model) -> None:
        """Initialise le fil graphique a partir du modele."""
        super().__init__()
        self.wire = wire_model
        self._is_selected = False
        self._locked = False
        
        self.setPen(QPen(Qt.black, 2))
        self.setFlags(QGraphicsItem.ItemIsSelectable | 
                      QGraphicsItem.ItemIsMovable | 
                      QGraphicsItem.ItemSendsGeometryChanges)
        self.setZValue(0)
        
        self.refresh_geometry()

    def refresh_geometry(self) -> None:
        """Reinitialise le fil a partir des coordonnees du modele."""
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

    def shape(self) -> QPainterPath:
        """Retourne une zone de clic plus epaisse pour faciliter la selection."""
        path = QPainterPath()
        path.moveTo(self.line().p1())
        path.lineTo(self.line().p2())
        stroker = QPainterPathStroker()
        stroker.setWidth(12)
        return stroker.createStroke(path)

    def _node_shared_with_dipole(self, node, model) -> bool:
        """Indique si le noeud est reference par un dipole."""
        if node is None:
            return False
        for dipole in model.dipoles.values():
            if dipole.node_a is node or dipole.node_b is node:
                return True
        return False

    def _wire_count_for_node(self, node, model) -> int:
        """Compte le nombre de fils rattaches au noeud."""
        if node is None:
            return 0
        count = 0
        for wire in model.wires.values():
            if wire.node_a is node or wire.node_b is node:
                count += 1
        return count

    def _endpoint_is_shared(self, node, model) -> bool:
        """Indique si l'extremite est partagee par plusieurs elements."""
        if node is None:
            return False
        if self._node_shared_with_dipole(node, model):
            return True
        return self._wire_count_for_node(node, model) > 1

    def _move_node_endpoint(
        self,
        node,
        delta: QPointF,
        scene,
        should_snap: bool,
    ) -> None:
        """Deplace un noeud et applique l'aimantation si demandee."""
        if node is None:
            return
        x_pos, y_pos = node.position
        x_pos += delta.x()
        y_pos += delta.y()
        if should_snap:
            snapped = scene.get_snapped_position(QPointF(x_pos, y_pos))
            node.position = (snapped[0], snapped[1])
        else:
            node.position = (x_pos, y_pos)

    def apply_scene_delta(
        self,
        delta: QPointF,
        detach_shared_nodes: bool = False,
        moved_node_ids: Optional[set[int]] = None,
        snap_endpoints: bool = True,
        preserve_node_model_ids: Optional[set[int]] = None,
    ) -> None:
        """Deplace un fil via ses noeuds avec aimantation optionnelle des extremites."""
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

        ax, ay = self.wire.node_a.position
        bx, by = self.wire.node_b.position

        moved_node_ids = moved_node_ids or set()
        preserve_node_model_ids = preserve_node_model_ids or set()

        preserve_a_internal = self.wire.node_a.id in preserve_node_model_ids
        preserve_b_internal = self.wire.node_b.id in preserve_node_model_ids

        # Si les noeuds ont ete detaches, les extremites peuvent s'aimanter independamment.
        # Sinon seules les bornes partagees avec des dipoles restent pilotees par les dipoles deplaces.
        should_snap_endpoints = detach_shared_nodes and snap_endpoints
        preserve_a_with_dipole = (not detach_shared_nodes) and self._node_shared_with_dipole(self.wire.node_a, model)
        preserve_b_with_dipole = (not detach_shared_nodes) and self._node_shared_with_dipole(self.wire.node_b, model)

        if detach_shared_nodes:
            if shared_a and not preserve_a_internal:
                ax, ay = self.wire.node_a.position
                self.wire.node_a = model.create_node(ax, ay)
                shared_a = False
            if shared_b and not preserve_b_internal:
                bx, by = self.wire.node_b.position
                self.wire.node_b = model.create_node(bx, by)
                shared_b = False

        node_a_id = id(self.wire.node_a)
        if node_a_id not in moved_node_ids:
            if preserve_a_with_dipole:
                # Conserve l'attache : le dipole selectionne met a jour ce noeud.
                moved_node_ids.add(node_a_id)
            else:
                self._move_node_endpoint(self.wire.node_a, delta, scene, should_snap_endpoints)
                moved_node_ids.add(node_a_id)

        node_b_id = id(self.wire.node_b)
        if node_b_id not in moved_node_ids:
            if preserve_b_with_dipole:
                # Conserve l'attache : le dipole selectionne met a jour ce noeud.
                moved_node_ids.add(node_b_id)
            else:
                self._move_node_endpoint(self.wire.node_b, delta, scene, should_snap_endpoints)
                moved_node_ids.add(node_b_id)

        self.refresh_geometry()

        if hasattr(scene, "_sync_free_node_items_from_model"):
            scene._sync_free_node_items_from_model()


    def itemChange(self, change, value):
        """Gere l'aimantation et les visuels de selection du fil."""
        # Aimantation de position
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            if self._locked:
                return self.pos()
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

    def set_locked(self, locked: bool) -> None:
        """Verrouille ou deverrouille le fil."""
        self._locked = bool(locked)
        self.setFlag(QGraphicsItem.ItemIsMovable, not self._locked)

    def is_locked(self) -> bool:
        """Indique si le fil est verrouille."""
        return self._locked

    def mouseReleaseEvent(self, event) -> None:
        """Finalise le glisser d'un fil entier."""
        super().mouseReleaseEvent(event)
        
        # Si le fil entier a ete deplace
        if self.pos().manhattanLength() > 0.1:
             if self.scene():
                 self.scene().handle_wire_move(self)