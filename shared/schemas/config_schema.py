"""Schemas for .archlens.yml configuration."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ForbidRule(BaseModel):
    """A hard rule that fails CI when a forbidden dependency appears.

    Attributes:
        from_glob: Source glob pattern.
        to_glob: Target glob pattern.
        message: Human-readable guidance for the violation.
    """

    model_config = ConfigDict(populate_by_name=True)

    from_glob: str = Field(alias="from", description="Source glob pattern, e.g. 'frontend/*'")
    to_glob: str = Field(alias="to", description="Target glob pattern, e.g. 'database/*'")
    message: str = Field(default="", description="Human-readable explanation")


class WarnRule(BaseModel):
    """A soft rule that surfaces a warning without failing CI.

    Attributes:
        from_glob: Source glob pattern.
        to_glob: Target glob pattern.
        message: Human-readable guidance for the warning.
    """

    model_config = ConfigDict(populate_by_name=True)

    from_glob: str = Field(alias="from", description="Source glob pattern")
    to_glob: str = Field(alias="to", description="Target glob pattern")
    message: str = Field(default="", description="Human-readable explanation")


class Thresholds(BaseModel):
    """Numeric thresholds for architecture health heuristics.

    Attributes:
        god_node_warn: Incoming edge count that raises a warning.
        god_node_fail: Incoming edge count that fails CI.
        cross_cluster_warn: Cross-cluster edge count that raises a warning.
        cross_cluster_fail: Cross-cluster edge count that fails CI.
    """

    god_node_warn: int = Field(default=15, description="Incoming edges before warning")
    god_node_fail: int = Field(default=30, description="Incoming edges before CI fail")
    cross_cluster_warn: int = Field(
        default=5,
        description="Cross-cluster edges per PR before warning",
    )
    cross_cluster_fail: int = Field(
        default=10,
        description="Cross-cluster edges per PR before CI fail",
    )


class ArchLensConfig(BaseModel):
    """Root schema for ``.archlens.yml``.

    Attributes:
        version: Config schema version.
        forbid: Hard rules that fail CI.
        warn: Soft rules that surface warnings only.
        thresholds: Numeric graph health thresholds.
        ignore: Glob patterns excluded from scanning.
    """

    version: int = Field(default=1)
    forbid: list[ForbidRule] = Field(default_factory=list)
    warn: list[WarnRule] = Field(default_factory=list)
    thresholds: Thresholds = Field(default_factory=Thresholds)
    ignore: list[str] = Field(default_factory=list, description="Glob patterns to exclude from scan")
