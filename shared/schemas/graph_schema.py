"""Schemas for Graphify graph data structures."""

from __future__ import annotations

from pydantic import BaseModel, Field

MetadataValue = str | int | float


class GraphNode(BaseModel):
    """A node in the knowledge graph.

    Attributes:
        id: Unique node identifier, typically ``file:entity``.
        name: Human-readable node name.
        type: Node type such as ``module``, ``class``, ``function``, or ``file``.
        file_path: Source file path relative to the repository root.
        cluster_id: Leiden community cluster identifier.
        metadata: Additional scalar metadata emitted by the graph builder.
    """

    id: str = Field(description="Unique node identifier (typically file:entity)")
    name: str = Field(description="Human-readable name")
    type: str = Field(description="Node type: module, class, function, file")
    file_path: str = Field(default="", description="Source file path relative to repo root")
    cluster_id: int = Field(default=-1, description="Leiden community cluster ID")
    metadata: dict[str, MetadataValue] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """A typed edge between two graph nodes.

    Attributes:
        source: Source node identifier.
        target: Target node identifier.
        edge_type: Relationship type such as ``imports`` or ``calls``.
        confidence: Extraction confidence, for example ``EXTRACTED`` or ``INFERRED``.
        metadata: Additional scalar metadata emitted during extraction.
    """

    source: str = Field(description="Source node ID")
    target: str = Field(description="Target node ID")
    edge_type: str = Field(description="Edge type: imports, calls, implements, depends_on")
    confidence: str = Field(
        default="EXTRACTED",
        description="EXTRACTED (from AST), INFERRED, or AMBIGUOUS",
    )
    metadata: dict[str, MetadataValue] = Field(default_factory=dict)


class GraphSnapshot(BaseModel):
    """A complete graph snapshot at a point in time.

    Attributes:
        nodes: All known graph nodes.
        edges: All typed relationships between nodes.
        metadata: Graph-level scalar metadata such as counts and version info.
    """

    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    metadata: dict[str, MetadataValue] = Field(
        default_factory=dict,
        description="Graph-level metadata: node_count, edge_count, cluster_count",
    )
