"""
Classe de base abstraite pour tous les composants électriques (dipôles et multi-bornes).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class Component(ABC):
    """Classe de base abstraite représentant tout composant électrique."""

    def __init__(
        self,
        dipole_id: int,
        name: str,
        *nodes: Optional[Any],
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
    ) -> None:
        """Initialise un composant avec ses nœuds et attributs géométriques."""
        self.id = int(dipole_id)
        self.name = str(name)
        self.nodes: list[Optional[Any]] = list(nodes)
        self.position = (float(x), float(y))
        self.rotation = float(rotation)
        self._current = 0.0

        for node in self.nodes:
            if node is not None and hasattr(node, "add_connection"):
                node.add_connection(self)

    @property
    def node_count(self) -> int:
        """Nombre de bornes / nœuds du composant."""
        return len(self.nodes)

    @property
    def voltage(self) -> float:
        """Retourne la différence de potentiel principale (entre les deux premières bornes)."""
        if len(self.nodes) >= 2:
            va = self.nodes[0].potential if self.nodes[0] else 0.0
            vb = self.nodes[1].potential if self.nodes[1] else 0.0
            return float(va - vb)
        elif len(self.nodes) == 1:
            return float(self.nodes[0].potential if self.nodes[0] else 0.0)
        return 0.0

    @property
    def current(self) -> float:
        """Retourne le courant principal traversant le composant."""
        return self._current

    @current.setter
    def current(self, value: float) -> None:
        """Met à jour le courant principal."""
        self._current = float(value)

    @property
    def power(self) -> float:
        """Retourne la puissance instantanée calculée P = U * I."""
        return self.voltage * self.current

    def disconnect(self) -> None:
        """Détache le composant de tous ses nœuds connectés."""
        for node in self.nodes:
            if node is not None and hasattr(node, "remove_connection"):
                node.remove_connection(self)
        self.nodes = [None] * len(self.nodes)

    def replace_node(self, old_node: Any, new_node: Any) -> bool:
        """Remplace une référence de nœud par un autre (utile pour la fusion de nœuds)."""
        changed = False
        for idx, node in enumerate(self.nodes):
            if node is old_node:
                self.nodes[idx] = new_node
                changed = True
        return changed

    def to_dict(self) -> dict[str, object]:
        """Retourne une représentation sérialisable du composant."""
        node_ids = [n.id if n else None for n in self.nodes]
        data: dict[str, object] = {
            "type": self.__class__.__name__,
            "id": self.id,
            "name": self.name,
            "position": self.position,
            "rotation": self.rotation,
            "params": self.get_params(),
        }
        if len(node_ids) >= 1:
            data["node_a_id"] = node_ids[0]
        if len(node_ids) >= 2:
            data["node_b_id"] = node_ids[1]
        if len(node_ids) >= 3:
            data["node_c_id"] = node_ids[2]
        if len(node_ids) >= 4:
            data["node_d_id"] = node_ids[3]
        return data

    def get_params(self) -> dict[str, object]:
        """Retourne les paramètres spécifiques du composant."""
        return {}

    def set_params(self, params: dict[str, Any]) -> None:
        """Applique des paramètres spécifiques."""
        pass

    def get_state(self) -> Optional[str]:
        """Retourne l'état courant pour les composants multi-états."""
        return None

    def get_state_options(self) -> list[tuple[str, str]]:
        """Retourne la liste des options d'états (clé, libellé)."""
        return []

    def set_state(self, value: str) -> None:
        """Définit l'état actif."""
        pass

    def get_terminal_offsets(self) -> list[tuple[float, float]]:
        """Retourne les positions relatives (dx, dy) de chaque borne par rapport au centre."""
        if len(self.nodes) == 1:
            return [(0.0, 0.0)]
        return [(-30.0, 0.0), (30.0, 0.0)]

    @classmethod
    def from_dict(cls, data: dict[str, Any], nodes_dict: dict[int, Any]) -> Component:
        """Reconstruit un composant à partir d'un dictionnaire sérialisé."""
        node_keys = ["node_a_id", "node_b_id", "node_c_id", "node_d_id", "node_e_id"]
        nodes = []
        for key in node_keys:
            if key in data:
                nid = data[key]
                nodes.append(nodes_dict.get(nid) if nid is not None else None)

        x, y = data.get("position", (0.0, 0.0))
        rotation = float(data.get("rotation", 0.0))
        instance = cls(data["id"], *nodes, x=x, y=y, rotation=rotation)
        instance.set_params(data.get("params", {}))
        return instance
