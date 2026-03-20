from __future__ import annotations

from typing import Optional

import numpy as np

from model.components import Resistor, VoltageSourceDC

class DCSolver:
    """Solveur DC base sur l'analyse nodale."""

    def solve(self, circuit) -> None:
        """Resout un circuit continu par analyse nodale avec sources de tension."""
        if circuit is None:
            print("Circuit invalide")
            return
        # Regroupe les noeuds connectes par des fils
        node_groups = self._group_connected_nodes(circuit)
        
        # Gestion de la masse
        ground_node = circuit.get_ground_node()
        ground_group_id: Optional[int] = None
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

        # Correspondance groupe vers indice de matrice
        group_to_idx = self._build_group_index(node_groups, ground_group_id)
        num_v_vars = len(group_to_idx)

        # Variables de courant des sources de tension
        voltage_sources = self._collect_voltage_sources(circuit)
        num_i_vars = len(voltage_sources)
        total_vars = num_v_vars + num_i_vars
        if total_vars == 0:
            return
        
        # Matrices
        A = np.zeros((total_vars, total_vars))
        Z = np.zeros(total_vars)

        # Remplit les elements passifs
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

        # Remplit les sources de tension
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

        # Resolution
        try:
            x = np.linalg.solve(A, Z)
        except np.linalg.LinAlgError:
            print("Erreur de resolution: matrice singuliere")
            return

        # Repartit les resultats
        for node_id, node in circuit.nodes.items():
            group_id = node_groups[node_id]
            if group_id == ground_group_id:
                node.potential = 0.0
            else:
                idx = group_to_idx.get(group_id)
                if idx is not None:
                    new_pot = float(x[idx])
                    node.potential = new_pot

        # Met a jour les courants
        for dipole in circuit.dipoles.values():
            if isinstance(dipole, Resistor):
                dipole.current = dipole.voltage / dipole.resistance
        for i, v_src in enumerate(voltage_sources):
            idx_src = current_var_offset + i
            v_src.current = -float(x[idx_src])

    def _collect_voltage_sources(self, circuit) -> list[VoltageSourceDC]:
        """Retourne les sources de tension continues du circuit."""
        voltage_sources = []
        for dipole in circuit.dipoles.values():
            if isinstance(dipole, VoltageSourceDC):
                voltage_sources.append(dipole)
        return voltage_sources

    def _build_group_index(self, node_groups: dict[int, int], ground_group_id: Optional[int]) -> dict[int, int]:
        """Associe chaque groupe de noeuds a un indice de matrice."""
        group_to_idx: dict[int, int] = {}
        next_index = 0
        for gid in set(node_groups.values()):
            if gid == ground_group_id:
                continue
            group_to_idx[gid] = next_index
            next_index += 1
        return group_to_idx

    def _group_connected_nodes(self, circuit) -> dict[int, int]:
        """Utilise Union-Find pour regrouper les noeuds relies par des fils."""
        parent = {node_id: node_id for node_id in circuit.nodes}

        def find(node_id: int) -> int:
            """Retourne la racine d'un noeud avec compression de chemin."""
            if parent[node_id] == node_id:
                return node_id
            parent[node_id] = find(parent[node_id])
            return parent[node_id]

        def union(left_id: int, right_id: int) -> None:
            """Fusionne deux ensembles de noeuds."""
            root_i = find(left_id)
            root_j = find(right_id)
            if root_i != root_j:
                parent[root_i] = root_j

        for wire in circuit.wires.values():
            if wire.node_a and wire.node_b:
                union(wire.node_a.id, wire.node_b.id)

        return {node_id: find(node_id) for node_id in circuit.nodes}

    def _get_matrix_index(
        self,
        node,
        node_groups: dict[int, int],
        group_to_idx: dict[int, int],
        ground_group_id: Optional[int],
    ) -> Optional[int]:
        """Associe un noeud a son indice de matrice en ignorant le groupe de masse."""
        if node is None:
            return None
        gid = node_groups[node.id]
        if gid == ground_group_id:
            return None
        return group_to_idx.get(gid)