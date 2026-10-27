# Contributing to QA Metrics Dashboard

Thank you for your interest in contributing to **QA Metrics Dashboard** (`QA-GOV-2026-v1.0`)!

## Architecture Overview

- **`backend/`**: Python 3.11+ / FastAPI / SQLAlchemy 2.0 / Alembic.
  - `app/domain/`: Canonical enums (`Severity`, `IssueStatus`, `FoundIn`, `TestStatus`) and Pydantic schemas.
  - `app/db/`: Relational models (`Module`, `Issue`, `IssueTransition`, `TestRun`, `TestCase`, `TestAttempt`, `ScenarioAlias`).
  - `app/metrics/`: Pure statistical functions tested via TDD against the deterministic Golden Dataset.
  - `app/integrations/`: Adapters for GitHub Issues, Jira Cloud, Azure DevOps Boards, and Slack Block Kit alerts.
  - `app/api/`: FastAPI routers (`/api/metrics`, `/api/ingest`, `/api/webhooks`).
- **`frontend/`**: Next.js (App Router) + React + TypeScript + Tailwind CSS + Lucide Icons.

## Development Workflow

1. Create a feature branch from `main` (`git checkout -b feat/your-feature`).
2. Write or update tests in `backend/tests/` following TDD.
3. Run the backend test suite and ensure 100% pass rate:
   ```powershell
   cd backend
   .venv\Scripts\pytest -v
   ```
4. Open a Pull Request against `main`.