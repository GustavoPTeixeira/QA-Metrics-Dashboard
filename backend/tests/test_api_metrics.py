import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
import app.db.models
from app.main import app
from app.seeds.generator import seed_database
from app.seeds.golden_dataset import (
    GOLDEN_EXPECTATIONS_DEFECTS,
    GOLDEN_EXPECTATIONS_TESTS,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def seeded_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    with TestingSessionLocal() as session:
        seed_database(session, seed=42)
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_api_get_kpis(seeded_client):
    response = seeded_client.get("/api/metrics/kpis?window_days=60")
    assert response.status_code == 200
    data = response.json()["kpis"]

    # Reopen Rate = 5.0%
    assert data["reopen_rate"]["rate_pct"] == GOLDEN_EXPECTATIONS_DEFECTS.expected_reopen_rate
    # Final Pass % = 95.0%
    assert data["test_pass_rate"]["final_pass_rate_pct"] == GOLDEN_EXPECTATIONS_TESTS.expected_final_pass_rate
    # Flaky executions = 5
    assert data["flakiness"]["flaky_executions_count"] == GOLDEN_EXPECTATIONS_TESTS.flaky_executions
    # Quarentena = 1 candidato
    assert data["flakiness"]["quarantine_candidates_count"] == 1


def test_api_get_heatmap(seeded_client):
    response = seeded_client.get("/api/metrics/heatmap?window_days=60")
    assert response.status_code == 200
    data = response.json()
    assert len(data["modules"]) == 5
    assert "Critical" in data["severities"]


def test_api_get_quarantine(seeded_client):
    response = seeded_client.get("/api/metrics/quarantine?window_days=60")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    candidate = data[0]
    assert candidate["scenario_title"] == "payment_with_pix_timeout"
    assert candidate["owner_team"] == "Orders Squad"
    assert candidate["flakiness_pct"] == 30.0


