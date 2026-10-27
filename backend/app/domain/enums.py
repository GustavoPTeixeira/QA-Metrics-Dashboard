from enum import Enum

class Severity(str, Enum):
    CRITICAL  = "Critical"
    HIGH  = "High"
    MEDIUM = "Medium"
    LOW = "Low"

    @property
    def weight(self)->int:
        return {Severity.CRITICAL: 4, Severity.HIGH: 3, Severity.MEDIUM: 2, Severity.LOW: 1}[self]

class IssueStatus(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"

    @property
    def issue_status(self)->int:
        return {IssueStatus.OPEN: 1, IssueStatus.IN_PROGRESS: 2, IssueStatus.RESOLVED: 3, IssueStatus.CLOSED: 4}[self]

class FoundIn(str, Enum):
    PR = "Pre-Release"
    PROD = "Production"

    @property
    def found_in(self)->int:
        return {FoundIn.PR: 1, FoundIn.PROD: 2}[self]

class TestStatus(str, Enum):
    __test__ = False

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"

