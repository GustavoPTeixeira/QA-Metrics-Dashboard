from typing import Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.ingest import ingest_issue, verify_api_key
from app.integrations.alerts import (
    dispatch_slack_alert,
    evaluate_governance_alerts,
    evaluate_issue_instant_alert,
)
from app.integrations.connectors import (
    parse_github_issue_webhook,
    parse_jira_issue_webhook,
)

router = APIRouter(prefix="/webhooks", tags=["Webhooks & Alerts"])


@router.post("/github", status_code=status.HTTP_200_OK)
def handle_github_webhook(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """
    Receives a native GitHub Issues webhook payload, normalizes it,
    persists the issue/transition, and triggers instant P1 alerts if applicable.
    """
    normalized = parse_github_issue_webhook(payload)
    result = ingest_issue(payload=normalized, db=db, _=api_key)

    alert = evaluate_issue_instant_alert(normalized)
    alert_dispatched = False
    if alert:
        alert_dispatched = dispatch_slack_alert(alert)

    return {
        **result,
        "external_key": normalized.external_key,
        "alert_triggered": alert is not None,
        "alert_type": alert.alert_type if alert else None,
        "alert_dispatched": alert_dispatched,
    }


@router.post("/jira", status_code=status.HTTP_200_OK)
def handle_jira_webhook(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """
    Receives a native Jira Issue webhook payload, normalizes it,
    persists the issue/transition, and triggers instant P1 alerts if applicable.
    """
    normalized = parse_jira_issue_webhook(payload)
    result = ingest_issue(payload=normalized, db=db, _=api_key)

    alert = evaluate_issue_instant_alert(normalized)
    alert_dispatched = False
    if alert:
        alert_dispatched = dispatch_slack_alert(alert)

    return {
        **result,
        "external_key": normalized.external_key,
        "alert_triggered": alert is not None,
        "alert_type": alert.alert_type if alert else None,
        "alert_dispatched": alert_dispatched,
    }


@router.post("/alerts/evaluate", status_code=status.HTTP_200_OK)
def trigger_governance_alerts(
    window_days: int = Query(60, description="Historical window in days"),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """
    Evaluates SLA breaches and Flaky Test Quarantine thresholds across the database
    and generates Slack Block Kit notifications.
    """
    alerts = evaluate_governance_alerts(db, window_days=window_days)
    results = []
    for a in alerts:
        dispatched = dispatch_slack_alert(a)
        results.append(
            {
                "alert_type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "channel": a.channel,
                "dispatched": dispatched,
                "slack_payload": a.slack_payload,
            }
        )

    return {
        "window_days": window_days,
        "alerts_count": len(results),
        "alerts": results,
    }