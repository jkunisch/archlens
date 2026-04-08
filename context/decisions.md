# ArchLens — Entscheidungslog

> Append-only. Nie löschen, nie editieren. Neueste unten.

---

## D-001: Projektname (2026-04-08)
**Entscheidung:** ArchLens
**Begründung:** "Architecture Lens" ist selbsterklärend für Engineering Leads. GitLens-Analogie funktioniert. Domain-Check steht noch aus (archlens.dev, archlens.io).
**Alternativen verworfen:** DriftMap (ML-Kollision), TopoDiff (zu akademisch), GraphGuard (Security-Konnotation), StructureCI (generisch)

## D-002: Graphify als Blackbox, kein Fork (2026-04-08)
**Entscheidung:** `pip install graphifyy` als Dependency. Kein Fork.
**Begründung:** MIT-Lizenz erlaubt kommerzielle Nutzung. Wartungsaufwand eines Forks ist nicht tragbar für ein 1-Person-Team. Fork-Option bleibt als Fallback.
**Risiko:** Wenn Graphify Breaking Changes macht oder abandoned wird → dann forken.

## D-003: Zero-Code-Egress als Architektur-Prinzip (2026-04-08)
**Entscheidung:** Graphify läuft ausschließlich im GitHub Action Runner des Kunden. Nur graph.json (Metadaten) wird übertragen.
**Begründung:** Eliminiert Enterprise-Security-Reviews. Kundencode verlässt nie deren Infrastruktur.
**Implikation:** Kein "hosted scan" Feature. Immer CI-basiert.

## D-004: Determinismus vor LLM (2026-04-08)
**Entscheidung:** Kein LLM-Aufruf in Phase 1. Alles AST-basiert und Graph-Traversal.
**Begründung:** Reproduzierbarkeit, Kosteneffizienz, Vertrauen. LLM-generierte PR-Kommentare die falsch sind zerstören Trust sofort.
**Ausnahme:** Phase 3 — Refactoring-Hints (Pattern-basiert, keine Code-Patches).

## D-005: .archlens.yml als Regel-Format (2026-04-08)
**Entscheidung:** YAML-basierte Config im Kunden-Repo. Syntax: `forbid:`, `warn:`, `threshold:`.
**Begründung:** Config-as-Code. Versioniert, reviewbar. Kein Dashboard-Lock-in.
**Vorbild:** .eslintrc, CODEOWNERS, .github/dependabot.yml

## D-006: Phase 1 Scope-Lock (2026-04-08)
**Entscheidung:** Phase 1 = nur Code + Markdown. Kein Bild/PDF-Support. Kein LLM. Kein Neo4j. Kein Multi-SCM.
**Begründung:** Der multimodale Pass steckt im Agent-Skill (nicht headless). AST-Pass ist vollständig headless und deterministisch. Scope-Disziplin > Feature-Completeness.

## D-007: 10-Punkte-Bewertung (2026-04-08)
**Tier A (MVP):** .archlens.yml Guardrails, Mermaid PR-Visuals, Zero-Code-Egress, Predictive Blast Radius
**Tier B (Phase 2):** ADR-Matching, Boiling Frog Tracker, Accept-Debt Workflow, Smart Reviewer Tagging
**Tier C (Phase 3+):** AI Auto-Fix Suggestions, CTO Health Dashboard
**Begründung:** Siehe implementation_plan.md für detaillierte Bewertung jedes Punktes.

## D-008: Pydantic als Basis-Dependency (2026-04-08)
**Entscheidung:** `pydantic` ist Base-Dependency im Projektroot, nicht nur im `api`-Extra.
**Begründung:** `shared/schemas/` und `tests/` benötigen Pydantic direkt. Es macht keinen Sinn eine Kernbibliothek als optionales Extra zu deklarieren wenn sie im gemeinsamen Vertrag gebraucht wird.
**Abweichung von:** Task 02 Prompt — dort stand `pydantic` im `api`-Extra

## D-009: Eigener Import-Diff statt graph_diff() — KRITISCH (2026-04-08)
**Entscheidung:** ArchLens baut einen eigenen Diff auf Basis der rohen `extract()`-Ausgabe. `graphify.analyze.graph_diff()` wird NICHT genutzt.
**Begründung:** `build_from_json()` erzeugt einen ID-Mismatch: Import-Edges referenzieren Target-IDs wie `database_models` während Nodes als `models` gelistet sind. Diese Filter-Eigenheit entfernt genau die Edges die wir brauchen. Die rohe `extract()`-Ausgabe enthält alle Kanten korrekt.
**Implikation:** `GraphifyAdapter._normalize()` muss auf `extract(collect_files())` aufbauen. Edge-Felder: `relation`, `source_file`, `confidence`. Edges in `links` (nicht `edges`). Nodes: `label` (nicht `name`).
**Dokumentiert in:** spike/SPIKE_REPORT.md

## D-010: Drift-Informationen müssen Agent-konsumierbar sein (2026-04-08)
**Entscheidung:** ArchLens gibt Drift-Daten in zwei Formaten aus: (A) Markdown für Menschen (PR-Kommentar), (B) `archlens_context.json` für Coding-Agents und Projekt-Agents.
**Begründung:** Wenn Coding-Agents (Claude Code, Cursor, Codex, Gemini) die Drift-Informationen nicht als strukturierten Kontext erhalten, bleibt ArchLens ein reines Review-Tool. Der echte Moat ist: Agents handeln auf Basis von Architektur-Kontext BEVOR sie Code schreiben.
**Phase 1 (kostenlos):** GitHub Action schreibt `archlens_context.json` als Workflow-Artifact + in `GITHUB_STEP_SUMMARY`. Agents im selben CI-Pipeline können es lesen.
**Phase 2 (MCP Server):** ArchLens API exposiert `/mcp`-Endpoint nach MCP-Protokoll (Graphify hat bereits MCP-Support, wir kennen das Format). Tool-Calls: `get_drift_context(file)`, `get_violations(repo, sha)`, `get_blast_radius(node)`.
**Format archlens_context.json:** Maschinenlesbar, mit context-ready Sätzen für LLM-Injection (nicht nur Rohdaten).


## D-008: Graphify Spike — GO (2026-04-08)
**Entscheidung:** ✅ GO. Graphify's AST-Pass liefert klares, noise-freies Signal für Layer-Violation-Detection.
**Begründung:** 2 injizierte Boundary-Violations (frontend→database, frontend→services) werden als exakt 2 neue `imports_from`-Edges erkannt. 0 Noise. Python-Import funktioniert (kein subprocess nötig). Alle 6 API-Module (extract, build, cluster, analyze, export, graphify) importierbar.
**Evidenz:** `spike/SPIKE_REPORT.md`, `spike/test_import_diff.py`

## D-009: Import-Diff auf Extraction-Ebene, nicht NetworkX (2026-04-08)
**Entscheidung:** ArchLens's Layer-Violation-Detection arbeitet auf der rohen Extraction (`graphify.extract.extract()`), NICHT auf dem NetworkX-Graph (`graphify.build.build_from_json()`).
**Begründung:** `build_from_json()` filtert Import-Edges als "dangling" heraus, weil Import-Target-IDs (z.B. `database_models`) nicht mit Node-IDs (z.B. `models`) matchen. Die rohe Extraction enthält alle Imports korrekt. NetworkX-Graph wird weiterhin für Clustering, Blast Radius und Visualisierung genutzt.
**Risiko:** Wenn Graphify das ID-Schema ändert, muss unser Import-Diff angepasst werden. Fork-Option bleibt Fallback.

## D-010: Konfigurationsschlüssel `thresholds` wird pluralisiert (2026-04-08)
**Entscheidung:** Der Root-Schlüssel in `.archlens.yml` heißt `thresholds`.
**Begründung:** `ARCHITECTURE.md` und die Shared-Schemas verwenden bereits die Pluralform für mehrere numerische Grenzwerte. Das vermeidet einen unnötigen Sonderfall im Datenvertrag zwischen Action, API und Worker.
**Implikation:** Neue Implementierungen und Beispiele verwenden ausschließlich `thresholds:`.

## D-011: Agent-First Pivot — MCP Server als primäres Auslieferungsformat (2026-04-08)
**Entscheidung:** ArchLens pivotiert von "PR-Review-Tool für Menschen" zu "Architecture Context Layer für Coding-Agents". Der MCP-Server (`mcp/`) wird das primäre Interface. PR-Kommentare werden zum Bonus-Feature.
**Begründung:** Kein Coding-Agent (Cursor, Claude Code, Codex) hat heute Architektur-Awareness. Agents schreiben Code der "funktioniert" aber Struktur zerstört. ArchLens wird der Layer der Agents ihre Architektur-Grenzen beibringt — proaktiv, vor dem Code-Schreiben. Markt-Timing: MCP-Ökosystem explodiert, Agent-Adoption ist Mainstream.
**Implikation:** `mcp/` als neuer Bounded Context. 5 MCP-Tools: `check_boundaries`, `get_violations`, `get_blast_radius`, `get_architecture_rules`, `get_drift_summary`. 3 Resources. 1 Prompt-Template. Engine wird als wiederverwendbare Library refactored.

## D-012: Dashboard auf Phase 2 verschoben (2026-04-08)
**Entscheidung:** Next.js Dashboard wird in Phase 1 nicht gebaut. Human-Oversight kommt über CLI (`archlens scan`, `archlens report`) und PR-Kommentare.
**Begründung:** Dashboard kostet ~7 Tage Solo-Arbeit und ist nicht der differenzierende Faktor. CLI-Output reicht als Wirkungsnachweis für Menschen. Spart Scope und fokussiert auf den Agent-Moat.
**Implikation:** Dashboard-Tasks in todo.md nach Phase 2 verschoben. `cli/` als neuer Bounded Context.

## D-013: CLI als Human-Oversight-Layer (2026-04-08)
**Entscheidung:** `archlens scan [path]` und `archlens report [path]` liefern menschenlesbaren Output. `archlens serve` startet den MCP-Server.
**Begründung:** Menschen müssen die Wirkung von ArchLens prüfen können ohne Dashboard. CLI ist der schnellste Weg dahin. Rich-formatierter Terminal-Output + Markdown-Reports.
**Implikation:** Dependencies: `click>=8.0`, `rich>=13.0` im `[cli]` Extra.
