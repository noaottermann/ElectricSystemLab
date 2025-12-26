import math

class Dipole:
    """
    Classe de base représentant un composant électrique générique
    """

    def __init__(self, dipole_id, name, node_a, node_b, x=0.0, y=0.0, rotation=0.0):
        """
        Initialise un dipôle générique.

        Args:
            dipole_id (int): Identifiant unique du composant
            name (str): Nom affiché
            node_a (Node): Le premier noeud de connexion (Pôle + conventionnel)
            node_b (Node): Le second noeud de connexion (Pôle - conventionnel)
            x (float): Coordonnée X du centre du composant
            y (float): Coordonnée Y du centre du composant
            rotation (float): Angle de rotation en degrés
        """
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
    def voltage(self):
        va = self.node_a.potential if self.node_a else 0.0
        vb = self.node_b.potential if self.node_b else 0.0
        return va - vb

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, value):
        self._current = float(value)

    @property
    def power(self):
        return self.voltage * self.current

    def disconnect(self):
        if self.node_a:
            self.node_a.remove_connection(self)
        if self.node_b:
            self.node_b.remove_connection(self)
        self.node_a = None
        self.node_b = None

    def to_dict(self):
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

    def get_params(self):
        return {}

    @classmethod
    def from_dict(cls, data, nodes_dict):
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

    def set_params(self, params):
        pass

    def __repr__(self):
        return (f"<{self.__class__.__name__} {self.name} (ID={self.id}) | "
                f"Nodes: {self.node_a.id if self.node_a else 'None'}-{self.node_b.id if self.node_b else 'None'} | "
                f"U={self.voltage:.2f}V I={self.current:.2f}A>")