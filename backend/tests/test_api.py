"""HTTP orchestration tests with a fake extractor; no model accuracy claims."""

import pytest
from fastapi.testclient import TestClient
from nobluff.api import create_app
from nobluff.model import ClaimExtractionResult, ExtractionError, OllamaSettings
from nobluff.pipeline import AnalysisService, CapacityError
from nobluff.schemas import AnalysisReport, AnalysisRequest, Claim

INPUT = {
    "repository": "owner/repository",
    "revision": "main",
    "report_text": "The exporter crashes.",
}


def successful(text, settings):
    return ClaimExtractionResult(
        model=settings.model,
        created_at="2026-11-01T00:00:00Z",
        attempts=1,
        elapsed_ms=1,
        claims=[Claim(id="claim-1", text=text, kind="behavior")],
    )


@pytest.fixture
def service():
    return AnalysisService(OllamaSettings(), extractor=successful)


def test_post_then_poll_returns_real_contract_without_verdicts(service):
    with TestClient(create_app(service)) as client:
        response = client.post("/api/analyses", json=INPUT)
        assert response.status_code == 202
        assert response.headers["x-nobluff-scope"] == "claim_extraction_only"
        report_response = client.get(response.headers["location"])
        assert report_response.status_code == 200
        report = AnalysisReport.model_validate(report_response.json())
        assert report.repository == "https://github.com/owner/repository"
        assert report.stage == "awaiting_evidence"
        assert report.claims[0].text == INPUT["report_text"]
        assert report.evidence == report.findings == report.executions == []
        assert (
            client.post(response.headers["location"] + "/verification").status_code
            == 501
        )


@pytest.mark.parametrize("code", ["unavailable", "timeout", "invalid_output"])
def test_model_failure_is_visible_and_next_request_is_possible(code):
    def failing(text, settings):
        raise ExtractionError(code, "Model could not finish.")

    service = AnalysisService(OllamaSettings(), extractor=failing)
    with TestClient(create_app(service)) as client:
        response = client.post("/api/analyses", json=INPUT)
        report = client.get(response.headers["location"]).json()
        assert report["stage"] == "error"
        assert report["errors"] == [f"{code}: Model could not finish."]
        assert report["claims"] == []
        assert client.post("/api/analyses", json=INPUT).status_code == 202


def test_unexpected_error_does_not_leak_input_or_diagnostics():
    def failing(text, settings):
        raise RuntimeError("secret diagnostic and report text")

    with TestClient(
        create_app(AnalysisService(OllamaSettings(), extractor=failing))
    ) as client:
        response = client.post("/api/analyses", json=INPUT)
        report = client.get(response.headers["location"]).json()
        assert report["stage"] == "error"
        assert "secret" not in str(report["errors"])


@pytest.mark.parametrize(
    "patch",
    [
        {"report_text": " "},
        {"report_text": "a" * 12001},
        {"revision": " "},
        {"revision": "main\nother"},
        {"model": "unapproved-model"},
        {"repository": "/Users/private"},
        {"repository": "http://localhost/private"},
        {"repository": "https://github.com.evil.test/owner/repo"},
        {"repository": "https://user:password@github.com/owner/repo"},
        {"repository": "https://github.com/owner/repo/issues/1"},
        {"repository": "https://github.com/owner/repo?token=private"},
        {"repository": "owner/.."},
    ],
)
def test_invalid_requests_do_not_reach_extractor(service, patch):
    with TestClient(create_app(service)) as client:
        response = client.post("/api/analyses", json=INPUT | patch)
        assert response.status_code == 422
        assert all("input" not in error for error in response.json()["detail"])


def test_git_url_normalization(service):
    with TestClient(create_app(service)) as client:
        response = client.post(
            "/api/analyses",
            json=INPUT | {"repository": "https://github.com/owner/repo.git"},
        )
        assert (
            client.get(response.headers["location"]).json()["repository"]
            == "https://github.com/owner/repo"
        )


def test_unknown_analysis_is_404(service):
    with TestClient(create_app(service)) as client:
        assert client.get("/api/analyses/missing").status_code == 404
        assert client.post("/api/analyses/missing/verification").status_code == 404


def test_health_is_not_a_claim_of_model_readiness(service):
    with TestClient(create_app(service)) as client:
        data = client.get("/api/health").json()
        assert data["status"] == "ok"
        assert data["model_readiness"] == "not_checked"
        assert data["verification"] is False


def test_cors_preflight_exact_origins(service):
    with TestClient(create_app(service)) as client:
        for origin, allowed in [
            ("http://localhost:5173", True),
            ("https://evil.test", False),
        ]:
            response = client.options(
                "/api/analyses",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                },
            )
            assert (
                response.headers.get("access-control-allow-origin") == origin
            ) is allowed


def test_request_body_size_is_bounded(service):
    with TestClient(create_app(service)) as client:
        response = client.post("/api/analyses", content=b"x" * 64001)
        assert response.status_code == 413


def test_invalid_json_is_422(service):
    with TestClient(create_app(service)) as client:
        assert (
            client.post(
                "/api/analyses",
                content="{",
                headers={"Content-Type": "application/json"},
            ).status_code
            == 422
        )


def test_busy_api_returns_retry_after(service):
    service.submit(AnalysisRequest(**INPUT))
    with TestClient(create_app(service)) as client:
        response = client.post("/api/analyses", json=INPUT)
        assert response.status_code == 429
        assert response.headers["retry-after"] == "2"


def test_service_progress_capacity_and_copy_isolation():
    service = AnalysisService(OllamaSettings(), extractor=successful, max_reports=1)
    identifier = service.submit(AnalysisRequest(**INPUT))
    assert service.get(identifier).stage == "queued"
    with pytest.raises(CapacityError):
        service.submit(AnalysisRequest(**INPUT))
    service.run(identifier, INPUT["report_text"])
    report = service.get(identifier)
    report.claims.clear()
    assert len(service.get(identifier).claims) == 1
    with pytest.raises(CapacityError):
        service.submit(AnalysisRequest(**INPUT))


def test_extractor_can_observe_extracting_stage():
    service = None
    identifier = None

    def observing(text, settings):
        assert service.get(identifier).stage == "extracting"
        return successful(text, settings)

    service = AnalysisService(OllamaSettings(), extractor=observing)
    identifier = service.submit(AnalysisRequest(**INPUT))
    service.run(identifier, INPUT["report_text"])
    assert service.get(identifier).stage == "awaiting_evidence"


def test_openapi_documents_request_and_report(service):
    with TestClient(create_app(service)) as client:
        document = client.get("/openapi.json").json()
        assert "APIAnalysisRequest" in document["components"]["schemas"]
        assert "AnalysisReport" in document["components"]["schemas"]
