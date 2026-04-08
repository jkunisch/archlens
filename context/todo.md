# ArchLens — Sprint-Backlog

> Aktuell: **Phase 1 Woche 1 — Engine + MCP + CLI** 🟡 AKTIV
> **PIVOT: Agent-First (D-011)**

---

## Phase 0: Spike (Tag 1–3) — ✅ ABGESCHLOSSEN

- [x] `pip install graphifyy` in lokaler venv
- [x] Dummy-Repo erstellen (5–10 Python-Dateien mit klarer Struktur)
- [x] Graphify AST-Pass ausführen → `base_graph.json` inspiziert
- [x] Absichtliche Boundary-Violation eingebaut
- [x] Graphify erneut → `head_graph.json`
- [x] Signal-to-Noise: 2/2 Violations erkannt, 0 Noise
- [x] Python-Import: Alle 6 Pfade verifiziert, kein subprocess nötig
- [x] **GO Entscheidung** ✔️
- [x] Kritischer Fund geloggt als D-009: Eigener Diff auf `extract()`, nicht `graph_diff()`

## Phase 0b: Schemas + Projektsetup — ✅ ABGESCHLOSSEN

- [x] pyproject.toml (pydantic als Base-Dep, D-008)
- [x] shared/schemas/ (Graph, Diff, Config, Violation, Job)
- [x] shared/constants/edge_types.py
- [x] 11 pytest Tests grün, mypy sauber, ruff sauber
- [x] Paketmarker action/, api/, dashboard/ angelegt → ✅ GO (D-008)

---

## Phase 1: Agent-First MVP (Wochen 1–3) 🟡 AKTIV

> **PIVOT (D-011):** MCP-Server ist primäres Interface. Dashboard verschoben auf Phase 2 (D-012).
> **D-009 beachten:** GraphifyAdapter nutzt `extract()`, nicht `graph_diff()` oder `build_from_json()`

### Woche 1 — Engine + MCP Server 🟡 JETZT
- [ ] Engine: GraphifyAdapter (`extract()`-basiert)
- [ ] Engine: config_parser.py (.archlens.yml Parser)
- [ ] Engine: violation_checker.py (forbid/warn/threshold)
- [ ] Engine: blast_radius.py (BFS Reverse-Traversal)
- [ ] Engine: edge_noise_filter.py (Cross-Cluster + Rule-Match)
- [ ] Engine: context_writer.py (archlens_context.json)
- [ ] MCP Server: server.py (5 Tools, 3 Resources, 1 Prompt)
- [ ] MCP Server: engine_bridge.py (Engine-Cache)
- [ ] pyproject.toml: mcp + cli Dependencies

### Woche 2 — CLI + Tests + Action 🔴 GESPERRT
- [ ] CLI: main.py (scan, report, serve)
- [ ] Tests: min. 20 Tests (Engine + MCP + CLI)
- [ ] GitHub Action: entrypoint.py (nutzt Engine-Library)
- [ ] GitHub Action: action.yml + Dockerfile
- [ ] MCP-Server in Claude Code testen
- [ ] Dogfooding: ArchLens auf eigenem Repo

### Woche 3 — Ship 🔴 GESPERRT
- [ ] README.md (MCP Setup-Anleitung)
- [ ] GitHub Marketplace Listing (Action)
- [ ] PyPI Publish (archlens)
- [ ] 5 Beta-User einladen (Agent-User, nicht PR-Reviewer)

---

## Phase 2: Dashboard + Memory (Wochen 4–8) 🔴 GESPERRT

- [ ] Next.js Dashboard + GitHub OAuth (D-012: verschoben aus Phase 1)
- [ ] FastAPI Backend + PostgreSQL
- [ ] Boiling Frog Tracker (Zep temporal queries)
- [ ] ADR-Matching
- [ ] Accept-Debt Workflow
- [ ] Trend-Charts
- [ ] Remote MCP Server (HTTP transport via API)

## Phase 3: Enterprise 🔴 GESPERRT

- [ ] CTO Health Dashboard
- [ ] AI Refactoring Hints
- [ ] Multi-SCM (GitLab, Bitbucket)
- [ ] SSO/SAML
