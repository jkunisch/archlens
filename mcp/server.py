"""ArchLens MCP Server — Architecture Context for Coding Agents.

Exposes 5 tools, 3 resources, and 1 prompt via the Model Context Protocol.
Agents (Cursor, Claude Code, Codex, Gemini) connect to this server to get
architecture awareness before writing code.

Usage:
    # stdio transport (for Claude Code, Cursor)
    python -m mcp.server

    # Or via CLI
    archlens serve
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from mcp.engine_bridge import EngineBridge

# Logging to stderr (required for MCP stdio transport)
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("archlens-mcp")

# Initialize FastMCP server and engine bridge
mcp_server = FastMCP(
    "archlens",
    instructions=(
        "ArchLens provides architecture context for your codebase. "
        "Use check_boundaries before importing modules to verify you're not "
        "violating architecture rules. Use get_architecture_rules to understand "
        "the codebase's dependency boundaries."
    ),
)
bridge = EngineBridge()


# ─── Tools ───────────────────────────────────────────────────────────


@mcp_server.tool()
def check_boundaries(file_path: str, repo_path: str = ".") -> str:
    """Check if a file violates any architecture boundaries.

    Call this BEFORE adding imports to verify you're not crossing
    a forbidden boundary. Returns violations if any exist.

    Args:
        file_path: Relative path to the file to check (e.g. "frontend/views.py")
        repo_path: Path to the repository root (default: current directory)
    """
    try:
        repo = str(Path(repo_path).resolve())
        violations = bridge.check_boundaries(file_path, repo)
        if not violations:
            return f"✅ No boundary violations for {file_path}. Safe to proceed."
        result = f"⚠️ {len(violations)} boundary violation(s) for {file_path}:\n\n"
        for v in violations:
            result += f"  🔴 {v['source_path']} → {v['target_path']}\n"
            if v.get("rule_message"):
                result += f"     Rule: {v['rule_message']}\n"
            if v.get("detail"):
                result += f"     Detail: {v['detail']}\n"
        return result
    except Exception as e:
        logger.error("check_boundaries failed: %s", e)
        return f"Error checking boundaries: {e}"


@mcp_server.tool()
def get_violations(repo_path: str = ".") -> str:
    """Get all current architecture violations in the codebase.

    Returns a summary of all rule violations, god nodes, and
    cross-cluster issues detected in the current codebase state.

    Args:
        repo_path: Path to the repository root (default: current directory)
    """
    try:
        repo = str(Path(repo_path).resolve())
        report = bridge.get_violations(repo)
        violations = report.get("violations", [])
        if not violations:
            return "✅ No architecture violations detected. Codebase is clean."
        result = f"Found {len(violations)} violation(s):\n\n"
        for v in violations:
            severity = "🔴 FAIL" if v["severity"] == "fail" else "🟡 WARN"
            result += f"  {severity} [{v['violation_type']}] {v['source_path']}"
            if v.get("target_path"):
                result += f" → {v['target_path']}"
            result += "\n"
            if v.get("rule_message"):
                result += f"     {v['rule_message']}\n"
        return result
    except Exception as e:
        logger.error("get_violations failed: %s", e)
        return f"Error getting violations: {e}"


@mcp_server.tool()
def get_blast_radius(node_id: str, repo_path: str = ".") -> str:
    """Get the blast radius for a specific node (file/module).

    Shows how many other nodes are transitively affected if this
    node changes. Use this to assess impact before making changes.

    Args:
        node_id: The node identifier (e.g. "payment", "views", "models")
        repo_path: Path to the repository root (default: current directory)
    """
    try:
        repo = str(Path(repo_path).resolve())
        result = bridge.get_blast_radius(node_id, repo)
        radius = result["blast_radius"]
        affected = result["affected_nodes"]
        if radius == 0:
            return f"Node '{node_id}' has a blast radius of 0. No other nodes depend on it."
        response = f"Node '{node_id}' has a blast radius of {radius} nodes:\n\n"
        for node in affected[:20]:  # cap display at 20
            response += f"  • {node}\n"
        if radius > 20:
            response += f"  ... and {radius - 20} more\n"
        return response
    except Exception as e:
        logger.error("get_blast_radius failed: %s", e)
        return f"Error calculating blast radius: {e}"


@mcp_server.tool()
def get_architecture_rules(repo_path: str = ".") -> str:
    """Get all architecture rules defined in .archlens.yml.

    Returns the complete set of boundary rules (forbid/warn),
    thresholds, and ignored paths. Read this to understand which
    imports are allowed and which are forbidden.

    Args:
        repo_path: Path to the repository root (default: current directory)
    """
    try:
        repo = str(Path(repo_path).resolve())
        rules = bridge.get_architecture_rules(repo)
        if not rules.get("forbid") and not rules.get("warn"):
            return (
                "No .archlens.yml found or no rules defined. "
                "This repo has no explicit architecture boundaries configured."
            )
        result = "Architecture Rules (.archlens.yml):\n\n"
        if rules.get("forbid"):
            result += "🔴 FORBIDDEN (CI will fail):\n"
            for r in rules["forbid"]:
                result += f"  • {r['from_glob']} → {r['to_glob']}"
                if r.get("message"):
                    result += f" — {r['message']}"
                result += "\n"
        if rules.get("warn"):
            result += "\n🟡 WARNINGS:\n"
            for r in rules["warn"]:
                result += f"  • {r['from_glob']} → {r['to_glob']}"
                if r.get("message"):
                    result += f" — {r['message']}"
                result += "\n"
        thresholds = rules.get("thresholds", {})
        if thresholds:
            result += f"\n📊 Thresholds:\n"
            result += f"  • God node warning: {thresholds.get('god_node_warn', 15)} incoming edges\n"
            result += f"  • God node fail: {thresholds.get('god_node_fail', 30)} incoming edges\n"
            result += f"  • Cross-cluster warning: {thresholds.get('cross_cluster_warn', 5)} edges/PR\n"
            result += f"  • Cross-cluster fail: {thresholds.get('cross_cluster_fail', 10)} edges/PR\n"
        return result
    except Exception as e:
        logger.error("get_architecture_rules failed: %s", e)
        return f"Error reading architecture rules: {e}"


@mcp_server.tool()
def get_drift_summary(repo_path: str = ".") -> str:
    """Get a compact architecture drift summary.

    Returns a single paragraph suitable for injection into an
    agent's system prompt or context window.

    Args:
        repo_path: Path to the repository root (default: current directory)
    """
    try:
        repo = str(Path(repo_path).resolve())
        return bridge.get_drift_summary(repo)
    except Exception as e:
        logger.error("get_drift_summary failed: %s", e)
        return f"Error generating drift summary: {e}"


# ─── Resources ───────────────────────────────────────────────────────


@mcp_server.resource("archlens://rules/{repo_path}")
def rules_resource(repo_path: str) -> str:
    """The .archlens.yml rules as structured JSON."""
    repo = str(Path(repo_path).resolve())
    rules = bridge.get_architecture_rules(repo)
    return json.dumps(rules, indent=2)


@mcp_server.resource("archlens://graph/{repo_path}")
def graph_resource(repo_path: str) -> str:
    """The current graph snapshot as JSON."""
    repo = str(Path(repo_path).resolve())
    graph = bridge.get_graph(repo)
    return json.dumps(graph.model_dump(), indent=2, default=str)


@mcp_server.resource("archlens://context/{repo_path}")
def context_resource(repo_path: str) -> str:
    """The full agent context (archlens_context.json) as JSON."""
    repo = str(Path(repo_path).resolve())
    report_data = bridge.get_violations(repo)
    from shared.schemas.violation_schema import ViolationReport
    from shared.schemas.diff_schema import DiffResult
    from action.context_writer import build_agent_context
    report = ViolationReport.model_validate(report_data)
    context = build_agent_context(report, DiffResult(), repo=repo)
    return json.dumps(context, indent=2, default=str)


# ─── Prompts ─────────────────────────────────────────────────────────


@mcp_server.prompt()
def architecture_review(repo_path: str = ".") -> str:
    """Generate an architecture-aware system prompt for coding agents.

    Injects the current architecture rules and violation status into
    a prompt that agents can use as context for code generation.
    """
    try:
        repo = str(Path(repo_path).resolve())
        rules = bridge.get_architecture_rules(repo)
        summary = bridge.get_drift_summary(repo)

        prompt = (
            "You are working on a codebase with the following architecture rules:\n\n"
        )

        forbid = rules.get("forbid", [])
        if forbid:
            prompt += "FORBIDDEN imports (these will fail CI):\n"
            for r in forbid:
                prompt += f"  - {r['from_glob']} must NOT import from {r['to_glob']}"
                if r.get("message"):
                    prompt += f" ({r['message']})"
                prompt += "\n"

        warn = rules.get("warn", [])
        if warn:
            prompt += "\nWarned imports (these will generate warnings):\n"
            for r in warn:
                prompt += f"  - {r['from_glob']} should avoid importing from {r['to_glob']}"
                if r.get("message"):
                    prompt += f" ({r['message']})"
                prompt += "\n"

        prompt += f"\nCurrent status: {summary}\n"
        prompt += (
            "\nBefore adding any import, verify it does not cross a forbidden boundary. "
            "If unsure, use the check_boundaries tool."
        )
        return prompt
    except Exception as e:
        return f"Unable to generate architecture context: {e}"


# ─── Entry point ─────────────────────────────────────────────────────


def main() -> None:
    """Run the MCP server."""
    mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
