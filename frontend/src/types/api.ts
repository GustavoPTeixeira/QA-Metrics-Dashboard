export interface MTTRKpi {
    sev1_hours: number;
    sev2_hours: number;
    sev1_breaches: number;
    sev2_breaches: number;
}

export interface ReopenRateKpi {
    rate_pct: number;
    reopened_count: number;
    resolved_count: number;
}

export interface TestPassRateKpi {
  final_pass_rate_pct: number;
  first_attempt_pass_rate_pct: number;
  total_executed_tests: number;
}
export interface FlakinessKpi {
  execution_flaky_rate_pct: number;
  flaky_executions_count: number;
  quarantine_candidates_count: number;
}
export interface EscapeRateKpi {
  rate_pct: number;
  escaped_count: number;
  total_defects: number;
}
export interface OpenDefectsKpi {
  total_open: number;
}
export interface DashboardKPIsResponse {
  window_days: number;
  kpis: {
    mttr: MTTRKpi;
    reopen_rate: ReopenRateKpi;
    test_pass_rate: TestPassRateKpi;
    flakiness: FlakinessKpi;
    escape_rate: EscapeRateKpi;
    open_defects: OpenDefectsKpi;
  };
}
export interface HeatmapResponse {
  modules: string[];
  severities: string[];
  matrix: Record<string, Record<string, number>>;
}
export interface QuarantineCandidate {
  scenario_id: string;
  scenario_title: string;
  module_name: string;
  owner_team: string;
  total_runs: number;
  flaky_runs: number;
  flakiness_pct: number;
  recommendation: string;
}