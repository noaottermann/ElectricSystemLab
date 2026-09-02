import math

from PyQt5.QtCore import QElapsedTimer, QPointF, QRectF, Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QApplication, QGraphicsItem, QStyle

from utils.translator import Translator

from model.components import (
    Ammeter,
    Capacitor,
    Comparator,
    CurrentControlledCurrentSource,
    CurrentControlledVoltageSource,
    CurrentSource,
    CurrentSourceAC,
    CurrentSourceDC,
    Diode,
    Fuse,
    Ground,
    Inductor,
    LED,
    LogicGate,
    MOSFET,
    MOSFET_NMOS,
    MOSFET_PMOS,
    OpAmp,
    Potentiometer,
    PulseVoltageSource,
    Resistor,
    Switch,
    Transformer,
    Transistor,
    VoltageControlledCurrentSource,
    VoltageControlledVoltageSource,
    VoltageSource,
    VoltageSourceAC,
    VoltageSourceDC,
    Voltmeter,
    ZenerDiode,
)

STANDARD_CIRCLE_RADIUS: float = 16.0


class ComponentItem(QGraphicsItem):
    """Element graphique de base pour tous les dipoles"""

    WIDTH = 60
    HEIGHT = 40
    TERMINAL_OFFSET = 30
    STANDARD_CIRCLE_RADIUS = STANDARD_CIRCLE_RADIUS

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
        """Recalcule les positions de tous les noeuds a partir du centre et de la rotation."""
        center_x, center_y = self.pos().x(), self.pos().y()
        self.component.position = (float(center_x), float(center_y))
        rot_rad = math.radians(self.rotation())
        cos_r = math.cos(rot_rad)
        sin_r = math.sin(rot_rad)

        offsets = getattr(self.component, "get_terminal_offsets", lambda: [(-30.0, 0.0), (30.0, 0.0)])()
        nodes = getattr(self.component, "nodes", [getattr(self.component, "node_a", None), getattr(self.component, "node_b", None)])
        for i, node in enumerate(nodes):
            if node is not None and i < len(offsets):
                ox, oy = offsets[i]
                nx = center_x + ox * cos_r - oy * sin_r
                ny = center_y + ox * sin_r + oy * cos_r
                node.position = (float(nx), float(ny))

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
        offsets = getattr(self.component, "get_terminal_offsets", lambda: [(-30.0, 0.0), (30.0, 0.0)])()
        show_dots = getattr(self.scene(), "show_terminal_dots", True) if self.scene() else True
        if show_dots:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#1f2937"))
            for ox, oy in offsets:
                painter.drawEllipse(QPointF(float(ox), float(oy)), 2.5, 2.5)


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
        painter.drawLine(-30, 0, -int(STANDARD_CIRCLE_RADIUS), 0)
        painter.drawLine(int(STANDARD_CIRCLE_RADIUS), 0, 30, 0)
        
        # Cercle standardise
        painter.drawEllipse(QPointF(0.0, 0.0), STANDARD_CIRCLE_RADIUS, STANDARD_CIRCLE_RADIUS)
        
        # Symboles +/- ou ~
        painter.setPen(self._pen_light())

        state = (getattr(self.component, "get_state", lambda: "dc")() or "dc").lower()
        if state == "dc":
            painter.drawLine(-10, 0, -4, 0)
            painter.drawLine(-7, -3, -7, 3)
            painter.drawLine(4, 0, 10, 0)
        else:
            # Sinusoidal curve
            path = QPainterPath()
            path.moveTo(-8.0, 0.0)
            path.cubicTo(-3.0, -14.0, 3.0, 14.0, 8.0, 0.0)
            painter.drawPath(path)

    def get_value_text(self) -> str:
        """Retourne la valeur de tension a afficher."""
        state = (getattr(self.component, "get_state", lambda: "dc")() or "dc").lower()
        if state == "dc":
            return f"{self.component.dc_voltage} V"
        if state == "ac":
            return f"{self.component.amplitude} V"
        return ""


class CurrentSourceItem(ComponentItem):
    """Item graphique pour les sources de courant."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole de la source de courant."""
        painter.setPen(self._pen())
        painter.setBrush(Qt.NoBrush)

        painter.drawLine(-30, 0, -int(STANDARD_CIRCLE_RADIUS), 0)
        painter.drawLine(int(STANDARD_CIRCLE_RADIUS), 0, 30, 0)
        painter.drawEllipse(QPointF(0.0, 0.0), STANDARD_CIRCLE_RADIUS, STANDARD_CIRCLE_RADIUS)

        painter.setPen(self._pen_light())
        state = (getattr(self.component, "get_state", lambda: "dc")() or "dc").lower()
        if state == "dc":
            painter.drawLine(-6, 0, 6, 0)
            painter.drawLine(6, 0, 2, -3)
            painter.drawLine(6, 0, 2, 3)
        else:
            painter.drawLine(-6, 6, 6, 6)
            painter.drawLine(6, 6, 2, 3)
            painter.drawLine(6, 6, 2, 9)
            path = QPainterPath()
            path.moveTo(-8, -5)
            path.cubicTo(-3, -19, 3, 9, 8, -5)
            painter.drawPath(path)

    def get_value_text(self) -> str:
        """Retourne la valeur de courant a afficher."""
        state = (getattr(self.component, "get_state", lambda: "dc")() or "dc").lower()
        if state == "dc":
            return f"{self.component.dc_current} A"
        if state == "ac":
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
        painter.drawLine(-6, 0, 6, 0)
        painter.drawLine(6, 0, 2, -3)
        painter.drawLine(6, 0, 2, 3)
        if isinstance(self.component, VoltageControlledCurrentSource):
            painter.drawText(18, -10, "Vx")
        else:
            painter.drawText(18, -10, "Ix")

    def get_value_text(self) -> str:
        """Retourne la valeur de gain a afficher."""
        if isinstance(self.component, VoltageControlledCurrentSource):
            return f"{self.component.transconductance} S"
        if isinstance(self.component, CurrentControlledCurrentSource):
            return f"{self.component.gain} A/A"
        return ""


class DependentVoltageSourceItem(ComponentItem):
    """Item graphique pour les sources de tension dependantes."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole d'une source de tension dependante."""
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
        painter.drawLine(-10, 0, -4, 0)
        painter.drawLine(-7, -3, -7, 3)
        painter.drawLine(4, 0, 10, 0)
        if isinstance(self.component, VoltageControlledVoltageSource):
            painter.drawText(18, -10, "Vx")
        elif isinstance(self.component, CurrentControlledVoltageSource):
            painter.drawText(18, -10, "Ix")

    def get_value_text(self) -> str:
        """Retourne la valeur de gain a afficher."""
        if isinstance(self.component, VoltageControlledVoltageSource):
            return f"{self.component.gain} V/V"
        if isinstance(self.component, CurrentControlledVoltageSource):
            return f"{self.component.transresistance} Ohm"
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
    """Item graphique pour une diode (unifiee standard, zener, led)."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole d'une diode selon son etat."""
        painter.setPen(self._pen())
        painter.setBrush(Qt.NoBrush)

        painter.drawLine(-30, 0, -12, 0)
        painter.drawLine(12, 0, 30, 0)

        triangle = QPainterPath()
        triangle.moveTo(-12.0, -10.0)
        triangle.lineTo(6.0, 0.0)
        triangle.lineTo(-12.0, 10.0)
        triangle.closeSubpath()
        painter.drawPath(triangle)

        state = (getattr(self.component, "get_state", lambda: "standard")() or "standard").lower()
        if "zener" in state or isinstance(self.component, ZenerDiode):
            # Cathode en Z inversee : haut-droit (8->12, -12) et bas-gauche (4->8, 12)
            painter.drawLine(8, -12, 8, 12)
            painter.drawLine(8, -12, 12, -12)
            painter.drawLine(4, 12, 8, 12)
        else:
            painter.drawLine(8, -12, 8, 12)

        if "led" in state or isinstance(self.component, LED):
            painter.setPen(self._pen_light())
            painter.drawLine(12, -8, 20, -16)
            painter.drawLine(20, -16, 16, -16)
            painter.drawLine(20, -16, 20, -12)
            painter.drawLine(16, -4, 24, -12)
            painter.drawLine(24, -12, 20, -12)
            painter.drawLine(24, -12, 24, -8)

    def get_value_text(self) -> str:
        """Retourne un libelle adapte a l'etat de la diode."""
        state = (getattr(self.component, "get_state", lambda: "standard")() or "standard").lower()
        if "zener" in state or isinstance(self.component, ZenerDiode):
            vz = getattr(self.component, "zener_voltage", 5.1)
            return f"Vz={vz:.3g}V"
        if "led" in state or isinstance(self.component, LED):
            return "LED"
        return "D"


class LedItem(DiodeItem):
    """Item graphique pour une LED."""

    def get_value_text(self) -> str:
        """Retourne un libelle court."""
        return "LED"


class SwitchItem(ComponentItem):
    """Item graphique pour un interrupteur."""

    def __init__(self, component_model) -> None:
        super().__init__(component_model)
        self._flash_timer = QTimer()
        self._flash_timer.setInterval(30)
        self._flash_timer.timeout.connect(self._on_flash_tick)
        self._flash_elapsed = QElapsedTimer()
        self._flash_duration_ms = 220

    def mousePressEvent(self, event) -> None:
        """Bascule l'etat du switch avec clic droit."""
        if event.button() == Qt.RightButton:
            if self.scene() and hasattr(self.scene(), "_push_undo_snapshot"):
                self.scene()._push_undo_snapshot()
            current = (getattr(self.component, "get_state", lambda: "")() or "").lower()
            new_state = "closed" if current != "closed" else "open"
            if hasattr(self.component, "set_state"):
                self.component.set_state(new_state)
            self._start_flash()
            self.update()
            if self.scene() is not None:
                self.scene().update()
            event.accept()
            return
        super().mousePressEvent(event)

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole d'un interrupteur."""
        painter.setPen(self._pen())
        painter.setBrush(Qt.NoBrush)

        painter.drawLine(-30, 0, -10, 0)
        painter.drawLine(10, 0, 30, 0)

        state = (getattr(self.component, "get_state", lambda: "")() or "").lower()
        if state == "closed":
            painter.drawLine(-10, 0, 10, 0)
        else:
            painter.drawLine(-10, 0, 8, -10)

        indicator_color = QColor("#16a34a") if state == "closed" else QColor("#dc2626")
        painter.setBrush(indicator_color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(0, -12), 4, 4)

        if self._flash_timer.isActive():
            progress = min(self._flash_elapsed.elapsed() / self._flash_duration_ms, 1.0)
            alpha = int(90 * (1.0 - progress))
            if alpha > 0:
                painter.setBrush(QColor(255, 200, 80, alpha))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QPointF(0, 0), 18, 18)

    def get_value_text(self) -> str:
        state = (getattr(self.component, "get_state", lambda: "")() or "").lower()
        key = "switch_state_closed" if state == "closed" else "switch_state_open"
        return Translator.tr(key)

    def _start_flash(self) -> None:
        self._flash_elapsed.start()
        if not self._flash_timer.isActive():
            self._flash_timer.start()

    def _on_flash_tick(self) -> None:
        if self._flash_elapsed.elapsed() >= self._flash_duration_ms:
            self._flash_timer.stop()
        self.update()

class ZenerDiodeItem(DiodeItem):
    """Item graphique pour une diode Zener."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole d'une diode Zener avec cathode en Z inversee."""
        painter.setPen(self._pen())
        painter.setBrush(Qt.NoBrush)

        painter.drawLine(-30, 0, -12, 0)
        painter.drawLine(12, 0, 30, 0)

        triangle = QPainterPath()
        triangle.moveTo(-12.0, -10.0)
        triangle.lineTo(6.0, 0.0)
        triangle.lineTo(-12.0, 10.0)
        triangle.closeSubpath()
        painter.drawPath(triangle)

        # Cathode en Z inversee : barre principale + haut-droit + bas-gauche
        painter.drawLine(8, -12, 8, 12)
        painter.drawLine(8, -12, 12, -12)
        painter.drawLine(4, 12, 8, 12)

    def get_value_text(self) -> str:
        vz = getattr(self.component, "zener_voltage", 5.1)
        return f"Vz={vz:.3g}V"


class PotentiometerItem(ComponentItem):
    """Item graphique pour un potentiomètre."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole d'un potentiomètre."""
        painter.setPen(self._pen())
        painter.setBrush(Qt.NoBrush)

        painter.drawLine(-30, 0, -18, 0)
        painter.drawLine(18, 0, 30, 0)
        painter.drawRect(QRectF(-18, -8, 36, 16))

        # Curseur fléché vers le haut
        painter.drawLine(0, -20, 0, -8)
        arrow = QPainterPath()
        arrow.moveTo(-4, -12)
        arrow.lineTo(0, -8)
        arrow.lineTo(4, -12)
        painter.drawPath(arrow)

    def get_value_text(self) -> str:
        res = getattr(self.component, "resistance", 10000.0)
        ratio = getattr(self.component, "slider_ratio", 0.5)
        return f"{res:.3g}Ω ({int(ratio*100)}%)"


class OpAmpItem(ComponentItem):
    """Item graphique pour un amplificateur opérationnel (AOP)."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole d'un AOP (3 bornes ou 5 bornes avec alimentation)."""
        painter.setPen(self._pen())
        painter.setBrush(Qt.NoBrush)

        # Triangle principal
        tri = QPainterPath()
        tri.moveTo(-20.0, -22.0)
        tri.lineTo(-20.0, 22.0)
        tri.lineTo(20.0, 0.0)
        tri.closeSubpath()
        painter.drawPath(tri)

        # Lignes d'entrée et sortie
        painter.drawLine(-30, -12, -20, -12)
        painter.drawLine(-30, 12, -20, 12)
        painter.drawLine(20, 0, 30, 0)

        # Broches d'alimentation pour AOP 5 bornes
        is_5_term = getattr(self.component, "mode", "3_terminal") == "5_terminal"
        if is_5_term:
            painter.drawLine(0, -11, 0, -25)
            painter.drawLine(0, 11, 0, 25)
            painter.setPen(self._pen_light())
            font_v = QFont("Arial", 6, QFont.Bold)
            painter.setFont(font_v)
            painter.drawText(QRectF(3.0, -27.0, 18.0, 10.0), Qt.AlignLeft | Qt.AlignVCenter, "V+")
            painter.drawText(QRectF(3.0, 17.0, 18.0, 10.0), Qt.AlignLeft | Qt.AlignVCenter, "V-")

        # Signes + et - : rapprochés de l'axe horizontal (y = +/- 7.0) et décalés vers la droite (x = -10.0)
        painter.setPen(self._pen_light())
        # Entrée + en haut
        painter.drawLine(-13, -7, -7, -7)
        painter.drawLine(-10, -10, -10, -4)
        # Entrée - en bas
        painter.drawLine(-13, 7, -7, 7)

    def get_value_text(self) -> str:
        return "OpAmp"


class TransformerItem(ComponentItem):
    """Item graphique pour un transformateur."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole d'un transformateur avec raccordement sans rupture."""
        painter.setPen(self._pen())
        painter.setBrush(Qt.NoBrush)

        # Lignes externes se connectant rigoureusement aux arcs d'enroulement à x = +/- 13.0
        painter.drawLine(-30, -15, -13, -15)
        painter.drawLine(-30, 15, -13, 15)
        painter.drawLine(13, -15, 30, -15)
        painter.drawLine(13, 15, 30, 15)

        # Enroulement primaire (gauche) : arcs tangents à x = -13.0
        for i in range(3):
            y = -15.0 + i * 10.0
            painter.drawArc(QRectF(-18.0, y, 10.0, 10.0), -90 * 16, 180 * 16)

        # Enroulement secondaire (droite) : arcs tangents à x = 13.0
        for i in range(3):
            y = -15.0 + i * 10.0
            painter.drawArc(QRectF(8.0, y, 10.0, 10.0), 90 * 16, 180 * 16)

        # Barres de noyau central
        painter.setPen(self._pen_light())
        painter.drawLine(-2, -18, -2, 18)
        painter.drawLine(2, -18, 2, 18)

    def get_value_text(self) -> str:
        ratio = getattr(self.component, "ratio", 1.0)
        return f"1:{ratio:.3g}"


class TransistorItem(ComponentItem):
    """Item graphique pour un transistor BJT."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole d'un transistor BJT (NPN ou PNP)."""
        painter.setPen(self._pen())
        painter.setBrush(Qt.NoBrush)

        # Cercle standardise
        painter.drawEllipse(QPointF(0.0, 0.0), STANDARD_CIRCLE_RADIUS, STANDARD_CIRCLE_RADIUS)

        # Ligne et barre de base
        painter.drawLine(-30, 0, -8, 0)
        painter.drawLine(-8, -12, -8, 12)

        # Collecteur et Émetteur (se raccordant exactement aux bornes a x=15.0, y=+/-25.0)
        painter.drawLine(-8, -6, 15, -25)
        painter.drawLine(-8, 6, 15, 25)

        # Flèche émetteur symétrique et alignée sur la diagonale
        is_pnp = str(getattr(self.component, "transistor_type", "NPN")).upper() == "PNP"
        if not is_pnp:
            # Flèche sortante NPN (vers l'émetteur en bas à droite)
            tip_x, tip_y = 5.8, 17.4
            painter.drawLine(QPointF(tip_x, tip_y), QPointF(3.44, 12.43))
            painter.drawLine(QPointF(tip_x, tip_y), QPointF(0.48, 16.02))
        else:
            # Flèche entrante PNP (vers la base en haut à gauche)
            tip_x, tip_y = 1.2, 13.6
            painter.drawLine(QPointF(tip_x, tip_y), QPointF(3.56, 18.57))
            painter.drawLine(QPointF(tip_x, tip_y), QPointF(6.52, 14.98))

    def get_value_text(self) -> str:
        t_type = getattr(self.component, "transistor_type", "NPN")
        beta = getattr(self.component, "beta", 100.0)
        return f"{t_type} (β={int(beta)})"


class MosfetItem(ComponentItem):
    """Item graphique pour un transistor MOSFET."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole d'un transistor MOSFET (NMOS ou PMOS)."""
        painter.setPen(self._pen())
        painter.setBrush(Qt.NoBrush)

        # Cercle standardise
        painter.drawEllipse(QPointF(0.0, 0.0), STANDARD_CIRCLE_RADIUS, STANDARD_CIRCLE_RADIUS)

        # Grille
        painter.drawLine(-30, 0, -10, 0)
        painter.drawLine(-10, -14, -10, 14)

        # Canal segmenté
        painter.drawLine(-5, -14, -5, -6)
        painter.drawLine(-5, -3, -5, 3)
        painter.drawLine(-5, 6, -5, 14)

        # Drain et Source (se raccordant exactement aux bornes a x=15.0, y=+/-25.0)
        painter.drawLine(-5, -10, 15, -25)
        painter.drawLine(-5, 10, 15, 25)

        # Flèche de substrat (direction selon NMOS / PMOS)
        is_pmos = str(getattr(self.component, "mosfet_type", "NMOS")).upper() == "PMOS"
        if not is_pmos:
            # Flèche pointant vers le canal intérieur pour NMOS
            painter.drawLine(QPointF(3.0, 0.0), QPointF(-5.0, 0.0))
            painter.drawLine(QPointF(-5.0, 0.0), QPointF(-1.5, -3.0))
            painter.drawLine(QPointF(-5.0, 0.0), QPointF(-1.5, 3.0))
        else:
            # Flèche pointant vers l'extérieur pour PMOS
            painter.drawLine(QPointF(-5.0, 0.0), QPointF(3.0, 0.0))
            painter.drawLine(QPointF(3.0, 0.0), QPointF(-0.5, -3.0))
            painter.drawLine(QPointF(3.0, 0.0), QPointF(-0.5, 3.0))

    def get_value_text(self) -> str:
        return getattr(self.component, "mosfet_type", "NMOS")


class ComparatorItem(ComponentItem):
    """Item graphique pour un comparateur de tension analogique."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole d'un comparateur avec cycle d'hystérésis Schmitt standard."""
        painter.setPen(self._pen())
        painter.setBrush(Qt.NoBrush)

        # Triangle
        tri = QPainterPath()
        tri.moveTo(-20.0, -22.0)
        tri.lineTo(-20.0, 22.0)
        tri.lineTo(20.0, 0.0)
        tri.closeSubpath()
        painter.drawPath(tri)

        painter.drawLine(-30, -12, -20, -12)
        painter.drawLine(-30, 12, -20, 12)
        painter.drawLine(20, 0, 30, 0)

        # Symbole d'hystérésis Schmitt standard IEEE (double palier et transitions nettes)
        painter.setPen(self._pen_light())
        hys = QPainterPath()
        hys.moveTo(-6.0, -4.5)
        hys.lineTo(3.0, -4.5)
        hys.lineTo(3.0, 4.5)
        hys.moveTo(6.0, 4.5)
        hys.lineTo(-3.0, 4.5)
        hys.lineTo(-3.0, -4.5)
        painter.drawPath(hys)

    def get_value_text(self) -> str:
        return "Comp"


class PulseVoltageSourceItem(ComponentItem):
    """Item graphique pour une source de tension impulsionnelle / horloge."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole d'une source impulsionnelle standardisee."""
        painter.setPen(self._pen())
        painter.setBrush(Qt.NoBrush)

        painter.drawEllipse(QPointF(0.0, 0.0), STANDARD_CIRCLE_RADIUS, STANDARD_CIRCLE_RADIUS)
        painter.drawLine(-30, 0, -int(STANDARD_CIRCLE_RADIUS), 0)
        painter.drawLine(int(STANDARD_CIRCLE_RADIUS), 0, 30, 0)

        # Signal créneau
        pulse = QPainterPath()
        pulse.moveTo(-10.0, 4.0)
        pulse.lineTo(-4.0, 4.0)
        pulse.lineTo(-4.0, -4.0)
        pulse.lineTo(4.0, -4.0)
        pulse.lineTo(4.0, 4.0)
        pulse.lineTo(10.0, 4.0)
        painter.drawPath(pulse)

    def get_value_text(self) -> str:
        vp = getattr(self.component, "v_pulsed", 5.0)
        t_period = getattr(self.component, "period", 1e-3)
        return f"{vp}V / {t_period*1e3:.2g}ms"


class LogicGateItem(ComponentItem):
    """Item graphique pour une porte logique combinatoire (AND, OR, NOT, NAND, NOR, XOR)."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole IEEE standard de la porte logique."""
        painter.setPen(self._pen())
        painter.setBrush(Qt.NoBrush)

        gtype = str(getattr(self.component, "gate_type", "AND")).upper()

        if gtype == "NOT":
            painter.drawLine(-30, 0, -15, 0)
            tri = QPainterPath()
            tri.moveTo(-15, -12)
            tri.lineTo(-15, 12)
            tri.lineTo(10, 0)
            tri.closeSubpath()
            painter.drawPath(tri)
            painter.drawEllipse(QPointF(13, 0), 3, 3)
            painter.drawLine(16, 0, 30, 0)
        elif gtype in ("AND", "NAND"):
            painter.drawLine(-30, -10, -15, -10)
            painter.drawLine(-30, 10, -15, 10)
            path = QPainterPath()
            path.moveTo(-15, -14)
            path.lineTo(0, -14)
            path.arcTo(QRectF(-14, -14, 28, 28), 90, -180)
            path.lineTo(-15, 14)
            path.closeSubpath()
            painter.drawPath(path)
            if gtype == "NAND":
                painter.drawEllipse(QPointF(17, 0), 3, 3)
                painter.drawLine(20, 0, 30, 0)
            else:
                painter.drawLine(14, 0, 30, 0)
        elif gtype in ("OR", "NOR", "XOR"):
            painter.drawLine(-30, -10, -15, -10)
            painter.drawLine(-30, 10, -15, 10)
            if gtype == "XOR":
                xor_arc = QPainterPath()
                xor_arc.moveTo(-20, -14)
                xor_arc.quadTo(-14, 0, -20, 14)
                painter.drawPath(xor_arc)

            path = QPainterPath()
            path.moveTo(-15, -14)
            path.quadTo(5, -14, 15, 0)
            path.quadTo(5, 14, -15, 14)
            path.quadTo(-8, 0, -15, -14)
            painter.drawPath(path)

            if gtype == "NOR":
                painter.drawEllipse(QPointF(18, 0), 3, 3)
                painter.drawLine(21, 0, 30, 0)
            else:
                painter.drawLine(15, 0, 30, 0)

    def get_value_text(self) -> str:
        return getattr(self.component, "gate_type", "AND")


class FuseItem(ComponentItem):
    """Item graphique pour un fusible."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole d'un fusible."""
        painter.setPen(self._pen())
        painter.setBrush(Qt.NoBrush)

        painter.drawRect(QRectF(-18, -8, 36, 16))
        painter.drawLine(-30, 0, -18, 0)
        painter.drawLine(18, 0, 30, 0)

        is_blown = bool(getattr(self.component, "blown", False))
        if is_blown:
            painter.setPen(QPen(QColor("#dc2626"), 2))
            painter.drawLine(-12, -4, -2, 4)
            painter.drawLine(2, -4, 12, 4)
        else:
            painter.setPen(self._pen_light())
            painter.drawLine(-18, 0, 18, 0)

    def get_value_text(self) -> str:
        inom = getattr(self.component, "i_nominal", 1.0)
        blown = getattr(self.component, "blown", False)
        return f"{inom}A (Fondu)" if blown else f"{inom}A"


class GroundItem(ComponentItem):
    """Item graphique pour le symbole de masse (Ground)."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole de masse normalisé."""
        painter.setPen(self._pen())
        painter.setBrush(Qt.NoBrush)

        # Ligne de connexion verticale
        painter.drawLine(0, -15, 0, 0)

        # 3 barres horizontales décroissantes
        painter.drawLine(-14, 0, 14, 0)
        painter.drawLine(-9, 5, 9, 5)
        painter.drawLine(-4, 10, 4, 10)

    def get_value_text(self) -> str:
        return "GND"


class VoltmeterItem(ComponentItem):
    """Item graphique pour un voltmètre."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole du voltmètre avec affichage de la mesure."""
        painter.setPen(self._pen())
        painter.setBrush(Qt.NoBrush)

        painter.drawEllipse(QPointF(0.0, 0.0), STANDARD_CIRCLE_RADIUS, STANDARD_CIRCLE_RADIUS)
        painter.drawLine(-30, 0, -int(STANDARD_CIRCLE_RADIUS), 0)
        painter.drawLine(int(STANDARD_CIRCLE_RADIUS), 0, 30, 0)

        painter.setFont(QFont("Arial", 11, QFont.Bold))
        painter.drawText(QRectF(-STANDARD_CIRCLE_RADIUS, -STANDARD_CIRCLE_RADIUS - 1.0, 2.0 * STANDARD_CIRCLE_RADIUS, 2.0 * STANDARD_CIRCLE_RADIUS), Qt.AlignCenter, "V")

        # Cadran numérique LCD affichant la tension mesurée
        v = float(getattr(self.component, "voltage", 0.0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#0f172a"))
        painter.drawRoundedRect(QRectF(-24.0, 18.0, 48.0, 14.0), 3.0, 3.0)
        painter.setPen(QColor("#38bdf8"))
        painter.setFont(QFont("Courier New", 7, QFont.Bold))
        txt = f"{v:+.2f}V" if abs(v) < 1000 else f"{v:+.1f}V"
        painter.drawText(QRectF(-24.0, 18.0, 48.0, 14.0), Qt.AlignCenter, txt)

    def get_value_text(self) -> str:
        return ""


class AmmeterItem(ComponentItem):
    """Item graphique pour un ampèremètre."""

    def draw_symbol(self, painter: QPainter) -> None:
        """Dessine le symbole de l'ampèremètre avec affichage de la mesure."""
        painter.setPen(self._pen())
        painter.setBrush(Qt.NoBrush)

        painter.drawEllipse(QPointF(0.0, 0.0), STANDARD_CIRCLE_RADIUS, STANDARD_CIRCLE_RADIUS)
        painter.drawLine(-30, 0, -int(STANDARD_CIRCLE_RADIUS), 0)
        painter.drawLine(int(STANDARD_CIRCLE_RADIUS), 0, 30, 0)

        painter.setFont(QFont("Arial", 11, QFont.Bold))
        painter.drawText(QRectF(-STANDARD_CIRCLE_RADIUS, -STANDARD_CIRCLE_RADIUS - 1.0, 2.0 * STANDARD_CIRCLE_RADIUS, 2.0 * STANDARD_CIRCLE_RADIUS), Qt.AlignCenter, "A")

        # Cadran numérique LCD affichant le courant mesuré
        i = float(getattr(self.component, "current", 0.0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#0f172a"))
        painter.drawRoundedRect(QRectF(-24.0, 18.0, 48.0, 14.0), 3.0, 3.0)
        painter.setPen(QColor("#4ade80"))
        painter.setFont(QFont("Courier New", 7, QFont.Bold))
        if abs(i) < 1e-3 and abs(i) > 0:
            txt = f"{i*1e6:+.0f}µA"
        elif abs(i) < 1.0 and abs(i) > 0:
            txt = f"{i*1e3:+.1f}mA"
        else:
            txt = f"{i:+.2f}A"
        painter.drawText(QRectF(-24.0, 18.0, 48.0, 14.0), Qt.AlignCenter, txt)

    def get_value_text(self) -> str:
        return ""


def create_component_item(component_model) -> ComponentItem:
    """Retourne l'élément graphique adapté à un objet modèle."""
    if isinstance(component_model, Resistor):
        return ResistorItem(component_model)
    elif isinstance(component_model, PulseVoltageSource):
        return PulseVoltageSourceItem(component_model)
    elif isinstance(component_model, (VoltageSource, VoltageSourceDC, VoltageSourceAC)):
        return VoltageSourceItem(component_model)
    elif isinstance(component_model, (CurrentSource, CurrentSourceDC, CurrentSourceAC)):
        return CurrentSourceItem(component_model)
    elif isinstance(component_model, (VoltageControlledCurrentSource, CurrentControlledCurrentSource)):
        return DependentCurrentSourceItem(component_model)
    elif isinstance(component_model, (VoltageControlledVoltageSource, CurrentControlledVoltageSource)):
        return DependentVoltageSourceItem(component_model)
    elif isinstance(component_model, Capacitor):
        return CapacitorItem(component_model)
    elif isinstance(component_model, Inductor):
        return InductorItem(component_model)
    elif isinstance(component_model, LED):
        return LedItem(component_model)
    elif isinstance(component_model, ZenerDiode):
        return ZenerDiodeItem(component_model)
    elif isinstance(component_model, Diode):
        return DiodeItem(component_model)
    elif isinstance(component_model, Switch):
        return SwitchItem(component_model)
    elif isinstance(component_model, Potentiometer):
        return PotentiometerItem(component_model)
    elif isinstance(component_model, OpAmp):
        return OpAmpItem(component_model)
    elif isinstance(component_model, Comparator):
        return ComparatorItem(component_model)
    elif isinstance(component_model, Transformer):
        return TransformerItem(component_model)
    elif isinstance(component_model, Transistor):
        return TransistorItem(component_model)
    elif isinstance(component_model, (MOSFET, MOSFET_NMOS, MOSFET_PMOS)):
        return MosfetItem(component_model)
    elif isinstance(component_model, LogicGate):
        return LogicGateItem(component_model)
    elif isinstance(component_model, Fuse):
        return FuseItem(component_model)
    elif isinstance(component_model, Ground):
        return GroundItem(component_model)
    elif isinstance(component_model, Voltmeter):
        return VoltmeterItem(component_model)
    elif isinstance(component_model, Ammeter):
        return AmmeterItem(component_model)
    else:
        return ComponentItem(component_model)