from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.domain.enums import Severity
from app.metrics.defects import (
    calculate_escape_rate,
    calculate_mttr_and_sla,
    calculate_open_defect_age,
    calculate_reopen_rate,
)
from app.metrics.risk import calculate_severity_module_heatmap
from app.metrics.tests import (
    calculate_test_pass_and_flaky_rates,
    get_quarantine_recommendations,
)

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/kpis")
def get_dashboard_kpis(
    window_days: int = Query(60, description="Janela de análise histórica em dias"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retorna a Linha de KPIs Executivos com tamanhos de amostra (n) e metas."""
    reopen = calculate_reopen_rate(db, window_days=window_days)
    mttr = calculate_mttr_and_sla(db, window_days=window_days)
    test_rates = calculate_test_pass_and_flaky_rates(db, window_days=window_days)
    quarantine = get_quarantine_recommendations(db, window_days=window_days)
    escape = calculate_escape_rate(db, window_days=window_days)
    open_age = calculate_open_defect_age(db)

    return {
        "window_days": window_days,
        "kpis": {
            "mttr": {
                "sev1_hours": mttr.mttr_first_resolution_hours.get(Severity.CRITICAL, 0.0),
                "sev2_hours": mttr.mttr_first_resolution_hours.get(Severity.HIGH, 0.0),
                "sev1_breaches": mttr.sla_breaches.get(Severity.CRITICAL, 0),
                "sev2_breaches": mttr.sla_breaches.get(Severity.HIGH, 0),
            },
            "reopen_rate": {
                "rate_pct": reopen.reopen_rate,
                "reopened_count": reopen.reopened_count,
                "resolved_count": reopen.resolved_count,
            },
            "test_pass_rate": {
                "final_pass_rate_pct": test_rates.final_pass_rate,
                "first_attempt_pass_rate_pct": test_rates.first_attempt_pass_rate,
                "total_executed_tests": test_rates.total_executed,
            },
            "flakiness": {
                "execution_flaky_rate_pct": test_rates.flaky_rate,
                "flaky_executions_count": test_rates.flaky_count,
                "quarantine_candidates_count": len(quarantine),
            },
            "escape_rate": {
                "rate_pct": escape.escape_rate,
                "escaped_count": escape.escaped_defects,
                "total_defects": escape.total_defects,
            },
            "open_defects": {
                "total_open": open_age.total_open_defects,
            },
        },
    }


@router.get("/heatmap")
def get_dashboard_heatmap(
    window_days: int = Query(60, description="Janela de análise histórica em dias"),
    db: Session = Depends(get_db),
):
    """Retorna a matriz Módulo x Severidade para renderização do Heatmap."""
    heatmap = calculate_severity_module_heatmap(db, window_days=window_days)
    return {
        "modules": heatmap.modules,
        "severities": heatmap.severities,
        "matrix": heatmap.matrix,
    }


@router.get("/quarantine")
def get_dashboard_quarantine(
    window_days: int = Query(60, description="Janela de análise histórica em dias"),
    min_flakiness_pct: float = Query(10.0, description="Limiar mínimo de instabilidade %"),
    min_runs: int = Query(10, description="Mínimo de execuções para recomendação"),
    db: Session = Depends(get_db),
):
    """Retorna os testes instáveis recomendados para quarentena (Hall of Shame)."""
    recommendations = get_quarantine_recommendations(
        db,
        window_days=window_days,
        min_flakiness_pct=min_flakiness_pct,
        min_runs=min_runs,
    )
    return [
        {
            "scenario_id": r.scenario_id,
            "scenario_title": r.scenario_title,
            "total_runs": r.total_runs,
            "flaky_runs": r.flaky_runs,
            "flakiness_pct": r.flakiness_pct,
            "module_name": r.module_name,
            "owner_team": r.owner_team,
        }
        for r in recommendations
    ]