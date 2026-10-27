from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
import app.db.models
from app.seeds.generator import seed_database
from app.seeds.golden_dataset import GOLDEN_EXPECTATIONS_DEFECTS
from app.metrics.defects import calculate_reopen_rate, calculate_mttr_and_sla
from app.domain.enums import Severity
from app.metrics.defects import (
    calculate_reopen_rate,
    calculate_mttr_and_sla,
    calculate_escape_rate,
    calculate_open_defect_age,
)


@pytest.fixture
def seeded_session():
    """Cria banco em memória e popula com o Golden Dataset."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_database(session, seed=42)
        yield session


def test_calculate_reopen_rate_matches_golden_dataset(seeded_session):
    window_end = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    
    metrics = calculate_reopen_rate(seeded_session, window_days=60, as_of=window_end)
    assert metrics.resolved_count == GOLDEN_EXPECTATIONS_DEFECTS.resolved_issues
    assert metrics.reopened_count == GOLDEN_EXPECTATIONS_DEFECTS.reopened_issues  
    assert metrics.reopen_rate == GOLDEN_EXPECTATIONS_DEFECTS.expected_reopen_rate  


def test_calculate_mttr_and_sla_matches_golden_dataset(seeded_session):
    window_end = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)

    result = calculate_mttr_and_sla(
        seeded_session,
        window_days=60,
        as_of=window_end,
        sla_targets={Severity.CRITICAL: 4.0, Severity.HIGH: 24.0},
    )


    assert result.sla_breaches[Severity.CRITICAL] == GOLDEN_EXPECTATIONS_DEFECTS.sev1_breaches
    assert result.sla_breaches[Severity.HIGH] == GOLDEN_EXPECTATIONS_DEFECTS.sev2_breaches     


    assert result.mttr_first_resolution_hours[Severity.CRITICAL] == 6.0


    assert result.total_lead_time_hours[Severity.CRITICAL] >= result.mttr_first_resolution_hours[Severity.CRITICAL]

def test_calculate_escape_rate_matches_golden_dataset(seeded_session):
    window_end = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    
    escape_metrics = calculate_escape_rate(seeded_session, window_days=60, as_of=window_end)
    assert escape_metrics.total_defects == GOLDEN_EXPECTATIONS_DEFECTS.total_issues             # 50
    assert escape_metrics.escaped_defects == GOLDEN_EXPECTATIONS_DEFECTS.production_escaped_issues # 5
    assert escape_metrics.escape_rate == GOLDEN_EXPECTATIONS_DEFECTS.expected_escape_rate       # 10.0%
def test_calculate_open_defect_age(seeded_session):
    window_end = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    
    age_metrics = calculate_open_defect_age(seeded_session, as_of=window_end)
    # Sabemos que há issues abertas (10 issues criadas como OPEN + 2 reabertas = 12 abertas)
    assert age_metrics.total_open_defects == 12
    # Para qualquer severidade que tenha bugs abertos, o P90 deve ser >= P50
    for sev, count in age_metrics.open_count_by_severity.items():
        if count > 0:
            assert age_metrics.p90_age_days[sev] >= age_metrics.p50_age_days[sev]