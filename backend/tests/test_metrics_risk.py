from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db.base import Base
from app.db.models import Issue, Module
from app.domain.enums import FoundIn, IssueStatus, Severity
from app.seeds.generator import seed_database
from app.metrics.defects import count_open_s1_production_defects
from app.metrics.risk import (
    calculate_risk_and_density,
    calculate_severity_module_heatmap,
    evaluate_release_gate,
)

@pytest.fixture
def seeded_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_database(session, seed=42)
        yield session

@pytest.fixture
def empty_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_calculate_risk_and_density(seeded_session):
    window_end = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    result = calculate_risk_and_density(seeded_session, window_days=60, as_of=window_end)
    assert result.total_risk_score > 0
    assert len(result.module_metrics) == 5
    for mod in result.module_metrics:
        assert mod.defect_count >= 0
        assert mod.risk_score >= 0
        assert mod.defect_density >= 0.0
def test_calculate_severity_module_heatmap(seeded_session):
    window_end = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    heatmap = calculate_severity_module_heatmap(seeded_session, window_days=60, as_of=window_end)
    assert len(heatmap.modules) == 5
    total_cells = sum(
        count for row in heatmap.matrix.values() for count in row.values()
    )
    assert total_cells == 50
def test_evaluate_release_gate_blocked_on_golden_dataset(seeded_session):
    window_end = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    gate = evaluate_release_gate(seeded_session, window_days=60, as_of=window_end)
    assert gate.status == "BLOCKED"
    assert 0 <= gate.readiness_score < 100
    assert len(gate.checks) == 5
    failed_blockers = [
        c for c in gate.checks if c.severity == "BLOCKER" and not c.passed
    ]
    assert len(failed_blockers) >= 1
def test_evaluate_release_gate_ready_when_clean(empty_session):
    now = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    mod = Module(id="mod-1", name="checkout", owner_team="Payments")
    empty_session.add(mod)
    empty_session.commit()
    assert count_open_s1_production_defects(empty_session) == 0
    gate = evaluate_release_gate(empty_session, window_days=14, as_of=now)
    assert gate.status == "READY"
    assert gate.readiness_score == 100
    assert all(c.passed for c in gate.checks)
def test_evaluate_release_gate_warning_on_high_escape_rate(empty_session):
    now = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    mod = Module(id="mod-1", name="checkout", owner_team="Payments")
    empty_session.add(mod)
    empty_session.add(
        Issue(
            id="iss-1",
            external_key="KAN-1",
            title="Minor UI alignment in prod",
            severity=Severity.LOW,
            status=IssueStatus.RESOLVED,
            found_in=FoundIn.PROD,
            module_id="mod-1",
            created_at=now,
            resolved_at=now,
        )
    )
    empty_session.commit()
    gate = evaluate_release_gate(empty_session, window_days=14, as_of=now)
    assert gate.status == "WARNING"
    assert gate.readiness_score == 90
    escape_check = next(c for c in gate.checks if c.id == "escape_rate")
    assert escape_check.passed is False