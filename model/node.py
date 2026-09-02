from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .component import Component


class Node:
    """Représente un noeud électrique dans le circuit."""

    def __init__(self, node_id: int, x: float = 0.0, y: float = 0.0, is_ground: bool = False) -> None:
        """Initialise un nouveau noeud."""
        self.id = int(node_id)
        self.position = (float(x), float(y))
        self.is_ground = bool(is_ground)
        self._potential = 0.0
        self.connected_dipoles: list[Component] = []

    @property
    def potential(self) -> float:
        """Retourne le potentiel électrique du noeud."""
        return self._potential

    @potential.setter
    def potential(self, value: float) -> None:
        """Met à jour le potentiel électrique en respectant la masse."""
        if self.is_ground:
            self._potential = 0.0
        else:
            self._potential = float(value)

    def add_connection(self, dipole: "Component") -> None:
        """Ajoute un composant aux connexions de ce noeud."""
        if dipole not in self.connected_dipoles:
            self.connected_dipoles.append(dipole)

    def remove_connection(self, dipole: "Component") -> None:
        """Supprime un composant des connexions de ce noeud."""
        if dipole in self.connected_dipoles:
            self.connected_dipoles.remove(dipole)

    def to_dict(self) -> dict[str, object]:
        """Retourne une représentation sérialisable du noeud."""
        return {
            "id": self.id,
            "position": self.position,
            "is_ground": self.is_ground,
            "potential": self._potential
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Node":
        """Reconstruit un noeud à partir d'un dictionnaire."""
        x, y = data.get("position", (0.0, 0.0))
        node = cls(
            node_id=data["id"],
            x=x,
            y=y,
            is_ground=data.get("is_ground", False)
        )
        if "potential" in data:
            node._potential = float(data["potential"])
        return node

    def __repr__(self) -> str:
        """Retourne une représentation textuelle du noeud."""
        state = "GND" if self.is_ground else f"{self._potential:.2f}V"
        return f"<Node {self.id} | Pos={self.position} | {state}>"