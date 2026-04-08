# 🔍 ArchLens — Architecture Context Layer for Coding Agents

> **Your coding agents know your architecture rules — before they write code, not after.**

ArchLens gives AI coding agents (Cursor, Claude Code, Codex, Gemini) architecture awareness via MCP (Model Context Protocol). It detects boundary violations, god nodes, and structural drift — proactively, before a single line of code is written.

For humans: CLI reports and PR comments provide oversight and proof of impact.

---

## Why ArchLens?

AI coding agents write code that *works* but **destroys structure**. They don't know:
- Which modules should never import from each other
- Which components are becoming god-objects  
- How a change cascades through the dependency graph

ArchLens solves this by giving agents **architecture context** before they write code — like a senior engineer looking over their shoulder.

---

## Quick Start

### 1. Install

```bash
pip install archlens[cli]       # CLI + Human oversight
pip install archlens[mcp]       # MCP Server for agents
pip install archlens[all]       # Everything
```

### 2. Create `.archlens.yml` in your repo

```yaml
version: 1
forbid:
  - from: "frontend/*"
    to: "database/*"
    message: "Frontend must not access database directly"
  - from: "api/*"
    to: "internal/*"
    message: "API must not use internal modules"
warn:
  - from: "*"
    to: "legacy/*"
    message: "Avoid new dependencies on legacy code"
thresholds:
  god_node_warn: 15
  god_node_fail: 30
```

### 3. Scan your repo

```bash
archlens scan .
```

Output:
```
🔍 ArchLens scanning /your/repo...
  📋 Rules: 2 forbid, 1 warn
  📊 Graph: 98 nodes, 169 edges
  ⚠️  3 violation(s) found:
    🟡 WARN [god_node] connection_databasepool
         Node has 18 incoming edges (threshold: 15)
  Summary: 0 failures, 3 warnings
```

### 4. Generate Architecture Report

```bash
archlens report . -o architecture_report.md
```

### 5. Connect to AI Agents via MCP

```bash
archlens serve       # stdio transport (Claude Code, Cursor)
archlens serve --http  # HTTP transport (port 8000)
```

#### Claude Code
```bash
claude mcp add archlens -- python -m mcp.server
```

#### Cursor / VS Code
Add to MCP settings:
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

---

## MCP Tools

When connected, your AI agent gains 5 architecture tools:

| Tool | What it does |
|------|-------------|
| `check_boundaries(file)` | "Can I import X?" — checks before writing code |
| `get_violations()` | All current architecture violations |
| `get_blast_radius(node)` | How many nodes are affected if this changes? |
| `get_architecture_rules()` | The rules from `.archlens.yml` |
| `get_drift_summary()` | One-paragraph architecture status |

**Example agent interaction:**

> **Agent:** *Calling `check_boundaries("frontend/views.py")`*  
> **ArchLens:** ✅ No boundary violations for frontend/views.py. Safe to proceed.

> **Agent:** *Calling `get_blast_radius("database_pool")`*  
> **ArchLens:** Node 'database_pool' has a blast radius of 42 nodes.

---

## GitHub Action

Add ArchLens to your CI pipeline:

```yaml
# .github/workflows/archlens.yml
name: Architecture Check
on: [pull_request]

jobs:
  archlens:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: archlens/archlens@v1
        with:
          fail-on-violations: 'true'
```

The action will:
- Scan your codebase for violations
- Post a PR comment with results
- Generate `archlens_context.json` as an artifact
- Fail CI if forbidden boundaries are crossed

---

## How It Works

```
                     YOUR REPO
                        │
                ┌───────▼───────┐
                │ .archlens.yml │  ← Your rules (config-as-code)
                └───────┬───────┘
                        │
                ┌───────▼───────┐
                │   Graphify    │  ← AST extraction (deterministic)
                │   AST Pass   │  
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

**Core principles:**
- **Zero Code Egress** — your source code never leaves your machine
- **Deterministic** — AST-based analysis, no LLM needed for detection
- **Config-as-Code** — rules live in your repo, versioned and reviewable

---

## Architecture Rules Reference

```yaml
version: 1

# FORBIDDEN — CI will fail
forbid:
  - from: "frontend/*"      # glob pattern for source
    to: "database/*"         # glob pattern for target
    message: "Use API layer" # human-readable explanation

# WARNINGS — CI passes but flags issues
warn:
  - from: "api/*"
    to: "internal/*"
    message: "Consider a public interface"

# THRESHOLDS — detect structural issues
thresholds:
  god_node_warn: 15    # warn if node has ≥15 incoming edges
  god_node_fail: 30    # fail if node has ≥30 incoming edges
  cross_cluster_warn: 5  # warn if PR adds ≥5 cross-cluster edges
  cross_cluster_fail: 10 # fail if PR adds ≥10 cross-cluster edges

# IGNORE — skip these paths
ignore:
  - "vendor/*"
  - "*.generated.*"
  - "__pycache__/*"
```

---

## Development

```bash
git clone https://github.com/archlens/archlens
cd archlens
python -m venv .venv && .venv/Scripts/activate  # or source .venv/bin/activate
pip install -e ".[all,dev]"
pytest tests/ -v
```

---

## License

MIT — See [LICENSE](LICENSE) for details.
