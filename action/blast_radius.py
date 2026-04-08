"""Calculate blast radius for changed nodes via BFS reverse-traversal.

Blast radius answers: "If I change node X, how many other nodes are
transitively affected?" This helps agents and humans assess the impact
of a change before making it.

Algorithm: BFS from each changed node, following all incoming edges
(reverse direction), counting unique reachable nodes.
"""

from __future__ import annotations

from collections import deque

from shared.schemas.graph_schema import GraphSnapshot


def calculate_blast_radius(
    graph: GraphSnapshot,
    changed_node_ids: list[str],
) -> dict[str, int]:
    """Calculate blast radius for each changed node.

    Args:
        graph: The head graph snapshot containing all edges.
        changed_node_ids: Node IDs that were modified.

    Returns:
        Dict mapping node_id → number of transitively affected nodes.
    """
    # Build reverse adjacency list (who depends on X?)
    reverse_adj: dict[str, set[str]] = {}
    for edge in graph.edges:
        # edge.target is depended upon → edge.source depends on it
        # Reverse: from target, we can reach source (source is affected if target changes)
        if edge.target not in reverse_adj:
            reverse_adj[edge.target] = set()
        reverse_adj[edge.target].add(edge.source)

    result: dict[str, int] = {}
    for node_id in changed_node_ids:
        affected = _bfs_reverse(node_id, reverse_adj)
        result[node_id] = len(affected)

    return result


def get_affected_nodes(
    graph: GraphSnapshot,
    node_id: str,
) -> set[str]:
    """Get the set of all nodes transitively affected by changes to node_id.

    Useful for the MCP get_blast_radius tool to return detailed info.
    """
    reverse_adj: dict[str, set[str]] = {}
    for edge in graph.edges:
        if edge.target not in reverse_adj:
            reverse_adj[edge.target] = set()
        reverse_adj[edge.target].add(edge.source)

    return _bfs_reverse(node_id, reverse_adj)


def _bfs_reverse(start: str, reverse_adj: dict[str, set[str]]) -> set[str]:
    """BFS from start node following reverse edges. Returns all reachable nodes."""
    visited: set[str] = set()
    queue: deque[str] = deque([start])

    while queue:
        current = queue.popleft()
        for neighbor in reverse_adj.get(current, set()):
            if neighbor not in visited and neighbor != start:
                visited.add(neighbor)
                queue.append(neighbor)

    return visited
