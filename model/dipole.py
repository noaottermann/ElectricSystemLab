from __future__ import annotations

from typing import Any, Optional
from .component import Component


class Dipole(Component):
    """Classe de base pour un composant électrique à 2 bornes."""

    def __init__(
        self,
        dipole_id: int,
        name: str,
        node_a: Optional[Any],
        node_b: Optional[Any],
        x: float = 0.0,
        y: float = 0.0,
        rotation: float = 0.0,
    ) -> None:
        """Initialise un dipôle (composant à 2 bornes)."""
        super().__init__(dipole_id, name, node_a, node_b, x=x, y=y, rotation=rotation)

    @property
    def node_a(self) -> Optional[Any]:
        """Premier nœud (borne positive/entrée)."""
        return self.nodes[0] if len(self.nodes) > 0 else None

    @node_a.setter
    def node_a(self, value: Optional[Any]) -> None:
        if len(self.nodes) > 0:
            self.nodes[0] = value
        else:
            self.nodes.append(value)

    @property
    def node_b(self) -> Optional[Any]:
        """Deuxième nœud (borne négative/sortie)."""
        return self.nodes[1] if len(self.nodes) > 1 else None

    @node_b.setter
    def node_b(self, value: Optional[Any]) -> None:
        if len(self.nodes) > 1:
            self.nodes[1] = value
        elif len(self.nodes) == 1:
            self.nodes.append(value)
        else:
            self.nodes.extend([None, value])

    @classmethod
    def from_dict(cls, data: dict, nodes_dict: dict) -> "Dipole":
        """Reconstruit un dipôle à partir d'un dictionnaire."""
        node_a_id = data.get("node_a_id")
        node_b_id = data.get("node_b_id")
        node_a = nodes_dict.get(node_a_id) if node_a_id is not None else None
        node_b = nodes_dict.get(node_b_id) if node_b_id is not None else None
        x, y = data.get("position", (0.0, 0.0))
        instance = cls(
            dipole_id=data["id"],
            name=data["name"],
            node_a=node_a,
            node_b=node_b,
            x=x,
            y=y,
            rotation=data.get("rotation", 0.0),
        )
        instance.set_params(data.get("params", {}))
        return instance


class StatefulDipole(Dipole):
    """Dipôle avec variantes sélectionnables via un état."""

    def __init__(self, *args, state: str = "", state_options: Optional[list[tuple[str, str]]] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._state = str(state)
        self._state_options = state_options or []

    @property
    def state(self) -> str:
        """Retourne l'état actif du dipôle."""
        return self._state

    @state.setter
    def state(self, value: str) -> None:
        """Définit l'état actif du dipôle."""
        self.set_state(value)

    def get_state(self) -> Optional[str]:
        return self._state

    def get_state_options(self) -> list[tuple[str, str]]:
        return list(self._state_options)

    def set_state(self, value: str) -> None:
        self._state = str(value)

    def get_params(self) -> dict[str, object]:
        params = super().get_params()
        params["state"] = self._state
        return params

    def set_params(self, params: dict) -> None:
        self._state = str(params.get("state", self._state))

    def __repr__(self) -> str:
        """Retourne une représentation textuelle du dipôle."""
        return (f"<{self.__class__.__name__} {self.name} (ID={self.id}) | "
                f"Nodes: {self.node_a.id if self.node_a else 'None'}-{self.node_b.id if self.node_b else 'None'} | "
                f"U={self.voltage:.2f}V I={self.current:.2f}A>")