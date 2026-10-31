"""Single-user extraction jobs. Retrieval and assessment are not implemented here."""

from collections.abc import Callable
from threading import Lock
from uuid import uuid4

from nobluff.model import (
    ClaimExtractionResult,
    ExtractionError,
    OllamaSettings,
    extract_claims,
)
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
    ):
        if max_reports < 1:
            raise ValueError("max_reports must be positive")
        self.settings = settings
        self.extractor = extractor
        self.max_reports = max_reports
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
            self._update(identifier, stage="extracting")
            result = self.extractor(report_text, self.settings)
            if result.model != self.settings.model:
                raise ExtractionError(
                    "unexpected_model", "The extractor returned a different model."
                )
            self._update(identifier, stage="awaiting_evidence", claims=result.claims)
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
