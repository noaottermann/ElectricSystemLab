import math

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QApplication, QGraphicsItem, QStyle

from model.components import Capacitor, Inductor, Resistor, VoltageSourceAC, VoltageSourceDC

class ComponentItem(QGraphicsItem):
    """Element graphique de base pour tous les dipoles"""

    WIDTH = 60
    HEIGHT = 40
    TERMINAL_OFFSET = 30

    def __init__(self, component_model) -> None:
        """Initialise l'item graphique associe au composant."""
        super().__init__()
        self.component = component_model

        self._press_scene_pos = None
        self._drag_started = False
        self._is_rotating = False
        self._rotate_start_angle = 0.0
        self._rotate_start_rotation = 0.0
        self._locked = False
        
        # Reglages d'interaction
        self.setFlags(
            QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        # Les dipoles (et donc leurs bornes colorees) doivent rester au-dessus des fils.
        self.setZValue(2)
        
        # Position et rotation initiales
        x, y = self.component.position
        self.setPos(x, y)
        self.setRotation(self.component.rotation)

        # Dimensions standard
        self.width = self.WIDTH
        self.height = self.HEIGHT
        
        # Infobulle
        self.setToolTip(f"{self.component.name} (ID: {self.component.id})")

    def boundingRect(self) -> QRectF:
        """Definit la zone rectangulaire interactive du composant."""
        margin = 5
        return QRectF(
            -self.width / 2 - margin,
            -self.height / 2 - margin,
            self.width + 2 * margin,
            self.height + 2 * margin,
        )

    def shape(self) -> QPainterPath:
        """Utilise une forme plus serree pour eviter de selectionner l'item dans le vide."""
        path = QPainterPath()
        path.addRect(QRectF(-self.width / 2, -self.height / 2, self.width, self.height))
        return path

    def itemChange(self, change, value):
        """Gere les effets de la scene lors des changements de position."""
        # Aimantation
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            if self._locked:
                return self.pos()
            scene = self.scene()
            new_pos = value
            grid_size = scene.GRID_SIZE
            x = round(new_pos.x() / grid_size) * grid_size
            y = round(new_pos.y() / grid_size) * grid_size  
            snapped_pos = QPointF(x, y)

            if hasattr(scene, "get_smart_snapped_component_position"):
                snapped_pos = scene.get_smart_snapped_component_position(
                    self.component,
                    snapped_pos,
                    self.rotation(),
                )

            scene.update_wires_connected_to(self.component, snapped_pos, self.rotation())
            return snapped_pos

        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event) -> None:
        """Finalise les deplacements et rotations du composant."""
        if self._is_rotating and event.button() == Qt.RightButton:
            self._is_rotating = False
            if self.scene():
                self.scene().handle_component_move(self)
            event.accept()
            return
        super().mouseReleaseEvent(event)

        self._drag_started = False
        self._press_scene_pos = None
        
        # Demande a la scene de mettre a jour les connexions
        if self.scene():
            self.scene().handle_component_move(self)

    def mousePressEvent(self, event) -> None:
        """Prepare un glisser ou une rotation selon le bouton."""
        if self._locked:
            # Autorise la selection mais bloque les interactions de deplacement/rotation.
            if event.button() == Qt.RightButton:
                event.ignore()
                return
            super().mousePressEvent(event)
            return
        if event.button() == Qt.RightButton:
            center = self.mapToScene(QPointF(0, 0))
            dx = event.scenePos().x() - center.x()
            dy = event.scenePos().y() - center.y()
            self._rotate_start_angle = math.degrees(math.atan2(dy, dx))
            self._rotate_start_rotation = self.rotation()
            self._is_rotating = True
            if self.scene() and hasattr(self.scene(), "_push_undo_snapshot"):
                self.scene()._push_undo_snapshot()
            event.accept()
            return
        self._press_scene_pos = event.scenePos()
        self._drag_started = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Met a jour la rotation ou le glisser en cours."""
        if self._is_rotating:
            current_angle = self._compute_rotation_angle(event.scenePos())
            delta = current_angle - self._rotate_start_angle
            new_rotation = (self._rotate_start_rotation + delta) % 360
            self.setRotation(new_rotation)
            self.component.rotation = float(new_rotation)
            if self.scene():
                self.scene().update_wires_connected_to(self.component, self.pos(), new_rotation)
            event.accept()
            return
        if not self._drag_started and self._press_scene_pos is not None:
            drag_distance = (event.scenePos() - self._press_scene_pos).manhattanLength()
            if drag_distance < QApplication.startDragDistance():
                event.ignore()
                return
            self._drag_started = True

        super().mouseMoveEvent(event)

    def update_model_nodes(self) -> None:
        """Recalcule les positions des noeuds a partir du centre et de la rotation."""
        center_x, center_y = self.pos().x(), self.pos().y()
        delta_x, delta_y = self._terminal_offset_from_rotation(self.rotation())

        # Calcul trigonometrie pour placer les bornes a distance fixe du centre.
        self.component.node_a.position = (center_x - delta_x, center_y - delta_y)
        self.component.node_b.position = (center_x + delta_x, center_y + delta_y)
        self.component.position = (center_x, center_y)

    def _compute_rotation_angle(self, scene_pos: QPointF) -> float:
        """Calcule l'angle de rotation en degres depuis le centre."""
        center = self.mapToScene(QPointF(0, 0))
        delta_x = scene_pos.x() - center.x()
        delta_y = scene_pos.y() - center.y()
        return math.degrees(math.atan2(delta_y, delta_x))

    def _terminal_offset_from_rotation(self, rotation_degrees: float) -> tuple[float, float]:
        """Retourne le decalage (dx, dy) des bornes pour une rotation."""
        radians = math.radians(rotation_degrees)
        delta_x = self.TERMINAL_OFFSET * math.cos(radians)
        delta_y = self.TERMINAL_OFFSET * math.sin(radians)
        return delta_x, delta_y

    def set_locked(self, locked: bool) -> None:
        """Verrouille ou deverrouille l'item graphique."""
        self._locked = bool(locked)

    def is_locked(self) -> bool:
        """Indique si l'item est verrouille."""
        return self._locked

    def paint(self, painter, option, widget=None) -> None:
        """Dessine les limites de selection et le symbole specifique."""
        painter.setRenderHint(QPainter.Antialiasing)
        is_selected = option.state & QStyle.State_Selected
        if is_selected:
            pen = QPen(Qt.DashLine)
            pen.setColor(QColor("#0078d7"))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(self.boundingRect())
        self.draw_symbol(painter)
        painter.setPen(Qt.NoPen)
        painter.setBrush(Qt.red)
        painter.drawEllipse(QPointF(-30, 0), 2, 2)
        painter.setBrush(Qt.black)
        painter.drawEllipse(QPointF(30, 0), 2, 2)


    def draw_labels(self, painter: QPainter) -> None:
        """Dessine le nom et la valeur principale."""
        painter.setPen(QColor("black"))
        font = QFont("Arial", 8)
        painter.setFont(font)

        name_rect = QRectF(-30, -35, 60, 15)
        painter.drawText(name_rect, Qt.AlignCenter, self.component.name)
        
        value_text = self.get_value_text()
        val_rect = QRectF(-30, 20, 60, 15)
        painter.drawText(val_rect, Qt.AlignCenter, value_text)

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole du composant (a surcharger)."""
        pass

    def get_value_text(self) -> str:
        """Retourne la valeur affichee pour l'item."""
        return ""

    # Dessin des symboles

class ResistorItem(ComponentItem):
    """Item graphique pour une resistance."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole de la resistance."""
        pen = QPen(QColor("black"), 2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        # Style europeen (rectangle)
        # Lignes de connexion
        painter.drawLine(-30, 0, -15, 0)  # Gauche
        painter.drawLine(15, 0, 30, 0)    # Droite
        
        # Corps (rectangle)
        rect = QRectF(-15, -8, 30, 16)
        painter.drawRect(rect)
    
    def get_value_text(self) -> str:
        """Retourne la valeur de resistance a afficher."""
        if hasattr(self.component, "resistance"):
            return f"{self.component.resistance} "
        return ""

class VoltageSourceItem(ComponentItem):
    """Item graphique pour les sources de tension."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole de la source de tension."""
        pen = QPen(Qt.black, 2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        # Lignes
        painter.drawLine(-30, 0, -15, 0)
        painter.drawLine(15, 0, 30, 0)
        
        # Cercle
        painter.drawEllipse(QPointF(0, 0), 15, 15)
        
        # Symboles +/- ou ~
        painter.setPen(QPen(Qt.black, 1.5))
        
        if isinstance(self.component, VoltageSourceDC):
            painter.drawLine(-10, 0, -4, 0)
            painter.drawLine(-7, -3, -7, 3)
            
            painter.drawLine(4, 0, 10, 0)
        elif isinstance(self.component, VoltageSourceAC):
            # Tilde (~)
            path = QPainterPath()
            path.moveTo(-7, 2)
            path.cubicTo(-2, -5, 2, 5, 7, -2)
            painter.drawPath(path)

    def get_value_text(self) -> str:
        """Retourne la valeur de tension a afficher."""
        if isinstance(self.component, VoltageSourceDC):
            return f"{self.component.dc_voltage} V"
        elif isinstance(self.component, VoltageSourceAC):
            return f"{self.component.amplitude} V"
        return ""

class CapacitorItem(ComponentItem):
    """Item graphique pour un condensateur."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole du condensateur."""
        pen = QPen(Qt.black, 2)
        painter.setPen(pen)
        
        # Lignes
        painter.drawLine(-30, 0, -5, 0)
        painter.drawLine(5, 0, 30, 0)
        
        # Plaques verticales
        painter.drawLine(-5, -12, -5, 12)
        painter.drawLine(5, -12, 5, 12)

    def get_value_text(self) -> str:
        """Retourne la valeur de capacite a afficher."""
        return f"{self.component.capacitance} F"

class InductorItem(ComponentItem):
    """Item graphique pour une inductance."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole de l'inductance."""
        pen = QPen(Qt.black, 2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        
        # Lignes
        painter.drawLine(-30, 0, -15, 0)
        painter.drawLine(15, 0, 30, 0)
        
        # Arcs
        painter.drawArc(-15, -5, 10, 10, 0, 180 * 16)
        painter.drawArc(-5, -5, 10, 10, 0, 180 * 16)
        painter.drawArc(5, -5, 10, 10, 0, 180 * 16)

    def get_value_text(self) -> str:
        """Retourne la valeur d'inductance a afficher."""
        return f"{self.component.inductance} H"

def create_component_item(component_model) -> ComponentItem:
    """Retourne l'element graphique adapte a un objet modele."""
    if isinstance(component_model, Resistor):
        return ResistorItem(component_model)
    elif isinstance(component_model, (VoltageSourceDC, VoltageSourceAC)):
        return VoltageSourceItem(component_model)
    elif isinstance(component_model, Capacitor):
        return CapacitorItem(component_model)
    elif isinstance(component_model, Inductor):
        return InductorItem(component_model)
    else:
        # Repli pour les composants inconnus
        return ComponentItem(component_model)