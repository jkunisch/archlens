"""Schemas for worker job tracking."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Supported job lifecycle states."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobRequest(BaseModel):
    """Request payload for analyzing a pull request.

    Attributes:
        repo_full_name: Repository identifier in ``owner/repo`` form.
        pr_number: Pull request number.
        base_sha: Base commit SHA.
        head_sha: Head commit SHA.
        installation_id: GitHub App installation identifier.
    """

    repo_full_name: str = Field(description="owner/repo")
    pr_number: int
    base_sha: str = Field(description="Base commit SHA")
    head_sha: str = Field(description="Head commit SHA")
    installation_id: int = Field(description="GitHub App installation ID")


class JobResult(BaseModel):
    """Result payload for a completed or in-flight analysis job.

    Attributes:
        job_id: Unique job identifier.
        status: Current job status.
        started_at: Timestamp when work started.
        completed_at: Timestamp when work completed.
        violation_count: Number of fail-level violations found.
        warning_count: Number of warn-level violations found.
        has_failures: Whether the analysis should fail the PR.
        pr_comment_url: URL of the PR comment created by the worker.
        error_message: Failure detail when the job fails.
    """

    job_id: str
    status: JobStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    violation_count: int = Field(default=0)
    warning_count: int = Field(default=0)
    has_failures: bool = Field(default=False)
    pr_comment_url: str = Field(default="", description="URL of posted PR comment")
    error_message: str = Field(default="")
