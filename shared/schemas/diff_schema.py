"""Schemas for graph diff results."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .graph_schema import GraphEdge, GraphNode

ClusterChangeValue = str | int


class DiffResult(BaseModel):
    """Result of comparing two graph snapshots.

    Attributes:
        added_edges: Edges present only in the head snapshot.
        removed_edges: Edges present only in the base snapshot.
        added_nodes: Nodes introduced by the change.
        removed_nodes: Nodes removed by the change.
        cluster_changes: Nodes whose cluster assignment changed between snapshots.
    """

    added_edges: list[GraphEdge] = Field(default_factory=list)
    removed_edges: list[GraphEdge] = Field(default_factory=list)
    added_nodes: list[GraphNode] = Field(default_factory=list)
    removed_nodes: list[GraphNode] = Field(default_factory=list)
    cluster_changes: list[dict[str, ClusterChangeValue]] = Field(
        default_factory=list,
        description="Nodes that changed Leiden cluster between base and head",
    )

    @property
    def has_changes(self) -> bool:
        """Return ``True`` when any graph-level change was detected."""

        return bool(
            self.added_edges
            or self.removed_edges
            or self.added_nodes
            or self.removed_nodes
            or self.cluster_changes
        )

    @property
    def summary(self) -> str:
        """Return a compact, human-readable change summary."""

        parts: list[str] = []
        if self.added_edges:
            parts.append(f"+{len(self.added_edges)} edges")
        if self.removed_edges:
            parts.append(f"-{len(self.removed_edges)} edges")
        if self.added_nodes:
            parts.append(f"+{len(self.added_nodes)} nodes")
        if self.removed_nodes:
            parts.append(f"-{len(self.removed_nodes)} nodes")
        if self.cluster_changes:
            parts.append(f"~{len(self.cluster_changes)} cluster changes")
        return ", ".join(parts) if parts else "No changes"
