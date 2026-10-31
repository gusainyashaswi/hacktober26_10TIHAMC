"""Bounded, single-user source investigations and approved controlled execution."""

import hashlib
from collections.abc import Callable
from threading import Lock
from uuid import uuid4

from nobluff.model import (
    ClaimExtractionResult,
    ExtractionError,
    OllamaSettings,
    assess_claims,
    extract_claims,
)
from nobluff.retrieval import Snapshot, SnapshotError, retrieve_evidence
from nobluff.schemas import (
    AnalysisReport,
    AnalysisRequest,
    ApprovedTest,
    Evidence,
    Finding,
)
from nobluff.verification.comparison import compare_runs
from nobluff.verification.policy import VerificationPlan, observed_expected_failure


class CapacityError(RuntimeError):
    """No more local work can be admitted right now."""


class AnalysisService:
    """Bounded process-local reports; start one server worker, not multiple.

    Allow one active inference to avoid concurrent model loads on a laptop.
    Reports are copied at boundaries so callers cannot mutate stored state.
    """

    def __init__(
        self,
        settings: OllamaSettings,
        *,
        extractor: Callable[..., ClaimExtractionResult] = extract_claims,
        max_reports: int = 100,
        snapshot_loader: Callable[[str, str], Snapshot] | None = None,
        assessor: Callable = assess_claims,
        runner: Callable | None = None,
        workspace=None,
    ):
        if max_reports < 1:
            raise ValueError("max_reports must be positive")
        self.settings = settings
        self.extractor = extractor
        self.max_reports = max_reports
        self.snapshot_loader = snapshot_loader
        self.assessor = assessor
        self.runner = runner
        self.workspace = workspace
        self._snapshots: dict[str, Snapshot] = {}
        self._requests: dict[str, AnalysisRequest] = {}
        self._reports: dict[str, AnalysisReport] = {}
        self._active: str | None = None
        self._lock = Lock()

    def submit(self, request: AnalysisRequest) -> str:
        with self._lock:
            if self._active is not None:
                raise CapacityError(
                    "An extraction is already running; retry after it finishes."
                )
            if len(self._reports) >= self.max_reports:
                raise CapacityError(
                    "Local report storage is full; restart the development server to clear it."
                )
            identifier = str(uuid4())
            self._reports[identifier] = AnalysisReport(
                id=identifier,
                repository=request.repository,
                revision=request.revision,
                comparison_revision=request.comparison_revision,
                model=self.settings.model,
            )
            self._active = identifier
            self._requests[identifier] = request.model_copy(deep=True)
            if self.workspace:
                self.workspace.save(request, self._reports[identifier])
            return identifier

    def get(self, identifier: str) -> AnalysisReport | None:
        with self._lock:
            report = self._reports.get(identifier)
            if report is None and self.workspace:
                stored = self.workspace.investigation(identifier)
                if stored:
                    report = AnalysisReport.model_validate_json(stored["report_json"])
                    if report.stage not in ("complete", "error", "awaiting_evidence"):
                        report = AnalysisReport.model_validate(
                            report.model_dump()
                            | {
                                "stage": "error",
                                "errors": [
                                    "interrupted: The server restarted before this investigation finished."
                                ],
                            }
                        )
                    self._reports[identifier] = report
                    self._requests[identifier] = AnalysisRequest.model_validate_json(
                        stored["request_json"]
                    )
            return report.model_copy(deep=True) if report is not None else None

    def _update(self, identifier: str, **changes) -> None:
        with self._lock:
            data = self._reports[identifier].model_dump() | changes
            self._reports[identifier] = AnalysisReport.model_validate(data)
            if self.workspace:
                self.workspace.save(
                    self._requests[identifier], self._reports[identifier]
                )

    def run(self, identifier: str, report_text: str) -> None:
        try:
            snapshot = None
            if self.snapshot_loader:
                self._update(identifier, stage="loading")
                request = self._requests[identifier]
                snapshot = self.snapshot_loader(request.repository, request.revision)
                with self._lock:
                    self._snapshots[identifier] = snapshot
                self._update(
                    identifier,
                    revision=snapshot.commit,
                    source_revision=snapshot.commit,
                )
                if request.source_revision:
                    snapshot = self.snapshot_loader(
                        request.source_repository or request.repository,
                        request.source_revision,
                    )
                    self._update(
                        identifier,
                        comparison_revision=snapshot.commit,
                        source_revision=snapshot.commit,
                        source_repository=request.source_repository
                        or request.repository,
                    )
            self._update(identifier, stage="extracting")
            result = self.extractor(report_text, self.settings)
            if result.model != self.settings.model:
                raise ExtractionError(
                    "unexpected_model", "The extractor returned a different model."
                )
            self._update(identifier, stage="awaiting_evidence", claims=result.claims)
            if snapshot is not None:
                all_evidence = {}
                findings = []
                for claim in result.claims:
                    self._update(identifier, stage="retrieving")
                    snippets = retrieve_evidence(snapshot, [claim])
                    all_evidence.update({item.id: item for item in snippets})
                    self._update(
                        identifier,
                        stage="assessing",
                        evidence=list(all_evidence.values()),
                    )
                    assessment = self.assessor([claim], snippets, self.settings)
                    findings.extend(assessment.findings)
                    self._update(identifier, findings=findings)
                self._update(identifier, stage="complete")
        except SnapshotError as exc:
            self._update(identifier, stage="error", errors=[f"retrieval_error: {exc}"])
        except ExtractionError as exc:
            self._update(identifier, stage="error", errors=[f"{exc.code}: {exc}"])
        except Exception:  # noqa: BLE001 -- background boundary must record failure and release admission
            # Do not leak issue text, filesystem details or exception payloads.
            self._update(
                identifier,
                stage="error",
                errors=["internal_error: Extraction could not finish."],
            )
        finally:
            with self._lock:
                if self._active == identifier:
                    self._active = None

    def admit_verification(
        self, identifier: str, plan: VerificationPlan, *, comparison: bool = False
    ) -> None:
        with self._lock:
            report = self._reports.get(identifier)
            if report is None:
                raise KeyError(identifier)
            if self.runner is None:
                raise NotImplementedError(
                    "Verification must be enabled by the local operator"
                )
            if (
                self._active is not None
                or report.stage != "complete"
                or self.snapshot_loader is None
            ):
                raise CapacityError(
                    "Wait for a complete source investigation before verification"
                )
            if plan.claim_id not in {c.id for c in report.claims}:
                raise ValueError("Unknown claim for verification")
            if comparison and (
                not self._requests[identifier].comparison_revision or report.comparisons
            ):
                raise ValueError(
                    "Supply a comparison revision and use a fresh analysis for each comparison"
                )
            self._active = identifier

    def run_verification(self, identifier: str, plan: VerificationPlan) -> None:
        try:
            self._update(identifier, stage="verifying")
            run = self.runner(self.original_snapshot(identifier), plan)
            if (
                run.test_hash
                != hashlib.sha256(plan.test_code.encode("utf-8")).hexdigest()
            ):
                raise ValueError("Execution hash differs from the approved test")
            report = self.get(identifier)
            new_evidence = []
            findings = report.findings
            if run.status not in ("not_run", "blocked"):
                item = Evidence(
                    id=f"execution-{run.id}",
                    kind="execution",
                    revision=run.revision,
                    execution_id=run.id,
                    excerpt=f"Status: {run.status}\n{run.stdout}\n{run.stderr}",
                )
                new_evidence.append(item)
                if observed_expected_failure(run, plan):
                    findings = [
                        Finding(
                            claim_id=f.claim_id,
                            assessment="supported",
                            evidence_ids=[item.id],
                            explanation="The approved test failed and its output contains the declared expected failure.",
                            limitations=[
                                "Supports only the approved test and environment; review whether the test represents the claim."
                            ],
                        )
                        if f.claim_id == plan.claim_id
                        else f
                        for f in findings
                    ]
            self._update(
                identifier,
                stage="complete",
                executions=[*report.executions, run],
                approved_tests=[
                    *report.approved_tests,
                    ApprovedTest(
                        claim_id=plan.claim_id,
                        test_hash=run.test_hash,
                        test_code=plan.test_code,
                        expected_failure=plan.expected_failure,
                    ),
                ],
                evidence=[*report.evidence, *new_evidence],
                findings=findings,
            )
        except Exception:  # noqa: BLE001 -- background boundary must release admission and record failure
            self._update(
                identifier,
                stage="error",
                errors=[
                    "verification_error: Controlled verification failed to finish."
                ],
            )
        finally:
            with self._lock:
                self._active = None

    def run_comparison(self, identifier: str, plan: VerificationPlan) -> None:
        try:
            self._update(identifier, stage="loading")
            request = self._requests[identifier]
            after_snapshot = self.snapshot_loader(
                request.source_repository or request.repository,
                request.comparison_revision,
            )
            self._update(
                identifier, stage="verifying", comparison_revision=after_snapshot.commit
            )
            before = self.runner(self.original_snapshot(identifier), plan)
            after = self.runner(after_snapshot, plan)
            comparison = compare_runs(before, after, plan)
            report = self.get(identifier)
            evidence = [
                Evidence(
                    id=f"execution-{run.id}",
                    kind="execution",
                    revision=run.revision,
                    execution_id=run.id,
                    excerpt=f"Status: {run.status}\n{run.stdout}\n{run.stderr}",
                )
                for run in (before, after)
                if run.status not in ("not_run", "blocked")
            ]
            findings = report.findings
            if observed_expected_failure(before, plan):
                findings = [
                    Finding(
                        claim_id=f.claim_id,
                        assessment="supported",
                        evidence_ids=[f"execution-{before.id}"],
                        explanation="The approved test reproduced the declared exception on the original snapshot.",
                        limitations=[
                            "Limited to this reviewed test and recorded environment."
                        ],
                    )
                    if f.claim_id == plan.claim_id
                    else f
                    for f in findings
                ]
            self._update(
                identifier,
                stage="complete",
                executions=[*report.executions, before, after],
                approved_tests=[
                    *report.approved_tests,
                    ApprovedTest(
                        claim_id=plan.claim_id,
                        test_hash=before.test_hash,
                        test_code=plan.test_code,
                        expected_failure=plan.expected_failure,
                    ),
                ],
                evidence=[*report.evidence, *evidence],
                findings=findings,
                comparisons=[*report.comparisons, comparison],
            )
        except Exception:  # noqa: BLE001 -- isolate background work and always release admission
            self._update(
                identifier,
                stage="error",
                errors=["comparison_error: Controlled comparison could not finish."],
            )
        finally:
            with self._lock:
                self._active = None

    def original_snapshot(self, identifier):
        if identifier not in self._snapshots:
            report = self.get(identifier)
            self._snapshots[identifier] = self.snapshot_loader(
                report.repository, report.revision
            )
        return self._snapshots[identifier]
