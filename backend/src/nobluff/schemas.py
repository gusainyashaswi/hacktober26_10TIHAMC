"""Shared, JSON-serializable contracts. Validation is not evidence of truth."""

import hashlib
import re
from pathlib import PurePosixPath
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Assessment = Literal["supported", "contradicted", "inconclusive"]
ExecutionStatus = Literal[
    "not_run", "passed", "failed", "setup_error", "timeout", "blocked"
]
Stage = Literal[
    "queued",
    "loading",
    "extracting",
    "awaiting_evidence",
    "retrieving",
    "assessing",
    "awaiting_verification",
    "verifying",
    "complete",
    "error",
]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class AnalysisRequest(Contract):
    """Transport-neutral input; the API must enforce its own repository policy."""

    repository: Text
    revision: Text
    report_text: Text
    comparison_revision: Text | None = None


class Claim(Contract):
    id: Text
    text: Text
    kind: Literal["behavior", "cause", "documentation", "fix", "other"]
    search_terms: list[Text] = Field(default_factory=list)
    reported_as: Literal["assertion", "hypothesis"] = "assertion"


class Evidence(Contract):
    id: Text
    kind: Literal["source", "documentation", "test", "execution"]
    revision: Text
    path: Text | None = None
    start_line: int | None = Field(default=None, ge=1, strict=True)
    end_line: int | None = Field(default=None, ge=1, strict=True)
    excerpt: str = Field(min_length=1)
    execution_id: Text | None = None

    @model_validator(mode="after")
    def check_location(self) -> Self:
        if self.kind == "execution":
            if self.execution_id is None:
                raise ValueError("execution evidence requires execution_id")
            if any(x is not None for x in (self.path, self.start_line, self.end_line)):
                raise ValueError("execution evidence cannot claim source coordinates")
        else:
            if self.path is None or self.start_line is None or self.end_line is None:
                raise ValueError("file evidence requires path and line range")
            path = PurePosixPath(self.path)
            if path.is_absolute() or ".." in path.parts or "\\" in self.path:
                raise ValueError("evidence path must be repository-relative POSIX")
            if self.path == "." or ":" in self.path:
                raise ValueError("evidence path must name a repository file")
            if self.end_line < self.start_line:
                raise ValueError("end_line must not precede start_line")
            if self.execution_id is not None:
                raise ValueError("file evidence cannot reference an execution")
        return self


class Finding(Contract):
    claim_id: Text
    assessment: Assessment
    evidence_ids: list[Text] = Field(default_factory=list)
    explanation: Text
    limitations: list[Text] = Field(default_factory=list)
    suggested_next_step: Text | None = None

    @model_validator(mode="after")
    def require_basis(self) -> Self:
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("duplicate evidence references")
        if self.assessment != "inconclusive" and not self.evidence_ids:
            raise ValueError("supported or contradicted findings require evidence")
        if self.assessment == "inconclusive" and not self.limitations:
            raise ValueError("inconclusive findings require a limitation")
        return self


class ExecutionResult(Contract):
    id: Text
    revision: Text
    test_hash: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
    command: list[Text] = Field(min_length=1)
    environment: dict[str, str]
    status: ExecutionStatus
    exit_code: int | None = Field(default=None, strict=True)
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = Field(ge=0, strict=True)

    @model_validator(mode="after")
    def check_exit_status(self) -> Self:
        if self.status == "passed" and self.exit_code != 0:
            raise ValueError("passed execution requires exit_code 0")
        if self.status == "failed" and self.exit_code in (None, 0):
            raise ValueError("failed execution requires a nonzero exit_code")
        if self.status in ("not_run", "blocked") and self.exit_code is not None:
            raise ValueError("unexecuted checks cannot have an exit_code")
        return self


class ApprovedTest(Contract):
    claim_id: Text
    test_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    test_code: str = Field(min_length=1, max_length=8000)
    expected_failure: Text | None = None

    @model_validator(mode="after")
    def check_hash(self) -> Self:
        if hashlib.sha256(self.test_code.encode("utf-8")).hexdigest() != self.test_hash:
            raise ValueError("approved test hash does not match its bytes")
        return self


class ComparisonResult(Contract):
    claim_id: Text
    original_execution_id: Text
    comparison_execution_id: Text
    test_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal[
        "fix_verified_for_test",
        "not_reproduced_for_test",
        "still_failing",
        "inconclusive",
    ]
    limitations: list[Text] = Field(min_length=1)


class AnalysisReport(Contract):
    schema_version: Literal["1.0"] = "1.0"
    is_example: bool = False
    id: Text
    repository: Text
    revision: Text
    comparison_revision: Text | None = None
    model: Text
    stage: Stage = "queued"
    claims: list[Claim] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    executions: list[ExecutionResult] = Field(default_factory=list)
    approved_tests: list[ApprovedTest] = Field(default_factory=list)
    comparisons: list[ComparisonResult] = Field(default_factory=list)
    errors: list[Text] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_references(self) -> Self:
        for records in (self.claims, self.evidence, self.executions):
            ids = [record.id for record in records]
            if len(ids) != len(set(ids)):
                raise ValueError("record IDs must be unique within each collection")
        claims = {c.id for c in self.claims}
        evidence = {e.id for e in self.evidence}
        executions = {e.id: e for e in self.executions}
        revisions = {self.revision, self.comparison_revision} - {None}
        assessed = []
        for finding in self.findings:
            if finding.claim_id not in claims:
                raise ValueError("finding references unknown claim")
            if not set(finding.evidence_ids) <= evidence:
                raise ValueError("finding references unknown evidence")
            assessed.append(finding.claim_id)
        if len(set(assessed)) != len(assessed):
            raise ValueError("only one finding per claim is allowed")
        if self.stage == "complete" and set(assessed) != claims:
            raise ValueError("complete report requires a finding for every claim")
        for item in self.evidence:
            if item.revision not in revisions:
                raise ValueError("evidence revision is outside this analysis")
            if item.execution_id is not None:
                run = executions.get(item.execution_id)
                if run is None or run.revision != item.revision:
                    raise ValueError("execution evidence has no matching run/revision")
                if run.status in ("not_run", "blocked"):
                    raise ValueError(
                        "unexecuted check cannot supply execution evidence"
                    )
        if any(run.revision not in revisions for run in self.executions):
            raise ValueError("execution revision is outside this analysis")
        for item in self.comparisons:
            before = executions.get(item.original_execution_id)
            after = executions.get(item.comparison_execution_id)
            if item.claim_id not in claims or before is None or after is None:
                raise ValueError("comparison references unknown claim or execution")
            if (
                before.revision != self.revision
                or after.revision != self.comparison_revision
            ):
                raise ValueError("comparison executions have incorrect revisions")
            if before.test_hash != item.test_hash or after.test_hash != item.test_hash:
                raise ValueError("comparison requires identical test hashes")
            if item.status == "fix_verified_for_test" and not (
                before.status == "failed"
                and after.status == "passed"
                and before.revision != after.revision
                and re.fullmatch(
                    r"sha256:[0-9a-f]{64}", before.environment.get("image", "")
                )
                and before.environment.get("image") == after.environment.get("image")
            ):
                raise ValueError(
                    "verified comparison requires failure then pass in one immutable image"
                )
        return self
