import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
import app.db.models
from app.db.models import Issue, IssueTransition
from app.domain.enums import FoundIn, IssueStatus, Severity
from app.main import app
from app.seeds.generator import seed_database

API_HEADERS = {"X-API-Key": "qa-secret-token"}


@pytest.fixture
def integration_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        client.session_factory = TestingSessionLocal
        yield client
    app.dependency_overrides.clear()


def test_github_webhook_creates_issue_and_triggers_p1_alert(integration_client):
    github_payload = {
        "action": "opened",
        "repository": {"name": "checkout-service"},
        "sender": {"login": "alice-dev"},
        "issue": {
            "number": 42,
            "title": "Payment gateway crashes on 3DS verification",
            "state": "open",
            "labels": [
                {"name": "severity:critical"},
                {"name": "env:production"},
                {"name": "module:Checkout"},
            ],
        },
    }

    res = integration_client.post(
        "/api/webhooks/github", json=github_payload, headers=API_HEADERS
    )
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "created"
    assert data["external_key"] == "GH-checkout-service-42"
    assert data["alert_triggered"] is True
    assert data["alert_type"] == "PRODUCTION_CRITICAL_DEFECT"

    with integration_client.session_factory() as session:
        issue = (
            session.query(Issue)
            .filter(Issue.external_key == "GH-checkout-service-42")
            .first()
        )
        assert issue is not None
        assert issue.severity == Severity.CRITICAL
        assert issue.found_in == FoundIn.PROD
        assert issue.status == IssueStatus.OPEN


def test_jira_webhook_lifecycle_and_transitions(integration_client):
    jira_open_payload = {
        "webhookEvent": "jira:issue_created",
        "user": {"displayName": "Bob QA"},
        "issue": {
            "key": "BILL-777",
            "fields": {
                "summary": "Invoice PDF rounding discrepancy",
                "priority": {"name": "High"},
                "status": {"name": "Open"},
                "components": [{"name": "Billing"}],
                "labels": ["pre-release"],
            },
        },
    }

    # 1. Create via Jira webhook
    res1 = integration_client.post(
        "/api/webhooks/jira", json=jira_open_payload, headers=API_HEADERS
    )
    assert res1.status_code == 200
    assert res1.json()["status"] == "created"
    assert res1.json()["alert_triggered"] is False

    # 2. Resolve via Jira webhook
    jira_open_payload["issue"]["fields"]["status"]["name"] = "Done"
    res2 = integration_client.post(
        "/api/webhooks/jira", json=jira_open_payload, headers=API_HEADERS
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "updated"

    with integration_client.session_factory() as session:
        issue = (
            session.query(Issue).filter(Issue.external_key == "BILL-777").first()
        )
        assert issue is not None
        assert issue.status == IssueStatus.RESOLVED

        transitions = (
            session.query(IssueTransition)
            .filter(IssueTransition.issue_id == issue.id)
            .all()
        )
        assert len(transitions) == 2


def test_evaluate_governance_alerts_on_golden_dataset(integration_client):
    with integration_client.session_factory() as session:
        seed_database(session, seed=42)

    res = integration_client.post(
        "/api/webhooks/alerts/evaluate?window_days=60", headers=API_HEADERS
    )
    assert res.status_code == 200
    data = res.json()

    # Golden Dataset has 1 SLA_BREACH alert + 1 FLAKY_QUARANTINE alert
    assert data["alerts_count"] == 2
    alert_types = {a["alert_type"] for a in data["alerts"]}
    assert alert_types == {"SLA_BREACH", "FLAKY_QUARANTINE"}

    for alert in data["alerts"]:
        assert "blocks" in alert["slack_payload"]
        assert alert["channel"].startswith("#")

def test_azure_devops_webhook_and_issues_board_list(integration_client):
    ado_payload = {
        "eventType": "workitem.created",
        "resource": {
            "id": 904,
            "fields": {
                "System.Title": "Timeout on Azure SQL connection pool",
                "System.State": "Active",
                "Microsoft.VSTS.Common.Severity": "1 - Critical",
                "System.AreaPath": "Platform\\Auth",
                "System.Tags": "production; security",
                "System.CreatedBy": {"displayName": "Carlos SRE"},
            },
        },
    }

    res = integration_client.post(
        "/api/webhooks/azure-devops", json=ado_payload, headers=API_HEADERS
    )
    assert res.status_code == 200
    data = res.json()
    assert data["external_key"] == "ADO-904"
    assert data["status"] == "created"

    board_res = integration_client.get("/api/metrics/issues")
    assert board_res.status_code == 200
    items = board_res.json()
    assert len(items) == 1
    assert items[0]["external_key"] == "ADO-904"
    assert items[0]["provider"] == "Azure DevOps"
    assert items[0]["module_name"] == "Auth"