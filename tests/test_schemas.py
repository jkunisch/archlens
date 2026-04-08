"""Tests for shared Pydantic schemas."""

from __future__ import annotations

from shared.schemas import (
    ArchLensConfig,
    DiffResult,
    ForbidRule,
    GraphEdge,
    GraphNode,
    GraphSnapshot,
    JobRequest,
    JobResult,
    JobStatus,
    Severity,
    Violation,
    ViolationReport,
    ViolationType,
)


def test_forbid_rule_accepts_from_alias() -> None:
    rule = ForbidRule.model_validate(
        {
            "from": "frontend/*",
            "to": "database/*",
            "message": "Use the API layer.",
        }
    )

    assert rule.from_glob == "frontend/*"
    assert rule.to_glob == "database/*"


def test_forbid_rule_accepts_field_names() -> None:
    rule = ForbidRule.model_validate(
        {
            "from_glob": "frontend/*",
            "to_glob": "database/*",
        }
    )

    assert rule.from_glob == "frontend/*"
    assert rule.to_glob == "database/*"


def test_forbid_rule_dumps_aliases_when_requested() -> None:
    rule = ForbidRule.model_validate(
        {
            "from_glob": "frontend/*",
            "to_glob": "database/*",
        }
    )

    assert rule.model_dump(by_alias=True) == {
        "from": "frontend/*",
        "to": "database/*",
        "message": "",
    }


def test_archlens_config_loads_yaml_like_dict() -> None:
    config = ArchLensConfig.model_validate(
        {
            "version": 1,
            "forbid": [
                {
                    "from": "frontend/*",
                    "to": "database/*",
                    "message": "Frontend cannot reach the database.",
                }
            ],
            "warn": [
                {
                    "from": "api/*",
                    "to": "internal/*",
                    "message": "Keep the API boundary clean.",
                }
            ],
            "thresholds": {
                "god_node_warn": 20,
                "cross_cluster_warn": 7,
            },
            "ignore": ["vendor/*", "node_modules/*"],
        }
    )

    assert config.forbid[0].from_glob == "frontend/*"
    assert config.warn[0].to_glob == "internal/*"
    assert config.thresholds.god_node_warn == 20
    assert config.thresholds.god_node_fail == 30
    assert config.ignore == ["vendor/*", "node_modules/*"]


def test_graph_snapshot_round_trips_via_python_dump() -> None:
    snapshot = GraphSnapshot(
        nodes=[
            GraphNode(
                id="src/app.py:App",
                name="App",
                type="class",
                file_path="src/app.py",
                cluster_id=2,
                metadata={"line": 12},
            )
        ],
        edges=[
            GraphEdge(
                source="src/app.py:App",
                target="src/db.py:connect",
                edge_type="calls",
                metadata={"weight": 1},
            )
        ],
        metadata={"node_count": 1, "edge_count": 1},
    )

    restored = GraphSnapshot.model_validate(snapshot.model_dump())

    assert restored.model_dump() == snapshot.model_dump()


def test_graph_snapshot_round_trips_via_json() -> None:
    snapshot = GraphSnapshot(
        nodes=[GraphNode(id="src/app.py:run", name="run", type="function")],
        edges=[
            GraphEdge(
                source="src/app.py:run",
                target="src/service.py:Service",
                edge_type="depends_on",
                confidence="INFERRED",
            )
        ],
    )

    restored = GraphSnapshot.model_validate_json(snapshot.model_dump_json())

    assert restored.nodes[0].id == "src/app.py:run"
    assert restored.edges[0].confidence == "INFERRED"


def test_diff_result_summary_formats_all_changes() -> None:
    diff = DiffResult(
        added_edges=[GraphEdge(source="a", target="b", edge_type="imports")],
        removed_edges=[GraphEdge(source="b", target="c", edge_type="calls")],
        added_nodes=[GraphNode(id="c", name="C", type="module")],
        removed_nodes=[GraphNode(id="d", name="D", type="module")],
        cluster_changes=[{"node_id": "a", "from_cluster": 1, "to_cluster": 2}],
    )

    assert diff.summary == "+1 edges, -1 edges, +1 nodes, -1 nodes, ~1 cluster changes"
    assert diff.has_changes is True


def test_diff_result_reports_no_changes_when_empty() -> None:
    diff = DiffResult()

    assert diff.summary == "No changes"
    assert diff.has_changes is False


def test_diff_result_treats_cluster_only_changes_as_changes() -> None:
    diff = DiffResult(cluster_changes=[{"node_id": "service", "from_cluster": 3, "to_cluster": 4}])

    assert diff.has_changes is True
    assert diff.summary == "~1 cluster changes"


def test_violation_report_has_failures_and_counts() -> None:
    report = ViolationReport(
        violations=[
            Violation(
                violation_type=ViolationType.FORBIDDEN_EDGE,
                severity=Severity.FAIL,
                source_path="frontend/view.py",
                target_path="database/client.py",
                rule_message="Frontend cannot access the database directly.",
            ),
            Violation(
                violation_type=ViolationType.GOD_NODE,
                severity=Severity.WARN,
                source_path="api/router.py",
                detail="Incoming edge count exceeded warning threshold.",
            ),
        ],
        graph_summary="+1 edges",
    )

    assert report.has_failures is True
    assert report.failure_count == 1
    assert report.warning_count == 1


def test_job_request_and_result_validate_expected_fields() -> None:
    request = JobRequest.model_validate(
        {
            "repo_full_name": "openai/archlens",
            "pr_number": 42,
            "base_sha": "abc123",
            "head_sha": "def456",
            "installation_id": 99,
        }
    )
    result = JobResult(job_id="job-1", status=JobStatus.QUEUED)

    assert request.repo_full_name == "openai/archlens"
    assert request.pr_number == 42
    assert result.violation_count == 0
    assert result.has_failures is False
