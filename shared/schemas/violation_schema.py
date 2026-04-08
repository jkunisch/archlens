"""Schemas for architecture violations."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Supported violation severities."""

    FAIL = "fail"
    WARN = "warn"
    INFO = "info"


class ViolationType(str, Enum):
    """Supported architecture violation categories."""

    FORBIDDEN_EDGE = "forbidden_edge"
    GOD_NODE = "god_node"
    CROSS_CLUSTER = "cross_cluster"


class Violation(BaseModel):
    """A single architecture violation detected in a PR.

    Attributes:
        violation_type: Violation category.
        severity: Severity level used for CI and comment rendering.
        source_path: Source file or node that triggered the violation.
        target_path: Target file or node for edge-based violations.
        rule_message: Human-readable rule text from ``.archlens.yml``.
        detail: Additional diagnostic context.
        blast_radius: Number of transitively affected nodes.
    """

    violation_type: ViolationType
    severity: Severity
    source_path: str = Field(description="Source file/node that caused the violation")
    target_path: str = Field(default="", description="Target file/node (for edge violations)")
    rule_message: str = Field(default="", description="Message from .archlens.yml rule")
    detail: str = Field(default="", description="Additional context")
    blast_radius: int = Field(default=0, description="Number of transitively affected nodes")


class ViolationReport(BaseModel):
    """Collection of all violations for a single PR analysis.

    Attributes:
        violations: All violations detected for the PR.
        graph_summary: Compact summary derived from the graph diff.
    """

    violations: list[Violation] = Field(default_factory=list)
    graph_summary: str = Field(default="", description="DiffResult.summary")

    @property
    def has_failures(self) -> bool:
        """Return ``True`` when the report contains any failing violation."""

        return any(violation.severity == Severity.FAIL for violation in self.violations)

    @property
    def failure_count(self) -> int:
        """Return the number of failing violations."""

        return sum(1 for violation in self.violations if violation.severity == Severity.FAIL)

    @property
    def warning_count(self) -> int:
        """Return the number of warning violations."""

        return sum(1 for violation in self.violations if violation.severity == Severity.WARN)
