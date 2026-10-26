from sqlalchemy import create_engine
from app.db.base import Base
import app.db.models
import pytest
from sqlalchemy.orm import Session
from app.db.models import Module, Issue
from datetime import datetime, timezone
from app.domain.enums import Severity, IssueStatus, FoundIn
from sqlalchemy.exc import IntegrityError
from app.db.models import (Module, Issue, IssueTransition, TestRun, TestCase, TestAttempt, ScenarioAlias, TestStatus, compute_scenario_id,)

def test_tables_create():
    engine= create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

def test_expected_tables_registered():
    assert {"modules", "issues", "issue_transitions", "test_runs", "test_cases", "test_attempts", "scenario_aliases"} <= set(Base.metadata.tables)

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

def test_expected_tables_registered():
    assert {"modules", "issues", "issue_transitions", "test_runs", "test_cases", "test_attempts", "scenario_aliases"} <= set(Base.metadata.tables)

def test_test_run_roundtrip(session):
    now = datetime.now(timezone.utc)
    run = TestRun(
        suite_name="e2e-checkout",
        git_commit_sha="a1b2c3d4e5f67890123456789012345678901234",
        environment="staging",
        total_count=100,
        passed_count=95,
        failed_count=3,
        skipped_count=2,
        duration_ms=45200,
        executed_at=now,
    )
    session.add(run)
    session.commit()
    saved = session.query(TestRun).filter_by(suite_name="e2e-checkout").one()
    assert saved.passed_count == 95
    assert saved.environment == "staging"
    assert len(saved.id) == 36
def test_test_run_idempotency_duplicate_raises(session):
    now = datetime.now(timezone.utc)
    commit_sha = "abcdef1234567890abcdef1234567890abcdef12"
    run1 = TestRun(
        suite_name="unit-tests",
        git_commit_sha=commit_sha,
        environment="ci",
        total_count=50,
        passed_count=50,
        failed_count=0,
        skipped_count=0,
        duration_ms=1200,
        executed_at=now,
    )
    session.add(run1)
    session.commit()
    run2 = TestRun(
        suite_name="unit-tests",
        git_commit_sha=commit_sha,
        environment="ci",
        total_count=50,
        passed_count=50,
        failed_count=0,
        skipped_count=0,
        duration_ms=1200,
        executed_at=now,
    )
    session.add(run2)
    with pytest.raises(IntegrityError):
        session.commit()

def test_compute_scenario_id_is_deterministic():
    hash1 = compute_scenario_id("e2e", "CheckoutFeature", "should pay with credit card")
    hash2 = compute_scenario_id("e2e", "CheckoutFeature", "should pay with credit card")
    different_hash = compute_scenario_id("e2e", "CheckoutFeature", "should pay with pix")
    assert hash1 == hash2
    assert len(hash1) == 64
    assert hash1 != different_hash

def test_test_case_and_attempt_roundtrip(session):
    module = Module(name="Payments", owner_team="Checkout Squad")
    session.add(module)
    session.commit()
    run = TestRun(
        suite_name="e2e-checkout",
        git_commit_sha="1122334455667788990011223344556677889900",
        environment="ci",
        total_count=1,
        passed_count=1,
        failed_count=0,
        skipped_count=0,
        duration_ms=5000,
        executed_at=datetime.now(timezone.utc),
    )
    session.add(run)
    session.commit()
    scenario_id = compute_scenario_id("e2e-checkout", "Card", "payment success")
    case = TestCase(
        test_run_id=run.id,
        scenario_id=scenario_id,
        scenario_title="payment success",
        module_id=module.id,
        status=TestStatus.PASSED,
        duration_ms=4800,
        is_flaky=True,
        retry_count=1,
    )
    session.add(case)
    session.commit()
    attempt1 = TestAttempt(
        test_case_id=case.id,
        attempt_no=1,
        status=TestStatus.FAILED,
        duration_ms=2500,
        error_message="Gateway timeout",
    )
    attempt2 = TestAttempt(
        test_case_id=case.id,
        attempt_no=2,
        status=TestStatus.PASSED,
        duration_ms=2300,
    )
    session.add_all([attempt1, attempt2])
    session.commit()
    # 4. Asserções
    saved_case = session.query(TestCase).filter_by(scenario_id=scenario_id).one()
    assert saved_case.is_flaky is True
    assert saved_case.module_id == module.id
    attempts = session.query(TestAttempt).filter_by(test_case_id=case.id).order_by(TestAttempt.attempt_no).all()
    assert len(attempts) == 2
    assert attempts[0].status == TestStatus.FAILED
    assert attempts[0].error_message == "Gateway timeout"
    assert attempts[1].status == TestStatus.PASSED