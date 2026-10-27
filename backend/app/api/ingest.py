import os
from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import (
    Issue,
    IssueTransition,
    Module,
    TestAttempt,
    TestCase,
    TestRun,
    compute_scenario_id,
    utcnow,
)
from app.domain.enums import IssueStatus, TestStatus
from app.domain.schemas import IssueIngestPayload, TestRunIngestPayload

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

API_KEY_ENV = os.getenv("INGEST_API_KEY", "qa-secret-token")


def verify_api_key(
    x_api_key: str = Header(..., description="API Key de autenticação da ingestão")
) -> str:
    if x_api_key != API_KEY_ENV:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    return x_api_key


@router.post("/test-run", status_code=status.HTTP_201_CREATED)
def ingest_test_run(
    payload: TestRunIngestPayload,
    response: Response,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    existing_run = (
        db.query(TestRun)
        .filter(
            TestRun.suite_name == payload.suite_name,
            TestRun.git_commit_sha == payload.git_commit_sha,
            TestRun.executed_at == payload.executed_at,
        )
        .first()
    )

    if existing_run:
        response.status_code = status.HTTP_200_OK
        return {
            "status": "already_ingested",
            "test_run_id": existing_run.id,
            "message": "Test run execution already processed.",
        }

    passed_count = sum(
        1 for tc in payload.test_cases if tc.status == TestStatus.PASSED
    )
    failed_count = sum(
        1 for tc in payload.test_cases if tc.status == TestStatus.FAILED
    )
    skipped_count = sum(
        1 for tc in payload.test_cases if tc.status == TestStatus.SKIPPED
    )
    total_duration_ms = sum(tc.duration_ms for tc in payload.test_cases)

    test_run = TestRun(
        suite_name=payload.suite_name,
        git_commit_sha=payload.git_commit_sha,
        environment=payload.environment,
        total_count=len(payload.test_cases),
        passed_count=passed_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        duration_ms=total_duration_ms,
        executed_at=payload.executed_at,
    )
    db.add(test_run)
    db.flush()

    modules_cache: dict[str, Module] = {
        m.name: m for m in db.query(Module).all()
    }

    for tc in payload.test_cases:
        module = modules_cache.get(tc.module_name)
        if not module:
            module = Module(name=tc.module_name, owner_team="Core Squad")
            db.add(module)
            db.flush()
            modules_cache[tc.module_name] = module

        scenario_id = compute_scenario_id(
            suite_name=payload.suite_name,
            class_or_feature=tc.class_or_feature,
            scenario_title=tc.scenario_title,
        )

        retry_count = max(0, len(tc.attempts) - 1)
        has_failed_attempt = any(
            a.status == TestStatus.FAILED for a in tc.attempts
        )
        is_flaky = (tc.status == TestStatus.PASSED and has_failed_attempt) or (
            tc.status == TestStatus.PASSED and retry_count > 0
        )

        test_case = TestCase(
            test_run_id=test_run.id,
            scenario_id=scenario_id,
            scenario_title=tc.scenario_title,
            module_id=module.id,
            status=tc.status,
            duration_ms=tc.duration_ms,
            error_message=tc.error_message,
            stack_trace=tc.stack_trace,
            is_flaky=is_flaky,
            retry_count=retry_count,
        )
        db.add(test_case)
        db.flush()

        for att in tc.attempts:
            attempt = TestAttempt(
                test_case_id=test_case.id,
                attempt_no=att.attempt_no,
                status=att.status,
                duration_ms=att.duration_ms,
                error_message=att.error_message,
            )
            db.add(attempt)

    db.commit()

    return {
        "status": "ingested",
        "test_run_id": test_run.id,
        "total_cases": len(payload.test_cases),
    }


@router.post("/issue", status_code=status.HTTP_201_CREATED)
def ingest_issue(
    payload: IssueIngestPayload,
    response: Response = Response(),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    module = (
        db.query(Module).filter(Module.name == payload.module_name).first()
    )
    if not module:
        module = Module(name=payload.module_name, owner_team="Core Squad")
        db.add(module)
        db.flush()

    issue = (
        db.query(Issue)
        .filter(Issue.external_key == payload.external_key)
        .first()
    )

    now = utcnow()
    if issue:
        old_status = issue.status
        issue.title = payload.title
        issue.severity = payload.severity
        issue.status = payload.status
        issue.found_in = payload.found_in
        issue.release_version = payload.release_version
        issue.linked_commit_sha = payload.linked_commit_sha

        if payload.status == IssueStatus.RESOLVED and not issue.resolved_at:
            issue.resolved_at = payload.resolved_at or now
        if payload.status == IssueStatus.CLOSED and not issue.closed_at:
            issue.closed_at = payload.closed_at or now

        if old_status != payload.status:
            transition = IssueTransition(
                issue_id=issue.id,
                from_status=old_status,
                to_status=payload.status,
                transitioned_at=now,
                actor=payload.actor,
            )
            db.add(transition)

        db.commit()
        response.status_code = status.HTTP_200_OK
        return {"status": "updated", "issue_id": issue.id}

    issue = Issue(
        external_key=payload.external_key,
        title=payload.title,
        severity=payload.severity,
        status=payload.status,
        found_in=payload.found_in,
        module_id=module.id,
        release_version=payload.release_version,
        linked_commit_sha=payload.linked_commit_sha,
        created_at=payload.created_at or now,
        resolved_at=payload.resolved_at,
        closed_at=payload.closed_at,
    )
    db.add(issue)
    db.flush()

    transition = IssueTransition(
        issue_id=issue.id,
        from_status=None,
        to_status=payload.status,
        transitioned_at=payload.created_at or now,
        actor=payload.actor,
    )
    db.add(transition)
    db.commit()

    return {"status": "created", "issue_id": issue.id}