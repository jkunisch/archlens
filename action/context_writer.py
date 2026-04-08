"""Write archlens_context.json — structured output for Coding Agents.

Design goals (D-010):
- Machine-readable JSON with clear field names
- Includes context-ready sentences that an LLM can inject directly
- Includes file-level impact so agents know WHICH files to care about
- Can be read by any agent (Cursor, Claude Code, Codex, Gemini)

Output is both a local file and optionally appended to GITHUB_STEP_SUMMARY.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from shared.schemas.diff_schema import DiffResult
from shared.schemas.violation_schema import Severity, ViolationReport


def build_agent_context(
    report: ViolationReport,
    diff: DiffResult,
    repo: str = "",
    pr_number: int = 0,
) -> dict[str, Any]:
    """Build the structured context dict for agent consumption.

    This is the core data structure. write_context_file() and
    write_step_summary() are convenience wrappers.
    """
    failures = [v for v in report.violations if v.severity == Severity.FAIL]
    warnings = [v for v in report.violations if v.severity == Severity.WARN]

    # Build agent-injectable instructions (imperative, specific)
    instructions: list[str] = []
    for v in failures:
        msg = f"CRITICAL ARCHITECTURE VIOLATION: {v.source_path}"
        if v.target_path:
            msg += f" → {v.target_path}"
        if v.rule_message:
            msg += f". Rule: {v.rule_message}"
        if v.blast_radius > 0:
            msg += f" Blast radius: {v.blast_radius} affected nodes."
        instructions.append(msg)
    for v in warnings:
        msg = f"ARCHITECTURE WARNING: {v.source_path}"
        if v.target_path:
            msg += f" → {v.target_path}"
        if v.rule_message:
            msg += f". {v.rule_message}"
        instructions.append(msg)

    # Single paragraph for LLM system prompt injection
    if failures:
        arch_context = (
            f"This codebase has {len(failures)} active architecture violation(s). "
            f"Before adding new code, review the agent_instructions and avoid patterns that "
            f"cross the boundaries defined in .archlens.yml."
        )
    elif warnings:
        arch_context = (
            f"This codebase has {len(warnings)} architecture warning(s). "
            f"The codebase structure is mostly healthy but watch the flagged nodes."
        )
    else:
        arch_context = (
            "No architecture violations detected. Codebase boundaries are respected."
        )

    return {
        "schema_version": "1.0",
        "repo": repo,
        "pr_number": pr_number,
        "summary": report.graph_summary or f"{len(failures)} violations, {len(warnings)} warnings",
        "agent_instructions": instructions,
        "violations": [v.model_dump() for v in report.violations],
        "added_edges": [
            {
                "source": e.source,
                "target": e.target,
                "relation": e.edge_type,
                "source_file": e.metadata.get("source_file", ""),
            }
            for e in diff.added_edges
        ],
        "architecture_context": arch_context,
    }


def write_context_file(
    context: dict[str, Any],
    output_path: Path,
) -> None:
    """Write archlens_context.json to disk."""
    output_path.write_text(json.dumps(context, indent=2, default=str), encoding="utf-8")


def write_step_summary(context: dict[str, Any]) -> None:
    """Append context to GitHub Step Summary (if running in CI)."""
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not step_summary:
        return

    arch_context = context.get("architecture_context", "")
    instructions = context.get("agent_instructions", [])

    with open(step_summary, "a", encoding="utf-8") as f:
        f.write("## ArchLens Architecture Context\n\n")
        f.write(f"**{arch_context}**\n\n")
        if instructions:
            f.write("### Instructions for Coding Agents\n\n")
            for inst in instructions:
                f.write(f"- {inst}\n")
        f.write("\n```json\n")
        f.write(json.dumps(context, indent=2, default=str))
        f.write("\n```\n")
