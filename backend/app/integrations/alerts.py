from dataclasses import dataclass
import os
from typing import Any
import httpx
from sqlalchemy.orm import Session

from app.domain.enums import FoundIn, IssueStatus, Severity
from app.domain.schemas import IssueIngestPayload
from app.metrics.defects import calculate_mttr_and_sla
from app.metrics.tests import get_quarantine_recommendations


@dataclass(frozen=True)
class AlertMessage:
    alert_type: str
    severity: str
    title: str
    summary: str
    channel: str
    slack_payload: dict[str, Any]


def _build_slack_block_payload(
    title: str, summary: str, severity: str, channel: str
) -> dict[str, Any]:
    """Formats an alert into a standard Slack Incoming Webhook Block Kit payload."""
    emoji = "🚨" if severity == "CRITICAL" else "⚠️"
    return {
        "channel": channel,
        "text": f"{emoji} {title}: {summary}",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {title}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": summary,
                },
            },
        ],
    }


def evaluate_issue_instant_alert(
    issue: IssueIngestPayload,
) -> AlertMessage | None:
    """
    Evaluates an incoming defect immediately upon webhook ingestion.
    Triggers a CRITICAL alert if a Sev1 (Critical) bug escaped to Production.
    """
    if (
        issue.severity == Severity.CRITICAL
        and issue.found_in == FoundIn.PROD
        and issue.status == IssueStatus.OPEN
    ):
        title = f"P1 Production Defect Escaped: [{issue.external_key}]"
        summary = (
            f"*Title:* {issue.title}\n"
            f"*Module:* `{issue.module_name}` | *Severity:* `{issue.severity.value}`\n"
            f"*Reported by:* {issue.actor} | *SLA Target:* ≤ 4.0h"
        )
        channel = "#qa-incidents-critical"
        return AlertMessage(
            alert_type="PRODUCTION_CRITICAL_DEFECT",
            severity="CRITICAL",
            title=title,
            summary=summary,
            channel=channel,
            slack_payload=_build_slack_block_payload(
                title, summary, "CRITICAL", channel
            ),
        )
    return None


def evaluate_governance_alerts(
    session: Session, window_days: int = 60
) -> list[AlertMessage]:
    """
    Scans the database for SLA breaches and Flaky Test Quarantine candidates
    and returns structured alert notifications for Slack/Email.
    """
    alerts: list[AlertMessage] = []

    
    mttr = calculate_mttr_and_sla(session, window_days=window_days)
    sev1_breaches = mttr.sla_breaches.get(Severity.CRITICAL, 0)
    sev2_breaches = mttr.sla_breaches.get(Severity.HIGH, 0)

    if sev1_breaches > 0 or sev2_breaches > 0:
        severity = "CRITICAL" if sev1_breaches > 0 else "WARNING"
        title = "Defect Resolution SLA Breach Detected"
        summary = (
            f"*Window:* Last {window_days} days\n"
            f"• *Sev1 (Critical ≤4h):* {sev1_breaches} breaches (Avg MTTR: {mttr.mttr_first_resolution_hours.get(Severity.CRITICAL, 0.0)}h)\n"
            f"• *Sev2 (High ≤24h):* {sev2_breaches} breaches (Avg MTTR: {mttr.mttr_first_resolution_hours.get(Severity.HIGH, 0.0)}h)"
        )
        channel = "#qa-sla-governance"
        alerts.append(
            AlertMessage(
                alert_type="SLA_BREACH",
                severity=severity,
                title=title,
                summary=summary,
                channel=channel,
                slack_payload=_build_slack_block_payload(
                    title, summary, severity, channel
                ),
            )
        )


    quarantine_list = get_quarantine_recommendations(
        session, window_days=window_days
    )
    for q in quarantine_list:
        title = f"Flaky Test Quarantine Required: {q.scenario_title}"
        summary = (
            f"*Module:* `{q.module_name}` | *Owner Squad:* *{q.owner_team}*\n"
            f"*Flakiness Rate:* `{q.flakiness_pct}%` ({q.flaky_runs}/{q.total_runs} flaky executions)"
        )
        channel = "#ci-flakiness-alerts"
        alerts.append(
            AlertMessage(
                alert_type="FLAKY_QUARANTINE",
                severity="WARNING",
                title=title,
                summary=summary,
                channel=channel,
                slack_payload=_build_slack_block_payload(
                    title, summary, "WARNING", channel
                ),
            )
        )

    return alerts


def dispatch_slack_alert(
    alert: AlertMessage, webhook_url: str | None = None
) -> bool:
    """
    Sends the Slack Block Kit payload to a configured SLACK_WEBHOOK_URL.
    Returns True if sent over HTTP, or False if running in local dry-run mode.
    """
    target_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
    if not target_url:
        return False

    try:
        response = httpx.post(
            target_url, json=alert.slack_payload, timeout=5.0
        )
        return response.is_success
    except httpx.HTTPError:
        return False