from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

from app.domain.enums import FoundIn, IssueStatus, Severity, TestStatus


class TestAttemptPayload(BaseModel):
    attempt_no: int = Field(ge=1, description="Número da tentativa (1, 2, 3...)")
    status: TestStatus
    duration_ms: int = Field(ge=0)
    error_message: str | None = None


class TestCasePayload(BaseModel):
    scenario_title: str
    class_or_feature: str
    module_name: str
    status: TestStatus
    duration_ms: int = Field(ge=0)
    error_message: str | None = None
    stack_trace: str | None = None
    attempts: list[TestAttemptPayload] = Field(default_factory=list)


class TestRunIngestPayload(BaseModel):
    suite_name: str
    git_commit_sha: str
    environment: str = "ci"
    executed_at: datetime
    test_cases: list[TestCasePayload]


class IssueIngestPayload(BaseModel):
    external_key: str
    title: str
    severity: Severity
    status: IssueStatus
    found_in: FoundIn
    module_name: str
    actor: str = "system"
    release_version: str | None = None
    linked_commit_sha: str | None = None
    created_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None

