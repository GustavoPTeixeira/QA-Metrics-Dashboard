from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
import app.db.models
from app.seeds.generator import seed_database
from app.metrics.risk import calculate_risk_and_density, calculate_severity_module_heatmap


@pytest.fixture
def seeded_session():
    """Cria banco em memória e popula com o Golden Dataset."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_database(session, seed=42)
        yield session


def test_calculate_risk_and_density(seeded_session):
    window_end = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)

    result = calculate_risk_and_density(seeded_session, window_days=60, as_of=window_end)

    # 1. Total de risco global calculado pela soma ponderada (4*Sev1 + 3*Sev2 + 2*Sev3 + 1*Sev4)
    assert result.total_risk_score > 0

    # 2. Cada módulo deve ter uma densidade de defeitos calculada
    assert len(result.module_metrics) == 5
    for mod in result.module_metrics:
        assert mod.defect_count >= 0
        assert mod.risk_score >= 0
        assert mod.defect_density >= 0.0


def test_calculate_severity_module_heatmap(seeded_session):
    window_end = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)

    heatmap = calculate_severity_module_heatmap(seeded_session, window_days=60, as_of=window_end)

    # Deve conter os 5 módulos canônicos
    assert len(heatmap.modules) == 5
    # A soma de todas as células da matriz deve ser igual ao total de 50 defeitos
    total_cells = sum(
        count for row in heatmap.matrix.values() for count in row.values()
    )
    assert total_cells == 50