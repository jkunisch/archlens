"""Abstraction layer over Graphify. All Graphify calls go through here.

CRITICAL (D-009): Uses extract(collect_files(path)) directly.
Do NOT use build_from_json() or graphify.analyze.graph_diff() — they cause
an ID mismatch that silently drops import edges from the graph.

Field names verified from spike/SPIKE_REPORT.md and spike/inspect_imports.py:
- Extraction output uses "nodes" for nodes and "edges" for edges
- Edge fields: source, target, relation, source_file, confidence
- Node fields: id, label (not "name"), source_file
- extract() takes a files list from collect_files(), not a path directly
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from shared.schemas.diff_schema import DiffResult
from shared.schemas.graph_schema import GraphEdge, GraphNode, GraphSnapshot
from shared.constants.edge_types import EXTRACTED


def _try_import_graphify() -> tuple[Any, Any]:
    """Import Graphify with a clear error if not installed."""
    try:
        from graphify.extract import extract, collect_files
        return extract, collect_files
    except ImportError as exc:
        raise ImportError(
            "graphifyy is not installed. Install with: pip install graphifyy"
        ) from exc


class GraphifyAdapter:
    """Wraps Graphify's raw extract() output into our stable GraphSnapshot schema.

    All field name mapping happens in _normalize(). If Graphify changes
    its output format, only _normalize() needs updating.

    Usage:
        adapter = GraphifyAdapter()
        snapshot = adapter.build_graph(Path("./my-repo"))
        diff = adapter.build_diff(base_snapshot, head_snapshot)
    """

    def build_graph(self, repo_path: Path) -> GraphSnapshot:
        """Run Graphify AST pass and return normalized GraphSnapshot.

        Args:
            repo_path: Absolute path to the repository root to analyze.

        Returns:
            GraphSnapshot with all nodes, edges from the AST extraction.
        """
        extract_fn, collect_files_fn = _try_import_graphify()
        files = collect_files_fn(repo_path)
        raw = extract_fn(files)
        return self._normalize(raw, repo_path)

    def build_diff(self, base: GraphSnapshot, head: GraphSnapshot) -> DiffResult:
        """Compute diff between two snapshots using set arithmetic.

        Uses (source, target, edge_type) as the stable key.
        Runs in O(n) via dict lookups, not O(n²).

        IMPORTANT: We build our own diff here, NOT graphify.analyze.graph_diff(),
        because that function relies on build_from_json() which has the ID mismatch (D-009).
        """

        def edge_key(e: GraphEdge) -> tuple[str, str, str]:
            return (e.source, e.target, e.edge_type)

        base_edge_map = {edge_key(e): e for e in base.edges}
        head_edge_map = {edge_key(e): e for e in head.edges}
        base_node_ids = {n.id for n in base.nodes}
        head_node_ids = {n.id for n in head.nodes}

        # Detect cluster changes for nodes present in both snapshots
        base_node_map = {n.id: n for n in base.nodes}
        head_node_map = {n.id: n for n in head.nodes}
        cluster_changes: list[dict[str, str | int]] = []
        for nid in head_node_ids & base_node_ids:
            old_cluster = base_node_map[nid].cluster_id
            new_cluster = head_node_map[nid].cluster_id
            if old_cluster != new_cluster:
                cluster_changes.append({
                    "node_id": nid,
                    "old_cluster": old_cluster,
                    "new_cluster": new_cluster,
                })

        return DiffResult(
            added_edges=[head_edge_map[k] for k in head_edge_map if k not in base_edge_map],
            removed_edges=[base_edge_map[k] for k in base_edge_map if k not in head_edge_map],
            added_nodes=[n for n in head.nodes if n.id not in base_node_ids],
            removed_nodes=[n for n in base.nodes if n.id not in head_node_ids],
            cluster_changes=cluster_changes,
        )

    def _normalize(self, raw: dict[str, Any], repo_path: Path) -> GraphSnapshot:
        """Map Graphify's extract() output to our GraphSnapshot schema.

        Field names documented in spike/SPIKE_REPORT.md §Graph-Struktur:
        - nodes: raw["nodes"] → fields: id, label, source_file
        - edges: raw["links"] (NOT "edges"!) → fields: source, target, relation,
          source_file, confidence

        The source_file field is critical for package-path glob matching
        in violation_checker.py. Do NOT use node-ID string-splits.
        """
        repo_str = str(repo_path)

        nodes = [
            GraphNode(
                id=n["id"],
                name=n.get("label", n["id"]),
                type=n.get("file_type", "unknown"),
                file_path=_make_relative(n.get("source_file", ""), repo_str),
                cluster_id=n.get("community", -1),
            )
            for n in raw.get("nodes", [])
        ]

        # Spike verified: extraction uses "links" key, not "edges"
        edge_list_key = "links" if "links" in raw else "edges"
        edges = [
            GraphEdge(
                source=e["source"],
                target=e["target"],
                edge_type=e.get("relation", "imports"),
                confidence=e.get("confidence", EXTRACTED),
                metadata={
                    "source_file": _make_relative(e.get("source_file", ""), repo_str),
                },
            )
            for e in raw.get(edge_list_key, [])
        ]

        return GraphSnapshot(
            nodes=nodes,
            edges=edges,
            metadata={
                "node_count": len(nodes),
                "edge_count": len(edges),
            },
        )


def _make_relative(absolute_path: str, repo_root: str) -> str:
    """Convert an absolute file path to a repo-relative path."""
    if not absolute_path:
        return ""
    try:
        return str(Path(absolute_path).relative_to(repo_root))
    except ValueError:
        return absolute_path
