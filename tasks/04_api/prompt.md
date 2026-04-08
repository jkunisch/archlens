# Task 04: FastAPI Backend + Worker + Mermaid Renderer

> **Priorität:** 🟢 Starten NACH Task 01 (Spike) und Task 02 (Schemas)  
> **Geschätzter Aufwand:** 60–90 Minuten  
> **Empfohlener Agent:** Claude Code  
> **Arbeitsverzeichnis:** `C:\Users\Jonatan\Documents\projects_2026\archlens\api\`

---

## Kontext

Wir bauen **ArchLens** — ein GitHub-natives Architecture Drift Radar. Lies `ARCHITECTURE.md` im Projekt-Root für die vollständige Architektur.

Diese Komponente ist das **Backend** — es empfängt `graph.json` + `violations.json` von der GitHub Action, speichert Snapshots, führt den Graph-Diff Worker aus, generiert Mermaid-Diagramme, und postet PR-Kommentare via GitHub API.

---

## Deine Aufgabe

### Schritt 1: FastAPI App Setup

**`api/config.py`** — Pydantic Settings:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://archlens:archlens@localhost:5432/archlens"
    redis_url: str = "redis://localhost:6379/0"
    github_app_id: str = ""
    github_app_private_key_path: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    secret_key: str = "change-me"
    
    model_config = {"env_file": ".env"}
```

**`api/main.py`** — FastAPI App:
- CORS Middleware (für Dashboard)
- Health-Check Route (`GET /health`)
- Router includes für `intake`, `repos`, `history`, `auth`
- Exception Handlers

### Schritt 2: SQLAlchemy Models

**`api/models/base.py`** — SQLAlchemy Base + Session Factory

**`api/models/tenant.py`**:
```python
class Tenant(Base):
    id: int (PK, autoincrement)
    github_org: str (unique)
    plan: str (default "free")
    created_at: datetime
```

**`api/models/repo.py`**:
```python
class Repo(Base):
    id: int (PK)
    tenant_id: int (FK → Tenant)
    full_name: str (unique, "owner/repo")
    is_active: bool (default True)
    created_at: datetime
```

**`api/models/snapshot.py`**:
```python
class GraphSnapshotRecord(Base):
    id: int (PK)
    repo_id: int (FK → Repo)
    commit_sha: str
    graph_data: JSON  # Die komplette graph.json als JSONB
    node_count: int
    edge_count: int
    cluster_count: int
    created_at: datetime
```

**`api/models/job.py`**:
```python
class AnalysisJob(Base):
    id: str (PK, UUID)
    repo_id: int (FK → Repo)
    pr_number: int
    base_sha: str
    head_sha: str
    status: str (queued/running/completed/failed)
    violation_count: int (default 0)
    warning_count: int (default 0)
    has_failures: bool (default False)
    pr_comment_url: str (default "")
    error_message: str (default "")
    started_at: datetime (nullable)
    completed_at: datetime (nullable)
    created_at: datetime
```

### Schritt 3: API Routes

**`api/routes/intake.py`** — Graph Upload Endpoint:
```
POST /api/v1/intake
Body: {
    "repo_full_name": "owner/repo",
    "pr_number": 42,
    "base_sha": "abc123",
    "head_sha": "def456",
    "base_graph": { ... graph.json ... },
    "head_graph": { ... graph.json ... },
    "violations": [ ... violations ... ],
    "installation_id": 12345
}
Response: { "job_id": "uuid", "status": "queued" }
```

Workflow:
1. Validiere Input mit Pydantic
2. Upsert Tenant + Repo
3. Speichere beide Graph-Snapshots
4. Erstelle AnalysisJob mit status="queued"
5. Dispatche Worker-Job via Redis/RQ
6. Return job_id

**`api/routes/repos.py`**:
```
GET /api/v1/repos              → Liste aller Repos des Tenants
GET /api/v1/repos/:id          → Repo-Details
GET /api/v1/repos/:id/history  → Letzte 20 Snapshots
```

**`api/routes/health.py`**:
```
GET /health → {"status": "ok", "version": "0.1.0"}
```

### Schritt 4: Workers

**`api/workers/diff_worker.py`** — Kernlogik:

```python
"""Worker that processes graph analysis jobs.

Steps:
1. Load base_graph and head_graph from Postgres
2. Compute diff (added/removed edges and nodes)
3. Identify cluster changes
4. Calculate blast radius for changed nodes
5. Store results in Postgres
6. Trigger comment worker
"""
```

Implementiere:
- `compute_diff(base_graph, head_graph) -> DiffResult` — Vergleicht Edges und Nodes
- `find_god_nodes(graph, threshold) -> list[dict]` — Nodes mit zu vielen eingehenden Edges
- `count_cross_cluster_edges(diff, head_graph) -> int` — Wie viele neue Edges kreuzen Cluster-Grenzen

**`api/workers/mermaid_renderer.py`** — Graph-Diff als Mermaid-Diagramm:

```python
"""Render a graph diff as a Mermaid diagram for GitHub PR comments.

GitHub renders Mermaid natively in Markdown, so the output is directly
embeddable in PR comments.

Output example:
```mermaid
graph LR
    A[frontend/views.py] -->|imports 🔴| B[database/models.py]
    A -->|imports ✅| C[api/routes.py]
    C -->|calls| D[services/payment.py]
    
    style A fill:#1a1a2e
    style B fill:#e74c3c
```
"""
```

Implementiere:
- `render_diff_mermaid(diff: DiffResult, max_nodes: int = 15) -> str` — Beschränke auf die relevantesten Nodes
- Rote Edges (`-->|🔴 forbid|`) für verbotene Kanten
- Gelbe Edges (`-->|⚠️ warn|`) für Warnungen
- Grüne Edges (`-->|✅ resolved|`) für aufgelöste Violations
- Node-Labels sind Dateinamen (gekürzt wenn zu lang)

**`api/workers/comment_worker.py`** — PR-Kommentar zusammenbauen + posten:

```python
"""Compose and post PR comments via GitHub API.

Comment structure:
1. Header: ArchLens summary (# violations, # warnings)
2. Mermaid diagram (if violations exist)
3. Violation details (table)
4. Blast radius info
5. Footer: Link to dashboard
"""
```

Implementiere:
- `compose_comment(violations: ViolationReport, diff: DiffResult, mermaid: str) -> str`
- `post_comment(repo: str, pr_number: int, body: str, installation_id: int) -> str`
- GitHub App Authentication: JWT Token aus App ID + Private Key → Installation Access Token

### Schritt 5: Docker Compose (Entwicklung)

**`docker-compose.yml`** (im Projektroot):
```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: archlens
      POSTGRES_PASSWORD: archlens
      POSTGRES_DB: archlens
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    build:
      context: .
      dockerfile: api/Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://archlens:archlens@db:5432/archlens
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - db
      - redis

  worker:
    build:
      context: .
      dockerfile: api/Dockerfile
    command: python -m rq worker --url redis://redis:6379/0
    environment:
      DATABASE_URL: postgresql://archlens:archlens@db:5432/archlens
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
```

**`api/Dockerfile`**:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir ".[api]"
COPY shared/ shared/
COPY api/ api/
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Schritt 6: Tests

Erstelle in `tests/`:
- `test_diff_worker.py` — DiffResult Berechnung mit bekannten Graphen
- `test_mermaid_renderer.py` — Mermaid-Output enthält erwartete Edges und Styles
- `test_comment_composer.py` — Kommentar enthält Header, Violations, Mermaid

Mindestens 10 Tests. Nutze Fixtures mit festen Graph-Daten (keine Graphify-Dependency in Tests).

---

## Erwartetes Output

```
archlens/
├── docker-compose.yml
├── api/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   ├── Dockerfile
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── tenant.py
│   │   ├── repo.py
│   │   ├── snapshot.py
│   │   └── job.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── intake.py
│   │   ├── repos.py
│   │   └── health.py
│   └── workers/
│       ├── __init__.py
│       ├── diff_worker.py
│       ├── mermaid_renderer.py
│       └── comment_worker.py
└── tests/
    ├── test_diff_worker.py
    ├── test_mermaid_renderer.py
    └── test_comment_composer.py
```

---

## Regeln

- Lies `AGENTS.md` §4 — `api/` darf NICHT Graphify importieren und NICHT direkt GitHub API aufrufen (das macht der Worker)
- `api/` darf graph.json empfangen, Postgres lesen/schreiben, Worker-Jobs dispatchen
- Imports aus `shared/schemas/` und `shared/constants/` sind erlaubt
- Kein LLM-Aufruf — der Mermaid-Renderer ist rein deterministisch
- Kein Quellcode-Snippet in der Datenbank — nur Graph-Metadaten
- Nutze die Schemas aus `shared/schemas/` — erfinde keine neuen Datentypen
- GitHub App Auth: JWT (PyJWT), nicht Personal Access Token
