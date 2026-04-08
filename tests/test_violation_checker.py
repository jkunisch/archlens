"""Tests for violation_checker.py."""

import pytest
from shared.schemas.config_schema import ArchLensConfig, ForbidRule, WarnRule, Thresholds
from shared.schemas.diff_schema import DiffResult
from shared.schemas.graph_schema import GraphEdge, GraphNode, GraphSnapshot
from shared.schemas.violation_schema import Severity, ViolationType
from action.violation_checker import check_violations, check_single_file


def _make_edge(source: str, target: str, edge_type: str = "imports",
               source_file: str = "") -> GraphEdge:
    return GraphEdge(
        source=source, target=target, edge_type=edge_type,
        metadata={"source_file": source_file},
    )


def _make_node(id: str, cluster_id: int = 0) -> GraphNode:
    return GraphNode(id=id, name=id, type="module", cluster_id=cluster_id)


def test_forbid_rule_detects_violation() -> None:
    """Forbidden edge should produce a FAIL violation."""
    config = ArchLensConfig(
        forbid=[ForbidRule(from_glob="frontend/*", to_glob="database/*",
                           message="No direct DB access")],
    )
    diff = DiffResult(
        added_edges=[_make_edge("frontend/views", "database/models",
                                source_file="frontend/views.py")],
    )
    graph = GraphSnapshot(
        nodes=[_make_node("frontend/views"), _make_node("database/models")],
        edges=diff.added_edges,
    )
    report = check_violations(diff, graph, config)
    assert report.has_failures
    assert report.failure_count == 1
    assert report.violations[0].severity == Severity.FAIL
    assert report.violations[0].violation_type == ViolationType.FORBIDDEN_EDGE


def test_forbid_rule_no_match() -> None:
    """Non-matching edge should not produce a violation."""
    config = ArchLensConfig(
        forbid=[ForbidRule(from_glob="frontend/*", to_glob="database/*")],
    )
    diff = DiffResult(
        added_edges=[_make_edge("api/routes", "services/auth")],
    )
    graph = GraphSnapshot(
        nodes=[_make_node("api/routes"), _make_node("services/auth")],
        edges=diff.added_edges,
    )
    report = check_violations(diff, graph, config)
    assert not report.has_failures
    assert report.failure_count == 0


def test_warn_rule_produces_warning() -> None:
    """Warn rule should produce a WARN violation, not FAIL."""
    config = ArchLensConfig(
        warn=[WarnRule(from_glob="api/*", to_glob="internal/*",
                       message="Avoid internal imports")],
    )
    diff = DiffResult(
        added_edges=[_make_edge("api/handler", "internal/utils")],
    )
    graph = GraphSnapshot(
        nodes=[_make_node("api/handler"), _make_node("internal/utils")],
        edges=diff.added_edges,
    )
    report = check_violations(diff, graph, config)
    assert not report.has_failures
    assert report.warning_count == 1
    assert report.violations[0].severity == Severity.WARN


def test_god_node_warn() -> None:
    """Node with many incoming edges should trigger god-node warning."""
    config = ArchLensConfig(thresholds=Thresholds(god_node_warn=3, god_node_fail=5))
    nodes = [_make_node("hub")] + [_make_node(f"n{i}") for i in range(4)]
    edges = [_make_edge(f"n{i}", "hub") for i in range(4)]
    graph = GraphSnapshot(nodes=nodes, edges=edges)
    report = check_violations(DiffResult(), graph, config)
    assert report.warning_count >= 1
    god_v = [v for v in report.violations if v.violation_type == ViolationType.GOD_NODE]
    assert len(god_v) == 1
    assert god_v[0].severity == Severity.WARN


def test_god_node_fail() -> None:
    """Node exceeding fail threshold should produce FAIL."""
    config = ArchLensConfig(thresholds=Thresholds(god_node_warn=2, god_node_fail=3))
    nodes = [_make_node("hub")] + [_make_node(f"n{i}") for i in range(5)]
    edges = [_make_edge(f"n{i}", "hub") for i in range(5)]
    graph = GraphSnapshot(nodes=nodes, edges=edges)
    report = check_violations(DiffResult(), graph, config)
    assert report.has_failures
    god_v = [v for v in report.violations if v.violation_type == ViolationType.GOD_NODE]
    assert any(v.severity == Severity.FAIL for v in god_v)


def test_cross_cluster_warn() -> None:
    """Too many cross-cluster edges should trigger warning."""
    config = ArchLensConfig(thresholds=Thresholds(cross_cluster_warn=2, cross_cluster_fail=5))
    nodes = [
        _make_node("a1", cluster_id=0), _make_node("a2", cluster_id=0),
        _make_node("b1", cluster_id=1), _make_node("b2", cluster_id=1),
        _make_node("b3", cluster_id=1),
    ]
    edges = [
        _make_edge("a1", "b1"), _make_edge("a2", "b2"), _make_edge("a1", "b3"),
    ]
    diff = DiffResult(added_edges=edges)
    graph = GraphSnapshot(nodes=nodes, edges=edges)
    report = check_violations(diff, graph, config)
    cc_v = [v for v in report.violations if v.violation_type == ViolationType.CROSS_CLUSTER]
    assert len(cc_v) == 1
    assert cc_v[0].severity == Severity.WARN
