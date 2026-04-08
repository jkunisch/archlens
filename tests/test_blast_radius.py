"""Tests for blast_radius.py."""

import pytest
from shared.schemas.graph_schema import GraphEdge, GraphNode, GraphSnapshot
from action.blast_radius import calculate_blast_radius, get_affected_nodes


def _make_edge(source: str, target: str) -> GraphEdge:
    return GraphEdge(source=source, target=target, edge_type="imports")


def _make_node(id: str) -> GraphNode:
    return GraphNode(id=id, name=id, type="module")


def test_simple_chain() -> None:
    """A→B→C: changing C affects B and A."""
    graph = GraphSnapshot(
        nodes=[_make_node("a"), _make_node("b"), _make_node("c")],
        edges=[_make_edge("a", "b"), _make_edge("b", "c")],
    )
    result = calculate_blast_radius(graph, ["c"])
    assert result["c"] == 2  # b and a are affected


def test_no_dependents() -> None:
    """Leaf node with no dependents has blast radius 0."""
    graph = GraphSnapshot(
        nodes=[_make_node("a"), _make_node("b")],
        edges=[_make_edge("a", "b")],
    )
    result = calculate_blast_radius(graph, ["a"])
    assert result["a"] == 0


def test_hub_node() -> None:
    """Hub node depended on by many has large blast radius."""
    nodes = [_make_node("hub")] + [_make_node(f"n{i}") for i in range(5)]
    edges = [_make_edge(f"n{i}", "hub") for i in range(5)]
    graph = GraphSnapshot(nodes=nodes, edges=edges)
    result = calculate_blast_radius(graph, ["hub"])
    assert result["hub"] == 5


def test_diamond_dependency() -> None:
    """Diamond: A→B, A→C, B→D, C→D. Changing D affects B, C, A."""
    graph = GraphSnapshot(
        nodes=[_make_node(x) for x in ["a", "b", "c", "d"]],
        edges=[
            _make_edge("a", "b"), _make_edge("a", "c"),
            _make_edge("b", "d"), _make_edge("c", "d"),
        ],
    )
    result = calculate_blast_radius(graph, ["d"])
    assert result["d"] == 3  # b, c, a


def test_get_affected_nodes_returns_set() -> None:
    """get_affected_nodes should return the actual node IDs."""
    graph = GraphSnapshot(
        nodes=[_make_node("a"), _make_node("b"), _make_node("c")],
        edges=[_make_edge("a", "b"), _make_edge("b", "c")],
    )
    affected = get_affected_nodes(graph, "c")
    assert affected == {"a", "b"}


def test_isolated_node() -> None:
    """Node with no edges has blast radius 0."""
    graph = GraphSnapshot(
        nodes=[_make_node("lonely")],
        edges=[],
    )
    result = calculate_blast_radius(graph, ["lonely"])
    assert result["lonely"] == 0
