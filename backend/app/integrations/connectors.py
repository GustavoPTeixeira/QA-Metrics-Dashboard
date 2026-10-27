from datetime import datetime, timezone
from typing import Any

from app.domain.enums import FoundIn, IssueStatus, Severity
from app.domain.schemas import IssueIngestPayload


def parse_github_issue_webhook(payload: dict[str, Any]) -> IssueIngestPayload:
    """
    Adapter that normalizes a native GitHub Issues webhook payload
    into our internal IssueIngestPayload contract.
    """
    action = payload.get("action", "opened")
    issue_data = payload.get("issue", {})
    repo_name = payload.get("repository", {}).get("name", "repo")
    sender = payload.get("sender", {}).get("login", "github-webhook")

    number = issue_data.get("number", 0)
    external_key = f"GH-{repo_name}-{number}"
    title = issue_data.get("title", "Untitled GitHub Issue")

    # Extract labels (e.g. "severity:critical", "module:Checkout", "env:prod")
    raw_labels = issue_data.get("labels", [])
    labels = [
        lbl.get("name", "").lower() if isinstance(lbl, dict) else str(lbl).lower()
        for lbl in raw_labels
    ]

    # 1. Map Severity from labels
    severity = Severity.MEDIUM
    if any("critical" in l or "sev1" in l for l in labels):
        severity = Severity.CRITICAL
    elif any("high" in l or "sev2" in l for l in labels):
        severity = Severity.HIGH
    elif any("low" in l or "sev4" in l for l in labels):
        severity = Severity.LOW

    # 2. Map Environment (FoundIn) from labels
    found_in = (
        FoundIn.PROD
        if any("prod" in l or "production" in l for l in labels)
        else FoundIn.PR
    )

    # 3. Map Module from "module:<Name>" label
    module_name = "Core"
    for raw_lbl in raw_labels:
        lbl_str = raw_lbl.get("name", "") if isinstance(raw_lbl, dict) else str(raw_lbl)
        if lbl_str.lower().startswith("module:"):
            module_name = lbl_str.split(":", 1)[1].strip()
            break

    # 4. Map Status from GitHub action & state
    state = issue_data.get("state", "open").lower()
    if action == "reopened":
        status = IssueStatus.OPEN
    elif action == "closed" or state == "closed":
        status = IssueStatus.RESOLVED
    elif any("in-progress" in l or "wip" in l for l in labels):
        status = IssueStatus.IN_PROGRESS
    else:
        status = IssueStatus.OPEN

    return IssueIngestPayload(
        external_key=external_key,
        title=title,
        severity=severity,
        status=status,
        found_in=found_in,
        module_name=module_name,
        actor=sender,
        created_at=datetime.now(timezone.utc),
    )


def parse_jira_issue_webhook(payload: dict[str, Any]) -> IssueIngestPayload:
    """
    Adapter that normalizes a native Jira Issue webhook payload
    into our internal IssueIngestPayload contract.
    """
    issue_data = payload.get("issue", {})
    fields = issue_data.get("fields", {})
    user_data = payload.get("user", {})

    external_key = issue_data.get("key", "JIRA-UNKNOWN")
    title = fields.get("summary", "Untitled Jira Issue")
    actor = user_data.get("displayName") or user_data.get("name") or "jira-webhook"

    priority_name = (fields.get("priority") or {}).get("name", "").lower()
    PriorityMap = {
        "highest": Severity.CRITICAL,
        "blocker": Severity.CRITICAL,
        "critical": Severity.CRITICAL,
        "high": Severity.HIGH,
        "medium": Severity.MEDIUM,
        "low": Severity.LOW,
        "lowest": Severity.LOW,
    }
    severity = PriorityMap.get(priority_name, Severity.MEDIUM)


    status_name = (fields.get("status") or {}).get("name", "").lower()
    if status_name in ("resolved", "done", "fixed"):
        status = IssueStatus.RESOLVED
    elif status_name in ("closed",):
        status = IssueStatus.CLOSED
    elif status_name in ("in progress", "in review"):
        status = IssueStatus.IN_PROGRESS
    else:
        status = IssueStatus.OPEN


    components = fields.get("components") or []
    module_name = (
        components[0].get("name", "Core")
        if components and isinstance(components[0], dict)
        else "Core"
    )

    labels = [str(l).lower() for l in (fields.get("labels") or [])]
    found_in = (
        FoundIn.PROD
        if any("prod" in l or "escaped" in l for l in labels)
        else FoundIn.PR
    )

    return IssueIngestPayload(
        external_key=external_key,
        title=title,
        severity=severity,
        status=status,
        found_in=found_in,
        module_name=module_name,
        actor=actor,
        created_at=datetime.now(timezone.utc),
    )