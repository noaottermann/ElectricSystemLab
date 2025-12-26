class Node:
    """
    Représente un noeud électrique du circuit
    """

    def __init__(self, node_id, x=0.0, y=0.0, is_ground=False):
        """
        Initialise un nouveau noeud

        Args:
            node_id (int): Identifiant unique du noeud
            x (float): Coordonnée X sur la grille
            y (float): Coordonnée Y sur la grille
            is_ground (bool): Si True, ce noeud est la référence de masse (0V)
        """
        self.id = int(node_id)
        self.position = (float(x), float(y))
        self.is_ground = is_ground
        self._potential = 0.0
        self.connected_dipoles = []

    @property
    def potential(self):
        return self._potential

    @potential.setter
    def potential(self, value):
        if self.is_ground:
            self._potential = 0.0
        else:
            self._potential = float(value)

    def add_connection(self, dipole):
        if dipole not in self.connected_dipoles:
            self.connected_dipoles.append(dipole)

    def remove_connection(self, dipole):
        if dipole in self.connected_dipoles:
            self.connected_dipoles.remove(dipole)

    def to_dict(self):
        return {
            "id": self.id,
            "position": self.position,
            "is_ground": self.is_ground,
            "potential": self._potential
        }

    @classmethod
    def from_dict(cls, data):
        x, y = data.get("position", (0.0, 0.0))
        node = cls(
            node_id=data["id"],
            x=x,
            y=y,
            is_ground=data.get("is_ground", False)
        )
        if "potential" in data:
            node._potential = data["potential"]
        return node

    def __repr__(self):
        state = "GND" if self.is_ground else f"{self._potential:.2f}V"
        return f"<Node {self.id} | Pos={self.position} | {state}>"
    
    
class Wire:
    """
    Représente un fil électrique idéal
    """

    def __init__(self, wire_id, node_a, node_b, color="#000000"):
        """
        Initialise un fil.

        Args:
            wire_id (int): Identifiant unique du fil
            node_a (Node): Le nœud de départ
            node_b (Node): Le nœud d'arrivée
            color (str): Couleur du fil (code hexadécimal)
        """
        self.id = int(wire_id)
        self.node_a = node_a
        self.node_b = node_b
        self.color = color

    def disconnect(self):
        self.node_a = None
        self.node_b = None

    def to_dict(self):
        return {
            "id": self.id,
            "node_a_id": self.node_a.id if self.node_a else None,
            "node_b_id": self.node_b.id if self.node_b else None,
            "color": self.color
        }

    @classmethod
    def from_dict(cls, data, nodes_dict):
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

    def __repr__(self):
        id_a = self.node_a.id if self.node_a is not None else None
        id_b = self.node_b.id if self.node_b is not None else None
        return f"<Wire {self.id} | Nodes: {id_a}-{id_b}>"