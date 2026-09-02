"""
Gestionnaire d'aimantation à la grille et aux nœuds pour le canvas.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional, Tuple

from PyQt5.QtCore import QPointF
from config.constants import CANVAS

if TYPE_CHECKING:
    from model.circuit import Circuit
    from model.node import Node


class SnapManager:
    """Gère l'aimantation géométrique sur la grille et les éléments du circuit."""

    def __init__(self, grid_size: int = CANVAS.GRID_SIZE, snap_enabled: bool = True) -> None:
        self.grid_size = grid_size
        self.snap_enabled = snap_enabled
        self.wire_snap_threshold = CANVAS.WIRE_SNAP_THRESHOLD
        self.node_snap_threshold = CANVAS.NODE_SNAP_THRESHOLD

    def snap_point(self, pos: QPointF | Tuple[float, float]) -> Tuple[float, float]:
        """Aimante un point sur la grille régulière la plus proche."""
        if isinstance(pos, QPointF):
            x, y = pos.x(), pos.y()
        else:
            x, y = pos

        if not self.snap_enabled or self.grid_size <= 0:
            return float(x), float(y)

        snapped_x = round(x / self.grid_size) * self.grid_size
        snapped_y = round(y / self.grid_size) * self.grid_size
        return float(snapped_x), float(snapped_y)

    def find_nearest_node(
        self,
        x: float,
        y: float,
        circuit: Optional[Circuit],
        threshold: Optional[float] = None,
    ) -> Optional[Node]:
        """Trouve le nœud le plus proche dans le seuil d'aimantation."""
        if circuit is None:
            return None

        thresh = threshold if threshold is not None else self.node_snap_threshold
        thresh_sq = thresh * thresh

        nearest: Optional[Node] = None
        min_dist_sq = float("inf")

        for node in circuit.nodes.values():
            nx, ny = node.position
            dist_sq = (nx - x) ** 2 + (ny - y) ** 2
            if dist_sq <= thresh_sq and dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                nearest = node

        return nearest

    def snap_wire_angle(
        self,
        start_pos: Tuple[float, float],
        end_pos: Tuple[float, float],
        allow_diagonal: bool = True,
    ) -> Tuple[float, float]:
        """Contraint l'angle d'un fil (orthogonal ou 45°)."""
        x1, y1 = start_pos
        x2, y2 = end_pos
        dx = x2 - x1
        dy = y2 - y1

        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            return x2, y2

        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360.0

        step = 45.0 if allow_diagonal else 90.0
        snapped_angle = round(angle / step) * step
        rad = math.radians(snapped_angle)
        dist = math.hypot(dx, dy)

        return x1 + dist * math.cos(rad), y1 + dist * math.sin(rad)
