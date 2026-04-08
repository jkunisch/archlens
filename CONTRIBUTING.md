# Contributing to ArchLens

Thanks for your interest in contributing! ArchLens is an open-core project that gives AI coding agents architecture awareness.

## Getting Started

```bash
git clone https://github.com/jkunisch/archlens
cd archlens
python -m venv .venv && .venv/Scripts/activate
pip install -e ".[all,dev]"
pytest tests/ -v
```

## Architecture

ArchLens has 7 bounded components. **Do not introduce cross-component imports** (P5):

| Component | Purpose | May import |
|-----------|---------|-----------|
| `action/` | Engine (AST analysis, violations, blast radius) | `shared/` |
| `mcp/` | MCP Server (agent interface) | `action/`, `shared/` |
| `cli/` | CLI (human oversight) | `action/`, `shared/` |
| `shared/` | Schemas & constants only | Nothing |
| `api/` | Backend (Phase 2) | `shared/` |
| `dashboard/` | Frontend (Phase 2) | API only |

Read `AGENTS.md` for the full architecture rules.

## What to Contribute

### 🟢 Great first issues
- Add more violation types (circular dependencies, layer violations)
- Improve CLI output formatting
- Add language support beyond Python (JavaScript/TypeScript AST)
- Write more tests (target: >80% coverage)

### 🟡 Medium complexity
- Base-vs-head diff in GitHub Action (currently static analysis only)
- MCP resource templates for common architectures
- Config validation improvements

### 🔴 Needs discussion first
- New bounded components
- Changes to shared schemas
- LLM-based features (see P2: Determinism before LLM)

## Pull Request Process

1. Fork & create a feature branch
2. Write tests for your changes
3. Run `pytest tests/ -v` — all tests must pass
4. Run `archlens scan .` — no new violations (dogfooding!)
5. Update `context/decisions.md` if making architectural decisions
6. Submit PR with a clear description

## Code Style

- Python 3.11+, strict type hints
- Google-style docstrings
- `ruff` for formatting, `mypy` for type checking
- English for code/comments, German for project context files

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
