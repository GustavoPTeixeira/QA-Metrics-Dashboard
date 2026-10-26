from sqlalchemy import create_engine
from app.db.base import Base
import app.db.models
import pytest
from sqlalchemy.orm import Session
from app.db.models import Module, Issue
from datetime import datetime, timezone
from app.domain.enums import Severity, IssueStatus, FoundIn
from sqlalchemy.exc import IntegrityError
from app.db.models import Module, Issue, IssueTransition

def test_tables_create():
    engine= create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

def test_expected_tables_registered():
    assert {"modules", "issues", "issue_transitions"} <= set(Base.metadata.tables)

@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s

def test_module_roundtrip(session):
    module = Module(name="Checkout", owner_team="Payments")
    session.add(module)
    session.commit()

    saved = session.query(Module).filter_by(name="Checkout").one()

    assert saved.owner_team == "Payments"
    assert saved.parent_module_id is None
    assert len(saved.id) == 36

def test_issue_roundtrip(session):
    module = Module(name="Auth", owner_team="Security")
    session.add(module)
    session.commit()

    issue = Issue(
        external_key="AUTH-101",
        title="Password reset link expired immediately",
        severity=Severity.HIGH,
        status=IssueStatus.OPEN,
        found_in=FoundIn.PROD,
        module_id=module.id,
        created_at=datetime.now(timezone.utc),
    )
    session.add(issue)
    session.commit()

    saved = session.query(Issue).filter_by(external_key="AUTH-101").one()

    assert saved.title == "Password reset link expired immediately"
    assert saved.severity == Severity.HIGH
    assert saved.module_id == module.id
    assert saved.resolved_at is None
    assert saved.closed_at is None

def test_duplicate_issue_external_key_raises(session):
    # 1. Create a module
    module = Module(name="Billing", owner_team="Finance")
    session.add(module)
    session.commit()
    issue1 = Issue(
        external_key="BILL-100",
        title="Subscription charge failed",
        severity=Severity.MEDIUM,
        status=IssueStatus.OPEN,
        found_in=FoundIn.PROD,
        module_id=module.id,
        created_at=datetime.now(timezone.utc),
    )
    session.add(issue1)
    session.commit()
    issue2 = Issue(
        external_key="BILL-100",
        title="Another bug with same key",
        severity=Severity.HIGH,
        status=IssueStatus.OPEN,
        found_in=FoundIn.PROD,
        module_id=module.id,
        created_at=datetime.now(timezone.utc),
    )
    session.add(issue2)

    with pytest.raises(IntegrityError):
        session.commit()

def test_issue_transition_roundtrip(session):
    # 1. Cria o módulo e a issue
    module = Module(name="Search", owner_team="Discovery")
    session.add(module)
    session.commit()
    issue = Issue(
        external_key="SEARCH-42",
        title="Search indexing timeout",
        severity=Severity.LOW,
        status=IssueStatus.OPEN,
        found_in=FoundIn.PR,
        module_id=module.id,
        created_at=datetime.now(timezone.utc),
    )
    session.add(issue)
    session.commit()
    # 2. Registra uma transição (ex: OPEN -> IN_PROGRESS)
    now = datetime.now(timezone.utc)
    transition = IssueTransition(
        issue_id=issue.id,
        from_status=IssueStatus.OPEN,
        to_status=IssueStatus.IN_PROGRESS,
        transitioned_at=now,
        actor="developer_alice",
    )
    session.add(transition)
    session.commit()
    # 3. Consulta de volta
    saved_transition = (
        session.query(IssueTransition).filter_by(issue_id=issue.id).one()
    )
    # 4. Asserções
    assert saved_transition.from_status == IssueStatus.OPEN
    assert saved_transition.to_status == IssueStatus.IN_PROGRESS
    assert saved_transition.actor == "developer_alice"
    assert saved_transition.issue_id == issue.id