"""Tests for edge_noise_filter.py."""

import pytest
from shared.schemas.config_schema import ArchLensConfig, ForbidRule, WarnRule
from shared.schemas.diff_schema import DiffResult
from shared.schemas.graph_schema import GraphEdge, GraphNode, GraphSnapshot
from shared.constants.edge_types import EXTRACTED, INFERRED
from action.edge_noise_filter import filter_noise, MAX_EDGES


def _make_edge(source: str, target: str, confidence: str = EXTRACTED,
               source_file: str = "") -> GraphEdge:
    return GraphEdge(
        source=source, target=target, edge_type="imports",
        confidence=confidence,
        metadata={"source_file": source_file},
    )


def _make_node(id: str, cluster_id: int = 0) -> GraphNode:
    return GraphNode(id=id, name=id, type="module", cluster_id=cluster_id)


def test_cross_cluster_edge_kept() -> None:
    """Edges crossing cluster boundaries should be kept."""
    nodes = [_make_node("a", cluster_id=0), _make_node("b", cluster_id=1)]
    edge = _make_edge("a", "b")
    diff = DiffResult(added_edges=[edge])
    graph = GraphSnapshot(nodes=nodes, edges=[edge])
    config = ArchLensConfig()
    result = filter_noise(diff, graph, config)
    assert len(result.added_edges) == 1


def test_intra_cluster_edge_filtered() -> None:
    """Edges within the same cluster should be filtered out."""
    nodes = [_make_node("a", cluster_id=0), _make_node("b", cluster_id=0)]
    edge = _make_edge("a", "b")
    diff = DiffResult(added_edges=[edge])
    graph = GraphSnapshot(nodes=nodes, edges=[edge])
    config = ArchLensConfig()
    result = filter_noise(diff, graph, config)
    assert len(result.added_edges) == 0


def test_rule_match_kept_even_if_intra_cluster() -> None:
    """Edges matching a forbid rule should be kept even if intra-cluster."""
    nodes = [_make_node("frontend/x", cluster_id=0), _make_node("database/y", cluster_id=0)]
    edge = _make_edge("frontend/x", "database/y")
    diff = DiffResult(added_edges=[edge])
    graph = GraphSnapshot(nodes=nodes, edges=[edge])
    config = ArchLensConfig(
        forbid=[ForbidRule(from_glob="frontend/*", to_glob="database/*")],
    )
    result = filter_noise(diff, graph, config)
    assert len(result.added_edges) == 1


def test_inferred_edge_filtered() -> None:
    """INFERRED edges should be filtered out (Phase 1: EXTRACTED only)."""
    nodes = [_make_node("a", cluster_id=0), _make_node("b", cluster_id=1)]
    edge = _make_edge("a", "b", confidence=INFERRED)
    diff = DiffResult(added_edges=[edge])
    graph = GraphSnapshot(nodes=nodes, edges=[edge])
    config = ArchLensConfig()
    result = filter_noise(diff, graph, config)
    assert len(result.added_edges) == 0


def test_inferred_edge_kept_if_matches_rule() -> None:
    """INFERRED edge matching a rule should still be surfaced."""
    nodes = [_make_node("frontend/x", cluster_id=0), _make_node("database/y", cluster_id=1)]
    edge = _make_edge("frontend/x", "database/y", confidence=INFERRED)
    diff = DiffResult(added_edges=[edge])
    graph = GraphSnapshot(nodes=nodes, edges=[edge])
    config = ArchLensConfig(
        forbid=[ForbidRule(from_glob="frontend/*", to_glob="database/*")],
    )
    result = filter_noise(diff, graph, config)
    assert len(result.added_edges) == 1


def test_ignored_path_filtered() -> None:
    """Edges with ignored source/target should be filtered."""
    nodes = [_make_node("vendor/lib", cluster_id=0), _make_node("app/x", cluster_id=1)]
    edge = _make_edge("vendor/lib", "app/x")
    diff = DiffResult(added_edges=[edge])
    graph = GraphSnapshot(nodes=nodes, edges=[edge])
    config = ArchLensConfig(ignore=["vendor/*"])
    result = filter_noise(diff, graph, config)
    assert len(result.added_edges) == 0


def test_hard_cap_50() -> None:
    """Output should be capped at MAX_EDGES edges."""
    nodes = [_make_node(f"a{i}", cluster_id=0) for i in range(60)]
    nodes += [_make_node(f"b{i}", cluster_id=1) for i in range(60)]
    edges = [_make_edge(f"a{i}", f"b{i}") for i in range(60)]
    diff = DiffResult(added_edges=edges)
    graph = GraphSnapshot(nodes=nodes, edges=edges)
    config = ArchLensConfig()
    result = filter_noise(diff, graph, config)
    assert len(result.added_edges) <= MAX_EDGES
