from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.models import Issue, Module, TestCase
from app.domain.enums import Severity


@dataclass(frozen=True)
class ModuleRiskMetric:
    module_id: str
    module_name: str
    owner_team: str
    defect_count: int
    risk_score: int
    test_scenario_count: int
    defect_density: float


@dataclass(frozen=True)
class RiskAndDensityResult:
    total_risk_score: int
    module_metrics: list[ModuleRiskMetric]


@dataclass(frozen=True)
class HeatmapResult:
    modules: list[str]
    severities: list[str]
    matrix: dict[str, dict[str, int]]  # module_name -> {severity_name: count}


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def calculate_risk_and_density(
    session: Session,
    window_days: int = 60,
    as_of: datetime | None = None,
) -> RiskAndDensityResult:
    """Calcula o Risk Score ponderado e a Densidade de Defeitos por módulo."""
    if as_of is None:
        as_of = datetime.now(timezone.utc)
    as_of = _to_utc(as_of)
    window_start = as_of - timedelta(days=window_days)

    modules = session.query(Module).all()
    issues = (
        session.query(Issue)
        .filter(Issue.created_at >= window_start, Issue.created_at <= as_of)
        .all()
    )
    test_cases = session.query(TestCase).all()

    # Mapeia testes únicos por módulo para calcular tamanho do módulo
    scenarios_per_module: dict[str, set[str]] = {m.id: set() for m in modules}
    for tc in test_cases:
        if tc.module_id in scenarios_per_module:
            scenarios_per_module[tc.module_id].add(tc.scenario_id)

    # Mapeia defeitos por módulo
    issues_per_module: dict[str, list[Issue]] = {m.id: [] for m in modules}
    for issue in issues:
        if issue.module_id in issues_per_module:
            issues_per_module[issue.module_id].append(issue)

    module_metrics: list[ModuleRiskMetric] = []
    total_global_risk = 0

    for m in modules:
        mod_issues = issues_per_module[m.id]
        defect_count = len(mod_issues)
        
        # Risk = (4 * Sev1) + (3 * Sev2) + (2 * Sev3) + (1 * Sev4)
        risk_score = sum(issue.severity.weight for issue in mod_issues)
        total_global_risk += risk_score

        test_count = len(scenarios_per_module[m.id])
        # Densidade = defeitos / tamanho do módulo (ou total de testes)
        density = round(defect_count / test_count, 2) if test_count > 0 else float(defect_count)

        module_metrics.append(
            ModuleRiskMetric(
                module_id=m.id,
                module_name=m.name,
                owner_team=m.owner_team,
                defect_count=defect_count,
                risk_score=risk_score,
                test_scenario_count=test_count,
                defect_density=density,
            )
        )

    return RiskAndDensityResult(
        total_risk_score=total_global_risk,
        module_metrics=module_metrics,
    )


def calculate_severity_module_heatmap(
    session: Session,
    window_days: int = 60,
    as_of: datetime | None = None,
) -> HeatmapResult:
    """Gera a matriz Módulo x Severidade para o Heatmap do dashboard."""
    if as_of is None:
        as_of = datetime.now(timezone.utc)
    as_of = _to_utc(as_of)
    window_start = as_of - timedelta(days=window_days)

    modules = session.query(Module).order_by(Module.name.asc()).all()
    issues = (
        session.query(Issue)
        .filter(Issue.created_at >= window_start, Issue.created_at <= as_of)
        .all()
    )

    module_names = [m.name for m in modules]
    severity_names = [s.value for s in Severity]

    # Inicializa a matriz com zeros
    matrix: dict[str, dict[str, int]] = {
        m_name: {s_name: 0 for s_name in severity_names} for m_name in module_names
    }

    module_id_to_name = {m.id: m.name for m in modules}
    for issue in issues:
        m_name = module_id_to_name.get(issue.module_id)
        if m_name and issue.severity.value in matrix[m_name]:
            matrix[m_name][issue.severity.value] += 1

    return HeatmapResult(
        modules=module_names,
        severities=severity_names,
        matrix=matrix,
    )