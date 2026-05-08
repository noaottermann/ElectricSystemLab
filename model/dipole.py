from __future__ import annotations

from typing import Any, Optional


class Dipole:
    """Classe de base pour un composant electrique generique."""

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
        """Initialise un dipole generique."""
        self.id = int(dipole_id)
        self.name = name
        self.node_a = node_a
        self.node_b = node_b
        if self.node_a:
            self.node_a.add_connection(self)
        if self.node_b:
            self.node_b.add_connection(self)
        self.position = (float(x), float(y))
        self.rotation = float(rotation)
        self._current = 0.0

    @property
    def voltage(self) -> float:
        """Retourne la tension entre les bornes du dipole."""
        va = self.node_a.potential if self.node_a else 0.0
        vb = self.node_b.potential if self.node_b else 0.0
        return va - vb

    @property
    def current(self) -> float:
        """Retourne le courant traversant le dipole."""
        return self._current

    @current.setter
    def current(self, value: float) -> None:
        """Met a jour le courant du dipole."""
        self._current = float(value)

    @property
    def power(self) -> float:
        """Retourne la puissance instantanee du dipole."""
        return self.voltage * self.current

    def disconnect(self) -> None:
        """Detache le dipole de ses noeuds."""
        if self.node_a:
            self.node_a.remove_connection(self)
        if self.node_b:
            self.node_b.remove_connection(self)
        self.node_a = None
        self.node_b = None

    def to_dict(self) -> dict[str, object]:
        """Retourne une representation serialisable du dipole."""
        return {
            "type": self.__class__.__name__,
            "id": self.id,
            "name": self.name,
            "node_a_id": self.node_a.id if self.node_a else None,
            "node_b_id": self.node_b.id if self.node_b else None,
            "position": self.position,
            "rotation": self.rotation,
            "params": self.get_params()
        }

    def get_params(self) -> dict[str, object]:
        """Retourne les parametres specifiques du dipole."""
        return {}

    def get_state(self) -> Optional[str]:
        """Retourne l'etat courant (pour les dipoles a variantes)."""
        return None

    def get_state_options(self) -> list[tuple[str, str]]:
        """Retourne la liste des etats (valeur, libelle)."""
        return []

    @classmethod
    def from_dict(cls, data: dict, nodes_dict: dict) -> "Dipole":
        """Reconstruit un dipole a partir d'un dictionnaire."""
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
            rotation=data.get("rotation", 0.0)
        )
        instance.set_params(data.get("params", {}))
        return instance

    def set_params(self, params: dict) -> None:
        """Applique des parametres specifiques au dipole."""
        return None

    def set_state(self, value: str) -> None:
        """Met a jour l'etat du dipole si applicable."""
        return None


class StatefulDipole(Dipole):
    """Dipole avec variantes selectionnables via un etat."""

    def __init__(self, *args, state: str = "", state_options: Optional[list[tuple[str, str]]] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._state = str(state)
        self._state_options = state_options or []

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
        """Retourne une representation textuelle du dipole."""
        return (f"<{self.__class__.__name__} {self.name} (ID={self.id}) | "
                f"Nodes: {self.node_a.id if self.node_a else 'None'}-{self.node_b.id if self.node_b else 'None'} | "
                f"U={self.voltage:.2f}V I={self.current:.2f}A>")