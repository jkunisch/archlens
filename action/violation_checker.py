"""Check graph edges against .archlens.yml rules to detect violations.

Violation types:
1. FORBIDDEN_EDGE — edge matches a forbid rule → CI fail
2. GOD_NODE — node has too many incoming edges → warn or fail
3. CROSS_CLUSTER — too many cross-cluster edges in one diff → warn or fail

Glob matching uses the source_file metadata from edges (not node-ID string splits)
to determine package membership. This is critical per D-009 / spike findings.
"""

from __future__ import annotations

from fnmatch import fnmatch

from shared.schemas.config_schema import ArchLensConfig, ForbidRule, WarnRule
from shared.schemas.diff_schema import DiffResult
from shared.schemas.graph_schema import GraphEdge, GraphSnapshot
from shared.schemas.violation_schema import (
    Severity,
    Violation,
    ViolationReport,
    ViolationType,
)


def check_violations(
    diff: DiffResult,
    head_graph: GraphSnapshot,
    config: ArchLensConfig,
) -> ViolationReport:
    """Check graph diff and head graph against all configured rules.

    Args:
        diff: The filtered diff result (after noise filtering).
        head_graph: The full head graph snapshot (for god-node detection).
        config: Validated .archlens.yml configuration.

    Returns:
        ViolationReport containing all detected violations.
    """
    violations: list[Violation] = []

    # 1. Check forbid rules against new edges
    for edge in diff.added_edges:
        for rule in config.forbid:
            if _edge_matches_rule(edge, rule):
                violations.append(Violation(
                    violation_type=ViolationType.FORBIDDEN_EDGE,
                    severity=Severity.FAIL,
                    source_path=edge.source,
                    target_path=edge.target,
                    rule_message=rule.message,
                    detail=f"New edge {edge.source} → {edge.target} ({edge.edge_type}) "
                           f"matches forbid rule: {rule.from_glob} → {rule.to_glob}",
                ))

    # 2. Check warn rules against new edges
    for edge in diff.added_edges:
        for rule in config.warn:
            if _edge_matches_warn_rule(edge, rule):
                violations.append(Violation(
                    violation_type=ViolationType.FORBIDDEN_EDGE,
                    severity=Severity.WARN,
                    source_path=edge.source,
                    target_path=edge.target,
                    rule_message=rule.message,
                    detail=f"New edge {edge.source} → {edge.target} ({edge.edge_type}) "
                           f"matches warn rule: {rule.from_glob} → {rule.to_glob}",
                ))

    # 3. God node detection (on head graph)
    violations.extend(_check_god_nodes(head_graph, config))

    # 4. Cross-cluster edge count (on diff)
    violations.extend(_check_cross_cluster(diff, head_graph, config))

    return ViolationReport(
        violations=violations,
        graph_summary=diff.summary,
    )


def check_single_file(
    file_path: str,
    head_graph: GraphSnapshot,
    config: ArchLensConfig,
) -> list[Violation]:
    """Check violations for a single file — used by MCP check_boundaries tool.

    Returns violations where the file is either source or target of a forbidden edge.
    """
    violations: list[Violation] = []

    for edge in head_graph.edges:
        source_file = edge.metadata.get("source_file", "")
        # Check if this file is the source of a forbidden edge
        for rule in config.forbid:
            if (fnmatch(source_file, rule.from_glob) or fnmatch(edge.source, rule.from_glob)):
                if (fnmatch(edge.target, rule.to_glob)):
                    if _file_matches(file_path, source_file, edge.source):
                        violations.append(Violation(
                            violation_type=ViolationType.FORBIDDEN_EDGE,
                            severity=Severity.FAIL,
                            source_path=edge.source,
                            target_path=edge.target,
                            rule_message=rule.message,
                            detail=f"File {file_path} has forbidden import: "
                                   f"{edge.source} → {edge.target}",
                        ))

    return violations


def _file_matches(query_path: str, edge_source_file: str, edge_source_id: str) -> bool:
    """Check if a query file path matches the edge's source."""
    return (
        query_path in edge_source_file
        or query_path in edge_source_id
        or fnmatch(edge_source_file, f"*{query_path}*")
    )


def _edge_matches_rule(edge: GraphEdge, rule: ForbidRule) -> bool:
    """Check if an edge matches a forbid rule using glob patterns.

    Matches against both the edge source/target IDs and the source_file metadata
    for more accurate package detection.
    """
    source_file = edge.metadata.get("source_file", "")
    src_match = fnmatch(edge.source, rule.from_glob) or fnmatch(source_file, rule.from_glob)
    tgt_match = fnmatch(edge.target, rule.to_glob)
    return src_match and tgt_match


def _edge_matches_warn_rule(edge: GraphEdge, rule: WarnRule) -> bool:
    """Check if an edge matches a warn rule using glob patterns."""
    source_file = edge.metadata.get("source_file", "")
    src_match = fnmatch(edge.source, rule.from_glob) or fnmatch(source_file, rule.from_glob)
    tgt_match = fnmatch(edge.target, rule.to_glob)
    return src_match and tgt_match


def _check_god_nodes(
    graph: GraphSnapshot,
    config: ArchLensConfig,
) -> list[Violation]:
    """Detect nodes with too many incoming edges (god nodes)."""
    violations: list[Violation] = []
    incoming_count: dict[str, int] = {}

    for edge in graph.edges:
        incoming_count[edge.target] = incoming_count.get(edge.target, 0) + 1

    for node_id, count in incoming_count.items():
        if count >= config.thresholds.god_node_fail:
            violations.append(Violation(
                violation_type=ViolationType.GOD_NODE,
                severity=Severity.FAIL,
                source_path=node_id,
                detail=f"Node '{node_id}' has {count} incoming edges "
                       f"(threshold: {config.thresholds.god_node_fail})",
            ))
        elif count >= config.thresholds.god_node_warn:
            violations.append(Violation(
                violation_type=ViolationType.GOD_NODE,
                severity=Severity.WARN,
                source_path=node_id,
                detail=f"Node '{node_id}' has {count} incoming edges "
                       f"(warning threshold: {config.thresholds.god_node_warn})",
            ))

    return violations


def _check_cross_cluster(
    diff: DiffResult,
    graph: GraphSnapshot,
    config: ArchLensConfig,
) -> list[Violation]:
    """Check if too many new edges cross cluster boundaries."""
    violations: list[Violation] = []

    node_cluster = {n.id: n.cluster_id for n in graph.nodes}
    cross_cluster_count = 0

    for edge in diff.added_edges:
        src_cluster = node_cluster.get(edge.source, -1)
        tgt_cluster = node_cluster.get(edge.target, -1)
        if src_cluster != tgt_cluster and src_cluster != -1 and tgt_cluster != -1:
            cross_cluster_count += 1

    if cross_cluster_count >= config.thresholds.cross_cluster_fail:
        violations.append(Violation(
            violation_type=ViolationType.CROSS_CLUSTER,
            severity=Severity.FAIL,
            source_path="(multiple)",
            detail=f"{cross_cluster_count} new cross-cluster edges "
                   f"(threshold: {config.thresholds.cross_cluster_fail})",
        ))
    elif cross_cluster_count >= config.thresholds.cross_cluster_warn:
        violations.append(Violation(
            violation_type=ViolationType.CROSS_CLUSTER,
            severity=Severity.WARN,
            source_path="(multiple)",
            detail=f"{cross_cluster_count} new cross-cluster edges "
                   f"(warning threshold: {config.thresholds.cross_cluster_warn})",
        ))

    return violations
