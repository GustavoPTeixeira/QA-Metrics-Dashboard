import random
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from app.db.models import (
    Issue,
    IssueTransition,
    Module,
    TestAttempt,
    TestCase,
    TestRun,
    compute_scenario_id,
)
from app.domain.enums import FoundIn, IssueStatus, Severity, TestStatus
from app.seeds.golden_dataset import (
    GOLDEN_EXPECTATIONS_DEFECTS,
    GOLDEN_EXPECTATIONS_TESTS,
    QUARANTINE_SCENARIO_ID,
)

def create_modules(session: Session) -> dict[str, Module]:
    """Cria os módulos base e retorna um dicionário nome -> Module"""
    module_data = [
        ("Auth", "Security Squad"),
        ("Billing", "Finance Squad"),
        ("Checkout", "Orders Squad"),
        ("Search", "Discovery Squad"),
        ("Notifications", "Growth Squad")
    ]
    modules = {}
    for name, team in module_data:
        m = Module(name=name, owner_team=team)
        session.add(m)
        modules[name] = m
    session.flush()
    return modules

def seed_defects(session: Session, modules: dict[str, Module], base_date: datetime) -> list[Issue]:
    """Gera exatamente 50 issues com transições controladas para atender ao Golden Dataset."""
    module_list = list(modules.values())
    issues: list[Issue] = []

    for i in range(1, 41):
        created_at = base_date - timedelta(days=random.randint(10, 50), hours=random.randint(1, 10))
        if i == 1:
            sev = Severity.CRITICAL
            resolve_duration = timedelta(hours=6)
        elif i == 2:
            sev = Severity.HIGH
            resolve_duration = timedelta(hours=30)
        else:
            sev = random.choice([Severity.MEDIUM, Severity.LOW])
            resolve_duration = timedelta(hours=random.randint(2, 8))
        resolved_at = created_at + resolve_duration
        found_in = FoundIn.PROD if i <= 5 else FoundIn.PR
        mod = module_list[i % len(module_list)]
        issue = Issue(
            external_key=f"DEFECT-{i:03d}",
            title=f"Sample defect {i} in {mod.name}",
            severity=sev,
            status=IssueStatus.RESOLVED,
            found_in=found_in,
            module_id=mod.id,
            created_at=created_at,
            resolved_at=resolved_at,
        )
        session.add(issue)
        session.flush()

        t1 = IssueTransition(
            issue_id=issue.id,
            from_status=None,
            to_status=IssueStatus.OPEN,
            transitioned_at=created_at,
            actor="reporter_bot",
        )

        t2 = IssueTransition(
            issue_id=issue.id,
            from_status=IssueStatus.OPEN,
            to_status=IssueStatus.RESOLVED,
            transitioned_at=resolved_at,
            actor="engineer_bob",
        )
        session.add_all([t1, t2])
        
        if i in (1, 2):
            reopened_at = resolved_at + timedelta(days=2)
            t3 = IssueTransition(
                issue_id=issue.id,
                from_status=IssueStatus.RESOLVED,
                to_status=IssueStatus.OPEN,
                transitioned_at=reopened_at,
                actor="qa_tester",
            )
            session.add(t3)

            issue.status = IssueStatus.OPEN
        issues.append(issue)

    for i in range(41, 51):
        created_at = base_date - timedelta(days=random.randint(2, 20))
        mod = module_list[i % len(module_list)]
        issue = Issue(
            external_key=f"DEFECT-{i:03d}",
            title=f"Active open issue {i} in {mod.name}",
            severity=random.choice(list(Severity)),
            status=IssueStatus.OPEN,
            found_in=FoundIn.PR,
            module_id=mod.id,
            created_at=created_at,
            resolved_at=None,
        )
        session.add(issue)
        session.flush()
        t_open = IssueTransition(
            issue_id=issue.id,
            from_status=None,
            to_status=IssueStatus.OPEN,
            transitioned_at=created_at,
            actor="reporter_bot",
        )
        session.add(t_open)
        issues.append(issue)
    return issues

def seed_test_telemetry(session: Session, modules: dict[str, Module], base_date: datetime) -> list[TestRun]:
    """Gera 10 TestRuns e 100 TestCases respeitando o gabarito de métricas."""
    runs: list[TestRun] = []
    flaky_count = 0
    failed_count = 0
    checkout_module = modules["Checkout"]
    for run_idx in range(1, 11):
        executed_at = base_date - timedelta(days=(11 - run_idx) * 5)
        run = TestRun(
            suite_name="e2e-checkout",
            git_commit_sha=f"commit{run_idx:04d}000000000000000000000000000000",
            environment="ci",
            total_count=10,
            passed_count=0,  
            failed_count=0,   
            skipped_count=0,
            duration_ms=45000 + random.randint(100, 2000),
            executed_at=executed_at,
        )
        session.add(run)
        session.flush()
        run_passed = 0
        run_failed = 0
        for case_idx in range(1, 11):
            if case_idx == 1:
                feature = "CheckoutFeature"
                title = "payment_with_pix_timeout"
                scen_id = QUARANTINE_SCENARIO_ID
                is_this_flaky = run_idx in (1, 2, 3)
                is_this_failed = False
            else:
                feature = "CartFeature"
                title = f"scenario_{run_idx}_{case_idx}"
                scen_id = compute_scenario_id("e2e-checkout", feature, title)
                is_this_flaky = (run_idx == 4 and case_idx == 2) or (run_idx == 5 and case_idx == 2)
                is_this_failed = case_idx == 10 and run_idx <= 5
            if is_this_flaky:
                flaky_count += 1
                run_passed += 1
                case = TestCase(
                    test_run_id=run.id,
                    scenario_id=scen_id,
                    scenario_title=title,
                    module_id=checkout_module.id,
                    status=TestStatus.PASSED,
                    duration_ms=4200,
                    is_flaky=True,
                    retry_count=1,
                )
                session.add(case)
                session.flush()
                a1 = TestAttempt(test_case_id=case.id, attempt_no=1, status=TestStatus.FAILED, duration_ms=2100, error_message="Timeout")
                a2 = TestAttempt(test_case_id=case.id, attempt_no=2, status=TestStatus.PASSED, duration_ms=2100)
                session.add_all([a1, a2])
            elif is_this_failed:
                failed_count += 1
                run_failed += 1
                case = TestCase(
                    test_run_id=run.id,
                    scenario_id=scen_id,
                    scenario_title=title,
                    module_id=checkout_module.id,
                    status=TestStatus.FAILED,
                    duration_ms=3000,
                    is_flaky=False,
                    retry_count=1,
                )
                session.add(case)
                session.flush()
                a1 = TestAttempt(test_case_id=case.id, attempt_no=1, status=TestStatus.FAILED, duration_ms=1500, error_message="AssertionError: 500")
                a2 = TestAttempt(test_case_id=case.id, attempt_no=2, status=TestStatus.FAILED, duration_ms=1500, error_message="AssertionError: 500")
                session.add_all([a1, a2])
            else:
                run_passed += 1
                case = TestCase(
                    test_run_id=run.id,
                    scenario_id=scen_id,
                    scenario_title=title,
                    module_id=checkout_module.id,
                    status=TestStatus.PASSED,
                    duration_ms=1800,
                    is_flaky=False,
                    retry_count=0,
                )
                session.add(case)
                session.flush()
                a1 = TestAttempt(test_case_id=case.id, attempt_no=1, status=TestStatus.PASSED, duration_ms=1800)
                session.add(a1)
        run.passed_count = run_passed
        run.failed_count = run_failed
        runs.append(run)
    return runs
def seed_database(session: Session, seed: int = 42, base_date: datetime | None = None) -> None:
    """Função mestre que orquestra a geração do Golden Dataset completo."""
    random.seed(seed)
    if base_date is None:
        base_date = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    modules = create_modules(session)
    seed_defects(session, modules, base_date)
    seed_test_telemetry(session, modules, base_date)
    session.commit()