from datetime import datetime, timezone
from typing import Any
import httpx

from app.domain.enums import FoundIn, IssueStatus, Severity
from app.domain.schemas import IssueIngestPayload
from urllib.parse import urlparse

def _parse_iso_datetime(val: Any) -> datetime | None:
    if not val or not isinstance(val, str):
        return None
    try:
        normalized = val.replace("Z", "+00:00")
        if len(normalized) >= 5 and (normalized[-5] in ("+", "-")) and ":" not in normalized[-5:]:
            normalized = normalized[:-2] + ":" + normalized[-2:]
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def parse_github_issue_webhook(payload: dict[str, Any]) -> IssueIngestPayload:
    action = payload.get("action", "opened")
    issue_data = payload.get("issue", payload)
    repo_name = payload.get("repository", {}).get("name", "repo")
    sender = (
        payload.get("sender", {}).get("login")
        or (issue_data.get("user") or {}).get("login")
        or "github-webhook"
    )

    number = issue_data.get("number", 0)
    external_key = f"GH-{repo_name}-{number}"
    title = issue_data.get("title", "Untitled GitHub Issue")

    raw_labels = issue_data.get("labels", [])
    labels = [
        lbl.get("name", "").lower() if isinstance(lbl, dict) else str(lbl).lower()
        for lbl in raw_labels
    ]

    severity = Severity.MEDIUM
    if any("critical" in l or "sev1" in l for l in labels):
        severity = Severity.CRITICAL
    elif any("high" in l or "sev2" in l for l in labels):
        severity = Severity.HIGH
    elif any("low" in l or "sev4" in l for l in labels):
        severity = Severity.LOW

    found_in = (
        FoundIn.PROD
        if any("prod" in l or "production" in l for l in labels)
        else FoundIn.PR
    )

    module_name = "Core"
    for raw_lbl in raw_labels:
        lbl_str = raw_lbl.get("name", "") if isinstance(raw_lbl, dict) else str(raw_lbl)
        if lbl_str.lower().startswith("module:"):
            module_name = lbl_str.split(":", 1)[1].strip()
            break

    state = issue_data.get("state", "open").lower()
    if action == "reopened":
        status = IssueStatus.OPEN
    elif action == "closed" or state == "closed":
        status = IssueStatus.RESOLVED
    elif any("in-progress" in l or "wip" in l for l in labels):
        status = IssueStatus.IN_PROGRESS
    else:
        status = IssueStatus.OPEN

    created_at = _parse_iso_datetime(issue_data.get("created_at")) or datetime.now(timezone.utc)
    resolved_at = _parse_iso_datetime(issue_data.get("closed_at"))

    return IssueIngestPayload(
        external_key=external_key,
        title=title,
        severity=severity,
        status=status,
        found_in=found_in,
        module_name=module_name,
        actor=sender,
        created_at=created_at,
        resolved_at=resolved_at,
    )


def parse_jira_issue_webhook(payload: dict[str, Any]) -> IssueIngestPayload:
    issue_data = payload.get("issue", payload)
    fields = issue_data.get("fields", {})
    user_data = payload.get("user") or fields.get("reporter") or {}

    external_key = issue_data.get("key", "JIRA-UNKNOWN")
    title = fields.get("summary", "Untitled Jira Issue")
    actor = user_data.get("displayName") or user_data.get("name") or "jira-sync"

    priority_name = (fields.get("priority") or {}).get("name", "").lower()
    priority_map = {
        "highest": Severity.CRITICAL,
        "blocker": Severity.CRITICAL,
        "critical": Severity.CRITICAL,
        "high": Severity.HIGH,
        "medium": Severity.MEDIUM,
        "low": Severity.LOW,
        "lowest": Severity.LOW,
    }
    severity = priority_map.get(priority_name, Severity.MEDIUM)

    status_obj = fields.get("status") or {}
    status_name = status_obj.get("name", "").lower()
    status_category = (status_obj.get("statusCategory") or {}).get("key", "").lower()

    if status_name in ("resolved", "done", "fixed", "concluído", "resolvido") or status_category == "done":
        status = IssueStatus.RESOLVED
    elif status_name in ("closed", "fechado"):
        status = IssueStatus.CLOSED
    elif status_name in ("in progress", "in review", "em andamento") or status_category == "indeterminate":
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

    created_at = _parse_iso_datetime(fields.get("created")) or datetime.now(timezone.utc)
    resolved_at = _parse_iso_datetime(fields.get("resolutiondate"))

    return IssueIngestPayload(
        external_key=external_key,
        title=title,
        severity=severity,
        status=status,
        found_in=found_in,
        module_name=module_name,
        actor=actor,
        created_at=created_at,
        resolved_at=resolved_at,
    )


def parse_azure_devops_webhook(payload: dict[str, Any]) -> IssueIngestPayload:
    resource = payload.get("resource", payload)
    work_item_id = resource.get("workItemId") or resource.get("id") or 0
    fields = resource.get("fields", {})

    def _field(name: str, default: Any = "") -> Any:
        val = fields.get(name, default)
        if isinstance(val, dict) and "newValue" in val:
            return val["newValue"]
        return val

    external_key = f"ADO-{work_item_id}"
    title = str(_field("System.Title", "Untitled Azure DevOps Bug"))

    created_by = _field("System.ChangedBy") or _field("System.CreatedBy") or "ado-webhook"
    if isinstance(created_by, dict):
        actor = created_by.get("displayName", "ado-webhook")
    else:
        actor = str(created_by)

    raw_sev = str(_field("Microsoft.VSTS.Common.Severity", "3 - Medium")).lower()
    if "1" in raw_sev or "critical" in raw_sev:
        severity = Severity.CRITICAL
    elif "2" in raw_sev or "high" in raw_sev:
        severity = Severity.HIGH
    elif "4" in raw_sev or "low" in raw_sev:
        severity = Severity.LOW
    else:
        severity = Severity.MEDIUM

    raw_state = str(_field("System.State", "New")).lower()
    if raw_state in ("resolved", "done", "completed"):
        status = IssueStatus.RESOLVED
    elif raw_state in ("closed", "removed"):
        status = IssueStatus.CLOSED
    elif raw_state in ("active", "in progress", "committed"):
        status = IssueStatus.IN_PROGRESS
    else:
        status = IssueStatus.OPEN

    area_path = str(_field("System.AreaPath", "Core"))
    module_name = area_path.split("\\")[-1].strip() or "Core"

    tags = str(_field("System.Tags", "")).lower()
    found_in = (
        FoundIn.PROD
        if ("prod" in tags or "production" in tags)
        else FoundIn.PR
    )

    created_at = _parse_iso_datetime(_field("System.CreatedDate", None)) or datetime.now(timezone.utc)
    resolved_at = _parse_iso_datetime(
        _field("Microsoft.VSTS.Common.ResolvedDate", None)
        or _field("Microsoft.VSTS.Common.ClosedDate", None)
    )

    return IssueIngestPayload(
        external_key=external_key,
        title=title,
        severity=severity,
        status=status,
        found_in=found_in,
        module_name=module_name,
        actor=actor,
        created_at=created_at,
        resolved_at=resolved_at,
    )


def fetch_jira_board_issues(
    base_url: str,
    email: str,
    api_token: str,
    project_key: str,
    jql: str | None = None,
    max_results: int = 50,
) -> list[IssueIngestPayload]:
    raw_url = base_url.strip()
    if not raw_url.startswith(("http://", "https://")):
        raw_url = f"https://{raw_url}"
    parsed = urlparse(raw_url)
    clean_url = f"{parsed.scheme}://{parsed.netloc}"
    clean_key = project_key.strip().upper()
    query = jql or f'project = "{clean_key}" ORDER BY created DESC'
    params = {
        "jql": query,
        "maxResults": max_results,
        "fields": "summary,priority,status,components,labels,reporter,created,resolutiondate",
    }
    headers = {"Accept": "application/json"}
    with httpx.Client(
        auth=(email.strip(), api_token.strip()),
        headers=headers,
        follow_redirects=True,
        timeout=15.0,
    ) as client:
        res = client.get(f"{clean_url}/rest/api/3/search/jql", params=params)
        if res.status_code == 404:
            res = client.get(f"{clean_url}/rest/api/3/search", params=params)
        if not res.is_success:
            raise ValueError(
                f"Jira returned HTTP {res.status_code}: {res.text[:200]}"
            )
        try:
            data = res.json()
        except ValueError as exc:
            raise ValueError(
                f"Jira did not return valid JSON from {clean_url}. Check your Jira URL and API Token."
            ) from exc
    issues = data.get("issues", [])
    return [parse_jira_issue_webhook({"issue": raw}) for raw in issues]


def fetch_github_repo_issues(
    repo_full_name: str,
    token: str | None = None,
    max_results: int = 50,
) -> list[IssueIngestPayload]:
    repo_name = repo_full_name.split("/")[-1]
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with httpx.Client(headers=headers, timeout=15.0) as client:
        res = client.get(
            f"https://api.github.com/repos/{repo_full_name}/issues",
            params={"state": "all", "per_page": max_results},
        )
        res.raise_for_status()
        raw_items = res.json()

    results: list[IssueIngestPayload] = []
    for item in raw_items:
        if "pull_request" in item:
            continue
        results.append(
            parse_github_issue_webhook(
                {"issue": item, "repository": {"name": repo_name}}
            )
        )
    return results


def fetch_azure_devops_board_issues(
    org_url: str,
    project: str,
    pat: str,
    max_results: int = 50,
) -> list[IssueIngestPayload]:
    clean_org = org_url.rstrip("/")
    wiql_url = f"{clean_org}/{project}/_apis/wit/wiql?api-version=7.1"
    wiql_query = {
        "query": (
            f"SELECT [System.Id] FROM WorkItems "
            f"WHERE [System.TeamProject] = '{project}' "
            f"ORDER BY [System.CreatedDate] DESC"
        )
    }

    with httpx.Client(auth=("", pat), timeout=15.0) as client:
        wiql_res = client.post(wiql_url, json=wiql_query)
        wiql_res.raise_for_status()
        work_items = wiql_res.json().get("workItems", [])[:max_results]
        if not work_items:
            return []

        ids = ",".join(str(wi["id"]) for wi in work_items)
        batch_url = f"{clean_org}/{project}/_apis/wit/workitems?ids={ids}&api-version=7.1"
        batch_res = client.get(batch_url)
        batch_res.raise_for_status()
        items_data = batch_res.json().get("value", [])

    return [parse_azure_devops_webhook({"resource": item}) for item in items_data]