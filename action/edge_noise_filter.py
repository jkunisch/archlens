"""Filter trivial edges from graph diffs before violation analysis.

Without filtering, a Graphify diff can produce dozens of irrelevant edges
(re-exports, type hints, test helpers). This filter reduces noise to only
actionable signals.

Filtering strategy (in priority order):
1. ALWAYS surface: edges matching forbid/warn rules
2. ALWAYS surface: edges crossing Leiden cluster boundaries
3. FILTER OUT: edges within the same cluster (intra-cluster is expected)
4. FILTER OUT: edges with confidence=INFERRED (only EXTRACTED in Phase 1)
5. FILTER OUT: edges where source or target is in .archlens.yml ignore list
6. Hard cap: max 50 edges to prevent comment/output spam
"""

from __future__ import annotations

from fnmatch import fnmatch

from shared.schemas.config_schema import ArchLensConfig
from shared.schemas.diff_schema import DiffResult
from shared.schemas.graph_schema import GraphEdge, GraphSnapshot
from shared.constants.edge_types import EXTRACTED

MAX_EDGES = 50


def filter_noise(
    diff: DiffResult,
    head_graph: GraphSnapshot,
    config: ArchLensConfig,
) -> DiffResult:
    """Return a filtered DiffResult containing only actionable edges.

    Guarantees:
    - All edges matching forbid/warn rules are included (regardless of cluster)
    - All cross-cluster edges are included
    - Intra-cluster / same-module noise is excluded
    - INFERRED edges are excluded (Phase 1: only AST-extracted edges)
    - Max 50 edges in result (hard cap)
    """
    node_cluster: dict[str, int] = {n.id: n.cluster_id for n in head_graph.nodes}

    def is_cross_cluster(edge: GraphEdge) -> bool:
        src_cluster = node_cluster.get(edge.source, -1)
        tgt_cluster = node_cluster.get(edge.target, -1)
        return src_cluster != tgt_cluster and src_cluster != -1 and tgt_cluster != -1

    def matches_any_rule(edge: GraphEdge) -> bool:
        all_rules = list(config.forbid) + list(config.warn)
        source_file = edge.metadata.get("source_file", "")
        return any(
            (fnmatch(edge.source, r.from_glob) or fnmatch(source_file, r.from_glob))
            and fnmatch(edge.target, r.to_glob)
            for r in all_rules
        )

    def is_ignored(edge: GraphEdge) -> bool:
        source_file = edge.metadata.get("source_file", "")
        return any(
            fnmatch(edge.source, p)
            or fnmatch(edge.target, p)
            or fnmatch(source_file, p)
            for p in config.ignore
        )

    # Rule-matching edges first (highest priority), then cross-cluster
    rule_matches = []
    cross_cluster = []
    for e in diff.added_edges:
        if is_ignored(e):
            continue
        if e.confidence != EXTRACTED:
            # Still include if it matches a rule
            if matches_any_rule(e):
                rule_matches.append(e)
            continue
        if matches_any_rule(e):
            rule_matches.append(e)
        elif is_cross_cluster(e):
            cross_cluster.append(e)

    # Deduplicate (rule matches take priority)
    seen = {(e.source, e.target, e.edge_type) for e in rule_matches}
    unique_cross = [e for e in cross_cluster if (e.source, e.target, e.edge_type) not in seen]

    filtered_added = (rule_matches + unique_cross)[:MAX_EDGES]

    return DiffResult(
        added_edges=filtered_added,
        removed_edges=diff.removed_edges,
        added_nodes=diff.added_nodes,
        removed_nodes=diff.removed_nodes,
        cluster_changes=diff.cluster_changes,
    )
