from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
import app.db.models
from app.db.models import Issue, IssueTransition, TestCase, TestRun
from app.domain.enums import IssueStatus, Severity, TestStatus
from app.main import app

API_HEADERS = {"X-API-Key": "qa-secret-token"}


@pytest.fixture
def ingest_client():
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


def test_ingest_test_run_success(ingest_client):
    payload = {
        "suite_name": "E2E Checkout Suite",
        "git_commit_sha": "a1b2c3d4e5f6789012345678901234567890abcd",
        "environment": "staging",
        "executed_at": "2026-10-27T10:00:00Z",
        "test_cases": [
            {
                "scenario_title": "Login com credenciais válidas",
                "class_or_feature": "auth.feature",
                "module_name": "Auth",
                "status": "passed",
                "duration_ms": 1200,
                "attempts": [
                    {"attempt_no": 1, "status": "passed", "duration_ms": 1200}
                ],
            },
            {
                "scenario_title": "Checkout via PIX com instabilidade",
                "class_or_feature": "checkout.feature",
                "module_name": "Checkout",
                "status": "passed",
                "duration_ms": 4500,
                "attempts": [
                    {
                        "attempt_no": 1,
                        "status": "failed",
                        "duration_ms": 2000,
                        "error_message": "Gateway timeout",
                    },
                    {"attempt_no": 2, "status": "passed", "duration_ms": 2500},
                ],
            },
        ],
    }

    response = ingest_client.post("/api/ingest/test-run", json=payload, headers=API_HEADERS)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "ingested"
    assert "test_run_id" in data

    with ingest_client.session_factory() as session:
        run = session.query(TestRun).first()
        assert run is not None
        assert run.total_count == 2
        assert run.passed_count == 2
        assert run.failed_count == 0

        flaky_case = (
            session.query(TestCase)
            .filter(TestCase.scenario_title == "Checkout via PIX com instabilidade")
            .first()
        )
        assert flaky_case is not None
        assert flaky_case.is_flaky is True
        assert flaky_case.retry_count == 1


def test_ingest_test_run_idempotency(ingest_client):
    payload = {
        "suite_name": "Regression Suite",
        "git_commit_sha": "1234567890abcdef1234567890abcdef12345678",
        "environment": "ci",
        "executed_at": "2026-10-27T12:00:00Z",
        "test_cases": [
            {
                "scenario_title": "Busca simples de produto",
                "class_or_feature": "search.feature",
                "module_name": "Search",
                "status": "passed",
                "duration_ms": 800,
                "attempts": [
                    {"attempt_no": 1, "status": "passed", "duration_ms": 800}
                ],
            }
        ],
    }

    # Primeira ingestão: 201 Created
    res1 = ingest_client.post("/api/ingest/test-run", json=payload, headers=API_HEADERS)
    assert res1.status_code == 201
    run_id1 = res1.json()["test_run_id"]

    # Segunda ingestão idêntica (retry do CI): 200 OK sem duplicar
    res2 = ingest_client.post("/api/ingest/test-run", json=payload, headers=API_HEADERS)
    assert res2.status_code == 200
    assert res2.json()["status"] == "already_ingested"
    assert res2.json()["test_run_id"] == run_id1

    with ingest_client.session_factory() as session:
        runs_count = session.query(TestRun).count()
        assert runs_count == 1


def test_ingest_issue_lifecycle(ingest_client):
    issue_payload = {
        "external_key": "QA-101",
        "title": "Erro 500 no checkout ao aplicar cupom expirado",
        "severity": "High",
        "status": "Open",
        "found_in": "Production",
        "module_name": "Checkout",
        "actor": "qa.engineer@company.com",
    }

    # Criação do defeito
    res1 = ingest_client.post("/api/ingest/issue", json=issue_payload, headers=API_HEADERS)
    assert res1.status_code == 201
    assert res1.json()["status"] == "created"

    # Atualização de status (resolução)
    issue_payload["status"] = "Resolved"
    res2 = ingest_client.post("/api/ingest/issue", json=issue_payload, headers=API_HEADERS)
    assert res2.status_code == 200
    assert res2.json()["status"] == "updated"

    with ingest_client.session_factory() as session:
        issue = session.query(Issue).filter(Issue.external_key == "QA-101").first()
        assert issue is not None
        assert issue.status == IssueStatus.RESOLVED

        transitions = (
            session.query(IssueTransition)
            .filter(IssueTransition.issue_id == issue.id)
            .order_by(IssueTransition.transitioned_at.asc())
            .all()
        )
        assert len(transitions) == 2
        assert transitions[0].from_status is None
        assert transitions[0].to_status == IssueStatus.OPEN
        assert transitions[1].from_status == IssueStatus.OPEN
        assert transitions[1].to_status == IssueStatus.RESOLVED


def test_ingest_unauthorized(ingest_client):
    res = ingest_client.post("/api/ingest/test-run", json={}, headers={"X-API-Key": "wrong-key"})
    assert res.status_code == 401

