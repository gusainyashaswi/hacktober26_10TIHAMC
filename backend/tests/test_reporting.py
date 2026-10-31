import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from nobluff.api import create_app
from nobluff.model import OllamaSettings
from nobluff.pipeline import AnalysisService
from nobluff.reporting import export_report
from nobluff.schemas import AnalysisReport, AnalysisRequest


def test_fixture_exports_same_data():
    path = Path(__file__).resolve().parents[2] / "examples/contracts/report.json"
    report = AnalysisReport.model_validate_json(path.read_text())
    assert json.loads(export_report(report, "json")) == report.model_dump(mode="json")
    markdown = export_report(report, "markdown")
    assert "SYNTHETIC EXAMPLE" in markdown
    assert report.evidence[0].excerpt in markdown
    assert report.findings[0].explanation in markdown


def test_incomplete_and_injected_text_stay_explicit():
    report = AnalysisReport(
        id="r", repository="x\n# forged", revision="main", model="qwen3:8b"
    )
    rendered = export_report(report, "markdown")
    assert "INCOMPLETE INVESTIGATION" in rendered
    assert "```text\nRepository: x\n# forged" in rendered
    with pytest.raises(ValueError):
        export_report(report, "html")


def test_download_routes_and_invalid_format():
    service = AnalysisService(OllamaSettings())
    identifier = service.submit(
        AnalysisRequest(repository="a/b", revision="main", report_text="x")
    )
    with TestClient(create_app(service)) as client:
        response = client.get(f"/api/analyses/{identifier}/export?format=json")
        assert response.status_code == 200
        assert response.json()["stage"] == "queued"
        assert (
            'filename="nobluff-report.json"' in response.headers["content-disposition"]
        )
        assert (
            "INCOMPLETE"
            in client.get(f"/api/analyses/{identifier}/export?format=markdown").text
        )
        assert (
            client.get(f"/api/analyses/{identifier}/export?format=html").status_code
            == 422
        )
        assert client.get("/api/analyses/missing/export").status_code == 404
