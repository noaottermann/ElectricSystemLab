from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .node import Node


class Wire:
    """Représente un fil électrique idéal."""

    def __init__(self, wire_id: int, node_a: Optional["Node"], node_b: Optional["Node"], color: str = "#000000") -> None:
        """Initialise un fil."""
        self.id = int(wire_id)
        self.node_a: Optional["Node"] = node_a
        self.node_b: Optional["Node"] = node_b
        self.color = color

    def disconnect(self) -> None:
        """Détache le fil de ses noeuds."""
        self.node_a = None
        self.node_b = None

    def to_dict(self) -> dict[str, object]:
        """Retourne une représentation sérialisable du fil."""
        return {
            "id": self.id,
            "node_a_id": self.node_a.id if self.node_a else None,
            "node_b_id": self.node_b.id if self.node_b else None,
            "color": self.color
        }

    @classmethod
    def from_dict(cls, data: dict, nodes_dict: dict) -> Optional["Wire"]:
        """Reconstruit un fil à partir d'un dictionnaire."""
        node_a_id = data.get("node_a_id")
        node_b_id = data.get("node_b_id")
        node_a = nodes_dict.get(node_a_id)
        node_b = nodes_dict.get(node_b_id)
        if not node_a or not node_b:
            return None
        return cls(
            wire_id=data["id"],
            node_a=node_a,
            node_b=node_b,
            color=data.get("color", "#000000")
        )

    def __repr__(self) -> str:
        """Retourne une représentation textuelle du fil."""
        id_a = self.node_a.id if self.node_a is not None else None
        id_b = self.node_b.id if self.node_b is not None else None
        return f"<Wire {self.id} | Nodes: {id_a}-{id_b}>"