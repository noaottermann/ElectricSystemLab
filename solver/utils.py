from __future__ import annotations

from typing import Optional


def group_connected_nodes(circuit) -> dict[int, int]:
	"""Regroupe les noeuds relies par des fils via Union-Find."""
	parent = {node_id: node_id for node_id in circuit.nodes}

	def find(node_id: int) -> int:
		if parent[node_id] == node_id:
			return node_id
		parent[node_id] = find(parent[node_id])
		return parent[node_id]

	def union(left_id: int, right_id: int) -> None:
		root_left = find(left_id)
		root_right = find(right_id)
		if root_left != root_right:
			parent[root_left] = root_right

	for wire in circuit.wires.values():
		if wire.node_a and wire.node_b:
			union(wire.node_a.id, wire.node_b.id)

	return {node_id: find(node_id) for node_id in circuit.nodes}


def build_group_index(
	node_groups: dict[int, int], ground_group_id: Optional[int]
) -> dict[int, int]:
	"""Associe chaque groupe hors masse a un indice de matrice."""
	group_to_idx: dict[int, int] = {}
	next_index = 0
	for gid in set(node_groups.values()):
		if gid == ground_group_id:
			continue
		group_to_idx[gid] = next_index
		next_index += 1
	return group_to_idx


def matrix_index_for_node(
	node,
	node_groups: dict[int, int],
	group_to_idx: dict[int, int],
	ground_group_id: Optional[int],
) -> Optional[int]:
	"""Retourne l'indice de matrice d'un noeud (None pour masse)."""
	if node is None:
		return None
	gid = node_groups[node.id]
	if gid == ground_group_id:
		return None
	return group_to_idx.get(gid)
