"""GitHub Action entrypoint for ArchLens.

Runs the ArchLens engine inside a GitHub Action, analyzes the PR diff,
and either:
1. Posts a PR comment with violations (if GITHUB_TOKEN is set)
2. Writes archlens_context.json as an artifact
3. Sets CI status (fail if forbid violations found)

Environment variables (set by GitHub Actions):
- GITHUB_WORKSPACE: repo root
- GITHUB_EVENT_PATH: path to event JSON
- GITHUB_TOKEN: for PR comments
- GITHUB_STEP_SUMMARY: for step summary output
- INPUT_CONFIG_PATH: optional custom config path (default: .archlens.yml)
- INPUT_FAIL_ON_VIOLATIONS: whether to fail CI on violations (default: true)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

from action.graphify_adapter import GraphifyAdapter
from action.config_parser import load_config
from action.violation_checker import check_violations
from action.blast_radius import calculate_blast_radius
from action.edge_noise_filter import filter_noise
from action.context_writer import build_agent_context, write_context_file, write_step_summary
from shared.schemas.diff_schema import DiffResult


def main() -> None:
    """GitHub Action entrypoint."""
    workspace = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
    fail_on_violations = os.environ.get("INPUT_FAIL_ON_VIOLATIONS", "true").lower() == "true"

    print(f"::group::ArchLens Scan")
    print(f"Repository: {workspace}")

    # Load config
    config = load_config(workspace)
    print(f"Rules loaded: {len(config.forbid)} forbid, {len(config.warn)} warn")

    # Build graph
    adapter = GraphifyAdapter()
    try:
        graph = adapter.build_graph(workspace)
        print(f"Graph: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
    except ImportError:
        print("::error::graphifyy is not installed in the action container")
        sys.exit(1)
    except Exception as e:
        print(f"::error::Failed to build graph: {e}")
        sys.exit(1)

    # For CI: we do static analysis on HEAD graph (no base comparison yet)
    # TODO: In Phase 1b, compare base_sha vs head_sha for proper diff
    empty_diff = DiffResult()
    report = check_violations(empty_diff, graph, config)

    # Build agent context
    pr_number = _get_pr_number()
    repo_name = os.environ.get("GITHUB_REPOSITORY", "")
    context = build_agent_context(report, empty_diff, repo=repo_name, pr_number=pr_number)

    # Write outputs
    output_path = workspace / "archlens_context.json"
    write_context_file(context, output_path)
    print(f"Context written to: {output_path}")

    # Write GitHub step summary
    write_step_summary(context)

    # Set GitHub Action outputs
    _set_output("violation_count", str(report.failure_count))
    _set_output("warning_count", str(report.warning_count))
    _set_output("has_failures", str(report.has_failures).lower())
    _set_output("context_path", str(output_path))

    # Post PR comment if token available
    github_token = os.environ.get("GITHUB_TOKEN", "")
    if github_token and pr_number > 0 and repo_name:
        _post_pr_comment(github_token, repo_name, pr_number, report, context)

    print(f"::endgroup::")

    # Summary
    if report.has_failures:
        print(f"::error::{report.failure_count} architecture violation(s) found")
        if fail_on_violations:
            sys.exit(1)
    elif report.warning_count > 0:
        print(f"::warning::{report.warning_count} architecture warning(s)")
    else:
        print("✅ No architecture violations found")


def _get_pr_number() -> int:
    """Extract PR number from GitHub event payload."""
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not event_path or not Path(event_path).exists():
        return 0
    try:
        with open(event_path, encoding="utf-8") as f:
            event = json.load(f)
        return event.get("pull_request", {}).get("number", 0)
    except Exception:
        return 0


def _set_output(name: str, value: str) -> None:
    """Set a GitHub Action output variable."""
    output_file = os.environ.get("GITHUB_OUTPUT", "")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")


def _post_pr_comment(
    token: str,
    repo: str,
    pr_number: int,
    report: object,
    context: dict,
) -> None:
    """Post architecture analysis as a PR comment."""
    violations = context.get("violations", [])
    arch_context = context.get("architecture_context", "")

    # Build comment body
    body = "## 🔍 ArchLens Architecture Analysis\n\n"
    body += f"**{arch_context}**\n\n"

    if violations:
        body += "| Severity | Type | Source | Target | Message |\n"
        body += "|----------|------|--------|--------|---------|\n"
        for v in violations:
            severity = "🔴 FAIL" if v["severity"] == "fail" else "🟡 WARN"
            body += (
                f"| {severity} | {v['violation_type']} | "
                f"`{v['source_path']}` | `{v.get('target_path', '-')}` | "
                f"{v.get('rule_message') or v.get('detail', '')} |\n"
            )
    else:
        body += "✅ No violations found.\n"

    body += "\n---\n*Generated by [ArchLens](https://github.com/archlens/archlens) — Architecture Context for Coding Agents*"

    # Post via GitHub API
    try:
        resp = httpx.post(
            f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
            },
            json={"body": body},
            timeout=10.0,
        )
        if resp.status_code == 201:
            print(f"PR comment posted: {resp.json().get('html_url', '')}")
        else:
            print(f"::warning::Failed to post PR comment: {resp.status_code}")
    except Exception as e:
        print(f"::warning::Failed to post PR comment: {e}")


if __name__ == "__main__":
    main()
