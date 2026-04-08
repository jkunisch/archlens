"""Canonical edge type constants used across all components."""

IMPORTS = "imports"
CALLS = "calls"
IMPLEMENTS = "implements"
EXTENDS = "extends"
DEPENDS_ON = "depends_on"
CONTAINS = "contains"

SEMANTICALLY_SIMILAR = "semantically_similar_to"

DETERMINISTIC_EDGE_TYPES = frozenset(
    {
        IMPORTS,
        CALLS,
        IMPLEMENTS,
        EXTENDS,
        DEPENDS_ON,
        CONTAINS,
    }
)

EXTRACTED = "EXTRACTED"
INFERRED = "INFERRED"
AMBIGUOUS = "AMBIGUOUS"

__all__ = [
    "AMBIGUOUS",
    "CALLS",
    "CONTAINS",
    "DETERMINISTIC_EDGE_TYPES",
    "DEPENDS_ON",
    "EXTRACTED",
    "EXTENDS",
    "IMPLEMENTS",
    "IMPORTS",
    "INFERRED",
    "SEMANTICALLY_SIMILAR",
]
