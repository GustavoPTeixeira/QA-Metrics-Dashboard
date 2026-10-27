---
name: "🐛 Bug / Fix"
about: "Track a bug, regression, or technical fix"
title: "fix(scope): "
labels: ["bug", "severity:medium", "env:pre-release"]
---

## 🚨 What is Broken?
<!-- Brief description of the bug, error message, or unexpected behavior -->


## 🔍 Root Cause / Where in Code
- **File(s):** ``
- **Endpoint / Component:** ``

```text
# Paste traceback, console error, or failing test output here (if applicable)
```

## 🏷️ Dashboard Telemetry Tags
<!-- Tip: Adding these GitHub labels lets QA Metrics Dashboard classify this issue when syncing this repo! -->
- **Severity Label:** `severity:critical` | `severity:high` | `severity:medium` | `severity:low`
- **Module Label:** `module:Metrics` | `module:API` | `module:Frontend` | `module:Integrations`
- **Environment Label:** `env:production` | `env:pre-release`

## 🛠️ Fix & Regression Checklist
- [ ] Reproduce the issue or write a failing test in `backend/tests/`
- [ ] Apply fix
- [ ] All backend tests passing (`pytest -v`)
- [ ] Verified end-to-end in local stack (`uvicorn` + `next dev`)

