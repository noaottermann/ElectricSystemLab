"""
Gestionnaire de la sélection, déplacements groupés et transformations sur le canvas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, Optional

from PyQt5.QtCore import QPointF, QRectF
from PyQt5.QtWidgets import QGraphicsItem

if TYPE_CHECKING:
    from model.circuit import Circuit


class SelectionManager:
    """Gère la manipulation des groupes d'éléments sélectionnés."""

    def __init__(self) -> None:
        self._selection_snapshot: Optional[list[dict[str, Any]]] = None

    def get_selection_bounding_rect(self, items: Iterable[QGraphicsItem]) -> QRectF:
        """Calcule le rectangle englobant l'ensemble des éléments sélectionnés."""
        rect = QRectF()
        first = True
        for item in items:
            item_rect = item.sceneBoundingRect()
            if first:
                rect = item_rect
                first = False
            else:
                rect = rect.united(item_rect)
        return rect

    def move_selection(self, items: Iterable[QGraphicsItem], dx: float, dy: float) -> None:
        """Déplace un ensemble d'éléments graphiques."""
        for item in items:
            item.setPos(item.x() + dx, item.y() + dy)

    def rotate_selection(self, items: Iterable[QGraphicsItem], angle_step: float = 90.0) -> None:
        """Fait pivoter les composants sélectionnés."""
        for item in items:
            if hasattr(item, "setRotation"):
                new_rot = (item.rotation() + angle_step) % 360.0
                item.setRotation(new_rot)
                if hasattr(item, "dipole") and item.dipole is not None:
                    item.dipole.rotation = new_rot
