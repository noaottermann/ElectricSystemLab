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