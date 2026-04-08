"""ArchLens CLI — Human oversight for architecture analysis.

Commands:
    archlens scan [PATH]    — Scan a repo and show violations
    archlens report [PATH]  — Generate a Markdown architecture report
    archlens serve          — Start the MCP server (stdio transport)
    archlens serve --http   — Start the MCP server (HTTP transport)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

# Lazy imports to keep CLI startup fast
def _get_rich_console():
    from rich.console import Console
    return Console(stderr=True)


@click.group()
@click.version_option(version="0.1.0", prog_name="archlens")
def app() -> None:
    """ArchLens — Architecture Context Layer for Coding Agents."""
    pass


@app.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--json-output", is_flag=True, help="Output as JSON instead of formatted text")
def scan(path: str, json_output: bool) -> None:
    """Scan a repository for architecture violations."""
    from action.graphify_adapter import GraphifyAdapter
    from action.config_parser import load_config
    from action.violation_checker import check_violations
    from action.blast_radius import calculate_blast_radius
    from action.edge_noise_filter import filter_noise
    from action.context_writer import build_agent_context
    from shared.schemas.diff_schema import DiffResult

    console = _get_rich_console()
    repo_path = Path(path).resolve()

    console.print(f"\n[bold blue]🔍 ArchLens[/bold blue] scanning [cyan]{repo_path}[/cyan]...\n")

    # Load config
    config = load_config(repo_path)
    if config.forbid or config.warn:
        console.print(f"  📋 Rules: {len(config.forbid)} forbid, {len(config.warn)} warn")
    else:
        console.print("  ⚠️  No .archlens.yml found — using defaults")

    # Build graph
    try:
        adapter = GraphifyAdapter()
        graph = adapter.build_graph(repo_path)
        console.print(f"  📊 Graph: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
    except ImportError:
        console.print("[red]Error: graphifyy not installed. pip install graphifyy[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error building graph: {e}[/red]")
        sys.exit(1)

    # Check violations (static analysis, no diff)
    empty_diff = DiffResult()
    report = check_violations(empty_diff, graph, config)

    if json_output:
        context = build_agent_context(report, empty_diff, repo=str(repo_path))
        click.echo(json.dumps(context, indent=2, default=str))
        return

    # Display results
    if not report.violations:
        console.print("\n  [bold green]✅ No violations found![/bold green]\n")
    else:
        console.print(f"\n  [bold yellow]⚠️  {len(report.violations)} violation(s) found:[/bold yellow]\n")
        for v in report.violations:
            if v.severity.value == "fail":
                icon = "[red]🔴 FAIL[/red]"
            elif v.severity.value == "warn":
                icon = "[yellow]🟡 WARN[/yellow]"
            else:
                icon = "[blue]ℹ️  INFO[/blue]"

            console.print(f"    {icon} [{v.violation_type.value}] {v.source_path}", end="")
            if v.target_path:
                console.print(f" → {v.target_path}", end="")
            console.print()
            if v.rule_message:
                console.print(f"         {v.rule_message}")
            if v.detail:
                console.print(f"         [dim]{v.detail}[/dim]")

    # Summary
    console.print(f"\n  Summary: {report.failure_count} failures, {report.warning_count} warnings\n")

    if report.has_failures:
        sys.exit(1)


@app.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--output", "-o", default="archlens_report.md", help="Output file path")
def report(path: str, output: str) -> None:
    """Generate a Markdown architecture report."""
    from action.graphify_adapter import GraphifyAdapter
    from action.config_parser import load_config
    from action.violation_checker import check_violations
    from action.blast_radius import calculate_blast_radius
    from action.context_writer import build_agent_context
    from shared.schemas.diff_schema import DiffResult

    console = _get_rich_console()
    repo_path = Path(path).resolve()
    output_path = Path(output)

    console.print(f"\n[bold blue]📄 ArchLens Report[/bold blue] for [cyan]{repo_path}[/cyan]\n")

    config = load_config(repo_path)
    adapter = GraphifyAdapter()
    graph = adapter.build_graph(repo_path)

    empty_diff = DiffResult()
    violations_report = check_violations(empty_diff, graph, config)

    # Calculate blast radius for top nodes
    top_targets: list[str] = []
    incoming: dict[str, int] = {}
    for edge in graph.edges:
        incoming[edge.target] = incoming.get(edge.target, 0) + 1
    sorted_nodes = sorted(incoming.items(), key=lambda x: x[1], reverse=True)[:10]
    top_targets = [n[0] for n in sorted_nodes]
    blast_radii = calculate_blast_radius(graph, top_targets) if top_targets else {}

    # Build markdown report
    lines = [
        f"# ArchLens Architecture Report",
        f"",
        f"> Repository: `{repo_path}`  ",
        f"> Generated: {__import__('datetime').datetime.now().isoformat()}",
        f"",
        f"## Summary",
        f"",
        f"- **Nodes:** {len(graph.nodes)}",
        f"- **Edges:** {len(graph.edges)}",
        f"- **Violations:** {violations_report.failure_count} failures, {violations_report.warning_count} warnings",
        f"",
    ]

    if config.forbid or config.warn:
        lines.append("## Architecture Rules (.archlens.yml)")
        lines.append("")
        if config.forbid:
            lines.append("### Forbidden")
            for r in config.forbid:
                lines.append(f"- `{r.from_glob}` → `{r.to_glob}`: {r.message}")
        if config.warn:
            lines.append("")
            lines.append("### Warnings")
            for r in config.warn:
                lines.append(f"- `{r.from_glob}` → `{r.to_glob}`: {r.message}")
        lines.append("")

    if violations_report.violations:
        lines.append("## Violations")
        lines.append("")
        lines.append("| Severity | Type | Source | Target | Message |")
        lines.append("|----------|------|--------|--------|---------|")
        for v in violations_report.violations:
            lines.append(
                f"| {v.severity.value.upper()} | {v.violation_type.value} | "
                f"`{v.source_path}` | `{v.target_path or '-'}` | {v.rule_message or v.detail} |"
            )
        lines.append("")

    if blast_radii:
        lines.append("## Top Nodes by Blast Radius")
        lines.append("")
        lines.append("| Node | Incoming Edges | Blast Radius |")
        lines.append("|------|---------------|--------------|")
        for node_id in top_targets:
            in_count = incoming.get(node_id, 0)
            radius = blast_radii.get(node_id, 0)
            lines.append(f"| `{node_id}` | {in_count} | {radius} |")
        lines.append("")

    md_content = "\n".join(lines)
    output_path.write_text(md_content, encoding="utf-8")
    console.print(f"  [green]✅ Report written to {output_path}[/green]\n")


@app.command()
@click.option("--http", "use_http", is_flag=True, help="Use HTTP transport instead of stdio")
@click.option("--port", default=8000, help="HTTP port (only with --http)")
def serve(use_http: bool, port: int) -> None:
    """Start the ArchLens MCP server."""
    console = _get_rich_console()

    if use_http:
        console.print(f"\n[bold blue]🚀 ArchLens MCP Server[/bold blue] starting on port {port}...")
        console.print(f"  Connect: http://localhost:{port}/mcp")
        console.print(f"  Add to Claude Code: claude mcp add archlens http://localhost:{port}/mcp\n")
        from mcp.server import mcp_server
        mcp_server.run(transport="streamable-http", port=port)
    else:
        console.print("[bold blue]🚀 ArchLens MCP Server[/bold blue] starting (stdio)...", highlight=False)
        from mcp.server import mcp_server
        mcp_server.run(transport="stdio")


if __name__ == "__main__":
    app()
