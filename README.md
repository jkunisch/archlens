<div align="center">

# 🔍 ArchLens

### Architecture Context Layer for Coding Agents

*Your coding agents know your architecture rules — before they write code, not after.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-Compatible-purple.svg)](https://modelcontextprotocol.io)
[![Tests](https://img.shields.io/badge/Tests-34%20passing-brightgreen.svg)](#)

[Quick Start](#-quick-start) · [MCP Tools](#-mcp-tools) · [GitHub Action](#-github-action) · [Configuration](#-configuration)

</div>

---

## The Problem

AI coding agents (Cursor, Claude Code, Codex, Gemini) write code that **works** but **destroys structure**. They don't know:

- 🚫 Which modules should never import from each other
- 💀 Which components are becoming god-objects with 50+ dependents
- 💥 How a "small change" cascades through 42 transitive dependents

By the time a human spots the drift in review, it's already merged. Architecture erodes one PR at a time.

## The Solution

ArchLens gives agents **architecture context** via [MCP](https://modelcontextprotocol.io) — like a senior engineer looking over their shoulder. Agents check boundaries *before* writing code, not after.

```
Agent: "I need to import database.pool in the frontend..."
ArchLens: "🔴 FORBIDDEN. frontend/* → database/* violates boundary rule.
           Use the API layer instead. Blast radius: 42 nodes affected."
Agent: "Got it. I'll use api.get_connection() instead."
```

**For humans:** CLI reports and PR comments provide oversight and proof of impact.

---

## ✨ Key Features

| Feature | For Agents | For Humans |
|---------|-----------|------------|
| **Boundary Checking** | `check_boundaries()` before importing | PR comment: "This PR crosses 2 boundaries" |
| **God Node Detection** | "This module has 46 dependents, be careful" | Report: Top 10 nodes by blast radius |
| **Blast Radius** | "Changing this affects 42 other modules" | Table: Exact impact per node |
| **Drift Summary** | Injected into agent's context window | CLI: `archlens scan .` |
| **Architecture Rules** | Agent reads `.archlens.yml` automatically | Config-as-code, version-controlled |

**Core principles:**
- 🔒 **Zero Code Egress** — your source code never leaves your machine
- 🎯 **Deterministic** — AST-based analysis, no LLM needed for detection
- 📝 **Config-as-Code** — rules live in your repo, versioned and reviewable

---

## 🚀 Quick Start

### Install

```bash
# For AI agents (MCP server)
pip install archlens[mcp]

# For humans (CLI)
pip install archlens[cli]

# Everything
pip install archlens[all]
```

### Create `.archlens.yml`

Drop this in your repo root:

```yaml
version: 1

forbid:
  - from: "frontend/*"
    to: "database/*"
    message: "Frontend must not access database directly. Use the API layer."
  - from: "api/*"
    to: "internal/*"
    message: "API must not use internal modules."

warn:
  - from: "*"
    to: "legacy/*"
    message: "Avoid new dependencies on legacy code."

thresholds:
  god_node_warn: 15    # warn when a node has ≥15 incoming edges
  god_node_fail: 30    # fail when a node has ≥30 incoming edges

ignore:
  - "vendor/*"
  - "__pycache__/*"
```

### Scan Your Repo

```bash
$ archlens scan .

🔍 ArchLens scanning /your/repo...
  📋 Rules: 2 forbid, 1 warn
  📊 Graph: 98 nodes, 169 edges

  ⚠️  3 violation(s) found:
    🟡 WARN [god_node] connection_databasepool
         Node has 18 incoming edges (threshold: 15)
    🟡 WARN [god_node] auth_authservice
         Node has 13 incoming edges (threshold: 10)
    🟡 WARN [god_node] models_user
         Node has 11 incoming edges (threshold: 10)

  Summary: 0 failures, 3 warnings
```

### Generate Report

```bash
archlens report . -o architecture_report.md
```

Generates a Markdown report with violations, rules, and a **blast radius table**:

| Node | Incoming Edges | Blast Radius |
|------|---------------|--------------|
| `connection_databasepool` | 18 | **42** |
| `auth_authservice` | 13 | 23 |
| `models_user` | 11 | 34 |

---

## 🤖 MCP Tools

Connect ArchLens to any MCP-compatible agent:

### Claude Code
```bash
claude mcp add archlens -- python -m mcp.server
```

### Cursor / VS Code
Add to your MCP settings:
```json
{
  "mcpServers": {
    "archlens": {
      "command": "python",
      "args": ["-m", "mcp.server"],
      "cwd": "/path/to/your/repo"
    }
  }
}
```

### HTTP Transport
```bash
archlens serve --http --port 8000
# Then: claude mcp add --transport http archlens http://localhost:8000/mcp
```

### Available Tools

Once connected, your agent gains **5 architecture tools**:

#### `check_boundaries(file_path, repo_path)`
> 🛡️ **Call this before adding imports.** Returns violations if crossing a forbidden boundary.

```
Agent calls: check_boundaries("frontend/views.py")
→ "✅ No boundary violations. Safe to proceed."

Agent calls: check_boundaries("frontend/db_access.py")
→ "🔴 1 violation: frontend/* → database/* is forbidden."
```

#### `get_violations(repo_path)`
> 📋 All current architecture violations in the codebase.

#### `get_blast_radius(node_id, repo_path)`
> 💥 How many nodes are transitively affected if this node changes.

#### `get_architecture_rules(repo_path)`
> 📖 The complete `.archlens.yml` rules so the agent knows the boundaries.

#### `get_drift_summary(repo_path)`
> 📝 One-paragraph architecture status, injectable into agent context.

---

## 🔧 GitHub Action

Add ArchLens to your CI to catch drift on every PR:

```yaml
# .github/workflows/archlens.yml
name: Architecture Check
on: [pull_request]

jobs:
  archlens:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: jkunisch/archlens@main
        with:
          fail-on-violations: 'true'
```

The action will:
- 🔍 Scan your codebase for boundary violations
- 💬 Post a PR comment with results
- 📦 Generate `archlens_context.json` as an artifact
- ❌ Fail CI if forbidden boundaries are crossed

---

## 📐 Configuration

### Rules Reference

```yaml
version: 1

# FORBIDDEN — CI will fail
forbid:
  - from: "frontend/*"       # glob: source module/file
    to: "database/*"          # glob: target module/file
    message: "Use API layer"  # shown to agents and humans

# WARNINGS — CI passes, flags issues
warn:
  - from: "api/*"
    to: "internal/*"
    message: "Consider a public interface"

# THRESHOLDS — detect structural issues
thresholds:
  god_node_warn: 15       # warn if node has ≥N incoming edges
  god_node_fail: 30       # fail if node has ≥N incoming edges
  cross_cluster_warn: 5   # warn if PR adds ≥N cross-cluster edges
  cross_cluster_fail: 10  # fail if PR adds ≥N cross-cluster edges

# IGNORE — skip these paths entirely
ignore:
  - "vendor/*"
  - "*.generated.*"
  - "__pycache__/*"
```

### CLI Commands

| Command | What it does |
|---------|-------------|
| `archlens scan [PATH]` | Scan repo, show violations in terminal |
| `archlens scan [PATH] --json-output` | Output as JSON (for agent injection) |
| `archlens report [PATH] -o FILE` | Generate Markdown architecture report |
| `archlens serve` | Start MCP server (stdio, for Claude Code/Cursor) |
| `archlens serve --http` | Start MCP server (HTTP, port 8000) |

---

## 🏗️ How It Works

```
                  YOUR REPO
                      │
              ┌───────▼───────┐
              │ .archlens.yml │  ← Your rules (config-as-code)
              └───────┬───────┘
                      │
              ┌───────▼───────┐
              │   Graphify    │  ← AST extraction (deterministic)
              │   AST Pass   │     No LLM, no heuristics
              └───────┬───────┘
                      │
      ┌───────────────┼───────────────┐
      │               │               │
 ┌────▼────┐   ┌──────▼──────┐  ┌─────▼─────┐
 │   MCP   │   │    CLI      │  │  GitHub   │
 │  Server │   │  scan/report│  │  Action   │
 │(agents) │   │  (humans)   │  │   (CI)    │
 └─────────┘   └─────────────┘  └───────────┘
```

ArchLens uses [Graphify](https://pypi.org/project/graphifyy/) to build an AST-based dependency graph of your codebase. It then checks this graph against your `.archlens.yml` rules to detect:

1. **Boundary violations** — forbidden imports between modules
2. **God nodes** — modules with too many dependents (high fan-in)
3. **Cross-cluster drift** — new edges crossing package boundaries
4. **Blast radius** — transitive impact analysis via BFS

All analysis is **deterministic** — no LLM calls, no cloud services, no code egress.

---

## 🛠️ Development

```bash
git clone https://github.com/jkunisch/archlens
cd archlens
python -m venv .venv
.venv/Scripts/activate    # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -e ".[all,dev]"
pytest tests/ -v           # 34 tests
archlens scan .            # Dogfooding ✨
```

---

## 📄 License

MIT — See [LICENSE](LICENSE) for details.

---

<div align="center">

**ArchLens** is built to make AI coding agents architecture-aware.

[Report a Bug](https://github.com/jkunisch/archlens/issues) · [Request a Feature](https://github.com/jkunisch/archlens/issues) · [Star the Repo ⭐](https://github.com/jkunisch/archlens)

</div>
