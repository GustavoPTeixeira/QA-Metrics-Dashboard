import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.enums import FoundIn, IssueStatus, Severity, TestStatus

def new_uuid() -> str:
    return str(uuid.uuid4())

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def compute_scenario_id(suite_name: str, class_or_feature: str, scenario_title: str) -> str:
    raw = f"{suite_name}|{class_or_feature}|{scenario_title}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

class Module(Base):
    __tablename__ = "modules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(100))
    owner_team: Mapped[str] = mapped_column(String(100))
    parent_module_id: Mapped[str | None] = mapped_column(ForeignKey("modules.id"))

class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    external_key: Mapped[str] = mapped_column(String(100), unique=True) 
    title: Mapped[str] = mapped_column(String(500))

    severity: Mapped[Severity] = mapped_column(Enum(Severity))
    status: Mapped[IssueStatus] = mapped_column(Enum(IssueStatus))
    found_in: Mapped[FoundIn] = mapped_column(Enum(FoundIn))

    module_id: Mapped[str] = mapped_column(ForeignKey("modules.id"))

    release_version: Mapped[str | None] = mapped_column(String(50))
    linked_commit_sha: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class IssueTransition(Base):
    __tablename__ = "issue_transitions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    issue_id: Mapped[str] = mapped_column(ForeignKey("issues.id"))
    from_status: Mapped[IssueStatus | None] = mapped_column(Enum(IssueStatus))
    to_status: Mapped[IssueStatus] = mapped_column(Enum(IssueStatus))
    transitioned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor: Mapped[str] = mapped_column(String(100))

class TestRun(Base):
    __tablename__ = "test_runs"
    __test__ = False  # Evita que o pytest ache que esta classe é um teste!
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    suite_name: Mapped[str] = mapped_column(String(200))
    git_commit_sha: Mapped[str] = mapped_column(String(40))
    environment: Mapped[str] = mapped_column(String(50))
    total_count: Mapped[int] = mapped_column(Integer)
    passed_count: Mapped[int] = mapped_column(Integer)
    failed_count: Mapped[int] = mapped_column(Integer)
    skipped_count: Mapped[int] = mapped_column(Integer)
    duration_ms: Mapped[int] = mapped_column(Integer)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint(
            "suite_name",
            "git_commit_sha",
            "executed_at",
            name="uq_test_run_idempotency",
        ),
    )

class TestCase(Base):
    __tablename__ = "test_cases"
    __test__ = False  # Evita confusão no pytest
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    test_run_id: Mapped[str] = mapped_column(ForeignKey("test_runs.id"))
    scenario_id: Mapped[str] = mapped_column(String(64), index=True)
    scenario_title: Mapped[str] = mapped_column(String(500))
    module_id: Mapped[str] = mapped_column(ForeignKey("modules.id"))
    status: Mapped[TestStatus] = mapped_column(Enum(TestStatus))
    duration_ms: Mapped[int] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    stack_trace: Mapped[str | None] = mapped_column(Text)
    is_flaky: Mapped[bool] = mapped_column(Boolean, default=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
class TestAttempt(Base):
    __tablename__ = "test_attempts"
    __test__ = False  # Evita confusão no pytest
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    test_case_id: Mapped[str] = mapped_column(ForeignKey("test_cases.id"))
    attempt_no: Mapped[int] = mapped_column(Integer)
    status: Mapped[TestStatus] = mapped_column(Enum(TestStatus))
    duration_ms: Mapped[int] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
class ScenarioAlias(Base):
    __tablename__ = "scenario_aliases"
    old_scenario_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    new_scenario_id: Mapped[str] = mapped_column(String(64), index=True)
    renamed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))