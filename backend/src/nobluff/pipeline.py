"""Single-user extraction jobs. Retrieval and assessment are not implemented here."""

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
from nobluff.schemas import AnalysisReport, AnalysisRequest


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
    ):
        if max_reports < 1:
            raise ValueError("max_reports must be positive")
        self.settings = settings
        self.extractor = extractor
        self.max_reports = max_reports
        self.snapshot_loader = snapshot_loader
        self.assessor = assessor
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
            return identifier

    def get(self, identifier: str) -> AnalysisReport | None:
        with self._lock:
            report = self._reports.get(identifier)
            return report.model_copy(deep=True) if report is not None else None

    def _update(self, identifier: str, **changes) -> None:
        with self._lock:
            data = self._reports[identifier].model_dump() | changes
            self._reports[identifier] = AnalysisReport.model_validate(data)

    def run(self, identifier: str, report_text: str) -> None:
        try:
            snapshot = None
            if self.snapshot_loader:
                self._update(identifier, stage="loading")
                request = self._requests[identifier]
                snapshot = self.snapshot_loader(request.repository, request.revision)
                with self._lock:
                    self._snapshots[identifier] = snapshot
                self._update(identifier, revision=snapshot.commit)
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
