# Graphify Spike — Go/No-Go Report

> **Datum:** 2026-04-08
> **Agent:** Antigravity (Claude Opus 4.6)
> **Ergebnis:** ✅ GO (mit einer wichtigen Design-Implikation)

---

## 1. Signal: Zeigt der Diff die Violations klar als neue Edges?

| Violation | Ergebnis | Edge im Diff |
|-----------|----------|---------------|
| `frontend/views.py → database/models.py` | ✅ ERKANNT | `views --[imports_from]--> database_models` |
| `frontend/components.py → services/payment.py` | ✅ ERKANNT | `components --[imports_from]--> services_payment` |

**Beide Violations werden als exakt 2 neue Import-Edges im Diff angezeigt. Kein Noise.**

---

## 2. Noise: Wie viele ANDERE neue Edges zeigt der Diff, die NICHT die Violations sind?

**0 Noise-Edges auf Import-Ebene.**

Der Edge-Diff auf Basis der rohen Extraction (siehe Abschnitt 4) zeigt exakt die 2 Violations und sonst nichts.

**Hinweis:** Der `graph_diff()` auf NetworkX-Ebene zeigt 48 neue Edges — aber das sind strukturelle (contains, method, rationale_for) und INFERRED-Edges, die von neuen Klassen/Funktionen in den modifizierten Dateien stammen. Diese sind korrekt, aber für Layer-Violation-Detection irrelevant. Für ArchLens filtern wir auf `imports` und `imports_from` Relation-Typ.

---

## 3. Graph-Struktur: JSON-Format der Extraction

### Extraction Output (`graphify.extract.extract(files)`)

```json
{
  "nodes": [
    {
      "id": "helpers",
      "label": "helpers.py",
      "file_type": "code",
      "source_file": "C:/path/to/helpers.py",
      "source_location": "L1"
    }
  ],
  "edges": [
    {
      "source": "views",
      "target": "api_routes",
      "relation": "imports_from",
      "confidence": "EXTRACTED",
      "source_file": "C:/path/to/views.py",
      "source_location": "L2",
      "weight": 1.0
    }
  ]
}
```

### Node-Attribute

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `id` | string | Normalisierte ID aus Datei-Stem (z.B. `helpers`, `views`) |
| `label` | string | Lesbare Bezeichnung (Dateiname, Klassenname, Funktionsname) |
| `file_type` | string | Immer `"code"` für Source Files |
| `source_file` | string | Absoluter Pfad zur Quelldatei |
| `source_location` | string | Zeilenangabe, z.B. `"L1"` |

### Edge-Attribute

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `source` | string | Node-ID des Quell-Nodes |
| `target` | string | Node-ID des Ziel-Nodes |
| `relation` | string | Edge-Typ: `imports`, `imports_from`, `contains`, `method`, `calls`, `inherits`, `rationale_for`, `uses` |
| `confidence` | string | `EXTRACTED` (AST) oder `INFERRED` (Cross-File-Resolution) |
| `source_file` | string | Datei aus der die Edge stammt |
| `source_location` | string | Zeile im Code |
| `weight` | float | Gewichtung (immer 1.0 bei EXTRACTED) |

### Edge-Typen (für ArchLens relevant)

| Relation | Confidence | Bedeutung | Für ArchLens? |
|----------|-----------|-----------|---------------|
| `imports` | EXTRACTED | `import X` Statement | ✅ Primärsignal |
| `imports_from` | EXTRACTED | `from X.Y import Z` | ✅ Primärsignal |
| `contains` | EXTRACTED | Datei enthält Klasse/Funktion | Strukturell |
| `method` | EXTRACTED | Klasse hat Methode | Strukturell |
| `calls` | INFERRED | Funktionsaufruf (cross-file) | Sekundärsignal |
| `uses` | INFERRED | Typ-Referenz (cross-file) | Sekundärsignal |
| `rationale_for` | EXTRACTED | Docstring-Zuordnung | Irrelevant |
| `inherits` | EXTRACTED | Klassen-Vererbung | Blast Radius |

### ID-Schema (KRITISCH!)

- **File-Nodes**: Stem des Dateinamens → `views`, `models`, `helpers`
- **Import-Targets**: `{package}_{module}` → `database_models`, `services_payment`, `api_routes`
- **Klassen**: `{stem}_{classname}` → `views_dashboardview`, `models_user`
- **Methoden**: `{stem}_{classname}_{method}` → `views_dashboardview_render`

⚠️ **Mismatch beachten:** Import-Edge-Targets (`database_models`) matchen NICHT die Node-IDs (`models`). Graphify's `build_from_json()` filtert diese als "dangling edges" heraus. Für ArchLens müssen wir **direkt mit der Extraction arbeiten**, nicht mit dem NetworkX-Graph.

---

## 4. Import-Pfad: Welcher Python-Import funktioniert?

| Import-Pfad | Ergebnis |
|-------------|----------|
| `from graphify.analyze import graph_diff` | ✅ Funktioniert |
| `from graphify.extract import extract, collect_files` | ✅ Funktioniert |
| `from graphify.build import build_from_json` | ✅ Funktioniert |
| `from graphify.cluster import cluster` | ✅ Funktioniert |
| `from graphify.export import to_json, to_html` | ✅ Funktioniert |
| `import graphify` (lazy attrs) | ✅ Funktioniert |

**Alle 6 Import-Pfade funktionieren.** Kein subprocess-Fallback nötig.

### API-Signaturen (für Phase 1)

```python
# 1. Dateien sammeln
from graphify.extract import collect_files
files: list[Path] = collect_files(Path("repo/"))

# 2. AST-Extraction (deterministisch, kein LLM)
from graphify.extract import extract
extraction: dict = extract(files)
# → {"nodes": [...], "edges": [...]}

# 3. NetworkX Graph (optional — nötig für Cluster/Viz, nicht für Import-Diff)
from graphify.build import build_from_json
G: nx.Graph = build_from_json(extraction)

# 4. Clustering (optional — nötig für Blast Radius, Dashboard)
from graphify.cluster import cluster
communities: dict[int, list[str]] = cluster(G)

# 5. Export (optional — Dashboard Graph Viewer)
from graphify.export import to_json, to_html
to_json(G, communities, "graph.json")
to_html(G, communities, "graph.html")

# 6. Graph Diff (auf NetworkX-Ebene)
from graphify.analyze import graph_diff
diff: dict = graph_diff(G_old, G_new)
# → {"new_nodes": [...], "removed_nodes": [...], "new_edges": [...], ...]
```

---

## 5. Go/No-Go Empfehlung

### ✅ GO

**Begründung:**
1. **Signal ist klar:** 2 injizierte Violations → 2 neue `imports_from`-Edges im Diff. Noise: 0.
2. **Python-Import funktioniert:** Alle 6 relevanten Module importierbar. Kein subprocess nötig.
3. **Deterministisch:** AST-Pass ist reproduzierbar, kein LLM, keine Varianz.
4. **Graph-Format dokumentiert:** Nodes, Edges, Relationen, Confidence-Level — alles klar.

### Design-Implikation für Phase 1

> **ArchLens braucht einen eigenen Import-Diff auf Extraction-Ebene, nicht `graphify.analyze.graph_diff()`.**

Graphify's `graph_diff()` arbeitet auf dem NetworkX-Graph, der Import-Edges filtert (weil Targets als "external" klassifiziert werden — ein ID-Mismatch im Import-Handler). Der NetworkX-Graph ist trotzdem nützlich für:
- Clustering (Blast Radius, Community Detection)
- Graph Visualization (Dashboard)
- God Node Detection

Aber für die Kern-Value-Prop (Layer-Violation-Detection) nutzen wir direkt die rohe Extraction:

```python
# ArchLens Import-Diff (Pseudocode)
base_imports = {(e["source"], e["target"]) 
                for e in base_extraction["edges"] 
                if e["relation"] in ("imports", "imports_from")}

head_imports = {(e["source"], e["target"]) 
                for e in head_extraction["edges"] 
                if e["relation"] in ("imports", "imports_from")}

new_imports = head_imports - base_imports

# Gegen .archlens.yml Regeln prüfen
for src, tgt in new_imports:
    src_pkg = get_package_from_source_file(src)
    tgt_pkg = tgt.split("_")[0]  # z.B. "database" aus "database_models"
    check_rules(src_pkg, tgt_pkg)
```

---

## Dateien erzeugt

```
spike/
├── dummy_repo/           # 5-Ordner Python Codebase (14 Dateien)
│   ├── frontend/         # views.py, components.py, __init__.py
│   ├── api/              # routes.py, middleware.py, __init__.py
│   ├── services/         # auth.py, payment.py, __init__.py
│   ├── database/         # models.py, connection.py, __init__.py
│   └── utils/            # helpers.py, __init__.py
├── test_graphify.py      # Vollständiger Spike (graph_diff auf NetworkX-Ebene)
├── test_import_diff.py   # Import-Aware Diff (Extraction-Ebene) ← DER RICHTIGE ANSATZ
├── base_graph.json       # Graph VOR Violation (NetworkX export)
├── head_graph.json       # Graph NACH Violation (NetworkX export)
├── diff_output.json      # graph_diff Ergebnis (NetworkX-Ebene)
├── diff_output.txt       # Vollständiger Test-Output
├── raw_extraction.json   # Rohe AST-Extraction (zur Inspektion)
├── analyze_diff.py       # Hilfs-Script: Edge-Analyse
├── inspect_imports.py    # Hilfs-Script: Import-Edge Deep-Dive
├── inspect_extraction.py # Hilfs-Script: Extraction Debug
├── debug_cache.py        # Hilfs-Script: Cache Debug
└── SPIKE_REPORT.md       # Dieser Report
```

---

## Schlüssel-Learnings für Phase 1

1. **`extract()` ist die Goldgrube** — nicht `build_from_json()`. Die rohe Extraction enthält alle Imports korrekt mit Modul-Pfad-IDs.

2. **Import-Target-IDs folgen dem Muster `{package}_{module}`** — z.B. `database_models` für `from database.models import ...`. Das ist perfekt für `.archlens.yml` Glob-Matching.

3. **Graphify cached Extractions** (`.graphify_cache/`). In der GitHub Action müssen wir sicherstellen, dass Base und Head jeweils frisch extrahiert werden.

4. **`cluster()` gibt nur `dict[int, list[str]]` zurück** — keine Community-Labels. Labels müssen wir selbst generieren (aus Dateinamen oder Clustered-Node-Labels).

5. **`graphify.analyze.graph_diff()` existiert nativ** — nützlich für Blast Radius und Dashboard-Diff, aber nicht für Layer-Violation-Detection (wegen Edge-Filtering).
