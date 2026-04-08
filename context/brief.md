# ArchLens — Projektstatus

> Letztes Update: 2026-04-08

---

## Status: 🔄 PIVOT — Agent-First (D-011)

**Was ist ArchLens?**
Architecture Context Layer für Coding-Agents. Gibt AI-Agents (Cursor, Claude Code, Codex) Architektur-Awareness — bevor sie Code schreiben, nicht danach. Sekundär: PR-Kommentare und CLI-Reports für menschliche Überwachung.

**Pivot-Begründung:**
Kein Coding-Agent kennt heute Architektur-Grenzen. Agents erzeugen den Architecture Drift den ArchLens erkennen soll. Lösung: Proaktiver Kontext via MCP-Server statt reaktiver PR-Kommentar.

**Aktueller Fokus:**
Phase 1 Woche 1 — Engine + MCP Server + CLI

**Nächster Meilenstein:**
MCP-Server lokal lauffähig mit 5 Tools, testbar in Claude Code

**Offene Blocker:**
- Domain-Check: archlens.dev / archlens.io

**Letzte Entscheidungen:**
- D-011: Agent-First Pivot — MCP Server als primäres Interface
- D-012: Dashboard auf Phase 2 verschoben
- D-013: CLI als Human-Oversight-Layer

**Team:**
Solo-Build (Jonatan)

**Stack:**
- Engine: Python 3.11+, Graphify (PyPI: graphifyy)
- MCP Server: `mcp` SDK (FastMCP), stdio + HTTP transport
- CLI: Click + Rich
- CI: GitHub Actions
- Backend/Dashboard: Phase 2 (FastAPI, Next.js)

**Wichtige Dokumente:**
- `AGENTS.md` — Architektur & Bounded Contexts
- `GEMINI.md` — Agent-Regeln
- `context/decisions.md` — Entscheidungslog (13 Entscheidungen)
- `context/todo.md` — Sprint-Backlog
