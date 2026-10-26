import pytest
from app.domain.enums import Severity, IssueStatus, FoundIn, TestStatus

def test_value_lookup():
    assert Severity("High") is Severity.HIGH

def test_invalid_value_raises():
    with pytest.raises(ValueError):
        Severity("tst")

@pytest.mark.parametrize(
    "severity, expected",
    [
        (Severity.CRITICAL, "Critical"),
        (Severity.LOW, "Low"),
    ],
)
def test_severity_codes(severity, expected):
    assert severity == expected

@pytest.mark.parametrize(
    "issue_status, expected",
    [
        (IssueStatus.OPEN, "Open"),
        (IssueStatus.CLOSED, "Closed"),
    ],
)
def test_issue_status_codes(issue_status, expected):
    assert issue_status == expected

@pytest.mark.parametrize(
    "found_in, expected",
    [
        (FoundIn.PR, "Pre-Release"),
        (FoundIn.PROD, "Production"),
    ],
)
def test_found_in_codes(found_in, expected):
    assert found_in == expected

@pytest.mark.parametrize(
    "severity, expected",
    [
        (Severity.CRITICAL, 4),
        (Severity.HIGH, 3),
        (Severity.MEDIUM, 2),
        (Severity.LOW, 1)
    ],
)
def test_severity_weight(severity, expected):
    assert severity.weight == expected

@pytest.mark.parametrize(
    "status, expected",
    [
        (TestStatus.PASSED, "passed"),
        (TestStatus.FAILED, "failed"),
        (TestStatus.SKIPPED, "skipped"),
    ],
)
def test_test_status_values(status, expected):
    assert status.value == expected