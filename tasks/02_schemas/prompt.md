# Task 02: Shared Schemas + Projekt-Setup

> **Priorität:** 🟡 PARALLEL zu Task 01 ausführbar  
> **Geschätzter Aufwand:** 20–30 Minuten  
> **Empfohlener Agent:** Codex oder Claude Code  
> **Arbeitsverzeichnis:** `C:\Users\Jonatan\Documents\projects_2026\archlens\`

---

## Kontext

Wir bauen **ArchLens** — ein GitHub-natives Architecture Drift Radar. Lies `ARCHITECTURE.md` im Projekt-Root für die vollständige Architektur.

Dieses Task erstellt die **Projekt-Grundstruktur** und die **geteilten Pydantic-Schemas**, die alle anderen Komponenten (`action/`, `api/`, `dashboard/`) verwenden.

---

## Deine Aufgabe

### Schritt 1: Projekt-Root-Dateien erstellen

**`pyproject.toml`** (im Projektroot):
```toml
[project]
name = "archlens"
version = "0.1.0"
description = "Architecture Drift Radar — detect structural degradation in every PR"
requires-python = ">=3.11"
license = { text = "MIT" }

[project.optional-dependencies]
api = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "pydantic>=2.0",
    "sqlalchemy>=2.0",
    "psycopg2-binary>=2.9",
    "redis>=5.0",
    "rq>=1.16",
    "httpx>=0.27",
]
action = [
    "graphifyy",
    "pyyaml>=6.0",
    "httpx>=0.27",
]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "mypy>=1.10",
    "ruff>=0.5",
]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

**`.gitignore`**:
```
__pycache__/
*.pyc
.venv/
.env
*.egg-info/
dist/
build/
spike/base_graph.json
spike/head_graph.json
spike/dummy_repo/graphify-out/
.mypy_cache/
.ruff_cache/
node_modules/
.next/
```

**`.env.example`**:
```env
# ArchLens Environment Variables
DATABASE_URL=postgresql://archlens:archlens@localhost:5432/archlens
REDIS_URL=redis://localhost:6379/0
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY_PATH=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
ARCHLENS_API_URL=http://localhost:8000
SECRET_KEY=change-me-in-production
```

### Schritt 2: Shared Schemas erstellen

Erstelle `shared/` mit allen Pydantic v2 Schemas. Diese definieren den Datenvertrag zwischen allen Komponenten.

**`shared/__init__.py`**: Leer.

**`shared/schemas/__init__.py`**: Exportiert alle Schemas.

**`shared/schemas/graph_schema.py`**:
```python
"""Schemas for Graphify graph data structures."""
from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """A node in the knowledge graph, representing a code entity."""
    id: str = Field(description="Unique node identifier (typically file:entity)")
    name: str = Field(description="Human-readable name")
    type: str = Field(description="Node type: module, class, function, file")
    file_path: str = Field(default="", description="Source file path relative to repo root")
    cluster_id: int = Field(default=-1, description="Leiden community cluster ID")
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """A typed edge between two nodes."""
    source: str = Field(description="Source node ID")
    target: str = Field(description="Target node ID")
    edge_type: str = Field(description="Edge type: imports, calls, implements, depends_on")
    confidence: str = Field(
        default="EXTRACTED",
        description="EXTRACTED (from AST), INFERRED, or AMBIGUOUS"
    )
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class GraphSnapshot(BaseModel):
    """A complete graph snapshot at a point in time."""
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    metadata: dict[str, str | int | float] = Field(
        default_factory=dict,
        description="Graph-level metadata: node_count, edge_count, cluster_count"
    )
```

**`shared/schemas/diff_schema.py`**:
```python
"""Schemas for graph diff results."""
from pydantic import BaseModel, Field
from .graph_schema import GraphEdge, GraphNode


class DiffResult(BaseModel):
    """Result of comparing two graph snapshots."""
    added_edges: list[GraphEdge] = Field(default_factory=list)
    removed_edges: list[GraphEdge] = Field(default_factory=list)
    added_nodes: list[GraphNode] = Field(default_factory=list)
    removed_nodes: list[GraphNode] = Field(default_factory=list)
    cluster_changes: list[dict[str, str | int]] = Field(
        default_factory=list,
        description="Nodes that changed Leiden cluster between base and head"
    )

    @property
    def has_changes(self) -> bool:
        return bool(
            self.added_edges or self.removed_edges
            or self.added_nodes or self.removed_nodes
        )

    @property
    def summary(self) -> str:
        parts: list[str] = []
        if self.added_edges:
            parts.append(f"+{len(self.added_edges)} edges")
        if self.removed_edges:
            parts.append(f"-{len(self.removed_edges)} edges")
        if self.added_nodes:
            parts.append(f"+{len(self.added_nodes)} nodes")
        if self.removed_nodes:
            parts.append(f"-{len(self.removed_nodes)} nodes")
        return ", ".join(parts) if parts else "No changes"
```

**`shared/schemas/config_schema.py`**:
```python
"""Schemas for .archlens.yml configuration."""
from pydantic import BaseModel, Field


class ForbidRule(BaseModel):
    """A hard rule: CI fails if this edge pattern exists."""
    from_glob: str = Field(alias="from", description="Source glob pattern, e.g. 'frontend/*'")
    to_glob: str = Field(alias="to", description="Target glob pattern, e.g. 'database/*'")
    message: str = Field(default="", description="Human-readable explanation")

    model_config = {"populate_by_name": True}


class WarnRule(BaseModel):
    """A soft rule: PR comment warning, no CI failure."""
    from_glob: str = Field(alias="from", description="Source glob pattern")
    to_glob: str = Field(alias="to", description="Target glob pattern")
    message: str = Field(default="", description="Human-readable explanation")

    model_config = {"populate_by_name": True}


class Thresholds(BaseModel):
    """Numeric thresholds for architecture health."""
    god_node_warn: int = Field(default=15, description="Incoming edges before warning")
    god_node_fail: int = Field(default=30, description="Incoming edges before CI fail")
    cross_cluster_warn: int = Field(default=5, description="Cross-cluster edges per PR before warning")
    cross_cluster_fail: int = Field(default=10, description="Cross-cluster edges per PR before CI fail")


class ArchLensConfig(BaseModel):
    """Root schema for .archlens.yml."""
    version: int = Field(default=1)
    forbid: list[ForbidRule] = Field(default_factory=list)
    warn: list[WarnRule] = Field(default_factory=list)
    thresholds: Thresholds = Field(default_factory=Thresholds)
    ignore: list[str] = Field(default_factory=list, description="Glob patterns to exclude from scan")
```

**`shared/schemas/violation_schema.py`**:
```python
"""Schemas for architecture violations."""
from enum import Enum
from pydantic import BaseModel, Field


class Severity(str, Enum):
    FAIL = "fail"
    WARN = "warn"
    INFO = "info"


class ViolationType(str, Enum):
    FORBIDDEN_EDGE = "forbidden_edge"
    GOD_NODE = "god_node"
    CROSS_CLUSTER = "cross_cluster"


class Violation(BaseModel):
    """A single architecture violation detected in a PR."""
    violation_type: ViolationType
    severity: Severity
    source_path: str = Field(description="Source file/node that caused the violation")
    target_path: str = Field(default="", description="Target file/node (for edge violations)")
    rule_message: str = Field(default="", description="Message from .archlens.yml rule")
    detail: str = Field(default="", description="Additional context")
    blast_radius: int = Field(default=0, description="Number of transitively affected nodes")


class ViolationReport(BaseModel):
    """Collection of all violations for a single PR analysis."""
    violations: list[Violation] = Field(default_factory=list)
    graph_summary: str = Field(default="", description="DiffResult.summary")

    @property
    def has_failures(self) -> bool:
        return any(v.severity == Severity.FAIL for v in self.violations)

    @property
    def failure_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.FAIL)

    @property
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.WARN)
```

**`shared/schemas/job_schema.py`**:
```python
"""Schemas for worker job tracking."""
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobRequest(BaseModel):
    """Request to analyze a PR."""
    repo_full_name: str = Field(description="owner/repo")
    pr_number: int
    base_sha: str = Field(description="Base commit SHA")
    head_sha: str = Field(description="Head commit SHA")
    installation_id: int = Field(description="GitHub App installation ID")


class JobResult(BaseModel):
    """Result of a completed analysis job."""
    job_id: str
    status: JobStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    violation_count: int = Field(default=0)
    warning_count: int = Field(default=0)
    has_failures: bool = Field(default=False)
    pr_comment_url: str = Field(default="", description="URL of posted PR comment")
    error_message: str = Field(default="")
```

**`shared/constants/__init__.py`**: Leer.

**`shared/constants/edge_types.py`**:
```python
"""Canonical edge type constants used across all components."""

# Deterministic (from AST)
IMPORTS = "imports"
CALLS = "calls"
IMPLEMENTS = "implements"
EXTENDS = "extends"
DEPENDS_ON = "depends_on"
CONTAINS = "contains"

# Inferred (from analysis)
SEMANTICALLY_SIMILAR = "semantically_similar_to"

# All deterministic types (used in Phase 1)
DETERMINISTIC_EDGE_TYPES = frozenset({
    IMPORTS, CALLS, IMPLEMENTS, EXTENDS, DEPENDS_ON, CONTAINS
})

# Confidence levels
EXTRACTED = "EXTRACTED"
INFERRED = "INFERRED"
AMBIGUOUS = "AMBIGUOUS"
```

### Schritt 3: Verzeichnisstruktur erstellen

Erstelle leere `__init__.py` Dateien für alle Module:

```
action/__init__.py          (leer)
api/__init__.py             (leer)
api/models/__init__.py      (leer)
api/routes/__init__.py      (leer)
api/workers/__init__.py     (leer)
tests/__init__.py           (leer)
tests/test_schemas.py       (siehe Schritt 4)
```

### Schritt 4: Schema-Tests

Erstelle `tests/test_schemas.py` mit grundlegenden Tests:

- Test: ArchLensConfig kann aus YAML-ähnlichem Dict geladen werden (inkl. `from` alias)
- Test: GraphSnapshot mit Nodes und Edges serialisiert/deserialisiert korrekt
- Test: ViolationReport.has_failures ist True wenn mindestens eine FAIL-Violation existiert
- Test: DiffResult.summary formatiert korrekt
- Test: ForbidRule akzeptiert `from` als Alias für `from_glob`

Mindestens 8 Tests, alle sollen `pytest` grün bestehen.

---

## Erwartetes Output

```
archlens/
├── pyproject.toml
├── .gitignore
├── .env.example
├── shared/
│   ├── __init__.py
│   ├── schemas/
│   │   ├── __init__.py       # re-exports
│   │   ├── graph_schema.py
│   │   ├── diff_schema.py
│   │   ├── config_schema.py
│   │   ├── violation_schema.py
│   │   └── job_schema.py
│   └── constants/
│       ├── __init__.py
│       └── edge_types.py
├── action/__init__.py
├── api/__init__.py
├── api/models/__init__.py
├── api/routes/__init__.py
├── api/workers/__init__.py
└── tests/
    ├── __init__.py
    └── test_schemas.py       # 8+ pytest Tests
```

---

## Regeln

- Lies `AGENTS.md` §4 (Bounded Contexts) und §5 (Dateistruktur) im Projekt-Root
- `shared/` darf KEINE Business-Logik enthalten — nur Datenstrukturen und Konstanten
- `shared/` darf NICHT aus `action/`, `api/` oder `dashboard/` importieren
- Alle Schemas nutzen Pydantic v2 (`BaseModel` aus `pydantic`)
- Alle Type Hints strikt — kein `Any`
- Docstrings im Google-Style
- Die Schemas oben sind Vorschläge — passe Feldnamen an wenn du beim Spike (Task 01) siehst dass Graphify's graph.json andere Feldnamen nutzt. Dokumentiere Abweichungen.
