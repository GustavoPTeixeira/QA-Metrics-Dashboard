from dataclasses import dataclass
from app.db.models import compute_scenario_id
@dataclass(frozen=True)
class ExpectedDefectMetrics:
    total_issues: int
    resolved_issues: int
    reopened_issues: int
    expected_reopen_rate: float
    production_escaped_issues: int
    expected_escape_rate: float  
    sev1_breaches: int
    sev2_breaches: int
@dataclass(frozen=True)
class ExpectedTestMetrics:
    total_runs: int
    total_executed_tests: int
    first_attempt_passes: int
    final_passes: int
    flaky_executions: int
    expected_first_attempt_pass_rate: float
    expected_final_pass_rate: float
    expected_execution_flaky_rate: float
    quarantine_candidate_scenario_id: str

GOLDEN_EXPECTATIONS_DEFECTS = ExpectedDefectMetrics(
    total_issues=50,
    resolved_issues=40,
    reopened_issues=2,
    expected_reopen_rate=5.0,
    production_escaped_issues=5,
    expected_escape_rate=10.0,
    sev1_breaches=1,
    sev2_breaches=1,
)

QUARANTINE_SCENARIO_ID = compute_scenario_id(
    suite_name="e2e-checkout",
    class_or_feature="CheckoutFeature",
    scenario_title="payment_with_pix_timeout",
)

GOLDEN_EXPECTATIONS_TESTS = ExpectedTestMetrics(
    total_runs=10,
    total_executed_tests=100,
    first_attempt_passes=90,
    final_passes=95,
    flaky_executions=5,
    expected_first_attempt_pass_rate=90.0,
    expected_final_pass_rate=95.0,
    expected_execution_flaky_rate=5.0,

quarantine_candidate_scenario_id=QUARANTINE_SCENARIO_ID
,
)