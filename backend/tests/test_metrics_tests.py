from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
import app.db.models
from app.seeds.generator import seed_database
from app.seeds.golden_dataset import GOLDEN_EXPECTATIONS_TESTS
from app.metrics.tests import calculate_test_pass_and_flaky_rates, get_quarantine_recommendations


@pytest.fixture
def seeded_session():
    """Cria banco em memória e popula com o Golden Dataset."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_database(session, seed=42)
        yield session


def test_calculate_test_rates_matches_golden_dataset(seeded_session):
    window_end = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)

    metrics = calculate_test_pass_and_flaky_rates(seeded_session, window_days=60, as_of=window_end)

    # 1. Contagens brutas
    assert metrics.total_executed == GOLDEN_EXPECTATIONS_TESTS.total_executed_tests # 100
    assert metrics.first_attempt_passed == GOLDEN_EXPECTATIONS_TESTS.first_attempt_passes # 90
    assert metrics.final_passed == GOLDEN_EXPECTATIONS_TESTS.final_passes # 95
    assert metrics.flaky_count == GOLDEN_EXPECTATIONS_TESTS.flaky_executions # 5

    # 2. Taxas percentuais
    assert metrics.first_attempt_pass_rate == GOLDEN_EXPECTATIONS_TESTS.expected_first_attempt_pass_rate # 90.0%
    assert metrics.final_pass_rate == GOLDEN_EXPECTATIONS_TESTS.expected_final_pass_rate # 95.0%
    assert metrics.flaky_rate == GOLDEN_EXPECTATIONS_TESTS.expected_execution_flaky_rate # 5.0%


def test_quarantine_recommendations(seeded_session):
    window_end = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)

    # Limiar padrão: flakiness > 10% e mínimo de 10 execuções
    recommendations = get_quarantine_recommendations(
        seeded_session,
        window_days=60,
        as_of=window_end,
        min_flakiness_pct=10.0,
        min_runs=10,
    )

    # Deve encontrar exatamente 1 cenário na quarentena
    assert len(recommendations) == 1
    rec = recommendations[0]

    assert rec.scenario_id == GOLDEN_EXPECTATIONS_TESTS.quarantine_candidate_scenario_id
    assert rec.scenario_title == "payment_with_pix_timeout"
    assert rec.total_runs == 10
    assert rec.flaky_runs == 3
    assert rec.flakiness_pct == 30.0
    assert rec.module_name == "Checkout"
    assert rec.owner_team == "Orders Squad"