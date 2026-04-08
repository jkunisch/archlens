# Task 03: GitHub Action + .archlens.yml Parser

> **Priorität:** 🟢 Starten NACH Task 01 (Spike) und Task 02 (Schemas)  
> **Geschätzter Aufwand:** 60–75 Minuten  
> **Empfohlener Agent:** Claude Code  
> **Arbeitsverzeichnis:** `C:\Users\Jonatan\Documents\projects_2026\archlens\action\`

> [!WARNING]
> **Wichtig: 2 Mitigations sind explizit eingebaut**
> - **Schwachstelle 1 (Signal-Noise):** Schritt 2b implementiert `EdgeNoiseFilter` — nur Edges die Cluster-Grenzen kreuzen ODER Regeln matchen werden gesurfaced
> - **Schwachstelle 2 (Graphify-Abhängigkeit):** Schritt 1a implementiert `GraphifyAdapter` als Abstraktions-Layer — ein späterer Fork/Ersatz braucht nur diesen Adapter zu ändern
> - **Schwachstelle 4 (CI-Laufzeit):** Schritt 5 nutzt GitHub Actions Cache für Graphify's SHA256-Cache

---

## Kontext

Wir bauen **ArchLens** — ein GitHub-natives Architecture Drift Radar. Lies `ARCHITECTURE.md` im Projekt-Root für die vollständige Architektur.

Diese Komponente ist die **GitHub Action**, die im CI-Runner des Kunden läuft. Sie:
1. Checkt Base- und Head-Commit aus
2. Führt Graphify's AST-Pass aus (2x → 2 Graphen)
3. Parst `.archlens.yml` Regeln
4. Prüft hard violations lokal (CI fail)
5. Uploaded `graph.json` + `violations.json` an die ArchLens API

**KRITISCH:** Der Quellcode des Kunden verlässt NIEMALS den CI-Runner. Nur Metadaten (Knotennamen, Edge-Typen, Cluster-IDs) werden übertragen.

**WICHTIG:** Lies zuerst `spike/SPIKE_REPORT.md` — dort steht welcher Graphify-Import-Pfad funktioniert und wie `graph.json` strukturiert ist.

---

## Deine Aufgabe

### Schritt 1a: Graphify Abstraktions-Layer ⚠️ MITIGATION Schwachstelle 2

Erstelle `action/graphify_adapter.py`.

> [!WARNING]
> **D-009 — KRITISCH:** Nutze `extract(collect_files(path))` direkt. `build_from_json()` und
> `graph_diff()` NICHT verwenden — sie haben einen ID-Mismatch der Import-Edges dropped.
> Verifiziert in `spike/test_import_diff.py`.

> [!WARNING]
> **Feldnamen — aus Spike-Dateien verifiziert, nicht geraten:**
> - `graph.json` hat `"links"` für Edges, NICHT `"edges"` (→ `inspect_imports.py:18`)
> - Edge-Felder: `source`, `target`, `relation` (nicht `type`!), `source_file`, `confidence`
> - Node-Felder: `id`, `label` (nicht `name`!), `community` noch ungetestet (Spike nutzte kein Clustering)
> - `extract()` nimmt `files`-Liste aus `collect_files()`, keinen Path direkt (→ `inspect_extraction.py:9`)

> [!IMPORTANT]
> **Fragile Stelle im Spike-Code (Zeile 138 in test_import_diff.py):**
> `tgt_pkg = tgt.split("_")[0]` funktioniert zufällig für `database_models → database`.
> Für ein Produktionssystem brauchen wir `source_file` für Package-Zuordnung, nicht String-Split.
> Die `source_file`-Feld enthält den echten Pfad (z.B. `spike/dummy_repo/database/models.py`).
> Nutze diesen für Glob-Matching, nicht den Node-ID-Split.

```python
"""Abstraction layer over Graphify. All Graphify calls go through here.

CRITICAL (D-009): Use extract(collect_files(path)) directly.
Do NOT use build_from_json() or graphify.analyze.graph_diff().

Field names verified from spike/inspect_extraction.py and spike/inspect_imports.py:
- graph.json uses "links" for edges (not "edges")
- Edge fields: source, target, relation, source_file, confidence
- Node fields: id, label (not "name"), community (cluster, verify this)
- extract() takes a files list from collect_files(), not a path directly
"""
from pathlib import Path
from graphify.extract import extract, collect_files
from graphify.cluster import leiden_cluster   # verify this exists before use
from shared.schemas.graph_schema import GraphSnapshot, GraphNode, GraphEdge
from shared.constants.edge_types import EXTRACTED


class GraphifyAdapter:
    """Wraps Graphify's raw extract() output into our stable GraphSnapshot schema.

    All field name mapping happens here. If Graphify changes field names,
    only _normalize() needs updating.
    """

    def build_graph(self, repo_path: Path) -> GraphSnapshot:
        """Run Graphify AST pass and return normalized GraphSnapshot."""
        files = collect_files(repo_path)
        raw = extract(files)
        # TODO: verify leiden_cluster exists and call signature before enabling
        # clustered = leiden_cluster(raw)
        return self._normalize(raw)

    def build_diff(self, base: GraphSnapshot, head: GraphSnapshot) -> "DiffResult":
        """Compute diff between two snapshots using set arithmetic on verified edge keys.

        Uses (source, target, relation) as the stable key — all three fields
        verified present in the raw extraction output.
        Runs in O(n) not O(n²) via dict lookups.
        """
        from shared.schemas.diff_schema import DiffResult

        def edge_key(e: GraphEdge) -> tuple[str, str, str]:
            return (e.source, e.target, e.edge_type)

        base_edge_map = {edge_key(e): e for e in base.edges}
        head_edge_map = {edge_key(e): e for e in head.edges}
        base_node_map = {n.id: n for n in base.nodes}
        head_node_map = {n.id: n for n in head.nodes}

        cluster_changes = [
            {
                "node_id": nid,
                "old_cluster": base_node_map[nid].cluster_id,
                "new_cluster": head_node_map[nid].cluster_id,
            }
            for nid in head_node_map
            if nid in base_node_map
            and head_node_map[nid].cluster_id != base_node_map[nid].cluster_id
        ]

        return DiffResult(
            added_edges=[head_edge_map[k] for k in head_edge_map if k not in base_edge_map],
            removed_edges=[base_edge_map[k] for k in base_edge_map if k not in head_edge_map],
            added_nodes=[n for nid, n in head_node_map.items() if nid not in base_node_map],
            removed_nodes=[n for nid, n in base_node_map.items() if nid not in head_node_map],
            cluster_changes=cluster_changes,
        )

    def _normalize(self, raw: dict) -> GraphSnapshot:
        """Map Graphify's raw output to GraphSnapshot.

        Field names verified from spike files:
        - nodes: raw["nodes"] → fields: id, label (use label as name)
        - edges: raw["links"] (NOT "edges"!) → fields: source, target, relation, source_file, confidence

        source_file is stored in metadata — needed for package-path Glob matching
        in violation_checker.py. Do NOT use node-ID string-split for package detection.
        """
        nodes = [
            GraphNode(
                id=n["id"],
                name=n.get("label", n["id"]),   # "label" not "name" — verified
                type=n.get("type", "unknown"),
                file_path=n.get("file_path", ""),  # TODO: verify field name for file path
                cluster_id=n.get("community", -1), # TODO: verify "community" after clustering
            )
            for n in raw.get("nodes", [])
        ]
        edges = [
            GraphEdge(
                source=e["source"],
                target=e["target"],
                edge_type=e["relation"],            # "relation" not "type" — verified
                confidence=e.get("confidence", EXTRACTED),
                metadata={
                    "source_file": e.get("source_file", ""),  # critical for Glob matching
                },
            )
            for e in raw.get("links", [])           # "links" not "edges" — verified
        ]
        return GraphSnapshot(
            nodes=nodes,
            edges=edges,
            metadata={"node_count": len(nodes), "edge_count": len(edges)},
        )
```

> [!IMPORTANT]
> **3 TODOs die der Agent beim Implementieren verifizieren muss:**
> 1. Node-Feld für Dateipfad: `file_path`? `path`? `source_file`? → In `raw_extraction.json` nachschauen
> 2. Cluster-Feld nach `leiden_cluster()`: `community`? → Aufruf testen, falls Import fehlschlägt → kein Clustering in Phase 1
> 3. `from graphify.cluster import leiden_cluster` existiert? → Wenn nicht, Phase 1 ohne Clustering starten, `cluster_id=-1`



> [!WARNING]
> **D-009 — KRITISCH:** Nutze `extract()` direkt. `build_from_json()` und `graph_diff()` NICHT verwenden.
> `build_from_json()` erzeugt einen ID-Mismatch: Import-Edges referenzieren `database_models` als Target,
> während Nodes als `models` gelistet sind. Diese Eigenheit filtert genau die Edges raus die wir brauchen.
> Die rohe `extract()`-Ausgabe enthält alle Kanten korrekt. Dokumentiert in spike/SPIKE_REPORT.md + D-009.

```python
"""Abstraction layer over Graphify. All Graphify calls go through here.

CRITICAL (D-009): Use extract() directly. Do NOT use build_from_json()
or graphify.analyze.graph_diff() — they cause an ID mismatch that silently
drops import edges from the graph, defeating the entire purpose.

If Graphify changes its API or we need to fork/replace it, only this
file needs to change. The rest of the codebase is Graphify-agnostic.
"""
from pathlib import Path
from graphify.extract import extract          # Verified working in spike
from graphify.cluster import leiden_cluster   # Verified working in spike
from shared.schemas.graph_schema import GraphSnapshot, GraphNode, GraphEdge
from shared.constants.edge_types import EXTRACTED


class GraphifyAdapter:
    """Wraps Graphify's raw extract() output into our stable schema.
    
    Uses extract() directly (not build_from_json) to preserve all
    import edges with correct source/target IDs. See D-009.
    """

    def build_graph(self, repo_path: Path) -> GraphSnapshot:
        """Run Graphify AST pass and return normalized GraphSnapshot.
        
        Args:
            repo_path: Absolute path to the repository root to analyze.
            
        Returns:
            GraphSnapshot with all nodes, edges, and cluster assignments.
        """
        # Step 1: Raw extraction (preserves all edges, correct IDs)
        raw = extract(str(repo_path))
        
        # Step 2: Leiden clustering for community detection
        clustered = leiden_cluster(raw)
        
        # Step 3: Normalize to our stable schema
        return self._normalize(clustered)

    def build_diff(self, base: GraphSnapshot, head: GraphSnapshot) -> "DiffResult":
        """Compute diff between two snapshots using set arithmetic.
        
        IMPORTANT: We build our own diff here, NOT graphify.analyze.graph_diff(),
        because that function relies on build_from_json() which has the ID mismatch.
        Set arithmetic on (source, target, edge_type) tuples is correct and simple.
        """
        from shared.schemas.diff_schema import DiffResult

        def edge_key(e: GraphEdge) -> tuple[str, str, str]:
            return (e.source, e.target, e.edge_type)

        base_edges = {edge_key(e): e for e in base.edges}
        head_edges = {edge_key(e): e for e in head.edges}
        base_nodes = {n.id for n in base.nodes}
        head_nodes = {n.id for n in head.nodes}

        return DiffResult(
            added_edges=list(head_edges[k] for k in head_edges if k not in base_edges),
            removed_edges=list(base_edges[k] for k in base_edges if k not in head_edges),
            added_nodes=[n for n in head.nodes if n.id not in base_nodes],
            removed_nodes=[n for n in base.nodes if n.id not in head_nodes],
            cluster_changes=[
                {"node_id": n.id, "old_cluster": b.cluster_id, "new_cluster": n.cluster_id}
                for n in head.nodes
                for b in base.nodes
                if n.id == b.id and n.cluster_id != b.cluster_id
            ],
        )

    def _normalize(self, raw: dict) -> GraphSnapshot:
        """Map Graphify's extract() output to our GraphSnapshot schema.
        
        Field names are documented in spike/SPIKE_REPORT.md §Graph-Struktur.
        Adjust field names here if Graphify's output format changes — this
        is the only place that needs updating.
        """
        nodes = [
            GraphNode(
                id=n["id"],
                name=n.get("name", n["id"]),
                type=n.get("type", "unknown"),
                file_path=n.get("file", ""),
                cluster_id=n.get("community", -1),
            )
            for n in raw.get("nodes", [])
        ]
        edges = [
            GraphEdge(
                source=e["source"],
                target=e["target"],
                edge_type=e.get("type", "imports"),
                confidence=e.get("provenance", EXTRACTED),
            )
            for e in raw.get("edges", [])
        ]
        return GraphSnapshot(
            nodes=nodes,
            edges=edges,
            metadata={
                "node_count": len(nodes),
                "edge_count": len(edges),
            },
        )
```

### Schritt 1b: .archlens.yml Parser

Erstelle `action/config_parser.py`:

- Liest `.archlens.yml` aus dem Repo-Root (oder gibt leere Default-Config zurück wenn Datei fehlt)
- Nutzt `shared.schemas.config_schema.ArchLensConfig` für Validierung
- Gibt ein validiertes `ArchLensConfig` Objekt zurück

```python
import yaml
from pathlib import Path
from shared.schemas.config_schema import ArchLensConfig


def load_config(repo_path: Path) -> ArchLensConfig:
    """Load and validate .archlens.yml from repo root."""
    config_path = repo_path / ".archlens.yml"
    if not config_path.exists():
        return ArchLensConfig()  # default config, no rules
    
    with open(config_path) as f:
        raw = yaml.safe_load(f)
    
    return ArchLensConfig.model_validate(raw)
```

### Schritt 2a: Edge Noise Filter ⚠️ MITIGATION Schwachstelle 1

Erstelle `action/edge_noise_filter.py` — **bevor Edges analysiert werden, werden triviale Edges herausgefiltert**. Das verhindert dass Entwickler von irrelevanten Findings überflutet werden.

```python
"""Filter trivial edges from graph diffs before analysis.

Without filtering, a Graphify diff between two similar commits can 
produce dozens of irrelevant edges (re-exports, type hints, test 
helpers). This filter reduces noise to only actionable signals.

Filtering strategy (in order of priority):
1. ALWAYS surface: edges matching forbid/warn rules
2. ALWAYS surface: edges crossing Leiden cluster boundaries
3. FILTER OUT: edges within the same cluster (intra-cluster is expected)
4. FILTER OUT: edges with confidence=INFERRED (only show EXTRACTED in Phase 1)
5. FILTER OUT: edges where source or target is in .archlens.yml ignore list
"""
from shared.schemas.diff_schema import DiffResult
from shared.schemas.graph_schema import GraphEdge, GraphSnapshot
from shared.schemas.config_schema import ArchLensConfig
from shared.constants.edge_types import EXTRACTED


def filter_noise(
    diff: DiffResult,
    head_graph: GraphSnapshot,
    config: ArchLensConfig,
) -> DiffResult:
    """Return a filtered DiffResult containing only actionable edges.
    
    Guarantees:
    - All edges matching forbid/warn rules are included
    - All cross-cluster edges are included  
    - Intra-cluster / same-module noise is excluded
    - Max 50 edges in result (hard cap to prevent comment spam)
    """
    node_cluster: dict[str, int] = {n.id: n.cluster_id for n in head_graph.nodes}
    
    def is_cross_cluster(edge: GraphEdge) -> bool:
        src_cluster = node_cluster.get(edge.source, -1)
        tgt_cluster = node_cluster.get(edge.target, -1)
        return src_cluster != tgt_cluster and src_cluster != -1 and tgt_cluster != -1
    
    def matches_any_rule(edge: GraphEdge) -> bool:
        from fnmatch import fnmatch
        all_rules = list(config.forbid) + list(config.warn)
        return any(
            fnmatch(edge.source, r.from_glob) and fnmatch(edge.target, r.to_glob)
            for r in all_rules
        )
    
    def is_ignored(edge: GraphEdge) -> bool:
        from fnmatch import fnmatch
        return any(
            fnmatch(edge.source, p) or fnmatch(edge.target, p)
            for p in config.ignore
        )
    
    filtered_added = [
        e for e in diff.added_edges
        if not is_ignored(e)
        and (e.confidence == EXTRACTED)
        and (is_cross_cluster(e) or matches_any_rule(e))
    ][:50]  # hard cap
    
    return DiffResult(
        added_edges=filtered_added,
        removed_edges=diff.removed_edges,
        added_nodes=diff.added_nodes,
        removed_nodes=diff.removed_nodes,
        cluster_changes=diff.cluster_changes,
    )
```

### Schritt 2b: Violation Checker

Erstelle `action/violation_checker.py`:

- Nimmt `ArchLensConfig` + **gefilterten** `DiffResult` (nach `edge_noise_filter.filter_noise()`)
- Prüft jede `forbid` Regel: matcht `from_glob` und `to_glob` gegen Edge-Source und -Target mit `fnmatch`
- Prüft jede `warn` Regel: gleiche Logik, aber Severity=WARN
- Prüft `thresholds.god_node_warn/fail`: zählt eingehende Edges pro Node im Head-Graph
- Prüft `thresholds.cross_cluster_warn/fail`: zählt Cross-Cluster-Edges in den neuen Edges
- Gibt `ViolationReport` zurück (aus `shared.schemas.violation_schema`)

**Glob-Matching Logik:**
```python
from fnmatch import fnmatch

def edge_matches_rule(edge_source_path: str, edge_target_path: str, 
                      from_glob: str, to_glob: str) -> bool:
    """Check if an edge matches a forbid/warn rule."""
    return fnmatch(edge_source_path, from_glob) and fnmatch(edge_target_path, to_glob)
```

### Schritt 3: Blast Radius Calculator

Erstelle `action/blast_radius.py`:

- Nimmt den Head-Graph (Nodes + Edges) und eine Liste von geänderten Node-IDs
- Führt BFS (Breadth-First Search) aus: von jedem geänderten Node, folge allen eingehenden Edges (Reverse-Traversal)
- Zählt wie viele unique Nodes transitiv betroffen sind
- Gibt `dict[str, int]` zurück: `{node_id: blast_radius_count}`

### Schritt 4: Entrypoint + Agent-Kontext Output (D-010)

Erstelle `action/entrypoint.py` — das Hauptskript das die GitHub Action ausführt:

```python
"""ArchLens GitHub Action entrypoint.

Workflow:
1. Read environment variables (GITHUB_WORKSPACE, INPUT_*)
2. Run Graphify AST pass on base and head commits (via GraphifyAdapter)
3. Compute graph diff (GraphifyAdapter.build_diff — eigener Diff, nicht graph_diff())
4. Filter noise (EdgeNoiseFilter — only cross-cluster + rule-matching edges)
5. Load .archlens.yml and check violations
6. Calculate blast radius for changed nodes
7. Write archlens_context.json — structured for Agent consumption (D-010)
8. Write GITHUB_STEP_SUMMARY — human-readable + agent-readable
9. If hard violations: set CI status fail (exit code 1)
10. Upload results to ArchLens API (if configured)
11. Output violation count to GitHub Action outputs
"""
```

**Implementiere den vollen Workflow.** Dann ergänze `action/context_writer.py`:

```python
"""Write archlens_context.json — structured output for Coding and Project Agents.

Design goals (D-010):
- Machine-readable JSON with clear field names
- Includes context-ready sentences that an LLM can inject directly into its system prompt
- Includes file-level impact so agents know WHICH files they should care about
- Written as both a local file AND to GITHUB_STEP_SUMMARY

Agents (Claude Code, Cursor, Codex, Gemini) should read archlens_context.json
at session start to understand the current architectural state of the codebase.
"""
import json
import os
from pathlib import Path
from shared.schemas.violation_schema import ViolationReport, Severity
from shared.schemas.diff_schema import DiffResult


def write_agent_context(
    report: ViolationReport,
    diff: DiffResult,
    repo: str,
    pr_number: int,
    output_path: Path,
) -> None:
    """Write structured context file for AI agent consumption.

    Output schema (archlens_context.json):
    {
      "schema_version": "1.0",
      "repo": "owner/repo",
      "pr_number": 42,
      "summary": "2 violations, 1 warning. Blast radius: 47 nodes.",
      "agent_instructions": [
        "CRITICAL: frontend/checkout.py directly imports database/models.py. This violates the architecture boundary. Route through api/checkout_service.py instead.",
        "WARNING: services/payment.py has 23 incoming dependencies. Avoid adding more imports to this file."
      ],
      "violations": [...],   // full ViolationReport JSON
      "changed_files": [...], // files changed in this PR
      "high_blast_radius_nodes": [...], // nodes with blast_radius > 10
      "architecture_context": "..."  // single paragraph summary for LLM injection
    }
    """
    failures = [v for v in report.violations if v.severity == Severity.FAIL]
    warnings = [v for v in report.violations if v.severity == Severity.WARN]

    # Build agent-injectable instructions (imperative, specific)
    instructions: list[str] = []
    for v in failures:
        msg = f"CRITICAL ARCHITECTURE VIOLATION: {v.source_path}"
        if v.target_path:
            msg += f" → {v.target_path}"
        if v.rule_message:
            msg += f". Rule: {v.rule_message}"
        if v.blast_radius > 0:
            msg += f" Blast radius: {v.blast_radius} affected nodes."
        instructions.append(msg)
    for v in warnings:
        msg = f"ARCHITECTURE WARNING: {v.source_path}"
        if v.rule_message:
            msg += f". {v.rule_message}"
        instructions.append(msg)

    # Single paragraph for LLM system prompt injection
    if failures:
        arch_context = (
            f"This codebase has {len(failures)} active architecture violation(s) in PR #{pr_number}. "
            f"Before adding new code, review the agent_instructions and avoid patterns that "
            f"cross the boundaries defined in .archlens.yml."
        )
    elif warnings:
        arch_context = (
            f"This codebase has {len(warnings)} architecture warning(s). "
            f"The codebase structure is mostly healthy but watch the flagged nodes."
        )
    else:
        arch_context = "No architecture violations detected in this PR. Codebase boundaries are respected."

    context = {
        "schema_version": "1.0",
        "repo": repo,
        "pr_number": pr_number,
        "summary": report.graph_summary or f"{len(failures)} violations, {len(warnings)} warnings",
        "agent_instructions": instructions,
        "violations": [v.model_dump() for v in report.violations],
        "added_edges": [
            {
                "source": e.source,
                "target": e.target,
                "relation": e.edge_type,
                "source_file": e.metadata.get("source_file", ""),
            }
            for e in diff.added_edges
        ],
        "architecture_context": arch_context,
    }

    output_path.write_text(json.dumps(context, indent=2))

    # Also write to GitHub Step Summary (agents running in CI see this)
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a") as f:
            f.write("## ArchLens Architecture Context\n\n")
            f.write(f"**{arch_context}**\n\n")
            if instructions:
                f.write("### Instructions for Coding Agents\n\n")
                for inst in instructions:
                    f.write(f"- {inst}\n")
            f.write("\n```json\n")
            f.write(json.dumps(context, indent=2))
            f.write("\n```\n")
```

Umgebungsvariablen die die GitHub Action bereitstellt:
- `GITHUB_WORKSPACE` — Pfad zum ausgecheckten Repo
- `GITHUB_STEP_SUMMARY` — Pfad zur Summary-Datei (für UI + Agent-Lesbarkeit)
- `INPUT_ARCHLENS_API_URL` — URL der ArchLens API (optional)
- `INPUT_ARCHLENS_API_KEY` — API Key (optional)
- `GITHUB_BASE_REF` — Base Branch
- `GITHUB_HEAD_REF` — Head Branch
- `GITHUB_SHA` — Head Commit SHA


### Schritt 5: action.yml + GitHub Actions Cache ⚠️ MITIGATION Schwachstelle 4

Erstelle `action/action.yml`.

**Wichtig:** Der Graphify-Cache (SHA256-basiert) muss zwischen CI-Runs persistiert werden, sonst wird bei jedem PR die komplette Codebase neu geparst. Der Cache reduziert die Laufzeit bei unveränderten Dateien auf Millisekunden.

```yaml
name: 'ArchLens — Architecture Drift Radar'
description: 'Detect architectural boundary violations in every PR'
branding:
  icon: 'eye'
  color: 'purple'

inputs:
  archlens-api-url:
    description: 'ArchLens API URL (optional, for dashboard integration)'
    required: false
  archlens-api-key:
    description: 'ArchLens API key (optional)'
    required: false

outputs:
  violations:
    description: 'Number of violations found'
  warnings:
    description: 'Number of warnings found'
  has-failures:
    description: 'Whether any hard violations were found (true/false)'

runs:
  using: 'docker'
  image: 'Dockerfile'
```

Erstelle außerdem `action/example-workflow.yml` — das fertige Workflow-File das Kunden in ihr `.github/workflows/` kopieren:

```yaml
name: ArchLens Architecture Check

on:
  pull_request:
    branches: [main, master]

jobs:
  architecture-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history needed for base/head comparison

      # MITIGATION: Cache Graphify's SHA256 file cache between runs
      # Without this, every run re-parses the full codebase.
      # With this, only changed files are re-parsed.
      - name: Cache Graphify analysis
        uses: actions/cache@v4
        with:
          path: graphify-out/cache
          key: graphify-${{ runner.os }}-${{ github.repository }}-${{ github.sha }}
          restore-keys: |
            graphify-${{ runner.os }}-${{ github.repository }}-

      - name: ArchLens Architecture Check
        uses: archlens/archlens-action@v1
        with:
          archlens-api-url: ${{ secrets.ARCHLENS_API_URL }}
          archlens-api-key: ${{ secrets.ARCHLENS_API_KEY }}
```

### Schritt 6: Dockerfile

Erstelle `action/Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Install graphify and dependencies
RUN pip install --no-cache-dir graphifyy pyyaml httpx pydantic

COPY . /action
WORKDIR /action

ENTRYPOINT ["python", "/action/entrypoint.py"]
```

### Schritt 7: Tests

Erstelle `tests/test_config_parser.py`, `tests/test_violation_checker.py`, und `tests/test_edge_noise_filter.py`:

- Test: Config-Parser lädt gültige .archlens.yml
- Test: Config-Parser gibt Defaults bei fehlender Datei
- Test: forbid-Regel matched korrekt gegen Edges
- Test: forbid-Regel matched NICHT bei nicht-matchendem Pfad
- Test: God-Node-Threshold wird korrekt erkannt
- Test: Blast Radius BFS findet transitive Dependencies
- Test: ViolationReport.has_failures ist korrekt
- **Test: NoiseFilter behält Cross-Cluster-Edge, filtert Intra-Cluster-Edge**
- **Test: NoiseFilter behält Edge die forbid-Regel matcht, auch wenn intra-cluster**
- **Test: NoiseFilter filtert INFERRED-Edges heraus**
- **Test: NoiseFilter respektiert Hard-Cap von 50 Edges**
- **Test: NoiseFilter filtert ignorierte Pfade**

Mindestens 13 Tests.

---

## Erwartetes Output

```
action/
├── __init__.py
├── action.yml
├── example-workflow.yml     # Copy-paste ready for customers
├── Dockerfile
├── entrypoint.py
├── graphify_adapter.py      # NEW: abstraction layer (Schwachstelle 2)
├── config_parser.py
├── edge_noise_filter.py     # NEW: signal-to-noise filter (Schwachstelle 1)
├── violation_checker.py
└── blast_radius.py

tests/
├── test_config_parser.py
├── test_violation_checker.py
└── test_edge_noise_filter.py  # NEW
```

---

## Regeln

- Lies `AGENTS.md` §4 — `action/` darf NUR Graphify importieren, .archlens.yml parsen, graph.json erzeugen, API aufrufen
- `action/` darf NICHT auf Datenbank zugreifen oder Dashboard-Code importieren
- Imports aus `shared/schemas/` und `shared/constants/` sind erlaubt und erwünscht
- Kein LLM-Aufruf — alles deterministisch (Prinzip P2)
- Kein Quellcode-Snippet darf in der API-Upload-Payload landen (Prinzip P1)
- Nutze den Graphify-Import-Pfad aus `spike/SPIKE_REPORT.md`
