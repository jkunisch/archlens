# AGENTS.md — ArchLens Project Rules

> Architecture Context Layer for Coding Agents. (Pivot D-011)

---

## §1 Projekt-Überblick

**ArchLens** ist ein Architecture Context Layer für Coding-Agents. Es gibt AI-Agents (Cursor, Claude Code, Codex, Gemini) Architektur-Awareness — proaktiv via MCP-Server, bevor sie Code schreiben. Sekundär: PR-Kommentare und CLI-Reports für menschliche Überwachung.

**Kern-Value-Prop:** "Deine Coding-Agents kennen deine Architektur-Regeln — bevor sie Code schreiben, nicht danach."

**Business Model:** Open-Core. MCP Server + CLI (Free) → SaaS Dashboard + History (Pro) → Enterprise (Custom).

---

## §2 Architektur-Prinzipien (unveränderlich)

### P1: Zero-Code-Egress
Der Quellcode des Kunden verlässt NIEMALS dessen Infrastruktur. Graphify läuft im GitHub Action Runner. Nur `graph.json` (Metadaten: Knoten-Namen, Edge-Typen, Cluster-IDs) wird an unsere API übertragen. Kein Token, kein Snippet, kein AST-Fragment.

### P2: Determinismus vor LLM
Jedes Feature das deterministisch lösbar ist, wird deterministisch gelöst. LLM-Aufrufe NUR wenn Graph-Traversal allein nicht reicht. Reihenfolge: AST → Graph-Traversal → Heuristik → LLM (letzter Ausweg).

### P3: Graph-Diff ist das Produkt
Nicht der Graph selbst. Niemand zahlt für einen Knowledge Graph. Leute zahlen für: "In diesem PR bricht etwas." Die Engine ist Commodity, das Signal ist das Produkt.

### P4: Config-as-Code (.archlens.yml)
Architektur-Regeln leben im Repository des Kunden, nicht in unserem Dashboard. Versioniert, reviewbar, auditierbar. Genau wie `.eslintrc` oder `CODEOWNERS`.

### P5: Bounded Components
7 harte Grenzen im System:

```
┌─────────────┐  ┌───────────┐  ┌─────────────┐
│  action/     │  │  mcp/      │  │  cli/        │
│ (Engine +    │  │ (MCP       │  │ (Human       │
│  GitHub CI)  │  │  Server)   │  │  Oversight)  │
│              │  │            │  │              │
│ Graphify +   │  │ 5 Tools,   │  │ scan,        │
│ .archlens.yml│  │ 3 Resources│  │ report,      │
│ Violation    │  │ Agent-First │  │ serve        │
│ Checker      │  │            │  │              │
└──────┬───────┘  └─────┬──────┘  └──────┬───────┘
       │                │                │
       └────────────────┴────────────────┘
                        │
              ┌─────────▼─────────┐
              │  shared/schemas/   │
              └────────────────────┘

          Phase 2:
┌──────────────┐  ┌───────────┐  ┌─────────────┐
│   api/        │  │  worker/  │  │  dashboard/ │
│  (FastAPI)    │  │ (RQ+Redis)│  │ (Next.js)   │
└──────────────┘  └───────────┘  └─────────────┘
```

**REGEL:** Kein Cross-Import zwischen Bounded Components. `action/` ist die Engine-Library. `mcp/` und `cli/` importieren aus `action/` (Engine) und `shared/schemas/`. Jedes Modul ist eigenständig deploybar.

### P6: Eat Our Own Dogfood
ArchLens läuft auf dem ArchLens-Repo ab Woche 2. Jeder PR wird vom eigenen Tool gescannt.

---

## §3 Model Lock

| Zweck | Erlaubtes Modell | Begründung |
|-------|------------------|------------|
| Code-Generierung | Gemini 2.5 Pro, Claude Sonnet/Opus 4 | Kosten-Balance |
| PR-Kommentar-Rendering | KEIN LLM — deterministisch | P2 |
| Refactoring-Hints (Phase 3) | Claude Sonnet 4 | Präzision bei Code |
| Research/Planung | Beliebig | Unkritisch |

---

## §4 Bounded Contexts — Wer darf was?

### `action/` — Engine + GitHub Action (Kunden-CI)
- DARF: Graphify importieren, .archlens.yml parsen, graph.json erzeugen, Violations prüfen, Blast Radius berechnen
- DARF NICHT: Datenbank-Zugriff, Dashboard-Code, User-Daten, MCP-Protokoll

### `mcp/` — MCP Server (Agent-Interface) ← NEU (D-011)
- DARF: Engine aus `action/` importieren, `shared/schemas/` importieren, MCP-Tools/Resources exponieren
- DARF NICHT: Graphify direkt importieren (→ via Engine), Datenbank-Zugriff, GitHub API

### `cli/` — CLI (Human-Oversight) ← NEU (D-013)
- DARF: Engine aus `action/` importieren, `shared/schemas/` importieren, Terminal-Output formatieren
- DARF NICHT: Graphify direkt importieren (→ via Engine), MCP-Protokoll, Datenbank-Zugriff

### `api/` — FastAPI Backend (Phase 2)
- DARF: graph.json empfangen, Postgres lesen/schreiben, Worker-Jobs dispatchen
- DARF NICHT: Graphify importieren, GitHub API direkt aufrufen (→ Worker), Frontend-Code

### `dashboard/` — Next.js Frontend (Phase 2)
- DARF: API aufrufen, graph.html einbetten, User-Session verwalten
- DARF NICHT: Backend-Logik, direkte DB-Zugriffe, Worker-Logik

### `shared/` — Shared Schemas
- DARF: TypedDict/Pydantic-Schemas, Konstanten, Enums
- DARF NICHT: Business-Logik, Imports aus anderen Modulen, I/O

---

## §5 Dateistruktur

```
archlens/
├── AGENTS.md                    # Diese Datei
├── GEMINI.md                    # Globale Agent-Regeln
├── .cursorrules                 # Cursor IDE Regeln
├── context/
│   ├── decisions.md             # Append-only Entscheidungslog
│   ├── todo.md                  # Sprint-Backlog
│   ├── brief.md                 # Aktueller Projektstatus
│   └── agents.md                # Multi-Agent Claims
│
├── action/                      # Engine + GitHub Action
│   ├── graphify_adapter.py      # Graphify Abstraktions-Layer (D-009)
│   ├── config_parser.py         # .archlens.yml Parser
│   ├── violation_checker.py     # forbid/warn/threshold Checks
│   ├── blast_radius.py          # BFS Reverse-Traversal
│   ├── edge_noise_filter.py     # Signal-to-Noise Filter
│   ├── context_writer.py        # archlens_context.json Writer
│   ├── entrypoint.py            # GitHub Action Entrypoint
│   ├── action.yml               # GitHub Action Definition
│   └── Dockerfile               # Action Container
│
├── mcp/                         # MCP Server (D-011) ← Agent-First
│   ├── server.py                # FastMCP: 5 Tools, 3 Resources, 1 Prompt
│   └── engine_bridge.py         # Engine-Cache Bridge
│
├── cli/                         # CLI (D-013) ← Human Oversight
│   └── main.py                  # scan, report, serve Commands
│
├── api/                         # FastAPI Backend (Phase 2)
├── dashboard/                   # Next.js Frontend (Phase 2)
│
├── shared/                      # Shared Types only
│   ├── schemas/
│   └── constants/
│
└── spike/                       # Phase 0: Technical Spike
    └── test_graphify.py
```

---

## §6 Handoff-Format

Bei Task-Übergabe zwischen Agents:

```markdown
## Handoff: [Task-Name]
- **Von:** [Agent-ID]
- **An:** [Agent-ID oder "Nächster"]
- **Status:** [done | blocked | partial]
- **Was erledigt:** [Bullet Points]
- **Was offen:** [Bullet Points]
- **Kritische Warnung:** [Falls relevant]
- **Dateien berührt:** [Liste]
```

---

## §7 Qualitäts-Gates

Kein PR wird gemerged ohne:
1. ✅ Alle bestehenden Tests grün
2. ✅ Kein neuer Cross-Component-Import (P5)
3. ✅ `context/decisions.md` aktualisiert bei architektonischen Änderungen
4. ✅ Ab Woche 2: ArchLens eigener Scan bestanden (P6)
