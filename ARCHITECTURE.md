# ArchLens — Architektur & Produkt-Referenz

> Letzte Aktualisierung: 2026-04-08  
> Status: Phase 0 — Spike

---

## Was wir bauen

**ArchLens** ist ein GitHub-natives SaaS-Produkt. Es erkennt automatisch, wenn die Architektur einer Codebase schleichend erodiert — bei jedem Pull Request.

### Das Problem

Codebases verfallen nicht durch eine große schlechte Entscheidung. Sie verfallen durch **1.000 kleine PRs**, die jeweils „okay" aussehen, aber in Summe die Architektur zerstören. Ein Frontend-Modul importiert plötzlich direkt aus der Datenbank-Schicht. Ein Service-Layer wird zum God-Object mit 47 eingehenden Dependencies. Kein einzelner PR ist schuld, aber nach 6 Monaten ist die Codebase Spaghetti.

**Kein bestehendes Tool erkennt das:**
- Code-Review checkt Syntax, Tests, Security — nicht Architektur-Topologie
- Sourcegraph/Copilot/Cursor suchen per Embedding — können aber keine Beziehungs-*Typen* modellieren
- Architektur-Diagramme veralten am Tag nachdem sie gezeichnet werden

### Die Lösung

ArchLens baut bei jedem PR automatisch einen **Knowledge Graph** der Codebase (via Graphify), **difft die Topologie** mit dem vorherigen Zustand, und postet einen Kommentar direkt im PR:

```
⚠️ ArchLens: 2 Architektur-Violations erkannt

🔴 FORBID: frontend/checkout.py → database/models.py
   Regel: "frontend/* darf nicht auf database/* zugreifen" (.archlens.yml:12)
   Lösung: Nutze den API-Layer (api/checkout_service.py)

🟡 WARN: services/payment.py hat jetzt 23 eingehende Edges (+3 in diesem PR)
   Blast Radius: Änderungen an diesem Node betreffen 4 Cluster
   Trend: +1.9 Edges/Woche über die letzten 8 PRs ← Boiling Frog Alert

┌──────────────┐     ┌──────────────┐
│  frontend/   │──🔴──▶│  database/   │   ← Verbotene Kante
│  checkout.py │      │  models.py   │
└──────────────┘      └──────────────┘
        │
        │ (erlaubt)
        ▼
┌──────────────┐
│  api/        │
│  checkout_   │
│  service.py  │
└──────────────┘
```

### Für wen

**Primärer Käufer:** Engineering Manager / Head of Platform in Firmen mit 50–5.000 Entwicklern.  
**Sekundärer Nutzer:** Staff Engineers, Tech Leads, Platform Teams.  
**Preis:** Free (1 Repo) → Pro $29/user/Monat → Enterprise Custom.

---

## Architektur-Übersicht

Das System hat **5 isolierte Komponenten**. Keine darf Code aus einer anderen importieren.

```
══════════════════════════════════════════════════════════════════════════════
            KUNDEN-INFRASTRUKTUR                    ARCHLENS CLOUD
         (Quellcode verlässt hier NIE)
══════════════════════════════════════════════════════════════════════════════

 ┌─────────────────────────────────────┐
 │       GitHub Action Runner          │
 │                                     │
 │   1. git checkout base              │
 │      → Graphify AST-Pass            │
 │      → base_graph.json              │
 │                                     │
 │   2. git checkout head              │
 │      → Graphify AST-Pass            │
 │      → head_graph.json              │
 │                                     │
 │   3. .archlens.yml laden            │
 │      → Hard-Violations → CI FAIL    │
 │                                     │
 │   4. graph.json + violations.json   │         ┌──────────────────┐
 │      ─────── HTTPS Upload ──────────│────────▶│  API Server      │
 │      (NUR Metadaten, kein Code!)    │         │  (FastAPI)       │
 │                                     │         │                  │
 └─────────────────────────────────────┘         │  Empfängt:       │
                                                  │  • graph.json    │
                                                  │  • violations    │
                                                  │                  │
                                                  │  Speichert in:   │
                                                  │  PostgreSQL      │
                                                  │                  │
                                                  │  Dispatcht:      │
                                                  │  Worker Job      │
                                                  └────────┬─────────┘
                                                           │
                                                  ┌────────▼─────────┐
 ┌─────────────────────────────────────┐         │  Worker          │
 │       GitHub PR                     │         │  (Redis + RQ)    │
 │                                     │         │                  │
 │   ← PR-Kommentar (Mermaid-Diagramm)│◀────────│  • graph_diff    │
 │   ← CI-Status (✅ pass / ❌ fail)   │         │  • leiden_cluster│
 │                                     │         │  • blast_radius  │
 └─────────────────────────────────────┘         │  • mermaid_render│
                                                  │  • compose_      │
                                                  │    pr_comment    │
                                                  │  • GitHub API    │
 ┌─────────────────────────────────────┐         │    → post comment│
 │       Dashboard (Next.js)           │         └────────┬─────────┘
 │                                     │                  │
 │   • Login via GitHub OAuth          │         ┌────────▼─────────┐
 │   • Repo-Liste + Aktivierung       │         │  PostgreSQL      │
 │   • PR-History + Violation-Log      │◀────────│                  │
 │   • Graph-Viewer (interaktiv)       │  REST   │  • tenants       │
 │   • Diff-View (Before/After)        │  API    │  • repos         │
 │   • Trend-Charts (Phase 2)          │         │  • graph_        │
 │                                     │         │    snapshots     │
 └─────────────────────────────────────┘         │  • jobs          │
                                                  │  • violations    │
                                                  │  • pr_comments   │
                                                  └────────┬─────────┘
                                                           │
                                                  ┌────────▼─────────┐
                                                  │  Zep / Graphiti  │
                                                  │  (Phase 2)       │
                                                  │                  │
                                                  │  Temporal Memory:│
                                                  │  • "Node X bekam │
                                                  │    3 neue Edges  │
                                                  │    in PR #143"   │
                                                  │  • "Violation    │
                                                  │    akzeptiert    │
                                                  │    am 15.04."    │
                                                  │  • Boiling Frog  │
                                                  │    Trend-Daten   │
                                                  └──────────────────┘
```

---

## Komponenten im Detail

### 1. `action/` — GitHub Action (läuft beim Kunden)

**Was es tut:** Scannt den Code des Kunden bei jedem PR. Erzeugt den Knowledge Graph lokal. Nur die Metadaten (Knotennamen, Edge-Typen, Cluster-IDs) werden an unsere API geschickt — **niemals Quellcode**.

**Technologie:** Docker-basierte GitHub Action, Python, Graphify (pip install graphifyy)

**Dateien:**
```
action/
├── action.yml          # GitHub Action Definition (inputs, outputs)
├── Dockerfile          # Python 3.11 + graphifyy + Dependencies
└── entrypoint.py       # Hauptskript:
                        #   1. Checkout base & head
                        #   2. Graphify AST-Pass (2x)
                        #   3. .archlens.yml parsen
                        #   4. Hard-Violations prüfen → CI fail
                        #   5. graph.json + violations.json → API upload
```

**Kritisch zu verstehen:** Der AST-Pass ist **deterministisch** (kein LLM). Er analysiert Imports, Funktionsaufrufe, Klassen-Hierarchien, Docstrings über 19 Programmiersprachen via tree-sitter. Das Ergebnis ist ein NetworkX-Graph mit getypten Edges (`calls`, `imports`, `implements`, `depends_on`).

---

### 2. `api/` — FastAPI Backend (unser Server)

**Was es tut:** Empfängt graph.json vom Action Runner, speichert Snapshots, dispatcht Worker-Jobs, bedient das Dashboard per REST API.

**Technologie:** Python 3.11, FastAPI, PostgreSQL, Pydantic v2

**Dateien:**
```
api/
├── main.py                  # FastAPI App + Middleware
├── config.py                # Environment-basierte Config
├── models/
│   ├── tenant.py            # Organisation/Team
│   ├── repo.py              # GitHub-Repo Referenz
│   ├── snapshot.py          # Graph-Snapshot (graph.json gespeichert)
│   ├── job.py               # Worker-Job Tracking
│   └── violation.py         # Erkannte Violations
├── routes/
│   ├── intake.py            # POST /intake — graph.json Upload
│   ├── repos.py             # GET /repos — Repo-Liste
│   ├── history.py           # GET /history — Snapshot-Verlauf
│   └── auth.py              # GitHub OAuth Callback
└── workers/
    ├── diff_worker.py       # graph_diff + Analyse
    ├── comment_worker.py    # PR-Kommentar erstellen + posten
    └── mermaid_renderer.py  # Graph-Diff → Mermaid Markdown
```

---

### 3. `dashboard/` — Next.js Frontend

**Was es tut:** Web-UI für Teams. Zeigt Repos, PR-History, Graph-Viewer, Violation-Trends.

**Technologie:** Next.js 14 (App Router), TypeScript, shadcn/ui, GitHub OAuth

**Dateien:**
```
dashboard/
├── app/
│   ├── layout.tsx           # Root Layout + Theme
│   ├── page.tsx             # Landing / Login
│   ├── dashboard/
│   │   ├── page.tsx         # Repo-Übersicht
│   │   └── [repo]/
│   │       ├── page.tsx     # Repo-Detail + PR-Liste
│   │       ├── graph/
│   │       │   └── page.tsx # Interaktiver Graph-Viewer
│   │       └── pr/
│   │           └── [id]/
│   │               └── page.tsx  # PR-Diff-Ansicht
│   └── settings/
│       └── page.tsx         # Team-Settings, Billing
├── components/
│   ├── graph-viewer.tsx     # Eingebettetes graph.html
│   ├── diff-view.tsx        # Before/After Cluster-Vergleich
│   ├── violation-card.tsx   # Einzelne Violation anzeigen
│   ├── blast-radius.tsx     # Abhängigkeits-Visualisierung
│   └── mermaid-preview.tsx  # Mermaid-Diagramm Renderer
└── lib/
    ├── api-client.ts        # Typisierter API-Client
    └── auth.ts              # GitHub OAuth Handling
```

---

### 4. `shared/` — Geteilte Typen

**Was es tut:** Definiert die Datenstrukturen die zwischen Komponenten ausgetauscht werden. **Keine Business-Logik.**

```
shared/
├── schemas/
│   ├── graph_schema.py      # GraphNode, GraphEdge, GraphSnapshot
│   ├── violation_schema.py  # Violation, ViolationType, Severity
│   ├── diff_schema.py       # DiffResult, AddedEdge, RemovedEdge
│   ├── config_schema.py     # ArchLensConfig (.archlens.yml Struktur)
│   └── job_schema.py        # JobStatus, JobResult
└── constants/
    └── edge_types.py        # CALLS, IMPORTS, IMPLEMENTS, DEPENDS_ON...
```

---

### 5. Zep/Graphiti — Temporal Memory (Phase 2)

**Was es tut:** Speichert zeitliche Fakten über die Evolution der Codebase. Ermöglicht Trend-Erkennung und kontextuelle PR-Kommentare.

**Warum erst Phase 2:** Zep braucht historische Daten. Ohne 20+ Snapshots über Wochen ist jede Trend-Analyse sinnlos. In Phase 1 speichern wir Snapshots simpel in Postgres.

**Was Zep in Phase 2 ermöglicht:**

| Feature | Wie Zep es ermöglicht |
|---|---|
| **Boiling Frog Tracker** | Query: "Alle Edge-Additions an Node X in den letzten 30 Tagen" → Trend berechnen → Alert wenn Schwelle überschritten |
| **Accept-Debt Workflow** | Fakt speichern: "Violation Y wurde akzeptiert von @alice am 15.04 in PR #143" → bei nächstem Scan nicht erneut melden |
| **ADR-Matching** | Fakt: "ADR-004 verbietet frontend→database" + Fakt: "PR #150 bricht ADR-004" → Kontext im PR-Kommentar |
| **Smart Reviewer** | Fakt: "User @bob hat 85% der Commits in Cluster 'payment' gemacht" → Auto-Tag als Reviewer |

---

## Features nach Phase

### Phase 0 — Spike (jetzt aktiv, 3 Tage)

| Feature | Beschreibung | Status |
|---|---|---|
| Graphify testen | `pip install graphifyy`, AST-Pass auf Dummy-Repo, graph.json inspizieren | 🔴 Offen |
| graph_diff testen | Absichtliche Boundary-Violation → Diff → Signal-to-Noise bewerten | 🔴 Offen |
| Python-Import prüfen | `from graphify import ...` vs. `subprocess.run(["graphify", ...])` | 🔴 Offen |
| **Go/No-Go** | Ist das Signal gut genug für ein Produkt? | 🔴 Entscheidung |

**Checkpoint 0:** Wenn der graph_diff bei einer absichtlichen Boundary-Violation eine klare, actionable Edge zeigt ohne Signal-Noise → ✅ GO. Sonst → Pivot oder Graphify-Patch.

---

### Phase 1 — MVP (4 Wochen, nach Go)

| # | Feature | Was der User sieht | Technisch |
|---|---------|---------------------|-----------|
| **F1** | `.archlens.yml` Guardrails | Tech Lead definiert: `forbid: frontend/* -> database/*`. CI failed wenn verletzt. | YAML-Parser, Glob-Matching auf Graph-Edges |
| **F2** | PR-Kommentar mit Violations | Markdown-Kommentar im PR: welche Regeln gebrochen, welche Edges neu | Worker → GitHub API → PR Comment |
| **F3** | Mermaid-Diagramm im PR | Visueller 3-5 Node Diff-Graph direkt im PR-Kommentar. Rot = verboten, gelb = Warnung | Graph-Diff → Mermaid-Syntax → GitHub rendert nativ |
| **F4** | Blast Radius | "Du änderst Node X, davon hängen 47 Nodes in 4 Clustern ab" | Graph-Traversal (BFS) von geänderten Nodes |
| **F5** | CI-Status | ✅ pass oder ❌ fail basierend auf .archlens.yml | GitHub Checks API |
| **F6** | Dashboard | Web-UI: Repos aktivieren, PR-History ansehen, Graph-Viewer | Next.js + GitHub OAuth |
| **F7** | Graph-Viewer | Interaktiver Knowledge Graph im Browser (Graphify's graph.html) | iframe/sandbox Embedding |

**Checkpoint 1:** Erster zahlender Kunde ODER 5 aktive Beta-User.

---

### Phase 2 — Memory & Intelligenz (Wochen 5–8)

| # | Feature | Was der User sieht | Technisch |
|---|---------|---------------------|-----------|
| **F8** | Boiling Frog Tracker | "⚠️ Node X hat über 12 PRs 23 neue Edges angesammelt. Trend: +1.9/Woche" | Zep temporal query über Snapshots |
| **F9** | ADR-Matching | "Diese Kante verletzt ADR-004 vom Mai 2025. Nutze den API-Layer." | Markdown-Parse von docs/adr/ + Graph-Edge-Match |
| **F10** | Accept-Debt | `/archlens accept-debt` im PR → Violation temporär akzeptiert, Ticket erstellt | PR Comment Command → Zep Fakt → Jira/Linear API |
| **F11** | Smart Reviewer | Auto-Tag des Cluster-Owners wenn ein PR in fremden Cluster greift | CODEOWNERS + Leiden-Cluster-Mapping |
| **F12** | Trend-Charts | Dashboard zeigt: Graph-Komplexität, Cluster-Stabilität, Violation-Rate über Zeit | Zeitreihen aus Postgres/Zep |

**Checkpoint 2:** 10+ aktive Kunden, Boiling Frog hat echten Drift bei mindestens 3 Kunden erkannt.

---

### Phase 3 — Enterprise (Monat 3+)

| # | Feature | Was der User sieht | Technisch |
|---|---------|---------------------|-----------|
| **F13** | CTO Health Dashboard | Aggregierter "Architecture Health Score" pro Repo/Team | Score aus: Violations, Trends, God Nodes, Cluster-Stabilität |
| **F14** | AI Refactoring Hints | "Pattern-Empfehlung: Führe ein Interface ein um Module X und Y zu entkoppeln" | LLM (Claude) mit isoliertem Sub-Graph als Input |
| **F15** | Multi-SCM | GitLab, Bitbucket Support | Abstraktions-Layer über SCM-APIs |
| **F16** | SSO/SAML | Enterprise Login | Auth-Provider Integration |
| **F17** | On-Prem | Self-hosted Docker Image | Alles in einem Container |

**Checkpoint 3:** Enterprise-Pipeline existiert, erster Enterprise-Vertrag unterzeichnet.

---

## Tech Stack Zusammenfassung

```
┌─────────────┬──────────────────────────────────┬──────────┐
│  Schicht    │  Technologie                     │  Warum   │
├─────────────┼──────────────────────────────────┼──────────┤
│  Engine     │  Graphify (graphifyy via PyPI)    │ AST→Graph│
│  Action     │  Docker + Python 3.11            │ CI-native│
│  Backend    │  FastAPI + Pydantic v2            │ Async    │
│  Queue      │  Redis + RQ                      │ Simpel   │
│  Datenbank  │  PostgreSQL                      │ Relational│
│  Frontend   │  Next.js 14 + shadcn/ui          │ Modern   │
│  Memory     │  Zep/Graphiti (Phase 2)          │ Temporal │
│  Hosting    │  Railway / Fly.io (Phase 1)      │ Schnell  │
│  Storage    │  Cloudflare R2                   │ Günstig  │
│  Auth       │  GitHub OAuth                    │ Native   │
│  Billing    │  Stripe                          │ Standard │
│  Monitoring │  Sentry + BetterUptime           │ Standard │
└─────────────┴──────────────────────────────────┴──────────┘
```

---

## .archlens.yml — Format-Spezifikation

Die Datei lebt im Root des Kunden-Repos. Sie definiert Architektur-Regeln.

```yaml
# .archlens.yml — ArchLens Konfiguration
version: 1

# Harte Regeln: CI failed bei Verstoß
forbid:
  - from: "frontend/*"
    to: "database/*"
    message: "Frontend darf nicht direkt auf die Datenbank zugreifen. Nutze den API-Layer."

  - from: "services/*"
    to: "tests/*"
    message: "Services dürfen keine Test-Utilities importieren."

# Weiche Warnungen: PR-Kommentar, kein CI-Fail
warn:
  - from: "api/*"
    to: "internal/*"
    message: "API-Layer sollte nicht auf interne Module zugreifen."

# Schwellenwerte
thresholds:
  # Maximale eingehende Edges pro Node bevor Warnung
  god_node_warn: 15
  god_node_fail: 30

  # Maximale Cluster-übergreifende Edges pro PR
  cross_cluster_warn: 5
  cross_cluster_fail: 10

# Ignorierte Pfade (werden nicht gescannt)
ignore:
  - "vendor/*"
  - "node_modules/*"
  - "*.generated.*"
  - "migrations/*"
```

---

## Schlüsselprinzipien (Kurzform)

| # | Prinzip | Bedeutung |
|---|---------|-----------|
| **P1** | Zero-Code-Egress | Kundencode verlässt nie deren CI-Runner |
| **P2** | Determinismus vor LLM | Kein LLM wo Graph-Traversal reicht |
| **P3** | Diff ist das Produkt | Das Signal zählt, nicht der Graph |
| **P4** | Config-as-Code | Regeln in .archlens.yml, nicht im Dashboard |
| **P5** | Bounded Components | 5 Module, keine Cross-Imports |
| **P6** | Dogfooding | ArchLens scannt sich selbst ab Woche 2 |

---

## Dein Fokus als Gründer

```
Phase 0 (jetzt):     Ist das Signal gut genug? → Spike ausführen
Phase 1 Woche 1-2:   Engine bauen — das ist das Herz des Produkts
Phase 1 Woche 3:     Dashboard bauen — das ist der Sales-Funnel  
Phase 1 Woche 4:     Ship & Beta-Kunden finden
Phase 2:             Memory einbauen — das wird der Moat
Phase 3:             Enterprise — das wird das Geld
```

**Die eine Sache die ALLES entscheidet:** Ob der `graph_diff` bei echtem Code ein klares, actionable Signal liefert. Alles andere ist nachgelagert. Deshalb Spike zuerst.
