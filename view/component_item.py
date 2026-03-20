import math

from PyQt5.QtWidgets import QGraphicsItem, QStyle, QApplication
from PyQt5.QtCore import QRectF, Qt, QPointF
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QPainterPath

from model.components import Resistor, VoltageSourceDC, VoltageSourceAC, Capacitor, Inductor

class ComponentItem(QGraphicsItem):
    """Element graphique de base pour tous les dipoles"""

    def __init__(self, component_model):
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
        self.width = 60
        self.height = 40
        
        # Infobulle
        self.setToolTip(f"{self.component.name} (ID: {self.component.id})")

    def boundingRect(self):
        """Definit la zone rectangulaire interactive du composant"""
        margin = 5
        return QRectF(-self.width/2 - margin, -self.height/2 - margin, self.width + 2*margin, self.height + 2*margin)

    def shape(self):
        """Utilise une forme plus serree pour eviter de selectionner l'item dans le vide"""
        path = QPainterPath()
        path.addRect(QRectF(-self.width / 2, -self.height / 2, self.width, self.height))
        return path

    def itemChange(self, change, value):
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

    def mouseReleaseEvent(self, event):
        """Appelee quand le composant est relache apres un deplacement"""
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

    def mousePressEvent(self, event):
        if self._locked:
            event.ignore()
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

    def mouseMoveEvent(self, event):
        if self._is_rotating:
            center = self.mapToScene(QPointF(0, 0))
            dx = event.scenePos().x() - center.x()
            dy = event.scenePos().y() - center.y()
            current_angle = math.degrees(math.atan2(dy, dx))
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

    def update_model_nodes(self):
        """Recalcule les positions des noeuds A et B depuis le centre et la rotation du composant"""
        # Centre du composant
        cx, cy = self.pos().x(), self.pos().y()
        rotation = self.rotation()
        
        # Decalage standard des bornes depuis le centre
        offset = 30
        
        # Calcul trigonometrique
        rad = math.radians(rotation)
        dx = offset * math.cos(rad)
        dy = offset * math.sin(rad)
        
        # Met a jour les coordonnees des noeuds
        self.component.node_a.position = (cx - dx, cy - dy)
        
        self.component.node_b.position = (cx + dx, cy + dy)
        
        # Met a jour la position du dipole
        self.component.position = (cx, cy)

    def set_locked(self, locked):
        self._locked = bool(locked)

    def is_locked(self):
        return self._locked

    def paint(self, painter, option, widget=None):
        """Dessine les limites de selection et le symbole specifique"""
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


    def draw_labels(self, painter):
        """Dessine le nom et la valeur principale"""
        painter.setPen(QColor("black"))
        font = QFont("Arial", 8)
        painter.setFont(font)

        name_rect = QRectF(-30, -35, 60, 15)
        painter.drawText(name_rect, Qt.AlignCenter, self.component.name)
        
        value_text = self.get_value_text()
        val_rect = QRectF(-30, 20, 60, 15)
        painter.drawText(val_rect, Qt.AlignCenter, value_text)

    def draw_symbol(self, painter):
        """A surcharger dans les sous-classes pour dessiner le symbole"""
        pass

    def get_value_text(self):
        """A surcharger pour fournir l'unite ou la valeur affichee"""
        return ""

    # Dessin des symboles

class ResistorItem(ComponentItem):
    def draw_symbol(self, painter):
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
    
    def get_value_text(self):
        # Accede aux proprietes specifiques du modele
        if hasattr(self.component, 'resistance'):
            return f"{self.component.resistance} Ω"
        return ""

class VoltageSourceItem(ComponentItem):
    def draw_symbol(self, painter):
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

    def get_value_text(self):
        if isinstance(self.component, VoltageSourceDC):
            return f"{self.component.dc_voltage} V"
        elif isinstance(self.component, VoltageSourceAC):
            return f"{self.component.amplitude} V"
        return ""

class CapacitorItem(ComponentItem):
    def draw_symbol(self, painter):
        pen = QPen(Qt.black, 2)
        painter.setPen(pen)
        
        # Lignes
        painter.drawLine(-30, 0, -5, 0)
        painter.drawLine(5, 0, 30, 0)
        
        # Plaques verticales
        painter.drawLine(-5, -12, -5, 12)
        painter.drawLine(5, -12, 5, 12)

    def get_value_text(self):
        return f"{self.component.capacitance} F"

class InductorItem(ComponentItem):
    def draw_symbol(self, painter):
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

    def get_value_text(self):
        return f"{self.component.inductance} H"

def create_component_item(component_model):
    """Fonction utilitaire qui retourne l'element graphique adapte a un objet modele"""
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