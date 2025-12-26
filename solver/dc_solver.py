import numpy as np
from model.components import Resistor, VoltageSourceDC

class DCSolver:
    def solve(self, circuit):
        # Groupement des noeuds
        node_groups = self._group_connected_nodes(circuit)
        
        # Gestion de la masse
        ground_node = circuit.get_ground_node()
        ground_group_id = None
        if ground_node:
            ground_group_id = node_groups[ground_node.id]
        else:
            if circuit.nodes:
                first_node = list(circuit.nodes.values())[0]
                first_node.is_ground = True
                ground_node = first_node
                ground_group_id = node_groups[first_node.id]
            else:
                print("Circuit vide")
                return

        # Mapping Groupe -> Index Matrice
        matrix_index = 0
        group_to_idx = {}
        unique_groups = set(node_groups.values())
        for gid in unique_groups:
            if gid != ground_group_id:
                group_to_idx[gid] = matrix_index
                matrix_index += 1
        num_v_vars = matrix_index

        # Variables de courant pour sources de tension
        voltage_sources = []
        for dipole in circuit.dipoles.values():
            if isinstance(dipole, VoltageSourceDC):
                voltage_sources.append(dipole)
        num_i_vars = len(voltage_sources)
        total_vars = num_v_vars + num_i_vars
        if total_vars == 0:
            return
        
        # Matrices
        A = np.zeros((total_vars, total_vars))
        Z = np.zeros(total_vars)

        # Remplissage Passifs
        for dipole in circuit.dipoles.values():
            idx_a = self._get_matrix_index(dipole.node_a, node_groups, group_to_idx, ground_group_id)
            idx_b = self._get_matrix_index(dipole.node_b, node_groups, group_to_idx, ground_group_id)
            if isinstance(dipole, Resistor):
                g = 1.0 / dipole.resistance
                if idx_a is not None:
                    A[idx_a, idx_a] += g
                    if idx_b is not None:
                        A[idx_a, idx_b] -= g
                if idx_b is not None:
                    A[idx_b, idx_b] += g
                    if idx_a is not None:
                        A[idx_b, idx_a] -= g

        # Remplissage Sources
        current_var_offset = num_v_vars
        for i, v_src in enumerate(voltage_sources):
            idx_src = current_var_offset + i
            idx_a = self._get_matrix_index(v_src.node_a, node_groups, group_to_idx, ground_group_id)
            idx_b = self._get_matrix_index(v_src.node_b, node_groups, group_to_idx, ground_group_id)
            if idx_a is not None:
                A[idx_src, idx_a] = 1
                A[idx_a, idx_src] = 1
            if idx_b is not None:
                A[idx_src, idx_b] = -1
                A[idx_b, idx_src] = -1
            Z[idx_src] = v_src.dc_voltage

        # Résolution
        x = np.linalg.solve(A, Z)

        # Distribution des résultats
        for node_id, node in circuit.nodes.items():
            group_id = node_groups[node_id]
            if group_id == ground_group_id:
                node.potential = 0.0
            else:
                idx = group_to_idx.get(group_id)
                if idx is not None:
                    new_pot = float(x[idx])
                    node.potential = new_pot

        # Mise à jour des courants
        for dipole in circuit.dipoles.values():
            if isinstance(dipole, Resistor):
                dipole.current = dipole.voltage / dipole.resistance
        for i, v_src in enumerate(voltage_sources):
            idx_src = current_var_offset + i
            v_src.current = -float(x[idx_src])

    def _group_connected_nodes(self, circuit):
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

        return {node_id: find(node_id) for node_id in circuit.nodes}

    def _get_matrix_index(self, node, node_groups, group_to_idx, ground_group_id):
        if node is None:
            return None
        gid = node_groups[node.id]
        if gid == ground_group_id:
            return None
        return group_to_idx.get(gid)