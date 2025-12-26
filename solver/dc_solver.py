import numpy as np
from model.components import Resistor, VoltageSourceDC, VoltageSourceAC
from model.node import Node, Wire

class DCSolver:
    """
    Solveur DC utilisant la Modified Nodal Analysis (MNA)
    """

    def solve(self, circuit):
        """
        Calcule les potentiels et les courants du circuit en régime continu (DC)
        """
        node_groups = self._group_connected_nodes(circuit)
        ground_group_id = None
        
        ground_node = circuit.get_ground_node()
        if ground_node:
            ground_group_id = node_groups[ground_node.id]
        else:
            if circuit.nodes:
                ground_node = list(circuit.nodes.values())[0]
                ground_node.is_ground = True
                ground_group_id = node_groups[ground_node.id]

        matrix_index = 0
        group_to_idx = {}
        unique_groups = set(node_groups.values())
        for gid in unique_groups:
            if gid != ground_group_id:
                group_to_idx[gid] = matrix_index
                matrix_index += 1
        num_v_vars = matrix_index

        voltage_sources = []
        for dipole in circuit.dipoles.values():
            if isinstance(dipole, VoltageSourceDC):
                voltage_sources.append(dipole)
        
        num_i_vars = len(voltage_sources)
        total_vars = num_v_vars + num_i_vars

        # Rien à résoudre si pas de variables
        if total_vars == 0:
            return

        A = np.zeros((total_vars, total_vars))
        Z = np.zeros(total_vars)

        for dipole in circuit.dipoles.values():
            idx_a = self._get_matrix_index(dipole.node_a, node_groups, group_to_idx, ground_group_id)
            idx_b = self._get_matrix_index(dipole.node_b, node_groups, group_to_idx, ground_group_id)
            if isinstance(dipole, Resistor):
                g = 1.0 / dipole.resistance
                # (+g sur diagonales, -g sur croisements)
                if idx_a is not None:
                    A[idx_a, idx_a] += g
                    if idx_b is not None:
                        A[idx_a, idx_b] -= g
                if idx_b is not None:
                    A[idx_b, idx_b] += g
                    if idx_a is not None:
                        A[idx_b, idx_a] -= g
            # elif isinstance(dipole, CurrentSource):

        current_var_offset = num_v_vars
        for i, v_src in enumerate(voltage_sources):
            idx_src = current_var_offset + i
            idx_a = self._get_matrix_index(v_src.node_a, node_groups, group_to_idx, ground_group_id)
            idx_b = self._get_matrix_index(v_src.node_b, node_groups, group_to_idx, ground_group_id)
            # Terme pour Va (coeff +1)
            if idx_a is not None:
                A[idx_src, idx_a] = 1
                A[idx_a, idx_src] = 1
            # Terme pour Vb (coeff -1)
            if idx_b is not None:
                A[idx_src, idx_b] = -1
                A[idx_b, idx_src] = -1
            Z[idx_src] = v_src.dc_voltage

        try:
            x = np.linalg.solve(A, Z)
        except np.linalg.LinAlgError:
            print("Erreur, matrice singulière (Circuit mal formé ou flottant)")
            return

        for node_id, node in circuit.nodes.items():
            group_id = node_groups[node_id]
            if group_id == ground_group_id:
                node.potential = 0.0
            else:
                idx = group_to_idx[group_id]
                node.potential = x[idx]

        for dipole in circuit.dipoles.values():
            if isinstance(dipole, Resistor):
                dipole.current = dipole.voltage / dipole.resistance

        for i, v_src in enumerate(voltage_sources):
            idx_src = current_var_offset + i
            v_src.current = -x[idx_src] 

    def _group_connected_nodes(self, circuit):
        """
        Parcourt les fils pour identifier les groupes de noeuds connectés
        Deux noeuds reliés par un fil auront le même group_id
        Retourne un dictionnaire {node_id: group_id}
        """
        parent = {node_id: node_id for node_id in circuit.nodes}
        def find(i):
            if parent[i] == i:
                return i
            parent[i] = find(parent[i])
            return parent[i]
        def union(i, j):
            root_i = find(i)
            root_j = find(j)
            if root_i != root_j:
                parent[root_i] = root_j
        for wire in circuit.wires.values():
            if wire.node_a and wire.node_b:
                union(wire.node_a.id, wire.node_b.id)
        groups = {}
        for node_id in circuit.nodes:
            groups[node_id] = find(node_id)
        return groups

    def _get_matrix_index(self, node, node_groups, group_to_idx, ground_group_id):
        if node is None:
            return None
        gid = node_groups[node.id]
        if gid == ground_group_id:
            return None
        return group_to_idx.get(gid)