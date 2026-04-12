import math

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QApplication, QGraphicsItem, QStyle

from model.components import (
    Capacitor,
    CurrentControlledCurrentSource,
    CurrentSourceAC,
    CurrentSourceDC,
    Diode,
    Inductor,
    LED,
    Resistor,
    VoltageControlledCurrentSource,
    VoltageSourceAC,
    VoltageSourceDC,
)

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
            snapped_pos = new_pos
            if getattr(scene, "snap_enabled", True):
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
        self._draw_voltage_indicator(painter)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#1f2937"))
        painter.drawEllipse(QPointF(-30, 0), 2, 2)
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

    def _draw_voltage_indicator(self, painter: QPainter) -> None:
        """Dessine la fleche de tension au-dessus du dipole."""
        scene = self.scene()
        if scene is None or not getattr(scene, "show_voltage_arrows", False):
            return
        voltage = float(getattr(self.component, "voltage", 0.0))
        arrow_length = 26
        arrow_offset = -self.height / 2 - 8
        start_x = -arrow_length / 2
        end_x = arrow_length / 2
        if voltage < 0:
            start_x, end_x = end_x, start_x
        painter.save()
        painter.setPen(QPen(QColor("#2a2a2a"), 1.4))
        painter.setBrush(Qt.NoBrush)
        painter.drawLine(QPointF(start_x, arrow_offset), QPointF(end_x, arrow_offset))
        head_size = 4
        head_dir = 1 if end_x >= start_x else -1
        painter.drawLine(
            QPointF(end_x, arrow_offset),
            QPointF(end_x - head_dir * head_size, arrow_offset - head_size),
        )
        painter.drawLine(
            QPointF(end_x, arrow_offset),
            QPointF(end_x - head_dir * head_size, arrow_offset + head_size),
        )
        font = QFont("Arial", 7)
        painter.setFont(font)
        text = f"{voltage:.3g} V"
        text_rect = QRectF(-30, arrow_offset - 12, 60, 10)
        painter.drawText(text_rect, Qt.AlignCenter, text)
        painter.restore()

    def get_value_text(self) -> str:
        """Retourne la valeur affichee pour l'item."""
        return ""

    @staticmethod
    def _pen(width: float = 2.0) -> QPen:
        pen = QPen(QColor("#181818"), width)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        return pen

    @staticmethod
    def _pen_light(width: float = 1.4) -> QPen:
        pen = QPen(QColor("#181818"), width)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        return pen

    # Dessin des symboles

class ResistorItem(ComponentItem):
    """Item graphique pour une resistance."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole de la resistance."""
        painter.setPen(self._pen())
        painter.setBrush(Qt.NoBrush)

        # Style europeen (rectangle)
        # Lignes de connexion
        painter.drawLine(-30, 0, -15, 0)
        painter.drawLine(15, 0, 30, 0)
        
        # Corps (rectangle)
        rect = QRectF(-15, -7, 30, 14)
        painter.drawRoundedRect(rect, 3, 3)
    
    def get_value_text(self) -> str:
        """Retourne la valeur de resistance a afficher."""
        if hasattr(self.component, "resistance"):
            return f"{self.component.resistance} Ohm"
        return ""

class VoltageSourceItem(ComponentItem):
    """Item graphique pour les sources de tension."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole de la source de tension."""
        painter.setPen(self._pen())
        painter.setBrush(Qt.NoBrush)

        # Lignes
        painter.drawLine(-30, 0, -15, 0)
        painter.drawLine(15, 0, 30, 0)
        
        # Cercle
        painter.drawEllipse(QPointF(0, 0), 15, 15)
        
        # Symboles +/- ou ~
        painter.setPen(self._pen_light())
        
        if isinstance(self.component, VoltageSourceDC):
            painter.drawLine(-10, 0, -4, 0)
            painter.drawLine(-7, -3, -7, 3)
            painter.drawLine(4, 0, 10, 0)
        elif isinstance(self.component, VoltageSourceAC):
            # Sinusoidal curve
            path = QPainterPath()
            path.moveTo(-8, 0)
            path.cubicTo(-3, -14, 3, 14, 8, 0)
            painter.drawPath(path)

    def get_value_text(self) -> str:
        """Retourne la valeur de tension a afficher."""
        if isinstance(self.component, VoltageSourceDC):
            return f"{self.component.dc_voltage} V"
        elif isinstance(self.component, VoltageSourceAC):
            return f"{self.component.amplitude} V"
        return ""


class CurrentSourceItem(ComponentItem):
    """Item graphique pour les sources de courant."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole de la source de courant."""
        painter.setPen(self._pen())
        painter.setBrush(Qt.NoBrush)

        painter.drawLine(-30, 0, -15, 0)
        painter.drawLine(15, 0, 30, 0)
        painter.drawEllipse(QPointF(0, 0), 15, 15)

        painter.setPen(self._pen_light())
        if isinstance(self.component, CurrentSourceDC):
            painter.drawLine(-6, 0, 6, 0)
            painter.drawLine(6, 0, 2, -3)
            painter.drawLine(6, 0, 2, 3)
        elif isinstance(self.component, CurrentSourceAC):
            painter.drawLine(-6, 6, 6, 6)
            painter.drawLine(6, 6, 2, 3)
            painter.drawLine(6, 6, 2, 9)
            path = QPainterPath()
            path.moveTo(-8, -5)
            path.cubicTo(-3, -19, 3, 9, 8, -5)
            painter.drawPath(path)

    def get_value_text(self) -> str:
        """Retourne la valeur de courant a afficher."""
        if isinstance(self.component, CurrentSourceDC):
            return f"{self.component.dc_current} A"
        if isinstance(self.component, CurrentSourceAC):
            return f"{self.component.amplitude} A"
        return ""


class DependentCurrentSourceItem(ComponentItem):
    """Item graphique pour les sources de courant dependantes."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole d'une source dependante."""
        painter.setPen(self._pen())
        painter.setBrush(Qt.NoBrush)

        painter.drawLine(-30, 0, -16, 0)
        painter.drawLine(16, 0, 30, 0)

        diamond = QPainterPath()
        diamond.moveTo(0, -16)
        diamond.lineTo(16, 0)
        diamond.lineTo(0, 16)
        diamond.lineTo(-16, 0)
        diamond.closeSubpath()
        painter.drawPath(diamond)

        painter.setPen(self._pen_light())
        if isinstance(self.component, VoltageControlledCurrentSource):
            painter.drawLine(-10, 0, -4, 0)
            painter.drawLine(-7, -3, -7, 3)
            painter.drawLine(4, 0, 10, 0)
        else:
            painter.drawLine(-6, 0, 6, 0)
            painter.drawLine(6, 0, 2, -3)
            painter.drawLine(6, 0, 2, 3)

    def get_value_text(self) -> str:
        """Retourne la valeur de gain a afficher."""
        if isinstance(self.component, VoltageControlledCurrentSource):
            return f"{self.component.transconductance} S"
        if isinstance(self.component, CurrentControlledCurrentSource):
            return f"{self.component.gain} A/A"
        return ""

class CapacitorItem(ComponentItem):
    """Item graphique pour un condensateur."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole du condensateur."""
        painter.setPen(self._pen())
        
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
        painter.setPen(self._pen())
        painter.setBrush(Qt.NoBrush)
        
        # Lignes
        painter.drawLine(-30, 0, -18, 0)
        painter.drawLine(18, 0, 30, 0)
        
        # Arcs
        radius = 6
        start_x = -18
        for i in range(3):
            x = start_x + i * (radius * 2)
            painter.drawArc(x, -radius, radius * 2, radius * 2, 0, 180 * 16)

    def get_value_text(self) -> str:
        """Retourne la valeur d'inductance a afficher."""
        return f"{self.component.inductance} H"


class DiodeItem(ComponentItem):
    """Item graphique pour une diode."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole d'une diode."""
        painter.setPen(self._pen())
        painter.setBrush(Qt.NoBrush)

        painter.drawLine(-30, 0, -12, 0)
        painter.drawLine(12, 0, 30, 0)

        triangle = QPainterPath()
        triangle.moveTo(-12, -10)
        triangle.lineTo(6, 0)
        triangle.lineTo(-12, 10)
        triangle.closeSubpath()
        painter.drawPath(triangle)
        painter.drawLine(8, -12, 8, 12)

    def get_value_text(self) -> str:
        """Retourne un libelle court."""
        return "D"


class LedItem(DiodeItem):
    """Item graphique pour une LED."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole d'une LED."""
        super().draw_symbol(painter)
        painter.setPen(self._pen_light())
        painter.drawLine(12, -8, 20, -16)
        painter.drawLine(20, -16, 16, -16)
        painter.drawLine(20, -16, 20, -12)
        painter.drawLine(16, -4, 24, -12)
        painter.drawLine(24, -12, 20, -12)
        painter.drawLine(24, -12, 24, -8)

    def get_value_text(self) -> str:
        """Retourne un libelle court."""
        return "LED"

def create_component_item(component_model) -> ComponentItem:
    """Retourne l'element graphique adapte a un objet modele."""
    if isinstance(component_model, Resistor):
        return ResistorItem(component_model)
    elif isinstance(component_model, (VoltageSourceDC, VoltageSourceAC)):
        return VoltageSourceItem(component_model)
    elif isinstance(component_model, (CurrentSourceDC, CurrentSourceAC)):
        return CurrentSourceItem(component_model)
    elif isinstance(component_model, (VoltageControlledCurrentSource, CurrentControlledCurrentSource)):
        return DependentCurrentSourceItem(component_model)
    elif isinstance(component_model, Capacitor):
        return CapacitorItem(component_model)
    elif isinstance(component_model, Inductor):
        return InductorItem(component_model)
    elif isinstance(component_model, LED):
        return LedItem(component_model)
    elif isinstance(component_model, Diode):
        return DiodeItem(component_model)
    else:
        # Repli pour les composants inconnus
        return ComponentItem(component_model)