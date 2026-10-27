from typing import Any
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.ingest import ingest_issue, verify_api_key
from app.domain.schemas import IssueIngestPayload
from app.integrations.alerts import (
    dispatch_slack_alert,
    evaluate_governance_alerts,
    evaluate_issue_instant_alert,
)
from app.integrations.connectors import (
    fetch_azure_devops_board_issues,
    fetch_github_repo_issues,
    fetch_jira_board_issues,
    parse_azure_devops_webhook,
    parse_github_issue_webhook,
    parse_jira_issue_webhook,
)

router = APIRouter(prefix="/webhooks", tags=["Webhooks & Alerts"])


class JiraSyncRequest(BaseModel):
    base_url: str
    email: str
    api_token: str
    project_key: str
    jql: str | None = None
    max_results: int = 50


class GitHubSyncRequest(BaseModel):
    repo_full_name: str
    token: str | None = None
    max_results: int = 50


class AzureDevOpsSyncRequest(BaseModel):
    org_url: str
    project: str
    pat: str
    max_results: int = 50


def _process_normalized_issue(
    normalized: IssueIngestPayload, db: Session, api_key: str
) -> dict[str, Any]:
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


@router.post("/github", status_code=status.HTTP_200_OK)
def handle_github_webhook(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> dict[str, Any]:
    normalized = parse_github_issue_webhook(payload)
    return _process_normalized_issue(normalized, db, api_key)


@router.post("/jira", status_code=status.HTTP_200_OK)
def handle_jira_webhook(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> dict[str, Any]:
    normalized = parse_jira_issue_webhook(payload)
    return _process_normalized_issue(normalized, db, api_key)


@router.post("/azure-devops", status_code=status.HTTP_200_OK)
def handle_azure_devops_webhook(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> dict[str, Any]:
    normalized = parse_azure_devops_webhook(payload)
    return _process_normalized_issue(normalized, db, api_key)


@router.post("/sync/jira", status_code=status.HTTP_200_OK)
def sync_jira_board(
    req: JiraSyncRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        issues = fetch_jira_board_issues(
            base_url=req.base_url,
            email=req.email,
            api_token=req.api_token,
            project_key=req.project_key,
            jql=req.jql,
            max_results=req.max_results,
        )
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Jira API sync failed: {exc}",
        ) from exc

    created_count = 0
    updated_count = 0
    for item in issues:
        res = _process_normalized_issue(item, db, api_key)
        if res["status"] == "created":
            created_count += 1
        else:
            updated_count += 1

    return {
        "provider": "jira",
        "project_key": req.project_key,
        "synced_total": len(issues),
        "created": created_count,
        "updated": updated_count,
    }


@router.post("/sync/github", status_code=status.HTTP_200_OK)
def sync_github_board(
    req: GitHubSyncRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        issues = fetch_github_repo_issues(
            repo_full_name=req.repo_full_name,
            token=req.token,
            max_results=req.max_results,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GitHub API sync failed: {exc}",
        ) from exc

    created_count = 0
    updated_count = 0
    for item in issues:
        res = _process_normalized_issue(item, db, api_key)
        if res["status"] == "created":
            created_count += 1
        else:
            updated_count += 1

    return {
        "provider": "github",
        "repo": req.repo_full_name,
        "synced_total": len(issues),
        "created": created_count,
        "updated": updated_count,
    }


@router.post("/sync/azure-devops", status_code=status.HTTP_200_OK)
def sync_azure_devops_board(
    req: AzureDevOpsSyncRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> dict[str, Any]:
    try:
        issues = fetch_azure_devops_board_issues(
            org_url=req.org_url,
            project=req.project,
            pat=req.pat,
            max_results=req.max_results,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Azure DevOps API sync failed: {exc}",
        ) from exc

    created_count = 0
    updated_count = 0
    for item in issues:
        res = _process_normalized_issue(item, db, api_key)
        if res["status"] == "created":
            created_count += 1
        else:
            updated_count += 1

    return {
        "provider": "azure-devops",
        "project": req.project,
        "synced_total": len(issues),
        "created": created_count,
        "updated": updated_count,
    }


@router.post("/alerts/evaluate", status_code=status.HTTP_200_OK)
def trigger_governance_alerts(
    window_days: int = Query(60, description="Historical window in days"),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
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