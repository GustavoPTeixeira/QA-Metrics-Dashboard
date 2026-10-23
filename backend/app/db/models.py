import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.enums import FoundIn, IssueStatus, Severity

def new_uuid() -> str:
    return str(uuid.uuid4())

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

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