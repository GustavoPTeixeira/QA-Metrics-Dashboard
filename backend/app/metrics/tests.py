from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.models import Module, TestCase, TestRun
from app.domain.enums import TestStatus


@dataclass(frozen=True)
class TestPassAndFlakyRatesResult:
    total_executed: int
    first_attempt_passed: int
    final_passed: int
    flaky_count: int
    first_attempt_pass_rate: float
    final_pass_rate: float
    flaky_rate: float


@dataclass(frozen=True)
class QuarantineRecommendation:
    scenario_id: str
    scenario_title: str
    total_runs: int
    flaky_runs: int
    flakiness_pct: float
    module_name: str
    owner_team: str


def _to_utc(dt: datetime) -> datetime:
    """Garante que a data seja offset-aware em UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def calculate_test_pass_and_flaky_rates(
    session: Session,
    window_days: int = 60,
    as_of: datetime | None = None,
) -> TestPassAndFlakyRatesResult:
    """Calcula taxas de passagem (1ª tentativa vs final) e taxa de flakiness na janela."""
    if as_of is None:
        as_of = datetime.now(timezone.utc)
    as_of = _to_utc(as_of)
    window_start = as_of - timedelta(days=window_days)

    # Busca todos os TestCases executados dentro de TestRuns na janela
    cases = (
        session.query(TestCase)
        .join(TestRun, TestCase.test_run_id == TestRun.id)
        .filter(TestRun.executed_at >= window_start, TestRun.executed_at <= as_of)
        .all()
    )

    executed_cases = [c for c in cases if c.status != TestStatus.SKIPPED]
    total_executed = len(executed_cases)

    if total_executed == 0:
        return TestPassAndFlakyRatesResult(
            total_executed=0,
            first_attempt_passed=0,
            final_passed=0,
            flaky_count=0,
            first_attempt_pass_rate=0.0,
            final_pass_rate=0.0,
            flaky_rate=0.0,
        )

    # Passou na 1ª tentativa: status PASSED e não foi instável
    first_attempt_passed = sum(
        1 for c in executed_cases if c.status == TestStatus.PASSED and not c.is_flaky
    )
    # Passagem final: passou na 1ª tentativa OU passou após retries
    final_passed = sum(1 for c in executed_cases if c.status == TestStatus.PASSED)
    # Execuções instáveis
    flaky_count = sum(1 for c in executed_cases if c.is_flaky)

    return TestPassAndFlakyRatesResult(
        total_executed=total_executed,
        first_attempt_passed=first_attempt_passed,
        final_passed=final_passed,
        flaky_count=flaky_count,
        first_attempt_pass_rate=round((first_attempt_passed / total_executed) * 100, 2),
        final_pass_rate=round((final_passed / total_executed) * 100, 2),
        flaky_rate=round((flaky_count / total_executed) * 100, 2),
    )


def get_quarantine_recommendations(
    session: Session,
    window_days: int = 60,
    as_of: datetime | None = None,
    min_flakiness_pct: float = 10.0,
    min_runs: int = 10,
) -> list[QuarantineRecommendation]:
    """Identifica cenários candidatos a quarentena com base no histórico de 60 dias."""
    if as_of is None:
        as_of = datetime.now(timezone.utc)
    as_of = _to_utc(as_of)
    window_start = as_of - timedelta(days=window_days)

    cases = (
        session.query(TestCase, Module)
        .join(TestRun, TestCase.test_run_id == TestRun.id)
        .join(Module, TestCase.module_id == Module.id)
        .filter(TestRun.executed_at >= window_start, TestRun.executed_at <= as_of)
        .all()
    )

    # Agrupa por cenário
    scenarios: dict[str, dict] = {}
    for case, module in cases:
        if case.scenario_id not in scenarios:
            scenarios[case.scenario_id] = {
                "title": case.scenario_title,
                "total_runs": 0,
                "flaky_runs": 0,
                "module_name": module.name,
                "owner_team": module.owner_team,
            }
        scenarios[case.scenario_id]["total_runs"] += 1
        if case.is_flaky:
            scenarios[case.scenario_id]["flaky_runs"] += 1

    recommendations: list[QuarantineRecommendation] = []
    for scenario_id, data in scenarios.items():
        total = data["total_runs"]
        flaky = data["flaky_runs"]
        pct = round((flaky / total) * 100, 2) if total > 0 else 0.0

        if pct > min_flakiness_pct and total >= min_runs:
            recommendations.append(
                QuarantineRecommendation(
                    scenario_id=scenario_id,
                    scenario_title=data["title"],
                    total_runs=total,
                    flaky_runs=flaky,
                    flakiness_pct=pct,
                    module_name=data["module_name"],
                    owner_team=data["owner_team"],
                )
            )

    return recommendations