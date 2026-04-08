"""Engine bridge for the MCP server — caches Graphify results in memory.

The MCP server may receive multiple tool calls in rapid succession.
Re-running Graphify's AST pass on every call would be wasteful. This
bridge caches the GraphSnapshot per repo_path and invalidates only
when the path changes or the cache is explicitly cleared.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from action.graphify_adapter import GraphifyAdapter
from action.config_parser import load_config
from action.violation_checker import check_violations, check_single_file
from action.blast_radius import calculate_blast_radius, get_affected_nodes
from action.edge_noise_filter import filter_noise
from action.context_writer import build_agent_context
from shared.schemas.config_schema import ArchLensConfig
from shared.schemas.diff_schema import DiffResult
from shared.schemas.graph_schema import GraphSnapshot
from shared.schemas.violation_schema import ViolationReport


class EngineBridge:
    """Cached bridge between MCP server and the ArchLens engine.

    Caches graph snapshots and config per repo path to avoid
    re-running expensive AST extraction on every tool call.
    """

    def __init__(self) -> None:
        self._adapter = GraphifyAdapter()
        self._cache: dict[str, GraphSnapshot] = {}
        self._config_cache: dict[str, ArchLensConfig] = {}

    def get_graph(self, repo_path: str) -> GraphSnapshot:
        """Get or build the graph snapshot for a repo path."""
        if repo_path not in self._cache:
            self._cache[repo_path] = self._adapter.build_graph(Path(repo_path))
        return self._cache[repo_path]

    def get_config(self, repo_path: str) -> ArchLensConfig:
        """Get or load the .archlens.yml config for a repo path."""
        if repo_path not in self._config_cache:
            self._config_cache[repo_path] = load_config(Path(repo_path))
        return self._config_cache[repo_path]

    def check_boundaries(self, file_path: str, repo_path: str) -> list[dict[str, Any]]:
        """Check if a file violates any architecture boundaries.

        Used by the MCP check_boundaries tool. Returns a list of
        violation dicts that the agent can act on.
        """
        graph = self.get_graph(repo_path)
        config = self.get_config(repo_path)
        violations = check_single_file(file_path, graph, config)
        return [v.model_dump() for v in violations]

    def get_violations(self, repo_path: str) -> dict[str, Any]:
        """Get all current violations for a repo.

        Returns the full violation report as a dict.
        """
        graph = self.get_graph(repo_path)
        config = self.get_config(repo_path)

        # For local scans, diff is empty (no base to compare against)
        # Violations come from the static graph analysis (god nodes, etc.)
        empty_diff = DiffResult()
        report = check_violations(empty_diff, graph, config)
        return report.model_dump()

    def get_blast_radius(self, node_id: str, repo_path: str) -> dict[str, Any]:
        """Get blast radius for a specific node."""
        graph = self.get_graph(repo_path)
        affected = get_affected_nodes(graph, node_id)
        return {
            "node_id": node_id,
            "blast_radius": len(affected),
            "affected_nodes": sorted(affected),
        }

    def get_architecture_rules(self, repo_path: str) -> dict[str, Any]:
        """Get all .archlens.yml rules as structured data."""
        config = self.get_config(repo_path)
        return config.model_dump()

    def get_drift_summary(self, repo_path: str) -> str:
        """Get a compact drift summary suitable for LLM injection."""
        graph = self.get_graph(repo_path)
        config = self.get_config(repo_path)
        empty_diff = DiffResult()
        report = check_violations(empty_diff, graph, config)
        context = build_agent_context(report, empty_diff, repo=repo_path)
        return context.get("architecture_context", "No analysis available.")

    def invalidate(self, repo_path: str | None = None) -> None:
        """Clear cached data. If repo_path is None, clear everything."""
        if repo_path is None:
            self._cache.clear()
            self._config_cache.clear()
        else:
            self._cache.pop(repo_path, None)
            self._config_cache.pop(repo_path, None)
