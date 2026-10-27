from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import pytest
from app.db.base import Base
import app.db.models
from app.db.models import Issue, Module, TestCase, TestRun
from app.domain.enums import FoundIn, IssueStatus, TestStatus
from app.seeds.generator import seed_database
from app.seeds.golden_dataset import (
    GOLDEN_EXPECTATIONS_DEFECTS,
    GOLDEN_EXPECTATIONS_TESTS,
)
@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
def test_seed_database_matches_golden_expectations(session):
    # Executa o seed
    seed_database(session, seed=42)
    modules_count = session.query(Module).count()
    assert modules_count == 5
    total_issues = session.query(Issue).count()
    assert total_issues == GOLDEN_EXPECTATIONS_DEFECTS.total_issues
    prod_escaped = session.query(Issue).filter_by(found_in=FoundIn.PROD).count()
    assert prod_escaped == GOLDEN_EXPECTATIONS_DEFECTS.production_escaped_issues
    total_runs = session.query(TestRun).count()
    assert total_runs == GOLDEN_EXPECTATIONS_TESTS.total_runs
    total_cases = session.query(TestCase).count()
    assert total_cases == GOLDEN_EXPECTATIONS_TESTS.total_executed_tests
    flaky_cases = session.query(TestCase).filter_by(is_flaky=True).count()
    assert flaky_cases == GOLDEN_EXPECTATIONS_TESTS.flaky_executions
    quarantine_runs = (
        session.query(TestCase)
        .filter_by(scenario_id=GOLDEN_EXPECTATIONS_TESTS.quarantine_candidate_scenario_id)
        .all()
    )
    assert len(quarantine_runs) == 10
    quarantine_flaky_count = sum(1 for c in quarantine_runs if c.is_flaky)
    assert quarantine_flaky_count == 3 