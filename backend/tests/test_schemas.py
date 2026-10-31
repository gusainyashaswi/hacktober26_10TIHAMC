"""Contract regressions; the example is deliberately synthetic, not a real run."""

import json
from pathlib import Path

import pytest
from nobluff.schemas import AnalysisReport, AnalysisRequest, Evidence, ExecutionResult
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def report_data():
    return json.loads((ROOT / "examples/contracts/report.json").read_text())


def test_example_round_trips(report_data):
    report = AnalysisReport.model_validate(report_data)
    assert report.is_example is True
    assert AnalysisReport.model_validate_json(report.model_dump_json()) == report
    assert AnalysisReport.model_json_schema()["additionalProperties"] is False


@pytest.mark.parametrize("field", ["repository", "revision", "report_text"])
def test_request_rejects_blank_values(field):
    data = {"repository": "owner/repo", "revision": "main", "report_text": "A crash"}
    data[field] = "   "
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate(data)


def test_rejects_unknown_fields(report_data):
    report_data["findings"][0]["confidence"] = 99
    with pytest.raises(ValidationError):
        AnalysisReport.model_validate(report_data)


@pytest.mark.parametrize(
    "path",
    ["/etc/passwd", "../secret", "src/../../secret", "C:/secret", "src\\file.py", "."],
)
def test_rejects_non_repository_paths(report_data, path):
    report_data["evidence"][0]["path"] = path
    with pytest.raises(ValidationError):
        AnalysisReport.model_validate(report_data)


@pytest.mark.parametrize("start,end", [(0, 2), (3, 2), (True, 2), ("1", 2)])
def test_rejects_invalid_line_ranges(report_data, start, end):
    report_data["evidence"][0].update(start_line=start, end_line=end)
    with pytest.raises(ValidationError):
        AnalysisReport.model_validate(report_data)


@pytest.mark.parametrize("target", ["claim", "evidence", "revision"])
def test_rejects_untraceable_report(report_data, target):
    if target == "claim":
        report_data["findings"][0]["claim_id"] = "invented"
    elif target == "evidence":
        report_data["findings"][0]["evidence_ids"] = ["invented"]
    else:
        report_data["evidence"][0]["revision"] = "another-revision"
    with pytest.raises(ValidationError):
        AnalysisReport.model_validate(report_data)


@pytest.mark.parametrize("collection", ["claims", "evidence", "findings"])
def test_rejects_duplicate_records(report_data, collection):
    report_data[collection].append(report_data[collection][0].copy())
    with pytest.raises(ValidationError):
        AnalysisReport.model_validate(report_data)


def test_complete_requires_all_findings(report_data):
    report_data["findings"].pop()
    with pytest.raises(ValidationError):
        AnalysisReport.model_validate(report_data)
    report_data["stage"] = "assessing"
    AnalysisReport.model_validate(report_data)


def test_conclusive_verdict_requires_evidence(report_data):
    report_data["findings"][0]["evidence_ids"] = []
    with pytest.raises(ValidationError):
        AnalysisReport.model_validate(report_data)


def test_inconclusive_requires_reason(report_data):
    report_data["findings"][1]["limitations"] = []
    with pytest.raises(ValidationError):
        AnalysisReport.model_validate(report_data)


def execution(**overrides):
    data = {
        "id": "run-1",
        "revision": "fixture-original",
        "test_hash": "a" * 64,
        "command": ["python", "-m", "pytest"],
        "environment": {"python": "3.11"},
        "status": "passed",
        "exit_code": 0,
        "duration_ms": 10,
    }
    return ExecutionResult.model_validate(data | overrides)


@pytest.mark.parametrize(
    "overrides",
    [
        {"status": "passed", "exit_code": 1},
        {"status": "failed", "exit_code": 0},
        {"status": "failed", "exit_code": None},
        {"status": "blocked", "exit_code": 0},
        {"duration_ms": -1},
        {"test_hash": "not-a-hash"},
        {"command": []},
    ],
)
def test_execution_consistency(overrides):
    with pytest.raises(ValidationError):
        execution(**overrides)


def test_setup_error_remains_separate():
    run = execution(status="setup_error", exit_code=1, stderr="Missing dependency")
    assert run.status == "setup_error"


def test_execution_evidence_requires_real_reference(report_data):
    item = Evidence(
        id="exec-1",
        kind="execution",
        revision="fixture-original",
        excerpt="illustrative output",
        execution_id="run-1",
    )
    report_data["evidence"].append(item.model_dump())
    with pytest.raises(ValidationError):
        AnalysisReport.model_validate(report_data)
    report_data["executions"] = [execution().model_dump()]
    AnalysisReport.model_validate(report_data)
    report_data["executions"][0].update(status="blocked", exit_code=None)
    with pytest.raises(ValidationError):
        AnalysisReport.model_validate(report_data)


def test_list_defaults_do_not_leak():
    first = AnalysisReport(id="1", repository="x", revision="r", model="qwen3:8b")
    second = AnalysisReport(id="2", repository="x", revision="r", model="qwen3:8b")
    first.errors.append("failure")
    assert second.errors == []
