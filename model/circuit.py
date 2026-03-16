import json
from .node import Node
from .wire import Wire
class Circuit:
    """Classe principale representant le circuit electrique complet"""

    def __init__(self):
        """Initialise un circuit vide"""
        self.nodes = {} 
        self.dipoles = {}
        self.wires = {}
        self._next_node_id = 1
        self._next_dipole_id = 1
        self._next_wire_id = 1

    # Gestion des noeuds

    def create_node(self, x, y, is_ground=False):
        node_id = self._next_node_id
        self._next_node_id += 1
        node = Node(node_id, x, y, is_ground)
        self.nodes[node_id] = node
        return node

    def remove_node(self, node_id):
        node_id = int(node_id)
        if node_id in self.nodes:
            del self.nodes[node_id]

    def _rebuild_node_connections(self):
        for node in self.nodes.values():
            node.connected_dipoles = []

        for dipole in self.dipoles.values():
            if dipole.node_a is not None and dipole.node_a.id in self.nodes:
                dipole.node_a.add_connection(dipole)
            if dipole.node_b is not None and dipole.node_b.id in self.nodes:
                dipole.node_b.add_connection(dipole)

    def _merge_node_into_keeper(self, keeper, node_to_merge):
        if keeper is None or node_to_merge is None or keeper is node_to_merge:
            return False

        changed = False

        for dipole in self.dipoles.values():
            if dipole.node_a is node_to_merge:
                dipole.node_a = keeper
                changed = True
            if dipole.node_b is node_to_merge:
                dipole.node_b = keeper
                changed = True

        for wire in self.wires.values():
            if wire.node_a is node_to_merge:
                wire.node_a = keeper
                changed = True
            if wire.node_b is node_to_merge:
                wire.node_b = keeper
                changed = True

        if node_to_merge.is_ground:
            keeper.is_ground = True
            keeper._potential = 0.0

        if node_to_merge.id in self.nodes:
            del self.nodes[node_to_merge.id]
            changed = True

        return changed

    def merge_nodes(self, node_a, node_b):
        if node_a is None:
            return node_b
        if node_b is None:
            return node_a
        if node_a is node_b:
            return node_a

        keeper, node_to_merge = (node_a, node_b) if node_a.id <= node_b.id else (node_b, node_a)

        if keeper.id not in self.nodes:
            self.nodes[keeper.id] = keeper

        changed = self._merge_node_into_keeper(keeper, node_to_merge)
        if changed:
            self._rebuild_node_connections()

        return keeper

    def merge_overlapping_nodes(self, decimals=6):
        if len(self.nodes) < 2:
            return False

        groups = {}
        for node in self.nodes.values():
            x, y = node.position
            key = (round(float(x), decimals), round(float(y), decimals))
            if key not in groups:
                groups[key] = []
            groups[key].append(node)

        changed = False
        for grouped_nodes in groups.values():
            if len(grouped_nodes) < 2:
                continue

            grouped_nodes.sort(key=lambda n: n.id)
            keeper = grouped_nodes[0]
            for node_to_merge in grouped_nodes[1:]:
                if self._merge_node_into_keeper(keeper, node_to_merge):
                    changed = True

        if changed:
            self._rebuild_node_connections()

        return changed

    def get_node_at(self, x, y, tolerance=10.0):
        # Priorité aux noeuds des dipôles
        dipole_nodes = set()
        for dipole in self.dipoles.values():
            if dipole.node_a is not None:
                dipole_nodes.add(dipole.node_a)
            if dipole.node_b is not None:
                dipole_nodes.add(dipole.node_b)

        # Noeuds de dipôles
        for node in dipole_nodes:
            nx, ny = node.position
            if (nx - x)**2 + (ny - y)**2 <= tolerance**2:
                return node

        # Autres noeuds
        for node in self.nodes.values():
            if node in dipole_nodes:
                continue
            nx, ny = node.position
            if (nx - x)**2 + (ny - y)**2 <= tolerance**2:
                return node
        return None
    
    # Gestion des fils

    def create_wire(self, node_a, node_b):
        if node_a.id not in self.nodes or node_b.id not in self.nodes:
            raise ValueError("Impossible de créer un fil : noeuds inconnus.")
        wire_id = self._next_wire_id
        self._next_wire_id += 1
        wire = Wire(wire_id, node_a, node_b)
        self.wires[wire_id] = wire
        return wire
    
    def remove_wire(self, wire_id):
        wire_id = int(wire_id)
        if wire_id in self.wires:
            self.wires[wire_id].disconnect()
            del self.wires[wire_id]

    # Gestion des dipoles

    def add_dipole(self, dipole):
        if dipole.node_a and dipole.node_a.id not in self.nodes:
            raise ValueError(f"Le Node A ({dipole.node_a.id}) n'existe pas dans ce circuit.")
        if dipole.node_b and dipole.node_b.id not in self.nodes:
            raise ValueError(f"Le Node B ({dipole.node_b.id}) n'existe pas dans ce circuit.")
        self.dipoles[dipole.id] = dipole
        if dipole.id >= self._next_dipole_id:
            self._next_dipole_id = dipole.id + 1

    def remove_dipole(self, dipole_id):
        dipole_id = int(dipole_id)
        if dipole_id in self.dipoles:
            self.dipoles[dipole_id].disconnect()
            del self.dipoles[dipole_id]

    def get_next_dipole_id(self):
        return self._next_dipole_id

    # Aides pour le solveur

    def get_ground_node(self):
        for node in self.nodes.values():
            if node.is_ground:
                return node
        return None

    def reset_simulation(self):
        for node in self.nodes.values():
            node.potential = 0.0
        for dipole in self.dipoles.values():
            dipole.current = 0.0

    def clear(self):
        self.nodes.clear()
        self.dipoles.clear()
        self.wires.clear()
        self._next_node_id = 1
        self._next_dipole_id = 1
        self._next_wire_id = 1

    # Sauvegarde / Chargement (JSON)

    def to_json(self):
        data = {
            "version": "1.0",
            "next_node_id": self._next_node_id,
            "next_dipole_id": self._next_dipole_id,
            "next_wire_id": self._next_wire_id,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "wires": [w.to_dict() for w in self.wires.values()],
            "dipoles": [d.to_dict() for d in self.dipoles.values()]
        }
        return json.dumps(data, indent=4)

    def load_from_json(self, json_str, component_classes):
        self.clear()
        data = json.loads(json_str)
        self._next_node_id = data.get("next_node_id", 1)
        self._next_dipole_id = data.get("next_dipole_id", 1)
        self._next_wire_id = data.get("next_wire_id", 1)
        for node_data in data["nodes"]:
            node = Node.from_dict(node_data)
            self.nodes[node.id] = node
        if "wires" in data:
            for wire_data in data["wires"]:
                wire = Wire.from_dict(wire_data, self.nodes)
                if wire:
                    self.wires[wire.id] = wire
        for dipole_data in data["dipoles"]:
            dtype = dipole_data["type"]
            if dtype in component_classes:
                cls = component_classes[dtype]
                dipole = cls.from_dict(dipole_data, self.nodes)
                self.dipoles[dipole.id] = dipole
            else:
                print(f"Attention: Type de composant inconnu '{dtype}', ignoré.")

    def __repr__(self):
        return (f"<Circuit: {len(self.nodes)} nodes, "
                f"{len(self.wires)} wires, {len(self.dipoles)} dipoles>")