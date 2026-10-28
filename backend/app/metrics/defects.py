from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.models import Issue, IssueTransition
from app.domain.enums import IssueStatus, Severity
from app.domain.enums import FoundIn, IssueStatus, Severity


@dataclass(frozen=True)
class ReopenRateResult:
    resolved_count: int
    reopened_count: int
    reopen_rate: float


@dataclass(frozen=True)
class MTTRResult:
    mttr_first_resolution_hours: dict[Severity, float]
    total_lead_time_hours: dict[Severity, float]
    sla_breaches: dict[Severity, int]
    resolved_counts: dict[Severity, int]


def calculate_reopen_rate(
    session: Session,
    window_days: int = 60,
    as_of: datetime | None = None,
) -> ReopenRateResult:
    """Calcula a Taxa de Reabertura (Cohort-Based) estritamente pela tabela IssueTransition."""
    if as_of is None:
        as_of = datetime.now(timezone.utc)

    window_start = as_of - timedelta(days=window_days)

    resolution_transitions = (
        session.query(IssueTransition)
        .filter(
            IssueTransition.to_status == IssueStatus.RESOLVED,
            IssueTransition.transitioned_at >= window_start,
            IssueTransition.transitioned_at <= as_of,
        )
        .all()
    )

    resolved_cohort: dict[str, datetime] = {}
    for t in resolution_transitions:
        if t.issue_id not in resolved_cohort or t.transitioned_at < resolved_cohort[t.issue_id]:
            resolved_cohort[t.issue_id] = t.transitioned_at

    resolved_count = len(resolved_cohort)
    if resolved_count == 0:
        return ReopenRateResult(resolved_count=0, reopened_count=0, reopen_rate=0.0)

    reopened_issue_ids = set()
    reopen_transitions = (
        session.query(IssueTransition)
        .filter(
            IssueTransition.issue_id.in_(list(resolved_cohort.keys())),
            IssueTransition.to_status == IssueStatus.OPEN,
        )
        .all()
    )

    for t in reopen_transitions:
        resolution_time = resolved_cohort[t.issue_id]
        if t.transitioned_at > resolution_time:
            reopened_issue_ids.add(t.issue_id)

    reopened_count = len(reopened_issue_ids)
    rate = round((reopened_count / resolved_count) * 100, 2)

    return ReopenRateResult(
        resolved_count=resolved_count,
        reopened_count=reopened_count,
        reopen_rate=rate,
    )


def calculate_mttr_and_sla(
    session: Session,
    window_days: int = 60,
    as_of: datetime | None = None,
    sla_targets: dict[Severity, float] | None = None,
) -> MTTRResult:
    """Calcula MTTR (1ª Resolução vs Lead Time Total) e Violações de SLA por severidade."""
    if as_of is None:
        as_of = datetime.now(timezone.utc)
    if sla_targets is None:
        sla_targets = {Severity.CRITICAL: 4.0, Severity.HIGH: 24.0}

    window_start = as_of - timedelta(days=window_days)

    resolved_transitions = (
        session.query(IssueTransition)
        .filter(
            IssueTransition.to_status == IssueStatus.RESOLVED,
            IssueTransition.transitioned_at >= window_start,
            IssueTransition.transitioned_at <= as_of,
        )
        .all()
    )

    issue_ids = list({t.issue_id for t in resolved_transitions})
    if not issue_ids:
        empty_floats = {s: 0.0 for s in Severity}
        empty_ints = {s: 0 for s in Severity}
        return MTTRResult(empty_floats, empty_floats, empty_ints, empty_ints)

    issues = session.query(Issue).filter(Issue.id.in_(issue_ids)).all()
    issues_by_id = {i.id: i for i in issues}

    all_transitions = (
        session.query(IssueTransition)
        .filter(
            IssueTransition.issue_id.in_(issue_ids),
            IssueTransition.to_status == IssueStatus.RESOLVED,
        )
        .order_by(IssueTransition.transitioned_at.asc())
        .all()
    )

    transitions_by_issue: dict[str, list[datetime]] = {}
    for t in all_transitions:
        transitions_by_issue.setdefault(t.issue_id, []).append(t.transitioned_at)

    first_res_durations: dict[Severity, list[float]] = {s: [] for s in Severity}
    lead_time_durations: dict[Severity, list[float]] = {s: [] for s in Severity}
    sla_breaches: dict[Severity, int] = {s: 0 for s in Severity}

    for issue_id, res_times in transitions_by_issue.items():
        issue = issues_by_id[issue_id]
        created_at = issue.created_at

        first_res_hours = (res_times[0] - created_at).total_seconds() / 3600.0
        final_res_hours = (res_times[-1] - created_at).total_seconds() / 3600.0

        first_res_durations[issue.severity].append(first_res_hours)
        lead_time_durations[issue.severity].append(final_res_hours)

        target = sla_targets.get(issue.severity)
        if target is not None and first_res_hours > target:
            sla_breaches[issue.severity] += 1

    mttr_first: dict[Severity, float] = {}
    mttr_lead: dict[Severity, float] = {}
    resolved_counts: dict[Severity, int] = {}

    for s in Severity:
        resolved_counts[s] = len(first_res_durations[s])
        mttr_first[s] = (
            round(sum(first_res_durations[s]) / len(first_res_durations[s]), 1)
            if first_res_durations[s]
            else 0.0
        )
        mttr_lead[s] = (
            round(sum(lead_time_durations[s]) / len(lead_time_durations[s]), 1)
            if lead_time_durations[s]
            else 0.0
        )

    return MTTRResult(
        mttr_first_resolution_hours=mttr_first,
        total_lead_time_hours=mttr_lead,
        sla_breaches=sla_breaches,
        resolved_counts=resolved_counts,
    )

@dataclass(frozen=True)
class EscapeRateResult:
    total_defects: int
    escaped_defects: int
    escape_rate: float
@dataclass(frozen=True)
class OpenDefectAgeResult:
    total_open_defects: int
    open_count_by_severity: dict[Severity, int]
    p50_age_days: dict[Severity, float]
    p90_age_days: dict[Severity, float]
def _percentile(values: list[float], p: float) -> float:
    """Calcula percentis (P50, P90) de forma precisa e determinística."""
    if not values:
        return 0.0
    sorted_v = sorted(values)
    k = (len(sorted_v) - 1) * (p / 100.0)
    f = int(k)
    c = f + 1
    if c < len(sorted_v):
        return round(sorted_v[f] + (k - f) * (sorted_v[c] - sorted_v[f]), 1)
    return round(sorted_v[f], 1)

def to_utc(dt: datetime) -> datetime:
    """Garante que a data seja offset-aware em UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def calculate_escape_rate(
    session: Session,
    window_days: int = 60,
    as_of: datetime | None = None,
) -> EscapeRateResult:
    """Calcula a taxa de defeitos que escaparam para produção na janela."""
    if as_of is None:
        as_of = datetime.now(timezone.utc)
    window_start = as_of - timedelta(days=window_days)
    issues = (
        session.query(Issue)
        .filter(Issue.created_at >= window_start, Issue.created_at <= as_of)
        .all()
    )
    total_defects = len(issues)
    escaped_defects = sum(1 for i in issues if i.found_in == FoundIn.PROD)
    escape_rate = (
        round((escaped_defects / total_defects) * 100, 2)
        if total_defects > 0
        else 0.0
    )
    return EscapeRateResult(
        total_defects=total_defects,
        escaped_defects=escaped_defects,
        escape_rate=escape_rate,
    )
def calculate_open_defect_age(
    session: Session,
    as_of: datetime | None = None,
) -> OpenDefectAgeResult:
    """Calcula a idade dos defeitos em aberto por severidade (P50 e P90 em dias)."""
    if as_of is None:
        as_of = datetime.now(timezone.utc)
    as_of = to_utc(as_of)
    open_issues = session.query(Issue).filter(Issue.status == IssueStatus.OPEN).all()
    total_open = len(open_issues)
    ages_by_severity: dict[Severity, list[float]] = {s: [] for s in Severity}
    for issue in open_issues:
        created_at = to_utc(issue.created_at)
        age_days = (as_of - created_at).total_seconds() / 86400.0
        ages_by_severity[issue.severity].append(age_days)
    open_counts = {s: len(ages_by_severity[s]) for s in Severity}
    p50 = {s: _percentile(ages_by_severity[s], 50.0) for s in Severity}
    p90 = {s: _percentile(ages_by_severity[s], 90.0) for s in Severity}
    return OpenDefectAgeResult(
        total_open_defects=total_open,
        open_count_by_severity=open_counts,
        p50_age_days=p50,
        p90_age_days=p90,
    )

def count_open_s1_production_defects(session: Session) -> int:
    return (
        session.query(Issue)
        .filter(
            Issue.severity == Severity.CRITICAL,
            Issue.found_in == FoundIn.PROD,
            Issue.status.in_([IssueStatus.OPEN, IssueStatus.IN_PROGRESS]),
        )
        .count()
    )