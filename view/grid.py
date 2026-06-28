from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QPen, QColor

class Grid:
    def __init__(self, grid_size=20):
        self.grid_size = grid_size
        
        # Couleur des points
        self.pen = QPen(QColor(200, 200, 200), 2)
        
        # Ignore le rendu quand le zoom est trop éloigné
        self.min_zoom_factor = 0.3 

    def draw(self, painter, rect, view_scale):
        """Dessine la grille uniquement dans la zone visible."""
        
        # Ignore le rendu quand le zoom est trop éloigné pour economiser le CPU
        if view_scale < self.min_zoom_factor:
            return

        # Limites visibles
        left = rect.left()
        top = rect.top()
        
        # Premier point aligne à la grille
        first_x = left - (left % self.grid_size)
        first_y = top - (top % self.grid_size)

        # Construit les points
        points = []
        
        # Parcourt X de gauche à droite
        x = first_x
        while x < rect.right():
            # Parcourt Y de haut en bas
            y = first_y
            while y < rect.bottom():
                points.append(QPointF(x, y))
                y += self.grid_size
            x += self.grid_size

        # Dessine
        if points:
            painter.setPen(self.pen)
            painter.drawPoints(points)