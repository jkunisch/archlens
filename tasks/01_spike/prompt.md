# Task 01: Graphify Spike — Go/No-Go Validation

> **Priorität:** 🔴 KRITISCH — Muss ZUERST abgeschlossen werden  
> **Geschätzter Aufwand:** 30–60 Minuten  
> **Empfohlener Agent:** Claude Code oder Gemini  
> **Arbeitsverzeichnis:** `C:\Users\Jonatan\Documents\projects_2026\archlens\spike\`

---

## Kontext

Wir bauen **ArchLens** — ein GitHub-natives SaaS, das bei jedem PR einen Knowledge Graph der Codebase baut (via Graphify AST-Pass), die Topologie difft, und architektonische Grenzverletzungen als PR-Kommentar surfaced.

**Graphify** (https://github.com/safishamsi/graphify, PyPI: `graphifyy`) wandelt Code-Ordner in queryable Knowledge Graphs um. Es nutzt tree-sitter AST-Parsing (19 Sprachen) + Leiden-Clustering. Kein LLM nötig für den Code-Pass.

Bevor wir irgendetwas bauen, müssen wir validieren:
1. Funktioniert Graphify's AST-Pass headless als Python-Import?
2. Ist der `graph_diff` Output brauchbar — klares Signal bei Boundary-Violations, kein Noise bei trivialen Änderungen?

---

## Deine Aufgabe

### Schritt 1: Environment Setup
```bash
cd C:\Users\Jonatan\Documents\projects_2026\archlens
python -m venv .venv
.venv\Scripts\activate
pip install graphifyy
```

### Schritt 2: Dummy-Repo erstellen

Erstelle in `spike/dummy_repo/` eine kleine Python-Codebase mit **klarer Schicht-Architektur**:

```
spike/dummy_repo/
├── frontend/
│   ├── __init__.py
│   ├── views.py          # Importiert NUR aus api/
│   └── components.py     # Importiert NUR aus frontend/
├── api/
│   ├── __init__.py
│   ├── routes.py          # Importiert aus services/
│   └── middleware.py      # Importiert aus api/
├── services/
│   ├── __init__.py
│   ├── payment.py         # Business-Logik, importiert aus database/
│   └── auth.py            # Business-Logik, importiert aus database/
├── database/
│   ├── __init__.py
│   ├── models.py          # SQLAlchemy-ähnliche Models
│   └── connection.py      # DB-Verbindung
└── utils/
    ├── __init__.py
    └── helpers.py          # Shared Utilities
```

**Wichtig:** Die Dateien müssen echte Imports und Funktionsaufrufe haben (nicht leere Files). Jede Datei sollte 10–30 Zeilen mit mindestens 2–3 Imports und 1–2 Funktionen haben. Die Imports müssen der Layer-Architektur folgen: `frontend → api → services → database`.

### Schritt 3: Graphify Base-Graph erzeugen

Versuche zuerst den Python-Import:
```python
# spike/test_graphify.py
from graphify.analyze import build_graph
# oder alternativ testen:
# from graphify import core
# oder: import graphify
```

Wenn der direkte Import scheitert, nutze subprocess als Fallback:
```python
import subprocess
result = subprocess.run(
    ["graphify", "spike/dummy_repo", "--no-viz"],
    capture_output=True, text=True
)
```

**Dokumentiere genau:**
- Welcher Import-Pfad funktioniert?
- Welche Argumente werden gebraucht?
- Wie sieht die graph.json-Struktur aus? (Knoten-Format, Edge-Format, Attribute)

Speichere das Ergebnis als `spike/base_graph.json`.

### Schritt 4: Boundary-Violation einbauen

Modifiziere `spike/dummy_repo/frontend/views.py` — füge einen **direkten Import aus database/** ein:

```python
# VIOLATION: Frontend greift direkt auf Database zu (sollte über api/ gehen)
from database.models import User
```

Füge optional eine zweite Violation ein in `spike/dummy_repo/frontend/components.py`:
```python
# VIOLATION: Frontend importiert aus services/ (sollte über api/ gehen)
from services.payment import process_payment
```

### Schritt 5: Head-Graph erzeugen + Diff

Erzeuge den neuen Graph nach der Violation und vergleiche:

```python
# Graph nach Violation
# head_graph = build_graph("spike/dummy_repo")  # oder subprocess

# Diff versuchen:
# from graphify.analyze import graph_diff
# diff = graph_diff(base_graph, head_graph)
```

Wenn `graph_diff` nicht als Funktion existiert, schreibe ein **manuelles Diff-Skript** (20–30 Zeilen):
```python
import json

with open("spike/base_graph.json") as f:
    base = json.load(f)
with open("spike/head_graph.json") as f:
    head = json.load(f)

base_edges = {(e["source"], e["target"], e.get("type", "unknown")) for e in base["edges"]}  
head_edges = {(e["source"], e["target"], e.get("type", "unknown")) for e in head["edges"]}

new_edges = head_edges - base_edges
removed_edges = base_edges - head_edges

print("=== NEUE EDGES ===")
for e in new_edges:
    print(f"  {e[0]} → {e[1]} ({e[2]})")

print("=== ENTFERNTE EDGES ===")
for e in removed_edges:
    print(f"  {e[0]} → {e[1]} ({e[2]})")
```

### Schritt 6: Signal-to-Noise bewerten

**Das ist der Lackmustest.** Beantworte in `spike/SPIKE_REPORT.md`:

1. **Signal:** Zeigt der Diff die 2 absichtlichen Violations klar als neue Edges?
   - `frontend/views.py → database/models.py` — sichtbar? ✅/❌
   - `frontend/components.py → services/payment.py` — sichtbar? ✅/❌

2. **Noise:** Wie viele ANDERE neue Edges zeigt der Diff, die NICHT die Violations sind?
   - 0 = perfekt
   - 1–3 = akzeptabel
   - 10+ = problematisch, brauchen wir Filter

3. **Graph-Struktur:** Dokumentiere das exakte JSON-Format von graph.json:
   - Wie heißen die Felder? (nodes, edges, links?)
   - Welche Attribute haben Nodes? (name, type, file, cluster?)
   - Welche Attribute haben Edges? (source, target, type, confidence?)

4. **Import-Pfad:** Welcher Python-Import hat funktioniert?
   - `from graphify.analyze import build_graph` → ✅/❌
   - `from graphify.core import ...` → ✅/❌
   - `subprocess.run(["graphify", ...])` → ✅/❌

5. **Go/No-Go Empfehlung:**
   - ✅ GO wenn: Signal klar, Noise < 5, Graph-Format dokumentiert
   - ❌ NO-GO wenn: Signal nicht erkennbar oder Noise > Signal
   - 🟡 GO MIT EINSCHRÄNKUNGEN wenn: Signal da aber Noise braucht Filtering

---

## Erwartetes Output

```
spike/
├── dummy_repo/           # 5-Ordner Python Codebase
│   ├── frontend/
│   ├── api/
│   ├── services/
│   ├── database/
│   └── utils/
├── test_graphify.py      # Import-Test + Graph-Build + Diff
├── base_graph.json       # Graph VOR Violation
├── head_graph.json       # Graph NACH Violation
├── diff_output.txt       # Diff-Ergebnis
└── SPIKE_REPORT.md       # Go/No-Go Report mit allen Antworten
```

---

## Regeln

- Lies `AGENTS.md` und `ARCHITECTURE.md` im Projekt-Root für vollen Kontext
- Dokumentiere ALLES was schiefgeht — Fehlermeldungen, fehlende Module, unerwartetes Verhalten
- Keine Änderungen außerhalb von `spike/`
- Wenn Graphify nicht installierbar ist oder fundamental nicht funktioniert → sofort SPIKE_REPORT.md schreiben mit NO-GO
