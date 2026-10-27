import {
  AlertTriangle,
  Bug,
  CheckCircle2,
  Clock,
  Flame,
  RotateCcw,
} from "lucide-react";
import { DashboardKPIsResponse } from "@/types/api";
import { KpiCard } from "./KpiCard";

interface KpiGridProps {
  data: DashboardKPIsResponse;
}

export function KpiGrid({ data }: KpiGridProps) {
  const {
    mttr,
    reopen_rate,
    test_pass_rate,
    flakiness,
    escape_rate,
    open_defects,
  } = data.kpis;

  const totalSlaBreaches = mttr.sev1_breaches + mttr.sev2_breaches;

  return (
    <section aria-label="Executive KPIs">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* 1. MTTR & SLA Breaches */}
        <KpiCard
          title="MTTR (Sev1 / Sev2)"
          value={`${mttr.sev1_hours}h / ${mttr.sev2_hours}h`}
          subtitle={`SLA Breaches: ${mttr.sev1_breaches} Sev1, ${mttr.sev2_breaches} Sev2`}
          sampleInfo="SLA: 4h / 24h"
          status={totalSlaBreaches === 0 ? "healthy" : "critical"}
          statusLabel={
            totalSlaBreaches === 0
              ? "Within SLA"
              : `${totalSlaBreaches} Breaches`
          }
          icon={<Clock className="w-4 h-4" />}
        />

        {/* 2. Cohort Reopen Rate */}
        <KpiCard
          title="Cohort Reopen Rate"
          value={`${reopen_rate.rate_pct}%`}
          subtitle={`${reopen_rate.reopened_count} reopened of ${reopen_rate.resolved_count} resolved`}
          sampleInfo={`n=${reopen_rate.resolved_count}`}
          status={
            reopen_rate.rate_pct <= 5
              ? "healthy"
              : reopen_rate.rate_pct <= 10
              ? "warning"
              : "critical"
          }
          statusLabel="Target ≤ 5.0%"
          icon={<RotateCcw className="w-4 h-4" />}
        />

        {/* 3. Test Pass Rate (Final vs First Attempt) */}
        <KpiCard
          title="Test Suite Pass Rate"
          value={`${test_pass_rate.final_pass_rate_pct}%`}
          subtitle={`First attempt pass: ${test_pass_rate.first_attempt_pass_rate_pct}%`}
          sampleInfo={`n=${test_pass_rate.total_executed_tests}`}
          status={
            test_pass_rate.final_pass_rate_pct >= 95
              ? "healthy"
              : test_pass_rate.final_pass_rate_pct >= 90
              ? "warning"
              : "critical"
          }
          statusLabel="Target ≥ 95%"
          icon={<CheckCircle2 className="w-4 h-4" />}
        />

        {/* 4. Flakiness Index */}
        <KpiCard
          title="Flakiness Index"
          value={`${flakiness.execution_flaky_rate_pct}%`}
          subtitle={`${flakiness.flaky_executions_count} flaky runs • ${flakiness.quarantine_candidates_count} in quarantine`}
          sampleInfo={`n=${test_pass_rate.total_executed_tests}`}
          status={
            flakiness.quarantine_candidates_count === 0
              ? "healthy"
              : "warning"
          }
          statusLabel={
            flakiness.quarantine_candidates_count > 0
              ? `${flakiness.quarantine_candidates_count} Quarantine`
              : "Stable"
          }
          icon={<Flame className="w-4 h-4" />}
        />

        {/* 5. Production Escape Rate */}
        <KpiCard
          title="Production Escape Rate"
          value={`${escape_rate.rate_pct}%`}
          subtitle={`${escape_rate.escaped_count} escaped to Production`}
          sampleInfo={`n=${escape_rate.total_defects}`}
          status={
            escape_rate.rate_pct <= 5
              ? "healthy"
              : escape_rate.rate_pct <= 10
              ? "warning"
              : "critical"
          }
          statusLabel="Target ≤ 5.0%"
          icon={<AlertTriangle className="w-4 h-4" />}
        />

        {/* 6. Active Open Backlog */}
        <KpiCard
          title="Active Open Defects"
          value={open_defects.total_open}
          subtitle="Unresolved issues currently in backlog"
          sampleInfo={`window=${data.window_days}d`}
          status={open_defects.total_open <= 10 ? "neutral" : "warning"}
          statusLabel="Backlog"
          icon={<Bug className="w-4 h-4" />}
        />
      </div>
    </section>
  );
}